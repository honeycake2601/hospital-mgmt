import pytest
from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    return app.test_client()


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "healthy"


def test_health_unhealthy_when_db_unreachable():
    c = create_app("/nonexistent-dir/x.db").test_client()
    assert c.get("/health").status_code == 503


def test_patient_flow(client):
    assert client.post("/api/patients", json={"name": "Asha", "age": 30}).status_code == 201
    data = client.get("/api/patients").get_json()
    assert len(data) == 1 and data[0]["name"] == "Asha"


def test_patient_requires_name(client):
    assert client.post("/api/patients", json={"age": 5}).status_code == 400


def test_appointment_flow(client):
    pid = client.post("/api/patients", json={"name": "Ravi"}).get_json()["id"]
    did = client.post("/api/doctors", json={"name": "Dr. Meena", "specialization": "Cardiology"}).get_json()["id"]
    r = client.post("/api/appointments", json={"patient_id": pid, "doctor_id": did, "date": "2026-10-20"})
    assert r.status_code == 201
    appt = client.get("/api/appointments").get_json()[0]
    assert appt["patient"] == "Ravi" and appt["doctor"] == "Dr. Meena"


def test_appointment_unknown_patient(client):
    r = client.post("/api/appointments", json={"patient_id": 99, "doctor_id": 1, "date": "2026-10-20"})
    assert r.status_code == 404


def test_stats(client):
    client.post("/api/doctors", json={"name": "Dr. A"})
    assert client.get("/api/stats").get_json()["doctors"] == 1
