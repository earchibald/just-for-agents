import json
import tempfile
import unittest
from pathlib import Path

from just_for_agents.dry_run import load_dry_run_result, run_request_dry_run
from just_for_agents.managed_paths import ensure_managed_layout
from just_for_agents.request_store import RequestStore


def _setup_repo(tmp: str):
    repo_root = Path(tmp)
    repo_root.joinpath("Justfile").write_text(
        "import? '.just-for-agents/managed/approved/includes/managed.just'\n\nhelper:\n    echo helper\n",
        encoding="utf-8",
    )
    paths = ensure_managed_layout(repo_root)
    return paths, RequestStore(paths)


class RunRequestDryRunTests(unittest.TestCase):
    def test_records_candidate_dry_run_and_updates_request_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            request = store.create(source="manual-add", target_recipes=["hello"])
            candidate = paths.quarantine_requests_dir / request.request_id / "candidate.just"
            candidate.write_text("hello:\n    echo hi\n", encoding="utf-8")

            payload = run_request_dry_run(paths, store, request.request_id)

            self.assertEqual(payload["status"], "passed")
            self.assertIn("dry-run passed for hello", payload["summary"])
            self.assertTrue(Path(payload["result_path"]).is_file())
            self.assertTrue(Path(payload["preview_path"]).is_file())
            self.assertIn("echo hi", Path(payload["preview_path"]).read_text(encoding="utf-8"))

            on_disk = json.loads(store.request_file(request.request_id).read_text(encoding="utf-8"))
            self.assertEqual(on_disk["dry_run_summary"], payload["summary"])
            self.assertEqual(load_dry_run_result(paths, request.request_id)["status"], "passed")

    def test_edit_request_dry_run_uses_candidate_body_not_live_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            (paths.approved_recipes_dir / "hello.just").write_text(
                "hello:\n    echo approved\n", encoding="utf-8"
            )
            request = store.create(source="manual-edit", target_recipes=["hello"])
            candidate = paths.quarantine_requests_dir / request.request_id / "candidate.just"
            candidate.write_text("hello:\n    echo candidate\n", encoding="utf-8")

            payload = run_request_dry_run(paths, store, request.request_id)

            preview = Path(payload["preview_path"]).read_text(encoding="utf-8")
            self.assertEqual(payload["status"], "passed")
            self.assertIn("echo candidate", preview)
            self.assertNotIn("echo approved", preview)

    def test_delete_request_records_skipped_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            (paths.approved_recipes_dir / "hello.just").write_text(
                "hello:\n    echo live\n", encoding="utf-8"
            )
            request = store.create(source="manual-delete", target_recipes=["hello"])
            tombstone = paths.quarantine_requests_dir / request.request_id / "tombstone.json"
            tombstone.write_text(
                json.dumps({"action": "delete", "recipe_name": "hello"}, indent=2) + "\n",
                encoding="utf-8",
            )

            payload = run_request_dry_run(paths, store, request.request_id)

            self.assertEqual(payload["status"], "skipped")
            self.assertIn("delete request has no candidate recipe body", payload["summary"])
            self.assertEqual(payload["recipe_results"][0]["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
