"""Mill floor view: live health of every machine at a glance."""
from html import escape

import streamlit as st

from data import HISTORY, MACHINES
from ml import risk

CSS = """<style>
.uf-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;font-family:inherit}
.uf-card{background:#fff;border-radius:12px;border-left:5px solid var(--c);padding:14px 16px;
box-shadow:0 1px 3px rgba(31,35,51,.08),0 4px 12px rgba(31,35,51,.05);color:#1F2333}
.uf-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.uf-name{font-weight:600;font-size:15px;line-height:1.25}
.uf-id{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;color:#6B7080;margin-top:2px}
.uf-pill{background:var(--bg);color:var(--c);font-size:11px;font-weight:600;padding:3px 9px;
border-radius:999px;white-space:nowrap}
.uf-bar{height:6px;background:#EEECE6;border-radius:3px;margin:12px 0 4px;overflow:hidden}
.uf-bar>div{height:100%;background:var(--c);border-radius:3px}
.uf-risk{font-size:11px;color:#6B7080;display:flex;justify-content:space-between}
.uf-read{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:10px;
border-top:1px solid #F0EEE8;padding-top:10px}
.uf-read b{display:block;font-size:15px;font-weight:600}
.uf-read span{font-size:10.5px;color:#6B7080}
.uf-tag{display:inline-block;margin-top:10px;font-size:11px;background:#EEF0FB;color:#3B4CCA;
padding:2px 8px;border-radius:6px;font-weight:500}
</style>"""

LEVELS = {  # rank, colour, pill background
    "attention": (0, "#C62828", "#FDECEC"),
    "watch": (1, "#B26A00", "#FFF4E0"),
    "healthy": (2, "#2E7D32", "#E8F5E9"),
}


def _card(mid, m, r_, fault, level):
    _, c, bg = LEVELS[level]
    s = m["sensors"]
    label = fault.replace("_", " ").capitalize() if level == "attention" else level.capitalize()
    repeats = sum(h.get("fault") == fault for h in HISTORY.get(mid, []))
    tag = f'<div class="uf-tag">🔁 {repeats} repeats</div>' if repeats >= 2 else ""
    reads = "".join(
        f"<div><b>{v}</b><span>{u}</span></div>"
        for v, u in [(f"{s['vibration_mm_s']:.1f}", "vibration mm/s"),
                     (f"{s['motor_temp_c']:.0f}", "motor °C"),
                     (f"{s['yarn_tension_cn']:.0f}", "tension cN")])
    return (f'<div class="uf-card" style="--c:{c};--bg:{bg}"><div class="uf-top"><div>'
            f'<div class="uf-name">{escape(m["name"])}</div><div class="uf-id">{escape(mid)}</div></div>'
            f'<span class="uf-pill">{escape(label)}</span></div>'
            f'<div class="uf-bar"><div style="width:{r_:.0%}"></div></div>'
            f'<div class="uf-risk"><span>Failure risk</span><span>{r_:.0%}</span></div>'
            f'<div class="uf-read">{reads}</div>{tag}</div>')


def render() -> None:
    rows = []
    for mid, m in MACHINES.items():
        r_, fault = risk(m["sensors"])
        level = "attention" if r_ >= 0.5 else "watch" if r_ >= 0.2 else "healthy"
        rows.append((LEVELS[level][0], -r_, mid, m, r_, fault, level))
    rows.sort(key=lambda x: x[:2])
    count = {k: sum(r[6] == k for r in rows) for k in LEVELS}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Machines running", len(rows))
    c2.metric("Need attention", count["attention"])
    c3.metric("Watch", count["watch"])
    c4.metric("Healthy", count["healthy"])

    cards = "".join(_card(mid, m, r_, f, lv) for *_, mid, m, r_, f, lv in rows)
    html = f'{CSS}<div class="uf-grid">{cards}</div>'
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)
