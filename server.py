"""
PCB Auditor — FastAPI Server
Exposes OpenEnv-compliant HTTP endpoints: /reset, /step, /state
Also serves the Gradio HUD at /
"""

from __future__ import annotations
import os
from typing import Any, Dict, Optional

import gradio as gr
import networkx as nx
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — required for server environments
import matplotlib.pyplot as plt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from environment import PCBAuditorEnv, Action, Observation, Reward, State
from tasks import TASKS

# ── FASTAPI APP ───────────────────────────────────────────────

app = FastAPI(
    title="PCB Auditor — Knight Divers",
    description="OpenEnv-compliant PCB netlist safety audit environment.",
    version="1.0.0",
)

# One environment instance per server (single-agent use)
_env = PCBAuditorEnv()
_last_obs: Optional[Observation] = None


# ── REQUEST MODELS ────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    check_type: str
    target_nets: Optional[list] = None
    verdict: Optional[str] = None


# ── OPENENV ENDPOINTS ─────────────────────────────────────────

@app.post("/reset", response_model=Dict[str, Any])
def reset_endpoint(req: ResetRequest = ResetRequest()):
    global _last_obs
    try:
        obs = _env.reset(task_id=req.task_id)
        _last_obs = obs
        return obs.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=Dict[str, Any])
def step_endpoint(req: StepRequest):
    global _last_obs
    if _last_obs is None:
        raise HTTPException(status_code=400, detail="Call /reset first.")
    try:
        action = Action(
            check_type=req.check_type,
            target_nets=req.target_nets,
            verdict=req.verdict,
        )
        obs, reward, done, info = _env.step(action)
        _last_obs = obs
        return {
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state", response_model=Dict[str, Any])
def state_endpoint():
    try:
        return _env.state().model_dump()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks", response_model=Dict[str, Any])
def list_tasks():
    return {
        tid: {
            "description": t["description"],
            "difficulty": t["difficulty"],
            "violation_count": len(t["violations"]),
        }
        for tid, t in TASKS.items()
    }


@app.get("/health")
def health():
    return {"status": "online", "environment": "PCB Auditor Knight Divers"}


# ── GRADIO HUD ────────────────────────────────────────────────

def generate_pcb_graph(task_id: str, violations_found: list):
    """Generate NetworkX topology map with violations highlighted."""
    if task_id not in TASKS:
        return None

    task = TASKS[task_id]
    G = nx.DiGraph()
    components = {c["id"]: c for c in task["components"]}
    violation_nodes = set()

    for v in violations_found:
        parts = v.split(":")
        if len(parts) >= 2:
            nodes = parts[1].split("->")
            violation_nodes.update(n.split("(")[0] for n in nodes)

    for conn in task["netlist"]:
        G.add_edge(conn["from"], conn["to"], net=conn.get("net", ""))

    plt.figure(figsize=(11, 6), facecolor="#0b0d17")
    ax = plt.gca()
    ax.set_facecolor("#0b0d17")

    pos = nx.spring_layout(G, seed=42, k=2.5)

    node_colors = []
    for node in G.nodes():
        if node in violation_nodes:
            node_colors.append("#ff4b2b")
        elif "GND" in node:
            node_colors.append("#444466")
        elif "VCC" in node or "POWER" in components.get(node, {}).get("type", "") or "VINPUT" in node or "V5V" in node or "VMOT" in node:
            node_colors.append("#f0a500")
        else:
            node_colors.append("#00d4ff")

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2200, ax=ax)
    nx.draw_networkx_labels(G, pos, font_color="white", font_size=8, font_weight="bold", ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color="#555577", arrows=True,
                           arrowsize=20, width=1.5, ax=ax)

    ax.set_title(f"PCB TOPOLOGY — {task_id.upper().replace('_', ' ')}",
                 color="white", fontsize=13, fontweight="bold", pad=12)

    legend_items = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff4b2b', markersize=10, label='⚠ Violation Node'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#f0a500', markersize=10, label='⚡ Power Source'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#00d4ff', markersize=10, label='✓ Normal Component'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#444466', markersize=10, label='⏚ Ground'),
    ]
    ax.legend(handles=legend_items, loc="lower left", facecolor="#1a1c2e",
              labelcolor="white", fontsize=8, framealpha=0.8)

    plt.tight_layout()
    return plt.gcf()


def run_audit(task_id: str, check_type: str, verdict: str):
    """Gradio callback: runs a full mini-episode."""
    env = PCBAuditorEnv()
    obs = env.reset(task_id=task_id)

    results = []
    violations_found = []

    # Step 1: Run the requested check
    action = Action(check_type=check_type)
    obs, reward, done, info = env.step(action)
    results.append(f"**Step 1 — {check_type}**\n{obs.last_check_result}")
    violations_found = list(env.state().violations_found)

    # Step 2: Submit verdict
    if not done:
        action2 = Action(check_type="submit_verdict", verdict=verdict)
        obs2, reward2, done2, info2 = env.step(action2)
        results.append(f"\n**Final Verdict Score: {info2.get('final_score', 0.0):.2f}/1.00**")
        results.append(f"\n{info2.get('grader_message', '')}")
    
    fig = generate_pcb_graph(task_id, violations_found)
    return "\n\n".join(results), fig


with gr.Blocks() as hud:
    gr.Markdown("""
# ⚡ KNIGHT DIVERS — PCB Auditor
### OpenEnv-Compliant PCB Netlist Safety Validation Environment
*Naman Pahariya & Kapish Gupta*
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🛠️ Audit Control Panel")
            task_dropdown = gr.Dropdown(
                choices=list(TASKS.keys()),
                value="task_voltage_mismatch",
                label="Select Task",
            )
            check_dropdown = gr.Dropdown(
                choices=["check_voltage_mismatch", "check_short_circuit", "check_component_rating"],
                value="check_voltage_mismatch",
                label="Select Check Type",
            )
            verdict_box = gr.Textbox(
                label="Your Verdict (describe violations found)",
                placeholder="e.g. 9V source connected to 3.3V MCU, causing voltage mismatch",
                lines=3,
            )
            scan_btn = gr.Button("🚀 RUN AUDIT", variant="primary")

        with gr.Column(scale=2):
            gr.Markdown("### 🖥️ Topology Diagnostic Map")
            graph_out = gr.Plot(label="PCB Netlist Topology")

    with gr.Row():
        result_out = gr.Markdown("### 📡 Waiting for audit...")

    scan_btn.click(
        fn=run_audit,
        inputs=[task_dropdown, check_dropdown, verdict_box],
        outputs=[result_out, graph_out],
    )

    gr.Markdown("""
---
**API Endpoints (OpenEnv Spec)**
- `POST /reset` — Start new episode
- `POST /step` — Execute action
- `GET /state` — Current environment state
- `GET /tasks` — List all available tasks
    """)


# ── MOUNT GRADIO ON FASTAPI ───────────────────────────────────

app = gr.mount_gradio_app(app, hud, path="/", root_path="")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
