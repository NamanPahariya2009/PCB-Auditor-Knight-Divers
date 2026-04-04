#!/usr/bin/env python3
"""
test_deployment.py — Pre-deployment verification script
Knight Divers | Naman Pahariya & Kapish Gupta

Run this locally BEFORE pushing to verify:
1. All 4 tasks are defined
2. Netlist parser works on sample file
3. Environment runs without errors
4. Graders score correctly

Usage: python test_deployment.py
"""

import json
import sys

def test_tasks():
    """Verify all 4 tasks exist and have correct structure."""
    print("🔍 Testing task definitions...")
    from tasks import TASKS
    
    expected_tasks = [
        "task_voltage_mismatch",
        "task_multi_violation", 
        "task_full_audit",
        "task_industrial_mcu"
    ]
    
    for task_id in expected_tasks:
        if task_id not in TASKS:
            print(f"  ❌ FAIL: Missing task '{task_id}'")
            return False
        
        task = TASKS[task_id]
        required = ["description", "difficulty", "max_steps", "violations", "components", "netlist"]
        for field in required:
            if field not in task:
                print(f"  ❌ FAIL: Task '{task_id}' missing field '{field}'")
                return False
    
    print(f"  ✅ PASS: All {len(expected_tasks)} tasks defined correctly")
    return True


def test_netlist_parser():
    """Verify KiCad netlist parser works."""
    print("\n🔍 Testing netlist parser...")
    try:
        from netlist_parser import parse_kicad_netlist
        
        task = parse_kicad_netlist("sample_board.net")
        
        if len(task["components"]) == 0:
            print("  ❌ FAIL: Parser extracted 0 components")
            return False
        
        if len(task["netlist"]) == 0:
            print("  ❌ FAIL: Parser extracted 0 connections")
            return False
        
        # Check for expected components
        comp_ids = [c["id"] for c in task["components"]]
        if "U1" not in comp_ids or "VCC" not in comp_ids:
            print(f"  ❌ FAIL: Missing expected components. Found: {comp_ids}")
            return False
        
        # Check for voltage mismatch (VCC=9V → U1 MCU max=3.6V)
        vcc = next((c for c in task["components"] if c["id"] == "VCC"), None)
        u1 = next((c for c in task["components"] if c["id"] == "U1"), None)
        
        if vcc and vcc.get("voltage") != 9.0:
            print(f"  ❌ FAIL: VCC voltage should be 9.0, got {vcc.get('voltage')}")
            return False
        
        if u1 and u1.get("max_input_voltage") != 3.6:
            print(f"  ❌ FAIL: U1 max voltage should be 3.6, got {u1.get('max_input_voltage')}")
            return False
        
        print(f"  ✅ PASS: Parser extracted {len(task['components'])} components, {len(task['netlist'])} connections")
        return True
        
    except Exception as e:
        print(f"  ❌ FAIL: Parser error: {e}")
        return False


def test_environment():
    """Verify environment runs without errors."""
    print("\n🔍 Testing environment...")
    try:
        from environment import PCBAuditorEnv, Action
        
        env = PCBAuditorEnv()
        obs = env.reset(task_id="task_voltage_mismatch")
        
        if obs.task_id != "task_voltage_mismatch":
            print(f"  ❌ FAIL: Reset returned wrong task_id: {obs.task_id}")
            return False
        
        # Run a check
        action = Action(check_type="check_voltage_mismatch")
        obs, reward, done, info = env.step(action)
        
        if reward.value <= 0:
            print(f"  ❌ FAIL: Check returned non-positive reward: {reward.value}")
            return False
        
        # Submit verdict
        action = Action(check_type="submit_verdict", verdict="9V connected to 3.3V MCU")
        obs, reward, done, info = env.step(action)
        
        if not done:
            print("  ❌ FAIL: submit_verdict should end episode")
            return False
        
        if "final_score" not in info:
            print("  ❌ FAIL: No final_score in info")
            return False
        
        print(f"  ✅ PASS: Environment step/reset working. Final score: {info['final_score']:.2f}")
        return True
        
    except Exception as e:
        print(f"  ❌ FAIL: Environment error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graders():
    """Verify all 4 task graders work."""
    print("\n🔍 Testing graders...")
    from tasks import run_grader, TASKS
    
    test_cases = [
        {
            "task_id": "task_voltage_mismatch",
            "checks": ["check_voltage_mismatch"],
            "violations": ["VOLTAGE_MISMATCH:VCC_9V->MCU_U1(9.0V>3.3V)"],
            "verdict": "9V power connected to 3.3V MCU",
            "expected_min_score": 0.9
        },
        {
            "task_id": "task_industrial_mcu",
            "checks": ["check_voltage_mismatch", "check_component_rating", "check_missing_decoupling"],
            "violations": [
                "VOLTAGE_MISMATCH:VINPUT_24V->SENSOR_IC_U3(24.0V>5.0V)",
                "OVERCURRENT:REGULATOR_U1->MCU_U2(750mA>500mA)",
                "MISSING_DECOUPLING:MCU_U2"
            ],
            "verdict": "24V voltage mismatch on sensor, 750mA overcurrent on MCU, missing decoupling capacitor",
            "expected_min_score": 0.9
        }
    ]
    
    all_passed = True
    for tc in test_cases:
        score, msg, found = run_grader(
            task_id=tc["task_id"],
            checks_performed=tc["checks"],
            violations_found=tc["violations"],
            verdict=tc["verdict"]
        )
        
        if score < tc["expected_min_score"]:
            print(f"  ❌ FAIL: {tc['task_id']} scored {score:.2f}, expected >={tc['expected_min_score']}")
            print(f"     Grader message: {msg}")
            all_passed = False
        else:
            print(f"  ✅ PASS: {tc['task_id']} scored {score:.2f}")
    
    return all_passed


def main():
    print("="*60)
    print("  PCB AUDITOR — PRE-DEPLOYMENT TESTS")
    print("  Knight Divers | Naman & Kapish")
    print("="*60)
    
    results = {
        "Tasks": test_tasks(),
        "Parser": test_netlist_parser(),
        "Environment": test_environment(),
        "Graders": test_graders(),
    }
    
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<15} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎯 ALL TESTS PASSED — READY TO DEPLOY")
        print("\nNext steps:")
        print("  1. Copy all files from outputs/ to your repo")
        print("  2. Run: git add . && git commit -m 'v3: .net parser + 4th task'")
        print("  3. Run: git push origin main")
        print("  4. Wait 2-3 min for HF Space rebuild")
        print("  5. Verify at: https://huggingface.co/spaces/Jarvis217/PCB-Auditor-Knight-Divers")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED — FIX BEFORE DEPLOYING")
        return 1


if __name__ == "__main__":
    sys.exit(main())
