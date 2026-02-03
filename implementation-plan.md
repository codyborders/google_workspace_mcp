# MCP OAuth 2.1 Dynamic Client Registration (DCR) Implementation Plan

## Problem Statement
Claude Desktop cannot connect to a remote workspace-mcp server because the server doesn't properly expose MCP OAuth 2.1 with Dynamic Client Registration (DCR).

## Root Cause Analysis
FastMCP's `GoogleProvider` **already implements DCR** at `/oauth/*` paths, but `oauth_config.py` advertises endpoints at `/oauth2/*` paths. This metadata mismatch causes client registration to fail.

**Evidence:**
- `oauth_config.py:332` returns `"registration_endpoint": f"{oauth_base}/oauth2/register"`
- FastMCP mounts routes at `/oauth/register`, `/oauth/authorize`, `/oauth/token`
- Clients discover endpoints via `/.well-known/oauth-authorization-server` and get wrong paths

---

## Implementation Approach: Test-Driven Development

Following PYTHON.md guidelines:
1. Design first: Define interfaces and data structures
2. Write tests: Create failing tests (TDD approach)
3. Implement incrementally: Build in small, testable chunks
4. Document: Write docstrings and update documentation
5. Refactor: Clean up code while tests pass

---

## 5-Subagent Parallel Implementation Strategy

### Subagent 1: Test Infrastructure Setup
**Focus**: Create test foundation and fixtures

Tasks:
- Create `tests/auth/__init__.py`
- Create `tests/auth/conftest.py` with shared fixtures:
  - `@pytest.fixture` for OAuth-enabled test client
  - `@pytest.fixture` for mock Google credentials
  - `@pytest.fixture` for test environment setup
- Ensure pytest-asyncio configuration is correct

**Files to create:**
- `tests/auth/__init__.py`
- `tests/auth/conftest.py`

---

### Subagent 2: Discovery Tests
**Focus**: Diagnose current DCR state

Tasks:
- Create `tests/auth/test_dcr_discovery.py`
- Write tests to discover actual endpoint paths:
  - `test_well_known_oauth_metadata_exists()`
  - `test_fastmcp_oauth_register_exists()` - test `/oauth/register`
  - `test_custom_oauth2_register_exists()` - test `/oauth2/register`
  - `test_metadata_registration_endpoint_path()`

**Files to create:**
- `tests/auth/test_dcr_discovery.py`

---

### Subagent 3: RFC 7591 Compliance Tests
**Focus**: Verify DCR follows RFC 7591 specification

Tasks:
- Create `tests/auth/test_dcr_rfc7591.py`
- Write compliance tests:
  - `test_dcr_accepts_minimal_request()` - only redirect_uris required
  - `test_dcr_accepts_authorization_code_only()` - no refresh_token needed
  - `test_dcr_returns_required_fields()` - client_id in response
  - `test_dcr_preserves_client_metadata()` - echoes back client_name
  - `test_dcr_rejects_invalid_redirect_uri()`

**Files to create:**
- `tests/auth/test_dcr_rfc7591.py`

---

### Subagent 4: Integration Tests (Claude Desktop Simulation)
**Focus**: End-to-end OAuth flow testing

Tasks:
- Create `tests/auth/test_dcr_integration.py`
- Write integration tests:
  - `test_full_dcr_oauth_flow()` - complete flow simulation
  - `test_metadata_endpoints_match_actual_routes()`
  - `test_authorization_redirects_to_google()`
  - `test_pkce_challenge_required()`

**Files to create:**
- `tests/auth/test_dcr_integration.py`

---

### Subagent 5: Implementation & Metadata Fix
**Focus**: Fix the metadata mismatch and verify routes

Tasks:
1. **Fix metadata paths** in `auth/oauth_config.py` (lines 315-356):
   ```python
   def get_authorization_server_metadata(self, scopes=None) -> Dict[str, Any]:
       oauth_base = self.get_oauth_base_url()
       return {
           "issuer": oauth_base,
           "authorization_endpoint": f"{oauth_base}/oauth/authorize",
           "token_endpoint": f"{oauth_base}/oauth/token",
           "registration_endpoint": f"{oauth_base}/oauth/register",
           # ... rest unchanged
       }
   ```

2. **Add route logging** in `core/server.py` for debugging:
   ```python
   logger.info(f"OAuth routes mounted: {[r.path for r in provider.get_routes()]}")
   ```

3. **Update docstrings** to document the OAuth 2.1 DCR flow

**Files to modify:**
- `auth/oauth_config.py` - Fix paths in `get_authorization_server_metadata()`
- `core/server.py` - Add route logging (optional)

---

## Files Summary

| File | Action | Subagent |
|------|--------|----------|
| `tests/auth/__init__.py` | Create | 1 |
| `tests/auth/conftest.py` | Create | 1 |
| `tests/auth/test_dcr_discovery.py` | Create | 2 |
| `tests/auth/test_dcr_rfc7591.py` | Create | 3 |
| `tests/auth/test_dcr_integration.py` | Create | 4 |
| `auth/oauth_config.py` | Modify (lines 315-356) | 5 |
| `core/server.py` | Modify (add logging) | 5 |

---

## Verification Strategy

### Automated Tests
```bash
# Activate venv first
source .venv/bin/activate || python -m venv .venv && source .venv/bin/activate

# Install test dependencies
uv sync --group test

# Run all auth tests with coverage
uv run pytest tests/auth/ -v --cov=auth --cov-report=term-missing

# Run specific test files
uv run pytest tests/auth/test_dcr_discovery.py -v
uv run pytest tests/auth/test_dcr_rfc7591.py -v
uv run pytest tests/auth/test_dcr_integration.py -v
```

### Manual Test with Remote Server
1. Deploy to remote server with:
   ```bash
   export MCP_ENABLE_OAUTH21=true
   export WORKSPACE_EXTERNAL_URL=https://your-server.example.com
   export GOOGLE_OAUTH_CLIENT_ID=your-client-id
   export GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   uv run main.py --transport streamable-http
   ```

2. Configure Claude Desktop:
   ```json
   {
     "mcpServers": {
       "google-workspace": {
         "url": "https://your-server.example.com/mcp",
         "transport": "streamable-http"
       }
     }
   }
   ```

3. Verify: Claude Desktop registers, user authenticates, tools work.

---

## Success Criteria

1. All tests in `tests/auth/` pass
2. Test coverage for auth module >80%
3. `/.well-known/oauth-authorization-server` returns paths matching actual routes
4. DCR endpoint accepts registration and returns `client_id`
5. Claude Desktop can connect to remote server and use Google Workspace tools

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FastMCP DCR bug (issue #2460) | Check FastMCP version >=2.14.4, upgrade if needed |
| CORS issues with remote clients | FastMCP handles CORS; verify headers in tests |
| Metadata discovery caching | Test with fresh client instances |
| Breaking existing OAuth 2.0 flow | Keep OAuth 2.0 paths as fallback, test both |

---

## Code Style Requirements (from PYTHON.md)

- Type hints on all function signatures
- Google-style docstrings with Args, Returns, Raises
- Arrange/Act/Assert pattern in tests
- pytest fixtures in conftest.py
- Specific exceptions (not generic Exception)
- Logging with appropriate levels
