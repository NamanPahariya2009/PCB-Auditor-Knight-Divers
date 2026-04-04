"""
PCB Auditor — FastAPI Server v2
Knight Divers | Naman Pahariya & Kapish Gupta

Upgrades:
- generate_pcb_graph now highlights full violation PATHS (edges + nodes) in Safety Orange
- Gradio result_out now renders full audit_log for transparency
"""

from __future__ import annotations
import os
from typing import Any, Dict, Optional

import gradio as gr
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from environment import PCBAuditorEnv, Action
from tasks import TASKS

# ── FASTAPI APP ───────────────────────────────────────────────

app = FastAPI(
    title="PCB Auditor — Knight Divers",
    description="OpenEnv-compliant PCB netlist safety audit environment.",
    version="2.0.0",
)

_env = PCBAuditorEnv()
_last_obs = None


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
        action = Action(check_type=req.check_type, target_nets=req.target_nets, verdict=req.verdict)
        obs, reward, done, info = _env.step(action)
        _last_obs = obs
        return {"observation": obs.model_dump(), "reward": reward.model_dump(), "done": done, "info": info}
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
        tid: {"description": t["description"], "difficulty": t["difficulty"],
              "violation_count": len(t["violations"])}
        for tid, t in TASKS.items()
    }


@app.get("/health")
def health():
    return {"status": "online", "environment": "PCB Auditor Knight Divers"}


# ── GRAPH GENERATOR ───────────────────────────────────────────

def generate_pcb_graph(task_dict: dict, violation_paths: list):
    """
    Build NetworkX topology map.
    Highlights entire violation PATHS in Safety Orange (#FF6B00)
    instead of just start/end nodes.
    """
    components = {c["id"]: c for c in task_dict["components"]}

    G = nx.DiGraph()
    for conn in task_dict["netlist"]:
        G.add_edge(conn["from"], conn["to"],
                   protection=conn.get("protection", True))

    # Build sets of violation nodes and edges from paths
    violation_nodes = set()
    violation_edges = set()
    for path in violation_paths:
        for node in path:
            violation_nodes.add(node)
        for i in range(len(path) - 1):
            violation_edges.add((path[i], path[i + 1]))

    plt.figure(figsize=(11, 6), facecolor="#0b0d17")
    ax = plt.gca()
    ax.set_facecolor("#0b0d17")

    pos = nx.spring_layout(G, seed=42, k=2.5)

    # Node colors
    node_colors = []
    for node in G.nodes():
        if node in violation_nodes:
            node_colors.append("#FF6B00")   # Safety Orange — violation
        elif "GND" in node:
            node_colors.append("#444466")   # Dark — ground
        elif components.get(node, {}).get("type") == "POWER_SUPPLY" or \
             any(p in node for p in ("VCC", "VMOT", "VINPUT", "V5V")):
            node_colors.append("#f0a500")   # Gold — power source
        else:
            node_colors.append("#00d4ff")   # Cyan — normal

    # Draw normal edges first
    normal_edges = [(u, v) for u, v in G.edges() if (u, v) not in violation_edges]
    violation_edge_list = [(u, v) for u, v in G.edges() if (u, v) in violation_edges]

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2200, ax=ax)
    nx.draw_networkx_labels(G, pos, font_color="white", font_size=8,
                            font_weight="bold", ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=normal_edges,
                           edge_color="#555577", arrows=True, arrowsize=18,
                           width=1.5, ax=ax)
    # Violation edges — thick Safety Orange
    if violation_edge_list:
        nx.draw_networkx_edges(G, pos, edgelist=violation_edge_list,
                               edge_color="#FF6B00", arrows=True, arrowsize=22,
                               width=3.5, ax=ax, style="dashed")

    ax.set_title(
        f"PCB TOPOLOGY — {task_dict.get('id', 'CUSTOM').upper().replace('_', ' ')}",
        color="white", fontsize=13, fontweight="bold", pad=12
    )

    legend_items = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#FF6B00', markersize=10, label='⚠ Violation Path'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#f0a500', markersize=10, label='⚡ Power Source'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#00d4ff', markersize=10, label='✓ Normal Component'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#444466', markersize=10, label='⏚ Ground'),
    ]
    ax.legend(handles=legend_items, loc="lower left", facecolor="#1a1c2e",
              labelcolor="white", fontsize=8, framealpha=0.8)
    plt.tight_layout()
    return plt.gcf()


