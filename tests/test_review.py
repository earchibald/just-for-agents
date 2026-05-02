import json
import tempfile
import unittest
from pathlib import Path

from just_for_agents.dry_run import run_request_dry_run
from just_for_agents.history import append_decision, commit_approval, ensure_managed_repo
from just_for_agents.managed_paths import ensure_managed_layout
from just_for_agents.projection import write_include
from just_for_agents.request_store import RequestStore
from just_for_agents.review import (
    ReviewError,
    render_dashboard_text,
    write_dashboard,
    write_request_review,
)


def _setup_repo(tmp: str):
    repo_root = Path(tmp)
    repo_root.joinpath("Justfile").write_text(
        "import? '.just-for-agents/managed/approved/includes/managed.just'\n",
        encoding="utf-8",
    )
    paths = ensure_managed_layout(repo_root)
    return paths, RequestStore(paths)


def _seed_approved_recipe(
    paths,
    *,
    recipe_name: str,
    body: str,
    request_id: str = "req-20260501-001",
    managed_commit: str = "abc1234",
) -> None:
    ensure_managed_repo(paths)
    (paths.approved_recipes_dir / f"{recipe_name}.just").write_text(body, encoding="utf-8")
    write_include(paths)
    append_decision(
        paths,
        {
            "request_id": request_id,
            "decision": "approve",
            "managed_commit": managed_commit,
            "target_recipes": [recipe_name],
        },
    )
    commit_approval(paths, request_id=request_id, action="recipe")


def _write_invalid_multi_target_request(paths, request_id: str) -> Path:
    request_dir = paths.quarantine_requests_dir / request_id
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "request.json").write_text(
        json.dumps(
            {
                "request_id": request_id,
                "source": "manual-add",
                "status": "quarantined",
                "created_at": "2026-05-01T12:00:00+00:00",
                "updated_at": "2026-05-01T12:00:00+00:00",
                "target_recipes": ["hello", "world"],
                "author_label": "",
                "review_notes": "",
                "risk_flags": [],
                "dry_run_summary": "",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return request_dir


class RequestReviewTests(unittest.TestCase):
    def test_write_request_review_renders_html_with_diff_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            _seed_approved_recipe(
                paths,
                recipe_name="hello",
                body="hello:\n    echo approved\n",
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
            self.assertIn("Managed history", html)
            self.assertIn("clean", html)

    def test_write_request_review_surfaces_drift_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            _seed_approved_recipe(
                paths,
                recipe_name="hello",
                body="hello:\n    echo approved\n",
            )
            (paths.approved_recipes_dir / "hello.just").write_text(
                "hello:\n    echo drifted\n", encoding="utf-8"
            )
            request = store.create(source="manual-edit", target_recipes=["hello"])
            candidate = paths.quarantine_requests_dir / request.request_id / "candidate.just"
            candidate.write_text("hello:\n    echo candidate\n", encoding="utf-8")

            payload = write_request_review(paths, store, request.request_id)

            html = Path(payload["review_path"]).read_text(encoding="utf-8")
            self.assertIn("drifted", html)
            self.assertIn("approved/recipes/hello.just", html)

    def test_write_request_review_rejects_multi_target_request_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            request_id = "req-20260501-001"
            request_dir = _write_invalid_multi_target_request(paths, request_id)
            (request_dir / "candidate.just").write_text(
                "hello:\n    echo candidate\n", encoding="utf-8"
            )

            with self.assertRaises(ReviewError) as ctx:
                write_request_review(paths, store, request_id)

            self.assertIn("exactly one recipe", str(ctx.exception))


class DashboardTests(unittest.TestCase):
    def test_dashboard_lists_queue_library_and_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            _seed_approved_recipe(
                paths,
                recipe_name="hello",
                body="hello:\n    echo live\n",
            )
            request = store.create(source="manual-add", target_recipes=["world"])
            candidate = paths.quarantine_requests_dir / request.request_id / "candidate.just"
            candidate.write_text("world:\n    echo queued\n", encoding="utf-8")
            run_request_dry_run(paths, store, request.request_id)

            text = render_dashboard_text(paths, store)
            payload = write_dashboard(paths, store)
            html = Path(payload["dashboard_path"]).read_text(encoding="utf-8")

            self.assertIn("Managed history", text)
            self.assertIn("clean\tmanaged approved surface matches the last approved commit", text)
            self.assertIn("Queue", text)
            self.assertIn(request.request_id, text)
            self.assertIn("Library", text)
            self.assertIn("hello", text)
            self.assertIn("[approval] allow_self_approval = True", text)
            self.assertIn("Managed operator dashboard", html)
            self.assertIn("abc1234", html)
            self.assertIn(request.request_id, html)

    def test_dashboard_surfaces_drift_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            _seed_approved_recipe(
                paths,
                recipe_name="hello",
                body="hello:\n    echo live\n",
            )
            paths.approved_include_file.write_text("# drifted by hand\n", encoding="utf-8")

            text = render_dashboard_text(paths, store)
            html = Path(write_dashboard(paths, store)["dashboard_path"]).read_text(encoding="utf-8")

            self.assertIn("drifted", text)
            self.assertIn("approved/includes/managed.just", text)
            self.assertIn("drifted", html)
            self.assertIn("approved/includes/managed.just", html)

    def test_dashboard_rejects_multi_target_request_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup_repo(tmp)
            _write_invalid_multi_target_request(paths, "req-20260501-001")

            with self.assertRaises(ReviewError) as ctx:
                render_dashboard_text(paths, store)

            self.assertIn("exactly one recipe", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
