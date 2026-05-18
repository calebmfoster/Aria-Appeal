try:
    from fastapi.testclient import TestClient
    import httpx
    print("Imports successful")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
