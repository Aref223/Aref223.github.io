from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def auth_header():
    client.post("/auth/register", json={"email": "v@example.com", "password": "strongpass"})
    r = client.post("/auth/login", data={"username": "v@example.com", "password": "strongpass"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_visas_crud_and_scrape():
    headers = auth_header()
    # Create
    r = client.post(
        "/visas/",
        json={"from_country": "US", "to_country": "FR", "requirement": "Visa-free up to 90 days", "source": "manual"},
        headers=headers,
    )
    assert r.status_code == 200
    visa_id = r.json()["id"]

    # Read
    r = client.get(f"/visas/{visa_id}", headers=headers)
    assert r.status_code == 200

    # List with filters
    r = client.get("/visas/?from_country=US&to_country=FR", headers=headers)
    assert r.status_code == 200

    # Trigger scrape
    r = client.post("/scrape/visas", headers=headers)
    assert r.status_code == 200