# ── GRADIO HUD ────────────────────────────────────────────────

def run_audit(task_id: str, check_type: str, verdict: str, custom_json: str = ""):
    """Run a full mini-episode and return audit log + graph."""
    import json
    env = PCBAuditorEnv()
    
    custom_task = None
    if custom_json and custom_json.strip():
        try:
            custom_task = json.loads(custom_json)
        except Exception as e:
            return f"❌ **JSON ERROR:** Failed to parse custom netlist.\n```\n{str(e)}\n```", None

    obs = env.reset(task_id=task_id, custom_task=custom_task)

    # Step 1: run the requested check
    action = Action(check_type=check_type)
    obs, reward, done, info = env.step(action)

    # Step 2: submit verdict
    if not done:
        action2 = Action(check_type="submit_verdict", verdict=verdict)
        obs, reward, done, info = env.step(action2)

    # Build audit log display
    log_lines = ["## 🔍 Audit Log\n"]
    for entry in obs.audit_log:
        log_lines.append(f"```\n{entry}\n```")

    if "final_score" in info:
        score = info["final_score"]
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        log_lines.append(f"\n### Final Score: `{score:.2f}/1.00`  [{bar}]")
        log_lines.append(f"\n**{info.get('grader_message', '')}**")

    fig = generate_pcb_graph(env._current_task, obs.violation_paths)
    return "\n\n".join(log_lines), fig


with gr.Blocks() as hud:
    gr.Markdown("""
# ⚡ KNIGHT DIVERS — PCB Auditor
### OpenEnv-Compliant PCB Netlist Safety Validation Environment
*Naman Pahariya & Kapish Gupta*
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🛠️ Audit Control Panel")
            with gr.Tabs():
                with gr.Tab("Built-in Tasks"):
                    task_dropdown = gr.Dropdown(
                        choices=list(TASKS.keys()), value="task_voltage_mismatch", label="Select Task"
                    )
                with gr.Tab("Live Fire (Custom)"):
                    gr.Markdown("*Judges: Paste a custom JSON netlist here to test the deterministic engine on the fly.*")
                    custom_json = gr.Code(
                        language="json",
                        lines=5,
                        label="Custom Netlist JSON",
                        value='{\n  "description": "Custom Audit: Trace a path.",\n  "components": [\n    {"id": "VCC", "type": "POWER_SUPPLY", "voltage": 5.0},\n    {"id": "GND", "type": "GROUND", "voltage": 0.0}\n  ],\n  "netlist": [\n    {"from": "VCC", "to": "GND", "net": "SHORT_NET", "protection": false}\n  ],\n  "violations": ["SHORT_CIRCUIT:VCC->GND"]\n}'
                    )

            check_dropdown = gr.Dropdown(
                choices=["check_voltage_mismatch", "check_short_circuit", "check_component_rating", "check_missing_decoupling"],
                value="check_voltage_mismatch", label="Select Check Type"
            )
            verdict_box = gr.Textbox(
                label="Your Verdict (describe violations found)", placeholder="e.g. 9V source connected to 3.3V MCU", lines=3
            )
            scan_btn = gr.Button("🚀 RUN AUDIT", variant="primary")

        with gr.Column(scale=2):
            gr.Markdown("### 🖥️ Topology Diagnostic Map")
            graph_out = gr.Plot(label="PCB Netlist Topology")

    result_out = gr.Markdown("### 📡 Waiting for audit...")

    scan_btn.click(
        fn=run_audit,
        inputs=[task_dropdown, check_dropdown, verdict_box, custom_json],
        outputs=[result_out, graph_out],
    )

    gr.Markdown("""
---
**API Endpoints (OpenEnv Spec)**
- `POST /reset` — Start new episode
- `POST /step` — Execute action
- `GET /state` — Current environment state
- `GET /tasks` — List all available tasks
- `GET /health` — Health check
    """)


app = gr.mount_gradio_app(app, hud, path="/", root_path="")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)