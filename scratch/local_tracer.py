import traceback, yaml, importlib, os, sys
sys.path.append(os.getcwd())

def run_trace():
    try:
        yaml_file = 'openenv.yaml'
        if not os.path.exists(yaml_file):
            print(f"ERROR: {yaml_file} not found")
            return
            
        with open(yaml_file, 'r') as f:
            d = yaml.safe_load(f)
            
        print('spec_version:', d.get('spec_version'))
        print('app:', d.get('app'))
        
        tasks = d.get('tasks', [])
        if not tasks:
            print("ERROR: No tasks found in openenv.yaml")
            return
            
        for t in tasks:
            gpath = t.get('grader', 'MISSING')
            print(f'id={t.get("id")} | grader={gpath}')
            try:
                mod, cls = str(gpath).rsplit(':', 1)
                mod_obj = importlib.import_module(mod)
                score = float(getattr(mod_obj, cls)().grade(None))
                print(f'  -> {score} {"OK" if 0 < score < 1 else "FAIL"}')
            except Exception as e:
                traceback.print_exc()
                print(f'  -> CRASHED - validator gets 0.0 by default')
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    run_trace()
