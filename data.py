"""Simulated mill: machines, live sensors, maintenance history, manual excerpts. Replace with real data later."""

FEATURES = ["spindle_rpm", "vibration_mm_s", "motor_temp_c", "yarn_tension_cn", "load_pct", "hours_since_service"]

_OK = dict(spindle_rpm=12000, vibration_mm_s=3.0, motor_temp_c=64, yarn_tension_cn=25, load_pct=72, hours_since_service=300)

MACHINES = {
    "loom-01": {"name": "Air-jet loom 01", "sensors": {**_OK, "hours_since_service": 420}},
    "loom-02": {"name": "Air-jet loom 02", "sensors": dict(_OK)},
    "loom-03": {"name": "Rapier loom 03", "sensors": {**_OK, "motor_temp_c": 93, "load_pct": 104}},
    "loom-04": {"name": "Rapier loom 04", "sensors": {**_OK, "vibration_mm_s": 4.1}},
    "loom-05": {"name": "Rapier loom 05", "sensors": {**_OK, "hours_since_service": 800}},
    "loom-14": {"name": "Air-jet loom 14", "sensors": {**_OK, "vibration_mm_s": 8.2, "hours_since_service": 1150}},
    "spinning-01": {"name": "Ring spinning frame 01", "sensors": {**_OK, "spindle_rpm": 16500, "yarn_tension_cn": 9}},
    "spinning-02": {"name": "Ring spinning frame 02", "sensors": {**_OK, "spindle_rpm": 15000}},
}

HISTORY = {
    "loom-14": [
        {"date": "2026-09-12", "fault": "bearing_wear", "action": "lubricated main shaft bearing"},
        {"date": "2026-10-03", "fault": "bearing_wear", "action": "lubricated main shaft bearing"},
    ],
    "loom-03": [{"date": "2026-08-20", "fault": "motor_overheat", "action": "cleaned cooling fan"}],
    "spinning-01": [{"date": "2026-07-15", "fault": "overload", "action": "replaced drive belt"}],
}

# Placeholder manual text; swap in real OEM manual excerpts.
MANUAL = {
    "bearing_wear": "Bearing wear: rising vibration, noise, worse after long service intervals. Lubricate and check alignment. If vibration returns within weeks, lubrication is not enough: replace the bearing (part BRG-6205) and inspect the shaft.",
    "motor_overheat": "Motor overheating: blocked ventilation, overload or failing winding. Reduce load, clean cooling path, check belt tension, inspect winding insulation.",
    "tension_fault": "Yarn tension out of range: worn tensioner or wrong setting causes breaks or slack. Recalibrate tensioner, inspect guides and yarn path, replace worn tensioner discs (part TNS-12).",
    "overload": "Overload at high speed: motor and drive stress. Lower speed or load, check drive belt (part BLT-A40) and gearbox oil.",
}
