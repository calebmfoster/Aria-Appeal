import requests
import time

API_URL = "http://localhost:8000/api/v1"

print("Triggering audio generation task...")
try:
    response = requests.post(f"{API_URL}/generate-audio", json={
        "text": "This is a test of the Qwen3 TTS system.",
        "emotion": "happy"
    })
    response.raise_for_status()
    data = response.json()
    task_id = data["task_id"]
    print(f"Task triggered successfully. Task ID: {task_id}")
except Exception as e:
    print(f"Failed to trigger task: {e}")
    if 'response' in locals() and hasattr(response, 'text'):
        print(f"Response: {response.text}")
    exit(1)

print("Polling for task completion...")
while True:
    try:
        res = requests.get(f"{API_URL}/generate-audio/{task_id}")
        res.raise_for_status()
        status_data = res.json()
        print(f"Status: {status_data['status']}")
        
        if status_data["status"] == "SUCCESS":
            print(f"Task completed successfully. Result: {status_data['result']}")
            break
        elif status_data["status"] == "FAILURE":
            print("Task failed.")
            break
            
        time.sleep(1.5)
    except Exception as e:
        print(f"Failed polling: {e}")
        break
