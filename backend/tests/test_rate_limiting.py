import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import limiter, get_db

async def override_get_db():
    class MockSession:
        async def execute(self, *args, **kwargs):
            class MockResult:
                def scalars(self):
                    class MockScalars:
                        def first(self):
                            return None
                    return MockScalars()
            return MockResult()
        async def add(self, *args, **kwargs): pass
        async def commit(self, *args, **kwargs): pass
        async def refresh(self, *args, **kwargs): pass
    yield MockSession()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_rate_limit_register():
    # Clear limiter state for the test
    limiter.reset()
    
    # Send 6 requests, limit is 5/minute
    for _ in range(5):
        res = client.post(
            "/api/v1/auth/register",
            json={"email": "rl@example.com", "password": "pass", "name": "Test"}
        )
        # We don't care if it's 400 or 200, just that it's not 429 yet
        assert res.status_code != 429

    # The 6th request should hit the 429 RateLimitExceeded
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "rl2@example.com", "password": "pass", "name": "Test"}
    )
    
    assert response.status_code == 429
    assert "error" in response.json()
    assert "Rate limit exceeded" in response.json()["error"]
