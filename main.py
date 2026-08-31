#!/usr/bin/env python3
"""FastAPI surface for the deterministic procurement cycle.

Endpoints are intentionally few. Orchestration is a Python for-loop over
folders, not a graph of agents. The cockpit subscribes to SSE and tails
output.md files as they are written.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from engine.graph_store import connect_store
from engine.layout import cockpit_graph
from engine.llm import StructuredLLM
from engine.orchestrator import ProcurementOrchestrator, read_pipeline_files
from engine.intent import parse_message
from engine.ask import answer_question
from init_workspace import PIPELINE, STAGES, WORKSPACE
from mock_data_generator import generate as generate_mock
from init_workspace import init_workspace

load_dotenv()

ROOT = Path(__file__).resolve().parent


class ProcurementRequest(BaseModel):
    requester_id: str = "emp-alex-rivera"
    vendor_id: str = "vnd-figma"
    item: str = "Figma Enterprise"
    vendor_hint: str = "Figma"
    category: str = "design-tools"
    amount_usd: float = 15_000
    seats: int = 120
    justification: str = Field(
        default=(
            "Design and Engineering share one component library. Organization-tier "
            "lacks SCIM; POL-SEC-011 requires SSO/SCIM above 25 seats."
        )
    )
    urgency: Literal["low", "normal", "high"] = "high"
    request_id: str = "PR-2026-0847"
    gated: bool = False
    message: str | None = None


class ChatIn(BaseModel):
    message: str
    gated: bool = False


class FileWrite(BaseModel):
    path: str
    content: str


class ResumeRequest(BaseModel):
    request: ProcurementRequest
    from_stage: str


def _bootstrap_if_needed() -> None:
    if not (ROOT / "data" / "employees.json").exists():
        generate_mock()
    if not (PIPELINE / "01_intake" / "CONTEXT.md").exists():
        init_workspace()


_bootstrap_if_needed()
STORE = connect_store()
STORE.seed()
LLM = StructuredLLM()
ORCH = ProcurementOrchestrator(STORE, LLM)
LAST_REQUEST: dict[str, Any] = ProcurementRequest().model_dump()

app = FastAPI(
    title="LIO SAR Procurement Orchestrator",
    description="Single-agent ICM + GraphRAG prototype. No multi-agent framework.",
    version="1.0.0",
)

origins = [
    os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "graph": STORE.backend,
        "llm": LLM.provider,
        "stages": STAGES,
    }


@app.get("/graph")
def graph(highlight: str = "") -> dict[str, Any]:
    ids = [h for h in highlight.split(",") if h]
    return cockpit_graph(STORE.snapshot(), ids)


@app.get("/workspace/files")
def workspace_files() -> dict[str, Any]:
    return {"files": read_pipeline_files()}


@app.put("/workspace/file")
def write_file(body: FileWrite) -> dict[str, str]:
    """Human gate: the operator edits output.md; the next stage reads disk."""
    target = (ROOT / body.path).resolve()
    allowed = (PIPELINE).resolve()
    if allowed not in target.parents and target.parent != allowed:
        raise HTTPException(400, "Writes are limited to workspace/pipeline")
    if target.name not in {"output.md", "output.json"}:
        raise HTTPException(400, "Only output.md / output.json are writable")
    target.write_text(body.content, encoding="utf-8")
    return {"status": "saved", "path": body.path}


@app.get("/seed")
def seed() -> dict[str, Any]:
    path = ROOT / "data" / "seed_scenario.json"
    return json.loads(path.read_text(encoding="utf-8"))


_STREAM_DONE = object()


def _sse(events) -> StreamingResponse:
    async def gen():
        # Pull the next orchestrator event in a worker thread (it may sleep)
        # then await so Starlette flushes the frame instead of buffering the
        # whole cycle into one dump — that dump is what looked "preset".
        yield ": connected\n\n"
        await asyncio.sleep(0)
        iterator = iter(events)
        while True:
            event = await asyncio.to_thread(next, iterator, _STREAM_DONE)
            if event is _STREAM_DONE:
                break
            name = event.get("event", "message")
            yield f"event: {name}\ndata: {json.dumps(event)}\n\n"
            yield ": ping\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/chat")
def chat(body: ChatIn) -> StreamingResponse:
    """Live cockpit entry: parse the user's words, then run the loop or answer from the graph."""
    global LAST_REQUEST
    parsed = parse_message(body.message, STORE, LAST_REQUEST)
    if parsed["kind"] == "ask":
        return _sse(_with_intent(parsed, answer_question(STORE, body.message, LAST_REQUEST)))
    request = dict(parsed["request"])
    LAST_REQUEST = {**request, "gated": body.gated}
    return _sse(_with_intent(parsed, ORCH.run(request, gated=body.gated)))


def _with_intent(parsed: dict[str, Any], events):
    yield {
        "event": "intent",
        "kind": parsed["kind"],
        "request": parsed.get("request"),
        "message": parsed.get("message"),
    }
    yield from events


@app.post("/run-procurement-cycle")
def run_procurement_cycle(payload: ProcurementRequest) -> StreamingResponse:
    """Synchronous loop over ICM folders, streamed as SSE to the cockpit."""
    global LAST_REQUEST
    data = payload.model_dump()
    message = data.pop("message", None)
    if message:
        parsed = parse_message(message, STORE, LAST_REQUEST)
        if parsed["kind"] == "ask":
            return _sse(_with_intent(parsed, answer_question(STORE, message, LAST_REQUEST)))
        request = dict(parsed["request"])
        gated = payload.gated
    else:
        request = data
        gated = request.pop("gated")
        request.pop("message", None)
    LAST_REQUEST = {**request, "gated": gated}
    return _sse(ORCH.run(request, gated=gated))


@app.post("/continue-cycle")
def continue_cycle(body: ResumeRequest) -> StreamingResponse:
    request = dict(LAST_REQUEST)
    request.pop("gated", None)
    request.pop("message", None)
    return _sse(ORCH.run_from(request, body.from_stage, gated=True))


@app.get("/state")
def state() -> dict[str, Any]:
    return {
        "health": health(),
        "graph": cockpit_graph(STORE.snapshot()),
        "files": read_pipeline_files(),
        "last_request": LAST_REQUEST,
        "workspace": str(WORKSPACE),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
