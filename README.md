---
title: PCB Safety Auditor
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
tags: [openenv]
---

# PCB Safety Auditor (Knight Divers)
**Lead Engineer:** Naman Pahariya  
**Built for:** Meta / Scaler OpenEnv Hackathon  
**Baseline Score:** 1.00 (gemini-3-flash-preview)

## Why I built this
I build a lot of IoT stuff—RFID door locks, motor controllers, sensor boards. Turns out shorting 9V into a 3.3V MCU is a $15 mistake. I've made that mistake 6 times. This tool is basically my apology to my wallet.

Manual netlist checking is slow and prone to human error. For this hackathon, I built the PCB Safety Auditor to automate the process. Instead of just wrapping an LLM and asking it to guess if a circuit is safe, I built an OpenEnv-compliant environment that natively parses real KiCad (`.net`) and Autodesk Fusion (`.fbrd`) files, and then runs a deterministic NetworkX graph engine over the topology to mathematically prove faults. 

The AI agent has to actually synthesize the physical graph data to pass the tasks. If it hallucinates a short circuit on a safe board, my custom grader heavily penalizes it.

## Observation Space
The environment passes a JSON state of the board and audit history at each step:
```json
{
  "task_id": "string",
  "task_description": "string",
  "netlist": [{"from": "node_A", "to": "node_B", "protection": true}],
  "components": [{"id": "MCU1", "type": "MICROCONTROLLER", "max_input_voltage": 3.3}],
  "available_checks": ["list[str]"],
  "last_check_result": "string | null",
  "checks_performed": ["list[str]"],
  "audit_log": ["list[str]"],
  "step_count": "integer",
  "max_steps": "integer",
  "done": "boolean"
}
```

## Action Space
Agents interact by passing JSON actions to run diagnostic tools or submit verdicts:

```json
{
  "check_type": "enum", 
  "target_nets": ["list[str] | null"],
  "verdict": "string | null" 
}
```

Valid `check_types`:
- `check_voltage_mismatch`
- `check_short_circuit`
- `check_component_rating`
- `check_missing_decoupling`
- `submit_verdict` (Agent must supply a text verdict detailing the flaws found)

## Environment Tasks
The environment scales across 4 difficulties:

1. **`task_voltage_mismatch` (Easy)**: Find a 9V source destroying a 3.3V MCU. (Max 5 steps).
2. **`task_multi_violation` (Medium)**: Find a voltage mismatch AND a VCC-to-GND short. (Max 6 steps).
3. **`task_full_audit` (Hard)**: Full power management board audit. Find a short, a voltage mismatch, and an overcurrent fault. (Max 7 steps).
4. **`task_industrial_mcu` (Expert)**: Advanced heuristics. Find an overcurrent fault, a voltage mismatch, and a missing decoupling capacitor. (Max 8 steps).

## Setup & Deployment

### Local Run:
```bash
git clone https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers.git
cd PCB-Auditor-Knight-Divers
pip install -r requirements.txt
python server.py
```
UI mounts at `http://localhost:7860`

### Docker:
```bash
docker build -t pcb-auditor .
docker run -p 7860:7860 pcb-auditor
```

### Live Deployment:
Visit the live interactive deployment here:
[https://huggingface.co/spaces/NamanPahariya2009/PCB-Auditor-Knight-Divers](https://huggingface.co/spaces/NamanPahariya2009/PCB-Auditor-Knight-Divers)

Built for the Meta / Scaler OpenEnv Hackathon. 