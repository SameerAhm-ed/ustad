# 🧵 Ustad

**The senior technician on every shift.** (*Ustad* is Urdu for master craftsman.)

Ustad is a maintenance copilot for textile mills, built around **Gemma 4**. A floor technician writes what they see, in Roman Urdu, Urdu or English. Ustad works out which machine it is, checks that machine's sensors, history and manual, then gives the fix and warns when the same fault keeps coming back.

Built at **Hacktoberfest Karachi 2026 Hack Day** · **Harness track** · MIT licence.

---

## The problem
Every mill has one *ustad* who knows why loom 14 keeps breaking. When they are off shift, that knowledge is gone:
- Technicians write quick notes like *"loom-14 se ajeeb awaaz aa rahi hai, dhaaga toot raha hai"* and then lose time finding the cause.
- Nobody checks the machine's history, so the same quick fix (lubricate the bearing) is repeated until the machine breaks down and production stops.

## What Ustad does
1. Reads a messy note in the technician's own language, plus an optional **photo** of the worn part, broken yarn or fabric defect (Gemma 4 is multimodal).
2. Pulls the evidence for that machine: live sensors, maintenance history, manual section, failure-risk model.
3. Diagnoses: cause, repair steps, part numbers, priority.
4. **Flags repeat faults**: "bearing wear has happened 2 times already, the earlier fix isn't holding, replace the part."
5. Replies in the technician's language and logs the case, so the next repeat is caught.

## Screenshots
| Diagnose | Diagnosis (Gemma 4 output) | Mill floor |
|---|---|---|
| ![Diagnose tab](docs/screenshots/1-diagnose.jpg) | ![Diagnosis card](docs/screenshots/2-diagnosis.jpg) | ![Mill floor dashboard](docs/screenshots/3-mill-floor.jpg) |
| Technician types or picks a note. | Repeat-fault alert, STOP MACHINE NOW, part BRG-6205, reply in Roman Urdu. | Every machine's health; loom-14 shows 🔁 2 repeats. |

The diagnosis screenshot shows Gemma 4's answer from a live run. The venue network was dropping connections, so the app displayed it from its demo cache (it says so in a blue banner; see [Reliability](#reliability)).

---

## Harness and skill: what is what
The event has two tracks. **Ustad is a Harness-track project.** It also ships the same job as a skill, so it can be used without code.

| | What it is | Where |
|---|---|---|
| **Harness** (our entry) | Python code around Gemma 4 that runs a fixed 4-step loop, calls our own tools between the two Gemma calls, checks the output, and logs the result. | `harness.py`, `llm.py`, tools in `data.py` / `ml.py`, UI in `app.py` |
| **Skill** (bonus, no code) | The same procedure written as plain-English instructions. Paste it into Google AI Studio with Gemma 4 31B and it does the diagnosis by hand. | [`skill/SKILL.md`](skill/SKILL.md) |

### How the harness works
```mermaid
flowchart LR
    N[Technician note<br/>Roman Urdu / Urdu / English] --> G1[Gemma 4 call 1<br/>Understand]
    G1 -->|machine, symptom,<br/>urgency, language| T[Our tools<br/>sensors · history · manual · ML risk]
    T -->|evidence| G2[Gemma 4 call 2<br/>Diagnose]
    G2 -->|cause, steps, parts,<br/>priority, repeat flag, reply| L[Log case to<br/>machine history]
    L --> UI[Ustad UI]
```

| Step | Who does it | Detail |
|---|---|---|
| 1. Understand | **Gemma 4** | Extracts `machine_id`, `symptom`, `urgency`, `language` as JSON from the note. If no machine is named, Ustad asks instead of guessing. |
| 2. Gather evidence | **Our code** | `get sensors`, `get history`, `search manual`, and a scikit-learn failure-risk model (`ml.py`). Counts how often this fault has already happened. |
| 3. Diagnose | **Gemma 4** | Reasons over the note + evidence, and over the technician's **photo** if one is attached (`photo_finding`: what it sees in the image). Returns `cause`, `steps`, `parts`, `priority`, `repeat_pattern`, and a `reply` in the technician's language. Told to use only the evidence (no invented part numbers). |
| 4. Remember | **Our code** | Appends the case to the machine's history, so the next repeat is detected. |

