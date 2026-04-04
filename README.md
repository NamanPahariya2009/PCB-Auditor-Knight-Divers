---
title: PCB Auditor Knight Divers
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
tags: [openenv]
---

# ⚡ PCB AUDITOR: Protocol "Knight Divers"
**Team:** Naman Pahariya & Kapish Gupta
**Status:** ALL SYSTEMS NOMINAL | Baseline: 1.00

> "You don’t send a payload into orbit without checking the seals. You don’t send a PCB to manufacturing without running the Knight Divers audit."

---

## 👁️ The Pitch (Why This Matters)
Hardware engineers lose thousands of dollars and weeks of lead time due to simple oversights: a 9V line touching a 3.3V MCU, an unprotected short circuit, or a missing decoupling capacitor. 

**PCB Auditor** is an industrial-grade, OpenEnv-compliant simulation where AI agents act as safety inspectors. The environment parses real KiCad `.net` files, builds a mathematical topology of the circuit, and forces the agent to hunt down hidden hardware violations before authorizing the board for production.

---

## 🌐 Non-Technical Quick Start (Zero Install)
You don't need to be a programmer to see the "Knight Divers" protocol in action. Access our industrial HUD directly through your web browser:

1.  **Launch the Command Center:** Open the [Live Hugging Face Space](https://huggingface.co/spaces/NamanPahariya2009/PCB-Auditor-Knight-Divers).
2.  **Select a Mission:** Use the "Built-in Tasks" dropdown to choose a challenge like `task_industrial_mcu`.
3.  **Deploy Audit:** Click **🚀 RUN AUDIT** to watch the BFS engine isolate short circuits and voltage mismatches in real-time.
4.  **Analyze the Map:** View the **Topology Diagnostic Map** where violation paths are highlighted in Safety Orange.

---

## ⚙️ The Arsenal (Core Capabilities)

* **True Deterministic Physics:** Short circuits aren't guessed; they are mathematically proven using a custom **NetworkX Breadth-First Search (BFS)** engine.
* **Industrial KiCad Parser:** Unlike basic environments, we natively parse **KiCad `.net` files**, extracting components, voltage ratings, and safety heuristics on the fly.
* **Dynamic UI / HUD:** A custom Gradio interface featuring a live diagnostic map and full audit logs for complete transparency.
* **Advanced Heuristics:** The "Expert" task requires agents to detect missing decoupling capacitors—a critical real-world engineering check.

### 🎯 The 4 Live-Fire Tasks
| Tier | Task ID | Difficulty | Violations | Max Steps |
|---|---|---|---|---|
| 🟢 | `task_voltage_mismatch` | Easy | 1 | 5 |
| 🟡 | `task_multi_violation` | Medium | 2 | 6 |
| 🟠 | `task_full_audit` | Hard | 3 | 7 |
| 🔴 | `task_industrial_mcu` | Expert | 3 | 8 |

---

## 🚀 Technical Setup (For Developers)

### Step 1: Secure the Blueprints
```bash
git clone [https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers.git](https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers.git)
cd PCB-Auditor-Knight-Divers