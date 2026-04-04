import os
import json
import time
import textwrap
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load local .env for credentials
load_dotenv()

# Project specific imports
from environment import PCBAuditorEnv, Action
from tasks import TASKS

# MANDATORY ENV VARS PER META SPEC
API_BASE_URL = os.getenv("API_BASE_URL") or "https://openrouter.ai/api/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "google/gemini-3-flash-preview"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENROUTER_API_KEY")
BENCHMARK = "pcb-auditor-knight-divers"

# Initialize Client
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "dummy-key")

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert PCB hardware safety engineer. Identify violations.
    Respond ONLY as a JSON object:
    {
      "check_type": "check_voltage_mismatch | check_short_circuit | check_component_rating | check_missing_decoupling | submit_verdict",
      "verdict": "Detailed string describing violations found (only if check_type is submit_verdict)"
    }
""").strip()

def run_task(task_id: str):
    env = PCBAuditorEnv()
    obs = env.reset(task_id=task_id)
    
    # 1. [START] line
    print(f"[START] task={task_id} env={BENCHMARK} model={MODEL_NAME}", flush=True)

    rewards = []
    steps_taken = 0
    score = 0.0
    success = False
    error = "null"

    for step in range(1, obs.max_steps + 1):
        prompt = f"TASK: {obs.task_description}\nCOMPONENTS: {obs.components}\nNETLIST: {obs.netlist}\nPREVIOUS: {obs.audit_log}"
        
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"}
            )
            raw_action = completion.choices[0].message.content
            action_dict = json.loads(raw_action)
            action = Action(**action_dict)
        except Exception as e:
            action = Action(check_type="submit_verdict", verdict="Format Error")
            error = str(e).replace("\n", " ")

        obs, reward_obj, done, info = env.step(action)
        
        step_reward = float(reward_obj.value)
        rewards.append(step_reward)
        steps_taken = step
        
        # 2. [STEP] line
        done_val = str(done).lower()
        print(f"[STEP] step={step} action={action.check_type} reward={step_reward:.2f} done={done_val} error={error}", flush=True)

        if done:
            score = info.get("final_score", 0.0)
            success = score >= 0.8
            break

    # 3. [END] line
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps_taken} score={score:.2f} rewards={rewards_str}", flush=True)

def main():
    # Loop through all 4 of your tasks
    for task_id in TASKS.keys():
        run_task(task_id)

if __name__ == "__main__":
    main()