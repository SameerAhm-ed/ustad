"""Self-check. `python check.py` runs offline tests; `python check.py live` also calls Gemma."""
import sys

from data import MACHINES
from ml import risk


def test_ml():
    assert risk(MACHINES["loom-14"]["sensors"])[1] == "bearing_wear"
    assert risk(MACHINES["loom-02"]["sensors"])[0] < 0.2
    assert len(MACHINES) == 8


LOOM14_NOTE = "loom-14 se ajeeb awaaz aa rahi hai, dhaaga toot raha hai"


def _fake_ask(*replies):
    it = iter(replies)
    def ask(prompt):
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r
    return ask


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
