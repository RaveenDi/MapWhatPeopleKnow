"""Replay of SANITIZED recordings of the first real Meta Model API calls (2026-10-30, synthetic inputs only).

tests/fixtures/live/*.json are {request, response} pairs: audio and images are replaced by their sha256, no auth header,
request id or account id was stored. They pin the *verified* wire shapes: POST /asr/transcribe (multipart), chat
completions with strict json_schema and image input, tools + tool_choice "auto". `httpx.post` is monkeypatched, so
nothing here touches the network. Map-specific schemas were not sent live: only their strict-mode compliance is checked."""
import json
from pathlib import Path

import httpx
import pytest

from app import providers
from app.providers import MetaReason, MetaSpeech
from app.resolver import TOOLS
from app.telemetry import ProviderFailure, Session

LIVE = Path(__file__).parent / "fixtures" / "live"


def fx(name):
    return json.loads((LIVE / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def wire(monkeypatch, tmp_path):
    """Serve queued responses through httpx.post; keep every outgoing call in `calls`."""
    monkeypatch.setenv("MODEL_PROVIDER", "meta")
    monkeypatch.setenv("MODEL_API_KEY", "test-only-placeholder")
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path))
    monkeypatch.delenv("META_REASONING_EFFORT", raising=False)
    monkeypatch.setattr("app.transport.time.sleep", lambda _: None)
    calls, queue = [], []

    def post(url, **kw):
        calls.append((url, kw))
        return httpx.Response(200, json=queue.pop(0), request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx, "post", post)
    return calls, queue


def with_content(name, content):
    """The recorded response envelope (ids, usage, finish_reason) with the message text swapped."""
    reply = json.loads(json.dumps(fx(name)["response"]))
    reply["choices"][0]["message"]["content"] = content
    return reply


def strict_ok(schema):
    """strict json_schema (verified): additionalProperties:false and every property required, on every object."""
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False and sorted(schema.get("required", [])) == sorted(schema["properties"])
        for v in schema.values():
            strict_ok(v)
    elif isinstance(schema, list):
        for v in schema:
            strict_ok(v)


# ---- speech -----------------------------------------------------------------------------------------------------
def test_recorded_transcription_replays_and_the_multipart_request_matches_the_live_one(wire):
    calls, queue = wire
    rec = fx("asr-transcribe")
    queue.append(rec["response"])
    assert MetaSpeech().transcribe(b"RIFF-not-decoded", "demo-transcript.wav") == rec["response"]["transcript"]
    url, kw = calls[0]
    assert url == "https://api.meta.ai/v1/asr/transcribe" and kw["headers"]["Authorization"].startswith("Bearer ")
    assert list(kw["params"]) == list(rec["request"]["query"]) == ["sessionId"] and kw["params"]["sessionId"].startswith("mwpk-")
    assert sorted(kw["files"]) == sorted(rec["request_files"] if "request_files" in rec else ["audio", "request"])
    part = kw["files"]["request"]
    assert part[0] is None and part[2] == "application/json" and json.loads(part[1]) == rec["request"]["multipart"]["request"]
    assert kw["files"]["audio"] == ("demo-transcript.wav", b"RIFF-not-decoded", "audio/wav")
    assert rec["response"]["audioDurationMs"] == 11760 and rec["response"]["turns"] == []


def test_transcription_reply_without_a_transcript_is_a_provider_failure_after_one_repair(wire):
    calls, queue = wire
    queue.extend([{"sessionId": "x", "text": "old field name"}, {"sessionId": "x"}])
    with pytest.raises(ProviderFailure):
        MetaSpeech().transcribe(b"RIFF", "a.wav")
    assert len(calls) == 2


def test_only_wav_is_sent_because_only_wav_was_verified(wire):
    calls, _ = wire
    with pytest.raises(ProviderFailure) as e:
        MetaSpeech().transcribe(b"ID3", "voice.mp3")
    assert "WAV" in str(e.value) and not calls


def test_speech_is_costed_per_audio_hour_not_per_token():
    reply = fx("asr-transcribe")["response"]
    trace = []
    session = Session(trace, 1)
    session.invoke("muse-voice-transcribe-1.0", "transcribe", lambda: reply)
    assert trace[0].estimated_cost_usd == pytest.approx(11760 / 3_600_000 * 0.18)
    assert session.totals()["usage_complete"] is True and session.totals()["cost_complete"] is True


# ---- chat, strict json_schema, vision ---------------------------------------------------------------------------
def test_chat_body_has_only_verified_parameters(wire, monkeypatch):
    calls, queue = wire
    monkeypatch.setenv("META_REASONING_EFFORT", "minimal")
    rec = fx("chat-basic")
    assert MetaReason()._body(rec["request"]["messages"]) == rec["request"] | {"max_completion_tokens": 2048}
    assert rec["response"]["usage"]["prompt_tokens"] == 15 and rec["response"]["usage"]["completion_tokens"] == 16


