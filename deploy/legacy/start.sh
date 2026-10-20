#!/bin/bash
set -e
cd /home/user/workspace-mcp
source .env
export GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET USER_GOOGLE_EMAIL WORKSPACE_MCP_PORT WORKSPACE_MCP_HOST OAUTHLIB_INSECURE_TRANSPORT
export HOME=/home/user
source /home/user/.local/bin/env
exec /home/user/workspace-mcp/cert-runtime-20261020/bin/python /home/user/workspace-mcp/cert-runtime-20261020/bin/workspace-mcp --transport streamable-http --tool-tier complete --single-user 2>&1
