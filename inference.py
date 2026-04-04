"""
inference.py — PCB Auditor Baseline Inference Script
Knight Divers | Naman Pahariya & Kapish Gupta

COMPLIANCE: Meta PyTorch OpenEnv Hackathon
This script outputs strict [START], [STEP], and [END] tags for automated evaluation.

Run: python inference.py
"""

import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
from environment import PCBAuditorEnv, Action
from tasks import TASKS

API_BASE_URL = os.environ.get("API_BASE_URL", "https://openrouter.ai/api/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "google/gemini-3-flash-preview")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("HF_TOKEN", "")

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=OPENROUTER_API_KEY or "dummy-key",
)

SYSTEM_PROMPT = """You are an expert PCB hardware safety engineer.
You are given a PCB netlist and must identify dangerous violations before the board goes to manufacturing.

You have access to these checks (call ONE per turn):
- check_voltage_mismatch  : Find components receiving higher voltage than their rated input
- check_short_circuit     : Find unprotected direct paths between power and ground
- check_component_rating  : Find components carrying more current than their rated maximum
- check_missing_decoupling : Find MCUs and critical logic ICs missing a 100nF decoupling capacitor
- submit_verdict          : Submit your final audit verdict (do this last)

Respond ONLY as a JSON object:
{
  "check_type": "<check name or submit_verdict>",
  "verdict": "<required string when check_type is submit_verdict, empty string otherwise>"
}

CRITICAL INSTRUCTION FOR VERDICT:
To pass the safety audit, your verdict string MUST include:
1. Exact violation terms ("voltage mismatch", "short circuit", "overcurrent", "missing decoupling").
2. Exact numerical values ("9.0V", "3.3V", "750mA").
3. Exact component names and nets.
"""

def build_user_prompt(obs_dict: dict) -> str:
    return f"""TASK: {obs_dict['task_description']}
COMPONENTS: {json.dumps(obs_dict['components'])}
NETLIST: {json.dumps(obs_dict['netlist'])}
CHECKS PERFORMED: {obs_dict['checks_performed']}
LAST RESULT: {obs_dict['last_check_result'] or 'None'}
STEPS LEFT: {obs_dict['max_steps'] - obs_dict['step_count']}
Respond with JSON only."""

def run_agent_on_task(task_id: str) -> dict:
    env = PCBAuditorEnv()
    obs = env.reset(task_id=task_id)

    # REQUIRED COMPLIANCE TAG
    print(f"[START] Task: {task_id}")

    history = []
    final_score = 0.0
    final_message = ""
    steps_taken = 0

    for step_num in range(obs.max_steps):
        user_content = build_user_prompt(obs.model_dump())
        history.append({"role": "user", "content": user_content})

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
                temperature=0.1,
                max_tokens=256,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            history.append({"role": "assistant", "content": raw})
            
            action_data = json.loads(raw)
            action = Action(**action_data)

        except Exception as e:
            action = Action(check_type="submit_verdict", verdict="Audit failed due to format error.")

        obs, reward, done, info = env.step(action)
        steps_taken = step_num + 1

        # REQUIRED COMPLIANCE TAG
        print(f"[STEP] Action: {action.check_type} | Reward: {reward.value:.2f}")

        if done:
            final_score = info.get("final_score", reward.value)
            final_message = info.get("grader_message", reward.message)
            break

        time.sleep(0.5)

    # REQUIRED COMPLIANCE TAG
    print(f"[END] Final Score: {final_score:.2f}")

    return {
        "task_id": task_id,
        "difficulty": TASKS[task_id]["difficulty"],
        "final_score": final_score,
        "steps_taken": steps_taken,
        "grader_message": final_message,
    }

def main():
    print("Initializing Meta Hackathon Compliance Run...")
    results = []
    for task_id in list(TASKS.keys()):
        results.append(run_agent_on_task(task_id))
        time.sleep(1)

    # Save results to JSON for baseline proof
    avg = sum(r["final_score"] for r in results) / len(results) if results else 0.0
    with open("baseline_results.json", "w") as f:
        json.dump({"model": MODEL_NAME, "results": results, "average": avg}, f, indent=2)

if __name__ == "__main__":
    main()