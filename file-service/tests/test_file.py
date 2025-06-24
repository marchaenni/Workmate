import sys
import os
import io
import pytest


# Pfad hinzufügen, damit Import klappt
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from file_service import app as flask_app  # Achtung: Datei muss file_service.py heißen

# App vorbereiten für Test-Client
flask_app.config["TESTING"] = True
flask_app.config["SECRET_KEY"] = "test"

@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client

def test_upload_valid_csv(client):
    data = {
        'file': (io.BytesIO(b"email\nmax@schule.ch\n"), 'test.csv')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert 'total_upns' in response.json
