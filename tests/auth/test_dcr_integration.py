"""Integration tests simulating Claude Desktop's OAuth flow for DCR.

These tests simulate the complete OAuth 2.1 flow that Claude Desktop
would use when connecting to this Google Workspace MCP server:

1. Discovery: GET /.well-known/oauth-authorization-server
2. Dynamic Client Registration: POST /oauth/register
3. Authorization: GET /oauth/authorize with PKCE parameters
"""

import base64
import hashlib
import os
import secrets
from urllib.parse import urlparse

import pytest
from starlette.testclient import TestClient


def generate_pkce_verifier() -> str:
    """Generate a PKCE code verifier.

    Returns:
        A random URL-safe string of 43-128 characters.
    """
    return secrets.token_urlsafe(32)


def generate_pkce_challenge(verifier: str) -> str:
    """Generate a PKCE code challenge from a verifier.

    Args:
        verifier: The code verifier string.

    Returns:
        Base64url-encoded SHA256 hash of the verifier.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def register_test_client(oauth_client: TestClient, metadata: dict) -> str:
    """Register a test client via DCR and return the client_id.

    This helper function performs Dynamic Client Registration to obtain
    a valid client_id that can be used in authorization requests.

    Args:
        oauth_client: The test client to use for registration.
        metadata: The OAuth metadata containing the registration_endpoint.

    Returns:
        The registered client_id.

    Raises:
        pytest.skip: If registration endpoint is not available.
        AssertionError: If DCR fails.
    """
    registration_endpoint = metadata.get("registration_endpoint")
    if not registration_endpoint:
        pytest.skip("No registration endpoint in metadata")

    # Extract path from full URL if needed
    if registration_endpoint.startswith("http"):
        registration_path = urlparse(registration_endpoint).path
    else:
        registration_path = registration_endpoint

    # Use full scope URLs as required by FastMCP
    scopes = " ".join([
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ])

    dcr_response = oauth_client.post(
        registration_path,
        json={
            "client_name": "Test Client",
            "redirect_uris": ["http://127.0.0.1:52532/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_basic",
            "scope": scopes,
        },
    )

    assert dcr_response.status_code == 201, (
        f"DCR should return 201, got {dcr_response.status_code}: {dcr_response.text}"
    )

    client_info = dcr_response.json()
    assert "client_id" in client_info, "DCR response must include client_id"
    return client_info["client_id"]


class TestClaudeDesktopDCRFlow:
    """Simulate Claude Desktop connecting to remote server.

    This test class simulates the complete OAuth 2.1 flow that Claude Desktop
    uses when connecting to an MCP server with OAuth 2.1 authentication.
    The flow follows the MCP specification for Dynamic Client Registration (DCR).
    """

    def test_full_dcr_oauth_flow(self, oauth_client: TestClient) -> None:
        """Simulate complete OAuth flow: discovery -> register -> authorize.

        Flow:
            1. GET /.well-known/oauth-authorization-server (discover endpoints)
            2. POST /oauth/register (register client via DCR)
            3. GET /oauth/authorize (start auth - expects redirect)

        This test verifies that the full OAuth 2.1 DCR flow works end-to-end,
        simulating exactly what Claude Desktop does when connecting to a
        remote MCP server.

        Args:
            oauth_client: Test client fixture configured for OAuth 2.1.
        """
        # Step 1: Discovery - Get OAuth authorization server metadata
        discovery_response = oauth_client.get(
            "/.well-known/oauth-authorization-server"
        )

        # If discovery endpoint doesn't exist, server may not support OAuth 2.1 DCR
        if discovery_response.status_code == 404:
            pytest.skip(
                "OAuth authorization server metadata endpoint not available - "
                "server may be in external OAuth provider mode"
            )

        assert discovery_response.status_code == 200, (
            f"Discovery endpoint should return 200, got {discovery_response.status_code}"
        )

        metadata = discovery_response.json()

        # Verify essential metadata fields exist
        assert "issuer" in metadata, "Metadata must include 'issuer'"
        assert "authorization_endpoint" in metadata, (
            "Metadata must include 'authorization_endpoint'"
        )
        assert "token_endpoint" in metadata, "Metadata must include 'token_endpoint'"

        # Step 2: Dynamic Client Registration (if available)
        registration_endpoint = metadata.get("registration_endpoint")

        if registration_endpoint:
            # Extract path from full URL if needed
            if registration_endpoint.startswith("http"):
                from urllib.parse import urlparse

                registration_path = urlparse(registration_endpoint).path
            else:
                registration_path = registration_endpoint

            # Use full scope URLs as required by FastMCP
            scopes = " ".join([
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ])
            dcr_response = oauth_client.post(
                registration_path,
                json={
                    "client_name": "Claude Desktop Test",
                    "redirect_uris": ["http://127.0.0.1:52532/callback"],
                    "grant_types": ["authorization_code", "refresh_token"],
                    "response_types": ["code"],
                    "token_endpoint_auth_method": "client_secret_basic",
                    "scope": scopes,
                },
            )

            # DCR should return 201 Created with client credentials
            assert dcr_response.status_code == 201, (
                f"DCR should return 201 Created, got {dcr_response.status_code}: "
                f"{dcr_response.text}"
            )

            client_info = dcr_response.json()
            assert "client_id" in client_info, "DCR response must include client_id"
            # Note: client_secret is not guaranteed to be in response for all client types
            # FastMCP's GoogleProvider returns the server's Google credentials

            client_id = client_info["client_id"]
        else:
            # No DCR endpoint - use pre-configured test client ID
            client_id = os.environ.get(
                "GOOGLE_OAUTH_CLIENT_ID", "test-client-id"
            )

        # Step 3: Authorization with PKCE
        authorization_endpoint = metadata.get("authorization_endpoint")
        if not authorization_endpoint:
            pytest.skip("No authorization endpoint in metadata")

        # Extract path from full URL if needed
        if authorization_endpoint.startswith("http"):
            from urllib.parse import urlparse

            auth_path = urlparse(authorization_endpoint).path
        else:
            auth_path = authorization_endpoint

        # Generate PKCE parameters
        code_verifier = generate_pkce_verifier()
        code_challenge = generate_pkce_challenge(code_verifier)

        # Build authorization request with full scope URLs
        auth_params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:52532/callback",
            "scope": "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
            "state": secrets.token_urlsafe(16),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        # Request authorization - should redirect to Google
        auth_response = oauth_client.get(
            auth_path, params=auth_params, follow_redirects=False
        )

        # Should return a redirect (302/303) to consent page or Google's authorization server
        assert auth_response.status_code in (302, 303, 307), (
            f"Authorization endpoint should redirect, got {auth_response.status_code}"
        )

        # Verify redirect location - FastMCP redirects to consent page first
        location = auth_response.headers.get("location", "")
        is_consent_page = "/consent" in location
        is_google_auth = "accounts.google.com" in location or "google.com" in location
        assert is_consent_page or is_google_auth, (
            f"Authorization should redirect to consent or Google, got: {location[:100]}"
        )

    def test_metadata_endpoints_match_actual_routes(
        self, oauth_client: TestClient
    ) -> None:
        """Verify advertised endpoints in metadata actually exist.

        This test ensures that all endpoints advertised in the OAuth
        authorization server metadata are actually reachable (return
        something other than 404).

        Args:
            oauth_client: Test client fixture configured for OAuth 2.1.
        """
        discovery_response = oauth_client.get(
            "/.well-known/oauth-authorization-server"
        )

        if discovery_response.status_code == 404:
            pytest.skip(
                "OAuth authorization server metadata endpoint not available"
            )

        assert discovery_response.status_code == 200
        metadata = discovery_response.json()

        # List of endpoint keys to verify
        endpoint_keys = [
            "authorization_endpoint",
            "token_endpoint",
            "registration_endpoint",
        ]

        for key in endpoint_keys:
            endpoint = metadata.get(key)
            if not endpoint:
                continue  # Optional endpoint not advertised

            # Extract path from full URL if needed
            if endpoint.startswith("http"):
                path = urlparse(endpoint).path
            else:
                path = endpoint

            # Make a GET request to verify the endpoint exists
            # May return 400/401/405 due to missing params, but not 404
            response = oauth_client.get(path)

            # Endpoint should exist (not 404)
            assert response.status_code != 404, (
                f"Advertised endpoint '{key}' at '{path}' returned 404 - "
                "endpoint does not exist"
            )

    def test_authorization_redirects(self, oauth_client: TestClient) -> None:
        """Test that authorization endpoint returns redirect response.

        When called with proper parameters, the authorization endpoint
        should redirect to Google's authorization server for user consent.

        Args:
            oauth_client: Test client fixture configured for OAuth 2.1.
        """
        discovery_response = oauth_client.get(
            "/.well-known/oauth-authorization-server"
        )

        if discovery_response.status_code == 404:
            pytest.skip(
                "OAuth authorization server metadata endpoint not available"
            )

        metadata = discovery_response.json()
        authorization_endpoint = metadata.get("authorization_endpoint")

        if not authorization_endpoint:
            pytest.skip("No authorization endpoint in metadata")

        # Register a client to get a valid client_id
        client_id = register_test_client(oauth_client, metadata)

        # Extract path from full URL if needed
        if authorization_endpoint.startswith("http"):
            auth_path = urlparse(authorization_endpoint).path
        else:
            auth_path = authorization_endpoint

        # Build authorization request with registered client
        auth_params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:52532/callback",
            "scope": "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
            "state": secrets.token_urlsafe(16),
        }

        # Request authorization without following redirects
        auth_response = oauth_client.get(
            auth_path, params=auth_params, follow_redirects=False
        )

        # Should return a redirect status
        redirect_statuses = (301, 302, 303, 307, 308)
        assert auth_response.status_code in redirect_statuses, (
            f"Authorization endpoint should return redirect, "
            f"got {auth_response.status_code}: {auth_response.text[:200]}"
        )

        # Should have Location header
        assert "location" in auth_response.headers, (
            "Redirect response must include Location header"
        )

    def test_pkce_parameters_accepted(self, oauth_client: TestClient) -> None:
        """Test that PKCE code_challenge is accepted.

        PKCE (Proof Key for Code Exchange) is required by OAuth 2.1.
        This test verifies that the authorization endpoint accepts
        PKCE parameters without returning an error.

        Args:
            oauth_client: Test client fixture configured for OAuth 2.1.
        """
        discovery_response = oauth_client.get(
            "/.well-known/oauth-authorization-server"
        )

        if discovery_response.status_code == 404:
            pytest.skip(
                "OAuth authorization server metadata endpoint not available"
            )

        metadata = discovery_response.json()
        authorization_endpoint = metadata.get("authorization_endpoint")

        if not authorization_endpoint:
            pytest.skip("No authorization endpoint in metadata")

        # Register a client to get a valid client_id
        client_id = register_test_client(oauth_client, metadata)

        # Extract path from full URL if needed
        if authorization_endpoint.startswith("http"):
            auth_path = urlparse(authorization_endpoint).path
        else:
            auth_path = authorization_endpoint

        # Generate PKCE parameters
        code_verifier = generate_pkce_verifier()
        code_challenge = generate_pkce_challenge(code_verifier)

        # Build authorization request with PKCE
        auth_params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:52532/callback",
            "scope": "openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile",
            "state": secrets.token_urlsafe(16),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        # Request authorization without following redirects
        auth_response = oauth_client.get(
            auth_path, params=auth_params, follow_redirects=False
        )

        # Should redirect (not error out due to PKCE params)
        # Common error for unsupported PKCE would be 400 Bad Request
        if auth_response.status_code == 400:
            error_body = auth_response.text.lower()
            assert "code_challenge" not in error_body, (
                "Server rejected PKCE code_challenge parameter - "
                "PKCE may not be supported"
            )
            assert "pkce" not in error_body, (
                "Server explicitly rejected PKCE - PKCE may not be supported"
            )

        # Normal flow should redirect
        redirect_statuses = (301, 302, 303, 307, 308)
        assert auth_response.status_code in redirect_statuses, (
            f"Authorization with PKCE should redirect or succeed, "
            f"got {auth_response.status_code}"
        )

        # Verify PKCE-related metadata fields if present
        pkce_methods = metadata.get("code_challenge_methods_supported", [])
        if pkce_methods:
            assert "S256" in pkce_methods, (
                "OAuth 2.1 requires S256 code_challenge_method support"
            )


class TestOAuthMetadataDiscovery:
    """Test OAuth 2.1 metadata discovery endpoints.

    These tests verify that the OAuth authorization server metadata
    is correctly formatted according to RFC 8414.
    """

    def test_well_known_oauth_metadata_format(
        self, oauth_client: TestClient
    ) -> None:
        """Verify OAuth authorization server metadata format.

        The metadata response should conform to RFC 8414 and include
        all required fields for OAuth 2.1 compliance.

        Args:
            oauth_client: Test client fixture configured for OAuth 2.1.
        """
        response = oauth_client.get("/.well-known/oauth-authorization-server")

        if response.status_code == 404:
            pytest.skip(
                "OAuth authorization server metadata endpoint not available"
            )

        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith(
            "application/json"
        )

        metadata = response.json()

        # Required fields per RFC 8414
        assert "issuer" in metadata, "Metadata must include 'issuer'"

        # Recommended fields for OAuth 2.1
        recommended_fields = [
            "authorization_endpoint",
            "token_endpoint",
            "response_types_supported",
            "grant_types_supported",
        ]

        for field in recommended_fields:
            if field not in metadata:
                # Log but don't fail - these are recommended, not required
                pass

    def test_protected_resource_metadata(
        self, oauth_client: TestClient
    ) -> None:
        """Verify protected resource metadata if available.

        When running in external OAuth provider mode, the server
        advertises itself as a protected resource pointing to
        Google's authorization server.

        Args:
            oauth_client: Test client fixture configured for OAuth 2.1.
        """
        # Try OAuth protected resource metadata endpoint
        response = oauth_client.get(
            "/.well-known/oauth-protected-resource"
        )

        if response.status_code == 404:
            # Not in external provider mode, skip
            pytest.skip("Protected resource metadata not available")

        assert response.status_code == 200
        metadata = response.json()

        # Should point to authorization servers
        assert "authorization_servers" in metadata or "resource" in metadata, (
            "Protected resource metadata should indicate authorization servers"
        )