def test_extract_speech_sends_strict_schema_and_parses_the_recorded_envelope(wire):
    calls, queue = wire
    rows = [{"entity": "old well", "predicate": "boundary_corner", "value": "1", "wording": "the old well"}]
    queue.append(with_content("chat-strict-json-schema-vision", json.dumps({"observations": rows})))
    assert MetaReason().extract_speech("bounded by the old well", {}) == rows
    body = calls[0][1]["json"]
    sent = fx("chat-strict-json-schema-vision")["request"]
    assert set(body) == {"model", "max_completion_tokens", "messages", "response_format"} and body["model"] == "muse-spark-1.3"
    assert body["response_format"]["type"] == sent["response_format"]["type"] == "json_schema"
    assert set(body["response_format"]["json_schema"]) == set(sent["response_format"]["json_schema"]) == {"name", "strict", "schema"}
    assert body["response_format"]["json_schema"]["strict"] is True
    strict_ok(body["response_format"]["json_schema"]["schema"])
    assert "max_tokens" not in body and "temperature" not in body


def test_sketch_image_part_has_the_recorded_vision_layout(wire):
    calls, queue = wire
    queue.append(with_content("chat-strict-json-schema-vision", json.dumps({"observations": []})))
    MetaReason().extract_sketch([{"label": "well"}], {}, b"\x89PNG-not-decoded")
    user = calls[0][1]["json"]["messages"][1]["content"]
    recorded = fx("chat-strict-json-schema-vision")["request"]["messages"][1]["content"]
    assert [p["type"] for p in user] == [p["type"] for p in recorded] == ["text", "image_url"]
    assert user[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_clarify_schema_is_strict_compliant(wire):
    calls, queue = wire
    queue.append(with_content("chat-strict-json-schema-vision", json.dumps({"questions": [{"id": "c1", "question": "Which?"}]})))
    assert MetaReason().clarify([{"id": "c1"}]) == {"c1": "Which?"}
    strict_ok(calls[0][1]["json"]["response_format"]["json_schema"]["schema"])


def test_truncated_reply_is_never_parsed_as_json(wire):
    calls, queue = wire
    for _ in range(2):
        reply = with_content("chat-strict-json-schema-vision", '{"observations": [')
        reply["choices"][0]["finish_reason"] = "length"
        queue.append(reply)
    with pytest.raises(ProviderFailure):
        MetaReason().extract_speech("x", {})
    assert len(calls) == 2  # one repair attempt, then a clear failure


def test_reasoning_effort_is_validated_and_opt_in(wire, monkeypatch):
    calls, queue = wire
    queue.append(with_content("chat-strict-json-schema-vision", json.dumps({"observations": []})))
    monkeypatch.setenv("META_REASONING_EFFORT", "low")
    MetaReason().extract_speech("x", {})
    assert calls[0][1]["json"]["reasoning_effort"] == "low"
    monkeypatch.setenv("META_REASONING_EFFORT", "none")  # Muse Spark rejects "none" (HTTP 400)
    with pytest.raises(ValueError):
        MetaReason()._body([])


# ---- tool calling -----------------------------------------------------------------------------------------------
def test_tool_turn_uses_auto_and_returns_the_recorded_parallel_tool_calls_untouched(wire):
    calls, queue = wire
    rec = fx("tools-turn-parallel-calls")
    queue.append(rec["response"])
    messages = rec["request"]["messages"]
    turn = MetaReason().resolve_turn(messages, TOOLS)
    body = calls[0][1]["json"]
    assert body["tool_choice"] == "auto" and rec["request"]["tool_choice"] == "auto"  # "required" is HTTP 400
    assert body["tools"] == TOOLS and all(set(t) == {"type", "function"} for t in body["tools"])
    assert body["messages"] == messages  # assistant tool_calls + {role: tool, tool_call_id, content} go back verbatim
    assert len(turn["tool_calls"]) == 5 and all(c["type"] == "function" and isinstance(c["function"]["arguments"], str) for c in turn["tool_calls"])
    assert [json.loads(c["function"]["arguments"]) for c in turn["tool_calls"]]  # arguments are a JSON string


def test_null_content_with_tool_calls_is_accepted(wire):
    calls, queue = wire
    queue.append(fx("tools-turn-null-content")["response"])
    turn = MetaReason().resolve_turn([{"role": "user", "content": "x"}], TOOLS)
    assert turn["content"] is None and len(turn["tool_calls"]) == 2


def test_prose_instead_of_tool_calls_gets_one_repair_then_fails(wire):
    calls, queue = wire
    queue.extend([fx("chat-basic")["response"]] * 2)
    with pytest.raises(ProviderFailure):
        MetaReason().resolve_turn([{"role": "user", "content": "x"}], TOOLS)
    assert len(calls) == 2


def test_module_exposes_no_stale_unverified_endpoints():
    assert not hasattr(providers, "BASE_URL") or providers.BASE_URL == "https://api.meta.ai/v1"
    assert "/audio/transcriptions" not in Path(providers.__file__).read_text(encoding="utf-8")
