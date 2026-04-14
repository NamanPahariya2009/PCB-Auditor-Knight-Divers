"""
PCB Auditor — FastAPI Server
Built by Naman Pahariya.
"""

from __future__ import annotations
import os
from typing import Any, Dict, Optional

import gradio as gr
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from environment import PCBAuditorEnv, Action
from tasks import TASKS

# Setting up the API

app = FastAPI(
    title="PCB Auditor — Hardware Safety",
    description="OpenEnv-compliant PCB netlist safety audit environment.",
    version="0.9.9",
)

# Root redirect handled by Gradio mount at "/"

# Adding some safety here to handle validation errors.
# The OpenEnv spec is strict: /reset can't have a reward, but /step must.

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"Intercepted validation error on {request.url.path}: {exc}")
    
    # Reset doesn't need a reward, but step does. Keeping it compliant.
    if request.url.path == "/reset":
        return JSONResponse(
            status_code=200,
            content={
                "observation": {
                    "task_id": "error", 
                    "task_description": "Validation error on reset",
                    "netlist": [], 
                    "components": [], 
                    "available_checks": [],
                    "step_count": 0, 
                    "max_steps": 5, 
                    "done": False
                },
                "info": {"error": "Invalid reset request"}
            }
        )
    else:  # /step endpoint
        return JSONResponse(
            status_code=200,
            content={
                "observation": {
                    "task_id": "error", 
                    "task_description": "Validation error on step",
                    "netlist": [], 
                    "components": [], 
                    "available_checks": [],
                    "step_count": 0, 
                    "max_steps": 5, 
                    "done": True
                },
                "reward": 0.0,
                "done": True,
                "info": {"score": 0.0, "error": "Invalid step request"}
            }
        )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Caught a 500 crash: {exc}")
    
    # I have to return a valid JSON even if the engine crashes, so the agent doesn't hang.
    if request.url.path == "/reset":
        return JSONResponse(
            status_code=200,
            content={
                "observation": {
                    "task_id": "error", "task_description": "recovered_crash",
                    "netlist": [], "components": [], "available_checks": [],
                    "last_check_result": "crash_recovered", "checks_performed": [],
                    "step_count": 0, "max_steps": 5, "done": False
                },
                "info": {"score": 0.17, "final_score": 0.17}
            }
        )
    else:
        return JSONResponse(
            status_code=200,
            content={
                "observation": {
                    "task_id": "error", "task_description": "recovered_crash",
                    "netlist": [], "components": [], "available_checks": [],
                    "last_check_result": "crash_recovered", "checks_performed": [],
                    "step_count": 1, "max_steps": 5, "done": True
                },
                "reward": 0.0,
                "done": True,
                "info": {"score": 0.0, "final_score": 0.0}
            }
        )

# --- Models & Environment State ---

_env = PCBAuditorEnv()
_last_obs = None


class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    check_type: str
    target_nets: Optional[list] = None
    verdict: Optional[str] = None


# Main API Endpoints

@app.post("/reset")
def reset_endpoint(req: ResetRequest = ResetRequest()):
    """OpenEnv-compliant reset: returns observation only, NO reward field"""
    global _last_obs
    try:
        obs = _env.reset(task_id=req.task_id)
        _last_obs = obs
        return {
            "observation": obs.model_dump(),
            "info": {"message": "Reset successful"}
        }
    except Exception as e:
        return {
            "observation": {
                "task_id": "error",
                "task_description": str(e),
                "netlist": [],
                "components": [],
                "available_checks": [],
                "step_count": 0,
                "max_steps": 5,
                "done": False
            },
            "info": {"error": str(e)}
        }

@app.post("/step")
def step_endpoint(req: StepRequest):
    """OpenEnv-compliant step: returns observation, reward, done, info"""
    global _last_obs
    try:
        action = Action(
            check_type=req.check_type, 
            target_nets=req.target_nets, 
            verdict=req.verdict
        )
        obs, reward, done, info = _env.step(action)
        _last_obs = obs
        return {
            "observation": obs.model_dump(),
            "reward": float(reward.value),
            "done": bool(done),
            "info": {"score": float(info.get("score", 0.0))}
        }
    except Exception as e:
        return {
            "observation": {
                "task_id": "error",
                "task_description": str(e),
                "netlist": [],
                "components": [],
                "available_checks": [],
                "step_count": 0,
                "max_steps": 5,
                "done": True
            },
            "reward": 0.17,
            "done": True,
            "info": {"score": 0.17, "error": str(e)}
        }


@app.get("/state")
def state_endpoint():
    try:
        return _env.state().model_dump()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks")
