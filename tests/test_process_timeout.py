import time
import concurrent.futures
import subprocess
import pytest

def boot_vm(vm_id):
    start_time = time.time()
    try:
        result = subprocess.run(
            ["python3", "-c", "import time; time.sleep(0.1); print('ready')"],
            capture_output=True,
            text=True,
            timeout=0.05
        )
        return {"vm_id": vm_id, "status": "Success", "boot_time": round(time.time() - start_time, 2)}
    except subprocess.TimeoutExpired:
        return {"vm_id": vm_id, "status": "Failed", "error": "Timeout"}
    except Exception as e:
        return {"vm_id": vm_id, "status": "Failed", "error": str(e)}

def test_concurrent_timeouts():
    success_count = 0
    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(boot_vm, range(1, 11))
        for res in results:
            if res["status"] == "Success":
                success_count += 1
            else:
                errors += 1
    assert success_count == 0
    assert errors == 10
