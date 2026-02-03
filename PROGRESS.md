# Progress Log

## 2026-02-02 - MCP OAuth 2.1 DCR Implementation Complete

### Summary
Implemented MCP OAuth 2.1 with Dynamic Client Registration (DCR) to enable Claude Desktop to connect to remote workspace-mcp servers.

### Changes Made

#### Test Infrastructure (`tests/auth/`)
- Created `tests/auth/__init__.py` - Module init
- Created `tests/auth/conftest.py` - Shared pytest fixtures for OAuth testing
- Created `tests/auth/test_dcr_discovery.py` - Discovery tests for DCR endpoints
- Created `tests/auth/test_dcr_rfc7591.py` - RFC 7591 compliance tests
- Created `tests/auth/test_dcr_integration.py` - Integration tests simulating Claude Desktop OAuth flow

#### Key Fixes
- Fixed OAuth metadata paths in `auth/oauth_config.py`: Changed from `/oauth2/*` to `/oauth/*` to match FastMCP routes
- Fixed test fixtures to call `configure_server_for_http()` before creating test client
- Fixed DCR endpoint path from `/oauth/register` to `/register` (FastMCP mounts at root)
- Fixed scope handling to use full Google API scope URLs
- Added helper function `register_test_client()` for tests that need a valid client_id

### Test Results
```
18 passed, 2 xfailed, 1 xpassed
```

- `xfailed`: Known FastMCP limitations (refresh_token required, invalid JSON handling)
- `xpassed`: `test_dcr_accepts_public_client` - FastMCP does support public clients

### Documentation
- Created `implementation-plan.md` with detailed implementation strategy

---

## 2026-02-03 - Deployed to GCP VM (mcp-vm)

### Summary
Deployed MCP OAuth 2.1 DCR server to GCP VM for remote Claude Desktop connections.

### Deployment Details
- **URL**: `https://mcp-vm.tail744e10.ts.net/workspace-dcr`
- **Port**: 8003 (internal)
- **User Email**: info@johnnysroofingaz.com
- **Service**: systemd user service `workspace-mcp-dcr.service`

### Configuration
```
WORKSPACE_EXTERNAL_URL=https://mcp-vm.tail744e10.ts.net/workspace-dcr
MCP_ENABLE_OAUTH21=true
WORKSPACE_MCP_PORT=8003
```

### Fix Applied
- Fixed `SecureFastMCP.http_app()` to accept `**kwargs` for FastMCP compatibility

### Verified Endpoints
- OAuth metadata: `/.well-known/oauth-authorization-server` - Working
- DCR registration: `/register` - Working
- Authorization: `/authorize` - Working

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "google-workspace": {
      "url": "https://mcp-vm.tail744e10.ts.net/workspace-dcr/mcp",
      "transport": "streamable-http"
    }
  }
}
```
