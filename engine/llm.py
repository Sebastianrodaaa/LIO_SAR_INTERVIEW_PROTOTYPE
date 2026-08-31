"""Single structured-LLM adapter.

One call per stage. Never a tool loop, never a swarm. Instructor (or the
offline mock) must return an instance of the stage's Pydantic schema.
"""

from __future__ import annotations

import json
import os
from typing import Any, TypeVar

from pydantic import BaseModel

from engine.mock_completions import MOCK_BUILDERS
from engine.schemas import STAGE_SCHEMAS

T = TypeVar("T", bound=BaseModel)


class StructuredLLM:
    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "mock").lower()
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self._client = None
        if self.provider in {"openai", "anthropic"}:
            self._client = self._build_instructor()

    def _build_instructor(self):
        try:
            import instructor
        except ImportError as exc:
            raise RuntimeError("instructor is required for live LLM mode") from exc

        if self.provider == "anthropic":
            from anthropic import Anthropic

            return instructor.from_anthropic(Anthropic())
        from openai import OpenAI

        return instructor.from_openai(OpenAI())

    def complete(
        self,
        stage: str,
        system: str,
        user: str,
        request: dict[str, Any],
        retrieval: dict[str, Any],
    ) -> BaseModel:
        schema = STAGE_SCHEMAS[stage]
        if self.provider == "mock" or self._client is None:
            builder = MOCK_BUILDERS[stage]
            obj = builder(request, retrieval)
            return schema.model_validate(obj.model_dump())

        result = self._client.chat.completions.create(
            model=self.model,
            response_model=schema,
            max_retries=2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return result


def render_user_prompt(
    stage: str,
    contract: str,
    previous_output: str,
    retrieval: dict[str, Any],
    request: dict[str, Any],
    voice: str,
) -> str:
    """Assemble the *only* user message this stage will see.

    Isolation is the product: previous stages appear as their output.md, not
    as their prompts, retrievals, or hidden chain-of-thought.
    """
    retrieval_json = json.dumps(_strip_heavy(retrieval), indent=2)
    payload = json.dumps(request, indent=2)
    previous = previous_output.strip() or "(no previous stage output)"
    return f"""# Stage {stage}

## Contract
{contract}

## Voice
{voice}

## GraphRAG retrieval (this stage only)
{retrieval_json}

## Request payload
{payload}

## Previous stage output.md
{previous}

Return only data that validates against the stage Pydantic schema.
"""


def _strip_heavy(retrieval: dict[str, Any]) -> dict[str, Any]:
    """Drop display-only keys so the model does not see cockpit chrome."""
    skip = {"highlight"}
    return {k: v for k, v in retrieval.items() if k not in skip}
