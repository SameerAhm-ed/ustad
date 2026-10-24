# Mill Floor Copilot: Design

Hacktoberfest Karachi 2026, Harness track. Solo, deadline 3:15 PM. Model: `gemma-4-31b-it` via Gemini API (`GEMINI_API_KEY`).

## Problem
A textile mill technician notices a problem ("loom 14 se ajeeb awaaz aa rahi hai, dhaaga toot raha hai"), then loses time finding the cause, the fix and whether it has happened before. Notes are messy, often Roman Urdu, and history is not checked.

## Success
Live demo: paste a messy note, watch Gemma extract it, gather evidence with tools, diagnose, produce a work order, and flag a repeating fault. Gemma visibly does the work. A mill person recognises the problem.

## Flow (the harness, `harness.py`)
1. **Understand (Gemma call 1):** note -> JSON `{machine_id, symptom, urgency, language}`.
2. **Gather evidence (plain Python tools, no model function-calling):**
   - `get_sensors(machine_id)`: latest simulated readings.
   - `get_history(machine_id)`: past maintenance entries.
   - `search_manual(symptom)`: keyword match over manual excerpts.
   - `ml_risk(readings)`: existing scikit-learn model, returns risk and likely fault.
3. **Diagnose (Gemma call 2):** note + evidence -> JSON `{cause, steps[], parts[], priority, repeat_pattern, reply}`, `reply` in the technician's language.
4. **Remember:** append a log entry to the history. If the same fault already appears 2+ times for that machine, Gemma is told and sets `repeat_pattern`.

## Units
- `harness.py`: `run(note) -> dict`. Tools, prompts, JSON parsing. No UI imports.
- `data.py`: 8 simulated machines, sensors, history (one machine with a repeating bearing fault), manual excerpts.
- `app.py`: Streamlit UI only. Note box, example-note buttons, step-by-step trace, result card, work-order download.
- `check.py`: runnable self-check with one Roman Urdu note (needs the key).

## Errors
- Gemma 503: retry 2s/4s/8s, then raise.
- Bad JSON from Gemma: one repair retry ("return only JSON"), then show raw text.
- Unknown machine in note: ask the technician for the machine number; do not guess.
- No key or Gemma down: UI shows gathered evidence only and says Gemma is unavailable.

## Out of scope
Photos, ERP chat, real sensors, auth, persistence beyond the session, Gemma native function calling.

## Honesty
Machines, sensors, history and manuals are simulated for the demo; say so in the demo and README.
