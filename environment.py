"""
PCB Auditor Environment — OpenEnv Compliant
Knight Divers | Naman Pahariya & Kapish Gupta

Simulates a real-world PCB netlist safety audit task.
An AI agent receives a netlist, decides which checks to run,
and is scored on how accurately it identifies hardware violations.
"""

from __future__ import annotations
import random
import copy
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
    step_count: int = Field(default=0, description="Number of steps taken so far")
    max_steps: int = Field(default=5, description="Maximum steps allowed per episode")
    done: bool = Field(default=False, description="Whether the episode has ended")


class Action(BaseModel):
    """What the agent can do."""
    check_type: str = Field(
        description="Type of check to perform. One of: check_voltage_mismatch, check_short_circuit, check_component_rating, submit_verdict"
    )
    target_nets: Optional[List[str]] = Field(
        default=None,
        description="Specific nets/nodes to focus the check on (optional)"
    )
    verdict: Optional[str] = Field(
        default=None,
        description="Required when check_type='submit_verdict'. The agent's final finding."
    )


class Reward(BaseModel):
    """Reward signal for this step."""
    value: float = Field(description="Reward value for this step (0.0 to 1.0, can be negative)")
    message: str = Field(description="Human-readable explanation of the reward")
    partial_credit: float = Field(default=0.0, description="Partial progress score so far")
    is_terminal: bool = Field(default=False, description="Whether this reward ends the episode")


class State(BaseModel):
    """Full internal state (for debugging/logging)."""
    current_task_id: str
    episode_step: int
    checks_performed: List[str]
    violations_found: List[str]
    correct_violations: List[str]
    score: float


# ── ENVIRONMENT ───────────────────────────────────────────────

