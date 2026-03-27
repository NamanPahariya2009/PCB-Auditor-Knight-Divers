from main import PCBAuditorEnv
from models import Action
import yaml

def run_audit():
    print("--- Stark Lab: Manual System Check ---")
    
    # 1. Check YAML
    try:
        with open("openenv.yaml", "r") as f:
            yaml.safe_load(f)
            print("✅ openenv.yaml: Format is Valid")
    except Exception as e:
        print(f"❌ YAML Error: {e}")

    # 2. Check Logic
    env = PCBAuditorEnv()
    
    # Test Hard Task (Voltage Mismatch)
    act = Action(check_type="Check_Voltage_Mismatch", target="All")
    obs, reward, done, info = env.step(act)
    
    if reward.value == 1.0:
        print(f"✅ Reward Logic: Working ({reward.message})")
        print("✅ ENVIRONMENT READY FOR SUBMISSION")
    else:
        print("❌ Logic Error: Reward not calculated correctly.")

if __name__ == "__main__":
    run_audit()