import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SCRIPT = REPO_ROOT / "examples" / "pi-consumer" / "install.sh"


def _write_stub(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class PiConsumerInstallScriptTests(unittest.TestCase):
    def test_resets_and_reinstalls_runtime_and_pi_bundle_into_selected_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            fake_bin = root / "bin"
            target = root / "target-workspace"
            home.joinpath(".pi", "agent").mkdir(parents=True, exist_ok=True)
            fake_bin.mkdir()
            target.mkdir()
            (target / ".pi").mkdir()
            (target / ".pi" / "stale.txt").write_text("old pi state\n", encoding="utf-8")
            (target / ".just-for-agents").mkdir()
            (target / ".just-for-agents" / "stale.txt").write_text("old runtime state\n", encoding="utf-8")
            (target / "just_for_agents").mkdir()
            (target / "just_for_agents" / "stale.txt").write_text("old python package state\n", encoding="utf-8")
            (target / "Justfile").write_text("stale\n", encoding="utf-8")

            _write_stub(
                fake_bin / "ollama",
                "#!/usr/bin/env bash\nexit 0\n",
            )
            _write_stub(
                fake_bin / "npm",
                "#!/usr/bin/env bash\nexit 0\n",
            )

            env = os.environ.copy()
            env["HOME"] = str(home)
            env["PATH"] = f"{fake_bin}:{env['PATH']}"

            subprocess.run(
                ["bash", str(INSTALL_SCRIPT), str(target)],
                check=True,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertTrue((target / "Justfile").is_file())
            self.assertTrue((target / ".just-for-agents").is_dir())
            self.assertTrue((target / "just_for_agents").is_dir())
            self.assertTrue((target / "VERSION").is_file())
            self.assertTrue((target / "README.md").is_file())
            self.assertTrue((target / "CHANGELOG.md").is_file())
            self.assertTrue((target / ".pi" / "settings.json").is_file())
            self.assertTrue((target / ".pi" / "extensions" / "just-consumer.ts").is_file())
            self.assertTrue((target / ".pi" / "extensions" / "package.json").is_file())
            self.assertTrue((target / ".pi" / "consumer-profile.json").is_file())
            self.assertTrue((home / ".pi" / "agent" / "models.json").is_file())
            self.assertFalse((target / ".pi" / "stale.txt").exists())
            self.assertFalse((target / ".just-for-agents" / "stale.txt").exists())
            self.assertFalse((target / "just_for_agents" / "stale.txt").exists())
            self.assertNotEqual((target / "Justfile").read_text(encoding="utf-8"), "stale\n")


if __name__ == "__main__":
    unittest.main()
