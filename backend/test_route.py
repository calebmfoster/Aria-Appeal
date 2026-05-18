from app.worker import generate_audio_task
import time

print("Sending task to Celery...")
task = generate_audio_task.delay(text="This is a test segment.")
print(f"Task ID: {task.id}")

while not task.ready():
    print("Waiting for task to finish...")
    time.sleep(1)

print(f"Task status: {task.status}")
print(f"Task result: {task.result}")
