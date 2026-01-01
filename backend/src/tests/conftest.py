"""Pytest configuration and fixtures."""
import os
import sys

import pytest

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def app_config():
    """Fixture for application configuration."""
    return {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE_URL": os.environ.get("DATABASE_URL", "sqlite:///:memory:"),
        "REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379"),
    }


@pytest.fixture
def client():
    """Fixture for test client."""

    # Mock client for testing
    class MockClient:
        def get(self, path):
            return MockResponse(200, {"status": "ok"})

        def post(self, path, data=None):
            return MockResponse(201, {"status": "created"})

    return MockClient()


class MockResponse:
    """Mock response for testing."""

    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


@pytest.fixture(scope="session")
def database_url():
    """Database URL for testing."""
    return os.environ.get("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")


@pytest.fixture(scope="session")
def redis_url():
    """Redis URL for testing."""
    return os.environ.get("REDIS_URL", "redis://localhost:6379")
