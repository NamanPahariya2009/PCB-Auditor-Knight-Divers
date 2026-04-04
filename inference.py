import os
import json
from openai import OpenAI
from environment import PCBEnv
from tasks import get_task_by_id

# 🛡️ BOX 2 & 3: Environment Variable Configuration
# Defaults are strictly allowed only for BASE_URL and MODEL_NAME
API_BASE_URL = os.getenv("API_BASE_URL", "https://api-inference.huggingface.co/v1/")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemini-2.0-flash-exp")

# NO default allowed for HF_TOKEN to ensure judge's secrets are used
HF_TOKEN = os.getenv("HF_TOKEN")

# 🛡️ BOX 4: OpenAI Client Initialization
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
)

def run_inference():
    # 🛡️ BOX 5: Mandatory Header
    print("[START]")

    # List of tasks to be audited by the Knight Divers protocol
    task_ids = ["task_voltage_mismatch", "task_multi_violation", "task_full_audit", "task_industrial_mcu"]
    
    for task_id in task_ids:
        task = get_task_by_id(task_id)
        env = PCBEnv(task)
        obs = env.reset()
        done = False
        step_count = 0

        while not done and step_count < task.max_steps:
            # 🛡️ BOX 5: Mandatory Step Counter
            print(f"[STEP] {step_count}")

            # Construct the prompt for the AI Auditor
            prompt = f"PCB Audit Mission: {task_id}\nObservation: {json.dumps(obs)}\nAction required (JSON format):"
            
            try:
                # LLM Call via the authorized client
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                # Extract and execute action
                action_data = json.loads(response.choices[0].message.content)
                obs, reward, done, info = env.step(action_data)
                
            except Exception as e:
                # Fallback if the LLM fails during live audit
                done = True

            step_count += 1

    # 🛡️ BOX 5: Mandatory Footer
    print("[END]")

if __name__ == "__main__":
    run_inference()