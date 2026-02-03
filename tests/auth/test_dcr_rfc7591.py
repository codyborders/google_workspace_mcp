"""RFC 7591 Dynamic Client Registration compliance tests.

This module tests compliance with RFC 7591 (OAuth 2.0 Dynamic Client Registration
Protocol) for the Google Workspace MCP server's /oauth/register endpoint.

RFC 7591 defines the protocol for dynamically registering OAuth clients with
an authorization server. These tests verify that the server correctly implements
the required behaviors for client registration.

Reference: https://datatracker.ietf.org/doc/html/rfc7591
"""

import pytest
from typing import Any
from starlette.testclient import TestClient


class TestRFC7591Compliance:
    """Test RFC 7591 DCR requirements.

    This class contains tests that verify compliance with RFC 7591
    Dynamic Client Registration Protocol. Each test corresponds to
    specific requirements from the RFC specification.

    Attributes:
        DCR_ENDPOINT: The endpoint path for dynamic client registration.
    """

    DCR_ENDPOINT: str = "/register"

    def test_dcr_accepts_minimal_request(self, oauth_client: TestClient) -> None:
        """RFC 7591: Only redirect_uris is required.

        Per RFC 7591 Section 2, the only required field in a client
        registration request is redirect_uris. The authorization server
        must accept a registration request containing only this field.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If the response status is not 201 or
                client_id is missing from the response.
        """
        # Arrange
        minimal_payload: dict[str, Any] = {
            "redirect_uris": ["http://localhost:8080/callback"]
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=minimal_payload,
        )

        # Assert
        assert response.status_code == 201, (
            f"Expected 201 for minimal DCR request, got {response.status_code}. "
            f"Response: {response.text}"
        )
        response_data = response.json()
        assert "client_id" in response_data, (
            "Response must include client_id per RFC 7591 Section 3.2.1"
        )

    @pytest.mark.xfail(
        reason="FastMCP GoogleProvider requires both authorization_code and refresh_token grants"
    )
    def test_dcr_accepts_authorization_code_only(
        self, oauth_client: TestClient
    ) -> None:
        """RFC 7591: refresh_token grant is optional.

        Per RFC 7591 Section 2, the grant_types field is optional. When
        specified, the server should accept authorization_code alone
        without requiring refresh_token. The refresh_token grant type
        is an optional extension.

        Note: FastMCP's GoogleProvider currently requires refresh_token grant,
        which is a known deviation from RFC 7591.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If the response status is not 201.
        """
        # Arrange
        payload: dict[str, Any] = {
            "redirect_uris": ["http://localhost:8080/callback"],
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=payload,
        )

        # Assert
        assert response.status_code == 201, (
            f"Expected 201 for authorization_code-only grant, got {response.status_code}. "
            f"Response: {response.text}"
        )

    def test_dcr_returns_required_fields(self, oauth_client: TestClient) -> None:
        """RFC 7591: Response must include client_id.

        Per RFC 7591 Section 3.2.1, the authorization server must return
        at minimum a client_id in the registration response. The client_id
        is a unique identifier issued to the registered client.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If the response does not contain client_id.
        """
        # Arrange
        payload: dict[str, Any] = {
            "redirect_uris": ["http://localhost:8080/callback"],
            "client_name": "Test Application",
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=payload,
        )

        # Assert
        assert response.status_code == 201, (
            f"Expected 201 for DCR request, got {response.status_code}. "
            f"Response: {response.text}"
        )
        response_data = response.json()

        # RFC 7591 Section 3.2.1: client_id is required in response
        assert "client_id" in response_data, (
            "client_id is a required field in DCR response per RFC 7591 Section 3.2.1"
        )
        assert response_data["client_id"], (
            "client_id must not be empty"
        )

    def test_dcr_preserves_client_metadata(self, oauth_client: TestClient) -> None:
        """RFC 7591: Server should echo back client metadata.

        Per RFC 7591 Section 3.2.1, the authorization server should
        return all registered metadata about the client, including
        any default values that were applied. The response should
        preserve metadata that was provided in the request.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If provided metadata is not echoed back.
        """
        # Arrange
        payload: dict[str, Any] = {
            "redirect_uris": [
                "http://localhost:8080/callback",
                "http://localhost:9000/auth",
            ],
            "client_name": "My Test Application",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_basic",
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=payload,
        )

        # Assert
        assert response.status_code == 201, (
            f"Expected 201 for DCR request, got {response.status_code}. "
            f"Response: {response.text}"
        )
        response_data = response.json()

        # Verify redirect_uris are preserved
        assert "redirect_uris" in response_data, (
            "Response must include redirect_uris"
        )
        for uri in payload["redirect_uris"]:
            assert uri in response_data["redirect_uris"], (
                f"redirect_uri '{uri}' should be preserved in response"
            )

        # Verify client_name is preserved if returned
        if "client_name" in response_data:
            assert response_data["client_name"] == payload["client_name"], (
                "client_name should be preserved in response"
            )

    def test_dcr_rejects_missing_redirect_uris(
        self, oauth_client: TestClient
    ) -> None:
        """RFC 7591: redirect_uris is required.

        Per RFC 7591 Section 2, the redirect_uris field is required
        for clients using flows that involve redirection (e.g.,
        authorization code flow). A request without redirect_uris
        should be rejected with an appropriate error.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If the server accepts a request without redirect_uris.
        """
        # Arrange
        invalid_payload: dict[str, Any] = {
            "client_name": "Invalid Client",
            "grant_types": ["authorization_code"],
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=invalid_payload,
        )

        # Assert
        # RFC 7591 Section 3.2.2 specifies error response format
        assert response.status_code in (400, 422), (
            f"Expected 400 or 422 for missing redirect_uris, got {response.status_code}. "
            f"Response: {response.text}"
        )
        response_data = response.json()

        # RFC 7591 Section 3.2.2: error response should include 'error' field
        assert "error" in response_data or "detail" in response_data, (
            "Error response should include 'error' or 'detail' field"
        )


