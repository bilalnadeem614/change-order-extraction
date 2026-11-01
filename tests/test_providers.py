"""Provider-layer tests that need no network: the Groq client's setup and its retry behaviour."""
import json
from types import SimpleNamespace

import openai
import pytest

from co_extract.llm import GroqClient, LLMError, OpenAICompatClient

SCHEMA = {"type": "object", "properties": {}}


def _bad_request(msg: str) -> openai.BadRequestError:
    # a minimal stand-in for the HTTP response, so the test does not depend on which HTTP
    # library the installed openai SDK uses (httpx or a fork of it)
    fake = SimpleNamespace(status_code=400, headers={}, request=SimpleNamespace())
    return openai.BadRequestError(msg, response=fake, body=None)


def _ok_response(args: dict):
    call = SimpleNamespace(function=SimpleNamespace(arguments=json.dumps(args)))
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason="tool_calls",
                                                    message=SimpleNamespace(tool_calls=[call]))])


def test_groq_needs_a_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GROQ_API_KEY"):
        GroqClient()


def test_groq_points_at_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_dummy")
    monkeypatch.delenv("CO_MODEL", raising=False)
    c = GroqClient()
    assert "api.groq.com" in str(c.client.base_url)
    assert c.name == "groq:" + GroqClient.DEFAULT_MODEL
    assert GroqClient(model="llama-3.3-70b-versatile").name == "groq:llama-3.3-70b-versatile"


def _client(monkeypatch, create):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_dummy")
    c = GroqClient()
    c.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return c


def test_malformed_tool_call_is_retried(monkeypatch):
    calls = {"n": 0}

    def create(**kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _bad_request("Failed to call a function. tool_use_failed")
        assert kw["tool_choice"]["function"]["name"] == "record_change_order"
        return _ok_response({"ok": True})

    assert _client(monkeypatch, create).extract("sys", "doc", SCHEMA) == {"ok": True}
    assert calls["n"] == 3


def test_persistent_malformed_tool_calls_give_a_clear_error(monkeypatch):
    def create(**kw):
        raise _bad_request("tool_use_failed")

    with pytest.raises(LLMError, match="malformed"):
        _client(monkeypatch, create).extract("sys", "doc", SCHEMA)


def test_other_bad_requests_are_not_retried(monkeypatch):
    calls = {"n": 0}

    def create(**kw):
        calls["n"] += 1
        raise _bad_request("model does not exist")

    with pytest.raises(LLMError, match="rejected"):
        _client(monkeypatch, create).extract("sys", "doc", SCHEMA)
    assert calls["n"] == 1


def test_openai_compat_requires_a_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.delenv("CO_MODEL", raising=False)
    with pytest.raises(LLMError, match="CO_MODEL"):
        OpenAICompatClient()
