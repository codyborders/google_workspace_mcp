"""
Shared pytest fixtures for DCR authentication tests.

Provides common fixtures for testing OAuth 2.1 Dynamic Client Registration
flows in the Google Workspace MCP server.
"""

import os
import sys
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """Set up OAuth 2.1 environment variables for testing.

    This fixture configures the environment with the necessary OAuth 2.1
    settings required for DCR authentication testing.

    Yields:
        dict[str, str]: Dictionary of the mocked environment variables.

    Example:
        def test_oauth_flow(mock_env_vars):
            # Arrange
            # Environment is already configured by fixture

            # Act
            result = some_oauth_function()

            # Assert
            assert result.is_authenticated
    """
    # Arrange
    env_vars = {
        "MCP_ENABLE_OAUTH21": "true",
        "GOOGLE_OAUTH_CLIENT_ID": "test-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
        "OAUTHLIB_INSECURE_TRANSPORT": "1",
    }

    # Act
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def oauth_client(mock_env_vars: dict[str, str]) -> Generator[TestClient, None, None]:
    """Create a Starlette TestClient for the fastmcp_server.

    This fixture provides a test client configured with OAuth 2.1 environment
    variables for testing authentication endpoints and flows.

    Args:
        mock_env_vars: The mock environment variables fixture (dependency).

    Yields:
        TestClient: A Starlette TestClient instance for the MCP server.

    Example:
        def test_health_endpoint(oauth_client):
            # Arrange
            # Client is already configured by fixture

            # Act
            response = oauth_client.get("/health")

            # Assert
            assert response.status_code == 200
    """
    # Arrange
    # Import here to ensure environment variables are set first
    from core.server import server, set_transport_mode, configure_server_for_http

    # Act
    # Set transport mode to streamable-http (required for OAuth 2.1)
    set_transport_mode("streamable-http")

    # Configure the OAuth 2.1 provider - this must be called before getting the app
    configure_server_for_http()

    # Get the Starlette ASGI app from the FastMCP server
    app = server.http_app()
    client = TestClient(app)

    yield client
