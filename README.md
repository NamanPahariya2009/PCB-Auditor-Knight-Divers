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
[cite_start]**Lead Architect & Primary Developer:** Naman Pahariya [cite: 1, 3]  
[cite_start]**Technical Assistant:** Kapish Gupta [cite: 1, 3]  
**Status:** ALL SYSTEMS NOMINAL | [cite_start]Baseline: 1.00 [cite: 3, 23, 70]

> [cite_start]*"You don’t send a payload into orbit without checking the seals. You don’t send a PCB to manufacturing without running the Knight Divers audit."* [cite: 3]

---

## 👁️ The Pitch (Why This Matters)
[cite_start]Hardware engineers lose thousands of dollars and weeks of lead time due to simple oversights: a 9V line touching a 3.3V MCU, an unprotected short circuit, or a missing decoupling capacitor[cite: 3]. 

[cite_start]**PCB Auditor** is an industrial-grade, OpenEnv-compliant simulation where AI agents act as safety inspectors[cite: 3]. [cite_start]The environment parses real KiCad `.net` files, builds a mathematical topology of the circuit, and forces the agent to hunt down hidden hardware violations before authorizing the board for production[cite: 3, 20].

---

## 🌐 Non-Technical Quick Start (Zero Install)
You don't need to be a programmer to see the "Knight Divers" protocol in action. Access the industrial HUD directly through your web browser:

1.  [cite_start]**Launch the Command Center:** Open the [Live Hugging Face Space](https://huggingface.co/spaces/NamanPahariya2009/PCB-Auditor-Knight-Divers)[cite: 13, 31, 57].
2.  [cite_start]**Select a Mission:** Use the "Built-in Tasks" dropdown to choose a challenge like `task_industrial_mcu`[cite: 18, 19].
3.  [cite_start]**Deploy Audit:** Click **🚀 RUN AUDIT** to watch the BFS engine isolate short circuits and voltage mismatches in real-time[cite: 26, 30].
4.  [cite_start]**Analyze the Map:** View the **Topology Diagnostic Map** where violation paths are highlighted in Safety Orange[cite: 14, 15].

---

## ⚙️ The Arsenal (Core Capabilities)

* [cite_start]**True Deterministic Physics:** Short circuits aren't guessed; they are mathematically proven using a custom **NetworkX Breadth-First Search (BFS)** engine[cite: 3, 26, 29].
* [cite_start]**Industrial KiCad Parser:** Unlike basic environments, we natively parse **KiCad `.net` files** (S-expressions), extracting components, voltage ratings, and safety heuristics on the fly[cite: 3, 20, 68].
* [cite_start]**Dynamic UI / HUD:** A custom Gradio interface featuring a live diagnostic map and full audit logs for complete transparency[cite: 3, 58].
* [cite_start]**Advanced Heuristics:** The "Expert" task requires agents to detect missing decoupling capacitors on logic chips—a critical real-world engineering check[cite: 3, 19, 27].

### 🎯 The 4 Live-Fire Tasks
| Tier | Task ID | Difficulty | Violations | Max Steps |
|---|---|---|---|---|
| 🟢 | [cite_start]`task_voltage_mismatch` [cite: 17] | Easy | 1 | 5 |
| 🟡 | [cite_start]`task_multi_violation` [cite: 18] | Medium | 2 | 6 |
| 🟠 | [cite_start]`task_full_audit` [cite: 18] | Hard | 3 | 7 |
| 🔴 | [cite_start]`task_industrial_mcu` [cite: 19] | Expert | 3 | 8 |

---

## 🚀 Technical Setup (For Developers)

### Step 1: Secure the Blueprints
```bash
git clone [https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers.git](https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers.git)
cd PCB-Auditor-Knight-Divers