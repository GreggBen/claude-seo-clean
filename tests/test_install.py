"""Installation must preserve pre-existing Claude skills and agents."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "install.sh"


def install_environment(home: Path) -> dict[str, str]:
    binary_directory = home / "bin"
    binary_directory.mkdir()
    python = binary_directory / "python3"
    python.write_text(
        "#!/bin/sh\n"
        "mkdir -p \"$3/bin\"\n"
        "printf '#!/bin/sh\\nexit 0\\n' > \"$3/bin/pip\"\n"
        "chmod 755 \"$3/bin/pip\"\n"
    )
    python.chmod(0o755)
    return {**os.environ, "HOME": str(home), "PATH": f"{binary_directory}:{os.environ['PATH']}"}


class InstallTests(unittest.TestCase):
    def test_fresh_install_copies_skills_and_agents(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                ["bash", str(INSTALLER)],
                env=install_environment(home),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list((home / ".claude" / "skills").glob("seo*"))), 24)
            self.assertEqual(len(list((home / ".claude" / "agents").glob("seo-*.md"))), 16)

    def test_existing_skill_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            existing = home / ".claude" / "skills" / "seo" / "SKILL.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("personal skill\n")

            result = subprocess.run(
                ["bash", str(INSTALLER)],
                env=install_environment(home),
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("existe déjà", result.stderr)
            self.assertEqual(existing.read_text(), "personal skill\n")
            self.assertFalse((home / ".claude" / "agents").exists())

    def test_existing_agent_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            existing = home / ".claude" / "agents" / "seo-technical.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("personal agent\n")

            result = subprocess.run(
                ["bash", str(INSTALLER)],
                env=install_environment(home),
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("existe déjà", result.stderr)
            self.assertEqual(existing.read_text(), "personal agent\n")
            self.assertFalse((home / ".claude" / "skills").exists())


if __name__ == "__main__":
    unittest.main()
