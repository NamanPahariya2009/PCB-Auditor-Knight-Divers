---
title: PCB Safety Auditor
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
tags: [openenv, reinforcement-learning, pcb-design]
---

# PCB Safety Auditor

PCB Safety Auditor is a deterministic Python environment for checking simplified PCB netlists for common electrical safety problems. It exposes the checker as an OpenEnv-style task environment, a FastAPI API, and a Gradio diagnostic UI.

The code is intentionally rule-based: it parses board/netlist files into structured components and nets, builds a NetworkX topology, and runs repeatable checks instead of asking an LLM to guess.

## What It Checks

- Voltage mismatches, such as a high-voltage supply feeding a low-voltage IC input.
- Short circuits, by searching unprotected power-to-ground paths.
- Overcurrent hazards, by comparing connection current against component ratings.
- Missing decoupling, by checking whether logic devices share a non-ground net with a capacitor.

## Project Structure

- `environment.py`: OpenEnv-style `PCBAuditorEnv`, observations, actions, rewards, and diagnostic checks.
- `netlist_parser.py`: KiCad/Fusion parser with S-expression handling, XML support, component inference, and net connection normalization.
- `tasks.py`: Built-in benchmark tasks and diagnostic-first grading.
- `server.py`: FastAPI endpoints plus the mounted Gradio UI.
- `inference.py`: OpenAI-compatible model loop for automated agent runs.
- `boards/`: Sample KiCad/Fusion board inputs.
- `tests/test_core.py`: Regression tests for parser behavior, task/check alignment, grading, and config.

## Supported Inputs

The parser accepts:

- KiCad exported netlists: `.net`
- KiCad board layouts: `.kicad_pcb`
- Autodesk Fusion/EAGLE-style XML board files: `.fbrd`
- Schematic XML files: `.sch`

Parsed custom boards are converted into the same task shape as built-in benchmark tasks:

```json
{
  "description": "Audit PCB netlist parsed from boards/example.net.",
  "components": [
    {
      "id": "U1",
      "type": "MICROCONTROLLER",
      "voltage": null,
      "max_input_voltage": 3.6,
      "max_current_ma": 500
    }
  ],
  "netlist": [
    {
      "from": "PWR1",
      "to": "U1",
      "net": "24V_RAIL",
      "current_ma": 500,
      "protection": true
    }
  ],
  "violations": []
}
```

## API

Run the server:

```bash
python server.py
```

The UI mounts at:

```text
http://localhost:7860
```

Available API endpoints:

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /tasks`
- `GET /health`

`/reset`, `/step`, and `/state` accept an optional `session_id` so concurrent callers do not share the same environment state.

Example:

```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d "{\"task_id\":\"task_full_audit\",\"session_id\":\"demo\"}"

curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d "{\"check_type\":\"check_voltage_mismatch\",\"session_id\":\"demo\"}"
```

## Local Setup

```bash
git clone https://github.com/NamanPahariya2009/PCB-Auditor-Knight-Divers.git
cd PCB-Auditor-Knight-Divers
pip install -r requirements.txt
python server.py
```

You can also use the installed console entry point after packaging:

```bash
server
```

## Docker

```bash
docker build -t pcb-auditor .
docker run -p 7860:7860 pcb-auditor
```

## Tests

Run the regression suite:

```bash
python -B -m unittest discover -s tests -v
```

The tests verify that:

- Built-in task declarations match actual diagnostic output.
- Parsed sample boards do not invent current faults.
- Known unsafe sample boards still detect voltage violations.
- Component inference correctly identifies common parts such as MCUs, sensors, relays, motors, and ground.
- `pyproject.toml` points to the working `server:main` entry point.

## Current Status

The project now favors correctness and reproducibility over presentation copy. The checker is still a heuristic safety auditor, not a replacement for professional PCB review or SPICE simulation, but its parser, diagnostics, grading, API config, and tests are aligned with the current implementation.

**Lead Engineer:** [Naman Pahariya](https://github.com/NamanPahariya2009)<br>
**License:** MIT
