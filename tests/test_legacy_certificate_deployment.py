"""Offline checks for the recorded certificate-only production launcher."""

import subprocess
import tempfile
import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1] / "deploy" / "legacy"


class LegacyCertificateDeploymentTests(unittest.TestCase):
    def test_versions_are_exact_and_separate_from_dcr(self):
        lines = (DEPLOY / "requirements.lock").read_text().splitlines()
        packages = {}
        for line in lines:
            if not line or line.startswith("#"):
                continue
            name, version = line.split("==")
            self.assertNotIn(name, packages)
            self.assertNotIn(" ", version)
            packages[name] = version
        self.assertEqual(packages["workspace-mcp"], "1.28.0")
        self.assertEqual(packages["certifi"], "2026.10.19")

    def run_launcher(self, *, runtime=True, environment=True):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            service = home / "workspace-mcp"
            service.mkdir()
            if environment:
                (service / ".env").write_text("WORKSPACE_MCP_PORT=8002\n")
            shell_env = home / ".local" / "bin"
            shell_env.mkdir(parents=True)
            (shell_env / "env").write_text("")
            if runtime:
                binary_dir = service / "cert-runtime-20261020" / "bin"
                binary_dir.mkdir(parents=True)
                python = binary_dir / "python"
                python.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
                python.chmod(0o755)
            launcher = home / "start.sh"
            launcher.write_text(
                (DEPLOY / "start.sh").read_text().replace("/home/user", str(home))
            )
            return subprocess.run(
                ["/bin/bash", str(launcher)],
                env={"PATH": "/usr/bin:/bin", "HOME": str(home)},
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

    def test_start_uses_existing_runtime_without_package_resolution(self):
        source = (DEPLOY / "start.sh").read_text()
        self.assertNotIn("uvx", source)
        self.assertNotIn("pip install", source)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.splitlines()[0].endswith("/bin/workspace-mcp"))
        self.assertEqual(
            result.stdout.splitlines()[1:],
            [
                "--transport",
                "streamable-http",
                "--tool-tier",
                "complete",
                "--single-user",
            ],
        )

    def test_missing_runtime_fails_closed(self):
        self.assertNotEqual(self.run_launcher(runtime=False).returncode, 0)

    def test_missing_environment_fails_closed(self):
        self.assertNotEqual(self.run_launcher(environment=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
