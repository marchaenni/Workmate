import sys
import os
import pytest
from flask_session import Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth_service import app as flask_app

# Redis während Tests deaktivieren / umgehen
flask_app.config['SESSION_TYPE'] = 'filesystem'  # statt Redis
flask_app.config['TESTING'] = True
flask_app.config['SECRET_KEY'] = 'test-secret'
Session(flask_app)

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

def _populate_session(client):
    with client.session_transaction() as sess:
        sess['user'] = {'name': 'Tester', 'tid': 'tenant1'}
        sess['tenant_id'] = 'tenant1'
        sess['access_token'] = 'secret-token'

def test_me_public_without_token(client):
    _populate_session(client)
    res = client.get("/me")
    assert res.status_code == 200
    assert 'access_token' not in res.json

def test_me_internal_with_token(client):
    _populate_session(client)
    res = client.get("/me", headers={"X-Internal-Request": "true"})
    assert res.status_code == 200
    assert res.json.get('access_token') == 'secret-token'
