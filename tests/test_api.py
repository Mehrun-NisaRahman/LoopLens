from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_and_get_review():
    items = client.get("/reviews?limit=3").json()
    assert 1 <= len(items) <= 3
    one = client.get(f"/reviews/{items[0]['id']}")
    assert one.status_code == 200


def test_missing_review_is_404():
    assert client.get("/reviews/nope").status_code == 404


def test_baseline_endpoint_returns_codes():
    rid = client.get("/reviews?limit=1").json()[0]["id"]
    r = client.post(f"/reviews/{rid}/baseline")
    assert r.status_code == 200
    assert "codes" in r.json()
