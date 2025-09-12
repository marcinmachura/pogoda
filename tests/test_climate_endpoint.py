from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_climate_range_no_aggregate():
    resp = client.get("/api/v1/climate", params={"place": "Testville", "start_year": 2000, "end_year": 2002})
    assert resp.status_code == 200
    data = resp.json()
    assert data["place"] == "Testville"
    assert data["start_year"] == 2000
    assert data["end_year"] == 2002
    assert data["aggregate"] is None
    assert len(data["records"]) == 3


def test_climate_range_with_aggregate():
    resp = client.get(
        "/api/v1/climate",
        params={
            "place": "AggTown",
            "start_year": 2010,
            "end_year": 2012,
            "aggregate": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["aggregate"] is not None
    assert data["aggregate"]["start_year"] == 2010
    assert data["aggregate"]["end_year"] == 2012
