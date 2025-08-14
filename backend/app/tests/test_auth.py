from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_and_login():
    # Register
    r = client.post("/auth/register", json={"email": "user@example.com", "password": "strongpass"})
    assert r.status_code == 200, r.text
    # Login
    r = client.post("/auth/login", data={"username": "user@example.com", "password": "strongpass"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data