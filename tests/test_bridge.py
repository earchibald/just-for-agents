import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_PATH = REPO_ROOT / ".just-for-agents" / "bridge.py"


def _load_bridge_module():
    spec = importlib.util.spec_from_file_location("jfa_bridge", BRIDGE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BridgeParseTests(unittest.TestCase):
    def test_parse_preserves_quoted_default_with_spaces(self) -> None:
        bridge = _load_bridge_module()
        list_output = """Available recipes:\ncreate-text-file path='test.txt' content='hello world'\n"""

        with patch.object(
            bridge.subprocess,
            "check_output",
            return_value=list_output.encode("utf-8"),
        ):
            payload = bridge.parse()

        tool = payload["tools"][0]
        self.assertEqual(tool["name"], "create-text-file")
        self.assertEqual(
            tool["parameters"],
            [
                {"name": "path", "required": False, "default": "test.txt"},
                {"name": "content", "required": False, "default": "hello world"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
