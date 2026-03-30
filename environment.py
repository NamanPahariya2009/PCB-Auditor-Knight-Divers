"""
PCB Auditor Environment — OpenEnv Compliant
Knight Divers | Naman Pahariya & Kapish Gupta

Upgrades v2:
- True BFS short circuit detection via NetworkX
- audit_log in Observation for full transparency
- violation_paths returned for full edge highlighting in graph
"""

from __future__ import annotations
import random
import copy
import networkx as nx
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from tasks import TASKS, run_grader


# ── TYPED MODELS (OpenEnv spec) ──────────────────────────────

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
    value: float = Field(description="Reward value for this step (0.0 to 1.0, can be negative)")
    message: str = Field(description="Human-readable explanation of the reward")
    partial_credit: float = Field(default=0.0)
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


# ── ENVIRONMENT ───────────────────────────────────────────────

class PCBAuditorEnv:
    AVAILABLE_CHECKS = [
        "check_voltage_mismatch",
        "check_short_circuit",
        "check_component_rating",
        "submit_verdict",
    ]

    def __init__(self, task_id: Optional[str] = None):
        self._task_id = task_id
        self._state: Optional[State] = None
        self._current_task: Optional[Dict] = None
        self._obs: Optional[Observation] = None

    def reset(self, task_id: Optional[str] = None) -> Observation:
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
            score=0.0,
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
        if self._state is None:
            raise RuntimeError("Call reset() before step().")

        self._state.episode_step += 1
        done = False
        info: Dict[str, Any] = {}
        check = action.check_type

        if check not in self.AVAILABLE_CHECKS:
            reward = Reward(value=-0.1, message=f"Invalid check type '{check}'.",
                            partial_credit=self._state.score, is_terminal=False)
            return self._build_obs(None), reward, False, info

        if check in self._state.checks_performed and check != "submit_verdict":
            msg = f"[REDUNDANT] '{check}' already performed. No new information."
            self._state.audit_log.append(msg)
            reward = Reward(value=-0.1, message=msg,
                            partial_credit=self._state.score, is_terminal=False)
            return self._build_obs(msg), reward, False, info

        if check == "submit_verdict":
            done = True
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

        step_reward = 0.2 + 0.15 * len(new_correct)
        self._state.score = min(0.9, self._state.score + step_reward)

        if self._state.episode_step >= self._obs.max_steps:
            done = True
            reward = Reward(value=0.0, message="Maximum steps reached without submitting verdict.",
                            partial_credit=self._state.score, is_terminal=True)
            return self._build_obs(check_result, done=True), reward, True, info

        reward = Reward(
            value=step_reward,
            message=f"'{check}' complete. {len(new_correct)} new violation(s) found.",
            partial_credit=self._state.score, is_terminal=False,
        )
        return self._build_obs(check_result), reward, done, info

    def state(self) -> State:
        if self._state is None:
            raise RuntimeError("Call reset() before state().")
        return self._state

    def _build_graph(self) -> Tuple[nx.DiGraph, Dict]:
        G = nx.DiGraph()
        components = {c["id"]: c for c in self._current_task["components"]}
        for conn in self._current_task["netlist"]:
            G.add_edge(conn["from"], conn["to"],
                       protection=conn.get("protection", True),
                       current_ma=conn.get("current_ma", 0),
                       net=conn.get("net", ""))
        return G, components

    def _run_check(self, check_type: str, target_nets: Optional[List[str]]) -> Tuple[str, List[str], List[List[str]]]:
        G, components = self._build_graph()
        found_violations = []
        found_paths: List[List[str]] = []
        result_lines = []

        if check_type == "check_voltage_mismatch":
            for src, dst, data in G.edges(data=True):
                src_v = components.get(src, {}).get("voltage")
                dst_v = components.get(dst, {}).get("max_input_voltage")
                if src_v and dst_v and src_v > dst_v:
                    violation = f"VOLTAGE_MISMATCH:{src}->{dst}({src_v}V>{dst_v}V)"
                    found_violations.append(violation)
                    found_paths.append([src, dst])
                    result_lines.append(f"⚠ VIOLATION: {src} outputs {src_v}V → {dst} max input {dst_v}V")
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

            # BFS on unprotected-only subgraph
            unprotected_G = nx.DiGraph()
            for src, dst, data in G.edges(data=True):
                if not data.get("protection", True):
                    unprotected_G.add_edge(src, dst)

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
            for src, dst, data in G.edges(data=True):
                current_ma = data.get("current_ma", 0)
                dst_max_ma = components.get(dst, {}).get("max_current_ma")
                if dst_max_ma and current_ma > dst_max_ma:
                    violation = f"OVERCURRENT:{src}->{dst}({current_ma}mA>{dst_max_ma}mA)"
                    found_violations.append(violation)
                    found_paths.append([src, dst])
                    result_lines.append(
                        f"⚠ VIOLATION: {src}→{dst} carries {current_ma}mA, rated {dst_max_ma}mA max"
                    )
            if not result_lines:
                result_lines.append("✓ All components within rated current limits.")

        return "\n".join(result_lines), found_violations, found_paths

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