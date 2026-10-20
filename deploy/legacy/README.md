# Pinned Workspace MCP deployment

This directory records the certificate-only correction installed on 2026-10-20.
It belongs to `workspace-mcp.service` on port 8002, not the DCR service on port
8003. The packaged service runs **workspace-mcp 1.28.0**; the repository source
and its root `uv.lock` describe the separate **1.9.0 DCR** application.

`requirements.lock` records the complete installed Linux / Python 3.11 package
versions, including `certifi==2026.10.19`. It is a version inventory, not a
hash-verified export. Do not use it to update the DCR service or resolve newer
package versions.

`start.sh` is the installed launcher. It uses the preserved runtime at
`/home/user/workspace-mcp/cert-runtime-20261020` directly. Startup must never
invoke `uvx`, install packages, or resolve dependencies. A missing runtime must
fail rather than fall back to a download. The existing deployment `.env` stays
on the host; no credentials are stored here.

For a future authorized rebuild, stage the pinned inventory in a new Linux /
Python 3.11 environment, validate artifact hashes from the package registry,
check dependency compatibility and exact package versions, and verify the
application version, certificate rejection, and `/health` before switching the
launcher. Do not overwrite an active environment. Changing the runtime path
requires explicit release review; this source commit does not deploy anything.

The original binaries, locks, and verification records remain on the host under
`/var/backups/jrc-certificates-20261020`. Restoring old certificate packages would
restore the reported exposure; rollback needs a separate security decision.
