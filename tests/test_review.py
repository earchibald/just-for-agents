import json
import tempfile
import unittest
from pathlib import Path

from just_for_agents.dry_run import run_request_dry_run
from just_for_agents.history import append_decision
from just_for_agents.managed_paths import ensure_managed_layout
from just_for_agents.request_store import RequestStore
from just_for_agents.review import render_dashboard_text, write_dashboard, write_request_review


def _setup_repo(tmp: str):
    repo_root = Path(tmp)
    repo_root.joinpath("Justfile").write_text(
        "import? '.just-for-agents/managed/approved/includes/managed.just'\n",
        encoding="utf-8",
    )
    paths = ensure_managed_layout(repo_root)
    return paths, RequestStore(paths)


class RequestReviewTests(unittest.TestCase):
    def test_write_request_review_renders_html_with_diff_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            (paths.approved_recipes_dir / "hello.just").write_text(
                "hello:\n    echo approved\n", encoding="utf-8"
            )
            request = store.create(
                source="manual-edit",
                target_recipes=["hello"],
                author_label="operator",
                review_notes="check updated command",
            )
            candidate = paths.quarantine_requests_dir / request.request_id / "candidate.just"
            candidate.write_text("hello:\n    echo candidate\n", encoding="utf-8")
            run_request_dry_run(paths, store, request.request_id)

            payload = write_request_review(paths, store, request.request_id)

            html = Path(payload["review_path"]).read_text(encoding="utf-8")
            self.assertIn("Managed request review", html)
            self.assertIn(request.request_id, html)
            self.assertIn("echo approved", html)
            self.assertIn("echo candidate", html)
            self.assertIn("dry-run passed for hello", html)
            self.assertIn("candidate.just", html)


class DashboardTests(unittest.TestCase):
    def test_dashboard_lists_queue_library_and_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            (paths.approved_recipes_dir / "hello.just").write_text(
                "hello:\n    echo live\n", encoding="utf-8"
            )
            append_decision(
                paths,
                {
                    "request_id": "req-20260501-001",
                    "decision": "approve",
                    "managed_commit": "abc1234",
                    "target_recipes": ["hello"],
                },
            )
            request = store.create(source="manual-add", target_recipes=["world"])
            candidate = paths.quarantine_requests_dir / request.request_id / "candidate.just"
            candidate.write_text("world:\n    echo queued\n", encoding="utf-8")
            run_request_dry_run(paths, store, request.request_id)

            text = render_dashboard_text(paths, store)
            payload = write_dashboard(paths, store)
            html = Path(payload["dashboard_path"]).read_text(encoding="utf-8")

            self.assertIn("Queue", text)
            self.assertIn(request.request_id, text)
            self.assertIn("Library", text)
            self.assertIn("hello", text)
            self.assertIn("[approval] allow_self_approval = True", text)
            self.assertIn("Managed operator dashboard", html)
            self.assertIn("abc1234", html)
            self.assertIn(request.request_id, html)


if __name__ == "__main__":
    unittest.main()