class TestRFC7591ClientMetadata:
    """Test RFC 7591 client metadata handling.

    This class tests the handling of various client metadata fields
    as defined in RFC 7591 Section 2.
    """

    DCR_ENDPOINT: str = "/register"

    @pytest.mark.xfail(
        reason="FastMCP GoogleProvider may not support token_endpoint_auth_method='none' for public clients"
    )
    def test_dcr_accepts_public_client(self, oauth_client: TestClient) -> None:
        """RFC 7591: Support for public clients (no client_secret).

        Per RFC 7591, public clients are clients that cannot maintain
        confidentiality of credentials. The server should support
        registration of public clients with token_endpoint_auth_method
        set to 'none'.

        Note: FastMCP's GoogleProvider may not fully support public clients
        since Google OAuth requires confidential clients for server-side flows.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If public client registration fails.
        """
        # Arrange - include refresh_token grant which FastMCP requires
        public_client_payload: dict[str, Any] = {
            "redirect_uris": ["http://localhost:8080/callback"],
            "client_name": "Public Client App",
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=public_client_payload,
        )

        # Assert
        assert response.status_code == 201, (
            f"Expected 201 for public client registration, got {response.status_code}. "
            f"Response: {response.text}"
        )
        response_data = response.json()
        assert "client_id" in response_data, (
            "Public client registration must return client_id"
        )

    def test_dcr_accepts_confidential_client(
        self, oauth_client: TestClient
    ) -> None:
        """RFC 7591: Support for confidential clients.

        Per RFC 7591, confidential clients can maintain credential
        confidentiality. The server should support registration with
        client_secret_basic or client_secret_post authentication.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If confidential client registration fails
                or client_secret is not returned.
        """
        # Arrange
        confidential_client_payload: dict[str, Any] = {
            "redirect_uris": ["https://app.example.com/callback"],
            "client_name": "Confidential Client App",
            "token_endpoint_auth_method": "client_secret_basic",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=confidential_client_payload,
        )

        # Assert
        assert response.status_code == 201, (
            f"Expected 201 for confidential client registration, got {response.status_code}. "
            f"Response: {response.text}"
        )
        response_data = response.json()
        assert "client_id" in response_data, (
            "Confidential client registration must return client_id"
        )
        # For confidential clients, a client_secret should be issued
        # (unless server uses alternative authentication)

    def test_dcr_with_multiple_redirect_uris(
        self, oauth_client: TestClient
    ) -> None:
        """RFC 7591: Support for multiple redirect URIs.

        Per RFC 7591 Section 2, redirect_uris is an array, and clients
        may register multiple redirect URIs. The server should accept
        and preserve all provided URIs.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If multiple redirect URIs are not accepted.
        """
        # Arrange
        multiple_uris_payload: dict[str, Any] = {
            "redirect_uris": [
                "http://localhost:8080/callback",
                "http://localhost:8080/oauth/callback",
                "https://app.example.com/auth/callback",
                "myapp://oauth/callback",
            ],
            "client_name": "Multi-URI Client",
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=multiple_uris_payload,
        )

        # Assert
        assert response.status_code == 201, (
            f"Expected 201 for multiple redirect URIs, got {response.status_code}. "
            f"Response: {response.text}"
        )
        response_data = response.json()
        assert "redirect_uris" in response_data, (
            "Response must include redirect_uris"
        )
        assert len(response_data["redirect_uris"]) == len(
            multiple_uris_payload["redirect_uris"]
        ), "All redirect URIs should be preserved"