class PCBAuditorEnv:
    """
    PCB Netlist Safety Auditor — OpenEnv Environment

    The agent is given a PCB netlist and must identify hardware violations
    by choosing which safety checks to run, then submitting a final verdict.

    Reward structure:
    - +0.2 for each relevant check performed (encourages exploration)
    - +0.1 per correctly identified violation (partial credit)
    - +1.0 for a perfect final verdict (catches all violations, no false positives)
    - -0.1 for redundant checks (penalizes loops)
    - -0.3 for submitting a verdict that misses critical violations
    """

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
        """Reset the environment and return the initial observation."""
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
            correct_violations=task["violations"],
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
            step_count=0,
            max_steps=task.get("max_steps", 5),
            done=False,
        )
        return self._obs

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict]:
        """Execute one action and return (observation, reward, done, info)."""
        if self._state is None:
            raise RuntimeError("Call reset() before step().")

        self._state.episode_step += 1
        done = False
        info: Dict[str, Any] = {}

        check = action.check_type

        # ── INVALID ACTION ────────────────────────────────────
        if check not in self.AVAILABLE_CHECKS:
            reward = Reward(
                value=-0.1,
                message=f"Invalid check type '{check}'. Choose from: {self.AVAILABLE_CHECKS}",
                partial_credit=self._state.score,
                is_terminal=False,
            )
            return self._build_obs(None), reward, False, info

        # ── REDUNDANT CHECK PENALTY ───────────────────────────
        if check in self._state.checks_performed and check != "submit_verdict":
            reward = Reward(
                value=-0.1,
                message=f"Redundant check: '{check}' was already performed. No new information gained.",
                partial_credit=self._state.score,
                is_terminal=False,
            )
            return self._build_obs(f"[REDUNDANT] {check} already performed."), reward, False, info

        # ── SUBMIT VERDICT ────────────────────────────────────
        if check == "submit_verdict":
            done = True
            grade_score, grade_msg, found = run_grader(
                task_id=self._state.current_task_id,
                checks_performed=self._state.checks_performed,
                violations_found=self._state.violations_found,
                verdict=action.verdict or "",
            )
            self._state.score = grade_score
            info["final_score"] = grade_score
            info["grader_message"] = grade_msg

            terminal_reward = grade_score
            reward = Reward(
                value=terminal_reward,
                message=grade_msg,
                partial_credit=grade_score,
                is_terminal=True,
            )
            return self._build_obs(grade_msg, done=True), reward, True, info

        # ── RUN CHECK ─────────────────────────────────────────
        self._state.checks_performed.append(check)
        check_result, new_violations = self._run_check(check, action.target_nets)

        # Partial credit: +0.1 per new correct violation found
        new_correct = [v for v in new_violations if v not in self._state.violations_found]
        self._state.violations_found.extend(new_correct)

        step_reward = 0.2  # Base reward for running a meaningful check
        step_reward += 0.15 * len(new_correct)
        self._state.score = min(0.9, self._state.score + step_reward)

        # Check if max steps reached
        if self._state.episode_step >= self._obs.max_steps:
            done = True
            reward = Reward(
                value=0.0,
                message="Maximum steps reached without submitting verdict. Episode ended.",
                partial_credit=self._state.score,
                is_terminal=True,
            )
            return self._build_obs(check_result, done=True), reward, True, info

        reward = Reward(
            value=step_reward,
            message=f"Check '{check}' completed. Found {len(new_correct)} new violation(s). {check_result}",
            partial_credit=self._state.score,
            is_terminal=False,
        )
        return self._build_obs(check_result), reward, done, info

    def state(self) -> State:
        """Return the current internal state."""
        if self._state is None:
            raise RuntimeError("Call reset() before state().")
        return self._state

    # ── INTERNALS ─────────────────────────────────────────────

    def _run_check(self, check_type: str, target_nets: Optional[List[str]]) -> Tuple[str, List[str]]:
        """Run a specific check against the current task netlist."""
        task = self._current_task
        netlist = task["netlist"]
        components = {c["id"]: c for c in task["components"]}
        found_violations = []
        result_lines = []

        if check_type == "check_voltage_mismatch":
            for conn in netlist:
                src = conn.get("from")
                dst = conn.get("to")
                src_v = components.get(src, {}).get("voltage")
                dst_v = components.get(dst, {}).get("max_input_voltage")
                if src_v and dst_v and src_v > dst_v:
                    violation = f"VOLTAGE_MISMATCH:{src}->{dst}({src_v}V>{dst_v}V)"
                    found_violations.append(violation)
                    result_lines.append(
                        f"⚠ VIOLATION: {src} outputs {src_v}V but {dst} max input is {dst_v}V"
                    )
            if not result_lines:
                result_lines.append("✓ No voltage mismatches detected.")

        elif check_type == "check_short_circuit":
            # Find nets where VCC and GND connect with no protection
            net_map: Dict[str, List[str]] = {}
            for conn in netlist:
                net = conn.get("net", "NET_UNKNOWN")
                net_map.setdefault(net, [])
                net_map[net].append(conn.get("from"))
                net_map[net].append(conn.get("to"))

            for conn in netlist:
                src = conn.get("from", "")
                dst = conn.get("to", "")
                src_type = components.get(src, {}).get("type", "")
                dst_type = components.get(dst, {}).get("type", "")
                protection = conn.get("protection", True)

                if (("VCC" in src or "POWER" in src_type) and
                        ("GND" in dst or "GROUND" in dst_type) and
                        not protection):
                    violation = f"SHORT_CIRCUIT:{src}->{dst}"
                    found_violations.append(violation)
                    result_lines.append(
                        f"⚠ VIOLATION: Direct path from {src} to {dst} with no protection element."
                    )
            if not result_lines:
                result_lines.append("✓ No short circuit paths detected.")

        elif check_type == "check_component_rating":
            for conn in netlist:
                src = conn.get("from")
                dst = conn.get("to")
                current_ma = conn.get("current_ma", 0)
                dst_max_ma = components.get(dst, {}).get("max_current_ma")
                if dst_max_ma and current_ma > dst_max_ma:
                    violation = f"OVERCURRENT:{src}->{dst}({current_ma}mA>{dst_max_ma}mA)"
                    found_violations.append(violation)
                    result_lines.append(
                        f"⚠ VIOLATION: {src}->{dst} carries {current_ma}mA but {dst} rated for {dst_max_ma}mA max."
                    )
            if not result_lines:
                result_lines.append("✓ All components within rated current limits.")

        return "\n".join(result_lines), found_violations

    def _build_obs(self, check_result: Optional[str], done: bool = False) -> Observation:
        """Build the next observation from current state."""
        return Observation(
            task_id=self._state.current_task_id,
            task_description=self._current_task["description"],
            netlist=self._current_task["netlist"],
            components=self._current_task["components"],
            available_checks=self.AVAILABLE_CHECKS,
            last_check_result=check_result,
            checks_performed=list(self._state.checks_performed),
            step_count=self._state.episode_step,
            max_steps=self._obs.max_steps,
            done=done,
        )
