"""Provider-agnostic LLM layer for schema-constrained extraction.

Every client implements one method, ``extract(system, document, schema, temperature) -> dict``,
which forces the model to answer by calling a single tool whose input schema is our Pydantic
schema. That gives structured output on any provider that supports tool calling.

Clients
  AnthropicClient     ANTHROPIC_API_KEY; model via CO_MODEL (default claude-sonnet-5-5)
  OpenAICompatClient  OPENAI_API_KEY (+ OPENAI_BASE_URL for OpenRouter/Groq/Gemini/...);
                      model via CO_MODEL (required)
  MockClient          replays a gold file. PLUMBING TESTS ONLY - never use it to measure accuracy.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from dotenv import load_dotenv

load_dotenv()  # .env in cwd or parents; real env vars win

TOOL_NAME = "record_change_order"
TOOL_DESC = "Record the structured data extracted from the change-order document."


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    name: str

    def extract(self, system: str, document: str, schema: dict, temperature: float = 0.0) -> dict: ...


# --------------------------------------------------------------------------- #
def inline_refs(schema: dict) -> dict:
    """Resolve every $ref and drop $defs/titles.

    Pydantic emits $defs for each Extracted[...] type. Some providers handle $ref badly
    (Gemini's OpenAI-compatible endpoint, for one), so we hand out a flat schema.
    """
    defs = schema.get("$defs", {})

    def walk(node: Any, seen: tuple = ()) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                if name in seen:
                    raise LLMError(f"recursive schema at {name}")
                return walk(copy.deepcopy(defs[name]), seen + (name,))
            return {k: walk(v, seen) for k, v in node.items() if k not in ("$defs", "title")}
        if isinstance(node, list):
            return [walk(v, seen) for v in node]
        return node

    return walk(schema)


# --------------------------------------------------------------------------- #
class AnthropicClient:
    def __init__(self, model: Optional[str] = None, max_tokens: int = 8192):
        import anthropic
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()          # reads ANTHROPIC_API_KEY
        self.model = model or os.getenv("CO_MODEL", "claude-sonnet-5-5")
        self.max_tokens = max_tokens
        self.name = f"anthropic:{self.model}"

    def extract(self, system: str, document: str, schema: dict, temperature: float = 0.0) -> dict:
        kwargs: Dict[str, Any] = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            tools=[{"name": TOOL_NAME, "description": TOOL_DESC, "input_schema": inline_refs(schema)}],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": document}],
        )
        try:
            msg = self.client.messages.create(temperature=temperature, **kwargs)
        except self._anthropic.BadRequestError as e:
            if "temperature" not in str(e).lower():
                raise
            msg = self.client.messages.create(**kwargs)    # model does not accept temperature
        if msg.stop_reason == "max_tokens":
            raise LLMError("output truncated (max_tokens). Raise max_tokens for long documents.")
        for block in msg.content:
            if block.type == "tool_use":
                return block.input
        raise LLMError("model did not call the extraction tool")


class OpenAICompatClient:
    """Any OpenAI-compatible endpoint: OpenAI, OpenRouter, Together, Groq (see GroqClient), ...

    The SDK retries 429 / 5xx with backoff (max_retries=8), which matters on free tiers.
    Some open models occasionally emit a malformed tool call; the provider then answers
    400 "tool_use_failed". That is random, so we simply try again.
    """

    def __init__(self, model: Optional[str] = None, max_tokens: int = 8192, base_url: Optional[str] = None,
                 api_key: Optional[str] = None, label: str = "openai-compat"):
        import openai
        from openai import OpenAI
        self._openai = openai
        self.client = OpenAI(base_url=base_url, api_key=api_key, max_retries=8)   # None -> env vars
        self.model = model or os.getenv("CO_MODEL")
        if not self.model:
            raise LLMError("set CO_MODEL (or pass --model) for the OpenAI-compatible client")
        self.max_tokens = max_tokens
        self.extra_body: dict = {}
        self.name = f"{label}:{self.model}"
        self.debug_dir: Optional[Path] = None      # where failed_generation bodies are saved, if set

    def _call(self, system: str, document: str, schema: dict, temperature: float):
        last: Optional[Exception] = None
        for _ in range(3):
            try:
                return self.client.chat.completions.create(
                    model=self.model,
                    temperature=temperature,
                    max_tokens=self.max_tokens,
                    extra_body=self.extra_body,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": document}],
                    tools=[{"type": "function", "function": {
                        "name": TOOL_NAME, "description": TOOL_DESC, "parameters": inline_refs(schema)}}],
                    tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
                )
            except self._openai.BadRequestError as e:
                msg = str(e).lower()
                if any(k in msg for k in ("tool_use_failed", "failed_generation", "failed to parse tool call")):
                    last = e
                    self._save_failed_generation(e)
                    continue
                raise LLMError(f"request rejected by the provider: {e}") from e
            except self._openai.RateLimitError as e:
                raise LLMError(f"rate limited even after retries (try --passes 1, a smaller model, or wait): {e}") from e
        raise LLMError(f"the model kept producing malformed tool calls: {last}")

    def _save_failed_generation(self, e: Exception) -> None:
        """Keep what the model actually emitted: cut off at the end (budget) or garbled mid-way (model)?"""
        body = getattr(e, "body", None)
        err = body.get("error", body) if isinstance(body, dict) else {}
        gen = err.get("failed_generation") if isinstance(err, dict) else None
        if not gen or self.debug_dir is None:
            return
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        n = len(list(self.debug_dir.glob("failed_generation_*.txt"))) + 1
        (self.debug_dir / f"failed_generation_{n}.txt").write_text(gen)

    def extract(self, system: str, document: str, schema: dict, temperature: float = 0.0) -> dict:
        resp = self._call(system, document, schema, temperature)
        choice = resp.choices[0]
        if choice.finish_reason == "length":
            raise LLMError("output truncated (max_tokens). Raise max_tokens for long documents.")
        calls = choice.message.tool_calls or []
        if not calls:
            raise LLMError("model did not call the extraction tool")
        try:
            return json.loads(calls[0].function.arguments)
        except json.JSONDecodeError as e:
            raise LLMError(f"tool arguments were not valid JSON: {e}") from e


class GroqClient(OpenAICompatClient):
    """Groq's OpenAI-compatible API. Key: GROQ_API_KEY. Model: --model, CO_MODEL, or the default."""

    DEFAULT_MODEL = "openai/gpt-oss-120b"

    def __init__(self, model: Optional[str] = None, max_tokens: int = 4500):
        # Groq free tier: 8k tokens/min per request, and max_tokens counts toward it.
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise LLMError("GROQ_API_KEY is not set")
        super().__init__(model=model or os.getenv("CO_MODEL") or self.DEFAULT_MODEL, max_tokens=max_tokens,
                         base_url="https://api.groq.com/openai/v1", api_key=key, label="groq")
        if "gpt-oss" in self.model:
            self.extra_body = {"reasoning_effort": "low"}   # reasoning tokens eat the max_tokens budget


# --------------------------------------------------------------------------- #
class MockClient:
    """Replays a gold file as if it were a model answer, with evidence copied from the text.

    Exists to test ingest -> parse -> map -> validate plumbing without an API key.
    It reads the answer key, so any accuracy number from it would be meaningless.
    """

    def __init__(self, gold_path: str | Path):
        self.gold = json.loads(Path(gold_path).read_text())
        self.name = "mock(gold replay - plumbing only)"

    @staticmethod
    def _candidates(field: str, v: Any) -> list:
        import datetime as dt
        if field == "co_date" and v is not None:
            d = dt.date.fromisoformat(str(v))
            return [d.isoformat(), f"{d.strftime('%B')} {d.day}, {d.year}", f"{d.month:02d}/{d.day:02d}/{d.year}",
                    f"{d.day:02d}-{d.strftime('%b')}-{d.year}", f"{d.day} {d.strftime('%B')} {d.year}"]
        if field == "currency":
            return {"USD": ["$"], "EUR": ["€"]}.get(str(v), [str(v)])
        if isinstance(v, str):
            return [v]
        if isinstance(v, bool):
            return ["/s/"] if v else ["____"]
        if isinstance(v, (int, float)) and field == "schedule_impact_days":
            return [f"{v} calendar days", "No change"]
        if isinstance(v, (int, float)):
            us = f"{abs(v):,.2f}"
            eu = us.replace(",", "\0").replace(".", ",").replace("\0", ".")
            return [us, eu] if field != "markup_percent" else [f"({v:g}%)", f"{v:g}%"]
        return []

    def _evidence(self, field: str, v: Any, document: str) -> Optional[str]:
        if v is None:
            return None
        cands = self._candidates(field, v)
        for line in document.splitlines():
            if any(c in line for c in cands):
                return line.strip()
        # a value that wraps across lines: a real model quotes the value itself
        if isinstance(v, str) and all(t in document for t in v.split()):
            return v
        return None

    def extract(self, system: str, document: str, schema: dict, temperature: float = 0.0) -> dict:
        g = self.gold
        out: Dict[str, Any] = {}
        for f, v in g.items():
            if f == "line_items":
                out[f] = [dict(li, evidence=self._evidence("amount", li["amount"], document)) for li in v]
            else:
                out[f] = {"value": v, "evidence": self._evidence(f, v, document)}
        return out
