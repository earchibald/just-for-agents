import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONSUMER_EXTENSION = REPO_ROOT / "examples" / "pi-consumer" / "just-consumer.ts"


class PiConsumerExtensionSourceTests(unittest.TestCase):
    def test_consumer_mode_no_longer_requires_justfile_at_startup(self) -> None:
        source = CONSUMER_EXTENSION.read_text(encoding="utf-8")
        self.assertNotIn('if (!existsSync(join(ctx.cwd, "Justfile"))) return;', source)
        self.assertIn("function workspaceHasJustfile(", source)
        self.assertIn("No Justfile found in this workspace yet.", source)
        self.assertIn("pi.setActiveTools(CONSUMER_TOOLS);", source)

    def test_consumer_extension_registers_tools_and_manifest_slash_commands(self) -> None:
        source = CONSUMER_EXTENSION.read_text(encoding="utf-8")
        self.assertIn("function syncManifestCommands()", source)
        self.assertIn('pi.registerCommand("tools"', source)
        self.assertIn("pi.registerCommand(tool.name,", source)
        self.assertIn("Use /tools to inspect them.", source)
        self.assertGreaterEqual(source.count("syncManifestCommands();"), 4)


if __name__ == "__main__":
    unittest.main()
