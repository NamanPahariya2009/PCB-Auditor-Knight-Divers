---
title: PCB Safety Auditor
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
tags: [openenv, reinforcement-learning, pcb-design]
---

# 🛡️ PCB Safety Auditor
**Lead Engineer:** [Naman Pahariya](https://github.com/NamanPahariya2009)  
**Baseline Score:** 1.00 (Expertly Audited)  
**Status:** Solo-Authored Portfolio Piece

---

## ⚡ The Motivation: My Apology to my Wallet
Building IoT hardware—RFID locks, motor controllers, and sensor clusters—is a thrill, until it isn't. Turns out, shorting a 9V motor rail into a 3.3V MCU is a $15 mistake that takes two weeks to arrive from FedEx. I've made that mistake exactly 6 times.

I built the **PCB Safety Auditor** because manual netlist checking is slow and human error is expensive. I wanted a way to mathematically prove a board is safe before I hit "Order" in KiCad.

## 🧠 The Brain: Graph-Theory vs. Guesswork
Most "AI Audits" today just wrap an LLM and ask it to guess if a circuit is safe. **I didn't want a guess; I wanted a proof.**

My engine natively parses real KiCad (`.net`) and Autodesk Fusion (`.fbrd`) files and synthesizes them into a **Directed Multi-Graph** using `NetworkX`. Instead of pattern matching, the auditor runs real physics-based heuristics and pathfinding algorithms to find:
- **Voltage Mismatches**: Detecting high-voltage rails hitting low-voltage logic pins.
- **Short Circuits**: Finding unprotected paths between power and ground.
- **Overcurrent Hazards**: Verifying if component ratings can handle the estimated current.
- **Missing Decoupling**: Identifying bypass capacitors where noise could be fatal.

---

## 🏗️ The Simulation Environment
Built on top of the **Meta OpenEnv** framework, this project provides a standardized Reinforcement Learning environment for hardware safety agents.

### 🔍 Observation Space
The agent receives a full JSON state of the physical board topology:
```json
{
  "task_description": "Identify 9V mismatch on MCU_U1",
  "netlist": [{"from": "VCC_9V", "to": "MCU_U1", "protection": true}],
  "available_checks": ["check_voltage_mismatch", "check_short_circuit"]
}
```

### 🛠️ Action Space
Agents can run diagnostic routines or submit final verdicts:
- `check_voltage_mismatch`: Runs the physics engine to find mismatched potentials.
- `check_short_circuit`: Executes BFS pathfinding to find VCC-to-GND shorts.
- `submit_verdict`: Formulates a natural language report of the audit findings.

---

## 🚀 Getting Started

### Local Setup
```bash
git clone https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers.git
pip install -r requirements.txt
python server.py
```
The professional diagnostic UI will mount at `http://localhost:7860`.

### Docker (Production-Ready)
```bash
docker build -t pcb-auditor .
docker run -p 7860:7860 pcb-auditor
```

---

## 🏆 Hackathon Context
This project was originally built for the **Meta / Scaler OpenEnv Hackathon**. While the competitive phase is over, I have since refactored it into a high-fidelity learning environment with a full 0.0-1.0 reward gradient for subsequent RL research.

**Lead Architect:** Naman Pahariya  
**License:** MIT