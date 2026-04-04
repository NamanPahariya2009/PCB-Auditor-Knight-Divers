---
title: PCB Auditor Knight Divers
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# ⚡ PCB Auditor — Knight Divers

**An OpenEnv-compliant real-world environment for training AI agents to audit PCB netlists for hardware safety violations.**

> Built for the OpenEnv Hackathon | Team: Naman Pahariya & Kapish Gupta

---

## 🔍 What Is This?

PCB engineers spend hours manually checking netlists for dangerous violations before a board goes to manufacturing. A single missed error — like a 9V source connected to a 3.3V microcontroller — can destroy thousands of dollars of hardware or cause fires.

This environment simulates that real audit task. An AI agent receives a PCB netlist, chooses which safety checks to run, and must identify all violations before submitting a final verdict.

---

## 🏗️ Environment Description

The agent interacts with a PCB netlist through a Gymnasium-style API. Each episode presents the agent with a circuit containing hidden violations. The agent must:

1. Choose which safety checks to run (`check_voltage_mismatch`, `check_short_circuit`, `check_component_rating`)
2. Interpret the check results
3. Submit a final verdict describing all violations found

The environment rewards thoroughness, penalizes redundancy, and scores the final verdict on accuracy.

---

## 🎯 Tasks

| Task ID | Difficulty | Violations | Max Steps | Description |
|---|---|---|---|---|
| `task_voltage_mismatch` | Easy | 1 | 5 | Single 9V→3.3V MCU voltage mismatch |
| `task_multi_violation` | Medium | 2 | 6 | Voltage mismatch + unprotected short circuit on motor driver board |
| `task_full_audit` | Hard | 3 | 7 | All 3 violation types on a complex power management PCB |

---

## 🎮 Action Space

```python
Action(
    check_type: str,        # One of: check_voltage_mismatch | check_short_circuit | check_component_rating | submit_verdict
    target_nets: list[str], # Optional: specific nets to focus on
    verdict: str,           # Required when check_type == "submit_verdict"
)
```

## 👁️ Observation Space

```python
Observation(
    task_id: str,
    task_description: str,
    netlist: list[dict],         # PCB connections with current, protection info
    components: list[dict],      # Component specs: voltage, current ratings
    available_checks: list[str],
    last_check_result: str,      # Result of last check performed
    checks_performed: list[str],
    step_count: int,
    max_steps: int,
    done: bool,
)
```

## 🏆 Reward Function

| Event | Reward |
|---|---|
| Meaningful check performed | +0.20 |
| New violation correctly identified | +0.15 |
| Perfect final verdict (all violations, no false positives) | +1.00 |
| Redundant check (already performed) | -0.10 |
| Verdict submitted missing critical violations | -0.30 |

The reward function provides **dense partial progress signals** throughout the episode — not just binary end-of-episode scoring.

---

## 🚀 Running Locally

### Prerequisites

| Requirement | Version | Check |
|---|---|---|
| **Python** | 3.10 or newer | `python --version` |
| **pip** | any recent | `pip --version` |
| **Git** | any | `git --version` |
| **Docker** *(optional)* | 20+ | `docker --version` |

> **Note:** The Gradio UI and FastAPI server run entirely on Python — no Node.js or frontend build step is needed.

### Step 1 — Clone the Repository

```bash
git clone https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers.git
cd PCB-Auditor-Knight-Divers
```

### Step 2 — Create a Virtual Environment

Creating a virtual environment keeps your system Python clean.

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> If you get a script-execution error, run:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` and try again.

</details>

<details>
<summary><strong>Windows (Command Prompt)</strong></summary>

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

</details>

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
python3 -m venv venv
source venv/bin/activate
```

</details>

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---|---|
| `fastapi` + `uvicorn` | REST API server |
| `gradio` | Interactive web UI (HUD) |
| `pydantic` | Typed models for observation/action/reward |
| `networkx` + `matplotlib` | PCB graph generation & visualization |
| `openai` | LLM client for baseline inference |
| `requests` | HTTP calls inside inference script |
| `numpy` | Numerical support |
| `pyyaml` | YAML config parsing |

### Step 4 — Start the Server

```bash
python server.py
```

You should see output like:

```
INFO:     Uvicorn running on http://0.0.0.0:7860
```

Open **http://localhost:7860** in your browser to access the Gradio HUD.

### Step 5 — Use the Gradio HUD

1. **Select a Task** from the dropdown (e.g. `task_voltage_mismatch`)
2. **Select a Check Type** (e.g. `check_voltage_mismatch`)
3. **Write a Verdict** describing the violations you expect
4. Click **🚀 RUN AUDIT**
5. View the **Audit Log** and **PCB Topology Graph** with violation paths highlighted in orange

---

## 🐳 Running with Docker

