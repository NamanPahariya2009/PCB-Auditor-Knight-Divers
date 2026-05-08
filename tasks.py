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
            {"id": "VCC_9V",    "type": "POWER_SUPPLY",  "voltage": 9.0,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "MCU_U1",    "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.3,  "max_current_ma": 50},
            {"id": "C_MCU",     "type": "CAPACITOR",      "voltage": None, "max_input_voltage": None, "max_current_ma": None},
            {"id": "R1",        "type": "RESISTOR",       "voltage": None, "max_input_voltage": 50.0, "max_current_ma": 200},
            {"id": "LED_D1",    "type": "LED",            "voltage": None, "max_input_voltage": 5.0,  "max_current_ma": 20},
            {"id": "GND",       "type": "GROUND",         "voltage": 0.0, "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VCC_9V", "to": "MCU_U1",  "net": "VCC_RAIL",   "current_ma": 45, "protection": True},
            {"from": "VCC_9V", "to": "C_MCU",   "net": "VCC_RAIL",   "current_ma": 1,  "protection": True},
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
            {"id": "VMOT_12V",   "type": "POWER_SUPPLY",  "voltage": 12.0, "max_input_voltage": None, "max_current_ma": None},
            {"id": "VCC_3V3",    "type": "POWER_SUPPLY",  "voltage": 3.3,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "LOGIC_IC_U2","type": "LOGIC_IC",      "voltage": None,  "max_input_voltage": 5.0,  "max_current_ma": 100},
            {"id": "C_LOGIC",    "type": "CAPACITOR",     "voltage": None,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "MOSFET_Q1",  "type": "MOSFET",        "voltage": None,  "max_input_voltage": 20.0, "max_current_ma": 3000},
            {"id": "MOTOR_M1",   "type": "MOTOR",         "voltage": None,  "max_input_voltage": 12.0, "max_current_ma": 2000},
            {"id": "GND",        "type": "GROUND",        "voltage": 0.0,  "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VMOT_12V",   "to": "LOGIC_IC_U2", "net": "VMOT_RAIL",  "current_ma": 95,   "protection": True},
            {"from": "VMOT_12V",   "to": "C_LOGIC",     "net": "VMOT_RAIL",  "current_ma": 1,    "protection": True},
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
            {"id": "VINPUT_24V",   "type": "POWER_SUPPLY",  "voltage": 24.0, "max_input_voltage": None, "max_current_ma": None},
            {"id": "V5V_RAIL",     "type": "POWER_SUPPLY",  "voltage": 5.0,  "max_input_voltage": None, "max_current_ma": None},
            {"id": "REGULATOR_U1", "type": "VOLTAGE_REG",   "voltage": 3.3,  "max_input_voltage": 30.0, "max_current_ma": 1000},
            {"id": "MCU_U2",       "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 500},
            {"id": "C_MCU_U2",     "type": "CAPACITOR",      "voltage": None, "max_input_voltage": None, "max_current_ma": None},
            {"id": "SENSOR_IC_U3", "type": "SENSOR_IC",     "voltage": None, "max_input_voltage": 5.0,  "max_current_ma": 30},
            {"id": "OLED_U4",      "type": "DISPLAY",       "voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 100},
            {"id": "SD_CARD_U5",   "type": "STORAGE",       "voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 150},
            {"id": "GND",          "type": "GROUND",        "voltage": 0.0, "max_input_voltage": None, "max_current_ma": None},
        ],
        "netlist": [
            {"from": "VINPUT_24V",   "to": "SENSOR_IC_U3",  "net": "24V_RAIL",   "current_ma": 28,  "protection": True},
            {"from": "VINPUT_24V",   "to": "REGULATOR_U1",  "net": "24V_RAIL",   "current_ma": 780, "protection": True},
            {"from": "REGULATOR_U1", "to": "MCU_U2",        "net": "3V3_RAIL",   "current_ma": 750, "protection": True},
            {"from": "REGULATOR_U1", "to": "C_MCU_U2",      "net": "3V3_RAIL",   "current_ma": 1,   "protection": True},
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
            {"id": "VINPUT_24V",   "type": "POWER_SUPPLY",  "voltage": 24.0, "max_input_voltage": None, "max_current_ma": None},
            {"id": "REGULATOR_U1", "type": "VOLTAGE_REG",   "voltage": 3.3,  "max_input_voltage": 30.0, "max_current_ma": 1000},
            {"id": "MCU_U2",       "type": "MICROCONTROLLER","voltage": None, "max_input_voltage": 3.6,  "max_current_ma": 500},
            {"id": "SENSOR_IC_U3", "type": "SENSOR_IC",     "voltage": None, "max_input_voltage": 5.0,  "max_current_ma": 30},
            {"id": "GND",          "type": "GROUND",        "voltage": 0.0, "max_input_voltage": None, "max_current_ma": None},
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
    Scores the actual diagnostics first, then uses the verdict as confirmation.
    """
    if task_id not in TASKS:
        return _safe_score(0.0), f"Unknown task_id: {task_id}", []

    task = TASKS[task_id]
    expected = set(task["violations"])
    found = set(violations_found)
    checks_performed = checks_performed if checks_performed else []
    verdict_lower = str(verdict).lower() if verdict else ""

    expected_types = {_violation_type(v) for v in expected}
    found_expected = expected & found
    found_types = {_violation_type(v) for v in found}
    unexpected_types = found_types - expected_types

    required_checks = {_required_check_for_type(vtype) for vtype in expected_types}
    required_checks.discard(None)
    checks_done = required_checks & set(checks_performed)

    check_score = len(checks_done) / len(required_checks) if required_checks else 1.0
    exact_found_score = len(found_expected) / len(expected) if expected else 1.0
    type_found_score = len(found_types & expected_types) / len(expected_types) if expected_types else 1.0
    found_score = max(exact_found_score, 0.8 * type_found_score)

    verdict_hits = {
        vtype for vtype in expected_types
        if _verdict_mentions_type(verdict_lower, vtype)
    }
    verdict_score = len(verdict_hits) / len(expected_types) if expected_types else _safe_verdict_score(verdict_lower)

    score = (0.35 * check_score) + (0.45 * found_score) + (0.20 * verdict_score)

    false_positive_types = {
        vtype for vtype in _known_violation_types()
        if vtype not in expected_types and _verdict_mentions_type(verdict_lower, vtype)
    }
    score -= 0.15 * len(unexpected_types)
    score -= 0.20 * len(false_positive_types)

    msgs = [
        f"Checks performed: {len(checks_done)}/{len(required_checks)} required.",
        f"Expected violations found: {len(found_expected)}/{len(expected)}.",
        f"Verdict coverage: {len(verdict_hits)}/{len(expected_types)} violation type(s).",
    ]
    if unexpected_types:
        msgs.append(f"Unexpected diagnostic type(s): {', '.join(sorted(unexpected_types))}.")
    if false_positive_types:
        msgs.append(f"Verdict false positive type(s): {', '.join(sorted(false_positive_types))}.")

    return _safe_score(score), " | ".join(msgs), list(found)


def _violation_type(violation: str) -> str:
    return str(violation).split(":", 1)[0].upper()


def _known_violation_types() -> set:
    return {"VOLTAGE_MISMATCH", "SHORT_CIRCUIT", "OVERCURRENT", "MISSING_DECOUPLING"}


def _required_check_for_type(violation_type: str) -> Optional[str]:
    return {
        "VOLTAGE_MISMATCH": "check_voltage_mismatch",
        "SHORT_CIRCUIT": "check_short_circuit",
        "OVERCURRENT": "check_component_rating",
        "MISSING_DECOUPLING": "check_missing_decoupling",
    }.get(violation_type)


def _verdict_mentions_type(verdict: str, violation_type: str) -> bool:
    keywords = {
        "VOLTAGE_MISMATCH": ("voltage", "overvoltage", "mismatch", "9v", "12v", "24v"),
        "SHORT_CIRCUIT": ("short", "short circuit", "direct"),
        "OVERCURRENT": ("overcurrent", "current", "rating", "750", "500"),
        "MISSING_DECOUPLING": ("decoupling", "capacitor", "missing cap"),
    }
    return any(keyword in verdict for keyword in keywords.get(violation_type, (violation_type.lower(),)))


def _safe_verdict_score(verdict: str) -> float:
    hallucination_terms = ("short", "voltage", "overcurrent", "mismatch", "violation", "decoupling")
    return 0.0 if any(term in verdict for term in hallucination_terms) else 1.0


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
