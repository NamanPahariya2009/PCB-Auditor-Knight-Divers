"""
PCB Auditor Environment.
Built by Naman Pahariya.
"""

from __future__ import annotations
from collections import defaultdict
import random
import copy
import networkx as nx
from typing import Any, Dict, Iterable, List, Optional, Tuple
from pydantic import BaseModel, Field

from tasks import TASKS, run_grader


# Data models for observations, actions, and rewards

class Observation(BaseModel):
    """What the agent sees at each step."""
    task_id: str = Field(description="Unique task identifier")
    task_description: str = Field(description="Natural language description of the audit task")
    netlist: List[Dict[str, Any]] = Field(description="List of netlist connections to audit")
    components: List[Dict[str, Any]] = Field(description="Component specifications")
    available_checks: List[str] = Field(description="List of check types the agent can run")
    last_check_result: Optional[str] = Field(default=None, description="Result of the last check performed")
    checks_performed: List[str] = Field(default_factory=list, description="Checks performed so far this episode")
    audit_log: List[str] = Field(default_factory=list, description="Full log of all check results this episode")
    violation_paths: List[List[str]] = Field(default_factory=list, description="Full node paths of violations found (for graph highlighting)")
    step_count: int = Field(default=0, description="Number of steps taken so far")
    max_steps: int = Field(default=5, description="Maximum steps allowed per episode")
    done: bool = Field(default=False, description="Whether the episode has ended")


class Action(BaseModel):
    """What the agent can do."""
    check_type: str = Field(
        description="Type of check to perform. One of: check_voltage_mismatch, check_short_circuit, check_component_rating, submit_verdict"
    )
    target_nets: Optional[List[str]] = Field(default=None)
    verdict: Optional[str] = Field(default=None)


class Reward(BaseModel):
    """Reward signal for this step."""
    value: float = Field(description="Reward value for this step (strictly between 0.15 and 0.85)")
    message: str = Field(description="Human-readable explanation of the reward")
    partial_credit: float = Field(default=0.15)
    is_terminal: bool = Field(default=False)


class State(BaseModel):
    """Full internal state (for debugging/logging)."""
    current_task_id: str
    episode_step: int
    checks_performed: List[str]
    violations_found: List[str]
    violation_paths: List[List[str]]
    correct_violations: List[str]
    audit_log: List[str]
    score: float


# Main Environment Logic

