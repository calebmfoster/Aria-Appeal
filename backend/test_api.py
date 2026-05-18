import requests
import time

api_url = "http://127.0.0.1:8000/api/v1"

print("Triggering generation...")
res = requests.post(
    f"{api_url}/generate-audio",
    json={"text": "Hello world from the script test.", "emotion": "", "voice_profile_id": None}
)
data = res.json()
print("Post Response:", data)
task_id = data.get("task_id")

while True:
    time.sleep(1)
    status_res = requests.get(f"{api_url}/generate-audio/{task_id}")
    status_data = status_res.json()
    print("Status:", status_data)
    if status_data.get("status") in ["SUCCESS", "FAILURE"]:
        break
