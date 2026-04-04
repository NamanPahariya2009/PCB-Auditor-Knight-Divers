#!/usr/bin/env python3
"""
verify_deployment.py — Post-deployment API health check
Knight Divers | Naman Pahariya & Kapish Gupta

Run this AFTER pushing to HF Spaces to verify the deployment is live.

Usage: python verify_deployment.py [--local]

Options:
  --local    Test against localhost:7860 instead of HF Space
"""

import requests
import json
import sys
import time

# Production URL (HF Space)
PROD_URL = "https://namanpahariya2009-pcb-auditor-knight-divers.hf.space"
LOCAL_URL = "http://localhost:7860"


def test_health(base_url: str) -> bool:
    """Test /health endpoint."""
    print(f"\n🔍 Testing /health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code != 200:
            print(f"  ❌ FAIL: Status {response.status_code}")
            return False
        
        data = response.json()
        if data.get("status") != "online":
            print(f"  ❌ FAIL: Status not 'online': {data}")
            return False
        
        print(f"  ✅ PASS: {data}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False


def test_tasks(base_url: str) -> bool:
    """Test /tasks endpoint."""
    print(f"\n🔍 Testing /tasks endpoint...")
    try:
        response = requests.get(f"{base_url}/tasks", timeout=10)
        if response.status_code != 200:
            print(f"  ❌ FAIL: Status {response.status_code}")
            return False
        
        tasks = response.json()
        expected = ["task_voltage_mismatch", "task_multi_violation", 
                    "task_full_audit", "task_industrial_mcu"]
        
        for task_id in expected:
            if task_id not in tasks:
                print(f"  ❌ FAIL: Missing task '{task_id}'")
                return False
        
        print(f"  ✅ PASS: All 4 tasks present")
        for task_id, meta in tasks.items():
            print(f"     • {task_id}: {meta['difficulty']} ({meta['violation_count']} violations)")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False


def test_reset_step(base_url: str) -> bool:
    """Test /reset and /step endpoints."""
    print(f"\n🔍 Testing /reset and /step...")
    try:
        # Reset
        response = requests.post(
            f"{base_url}/reset",
            json={"task_id": "task_voltage_mismatch"},
            timeout=10
        )
        if response.status_code != 200:
            print(f"  ❌ FAIL: /reset status {response.status_code}")
            return False
        
        obs = response.json()
        if obs["task_id"] != "task_voltage_mismatch":
            print(f"  ❌ FAIL: Wrong task_id: {obs['task_id']}")
            return False
        
        print(f"  ✅ PASS: /reset working")
        
        # Step
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "check_voltage_mismatch"},
            timeout=10
        )
        if response.status_code != 200:
            print(f"  ❌ FAIL: /step status {response.status_code}")
            return False
        
        result = response.json()
        if "observation" not in result or "reward" not in result:
            print(f"  ❌ FAIL: Missing observation/reward in response")
            return False
        
        print(f"  ✅ PASS: /step working (reward: {result['reward']['value']:.2f})")
        return True
        
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False


