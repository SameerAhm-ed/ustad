import json
from pathlib import Path

import streamlit as st

import floor
import harness
from data import MACHINES

CACHE = Path(__file__).with_name("demo_cache.json")
EXAMPLES = {
    "Roman Urdu: loom 14": "loom-14 se ajeeb awaaz aa rahi hai, dhaaga baar baar toot raha hai",
    "English: spinning 01": "Spinning frame 01 keeps breaking yarn, ends down every few minutes",
    "Urdu: loom 03": "لوم 03 کی موٹر بہت گرم ہو رہی ہے اور جلنے کی بو آ رہی ہے",
    "Vague note": "machine theek nahi chal rahi, check karo",
}
PRIORITY_COLOR = {"stop machine now": "red", "high": "orange", "medium": "orange", "low": "green"}


def plain(s):
    return str(s).replace("_", " ").capitalize()


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


ERROR_ICONS = {"no_internet": "📡", "timeout": "⏱️", "credits": "💳", "quota": "🚦", "auth": "🔑",
               "provider": "🚫", "busy": "🔥"}


def show_step(box, name, data):
    if name == "understood" and data.get("urgency") == "unknown":  # harness regex fallback, not Gemma
        box.write(f"⚠️ **Gemma unreachable**: {data.get('gemma_error') or 'no answer'} "
                  f"Found machine {data.get('machine_id') or '?'} from the note text instead.")
    elif name == "understood":
        box.write(f"✅ **Understood the note** ({data.get('language')}): {data.get('machine_id') or 'machine?'} · "
                  f"{data.get('symptom')} · urgency {data.get('urgency')}")
    elif name == "evidence":
        box.write(f"✅ **Checked the machine**: ML risk {data['ml_risk']:.0%} ({plain(data['ml_fault'])}) · "
                  f"{len(data['history'])} past jobs · {len(data['manual'])} manual section(s)")
    elif name == "diagnosing":
        box.write("🧠 **Gemma 4 is diagnosing** from the evidence…")
    elif name == "diagnosis":
        box.write("✅ **Diagnosis ready**, case logged to machine history")


st.set_page_config(page_title="Ustad", page_icon="🧵", layout="wide")
st.markdown("## 🧵 Ustad &nbsp;·&nbsp; <small>**The senior technician on every shift.**</small>", unsafe_allow_html=True)
st.caption("Write what you see on the floor, in Roman Urdu, Urdu or English. Ustad reads it with Gemma 4, checks the "
           "machine's sensors, history and manual, then tells you the fix and warns when a fault keeps coming back. "
           "Demo data is simulated.")

tab_dx, tab_floor = st.tabs(["🩺 Diagnose", "🏭 Mill floor"])

with tab_floor:  # drawn first so an early return in the Diagnose tab can't skip it
    floor.render()


def pick_example(text):  # callback runs before the text_area is drawn, so it may set its key
    st.session_state.note = text
    st.session_state.pop("result", None)  # don't leave the previous note's diagnosis on screen


def diagnose_tab():
    st.session_state.setdefault("note", EXAMPLES["Roman Urdu: loom 14"])
    note = st.text_area("Technician note", key="note", height=80)
    go = st.button("Diagnose with Ustad", type="primary")
    cols = st.columns(len(EXAMPLES))
    for col, (label, text) in zip(cols, EXAMPLES.items()):
        col.button(label, use_container_width=True, on_click=pick_example, args=(text,))

    if go and note.strip():
        with st.status("Ustad is working on it…", expanded=True) as box:
            r = harness.run(note.strip(), on_step=lambda name, data: show_step(box, name, data))
            if r["diagnosis"]:
                save_cache(note.strip(), r)
            elif r["error"] and note.strip() in load_cache():
                r = {**load_cache()[note.strip()], "cached": True,  # network died mid-demo: show last good run
                     "live_error": r["error"], "live_error_kind": r.get("error_kind")}
            box.update(label="Done" if r["diagnosis"] else "Needs attention", expanded=False,
                       state="complete" if r["diagnosis"] else "error")
        st.session_state.result = (note.strip(), r)

    if "result" not in st.session_state:
        return

    note, r = st.session_state.result
    ex, ev, dx = r["extracted"], r["evidence"], r["diagnosis"]
    if r.get("cached"):
        reason = (r.get("live_error") or "no answer").rstrip(".")
        st.info(f"Gemma couldn't answer live ({reason}). Showing the saved result from an earlier live run of the same note.")
    if r["needs_machine"]:
        st.warning("Which machine is this? The note doesn't name one, and Ustad won't guess. "
                   f"Add the machine number, e.g. one of: {', '.join(MACHINES)}")
        return
    if not dx:
        st.error(r["error"] or "No diagnosis.", icon=ERROR_ICONS.get(r.get("error_kind"), "⚠️"))
        return

    name = MACHINES[ex["machine_id"]]["name"]
    st.subheader(f"Diagnosis: {name}")
    if dx.get("repeat_pattern"):
        st.error(f"🔁 **Repeat fault.** {plain(ev['ml_fault'])} has happened {ev['repeat_count']} times on this machine "
                 "already. The earlier fix isn't holding.")

    left, right = st.columns([3, 2])
    with left:
        color = PRIORITY_COLOR.get(str(dx.get("priority", "")).lower(), "gray")
        st.markdown(f"### :{color}-background[{str(dx.get('priority', '?')).upper()}]")
        st.markdown(f"**Cause:** {plain(dx.get('cause'))}")
        st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(dx.get("steps", []), 1)))
        st.markdown(f"**Parts:** {', '.join(f'`{p}`' for p in dx.get('parts', [])) or 'none'}")
        st.chat_message("assistant", avatar="🧵").write(dx.get("reply", ""))
        st.download_button("Download work order", work_order(note, r), file_name="work_order.txt")
    with right:
        st.markdown("**Machine history**")
        for h in ev["history"]:
            mark = "🔁" if h["fault"] == ev["ml_fault"] else "•"
            st.markdown(f"{mark} `{h['date']}` {plain(h['fault'])}: {h['action']}")
        with st.expander("Evidence Gemma used"):
            st.write("**Live sensors**", ev["sensors"])
            st.write("**Manual sections**", ev["manual"])
            st.write("**Understood note**", ex)


with tab_dx:
    diagnose_tab()
