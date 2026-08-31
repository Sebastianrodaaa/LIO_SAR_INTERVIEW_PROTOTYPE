"""Python-controlled sequential loop over ICM stage folders.

This is Anthropic's *workflow* pattern (prompt chaining), not an autonomous
agent. Control flow lives in this file. The model is invoked once per folder
and never decides what the next folder is.

Context degradation is avoided by construction: each iteration reads
  1. that folder's CONTEXT.md
  2. the previous folder's output.md
  3. a GraphRAG slice named in the contract
and writes exactly one output.md. Sister stages' prompts never enter the
window.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from init_workspace import PIPELINE, STAGES, WORKSPACE
from engine.graphrag import retrieve
from engine.graph_store import GraphStore
from engine.hats import HATS
from engine.live_thoughts import conclusion_beats, thought_beats
from engine.llm import StructuredLLM, render_user_prompt
from engine.schemas import ContextBudget, STAGE_SCHEMAS

VOICE_PATH = WORKSPACE / "_shared" / "voice.md"


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class ProcurementOrchestrator:
    def __init__(self, store: GraphStore, llm: StructuredLLM | None = None) -> None:
        self.store = store
        self.llm = llm or StructuredLLM()

    def run(
        self,
        request: dict[str, Any],
        gated: bool = False,
        stage_pause_s: float = 0.7,
        start_stage: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        voice = VOICE_PATH.read_text(encoding="utf-8") if VOICE_PATH.exists() else ""
        working = dict(request)
        self._hydrate_working(working)

        start_idx = STAGES.index(start_stage) if start_stage else 0
        previous_output = self._previous_output(start_idx)

        for index, stage in enumerate(STAGES):
            if index < start_idx:
                continue

            yield from self._run_one(
                stage,
                index,
                working,
                previous_output,
                voice,
                trace_pause_s=0.0 if not stage_pause_s else 0.32,
            )

            previous_output = (PIPELINE / stage / "output.md").read_text(encoding="utf-8")
            sourcing = PIPELINE / "03_vendor_sourcing" / "output.json"
            if stage == "03_vendor_sourcing" and sourcing.exists():
                data = json.loads(sourcing.read_text(encoding="utf-8"))
                working["primary_vendor_id"] = data.get("primary_vendor_id")
                working["primary_tier"] = data.get("primary_tier")

            is_last = index == len(STAGES) - 1
            if gated and not is_last:
                yield {
                    "event": "awaiting_human",
                    "stage": stage,
                    "next_stage": STAGES[index + 1],
                }
                return

            if not gated and stage_pause_s and not is_last:
                time.sleep(stage_pause_s)

        yield {"event": "cycle_complete", "stage": STAGES[-1]}

    def run_from(
        self,
        request: dict[str, Any],
        start_stage: str,
        gated: bool = True,
        stage_pause_s: float = 0.0,
    ) -> Iterator[dict[str, Any]]:
        """Resume at start_stage. Gated continue runs *one* stage, then pauses again."""
        yield from self.run(
            request,
            gated=gated,
            stage_pause_s=stage_pause_s,
            start_stage=start_stage,
        )

    def _run_one(
        self,
        stage: str,
        index: int,
        working: dict[str, Any],
        previous_output: str,
        voice: str,
        trace_pause_s: float = 0.0,
    ) -> Iterator[dict[str, Any]]:
        folder = PIPELINE / stage
        hat = HATS[stage]
        contract = (folder / "CONTEXT.md").read_text(encoding="utf-8")
        retrieval = retrieve(self.store, stage, working)
        user = render_user_prompt(
            stage=stage,
            contract=contract,
            previous_output=previous_output,
            retrieval=retrieval,
            request=working,
            voice=voice,
        )
        system = (
            "You are the single Northstar procurement agent executing one ICM "
            "stage. Do not perform other stages. Do not call tools."
        )
        budget = ContextBudget(
            layer_0_2=estimate_tokens(contract) + estimate_tokens(system),
            layer_3=estimate_tokens(voice) + estimate_tokens(json.dumps(retrieval)),
            layer_4=estimate_tokens(previous_output),
            retrieval=estimate_tokens(json.dumps(retrieval)),
        )
        budget.total = budget.layer_0_2 + budget.layer_3 + budget.layer_4

        highlight = retrieval.get("highlight", [])
        yield {
            "event": "stage_start",
            "stage": stage,
            "index": index,
            "hat": hat["hat"],
            "retrieval_query": retrieval.get("query"),
            "highlight": highlight,
            "budget": budget.model_dump(),
            "provider": self.llm.provider,
            "request": {
                "item": working.get("item"),
                "amount_usd": working.get("amount_usd"),
                "requester_id": working.get("requester_id"),
                "vendor_hint": working.get("vendor_hint"),
            },
        }

        yield _reasoning(
            stage,
            "read",
            "Load contract",
            f"{stage}/CONTEXT.md"
            + (f" + {STAGES[index - 1]}/output.md" if index else " + this chat request"),
            path=f"workspace/pipeline/{stage}/CONTEXT.md",
            highlight=highlight,
            extra={"budget": budget.model_dump()},
        )
        query = retrieval.get("query")
        if query:
            yield _reasoning(stage, "tool", "GraphRAG", str(query), highlight=highlight)
            if trace_pause_s:
                time.sleep(trace_pause_s)

        thought = ""
        for event in _stream_thoughts(stage, thought_beats(stage, working, retrieval), trace_pause_s):
            yield event
            if event.get("content"):
                thought = event["content"]

        started = time.time()
        result = self.llm.complete(stage, system, user, working, retrieval)
        schema = STAGE_SCHEMAS[stage]
        validated = schema.model_validate(result.model_dump())
        markdown = validated.to_markdown()
        payload = validated.model_dump()

        for event in _stream_thoughts(
            stage,
            conclusion_beats(stage, payload),
            trace_pause_s,
            start=thought,
        ):
            yield event
            if event.get("content"):
                thought = event["content"]

        output_path = folder / "output.md"
        header = (
            f"<!-- ICM product artifact. Schema: {schema.__name__}. "
            f"Validated JSON lives beside this file as output.json. -->\n\n"
        )
        output_path.write_text(header + markdown, encoding="utf-8")
        (folder / "output.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        if stage == "03_vendor_sourcing":
            working["primary_vendor_id"] = validated.primary_vendor_id
            working["primary_tier"] = validated.primary_tier

        rel = str(output_path.relative_to(WORKSPACE.parent))
        accumulated = ""
        for chunk in _markdown_chunks(markdown):
            accumulated = f"{accumulated}\n\n{chunk}".strip() if accumulated else chunk
            yield {
                "event": "delta",
                "stage": stage,
                "text": chunk,
                "content": accumulated,
                "highlight": highlight,
            }
            if trace_pause_s:
                time.sleep(trace_pause_s)

        yield _reasoning(
            stage,
            "write",
            "Wrote output.md",
            rel,
            path=rel,
            highlight=highlight,
        )

        yield {
            "event": "file_written",
            "stage": stage,
            "hat": hat["hat"],
            "path": rel,
            "content": header + markdown,
            "json": payload,
            "summary": _brief_summary(validated, payload),
            "highlight": highlight,
            "budget": budget.model_dump(),
            "elapsed_ms": int((time.time() - started) * 1000),
            "provider": self.llm.provider,
        }

    def _previous_output(self, start_idx: int) -> str:
        if start_idx <= 0:
            return ""
        path = PIPELINE / STAGES[start_idx - 1] / "output.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _hydrate_working(self, working: dict[str, Any]) -> None:
        sourcing = PIPELINE / "03_vendor_sourcing" / "output.json"
        if sourcing.exists() and "primary_vendor_id" not in working:
            data = json.loads(sourcing.read_text(encoding="utf-8"))
            if data.get("primary_vendor_id"):
                working["primary_vendor_id"] = data["primary_vendor_id"]


def _reasoning(
    stage: str,
    kind: str,
    label: str,
    detail: str,
    path: str | None = None,
    highlight: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event": "reasoning",
        "stage": stage,
        "kind": kind,
        "label": label,
        "detail": detail,
        "highlight": highlight or [],
    }
    if path:
        event["path"] = path
    if extra:
        event.update(extra)
    return event


def _paced(events: list[dict[str, Any]], pause_s: float) -> Iterator[dict[str, Any]]:
    for event in events:
        yield event
        if pause_s:
            time.sleep(pause_s)


def _stream_thoughts(
    stage: str,
    beats: list[dict[str, Any]],
    pause_s: float,
    start: str = "",
) -> Iterator[dict[str, Any]]:
    """Yield thought_delta so the cockpit types the analysis instead of a checklist."""
    acc = start.strip()
    for beat in beats:
        text = (beat.get("text") or "").strip()
        if not text:
            continue
        highlight = beat.get("highlight") or []
        pieces = text.split() if pause_s else [text]
        built = ""
        for word in pieces:
            built = word if not built else f"{built} {word}"
            current = f"{acc} {built}".strip() if acc else built
            yield {
                "event": "thought_delta",
                "stage": stage,
                "kind": "thought",
                "text": word,
                "content": current,
                "highlight": highlight,
            }
            if pause_s:
                time.sleep(min(0.036, pause_s))
        acc = f"{acc} {text}".strip() if acc else text
        if pause_s:
            time.sleep(pause_s * 0.45)


def _markdown_chunks(markdown: str) -> list[str]:
    parts = [p.strip() for p in markdown.split("\n\n") if p.strip()]
    return parts or [markdown.strip()]


def _brief_summary(validated: Any, payload: dict[str, Any]) -> str:
    if hasattr(validated, "summary") and validated.summary:
        return str(validated.summary)
    if payload.get("requester_name"):
        ooo = (
            f" {payload.get('manager_name')} is out of office."
            if payload.get("manager_out_of_office")
            else ""
        )
        return (
            f"{payload['requester_name']} wants {payload.get('item')} "
            f"for ${payload.get('amount_usd', 0):,.0f}.{ooo}"
        )
    return ""


def read_pipeline_files() -> list[dict[str, Any]]:
    files = []
    for stage in STAGES:
        folder = PIPELINE / stage
        output = folder / "output.md"
        files.append(
            {
                "stage": stage,
                "contract": (folder / "CONTEXT.md").read_text(encoding="utf-8") if (folder / "CONTEXT.md").exists() else "",
                "output": output.read_text(encoding="utf-8") if output.exists() else "",
                "path": str(output.relative_to(WORKSPACE.parent)) if output.exists() else "",
            }
        )
    return files
