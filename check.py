"""Self-check. `python check.py` runs offline tests; `python check.py live` also calls Gemma."""
import sys

import llm
from data import MACHINES
from ml import risk

REAL_ASK = llm.ask  # tests below swap llm.ask for fakes


def test_ml():
    assert risk(MACHINES["loom-14"]["sensors"])[1] == "bearing_wear"
    assert risk(MACHINES["loom-02"]["sensors"])[0] < 0.2
    assert len(MACHINES) == 8


LOOM14_NOTE = "loom-14 se ajeeb awaaz aa rahi hai, dhaaga toot raha hai"


def _fake_ask(*replies):
    it = iter(replies)
    def ask(prompt, image=None):
        ask.calls.append((prompt, image))
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r
    ask.calls = []
    return ask


def test_photo_goes_to_diagnosis_only():
    import harness
    img = (b"fake-jpeg", "image/jpeg")
    harness.llm.ask = fake = _fake_ask(
        '{"machine_id": "loom-14", "symptom": "noise", "urgency": "high", "language": "English"}',
        '{"cause": "c", "steps": ["a"], "parts": [], "priority": "high", "repeat_pattern": true, "reply": "r",'
        ' "photo_finding": "pitted bearing race"}')
    saved = list(harness.HISTORY["loom-14"])
    r = harness.run(LOOM14_NOTE, image=img)
    harness.HISTORY["loom-14"][:] = saved  # later tests expect exactly 2 past bearing faults
    assert fake.calls[0][1] is None and fake.calls[1][1] == img
    assert "photo" in fake.calls[1][0].lower()
    assert r["diagnosis"]["photo_finding"] == "pitted bearing race"


def test_openrouter_message_with_image():
    import llm
    assert llm._messages("hi") == [{"role": "user", "content": "hi"}]
    content = llm._messages("hi", (b"abc", "image/png"))[0]["content"]
    assert content[0] == {"type": "text", "text": "hi"}
    assert content[1]["image_url"]["url"] == "data:image/png;base64,YWJj"


def test_parse_json():
    from harness import parse_json
    assert parse_json('```json\n{"a":1}\n```') == {"a": 1}
    assert parse_json('Sure! {"a":1} done') == {"a": 1}
    try:
        parse_json("no json here")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_unknown_machine():
    import harness
    harness.llm.ask = _fake_ask('{"machine_id": null, "symptom": "kuch kharab", "urgency": "low", "language": "Roman Urdu"}')
    r = harness.run("kuch kharab hai")
    assert r["needs_machine"] is True and r["diagnosis"] is None


def test_gemma_down_keeps_evidence():
    import harness
    harness.llm.ask = _fake_ask(*[RuntimeError("503")] * 3)
    r = harness.run(LOOM14_NOTE)
    assert r["error"] and r["diagnosis"] is None
    assert r["evidence"]["repeat_count"] == 2 and r["evidence"]["ml_fault"] == "bearing_wear"


def test_full_run_logs_case():
    import harness
    from data import HISTORY
    before = len(HISTORY["loom-14"])
    harness.llm.ask = _fake_ask(
        '{"machine_id": "loom-14", "symptom": "noise, yarn breaking", "urgency": "high", "language": "Roman Urdu"}',
        'oops not json',
        '```json\n{"cause": "bearing", "steps": ["a"], "parts": ["BRG-6205"], "priority": "high", "repeat_pattern": true, "reply": "x"}\n```')
    r = harness.run(LOOM14_NOTE)
    assert r["error"] is None and r["diagnosis"]["repeat_pattern"] is True
    assert len(HISTORY["loom-14"]) == before + 1


def test_bad_list_fields_and_null_symptom():
    import harness
    harness.llm.ask = _fake_ask(
        '{"machine_id": "loom-14", "symptom": null, "urgency": "high", "language": "English"}',
        '{"cause": "c", "steps": null, "parts": "BRG-6205", "priority": "high", "repeat_pattern": true, "reply": "r"}')
    dx = harness.run(LOOM14_NOTE)["diagnosis"]
    assert dx["steps"] == [] and dx["parts"] == ["BRG-6205"]


