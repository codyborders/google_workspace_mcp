"""Discovery tests for DCR (Dynamic Client Registration) endpoints.

These tests diagnose the current state of DCR endpoints in the Google Workspace
MCP server to understand which OAuth 2.1 endpoints are available and their paths.
"""
import logging
from urllib.parse import urlparse

import pytest
from starlette.testclient import TestClient

logger = logging.getLogger(__name__)


def test_well_known_oauth_metadata_exists(oauth_client: TestClient) -> None:
    """Verify .well-known/oauth-authorization-server returns metadata.

    This test checks that the OAuth 2.1 metadata endpoint is accessible and
    contains the required registration_endpoint field for DCR.

    Args:
        oauth_client: Test client fixture with OAuth 2.1 enabled.
    """
    # Arrange - client fixture handles setup

    # Act
    response = oauth_client.get("/.well-known/oauth-authorization-server")

    # Assert
    print(f"\n[DISCOVERY] /.well-known/oauth-authorization-server status: {response.status_code}")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}. "
        f"Response: {response.text[:500] if response.text else 'empty'}"
    )

    metadata = response.json()
    print(f"[DISCOVERY] OAuth metadata keys: {list(metadata.keys())}")

    assert "registration_endpoint" in metadata, (
        f"registration_endpoint not found in metadata. "
        f"Available keys: {list(metadata.keys())}"
    )

    print(f"[DISCOVERY] registration_endpoint: {metadata.get('registration_endpoint')}")


def test_fastmcp_oauth_register_exists(oauth_client: TestClient) -> None:
    """Test if /register endpoint exists for DCR.

    FastMCP's GoogleProvider mounts DCR at /register (not /oauth/register).
    This test verifies the endpoint exists and accepts POST requests with
    a minimal client registration payload.

    Args:
        oauth_client: Test client fixture with OAuth 2.1 enabled.
    """
    # Arrange - minimal DCR request body
    dcr_request = {
        "client_name": "test-client",
        "redirect_uris": ["http://localhost:8080/callback"],
    }

    # Act
    response = oauth_client.post("/register", json=dcr_request)

    # Assert
    print(f"\n[DISCOVERY] /register status: {response.status_code}")
    print(f"[DISCOVERY] /register response: {response.text[:500] if response.text else 'empty'}")

    # We expect either:
    # - 200/201: endpoint exists and registration succeeded
    # - 400/401/403: endpoint exists but request was rejected (auth/validation)
    # - 404: endpoint does not exist
    # - 405: endpoint exists but method not allowed
    endpoint_exists = response.status_code != 404

    assert endpoint_exists, (
        f"/register returned 404 - endpoint does not exist. "
        f"FastMCP may not have DCR enabled."
    )

    print(f"[DISCOVERY] /register endpoint EXISTS (status: {response.status_code})")


def test_custom_oauth2_register_exists(oauth_client: TestClient) -> None:
    """Test if /oauth2/register endpoint exists (alternative path).

    Some OAuth implementations use /oauth2/register instead of /oauth/register.
    This test checks if such an alternative path exists (expected to 404).

    Args:
        oauth_client: Test client fixture with OAuth 2.1 enabled.
    """
    # Arrange - minimal DCR request body
    dcr_request = {
        "client_name": "test-client",
        "redirect_uris": ["http://localhost:8080/callback"],
    }

    # Act
    response = oauth_client.post("/oauth2/register", json=dcr_request)

    # Assert
    print(f"\n[DISCOVERY] /oauth2/register status: {response.status_code}")
    print(f"[DISCOVERY] /oauth2/register response: {response.text[:500] if response.text else 'empty'}")

    # Log whether the endpoint exists (expect 404)
    if response.status_code == 404:
        print("[DISCOVERY] /oauth2/register does NOT exist (expected)")
    else:
        print(f"[DISCOVERY] /oauth2/register EXISTS with status {response.status_code}")


def test_metadata_registration_endpoint_path(oauth_client: TestClient) -> None:
    """Log and verify the actual path in the registration_endpoint field.

    This test extracts and logs the registration_endpoint from OAuth metadata
    to diagnose the exact path the server advertises for DCR.

    Args:
        oauth_client: Test client fixture with OAuth 2.1 enabled.
    """
    # Arrange - client fixture handles setup

    # Act
    response = oauth_client.get("/.well-known/oauth-authorization-server")

    # Assert
    print(f"\n[DISCOVERY] Fetching metadata for registration_endpoint analysis")

    if response.status_code != 200:
        pytest.skip(
            f"Cannot analyze registration_endpoint - metadata endpoint "
            f"returned {response.status_code}"
        )

    metadata = response.json()

    # Log all relevant endpoints
    relevant_keys = [
        "registration_endpoint",
        "authorization_endpoint",
        "token_endpoint",
        "revocation_endpoint",
        "introspection_endpoint",
    ]

    print("[DISCOVERY] OAuth 2.1 endpoint paths from metadata:")
    for key in relevant_keys:
        value = metadata.get(key, "NOT PRESENT")
        print(f"  {key}: {value}")

    # Verify registration_endpoint is present and extract path
    registration_endpoint = metadata.get("registration_endpoint")
    assert registration_endpoint is not None, (
        "registration_endpoint is None or missing from metadata"
    )

    # Extract just the path portion for logging
    parsed = urlparse(registration_endpoint)
    registration_path = parsed.path

    print(f"\n[DISCOVERY] Registration endpoint full URL: {registration_endpoint}")
    print(f"[DISCOVERY] Registration endpoint path: {registration_path}")

    # Verify the path starts with a forward slash
    assert registration_path.startswith("/"), (
        f"registration_endpoint path should start with /, got: {registration_path}"
    )

    # Test that the advertised endpoint actually exists
    print(f"\n[DISCOVERY] Testing advertised registration endpoint: {registration_path}")
    dcr_request = {
        "client_name": "metadata-test-client",
        "redirect_uris": ["http://localhost:8080/callback"],
    }
    test_response = oauth_client.post(registration_path, json=dcr_request)

    print(f"[DISCOVERY] Advertised endpoint {registration_path} status: {test_response.status_code}")
    print(f"[DISCOVERY] Advertised endpoint response: {test_response.text[:500] if test_response.text else 'empty'}")

    assert test_response.status_code != 404, (
        f"Advertised registration_endpoint {registration_path} returned 404. "
        f"Metadata advertises a non-existent endpoint!"
    )
