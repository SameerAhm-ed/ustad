# Hacktoberfest Karachi – Textile Predictive Maintenance

Event: Hacktoberfest Karachi, 3-hour build, must use Gemma (open-weight model).
Date: 2026-10-24

## Decisions
- **Product:** predictive maintenance for textile machines: predict fault, then suggest a remedy.
- **Data:** no public textile-machine fault dataset found. Use the UCI AI4I 2020 predictive-maintenance dataset
  (https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset, link/licence unverified)
  as a proxy, columns relabelled as textile signals (spindle speed, vibration, motor temp, tension, load).
  Say so openly in the demo.
- **Prediction model:** scikit-learn (gradient boosting / random forest): failure risk + fault type.
- **Remedy/explanation:** Gemma via API for now (local Ollama later if time). Prompt includes sensor readings,
  predicted fault and a manual snippet. Fallback: static fault-to-remedy table.
- **UI:** Streamlit (Python is installed on the team laptop).
- **Secrets:** API key in env var `GEMMA_API_KEY`, never in chat or committed.
- **Pitch:** runs on open weights, can go offline/on-prem, so machine data stays in the mill.

## Update (build)
- Data is **synthetic**, generated in `app.py` (no download); rules define fault labels. Replace with real mill logs if available.
- Gemma: `gemma-4-31b-it` via `google-genai`, key in env var `GEMINI_API_KEY`. Search tool, thinking and audio config from the sample were dropped.
- Solo team. Judging criteria still unknown, ask organisers.
- Run: `python -m pip install -r requirements.txt`, then `python -m streamlit run app.py`.

## Event rules (from Hacktoberfest-Karachi-Hack-Day.pptx)
- Track: Harness (code). Four must-haves: public GitHub repo, MIT/Apache-2.0/GPL-3.0 licence, Gemma 4 named in README as doing the work, MLH submission by 3:15 PM.
- Judges: it works, it's interesting, show it live.
- Submit: MLH Fest page > Challenges > Add Submission, tick every challenge.

## Polish decisions
- Photo inspection removed (untested, not core). Added: demo preset buttons, Urdu/Roman Urdu/English, follow-up chat, work-order download, retry on Gemma 503.
- Gemma is called only on button click or chat message, not on slider moves.
- Key rotated/kept out of files; `.gitignore` covers `.env`.

## Direction change (after brainstorming)
- Approved approach B, "Mill floor copilot": Gemma extracts a messy Roman Urdu note, our code runs tools (sensors, history, manual, ML risk), Gemma diagnoses and writes a work order, repeat faults flagged. Spec: docs/superpowers/specs/2026-10-24-mill-floor-copilot-design.md (awaiting user approval of the written spec).
- No training needed: harness = code + prompts. The small ML model trains in ~1s at startup.
- LLM access: `llm.py` tries OpenRouter `google/gemma-4-31b-it:free` (`OPENROUTER_API_KEY`), falls back to Google AI Studio (`GEMINI_API_KEY`). OpenRouter 404 because account allowed-providers excludes google-ai-studio; fix at openrouter.ai/settings/privacy. Fallback works.
- Keys were pasted in chat: rotate after the event. Never commit them.

## Product name
- **Ustad** (Urdu: master craftsman). Tagline: "The senior technician on every shift."

## Open questions
- Exact Gemma API model name/endpoint (see Gemma Quickstart link on the event page).
- Judging criteria, team size.

## Reference sources
- https://github.com/VictorBauler/awesome-bearing-dataset (bearing datasets index)
- https://ieee-dataport.org/comment/4788 (COMFAULDA)
- https://ntrs.nasa.gov/citations/20150007677 (C-MAPSS)
- https://arxiv.org/abs/1901.08247 (bearing diagnostics review)
- https://ifactoryapp.com/blog/ai-predictive-maintenance-textile-mills-spindles-looms (what to monitor)
