from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_yearly_climate_endpoint():
    """Test the yearly climate data endpoint."""
    resp = client.post("/api/v1/climate/yearly", json={
        "city": "Madrid", 
        "years": [2020, 2021]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["city"] == "Madrid"
    assert data["start_year"] == 2020
    assert data["end_year"] == 2021
    assert len(data["yearly_data"]) == 2
    assert "2020" in data["yearly_data"]
    assert "2021" in data["yearly_data"]
    assert "distance_km" in data
    assert isinstance(data["distance_km"], float)


def test_aggregated_climate_endpoint():
    """Test the aggregated climate data endpoint."""
    resp = client.post("/api/v1/climate/aggregated", json={
        "city": "Barcelona",
        "years": [2020, 2021, 2022]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"]["city"] == "Barcelona"
    assert data["start_year"] == 2020
    assert data["end_year"] == 2022
    assert "climate_data" in data
    assert "avg_monthly_temps" in data["climate_data"]
    assert len(data["climate_data"]["avg_monthly_temps"]) == 12
    assert "distance_km" in data
    assert isinstance(data["distance_km"], float)
