import os
from openai import OpenAI
from main import PCBAuditorEnv
from models import Action

def run_baseline():
    client = OpenAI(api_key=os.getenv("HF_TOKEN"), base_url=os.getenv("API_BASE_URL"))
    env = PCBAuditorEnv()
    obs = env.reset()
    
    # Simple logic to show the environment can be stepped through
    act = Action(check_type="Check_Voltage_Mismatch", target="All")
    new_obs, reward, done, info = env.step(act)
    print(f"Final Reward: {reward.value} | Msg: {reward.message}")

if __name__ == "__main__":
    run_baseline()