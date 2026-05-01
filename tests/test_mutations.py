import json
import tempfile
import unittest
from pathlib import Path

from just_for_agents.managed_paths import ensure_managed_layout
from just_for_agents.mutations import (
    MutationError,
    create_delete_request,
    create_edit_request,
    create_new_request,
)
from just_for_agents.request_store import RequestStore


def _setup(tmp: str):
    paths = ensure_managed_layout(Path(tmp))
    return paths, RequestStore(paths)


class CreateNewRequestTests(unittest.TestCase):
    def test_writes_candidate_without_touching_live_include(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)

            request, candidate = create_new_request(
                paths,
                store,
                recipe_name="hello",
                command="echo hi",
                desc='Say "hi"',
                params="name='world'",
                author_label="operator",
                review_notes="drafted by hand",
            )

            self.assertEqual(request.source, "manual-add")
            self.assertEqual(request.target_recipes, ["hello"])
            self.assertTrue(candidate.is_file())
            self.assertEqual(
                candidate.read_text(encoding="utf-8"),
                '[doc("@desc Say \\"hi\\"")]\nhello name=\'world\':\n    echo hi\n',
            )
            self.assertNotIn("import ", paths.approved_include_file.read_text(encoding="utf-8"))

            on_disk = json.loads(store.request_file(request.request_id).read_text(encoding="utf-8"))
            self.assertEqual(on_disk["author_label"], "operator")
            self.assertEqual(on_disk["review_notes"], "drafted by hand")

    def test_rejects_duplicate_approved_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            (paths.approved_recipes_dir / "hello.just").write_text("hello:\n    :\n", encoding="utf-8")

            with self.assertRaises(MutationError):
                create_new_request(paths, store, recipe_name="hello", command="echo hi")


class CreateEditRequestTests(unittest.TestCase):
    def test_clones_approved_recipe_into_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            approved = paths.approved_recipes_dir / "hello.just"
            approved.write_text("hello who='world':\n    echo {{who}}\n", encoding="utf-8")

            request, candidate = create_edit_request(paths, store, recipe_name="hello")

            self.assertEqual(request.source, "manual-edit")
            self.assertEqual(candidate.read_text(encoding="utf-8"), approved.read_text(encoding="utf-8"))
            self.assertEqual(approved.read_text(encoding="utf-8"), "hello who='world':\n    echo {{who}}\n")

    def test_requires_approved_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            with self.assertRaises(MutationError):
                create_edit_request(paths, store, recipe_name="missing")


class CreateDeleteRequestTests(unittest.TestCase):
    def test_writes_tombstone_and_leaves_approved_recipe_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            approved = paths.approved_recipes_dir / "hello.just"
            approved.write_text("hello:\n    echo hi\n", encoding="utf-8")

            request, tombstone = create_delete_request(
                paths,
                store,
                recipe_name="hello",
                author_label="operator",
            )

            self.assertEqual(request.source, "manual-delete")
            self.assertTrue(approved.is_file())
            self.assertTrue(tombstone.is_file())
            self.assertEqual(
                json.loads(tombstone.read_text(encoding="utf-8")),
                {
                    "action": "delete",
                    "approved_path": "hello.just",
                    "recipe_name": "hello",
                },
            )

    def test_requires_approved_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, store = _setup(tmp)
            with self.assertRaises(MutationError):
                create_delete_request(paths, store, recipe_name="missing")


if __name__ == "__main__":
    unittest.main()