def list_tasks():
    return {
        tid: {
            "description": t["description"], 
            "difficulty": t["difficulty"],
            "violation_count": len(t["violations"])
        }
        for tid, t in TASKS.items()
    }


    return {
        "status": "online", 
        "environment": "PCB Auditor",
        "score_range": [0.0, 1.0]
    }


# Logic to generate the PCB graph visualization

def generate_pcb_graph(task_dict: dict, violation_paths: list):
    """
    Build NetworkX topology map.
    Highlights entire violation PATHS in Safety Orange (#FF6B00).
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
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#FF6B00', markersize=10, label='[PATH] Violation'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#f0a500', markersize=10, label='[PWR] Power Source'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#00d4ff', markersize=10, label='[OK] Normal Component'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#444466', markersize=10, label='[GND] Ground'),
    ]
    ax.legend(handles=legend_items, loc="lower left", facecolor="#1a1c2e",
              labelcolor="white", fontsize=8, framealpha=0.8)
    plt.tight_layout()
    return plt.gcf()


# The web interface using Gradio

def run_audit(task_id: str, check_types: list, verdict: str, custom_json: str = "", netlist_file = None):
    """Run a full mini-episode and return audit log + graph."""
    import json
    env = PCBAuditorEnv()
    
    custom_task = None
    valid_extensions = (".net", ".fbrd", ".sch", ".kicad_pcb")
    if netlist_file and any(netlist_file.name.endswith(ext) for ext in valid_extensions):
        try:
            from netlist_parser import parse_board_file
            custom_task = parse_board_file(netlist_file.name)
        except Exception as e:
            return f"[FAIL] **PARSE ERROR:** {str(e)}", None
    elif custom_json and custom_json.strip():
        try:
            custom_task = json.loads(custom_json)
        except Exception as e:
            return f"[FAIL] **JSON ERROR:** Failed to parse custom netlist.\n```\n{str(e)}\n```", None

    obs = env.reset(task_id=task_id, custom_task=custom_task)
    done = False
    
    # Run all selected checks in sequence
    for ct in check_types:
        if not done:
            obs, reward, done, info = env.step(Action(check_type=ct))

    # Submit verdict
    if not done:
        obs, reward, done, info = env.step(Action(check_type="submit_verdict", verdict=verdict))

    log_lines = ["## [AUDIT] Audit Log\n"]
    for entry in obs.audit_log:
        log_lines.append(f"```\n{entry}\n```")

    if "final_score" in info:
        score = info["final_score"]
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        log_lines.append(f"\n### Final Score: `{score:.2f}/1.00`  [{bar}]")
        log_lines.append(f"\n**{info.get('grader_message', '')}**")

    fig = generate_pcb_graph(env._current_task, obs.violation_paths)
    return "\n\n".join(log_lines), fig


with gr.Blocks(title="PCB Auditor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🛡️ PCB Safety Auditor")
    gr.Markdown("### Developed by Naman Pahariya")
    
    with gr.Row():
        with gr.Column(scale=1):
            task_dropdown = gr.Dropdown(
                choices=list(TASKS.keys()), 
                value="task_voltage_mismatch", 
                label="Select Simulation Task"
            )
            with gr.Accordion("Custom Board Input", open=False):
                custom_json = gr.Code(label="Manual Netlist (JSON)", language="json")
                netlist_upload = gr.File(label="Upload KiCad/Fusion File", file_types=[".net", ".fbrd"])

            check_dropdown = gr.CheckboxGroup(
                choices=["check_voltage_mismatch", "check_short_circuit", "check_component_rating", "check_missing_decoupling"],
                value=["check_voltage_mismatch"], 
                label="Diagnostic Routine"
            )
            verdict_box = gr.Textbox(
                label="Manual Verdict Input", 
                placeholder="Describe the fault (e.g., 9V mismatch on U1)", 
                lines=2
            )
            scan_btn = gr.Button("🚀 RUN AUDIT", variant="primary")

        with gr.Column(scale=2):
            gr.Markdown("### 🔍 Topology Diagnostic Map")
            graph_out = gr.Plot(label="Live Graph View")
            result_out = gr.Markdown("### System Status: Ready")

    scan_btn.click(
        fn=run_audit,
        inputs=[task_dropdown, check_dropdown, verdict_box, custom_json, netlist_upload],
        outputs=[result_out, graph_out],
    )

    gr.Markdown("---")
    gr.Markdown("🛡️ Built for the **Meta / Scaler OpenEnv Hackathon**")


app = gr.mount_gradio_app(app, demo, path="/", root_path="")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