**Gemma 4 does the language understanding and the diagnosis.** The code around it decides what evidence Gemma sees, validates its JSON (with one repair retry), and keeps the history.

Model, in order of preference (`llm.py`):
1. **Local Gemma 4 in Ollama** (`gemma4:e2b`, set `OLLAMA_MODEL`): runs on the laptop with no internet, no rate limits and no cost; machine data never leaves the PC. A full diagnosis takes about 14 s on a laptop, a photo about 20 s.
2. **Gemma 4 31B on OpenRouter** (`google/gemma-4-31b-it:free`).
3. **Gemma 4 31B on Google AI Studio** (Gemini API).

If one fails, Ustad falls through to the next and tells the user why.

### Reliability
- Retries on API errors, then falls back to the second provider.
- If Gemma is unreachable during a demo, the app shows the last good live result for the same note, clearly labelled as cached (`demo_cache.json`).
- If Gemma returns malformed JSON, it is asked once to return only JSON.
- Clear error messages when Gemma can't answer: no internet, timeout, free-tier limit reached, no credits / billing limit, invalid key, model not available on the account, or Gemma servers busy.

---

## Data (simulated)
No public textile-machine fault dataset exists, so the demo mill is simulated in `data.py`:
- 8 machines (6 looms, 2 ring spinning frames), one live sensor snapshot each
- maintenance history: loom-14 has had bearing wear twice, fixed only by lubrication
- 4 manual excerpts with part numbers
- the failure-risk model trains in about a second on 6,000 generated rows

**Next step:** connect real sensor feeds, the mill's maintenance (CMMS) history and OEM manuals. The harness does not change; only the tools do.

## Future scope
- **Self-improving from the floor.** After each job the technician confirms what actually fixed it: one tap ("fixed / not fixed") plus what they did, in their own language. Ustad stores that outcome in the machine's history and, on the next diagnosis, gives Gemma 4 the fixes that worked or failed before on this machine and similar machines. New fault types reported by technicians become new manual/knowledge entries once a supervisor approves them. The more the mill uses Ustad, the better its advice gets, and the best technician's knowledge stays when they are off shift. This is retrieval of past outcomes, not retraining Gemma; the failure-risk model can be periodically retrained on the confirmed outcomes.
- **Video of the fault.** Photos already work; next is short video clips (a loom's motion, a vibrating spindle), which Gemma 4 can also take as input.
- **Voice notes** in Urdu, Punjabi or Sindhi for technicians who don't type.
- **Native function calling.** Gemma 4 supports tool calling, so the fixed 4-step loop can become an agent that decides which tools to call (spare-parts stock, shift roster, open work orders).
- **Real data.** Live sensor feeds (PLC/SCADA), the mill's CMMS maintenance history, OEM manuals for Rieter, Picanol, Toyota, etc.
- **Bigger local model on the mill's server:** offline mode already works with Gemma 4 e2b in Ollama on a laptop; a mill server could run the larger Gemma 4 models locally for sharper diagnoses.
- **Shift handover and fleet patterns.** A daily summary of open faults, and spotting the same fault across many machines (a bad batch of parts, a wrong setting).

## Run it
```
python -m pip install -r requirements.txt
ollama pull gemma4:e2b; $env:OLLAMA_MODEL="gemma4:e2b"   # offline (optional)
$env:OPENROUTER_API_KEY="..."   # and/or $env:GEMINI_API_KEY="..."
python -m streamlit run app.py
```
Try the example buttons: **Roman Urdu: loom 14** shows the repeat-fault alert, **Vague note** shows Ustad asking which machine.

Restart the app to reset the simulated history (each run logs a case).

## Tests
`python check.py` runs 8 offline checks (Gemma faked): JSON parsing, unknown machine, Gemma down, bad model output, healthy machine not blamed, steps reported in order.
`python check.py live` calls Gemma for real.

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI: Diagnose tab, Mill floor tab |
| `harness.py` | The 4-step loop and prompts |
| `llm.py` | Gemma 4 client (OpenRouter, Google fallback, retries) |
| `data.py` | Simulated machines, sensors, history, manual |
| `ml.py` | Failure-risk model (tool) |
| `floor.py` | Mill floor dashboard |
| `skill/SKILL.md` | The same job as a no-code skill |
| `docs/` | Design spec, plan, screenshots |

## License
MIT
