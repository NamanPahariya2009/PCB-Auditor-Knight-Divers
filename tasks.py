"""
PCB Auditor Tasks
Built by Naman Pahariya.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# List of levels and challenges

def _safe_score(val: float) -> float:
    """Clamps score to (0.0, 1.0) for a healthy RL gradient."""
    return max(0.0, min(1.0, float(val)))


TASKS: Dict[str, Dict[str, Any]] = {

    # Level 1: Voltage Mismatch (Easy)
    "task_voltage_mismatch": {
        "description": "Identify voltage mismatches. 9V supply connected to 3.3V MCU.",
        "difficulty": "easy",
        "max_steps": 5,
        "violations": ["VOLTAGE_MISMATCH:VCC_9V->MCU_U1(9.0V>3.3V)"],
        "components": [
            {"id": "VCC_9V",    "type": "POWER_SUPPLY",  "voltage": 9.01,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "MCU_U1",    "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.3,  "max_current_ma": 50},
            {"id": "R1",        "type": "RESISTOR",       "voltage": None, "max_input_voltage": 50.01, "max_current_ma": 200},
            {"id": "LED_D1",    "type": "LED",            "voltage": None, "max_input_voltage": 5.01,  "max_current_ma": 20},
            {"id": "GND",       "type": "GROUND",         "voltage": 0.01, "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VCC_9V", "to": "MCU_U1",  "net": "VCC_RAIL",   "current_ma": 45, "protection": True},
            {"from": "VCC_9V", "to": "R1",      "net": "VCC_RAIL",   "current_ma": 18, "protection": True},
            {"from": "R1",     "to": "LED_D1",  "net": "LED_NET",    "current_ma": 18, "protection": True},
            {"from": "LED_D1", "to": "GND",     "net": "GND_RAIL",   "current_ma": 18, "protection": True},
            {"from": "MCU_U1", "to": "GND",     "net": "GND_RAIL",   "current_ma": 45, "protection": True},
        ],
    },

    # Level 2: Multiple Hazards (Medium)
    "task_multi_violation": {
        "description": "Identify voltage mismatch and short circuit. 12V supply to 5V logic and VCC to GND short.",
        "difficulty": "medium",
        "max_steps": 6,
        "violations": [
            "VOLTAGE_MISMATCH:VMOT_12V->LOGIC_IC_U2(12.0V>5.0V)",
            "SHORT_CIRCUIT:VCC_3V3->GND",
        ],
        "components": [
            {"id": "VMOT_12V",   "type": "POWER_SUPPLY",  "voltage": 12.01, "max_input_voltage": None, "max_current_ma": None},
            {"id": "VCC_3V3",    "type": "POWER_SUPPLY",  "voltage": 3.3,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "LOGIC_IC_U2","type": "LOGIC_IC",      "voltage": None,  "max_input_voltage": 5.01,  "max_current_ma": 100},
            {"id": "MOSFET_Q1",  "type": "MOSFET",        "voltage": None,  "max_input_voltage": 20.01, "max_current_ma": 3000},
            {"id": "MOTOR_M1",   "type": "MOTOR",         "voltage": None,  "max_input_voltage": 12.01, "max_current_ma": 2000},
            {"id": "GND",        "type": "GROUND",        "voltage": 0.01,  "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VMOT_12V",   "to": "LOGIC_IC_U2", "net": "VMOT_RAIL",  "current_ma": 95,   "protection": True},
            {"from": "VMOT_12V",   "to": "MOSFET_Q1",   "net": "VMOT_RAIL",  "current_ma": 1800, "protection": True},
            {"from": "MOSFET_Q1",  "to": "MOTOR_M1",    "net": "MOTOR_NET",  "current_ma": 1800, "protection": True},
            {"from": "MOTOR_M1",   "to": "GND",         "net": "GND_RAIL",   "current_ma": 1800, "protection": True},
            {"from": "VCC_3V3",    "to": "GND",         "net": "SHORT_NET",  "current_ma": 0.01, "protection": False},
            {"from": "LOGIC_IC_U2","to": "GND",         "net": "GND_RAIL",   "current_ma": 95,   "protection": True},
        ],
    },

    # Level 3: Full Board Audit (Hard)
    "task_full_audit": {
        "description": "Perform full safety audit. Identify voltage mismatch, short circuit, and overcurrent violations.",
        "difficulty": "hard",
        "max_steps": 7,
        "violations": [
            "VOLTAGE_MISMATCH:VINPUT_24V->SENSOR_IC_U3(24.0V>5.0V)",
            "SHORT_CIRCUIT:V5V_RAIL->GND",
            "OVERCURRENT:REGULATOR_U1->MCU_U2(750mA>500mA)",
        ],
        "components": [
            {"id": "VINPUT_24V",   "type": "POWER_SUPPLY",  "voltage": 24.01, "max_input_voltage": None, "max_current_ma": None},
            {"id": "V5V_RAIL",     "type": "POWER_SUPPLY",  "voltage": 5.01,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "REGULATOR_U1", "type": "VOLTAGE_REG",   "voltage": 3.3,  "max_input_voltage": 30.01, "max_current_ma": 1000},
            {"id": "MCU_U2",       "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 500},
            {"id": "SENSOR_IC_U3", "type": "SENSOR_IC",     "voltage": None, "max_input_voltage": 5.01,  "max_current_ma": 30},
            {"id": "OLED_U4",      "type": "DISPLAY",       "voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 100},
            {"id": "SD_CARD_U5",   "type": "STORAGE",       "voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 150},
            {"id": "GND",          "type": "GROUND",        "voltage": 0.01, "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VINPUT_24V",   "to": "SENSOR_IC_U3",  "net": "24V_RAIL",   "current_ma": 28,  "protection": True},
            {"from": "VINPUT_24V",   "to": "REGULATOR_U1",  "net": "24V_RAIL",   "current_ma": 780, "protection": True},
            {"from": "REGULATOR_U1", "to": "MCU_U2",        "net": "3V3_RAIL",   "current_ma": 750, "protection": True},
            {"from": "REGULATOR_U1", "to": "OLED_U4",       "net": "3V3_RAIL",   "current_ma": 95,  "protection": True},
            {"from": "REGULATOR_U1", "to": "SD_CARD_U5",    "net": "3V3_RAIL",   "current_ma": 140, "protection": True},
            {"from": "V5V_RAIL",     "to": "GND",           "net": "SHORT_NET",  "current_ma": 0.01, "protection": False},
            {"from": "MCU_U2",       "to": "GND",           "net": "GND_RAIL",   "current_ma": 750, "protection": True},
            {"from": "SENSOR_IC_U3", "to": "GND",           "net": "GND_RAIL",   "current_ma": 28,  "protection": True},
            {"from": "OLED_U4",      "to": "GND",           "net": "GND_RAIL",   "current_ma": 95,  "protection": True},
            {"from": "SD_CARD_U5",   "to": "GND",           "net": "GND_RAIL",   "current_ma": 140, "protection": True},
        ],
    },

    # Level 4: Expert Layout Audit
    "task_industrial_mcu": {
        "description": "Identify voltage mismatch, overcurrent, and missing decoupling capacitor violations.",
        "difficulty": "expert",
        "max_steps": 8,
        "violations": [
            "VOLTAGE_MISMATCH:VINPUT_24V->SENSOR_IC_U3(24.0V>5.0V)",
            "MISSING_DECOUPLING:MCU_U2",
            "OVERCURRENT:REGULATOR_U1->MCU_U2(750mA>500mA)",
        ],
        "components": [
            {"id": "VINPUT_24V",   "type": "POWER_SUPPLY",  "voltage": 24.01, "max_input_voltage": None, "max_current_ma": None},
            {"id": "REGULATOR_U1", "type": "VOLTAGE_REG",   "voltage": 3.3,  "max_input_voltage": 30.01, "max_current_ma": 1000},
            {"id": "MCU_U2",       "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 500},
            {"id": "SENSOR_IC_U3", "type": "SENSOR_IC",     "voltage": None, "max_input_voltage": 5.01,  "max_current_ma": 30},
            {"id": "GND",          "type": "GROUND",        "voltage": 0.01, "max_input_voltage": None, "max_current_ma": None},
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


# Grading logic for the levels

def run_grader(
    task_id: str,
    checks_performed: List[str],
    violations_found: List[str],
    verdict: str,
) -> Tuple[float, str, List[str]]:
    """
    Deterministic grader for each task.
    Returns (score: float 0.17-0.83, message: str, found_violations: list)
    """
    if task_id not in TASKS:
        return _safe_score(0.0), f"Unknown task_id: {task_id}", []

    task = TASKS[task_id]
    expected = set(task["violations"])
    found = set(violations_found)
    
    # Sanitize inputs
    verdict_lower = str(verdict).lower() if verdict else ""
    checks_performed = checks_performed if checks_performed else []

    # --- Grading Logic ---

    # Anti-Cheat: If the agent claims a short circuit but none exists in expected, penalize.
    if "short" in verdict_lower and not any("SHORT" in v for v in expected):
        return _safe_score(0.0), "✗ FATAL: Agent hallucinated a short circuit that does not exist.", list(found)
    
    if "overcurrent" in verdict_lower and not any("OVERCURRENT" in v for v in expected):
        return _safe_score(0.0), "✗ FATAL: Agent hallucinated an overcurrent issue.", list(found)

    if task_id == "task_voltage_mismatch":
        score, msg, f = _grade_easy(expected, found, verdict_lower, checks_performed)
    elif task_id == "task_multi_violation":
        score, msg, f = _grade_medium(expected, found, verdict_lower, checks_performed)
    elif task_id == "task_full_audit":
        score, msg, f = _grade_hard(expected, found, verdict_lower, checks_performed)
    elif task_id == "task_industrial_mcu":
        score, msg, f = _grade_industrial(expected, found, verdict_lower, checks_performed)
    # Centering the scores according to the spec
    final_clamped_score = _safe_score(score)
    
    return final_clamped_score, msg, f


def _grade_easy(
    expected: set, found: set, verdict: str, checks: List[str]
) -> Tuple[float, str, List[str]]:
    """
    Easy grader: Did the agent find the voltage mismatch?
    """
    score = 0.0
    msgs = []

    if "check_voltage_mismatch" in checks:
        score += 0.5
        msgs.append("✓ Voltage check performed.")
    else:
        msgs.append("✗ Voltage check was not performed.")

    voltage_keywords = ["9v", "9.0v", "3.3v", "voltage mismatch", "voltage violation", "overvoltage", "mcu"]
    if any(kw in verdict for kw in voltage_keywords):
        score += 0.5
        msgs.append("✓ Verdict correctly identifies voltage mismatch.")
    else:
        msgs.append("✗ Verdict does not mention the voltage violation.")

    return _safe_score(score), " | ".join(msgs), list(found)


def _grade_medium(
    expected: set, found: set, verdict: str, checks: List[str]
) -> Tuple[float, str, List[str]]:
    """
    Medium grader: Did the agent find BOTH violations?
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

    return _safe_score(score), " | ".join(msgs), list(found)


