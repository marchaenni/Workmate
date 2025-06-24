import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from group_service import app as flask_app

flask_app.config["TESTING"] = True
flask_app.config["SECRET_KEY"] = "test"

@pytest.fixture
def client():
    with flask_app.test_client() as client:
        yield client


def test_groups_unauthorized(client):
    response = client.get("/groups")
    assert response.status_code == 401
