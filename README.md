# 🧵 Ustad

**The senior technician on every shift.** (*Ustad*: Urdu for master craftsman.)

**Problem:** In a textile mill, a technician spots a problem ("loom-14 se ajeeb awaaz aa rahi hai, dhaaga toot raha hai") and loses time finding the cause, the fix, and whether it has happened before. Notes are messy, often in Roman Urdu, and machine history is rarely checked, so the same quick fix is repeated until the machine breaks down.

**Solution:** Ustad, a harness around **Gemma 4** that turns a messy note into a diagnosis and work order, and flags faults that keep coming back.

Built for Hacktoberfest Karachi 2026, Harness track.

## How Gemma 4 does the work
`harness.py` runs a 4-step loop:
1. **Understand (Gemma 4):** reads a note in Roman Urdu, Urdu or English and extracts machine, symptom, urgency, language as JSON.
2. **Gather evidence (our tools):** live sensors, maintenance history, matching manual sections, and a scikit-learn failure-risk model.
3. **Diagnose (Gemma 4):** reasons over the evidence and returns cause, steps, part numbers, priority, a repeat-fault flag, and a reply in the technician's language.
4. **Remember:** logs the case to the machine's history, so the next repeat is caught.

Model: `gemma-4-31b-it`, via OpenRouter (`google/gemma-4-31b-it:free`) with Google AI Studio as fallback (`llm.py`). Gemma is open-weight, so this can run on a mill's own computer and keep machine data in the factory.

**Data is simulated** (8 machines, sensors, history, manual excerpts in `data.py`). Next step: real sensor feeds, CMMS history and OEM manuals.

## Run
```
python -m pip install -r requirements.txt
$env:OPENROUTER_API_KEY="..."   # and/or $env:GEMINI_API_KEY="..."
python -m streamlit run app.py
```
`python check.py` runs offline checks; `python check.py live` calls Gemma.

`demo_cache.json` holds results from earlier live runs; the app shows one (labelled as cached) only if Gemma is unreachable during a demo.

## License
MIT
