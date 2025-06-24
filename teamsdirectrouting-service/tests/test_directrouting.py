import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from teamsdirectrouting_service import app as flask_app

flask_app.config["TESTING"] = True
flask_app.config["SECRET_KEY"] = "test"

@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client


def test_assign_unauthorized(client):
    response = client.post("/assign")
    assert response.status_code == 401
