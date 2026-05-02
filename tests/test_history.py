import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from just_for_agents.drift import managed_surface_status
from just_for_agents.history import (
    ApprovalError,
    append_decision,
    approve_request,
    commit_approval,
    ensure_managed_repo,
)
from just_for_agents.managed_paths import ensure_managed_layout
from just_for_agents.request_store import RequestStore


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _setup(tmp: str):
    paths = ensure_managed_layout(Path(tmp))
    return paths, RequestStore(paths)


def _quarantined_request_with_candidate(
    paths,
    store,
    *,
    target_recipes,
    candidate_body: str = "@hello:\n    echo hi\n",
    now=None,
):
    request = store.create(
        source="manual-add",
        target_recipes=target_recipes,
        author_label="tester",
        now=now,
    )
    candidate = paths.quarantine_requests_dir / request.request_id / "candidate.just"
    candidate.write_text(candidate_body, encoding="utf-8")
    return request


class EnsureManagedRepoTests(unittest.TestCase):
    def test_initializes_git_repo_with_one_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _setup(tmp)
            repo = ensure_managed_repo(paths)

            self.assertTrue((repo / ".git").is_dir())
            log = _git(repo, "log", "--oneline").strip().splitlines()
            self.assertEqual(len(log), 1)
            self.assertIn("initialize managed overlay", log[0])

    def test_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _setup(tmp)
            ensure_managed_repo(paths)
            head_before = _git(paths.managed_root, "rev-parse", "HEAD").strip()
            ensure_managed_repo(paths)
            head_after = _git(paths.managed_root, "rev-parse", "HEAD").strip()
            self.assertEqual(head_before, head_after)


class ManagedSurfaceStatusTests(unittest.TestCase):
    def test_reports_uninitialized_before_first_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _setup(tmp)
            status = managed_surface_status(paths)
            self.assertEqual(status.status, "uninitialized")
            self.assertIn("quarantine-first", status.summary)


class AppendDecisionTests(unittest.TestCase):
    def test_appends_one_json_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _setup(tmp)
            append_decision(paths, {"request_id": "r1", "decision": "approve"})
            append_decision(paths, {"request_id": "r2", "decision": "reject"})
            lines = paths.decisions_log.read_text().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["request_id"], "r1")
            self.assertEqual(json.loads(lines[1])["decision"], "reject")


class CommitApprovalTests(unittest.TestCase):
    def test_creates_commit_capturing_managed_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _setup(tmp)
            ensure_managed_repo(paths)
            (paths.approved_recipes_dir / "foo.just").write_text("@foo:\n    :\n")
            sha = commit_approval(paths, request_id="req-x", action="recipe")
            self.assertTrue(sha)
            log = _git(paths.managed_root, "log", "--oneline").strip().splitlines()
            self.assertEqual(len(log), 2)
            self.assertIn("approve recipe from req-x", log[0])


class ApproveRequestTests(unittest.TestCase):
    def test_approves_quarantined_request_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
            request = _quarantined_request_with_candidate(
                paths, store, target_recipes=["hello"], now=now
            )

            entry = approve_request(
                paths,
                store,
                request.request_id,
                operator_label="op",
                rationale="looks good",
                now=now,
            )

            # Projection: the approved recipe and rebuilt include both exist.
            approved = paths.approved_recipes_dir / "hello.just"
            self.assertTrue(approved.is_file())
            self.assertIn(
                'import "../recipes/hello.just"',
                paths.approved_include_file.read_text(),
            )

            # Status flipped on the persisted request.
            on_disk = json.loads(store.request_file(request.request_id).read_text())
            self.assertEqual(on_disk["status"], "approved")

            # Ledger captured one approval entry referencing the new commit.
            lines = paths.decisions_log.read_text().splitlines()
            self.assertEqual(len(lines), 1)
            ledger = json.loads(lines[0])
            self.assertEqual(ledger["decision"], "approve")
            self.assertEqual(ledger["operator_label"], "op")
            self.assertEqual(ledger["rationale"], "looks good")
            self.assertEqual(ledger["managed_commit"], entry["managed_commit"])
            self.assertEqual(ledger["request_id"], request.request_id)

            # Exactly one new commit beyond the init commit.
            log = _git(paths.managed_root, "log", "--oneline").strip().splitlines()
            self.assertEqual(len(log), 2)
            self.assertIn(request.request_id, log[0])

    def test_double_approval_errors_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            request = _quarantined_request_with_candidate(
                paths, store, target_recipes=["x"]
            )
            approve_request(paths, store, request.request_id)
            with self.assertRaises(ApprovalError):
                approve_request(paths, store, request.request_id)

    def test_unknown_request_errors_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            with self.assertRaises(ApprovalError):
                approve_request(paths, store, "req-19990101-001")

    def test_missing_candidate_errors_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            request = store.create(source="manual-add", target_recipes=["nope"])
            # No candidate.just written.
            with self.assertRaises(ApprovalError):
                approve_request(paths, store, request.request_id)

    def test_rejects_multi_target_request_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            request_id = "req-20260501-001"
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
            (request_dir / "candidate.just").write_text("@hello:\n    echo hi\n", encoding="utf-8")

            with self.assertRaises(ApprovalError) as ctx:
                approve_request(paths, store, request_id)

            self.assertIn("exactly one recipe", str(ctx.exception))

    def test_refuses_approval_when_governed_surface_has_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            original = _quarantined_request_with_candidate(
                paths, store, target_recipes=["hello"]
            )
            approve_request(paths, store, original.request_id)

            (paths.approved_recipes_dir / "hello.just").write_text(
                "@hello:\n    echo drift\n", encoding="utf-8"
            )
            follow_up = _quarantined_request_with_candidate(
                paths,
                store,
                target_recipes=["hello"],
                candidate_body="@hello:\n    echo replacement\n",
            )

            with self.assertRaises(ApprovalError) as ctx:
                approve_request(paths, store, follow_up.request_id)

            self.assertIn("drift detected", str(ctx.exception))
            self.assertIn("approved/recipes/hello.just", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
