import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from just_for_agents.managed_paths import ensure_managed_layout
from just_for_agents.request_store import RequestStore


def _store(tmp: str) -> RequestStore:
    paths = ensure_managed_layout(Path(tmp))
    return RequestStore(paths)


class RequestStoreTests(unittest.TestCase):
    def test_create_persists_request_with_quarantined_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

            request = store.create(
                source="escalation",
                target_recipes=["fancy-tool"],
                author_label="agent-a",
                review_notes="initial draft",
                risk_flags=["uses-network"],
                now=now,
            )

            self.assertEqual(request.request_id, "req-20260501-001")
            self.assertEqual(request.status, "quarantined")
            self.assertEqual(request.source, "escalation")
            self.assertEqual(request.target_recipes, ["fancy-tool"])
            self.assertEqual(request.created_at, "2026-05-01T12:00:00+00:00")

            on_disk = json.loads(store.request_file(request.request_id).read_text())
            self.assertEqual(on_disk, request.to_dict())

    def test_get_returns_none_for_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertIsNone(store.get("req-19990101-001"))

    def test_round_trip_via_get(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            created = store.create(source="manual-add", target_recipes=["x"])
            loaded = store.get(created.request_id)
            self.assertEqual(loaded, created)

    def test_ids_increment_within_same_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            now = datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
            ids = [
                store.create(source="manual-add", target_recipes=[f"r{i}"], now=now).request_id
                for i in range(3)
            ]
            self.assertEqual(ids, ["req-20260501-001", "req-20260501-002", "req-20260501-003"])

    def test_list_quarantined_returns_only_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a = store.create(source="manual-add", target_recipes=["a"])
            b = store.create(source="escalation", target_recipes=["b"])

            # Mutate b on disk to look approved; list_quarantined should drop it.
            data = json.loads(store.request_file(b.request_id).read_text())
            data["status"] = "approved"
            store.request_file(b.request_id).write_text(json.dumps(data))

            quarantined = store.list_quarantined()
            self.assertEqual([r.request_id for r in quarantined], [a.request_id])

    def test_unknown_source_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                store.create(source="bogus", target_recipes=["x"])


if __name__ == "__main__":
    unittest.main()
