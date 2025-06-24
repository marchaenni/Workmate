import sys
import os
import pytest

# Sicherstellen, dass der Service importiert werden kann
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from license_service import app as flask_app  # ← Datei muss license_service.py heißen

# Testkonfiguration für Flask
flask_app.config["TESTING"] = True
flask_app.config["SECRET_KEY"] = "test"

@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client

def test_licenses_unauthorized(client):
    response = client.get("/licenses")
    assert response.status_code == 401
