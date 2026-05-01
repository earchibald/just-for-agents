import tempfile
import unittest
from pathlib import Path

from just_for_agents.managed_paths import (
    DEFAULT_MANAGED_TOML,
    ManagedPaths,
    ensure_managed_layout,
)


class EnsureManagedLayoutTests(unittest.TestCase):
    def test_creates_full_directory_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = ensure_managed_layout(Path(tmp))

            for directory in (
                paths.managed_root,
                paths.config_dir,
                paths.quarantine_requests_dir,
                paths.approved_recipes_dir,
                paths.approved_includes_dir,
                paths.rejected_requests_dir,
                paths.history_dir,
            ):
                self.assertTrue(directory.is_dir(), f"missing dir: {directory}")

            self.assertTrue(paths.config_file.is_file())
            self.assertEqual(paths.config_file.read_text(), DEFAULT_MANAGED_TOML)
            self.assertTrue(paths.approved_include_file.is_file())
            self.assertTrue(paths.decisions_log.is_file())
            self.assertEqual(paths.decisions_log.read_text(), "")

    def test_is_idempotent_and_preserves_user_edits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = ensure_managed_layout(Path(tmp))

            paths.config_file.write_text("[approval]\nallow_self_approval = false\n")
            paths.decisions_log.write_text('{"decision":"approve"}\n')
            paths.approved_include_file.write_text("# operator-touched\n")

            paths_again = ensure_managed_layout(Path(tmp))

            self.assertEqual(paths_again.managed_root, paths.managed_root)
            self.assertEqual(
                paths.config_file.read_text(),
                "[approval]\nallow_self_approval = false\n",
            )
            self.assertEqual(paths.decisions_log.read_text(), '{"decision":"approve"}\n')
            self.assertEqual(paths.approved_include_file.read_text(), "# operator-touched\n")

    def test_managed_paths_resolution_is_pure(self) -> None:
        # No filesystem touch — ManagedPaths is just path arithmetic.
        paths = ManagedPaths(repo_root=Path("/nonexistent/repo"))
        self.assertEqual(
            paths.managed_root, Path("/nonexistent/repo/.just-for-agents/managed")
        )
        self.assertEqual(
            paths.approved_include_file,
            Path("/nonexistent/repo/.just-for-agents/managed/approved/includes/managed.just"),
        )
        self.assertFalse(paths.managed_root.exists())


if __name__ == "__main__":
    unittest.main()