If you prefer Docker, no Python setup is needed on your host machine.

```bash
# Build the image
docker build -t pcb-auditor .

# Run the container
docker run -p 7860:7860 pcb-auditor
```

Then open **http://localhost:7860**.

To run inference inside the container, pass your API key:

```bash
docker run -p 7860:7860 \
  -e HF_TOKEN=your_openrouter_key \
  -e MODEL_NAME=google/gemma-3-27b-it:free \
  -e API_BASE_URL=https://openrouter.ai/api/v1 \
  pcb-auditor
```

---

## 🤖 Running Baseline Inference

The `inference.py` script uses an LLM to automatically audit all 3 tasks and reports scores.

### 1. Get an OpenRouter API Key

1. Go to [openrouter.ai](https://openrouter.ai) → Sign up
2. Go to **Keys** → Create a new key
3. Copy the key — this is your `OPENROUTER_API_KEY`

### 2. Set Environment Variables

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
$env:OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
$env:MODEL_NAME = "google/gemini-3-flash-preview"
$env:API_BASE_URL = "https://openrouter.ai/api/v1"
```

</details>

<details>
<summary><strong>Windows (Command Prompt)</strong></summary>

```cmd
set OPENROUTER_API_KEY=sk-or-v1-your-key-here
set MODEL_NAME=google/gemini-3-flash-preview
set API_BASE_URL=https://openrouter.ai/api/v1"
```

</details>

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
export OPENROUTER_API_KEY=sk-or-v1-your-key-here
export MODEL_NAME=google/gemini-3-flash-preview
export API_BASE_URL=https://openrouter.ai/api/v1"
```

</details>

### 3. Run

```bash
python inference.py
```

Results are saved to `baseline_results.json`.

### Baseline Scores (google/gemma-3-27b-it:free)

| Task | Difficulty | Score |
|---|---|---|
| task_voltage_mismatch | Easy | 1.00 |
| task_multi_violation | Medium | 0.70 |
| task_full_audit | Hard | 0.55 |
| **Average** | | **0.75** |

---

## 🔌 API Endpoints (OpenEnv Spec)

All endpoints are available at `http://localhost:7860` once the server is running.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reset` | Start a new episode (optionally pass `{"task_id": "..."}`) |
| `POST` | `/step` | Execute an action (`check_type`, `target_nets`, `verdict`) |
| `GET` | `/state` | Get current environment state |
| `GET` | `/tasks` | List all available tasks with metadata |
| `GET` | `/health` | Health check |

### Example: Full Episode via API

```python
import requests

BASE = "http://localhost:7860"

# 1. Reset — start a new episode
obs = requests.post(f"{BASE}/reset", json={"task_id": "task_voltage_mismatch"}).json()
print("Task:", obs["task_description"])

# 2. Step — run a safety check
result = requests.post(f"{BASE}/step", json={
    "check_type": "check_voltage_mismatch"
}).json()
print("Check result:", result["observation"]["last_check_result"])

# 3. Step — submit final verdict
result = requests.post(f"{BASE}/step", json={
    "check_type": "submit_verdict",
    "verdict": "9V power rail connected to 3.3V MCU input — critical voltage mismatch."
}).json()
print("Score:", result["reward"]["value"])   # 0.0 – 1.0
print("Message:", result["reward"]["message"])
```

---

## 📁 Project Structure

```
.
├── environment.py     # Core OpenEnv environment (Observation, Action, Reward, step/reset/state)
├── tasks.py           # 3 PCB tasks with deterministic graders
├── server.py          # FastAPI server + Gradio HUD
├── inference.py       # OpenAI-client baseline agent
├── openenv.yaml       # OpenEnv metadata spec
├── requirements.txt   # Python dependencies
├── Dockerfile         # Docker image definition
└── README.md          # This file
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `python` not found | Use `python3` instead (macOS/Linux), or add Python to your system PATH |
| `pip install` fails on Windows | Try `python -m pip install -r requirements.txt` |
| Port 7860 already in use | Kill the process using port 7860, or edit `server.py` to change the port |
| PowerShell blocks `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError` | Make sure your virtual environment is activated before running |
| Inference returns dummy results | Set `HF_TOKEN` to a valid OpenRouter API key |
| Docker build fails | Ensure Docker Desktop is running and you have internet access |

---

## 🔬 Why This Environment Matters

- **Real-world domain**: PCB netlist auditing is a genuine task done by engineers every day
- **Scalable**: New tasks can be added by adding entries to `tasks.py` — no code changes needed
- **Dense rewards**: Partial credit at every step makes it trainable with policy gradient methods
- **Deterministic graders**: Reproducible scoring, no LLM-as-judge ambiguity
- **Deployable**: Full Docker + Hugging Face Spaces support

---

## 📜 License

BSD-3-Clause