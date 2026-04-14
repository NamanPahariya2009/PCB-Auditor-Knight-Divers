import importlib
import sys
import os
import yaml

# Add current directory to path
sys.path.append(os.getcwd())

def smoke_test():
    yaml_path = "openenv.yaml"
    if not os.path.exists(yaml_path):
        print(f"CRITICAL: {yaml_path} missing.")
        return

    with open(yaml_path, "r") as f:
        config = yaml.safe_load(f)

    tasks = config.get("tasks", [])
    if not tasks:
        print("CRITICAL: No tasks found in openenv.yaml.")
        return

    failures = 0
    for t in tasks:
        task_id = t.get("id", "UNKNOWN")
        gpath = t.get("grader", "MISSING")
        
        print(f"id={task_id} | grader={gpath}")
        
        if gpath == "MISSING":
            print("  -> CRASHED - validator gets 0.0 by default (MISSING key)")
            failures += 1
            continue
            
        try:
            if ":" not in gpath:
                raise ValueError("No colon in grader path")
                
            mod_name, cls_name = gpath.rsplit(":", 1)
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            # Stress test: pass multiple arguments and keywords
            score = cls().grade(None, extra_arg="fuzzer_test", dynamic_state={"step": 1})
            
            if score == 0.17:
                print("  -> 0.17 OK")
            else:
                print(f"  -> FAIL: Unexpected score {score}")
                failures += 1
        except Exception as e:
            print(f"  -> CRASHED - validator gets 0.0 by default ({type(e).__name__}: {e})")
            failures += 1

    if failures == 0:
        print("\nSUMMARY: ALL TASKS PASSED NATIVE VALIDATION TEST")
    else:
        print(f"\nSUMMARY: {failures} TASKS FAILED NATIVE VALIDATION")

if __name__ == "__main__":
    smoke_test()
