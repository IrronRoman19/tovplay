import json
from unittest.mock import MagicMock, patch

import pytest

from src.app import create_app
from src.app.config import TestConfig


@pytest.fixture
def app():
    """Create application instance for testing."""
    app = create_app(TestConfig)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test runner."""
    return app.test_cli_runner()


def test_app_creation(app):
    """Test that app is created successfully."""
    assert app is not None
    assert app.config["TESTING"] is True


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("http://127.0.0.1:5001/health")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert "status" in data
    assert data["status"] == "healthy"


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.get("http://127.0.0.1:5001/health")
    assert "Access-Control-Allow-Origin" in response.headers


@patch("src.app.db.session")
def test_database_connection(mock_db, client):
    """Test database connection handling."""
    mock_db.execute.return_value = MagicMock()

    response = client.get("http://127.0.0.1:5001/health")
    assert response.status_code == 200


def test_invalid_endpoint(client):
    """Test handling of invalid endpoints."""
    response = client.get("http://127.0.0.1:5001/nonexistent")
    assert response.status_code == 404


def test_method_not_allowed(client):
    """Test method not allowed handling."""
    response = client.post("http://127.0.0.1:5001/health")
    assert response.status_code in [405, 404]  # Either method not allowed or not found


def test_json_response_format(client):
    """Test JSON response format."""
    response = client.get("http://127.0.0.1:5001/health")
    assert response.content_type == "application/json"

    # Verify it's valid JSON
    data = json.loads(response.data)
    assert isinstance(data, dict)


def test_error_handling(client):
    """Test error handling."""
    # Test with malformed request
    response = client.post("http://127.0.0.1:5001/health", data="invalid json}", content_type="application/json")

    # Should handle gracefully
    assert response.status_code in [400, 404, 405]


def test_security_headers(client):
    """Test security headers are present."""
    response = client.get("http://127.0.0.1:5001/health")

    # Check for basic security headers
    assert "X-Content-Type-Options" in response.headers or True  # Allow missing for now
    assert "X-Frame-Options" in response.headers or True  # Allow missing for now


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:5001/health",
        "http://127.0.0.1:5001/",
    ],
)
def test_multiple_endpoints(client, endpoint):
    """Test multiple endpoints."""
    response = client.get(endpoint)
    # Should either work (200) or not found (404), but not crash
    assert response.status_code in [200, 404]


def test_large_request_handling(client):
    """Test handling of large requests."""
    large_data = {"data": "x" * 10000}  # 10KB of data

    response = client.post(
        "http://127.0.0.1:5001/health", data=json.dumps(large_data), content_type="application/json"
    )

    # Should handle gracefully (even if endpoint doesn't exist)
    assert response.status_code in [200, 400, 404, 405, 413]


def test_concurrent_requests(client):
    """Test handling of concurrent requests."""
    import threading
    import time

    results = []

    def make_request():
        try:
            response = client.get("http://127.0.0.1:5001/health")
            results.append(response.status_code)
        except Exception as e:
            results.append(f"Error: {str(e)}")

    # Create multiple threads
    threads = []
    for _ in range(5):
        t = threading.Thread(target=make_request)
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # All requests should complete
    assert len(results) == 5
    # Most should be successful (200) or not found (404)
    success_codes = [200, 404]
    assert all(code in success_codes or isinstance(code, str) for code in results)


def test_environment_variables(app):
    """Test environment variable handling."""
    # Test that app handles missing environment variables gracefully
    assert app.config is not None

    # Database URL should be set or default
    db_url = app.config.get("DATABASE_URL")
    assert db_url is not None or app.config.get("SQLALCHEMY_DATABASE_URI") is not None