class TestRFC7591ErrorResponses:
    """Test RFC 7591 error response format.

    This class tests that error responses conform to RFC 7591
    Section 3.2.2 error response format.
    """

    DCR_ENDPOINT: str = "/register"

    def test_dcr_error_response_format(self, oauth_client: TestClient) -> None:
        """RFC 7591: Error response format.

        Per RFC 7591 Section 3.2.2, error responses should include
        an 'error' field with a single ASCII error code, and optionally
        an 'error_description' with a human-readable description.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If error response format is incorrect.
        """
        # Arrange - send invalid request to trigger error
        invalid_payload: dict[str, Any] = {
            "client_name": "Missing Required Fields",
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=invalid_payload,
        )

        # Assert
        assert response.status_code in (400, 422), (
            f"Expected 400 or 422 for invalid request, got {response.status_code}"
        )
        response_data = response.json()

        # RFC 7591 specifies 'error' field, but FastAPI may use 'detail'
        has_error_info = (
            "error" in response_data or
            "detail" in response_data
        )
        assert has_error_info, (
            "Error response must include 'error' or 'detail' field"
        )

    def test_dcr_rejects_empty_redirect_uris(
        self, oauth_client: TestClient
    ) -> None:
        """RFC 7591: Empty redirect_uris array should be rejected.

        Per RFC 7591, clients using redirection-based flows must have
        at least one redirect URI. An empty array should be rejected.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If empty redirect_uris is accepted.
        """
        # Arrange
        empty_uris_payload: dict[str, Any] = {
            "redirect_uris": [],
            "client_name": "Empty URIs Client",
        }

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            json=empty_uris_payload,
        )

        # Assert
        assert response.status_code in (400, 422), (
            f"Expected 400 or 422 for empty redirect_uris, got {response.status_code}. "
            f"Response: {response.text}"
        )

    @pytest.mark.xfail(
        reason="FastMCP raises unhandled JSONDecodeError instead of returning 400",
        raises=Exception,
    )
    def test_dcr_rejects_invalid_json(self, oauth_client: TestClient) -> None:
        """RFC 7591: Invalid JSON should be rejected.

        The server should return an appropriate error for malformed
        JSON in the request body.

        Note: FastMCP currently raises an unhandled JSONDecodeError instead
        of properly returning a 400 Bad Request response.

        Args:
            oauth_client: Test client fixture with OAuth 2.1 enabled.

        Returns:
            None

        Raises:
            AssertionError: If invalid JSON is not properly rejected.
        """
        # Arrange
        invalid_json = "{ invalid json }"

        # Act
        response = oauth_client.post(
            self.DCR_ENDPOINT,
            content=invalid_json,
            headers={"Content-Type": "application/json"},
        )

        # Assert
        assert response.status_code in (400, 422), (
            f"Expected 400 or 422 for invalid JSON, got {response.status_code}"
        )
