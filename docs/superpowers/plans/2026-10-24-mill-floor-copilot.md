# Mill Floor Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A technician pastes a messy (Roman Urdu) note; Gemma extracts it, our tools gather evidence, Gemma diagnoses, the case is logged and repeat faults are flagged.

**Architecture:** `harness.py` runs a fixed 4-step loop (extract, gather, diagnose, remember). Tools are plain Python over simulated data in `data.py`; the existing scikit-learn model is one tool (`ml.py`). `llm.ask(prompt) -> str` is the only model call. `app.py` is UI only.

**Tech Stack:** Python 3, Streamlit, scikit-learn, requests, `llm.py` (Gemma 4 31B via OpenRouter then Google AI Studio).

**Spec:** `docs/superpowers/specs/2026-10-24-mill-floor-copilot-design.md`

## Global Constraints
- Model: `gemma-4-31b-it` only, via `llm.ask`. No native function calling.
- Keys only from env vars `OPENROUTER_API_KEY` / `GEMINI_API_KEY`; never written to files.
- Simulated data, said so in UI and README. Deadline 3:15 PM, so no persistence beyond the session, no auth, no photos.
- Not a git repo: skip commit steps.

## Review Focus
- Gemma returns JSON wrapped in ```json fences or prose: parser must still extract it.
- Note names an unknown machine or none: return `needs_machine` and a question, never guess.
- Gemma unavailable: result still carries gathered evidence and `error`.
- Note in Urdu script / English / Roman Urdu: reply language follows the note.
- Same fault logged twice already: `repeat_count >= 2` is passed to Gemma and shown.

---

### Task 1: Data and ML tool

**Files:**
- Create: `data.py`, `ml.py`
- Modify: `app.py` (remove `label`, `train`, `MANUAL`, `FEATURES`; import from `ml`/`data`) in Task 3

**Interfaces:**
- Produces (`data.py`): `FEATURES: list[str]`; `MACHINES: dict[str, dict]` with keys `name`, `sensors` (dict over FEATURES); `HISTORY: dict[str, list[dict]]` entries `{"date": str, "fault": str, "action": str}`; `MANUAL: dict[str, str]` keyed by fault (`bearing_wear`, `motor_overheat`, `tension_fault`, `overload`).
- Produces (`ml.py`): `risk(readings: dict) -> tuple[float, str]` = (failure risk 0..1, most likely fault name).

- [ ] **Step 1: Test in `check.py`:** `assert risk(MACHINES["loom-14"]["sensors"])[1] == "bearing_wear"` and `risk(MACHINES["loom-02"]["sensors"])[0] < 0.2`. Spec value: 8 machines: `loom-01`..`loom-05`, `loom-14`, `spinning-01`, `spinning-02` (`loom-02` must be healthy).
- [ ] **Step 2:** Run `python check.py`; expected FAIL (ImportError).
- [ ] **Step 3:** Create `data.py` (loom-14: vibration 8.2, hours_since_service 1150, other sensors normal; `HISTORY["loom-14"]` has two `bearing_wear` entries, 6 and 3 weeks ago, action "lubricated"; other machines healthy with at most one unrelated entry). Create `ml.py` by moving `label`/`train` from `app.py` (use `functools.cache` instead of `st.cache_resource`).
- [ ] **Step 4:** Run `python check.py`; expected PASS.

### Task 2: Harness

**Files:**
- Create: `harness.py`
- Test: `check.py`

**Interfaces:**
- Consumes: `llm.ask`, `data.*`, `ml.risk`.
- Produces: `run(note: str) -> dict` with keys `extracted` (dict: `machine_id|None`, `symptom`, `urgency`, `language`), `evidence` (dict: `sensors`, `history`, `manual`, `ml_risk`, `ml_fault`, `repeat_count`), `diagnosis` (dict: `cause`, `steps: list[str]`, `parts: list[str]`, `priority`, `repeat_pattern: bool`, `reply: str`, or `None`), `error: str|None`, `needs_machine: bool`. Also `parse_json(text: str) -> dict` (raises `ValueError`) and `log_case(machine_id, fault, action)`.

- [ ] **Step 1: Tests (offline, patch `harness.llm.ask`):**
  `parse_json('```json\n{"a":1}\n```') == {"a": 1}`; `parse_json('Sure! {"a":1} done') == {"a":1}`; with `ask` patched to return an extraction with `machine_id: null`, `run("kuch kharab hai")["needs_machine"] is True` and `diagnosis is None`; with `ask` patched to raise, `run(note_for_loom_14)["error"]` is set and `evidence["repeat_count"] == 2`.
- [ ] **Step 2:** Run `python check.py`; expected FAIL.
- [ ] **Step 3:** Implement. Extraction prompt lists known machine ids and asks for JSON only. `evidence["manual"]` = `MANUAL[ml_fault]` plus any MANUAL entry whose fault name appears in the extracted symptom. `repeat_count` = number of `HISTORY[machine_id]` entries whose `fault == ml_fault`. Diagnose prompt includes note, evidence, `repeat_count`, and "reply in the note's language; return JSON only with keys cause, steps, parts, priority, repeat_pattern, reply". On bad JSON retry once with "return only JSON"; second failure sets `error`. `log_case` appends to `HISTORY` (called at end of successful `run`).
- [ ] **Step 4:** Run `python check.py`; expected PASS.
- [ ] **Step 5 (live, needs key):** `python check.py live` runs `run("loom-14 se ajeeb awaaz aa rahi hai, dhaaga toot raha hai")`; expected `diagnosis["repeat_pattern"] is True` and `needs_machine is False`.

### Task 3: Streamlit UI

**Files:**
- Modify: `app.py` (rewrite), `README.md`, `requirements.txt` (unchanged)

**Interfaces:**
- Consumes: `harness.run(note) -> dict` (keys above).

- [ ] **Step 1:** Rewrite `app.py`: text area for the note; three example-note buttons (Roman Urdu loom-14 note, English note for spinning-01, vague note with no machine); on submit call `harness.run`; show four steps as `st.status` rows (Understood / Evidence / Diagnosis / Logged) with the extracted JSON and evidence in expanders; result card with cause, numbered steps, parts, priority badge, `reply`; red banner when `repeat_pattern`; download button for a text work order; if `needs_machine` ask which machine; if `error` show evidence only.
- [ ] **Step 2:** Verify with `streamlit.testing.v1.AppTest`: no exception on first load; clicking the vague-note example shows the machine question (patch `harness.llm.ask` to return a null-machine extraction).
- [ ] **Step 3:** Manual run `python -m streamlit run app.py` with keys set; paste the loom-14 note; confirm repeat banner shows.
- [ ] **Step 4:** Update README (Mill Floor Copilot, Gemma 4 named as doing extraction, diagnosis and pattern flagging, data simulated, MIT).
