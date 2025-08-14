from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def auth_header():
    client.post("/auth/register", json={"email": "c@example.com", "password": "strongpass"})
    r = client.post("/auth/login", data={"username": "c@example.com", "password": "strongpass"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_cards_crud_and_scrape():
    headers = auth_header()
    # Create
    r = client.post(
        "/cards/",
        json={"name": "Test", "issuer": "Issuer", "network": "Visa", "annual_fee": 0, "rewards": "1%", "country": "US"},
        headers=headers,
    )
    assert r.status_code == 200
    card_id = r.json()["id"]

    # Read
    r = client.get(f"/cards/{card_id}", headers=headers)
    assert r.status_code == 200

    # Update
    r = client.put(f"/cards/{card_id}", json={"rewards": "2%"}, headers=headers)
    assert r.status_code == 200

    # List
    r = client.get("/cards/?q=Test", headers=headers)
    assert r.status_code == 200

    # Trigger scrape
    r = client.post("/scrape/cards", headers=headers)
    assert r.status_code == 200