class PCBAuditorEnv:
    AVAILABLE_CHECKS = [
        "check_voltage_mismatch",
        "check_short_circuit",
        "check_component_rating",
        "check_missing_decoupling",
        "submit_verdict",
    ]

    def __init__(self, task_id: Optional[str] = None):
        self._task_id = task_id
        self._state: Optional[State] = None
        self._current_task: Optional[Dict] = None
        self._obs: Optional[Observation] = None

    def reset(self, task_id: Optional[str] = None, custom_task: Optional[Dict] = None) -> Observation:
        if custom_task:
            task = copy.deepcopy(custom_task)
            tid = "custom_task"
        else:
            tid = task_id or self._task_id or random.choice(list(TASKS.keys()))
            if tid not in TASKS:
                raise ValueError(f"Unknown task_id '{tid}'. Available: {list(TASKS.keys())}")
            task = copy.deepcopy(TASKS[tid])

        self._current_task = task
        self._task_id = tid

        self._state = State(
            current_task_id=tid,
            episode_step=0,
            checks_performed=[],
            violations_found=[],
            violation_paths=[],
            correct_violations=task["violations"],
            audit_log=[],
            score=0.17,
        )

        self._obs = Observation(
            task_id=tid,
            task_description=task["description"],
            netlist=task["netlist"],
            components=task["components"],
            available_checks=self.AVAILABLE_CHECKS,
            last_check_result=None,
            checks_performed=[],
            audit_log=[],
            violation_paths=[],
            step_count=0,
            max_steps=task.get("max_steps", 5),
            done=False,
        )
        return self._obs

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict]:
        # Clean up NoneTypes
        if getattr(action, "verdict", None) is None:
            action.verdict = ""
        if getattr(action, "target_nets", None) is None:
            action.target_nets = []
            
        obs, reward, done, info = self._step_internal(action)
        
        # Ensure strict boolean
        if isinstance(done, bool):
            done = bool(done)
            
        return obs, reward, done, info

    def _step_internal(self, action: Action) -> Tuple[Observation, Reward, bool, Dict]:
        if self._state is None:
            raise RuntimeError("Call reset() before step().")

        self._state.episode_step += 1
        done = False
        info: Dict[str, Any] = {}
        check = action.check_type

        if check not in self.AVAILABLE_CHECKS:
            reward = Reward(value=0.15, message=f"Invalid check type '{check}'.",
                            partial_credit=self._state.score, is_terminal=False)
            return self._build_obs(None), reward, False, info

        if check in self._state.checks_performed and check != "submit_verdict":
            msg = f"[REDUNDANT] '{check}' already performed. No new information."
            self._state.audit_log.append(msg)
            reward = Reward(value=0.15, message=msg,
                            partial_credit=self._state.score, is_terminal=False)
            return self._build_obs(msg), reward, False, info

        if check == "submit_verdict":
            done = True
            
            # Find faults on custom boards
            if self._state.current_task_id == "custom_task":
                # Use deterministic checks as ground truth
                expected_violations, expected_paths = self._run_all_diagnostics()
                expected = set(expected_violations)
                self._merge_found_violations(expected_violations, expected_paths)
                
                grade_score = 0.0
                msgs = []
                
                if len(self._state.checks_performed) > 0:
                    grade_score += 0.30
                    msgs.append(f"✓ Performed {len(self._state.checks_performed)} diagnostic checks.")
                
                # Check if verdict string mentions found faults
                verdict_text = (action.verdict or "").lower()
                identified_count = 0
                
                expected_types = {_violation_type(v) for v in expected}
                for violation_type in expected_types:
                    # Simplify the violation string to keywords (e.g., "SHORT_CIRCUIT:VCC->GND" -> "short")
                    if _verdict_mentions_type(verdict_text, violation_type):
                        identified_count += 1

                if len(expected_types) > 0:
                    accuracy = identified_count / len(expected_types)
                    grade_score += (0.70 * accuracy)
                    if accuracy == 1.0:
                        msgs.append(f"✓ Identified all {len(expected_types)} fault type(s).")
                    else:
                        msgs.append(f"✗ Missed faults. Identified {identified_count}/{len(expected_types)} type(s).")
                else:
                    # Check for false positive
                    hallucination_keywords = ["short", "voltage", "current", "overcurrent", "mismatch", "violation"]
                    if any(kw in verdict_text for kw in hallucination_keywords):
                        grade_score += 0.20  # Penalty for false positive
                        msgs.append("✗ False positive: violations reported on safe board.")
                    else:
                        grade_score += 0.70
                        msgs.append("✓ Safe board correctly identified.")
                
                grade_score = max(0.0, min(1.0, float(grade_score)))
                
                grade_msg = " | ".join(msgs)
                found = list(expected)
                
            # Standard grading for predefined tasks
            else:
                grade_score, grade_msg, found = run_grader(
                    task_id=self._state.current_task_id,
                    checks_performed=self._state.checks_performed,
                    violations_found=self._state.violations_found,
                    verdict=action.verdict or "",
                )

            self._state.score = grade_score
            self._state.audit_log.append(f"[VERDICT] {action.verdict}")
            self._state.audit_log.append(f"[SCORE] {grade_score:.2f} — {grade_msg}")
            info["final_score"] = grade_score
            info["score"] = grade_score
            info["grader_message"] = grade_msg
            reward = Reward(value=grade_score, message=grade_msg,
                            partial_credit=grade_score, is_terminal=True)
            return self._build_obs(grade_msg, done=True), reward, True, info

        self._state.checks_performed.append(check)
        check_result, new_violations, new_paths = self._run_check(check, action.target_nets)
        self._state.audit_log.append(f"[{check.upper()}]\n{check_result}")

        new_correct = [v for v in new_violations if v not in self._state.violations_found]
        self._state.violations_found.extend(new_correct)
        self._state.violation_paths.extend(new_paths)

        step_reward = 0.2 + 0.2 * len(new_correct)
        self._state.score = max(0.0, min(1.0, self._state.score + step_reward))

        if self._state.episode_step >= self._obs.max_steps:
            done = True
            safe_score = max(0.0, min(1.0, float(self._state.score)))
            info["final_score"] = safe_score
            info["score"] = safe_score
            info["grader_message"] = "Maximum steps reached."
            reward = Reward(value=0.0, message="Maximum steps reached without submitting verdict.",
                            partial_credit=safe_score, is_terminal=True)
            return self._build_obs(check_result, done=True), reward, True, info

        info["score"] = self._state.score
        info["final_score"] = self._state.score
        safe_step_reward = max(0.15, min(0.85, float(step_reward)))
        reward = Reward(
            value=safe_step_reward,
            message=f"'{check}' complete. {len(new_correct)} new violation(s) found.",
            partial_credit=self._state.score, is_terminal=False,
        )
        return self._build_obs(check_result), reward, done, info

    def state(self) -> State:
        if self._state is None:
            raise RuntimeError("Call reset() before state().")
        return self._state

    def _build_graph(self) -> Tuple[nx.MultiGraph, Dict]:
        G = nx.MultiGraph()
        components = {c["id"]: c for c in self._current_task["components"]}
        for conn in self._current_task["netlist"]:
            G.add_edge(conn["from"], conn["to"],
                       protection=conn.get("protection", True),
                       current_ma=float(conn.get("current_ma", 0.15)),
                       net=conn.get("net", ""),
                       source=conn["from"],
                       target=conn["to"])
        return G, components

    def _run_check(self, check_type: str, target_nets: Optional[List[str]]) -> Tuple[str, List[str], List[List[str]]]:
        G, components = self._build_graph()
        connections = self._filtered_connections(target_nets)
        found_violations = []
        found_paths: List[List[str]] = []
        result_lines = []

        if check_type == "check_voltage_mismatch":
            for conn in connections:
                for src, dst in ((conn["from"], conn["to"]), (conn["to"], conn["from"])):
                    src_v = _optional_float(components.get(src, {}).get("voltage"))
                    dst_v = _optional_float(components.get(dst, {}).get("max_input_voltage"))
                    if src_v is None or dst_v is None or src_v <= dst_v:
                        continue
                    violation = _format_voltage_mismatch(src, dst, src_v, dst_v)
                    if violation not in found_violations:
                        found_violations.append(violation)
                        found_paths.append([src, dst])
                        result_lines.append(
                            f"⚠ VIOLATION: {src} outputs {_fmt_number(src_v)}V → {dst} max input {_fmt_number(dst_v)}V"
                        )
            if not result_lines:
                result_lines.append("✓ No voltage mismatches detected.")

        elif check_type == "check_short_circuit":
            power_nodes = [
                n for n in G.nodes()
                if components.get(n, {}).get("type") == "POWER_SUPPLY"
                or any(p in n for p in ("VCC", "VMOT", "VINPUT", "V5V", "V3V3"))
            ]
            ground_nodes = [
                n for n in G.nodes()
                if components.get(n, {}).get("type") == "GROUND" or n == "GND"
            ]

            # BFS on unprotected subgraph
            unprotected_G = nx.Graph()
            for conn in connections:
                if not conn.get("protection", True):
                    unprotected_G.add_edge(conn["from"], conn["to"])

            for pwr in power_nodes:
                for gnd in ground_nodes:
                    try:
                        path = nx.shortest_path(unprotected_G, source=pwr, target=gnd)
                        violation = f"SHORT_CIRCUIT:{pwr}->{gnd}"
                        if violation not in found_violations:
                            found_violations.append(violation)
                            found_paths.append(path)
                            result_lines.append(
                                f"⚠ VIOLATION: Unprotected path {' → '.join(path)}"
                            )
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        continue

            if not result_lines:
                result_lines.append("✓ No short circuit paths detected.")

        elif check_type == "check_component_rating":
            for conn in connections:
                src = conn["from"]
                dst = conn["to"]
                current_ma = _optional_float(conn.get("current_ma"))
                dst_max_ma = _optional_float(components.get(dst, {}).get("max_current_ma"))
                if current_ma is None or dst_max_ma is None or current_ma <= dst_max_ma:
                    continue
                violation = _format_overcurrent(src, dst, current_ma, dst_max_ma)
                if violation not in found_violations:
                    found_violations.append(violation)
                    found_paths.append([src, dst])
                    result_lines.append(
                        f"⚠ VIOLATION: {src}→{dst} carries {_fmt_current(current_ma)}mA, rated {_fmt_current(dst_max_ma)}mA max"
                    )
            if not result_lines:
                result_lines.append("✓ All components within rated current limits.")

        elif check_type == "check_missing_decoupling":
            net_members = self._net_members(connections)
            mcus = [cid for cid, comp in components.items() if comp.get("type") in ["MICROCONTROLLER", "LOGIC_IC"]]
            for mcu in mcus:
                # A decoupling capacitor shares at least one non-ground net with the IC.
                has_cap = any(
                    mcu in members
                    and not _is_ground_net(net)
                    and any(components.get(node, {}).get("type") == "CAPACITOR" for node in members)
                    for net, members in net_members.items()
                )
                
                if not has_cap:
                    violation = f"MISSING_DECOUPLING:{mcu}"
                    if violation not in found_violations:
                        found_violations.append(violation)
                        found_paths.append([mcu])
                        result_lines.append(f"⚠ VIOLATION: {mcu} lacks a decoupling capacitor.")
            
            if not result_lines:
                result_lines.append("✓ All logic chips have proper decoupling capacitors.")

        return "\n".join(result_lines), found_violations, found_paths

    def _filtered_connections(self, target_nets: Optional[List[str]]) -> List[Dict[str, Any]]:
        connections = list(self._current_task["netlist"])
        if not target_nets:
            return connections
        wanted = {str(net).lower() for net in target_nets}
        return [conn for conn in connections if str(conn.get("net", "")).lower() in wanted]

    def _net_members(self, connections: Iterable[Dict[str, Any]]) -> Dict[str, set]:
        members: Dict[str, set] = defaultdict(set)
        for conn in connections:
            net = str(conn.get("net", "UNKNOWN_NET"))
            members[net].add(conn["from"])
            members[net].add(conn["to"])
        return members

    def _run_all_diagnostics(self) -> Tuple[List[str], List[List[str]]]:
        all_violations: List[str] = []
        all_paths: List[List[str]] = []
        for check in self.AVAILABLE_CHECKS:
            if check == "submit_verdict":
                continue
            _, violations, paths = self._run_check(check, None)
            for violation, path in zip(violations, paths):
                if violation not in all_violations:
                    all_violations.append(violation)
                    all_paths.append(path)
        return all_violations, all_paths

    def _merge_found_violations(self, violations: List[str], paths: List[List[str]]) -> None:
        for violation, path in zip(violations, paths):
            if violation not in self._state.violations_found:
                self._state.violations_found.append(violation)
                self._state.violation_paths.append(path)

    def _build_obs(self, check_result: Optional[str], done: bool = False) -> Observation:
        return Observation(
            task_id=self._state.current_task_id,
            task_description=self._current_task["description"],
            netlist=self._current_task["netlist"],
            components=self._current_task["components"],
            available_checks=self.AVAILABLE_CHECKS,
            last_check_result=check_result,
            checks_performed=list(self._state.checks_performed),
            audit_log=list(self._state.audit_log),
            violation_paths=list(self._state.violation_paths),
            step_count=self._state.episode_step,
            max_steps=self._obs.max_steps,
            done=done,
        )


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_number(value: float) -> str:
    number = float(value)
    if abs(number - round(number)) < 1e-9:
        return f"{number:.1f}"
    text = f"{number:.3f}".rstrip("0").rstrip(".")
    return text if "." in text else f"{text}.0"


