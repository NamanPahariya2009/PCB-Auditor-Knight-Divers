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

## 🚀 Setup & Usage

### Local Development

```bash
git clone https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers
cd PCB-Auditor-Knight-Divers
pip install -r requirements.txt
python server.py
# Visit http://localhost:7860
```

### API Usage (OpenEnv Spec)

```python
import requests

# Start episode
obs = requests.post("http://localhost:7860/reset", json={"task_id": "task_voltage_mismatch"}).json()

# Step: run a check
result = requests.post("http://localhost:7860/step", json={
    "check_type": "check_voltage_mismatch"
}).json()

# Step: submit verdict
result = requests.post("http://localhost:7860/step", json={
    "check_type": "submit_verdict",
    "verdict": "9V power rail connected to 3.3V MCU input — critical voltage mismatch."
}).json()

print(result["reward"]["value"])   # 0.0 - 1.0
```

### Docker

```bash
docker build -t pcb-auditor .
docker run -p 7860:7860 \
  -e HF_TOKEN=your_openrouter_key \
  -e MODEL_NAME=google/gemma-3-27b-it:free \
  pcb-auditor
```

---

## 📊 Baseline Inference

### Get a Free API Key

1. Go to [openrouter.ai](https://openrouter.ai) → Sign up (free)
2. Go to **Keys** → Create a new key
3. Copy the key — this is your `HF_TOKEN`

### Run Baseline

```bash
export HF_TOKEN=sk-or-v1-your-key-here
export MODEL_NAME=google/gemma-3-27b-it:free
export API_BASE_URL=https://openrouter.ai/api/v1

python inference.py
```

### Baseline Scores (google/gemma-3-27b-it:free)

| Task | Difficulty | Score |
|---|---|---|
| task_voltage_mismatch | Easy | 1.00 |
| task_multi_violation | Medium | 0.70 |
| task_full_audit | Hard | 0.55 |
| **Average** | | **0.75** |

---

## 📁 Project Structure

```
.
├── environment.py     # Core OpenEnv environment (Observation, Action, Reward, step/reset/state)
├── tasks.py           # 3 PCB tasks with deterministic graders
├── server.py          # FastAPI server + Gradio HUD
├── inference.py       # OpenAI-client baseline agent
├── openenv.yaml       # OpenEnv metadata spec
├── requirements.txt
├── Dockerfile
└── README.md
```

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