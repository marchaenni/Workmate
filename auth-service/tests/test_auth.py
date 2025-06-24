import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_service import app as flask_app

# Redis während Tests deaktivieren / umgehen
flask_app.config['SESSION_TYPE'] = 'filesystem'  # statt Redis
flask_app.config['TESTING'] = True
flask_app.config['SECRET_KEY'] = 'test-secret'

@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client

def test_index_redirect(client):
    response = client.get("/")
    # Es sollte auf /login weiterleiten, wenn keine Session existiert
    assert response.status_code == 302
    assert "/login" in response.location

def test_me_unauthorized(client):
    response = client.get("/me")
    assert response.status_code == 401
    assert response.json == {"error": "unauthorized"}