def _format_voltage_mismatch(src: str, dst: str, src_v: float, dst_v: float) -> str:
    return f"VOLTAGE_MISMATCH:{src}->{dst}({_fmt_number(src_v)}V>{_fmt_number(dst_v)}V)"


def _format_overcurrent(src: str, dst: str, current_ma: float, dst_max_ma: float) -> str:
    return f"OVERCURRENT:{src}->{dst}({_fmt_current(current_ma)}mA>{_fmt_current(dst_max_ma)}mA)"


def _fmt_current(value: float) -> str:
    number = float(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return _fmt_number(number)


def _is_ground_net(net: str) -> bool:
    upper = net.upper()
    return "GND" in upper or "GROUND" in upper or upper in {"VSS", "0V"}


def _violation_type(violation: str) -> str:
    return violation.split(":", 1)[0].upper()


def _verdict_mentions_type(verdict_text: str, violation_type: str) -> bool:
    keywords = {
        "SHORT_CIRCUIT": ("short", "short circuit", "direct"),
        "VOLTAGE_MISMATCH": ("voltage", "overvoltage", "mismatch"),
        "OVERCURRENT": ("current", "overcurrent", "rating"),
        "MISSING_DECOUPLING": ("decoupling", "capacitor", "missing cap"),
    }
    return any(keyword in verdict_text for keyword in keywords.get(violation_type, (violation_type.lower(),)))
