"""Regression coverage for the repository-level skill lint."""

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "skills" / "seo" / "scripts" / "portability_check.py"
BACKLINKS_AUTH = REPO_ROOT / "skills" / "seo" / "scripts" / "backlinks_auth.py"
RUNNER = REPO_ROOT / "skills" / "seo" / "run-script"


class PortabilityCheckTests(unittest.TestCase):
    def test_checks_installed_skill_inventory(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), "--json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        report = json.loads(result.stdout)
        self.assertEqual(report["skills_checked"], 24)

        self.assertEqual(report["errors"], 0)

    def test_full_free_backlink_tier_has_no_paid_upgrade(self):
        with tempfile.TemporaryDirectory() as home:
            environment = os.environ.copy()
            environment.update({
                "HOME": home,
                "MOZ_API_KEY": "configured-moz-key",
                "BING_WEBMASTER_API_KEY": "configured-bing-key",
            })
            result = subprocess.run(
                [sys.executable, str(BACKLINKS_AUTH), "--tier", "--json"],
                cwd=REPO_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=True,
            )

        report = json.loads(result.stdout)
        self.assertEqual(report["tier"], 2)
        self.assertIsNone(report["missing"])

    def test_installed_runner_works_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(REPO_ROOT / "skills", root / "skills")
            working_directory = root / "unrelated-project"
            working_directory.mkdir()
            result = subprocess.run(
                [str(root / "skills" / "seo" / "run-script"),
                 "portability_check.py", "--json"],
                cwd=working_directory,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(json.loads(result.stdout)["skills_checked"], 24)

            interpreter = root / "skills" / "seo" / ".venv" / "bin" / "python"
            interpreter.parent.mkdir(parents=True)
            interpreter.write_text(
                "#!/usr/bin/env bash\n"
                "printf 'venv selected\\n' >&2\n"
                f"exec {shlex.quote(sys.executable)} \"$@\"\n"
            )
            interpreter.chmod(0o755)
            result = subprocess.run(
                [str(root / "skills" / "seo" / "run-script"),
                 "portability_check.py", "--json"],
                cwd=working_directory,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("venv selected", result.stderr)
            self.assertEqual(json.loads(result.stdout)["skills_checked"], 24)


if __name__ == "__main__":
    unittest.main()
