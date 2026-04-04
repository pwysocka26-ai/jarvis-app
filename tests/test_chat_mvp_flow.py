from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_mvp_flow_smoke():
    r1 = client.post("/chat", json={"message": "muszę kupić mleko", "mode": "b2c"})
    assert r1.status_code == 200
    body1 = r1.json()
    assert "reply" in body1

    r2 = client.post("/chat", json={"message": "zrób to jutro", "mode": "b2c"})
    assert r2.status_code == 200
    body2 = r2.json()
    assert "reply" in body2

    r3 = client.post("/chat", json={"message": "co mam jutro", "mode": "b2c"})
    assert r3.status_code == 200
    body3 = r3.json()
    assert "reply" in body3

    r4 = client.post("/chat", json={"message": "usuń ostatnie", "mode": "b2c"})
    assert r4.status_code == 200
    body4 = r4.json()
    assert "reply" in body4