def test_healthy_machine_not_blamed_or_logged():
    import harness
    from data import HISTORY
    harness.llm.ask = _fake_ask(
        '{"machine_id": "loom-02", "symptom": "routine check", "urgency": "low", "language": "English"}',
        '{"cause": "ok", "steps": ["none"], "parts": [], "priority": "low", "repeat_pattern": false, "reply": "ok"}')
    r = harness.run("loom-02 routine check")
    assert r["evidence"]["ml_fault"] == "none" and r["evidence"]["manual"] == {}
    assert "loom-02" not in HISTORY


def test_steps_reported_in_order():
    import harness
    harness.llm.ask = _fake_ask(
        '{"machine_id": "loom-14", "symptom": "noise", "urgency": "high", "language": "English"}',
        '{"cause": "c", "steps": ["a"], "parts": [], "priority": "high", "repeat_pattern": true, "reply": "r"}')
    seen = []
    harness.run(LOOM14_NOTE, on_step=lambda name, data: seen.append(name))
    assert seen == ["understood", "evidence", "diagnosing", "diagnosis"], seen


def _http_error(status, text=""):
    import requests
    resp = requests.models.Response()
    resp.status_code, resp._content = status, text.encode()
    return requests.HTTPError(f"{status} error", response=resp)


def test_explain_kinds():
    import requests
    from llm import explain
    assert explain(requests.ConnectionError("Max retries exceeded")).kind == "no_internet"
    assert explain(requests.ReadTimeout("read timed out")).kind == "timeout"
    assert explain(_http_error(402, '{"error": "Insufficient credits"}')).kind == "credits"
    assert explain(_http_error(429, "Rate limit exceeded: add 10 credits")).kind == "quota"  # code beats text
    assert explain(_http_error(401, "No auth credentials found")).kind == "auth"
    assert explain(_http_error(404, '{"error":{"message":"No allowed providers are available"}}')).kind == "provider"
    assert explain(_http_error(503, "Service Unavailable")).kind == "busy"
    e = explain(ValueError("weird thing"))
    assert e.kind == "unknown" and str(e) == e.message == "Gemma failed: weird thing"


def test_ask_no_keys_and_no_retry_on_auth():
    import os
    import llm
    saved = {k: os.environ.pop(k, None) for k in ("OPENROUTER_API_KEY", "GEMINI_API_KEY")}
    real = llm._openrouter
    try:
        try:
            REAL_ASK("x")
            raise AssertionError("expected GemmaError")
        except llm.GemmaError as e:
            assert e.kind == "auth"
        os.environ["OPENROUTER_API_KEY"] = "test"
        calls = []
        def bad_key(prompt, image=None):
            calls.append(1)
            raise _http_error(401, "invalid key")
        llm._openrouter = bad_key
        try:
            REAL_ASK("x")
            raise AssertionError("expected GemmaError")
        except llm.GemmaError as e:
            assert e.kind == "auth" and len(calls) == 1, (e.kind, calls)
    finally:
        llm._openrouter = real
        os.environ.pop("OPENROUTER_API_KEY", None)
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def test_harness_reports_friendly_reason():
    import harness
    from llm import GemmaError
    msg = "Gemma free-tier limit reached (too many requests or daily quota used). Wait a minute or use the other API key."
    harness.llm.ask = _fake_ask(GemmaError("quota", msg))
    r = harness.run(LOOM14_NOTE)
    assert r["error_kind"] == "quota" and r["error"] == msg, r["error"]
    assert r["extracted"]["urgency"] == "unknown" and r["evidence"]["ml_fault"] == "bearing_wear"


def live():
    import importlib
    import harness, llm
    importlib.reload(llm); importlib.reload(harness)  # undo fakes
    r = harness.run(LOOM14_NOTE)
    print(r["diagnosis"] or r["error"])
    assert r["needs_machine"] is False and r["diagnosis"]["repeat_pattern"] is True
    print("ok live")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    if sys.argv[1:] == ["live"]:
        globals()["live"]()
