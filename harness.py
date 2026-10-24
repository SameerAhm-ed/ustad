"""Mill Floor Copilot harness: Gemma extracts -> tools gather evidence -> Gemma diagnoses -> case logged."""
import json
import re
from datetime import date

import llm
from data import HISTORY, MACHINES, MANUAL
from ml import risk

EXTRACT = """You read maintenance notes written by textile mill technicians (Roman Urdu, Urdu or English).
Known machine ids: {ids}
Note: {note}
Return JSON only: {{"machine_id": one known id or null if the note does not name one, "symptom": short English summary,
"urgency": "low"|"medium"|"high", "language": "Roman Urdu"|"Urdu"|"English" (the note's language)}}"""

DIAGNOSE = """You are a senior maintenance engineer in a textile mill. Diagnose using ONLY the evidence below.
Technician note: {note}
Machine: {machine_id} ({name})
Live sensors: {sensors}
ML failure model: risk {risk:.0%}, most likely fault {fault}
Maintenance history: {history}
This fault has already occurred {repeat} times on this machine.
Manual: {manual}
If it repeated 2+ times, say the earlier fix is not working and recommend the permanent fix from the manual.
Return JSON only: {{"cause": str, "steps": [3-5 short steps], "parts": [part numbers from the manual, or []],
"priority": "low"|"medium"|"high"|"stop machine now", "repeat_pattern": true|false,
"reply": a short message to the technician in {language}}}"""


def parse_json(text):
    """Pull the first {...} object out of a model reply (handles ``` fences and chatter)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"no JSON in reply: {text[:200]}")
    return json.loads(text[start:end + 1])


def _ask_json(prompt):
    try:
        return parse_json(llm.ask(prompt))
    except ValueError:  # one repair try, then let it raise
        return parse_json(llm.ask(prompt + "\nReturn ONLY the JSON object, nothing else."))


def find_machine(text):
    m = re.search(r"(loom|spinning)[\s_-]*(\d+)", text, re.I)
    mid = m and f"{m[1].lower()}-{int(m[2]):02d}"
    return mid if mid in MACHINES else None


def _as_list(x):
    return [str(v) for v in ([x] if isinstance(x, str) else list(x or []))]


def gather(machine_id, symptom=""):
    sensors = MACHINES[machine_id]["sensors"]
    ml_risk, ml_fault = risk(sensors)
    if ml_risk < 0.2:
        ml_fault = "none"  # healthy machine: don't feed Gemma a fault to invent
    history = HISTORY.get(machine_id, [])
    manual = {f: t for f, t in MANUAL.items() if f == ml_fault or f.split("_")[0] in symptom.lower()}
    return {"sensors": sensors, "history": history, "manual": manual, "ml_risk": ml_risk, "ml_fault": ml_fault,
            "repeat_count": sum(h["fault"] == ml_fault for h in history)}


def log_case(machine_id, fault, action):
    HISTORY.setdefault(machine_id, []).append({"date": date.today().isoformat(), "fault": fault, "action": action})


def _fail(out, e):
    """Record why Gemma failed: the plain-words reason for GemmaError, raw text otherwise."""
    gemma = isinstance(e, llm.GemmaError)
    out["error"] = str(e) if gemma else f"Gemma unavailable: {e}"
    out["error_kind"] = e.kind if gemma else "unknown"


def run(note, on_step=lambda name, data: None):
    """on_step(name, data) fires as each step finishes, so the UI can show progress live."""
    out = {"extracted": None, "evidence": None, "diagnosis": None, "error": None, "error_kind": None,
           "needs_machine": False}
    try:
        ex = _ask_json(EXTRACT.format(ids=", ".join(MACHINES), note=note))
    except Exception as e:  # Gemma down: fall back to regex so evidence still shows
        _fail(out, e)
        ex = {"machine_id": None, "symptom": note, "urgency": "unknown", "language": "English",
              "gemma_error": out["error"]}
    if ex.get("machine_id") not in MACHINES:
        ex["machine_id"] = find_machine(note)
    out["extracted"] = ex
    on_step("understood", ex)
    if not ex["machine_id"]:
        out["needs_machine"] = True  # never guess the machine
        return out

    mid = ex["machine_id"]
    ev = out["evidence"] = gather(mid, str(ex.get("symptom") or note))
    on_step("evidence", ev)
    if out["error"]:
        return out
    on_step("diagnosing", None)
    try:
        dx = _ask_json(DIAGNOSE.format(
            note=note, machine_id=mid, name=MACHINES[mid]["name"], sensors=ev["sensors"], risk=ev["ml_risk"],
            fault=ev["ml_fault"], history=ev["history"] or "none", repeat=ev["repeat_count"],
            manual=" ".join(ev["manual"].values()) or "no matching section", language=ex.get("language", "English")))
    except Exception as e:
        _fail(out, e)
        return out
    dx["steps"], dx["parts"] = _as_list(dx.get("steps")), _as_list(dx.get("parts"))
    out["diagnosis"] = dx
    on_step("diagnosis", dx)
    if ev["ml_risk"] >= 0.5:  # only log real faults, so healthy machines never build a fake repeat history
        log_case(mid, ev["ml_fault"], (dx["steps"] or ["see diagnosis"])[0])
    return out