def test_full_episode(base_url: str) -> bool:
    """Run a complete episode on task_industrial_mcu (expert task)."""
    print(f"\n🔍 Testing full episode on expert task...")
    try:
        # Reset to expert task
        response = requests.post(
            f"{base_url}/reset",
            json={"task_id": "task_industrial_mcu"},
            timeout=10
        )
        obs = response.json()
        
        # Step 1: Check voltage
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "check_voltage_mismatch"},
            timeout=10
        )
        
        # Step 2: Check current
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "check_component_rating"},
            timeout=10
        )
        
        # Step 3: Check decoupling
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "check_missing_decoupling"},
            timeout=10
        )
        
        # Step 4: Submit verdict
        verdict = (
            "24V voltage mismatch on sensor IC (rated 5V max), "
            "750mA overcurrent on MCU (rated 500mA max), "
            "MCU missing decoupling capacitor"
        )
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "submit_verdict", "verdict": verdict},
            timeout=10
        )
        
        result = response.json()
        score = result.get("info", {}).get("final_score", 0.0)
        msg = result.get("info", {}).get("grader_message", "")
        
        if score < 0.9:
            print(f"  ❌ FAIL: Expert task scored {score:.2f} (expected >=0.9)")
            print(f"     Message: {msg}")
            return False
        
        print(f"  ✅ PASS: Expert task scored {score:.2f}")
        print(f"     {msg}")
        return True
        
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # Parse args
    base_url = LOCAL_URL if "--local" in sys.argv else PROD_URL
    
    print("="*60)
    print("  PCB AUDITOR — POST-DEPLOYMENT VERIFICATION")
    print("  Knight Divers | Naman & Kapish")
    print("="*60)
    print(f"  Target: {base_url}")
    print("="*60)
    
    if base_url == PROD_URL:
        print("\n⏳ Waiting 3 seconds for HF Space to wake up...")
        time.sleep(3)
    
    results = {
        "Health": test_health(base_url),
        "Tasks": test_tasks(base_url),
        "Reset/Step": test_reset_step(base_url),
        "Full Episode": test_full_episode(base_url),
    }
    
    print("\n" + "="*60)
    print("  VERIFICATION SUMMARY")
    print("="*60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<15} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 DEPLOYMENT VERIFIED — ALL SYSTEMS OPERATIONAL")
        print(f"\n✅ Space is live: {base_url}")
        print("✅ All 4 tasks working")
        print("✅ Expert task achieves high score")
        print("\n📝 Ready for hackathon submission!")
        return 0
    else:
        print("\n❌ DEPLOYMENT ISSUES DETECTED")
        print("\nTroubleshooting:")
        print("  1. Check HF Space build logs")
        print("  2. Verify all files were pushed correctly")
        print("  3. Check Dockerfile builds without errors")
        print("  4. Test locally with: python server.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
verify_deployment.py — Post-deployment API health check
Knight Divers | Naman Pahariya & Kapish Gupta

Run this AFTER pushing to HF Spaces to verify the deployment is live.

Usage: python verify_deployment.py [--local]

Options:
  --local    Test against localhost:7860 instead of HF Space
"""

import requests
import json
import sys
import time

# Production URL (HF Space)
PROD_URL = "https://jarvis217-pcb-auditor-knight-divers.hf.space"
LOCAL_URL = "http://localhost:7860"


def test_health(base_url: str) -> bool:
    """Test /health endpoint."""
    print(f"\n🔍 Testing /health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code != 200:
            print(f"  ❌ FAIL: Status {response.status_code}")
            return False
        
        data = response.json()
        if data.get("status") != "online":
            print(f"  ❌ FAIL: Status not 'online': {data}")
            return False
        
        print(f"  ✅ PASS: {data}")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False


def test_tasks(base_url: str) -> bool:
    """Test /tasks endpoint."""
    print(f"\n🔍 Testing /tasks endpoint...")
    try:
        response = requests.get(f"{base_url}/tasks", timeout=10)
        if response.status_code != 200:
            print(f"  ❌ FAIL: Status {response.status_code}")
            return False
        
        tasks = response.json()
        expected = ["task_voltage_mismatch", "task_multi_violation", 
                    "task_full_audit", "task_industrial_mcu"]
        
        for task_id in expected:
            if task_id not in tasks:
                print(f"  ❌ FAIL: Missing task '{task_id}'")
                return False
        
        print(f"  ✅ PASS: All 4 tasks present")
        for task_id, meta in tasks.items():
            print(f"     • {task_id}: {meta['difficulty']} ({meta['violation_count']} violations)")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False


def test_reset_step(base_url: str) -> bool:
    """Test /reset and /step endpoints."""
    print(f"\n🔍 Testing /reset and /step...")
    try:
        # Reset
        response = requests.post(
            f"{base_url}/reset",
            json={"task_id": "task_voltage_mismatch"},
            timeout=10
        )
        if response.status_code != 200:
            print(f"  ❌ FAIL: /reset status {response.status_code}")
            return False
        
        obs = response.json()
        if obs["task_id"] != "task_voltage_mismatch":
            print(f"  ❌ FAIL: Wrong task_id: {obs['task_id']}")
            return False
        
        print(f"  ✅ PASS: /reset working")
        
        # Step
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "check_voltage_mismatch"},
            timeout=10
        )
        if response.status_code != 200:
            print(f"  ❌ FAIL: /step status {response.status_code}")
            return False
        
        result = response.json()
        if "observation" not in result or "reward" not in result:
            print(f"  ❌ FAIL: Missing observation/reward in response")
            return False
        
        print(f"  ✅ PASS: /step working (reward: {result['reward']['value']:.2f})")
        return True
        
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False


def test_full_episode(base_url: str) -> bool:
    """Run a complete episode on task_industrial_mcu (expert task)."""
    print(f"\n🔍 Testing full episode on expert task...")
    try:
        # Reset to expert task
        response = requests.post(
            f"{base_url}/reset",
            json={"task_id": "task_industrial_mcu"},
            timeout=10
        )
        obs = response.json()
        
        # Step 1: Check voltage
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "check_voltage_mismatch"},
            timeout=10
        )
        
        # Step 2: Check current
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "check_component_rating"},
            timeout=10
        )
        
        # Step 3: Check decoupling
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "check_missing_decoupling"},
            timeout=10
        )
        
        # Step 4: Submit verdict
        verdict = (
            "24V voltage mismatch on sensor IC (rated 5V max), "
            "750mA overcurrent on MCU (rated 500mA max), "
            "MCU missing decoupling capacitor"
        )
        response = requests.post(
            f"{base_url}/step",
            json={"check_type": "submit_verdict", "verdict": verdict},
            timeout=10
        )
        
        result = response.json()
        score = result.get("info", {}).get("final_score", 0.0)
        msg = result.get("info", {}).get("grader_message", "")
        
        if score < 0.9:
            print(f"  ❌ FAIL: Expert task scored {score:.2f} (expected >=0.9)")
            print(f"     Message: {msg}")
            return False
        
        print(f"  ✅ PASS: Expert task scored {score:.2f}")
        print(f"     {msg}")
        return True
        
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # Parse args
    base_url = LOCAL_URL if "--local" in sys.argv else PROD_URL
    
    print("="*60)
    print("  PCB AUDITOR — POST-DEPLOYMENT VERIFICATION")
    print("  Knight Divers | Naman & Kapish")
    print("="*60)
    print(f"  Target: {base_url}")
    print("="*60)
    
    if base_url == PROD_URL:
        print("\n⏳ Waiting 3 seconds for HF Space to wake up...")
        time.sleep(3)
    
    results = {
        "Health": test_health(base_url),
        "Tasks": test_tasks(base_url),
        "Reset/Step": test_reset_step(base_url),
        "Full Episode": test_full_episode(base_url),
    }
    
    print("\n" + "="*60)
    print("  VERIFICATION SUMMARY")
    print("="*60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name:<15} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 DEPLOYMENT VERIFIED — ALL SYSTEMS OPERATIONAL")
        print(f"\n✅ Space is live: {base_url}")
        print("✅ All 4 tasks working")
        print("✅ Expert task achieves high score")
        print("\n📝 Ready for hackathon submission!")
        return 0
    else:
        print("\n❌ DEPLOYMENT ISSUES DETECTED")
        print("\nTroubleshooting:")
        print("  1. Check HF Space build logs")
        print("  2. Verify all files were pushed correctly")
        print("  3. Check Dockerfile builds without errors")
        print("  4. Test locally with: python server.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
