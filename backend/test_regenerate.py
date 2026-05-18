import requests

def test_regenerate():
    url = "http://localhost:8000/api/v1/regenerate-segment"
    payload = {
        "sentence_id": "1",
        "text": "This is a test segment",
        "start_ms": 0,
        "end_ms": 1000,
        "original_file_url": None
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_regenerate()
