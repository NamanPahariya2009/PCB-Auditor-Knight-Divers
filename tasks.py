"""
PCB Auditor Tasks — 3 tasks with deterministic graders (Easy → Hard)

Task 1 (Easy):    Single voltage mismatch — agent must find 1 obvious violation
Task 2 (Medium):  Short circuit + voltage mismatch — agent must find 2 violations
Task 3 (Hard):    All 3 violation types across a complex netlist — agent must find all 3
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# ── TASK DEFINITIONS ──────────────────────────────────────────

TASKS: Dict[str, Dict[str, Any]] = {

    # ── TASK 1: EASY — Voltage Mismatch ──────────────────────
    "task_voltage_mismatch": {
        "description": (
            "You are auditing a simple sensor module PCB. "
            "A 9V power supply is connected through the board. "
            "Inspect the netlist for any dangerous voltage mismatches "
            "that could damage components. "
            "Submit your findings with a verdict."
        ),
        "difficulty": "easy",
        "max_steps": 5,
        "violations": ["VOLTAGE_MISMATCH:VCC_9V->MCU_U1(9.0V>3.3V)"],
        "components": [
            {"id": "VCC_9V",    "type": "POWER_SUPPLY",  "voltage": 9.0,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "MCU_U1",    "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.3,  "max_current_ma": 50},
            {"id": "R1",        "type": "RESISTOR",       "voltage": None, "max_input_voltage": 50.0, "max_current_ma": 200},
            {"id": "LED_D1",    "type": "LED",            "voltage": None, "max_input_voltage": 5.0,  "max_current_ma": 20},
            {"id": "GND",       "type": "GROUND",         "voltage": 0.0,  "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VCC_9V", "to": "MCU_U1",  "net": "VCC_RAIL",   "current_ma": 45, "protection": True},
            {"from": "VCC_9V", "to": "R1",      "net": "VCC_RAIL",   "current_ma": 18, "protection": True},
            {"from": "R1",     "to": "LED_D1",  "net": "LED_NET",    "current_ma": 18, "protection": True},
            {"from": "LED_D1", "to": "GND",     "net": "GND_RAIL",   "current_ma": 18, "protection": True},
            {"from": "MCU_U1", "to": "GND",     "net": "GND_RAIL",   "current_ma": 45, "protection": True},
        ],
    },

    # ── TASK 2: MEDIUM — Voltage Mismatch + Short Circuit ────
    "task_multi_violation": {
        "description": (
            "You are auditing a motor driver board. "
            "The design uses a 12V motor supply and a 3.3V logic rail. "
            "There are two separate issues on this board. "
            "Find ALL violations before submitting your verdict. "
            "Missing any violation will reduce your score."
        ),
        "difficulty": "medium",
        "max_steps": 6,
        "violations": [
            "VOLTAGE_MISMATCH:VMOT_12V->LOGIC_IC_U2(12.0V>5.0V)",
            "SHORT_CIRCUIT:VCC_3V3->GND",
        ],
        "components": [
            {"id": "VMOT_12V",   "type": "POWER_SUPPLY",  "voltage": 12.0, "max_input_voltage": None, "max_current_ma": None},
            {"id": "VCC_3V3",    "type": "POWER_SUPPLY",  "voltage": 3.3,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "LOGIC_IC_U2","type": "LOGIC_IC",      "voltage": None,  "max_input_voltage": 5.0,  "max_current_ma": 100},
            {"id": "MOSFET_Q1",  "type": "MOSFET",        "voltage": None,  "max_input_voltage": 20.0, "max_current_ma": 3000},
            {"id": "MOTOR_M1",   "type": "MOTOR",         "voltage": None,  "max_input_voltage": 12.0, "max_current_ma": 2000},
            {"id": "GND",        "type": "GROUND",        "voltage": 0.0,   "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VMOT_12V",   "to": "LOGIC_IC_U2", "net": "VMOT_RAIL",  "current_ma": 95,   "protection": True},
            {"from": "VMOT_12V",   "to": "MOSFET_Q1",   "net": "VMOT_RAIL",  "current_ma": 1800, "protection": True},
            {"from": "MOSFET_Q1",  "to": "MOTOR_M1",    "net": "MOTOR_NET",  "current_ma": 1800, "protection": True},
            {"from": "MOTOR_M1",   "to": "GND",         "net": "GND_RAIL",   "current_ma": 1800, "protection": True},
            {"from": "VCC_3V3",    "to": "GND",         "net": "SHORT_NET",  "current_ma": 0,    "protection": False},
            {"from": "LOGIC_IC_U2","to": "GND",         "net": "GND_RAIL",   "current_ma": 95,   "protection": True},
        ],
    },

    # ── TASK 3: HARD — All 3 Violation Types ─────────────────
    "task_full_audit": {
        "description": (
            "You are performing a full safety audit of a power management PCB "
            "before it goes to manufacturing. This is a complex board with "
            "multiple power domains: 24V industrial input, 5V logic, and 3.3V MCU rail. "
            "There are three distinct violations hidden in this netlist. "
            "You must run ALL relevant checks to find them. "
            "Only a perfect audit (all violations found, no false positives) "
            "will earn full marks. A partial audit will receive partial credit."
        ),
        "difficulty": "hard",
        "max_steps": 7,
        "violations": [
            "VOLTAGE_MISMATCH:VINPUT_24V->SENSOR_IC_U3(24.0V>5.0V)",
            "SHORT_CIRCUIT:V5V_RAIL->GND",
            "OVERCURRENT:REGULATOR_U1->MCU_U2(750mA>500mA)",
        ],
        "components": [
            {"id": "VINPUT_24V",   "type": "POWER_SUPPLY",  "voltage": 24.0, "max_input_voltage": None, "max_current_ma": None},
            {"id": "V5V_RAIL",     "type": "POWER_SUPPLY",  "voltage": 5.0,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "REGULATOR_U1", "type": "VOLTAGE_REG",   "voltage": 3.3,  "max_input_voltage": 30.0, "max_current_ma": 1000},
            {"id": "MCU_U2",       "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 500},
            {"id": "SENSOR_IC_U3", "type": "SENSOR_IC",     "voltage": None, "max_input_voltage": 5.0,  "max_current_ma": 30},
            {"id": "OLED_U4",      "type": "DISPLAY",       "voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 100},
            {"id": "SD_CARD_U5",   "type": "STORAGE",       "voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 150},
            {"id": "GND",          "type": "GROUND",        "voltage": 0.0,  "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VINPUT_24V",   "to": "SENSOR_IC_U3",  "net": "24V_RAIL",   "current_ma": 28,  "protection": True},
            {"from": "VINPUT_24V",   "to": "REGULATOR_U1",  "net": "24V_RAIL",   "current_ma": 780, "protection": True},
            {"from": "REGULATOR_U1", "to": "MCU_U2",        "net": "3V3_RAIL",   "current_ma": 750, "protection": True},
            {"from": "REGULATOR_U1", "to": "OLED_U4",       "net": "3V3_RAIL",   "current_ma": 95,  "protection": True},
            {"from": "REGULATOR_U1", "to": "SD_CARD_U5",    "net": "3V3_RAIL",   "current_ma": 140, "protection": True},
            {"from": "V5V_RAIL",     "to": "GND",           "net": "SHORT_NET",  "current_ma": 0,   "protection": False},
            {"from": "MCU_U2",       "to": "GND",           "net": "GND_RAIL",   "current_ma": 750, "protection": True},
            {"from": "SENSOR_IC_U3", "to": "GND",           "net": "GND_RAIL",   "current_ma": 28,  "protection": True},
            {"from": "OLED_U4",      "to": "GND",           "net": "GND_RAIL",   "current_ma": 95,  "protection": True},
            {"from": "SD_CARD_U5",   "to": "GND",           "net": "GND_RAIL",   "current_ma": 140, "protection": True},
        ],
    },

    # ── TASK 4: EXPERT — Heuristics + Multiple Violations ──────
    "task_industrial_mcu": {
        "description": (
            "You are auditing a high-reliability industrial controller. "
            "The board takes a 24V input and regulates it down for a sensitive MCU. "
            "This task requires advanced heuristics. In addition to standard "
            "electrical checks, ensure that high-speed digital components "
            "have proper decoupling shielding. "
            "Find all 3 violations: one voltage, one current, and one heuristic."
        ),
        "difficulty": "expert",
        "max_steps": 8,
        "violations": [
            "VOLTAGE_MISMATCH:VINPUT_24V->SENSOR_IC_U3(24.0V>5.0V)",
            "MISSING_DECOUPLING:MCU_U2",
            "OVERCURRENT:REGULATOR_U1->MCU_U2(750mA>500mA)",
        ],
        "components": [
            {"id": "VINPUT_24V",   "type": "POWER_SUPPLY",  "voltage": 24.0, "max_input_voltage": None, "max_current_ma": None},
            {"id": "REGULATOR_U1", "type": "VOLTAGE_REG",   "voltage": 3.3,  "max_input_voltage": 30.0, "max_current_ma": 1000},
            {"id": "MCU_U2",       "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 500},
            {"id": "SENSOR_IC_U3", "type": "SENSOR_IC",     "voltage": None, "max_input_voltage": 5.0,  "max_current_ma": 30},
            {"id": "GND",          "type": "GROUND",        "voltage": 0.0,  "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VINPUT_24V",   "to": "SENSOR_IC_U3",  "net": "24V_RAIL",   "current_ma": 28,  "protection": True},
            {"from": "VINPUT_24V",   "to": "REGULATOR_U1",  "net": "24V_RAIL",   "current_ma": 780, "protection": True},
            {"from": "REGULATOR_U1", "to": "MCU_U2",        "net": "3V3_RAIL",   "current_ma": 750, "protection": True},
            {"from": "MCU_U2",       "to": "GND",           "net": "GND_RAIL",   "current_ma": 750, "protection": True},
            {"from": "SENSOR_IC_U3", "to": "GND",           "net": "GND_RAIL",   "current_ma": 28,  "protection": True},
        ],
    },
}


# ── GRADERS ───────────────────────────────────────────────────

def run_grader(
    task_id: str,
    checks_performed: List[str],
    violations_found: List[str],
    verdict: str,
) -> Tuple[float, str, List[str]]:
    """
    Deterministic grader for each task.
    Returns (score: float 0.0-1.0, message: str, found_violations: list)
    """
    if task_id not in TASKS:
        return 0.0, f"Unknown task_id: {task_id}", []

    task = TASKS[task_id]
    expected = set(task["violations"])
    found = set(violations_found)
    verdict_lower = verdict.lower()

    # ── TASK-SPECIFIC GRADERS ─────────────────────────────────

    if task_id == "task_voltage_mismatch":
        return _grade_easy(expected, found, verdict_lower, checks_performed)

    elif task_id == "task_multi_violation":
        return _grade_medium(expected, found, verdict_lower, checks_performed)

    elif task_id == "task_full_audit":
        return _grade_hard(expected, found, verdict_lower, checks_performed)

    elif task_id == "task_industrial_mcu":
        return _grade_industrial(expected, found, verdict_lower, checks_performed)

    return 0.0, "No grader defined for this task.", []


def _grade_easy(
    expected: set, found: set, verdict: str, checks: List[str]
) -> Tuple[float, str, List[str]]:
    """
    Easy grader: Did the agent find the voltage mismatch?
    Full score (1.0) requires:
    - check_voltage_mismatch was performed
    - verdict mentions 9V, 3.3V, or voltage mismatch
    """
    score = 0.0
    msgs = []

    if "check_voltage_mismatch" in checks:
        score += 0.4
        msgs.append("✓ Voltage check performed.")
    else:
        msgs.append("✗ Voltage check was not performed.")

    voltage_keywords = ["9v", "9.0v", "3.3v", "voltage mismatch", "voltage violation", "overvoltage", "mcu"]
    if any(kw in verdict for kw in voltage_keywords):
        score += 0.6
        msgs.append("✓ Verdict correctly identifies voltage mismatch.")
    else:
        msgs.append("✗ Verdict does not mention the voltage violation.")

    score = min(1.0, score)
    return score, " | ".join(msgs), list(found)


def _grade_medium(
    expected: set, found: set, verdict: str, checks: List[str]
) -> Tuple[float, str, List[str]]:
    """
    Medium grader: Did the agent find BOTH violations?
    Full score (1.0) requires both checks AND both violations in verdict.
    Partial credit (0.5) for finding one.
    """
    score = 0.0
    msgs = []

    # Check 1: Voltage mismatch
    voltage_ok = "check_voltage_mismatch" in checks
    voltage_in_verdict = any(kw in verdict for kw in ["12v", "12.0v", "5v", "voltage", "overvoltage"])

    # Check 2: Short circuit
    short_ok = "check_short_circuit" in checks
    short_in_verdict = any(kw in verdict for kw in ["short", "short circuit", "3.3v", "3v3", "gnd"])

    if voltage_ok:
        score += 0.2
        msgs.append("✓ Voltage check performed.")
    else:
        msgs.append("✗ Voltage check skipped.")

    if short_ok:
        score += 0.2
        msgs.append("✓ Short circuit check performed.")
    else:
        msgs.append("✗ Short circuit check skipped.")

    if voltage_in_verdict:
        score += 0.3
        msgs.append("✓ Verdict identifies voltage violation.")
    else:
        msgs.append("✗ Verdict misses voltage violation.")

    if short_in_verdict:
        score += 0.3
        msgs.append("✓ Verdict identifies short circuit.")
    else:
        msgs.append("✗ Verdict misses short circuit.")

    score = min(1.0, score)
    return score, " | ".join(msgs), list(found)


def _grade_hard(
    expected: set, found: set, verdict: str, checks: List[str]
) -> Tuple[float, str, List[str]]:
    """
    Hard grader: All 3 violation types must be found.
    Full score (1.0) requires all 3 checks AND all 3 violations mentioned.
    Partial credit scales with how many are found.
    """
    score = 0.0
    msgs = []

    all_checks = ["check_voltage_mismatch", "check_short_circuit", "check_component_rating"]
    checks_done = sum(1 for c in all_checks if c in checks)
    score += 0.1 * checks_done
    msgs.append(f"Checks performed: {checks_done}/3.")

    # Voltage mismatch (24V -> 5V sensor)
    voltage_hit = any(kw in verdict for kw in ["24v", "24.0v", "sensor", "voltage mismatch", "overvoltage"])
    if voltage_hit:
        score += 0.25
        msgs.append("✓ Voltage mismatch found.")
    else:
        msgs.append("✗ Voltage mismatch missed.")

    # Short circuit (5V rail to GND)
    short_hit = any(kw in verdict for kw in ["short", "5v", "5.0v", "v5v", "gnd direct"])
    if short_hit:
        score += 0.25
        msgs.append("✓ Short circuit found.")
    else:
        msgs.append("✗ Short circuit missed.")

    # Overcurrent (regulator to MCU)
    current_hit = any(kw in verdict for kw in ["overcurrent", "750", "500", "mcu", "current rating", "component rating"])
    if current_hit:
        score += 0.25
        msgs.append("✓ Overcurrent violation found.")
    else:
        msgs.append("✗ Overcurrent violation missed.")

    score = min(1.0, score)
    return score, " | ".join(msgs), list(found)


def _grade_industrial(
    expected: set, found: set, verdict: str, checks: List[str]
) -> Tuple[float, str, List[str]]:
    """
    Expert grader: Decoupling + Voltage + Current.
    """
    score = 0.0
    msgs = []

    # 1. Voltage mismatch
    v_hit = any(kw in verdict for kw in ["24v", "sensor", "voltage mismatch"])
    if v_hit:
        score += 0.3
        msgs.append("✓ Voltage mismatch found.")
    else:
        msgs.append("✗ Voltage mismatch missed.")

    # 2. Overcurrent
    c_hit = any(kw in verdict for kw in ["overcurrent", "750", "current rating"])
    if c_hit:
        score += 0.3
        msgs.append("✓ Overcurrent found.")
    else:
        msgs.append("✗ Overcurrent missed.")

    # 3. Decoupling
    d_hit = "check_missing_decoupling" in checks and any(kw in verdict for kw in ["decoupling", "capacitor", "missing cap"])
    if d_hit:
        score += 0.4
        msgs.append("✓ Decoupling violation found.")
    else:
        msgs.append("✗ Decoupling violation missed.")

    score = min(1.0, score)
    return score, " | ".join(msgs), list(found)