def _grade_hard(
    expected: set, found: set, verdict: str, checks: List[str]
) -> Tuple[float, str, List[str]]:
    """
    Hard grader: All 3 violation types must be found.
    """
    score = 0.0
    msgs = []

    all_checks = ["check_voltage_mismatch", "check_short_circuit", "check_component_rating"]
    checks_done = sum(1 for c in all_checks if c in checks)
    score += 0.1 * checks_done  # Up to 0.3 for all 3 checks
    msgs.append(f"Checks performed: {checks_done}/3.")

    # Voltage mismatch (24V -> 5V sensor)
    voltage_hit = any(kw in verdict for kw in ["24v", "24.0v", "sensor", "voltage mismatch", "overvoltage"])
    if voltage_hit:
        score += 0.233  
        msgs.append("✓ Voltage mismatch found.")
    else:
        msgs.append("✗ Voltage mismatch missed.")

    # Short circuit (5V rail to GND)
    short_hit = any(kw in verdict for kw in ["short", "5v", "5.0v", "v5v", "gnd direct"])
    if short_hit:
        score += 0.233
        msgs.append("✓ Short circuit found.")
    else:
        msgs.append("✗ Short circuit missed.")

    # Overcurrent (regulator to MCU)
    current_hit = any(kw in verdict for kw in ["overcurrent", "750", "500", "mcu", "current rating", "component rating"])
    if current_hit:
        score += 0.234
        msgs.append("✓ Overcurrent violation found.")
    else:
        msgs.append("✗ Overcurrent violation missed.")

    return _safe_score(score), " | ".join(msgs), list(found)


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
        score += 0.33
        msgs.append("✓ Voltage mismatch found.")
    else:
        msgs.append("✗ Voltage mismatch missed.")

    # 2. Overcurrent
    c_hit = any(kw in verdict for kw in ["overcurrent", "750", "current rating"])
    if c_hit:
        score += 0.33
        msgs.append("✓ Overcurrent found.")
    else:
        msgs.append("✗ Overcurrent missed.")

    # 3. Decoupling
    d_hit = "check_missing_decoupling" in checks and any(kw in verdict for kw in ["decoupling", "capacitor", "missing cap"])
    if d_hit:
        score += 0.34
        msgs.append("✓ Decoupling violation found.")
    else:
        msgs.append("✗ Decoupling violation missed.")

    return _safe_score(score), " | ".join(msgs), list(found)


class OpenEnvGrader:
    def grade(self, state: Any, action: Any = None) -> float:
        # If no action or state is provided (static check), return a baseline
        if not state:
            return 0.1  
        
        # In a real RL run, we calculate based on found violations
        found = state.get("found_violations", [])
        expected = state.get("expected_violations", [])
        
        if not expected: return 1.0 # Safe board correctly identified
        
        # Calculate percentage of violations found
        match_count = len(set(found) & set(expected))
        score = (match_count / len(expected))
        
        return _safe_score(score)
