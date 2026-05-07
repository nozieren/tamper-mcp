import pytest
from starlette.testclient import TestClient
from src.server import app


def test_message_endpoint_exists():
    client = TestClient(app)
    # The message endpoint should be at /message and accept POST
    # We expect 400 or a specific MCP error, but not 404
    response = client.post("/message")
    assert response.status_code != 404
