import io
import sys
import os
import pytest
from unittest.mock import patch

# Pfad zum Frontend-Verzeichnis hinzufügen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app  

@pytest.fixture
def client():
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['access_token'] = "dummy-token"
        yield client

def test_frontpage_redirect_or_landing(client):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 401  # Simuliere fehlgeschlagenen Auth-Check
        response = client.get("/")
        assert response.status_code == 200
        assert b"html" in response.data.lower()

def test_dashboard_auth_success(client):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "access_token": "abc123", "name": "Test User"
        }
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert b"html" in response.data.lower()

def test_dashboard_auth_fail(client):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 401
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "auth" in response.location.lower()

def test_license_route(client):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"LICENSE-A": {"total": 10, "used": 2}}
        response = client.get("/license")
        assert response.status_code == 200
        assert b"LICENSE-A" in response.data

def test_assign_license_missing_file(client):
    response = client.post("/assign_license", data={"license_name": "LICENSE-A"})
    assert response.status_code == 400

def test_assign_license_success(client):
    dummy_file = (io.BytesIO(b"email\nuser@schule.ch"), "test.csv")
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "results": [{"upn": "user@schule.ch", "status": "Lizenz zugewiesen"}]
        }
        response = client.post(
            "/assign_license",
            data={"license_name": "LICENSE-A", "file": dummy_file},
            content_type="multipart/form-data"
        )
        assert response.status_code == 200
        assert b"Lizenz zugewiesen" in response.data

