from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_and_get_case():
    items = client.get("/cases?limit=3").json()
    assert 1 <= len(items) <= 3
    one = client.get(f"/cases/{items[0]['id']}").json()
    assert "listing" in one and "review_text" in one


def test_missing_case_is_404():
    assert client.get("/cases/nope").status_code == 404


def test_single_model_endpoint_returns_a_verdict():
    cid = client.get("/cases?limit=1").json()[0]["id"]
    r = client.post(f"/cases/{cid}/single-model")
    assert r.status_code == 200
    assert r.json()["verdict"] in {"match", "mismatch", "unclear"}


def test_pipeline_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    case_id = c.get("/cases").json()[0]["id"]
    r = c.post(f"/cases/{case_id}/pipeline?mode=full")
    assert r.status_code == 200 and r.json()["mode"] == "full"
    assert c.post(f"/cases/{case_id}/pipeline?mode=bogus").status_code == 400
