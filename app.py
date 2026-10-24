import json
from pathlib import Path

import streamlit as st

import harness
from data import MACHINES

CACHE = Path(__file__).with_name("demo_cache.json")
EXAMPLES = {
    "Roman Urdu: loom 14": "loom-14 se ajeeb awaaz aa rahi hai, dhaaga baar baar toot raha hai",
    "English: spinning 01": "Spinning frame 01 keeps breaking yarn, ends down every few minutes",
    "Urdu: loom 03": "لوم 03 کی موٹر بہت گرم ہو رہی ہے اور جلنے کی بو آ رہی ہے",
    "Vague note": "machine theek nahi chal rahi, check karo",
}


def load_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(note, result):
    c = load_cache()
    c[note] = result
    CACHE.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")


def work_order(note, r):
    ex, ev, dx = r["extracted"], r["evidence"], r["diagnosis"]
    lines = [f"WORK ORDER - {MACHINES[ex['machine_id']]['name']} ({ex['machine_id']})",
             f"Priority: {dx.get('priority')}", f"Technician note: {note}", f"Cause: {dx.get('cause')}",
             f"ML risk: {ev['ml_risk']:.0%} ({ev['ml_fault']})", "Steps:"]
    lines += [f"  {i}. {s}" for i, s in enumerate(dx.get("steps", []), 1)]
    lines += [f"Parts: {', '.join(dx.get('parts', [])) or 'none'}", f"Repeat fault: {dx.get('repeat_pattern')}"]
    return "\n".join(lines)


st.set_page_config(page_title="Ustad", page_icon="🧵")
st.title("🧵 Ustad")
st.markdown("**The senior technician on every shift.**")
st.caption("Write what you see on the floor, in Roman Urdu, Urdu or English. Ustad reads it with Gemma 4, checks the "
           "machine's sensors, history and manual, then tells you the fix and warns when a fault keeps coming back. "
           "Demo data is simulated.")

st.session_state.setdefault("note", EXAMPLES["Roman Urdu: loom 14"])
cols = st.columns(len(EXAMPLES))
for col, (label, text) in zip(cols, EXAMPLES.items()):
    if col.button(label, use_container_width=True):
        st.session_state.note = text
        st.session_state.pop("result", None)  # don't leave the previous note's diagnosis on screen
note = st.text_area("Technician note", key="note", height=90)

if st.button("Diagnose with Gemma", type="primary") and note.strip():
    with st.spinner("Gemma is reading the note and checking the machine..."):
        r = harness.run(note.strip())
    if r["diagnosis"]:
        save_cache(note.strip(), r)
    elif r["error"] and note.strip() in load_cache():
        r = {**load_cache()[note.strip()], "cached": True}  # network died mid-demo: show last good run
    st.session_state.result = (note.strip(), r)

if "result" not in st.session_state:
    st.stop()

note, r = st.session_state.result
ex, ev, dx = r["extracted"], r["evidence"], r["diagnosis"]
if r.get("cached"):
    st.info("Gemma is unreachable right now, so this is the saved result from an earlier live run of the same note.")

st.subheader("How Gemma worked it out")
with st.expander("1. Understood the note", expanded=False):
    st.json(ex)
if r["needs_machine"]:
    st.warning("Which machine is this? The note doesn't name one, and the copilot won't guess. "
               f"Add the machine number, e.g. one of: {', '.join(MACHINES)}")
    st.stop()
with st.expander(f"2. Gathered evidence for {MACHINES[ex['machine_id']]['name']}"):
    c1, c2, c3 = st.columns(3)
    c1.metric("ML failure risk", f"{ev['ml_risk']:.0%}")
    c2.metric("Likely fault", ev["ml_fault"].replace("_", " "))
    c3.metric("Same fault before", ev["repeat_count"])
    st.write("**Live sensors**", ev["sensors"])
    st.write("**Maintenance history**", ev["history"] or "none")
    st.write("**Manual sections used**", ev["manual"])

if not dx:
    st.error(r["error"] or "No diagnosis.")
    st.stop()

st.subheader("3. Diagnosis")
if dx.get("repeat_pattern"):
    st.error(f"🔁 Repeat fault: {ev['ml_fault'].replace('_', ' ')} has happened {ev['repeat_count']} times on this "
             "machine already. The earlier fix isn't holding.")
c1, c2 = st.columns(2)
c1.metric("Priority", str(dx.get("priority", "?")).upper())
c2.metric("Parts", ", ".join(dx.get("parts", [])) or "none")
st.markdown(f"**Cause:** {dx.get('cause')}")
st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(dx.get("steps", []), 1)))
st.chat_message("assistant").write(dx.get("reply", ""))
st.subheader("4. Logged")
st.download_button("Download work order", work_order(note, r), file_name="work_order.txt")
