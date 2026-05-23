import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from bgs_tools.constellation.compile.staging import stage_source_files
from bgs_tools.constellation.packaging.operations import mirror_source
from bgs_tools.constellation.preprocessor import preprocess_build_items, preprocess_file, transpile_source


LINK_QUEST_SOURCE = textwrap.dedent(
    """
    ScriptName TestQuestScript Extends Quest

    $LinkQuest(Example.esm, 0x811)

    Event OnQuestInit()
    EndEvent
    """
).lstrip()


class ConstellationPreprocessorTests(unittest.TestCase):
    def test_transpile_source_reports_tree_sitter_metadata(self):
        source_text = "ScriptName PlainScript Extends Quest\n"

        result = transpile_source(source_text, "PlainScript.psc")

        self.assertEqual(source_text, result.primary.text)
        self.assertEqual("tree-sitter", result.parser.to_dict()["engine"])
        self.assertIn("available", result.parser.to_dict())

    def test_preprocess_file_lowers_link_quest_directive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "TestQuestScript.psc"
            source_path.write_text(LINK_QUEST_SOURCE, encoding="utf-8")

            metadata = preprocess_file(
                source_path,
                collect_metadata=True,
            )
            transformed_text = source_path.read_text(encoding="utf-8")

        self.assertNotIn("$LinkQuest", transformed_text)
        self.assertIn("TestQuestScript Function GetSelf() Global", transformed_text)
        self.assertIn("String PF = \"Example.esm\"", transformed_text)
        self.assertEqual("LinkQuest", metadata["macro_calls"][0]["name"])
        self.assertEqual("Example.esm", metadata["macro_calls"][0]["plugin_file"])
        self.assertEqual("TestQuestScript", metadata["macro_calls"][0]["script_name"])

    def test_copy_source_to_mirrors_transpiled_staged_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_root = temp_root / "src"
            build_dir = temp_root / "build"
            copy_source_to = temp_root / "deploy" / "Scripts" / "Source"
            source_root.mkdir(parents=True)
            source_path = source_root / "TestQuestScript.psc"
            source_path.write_text(LINK_QUEST_SOURCE, encoding="utf-8")

            build_items = stage_source_files([source_path], source_root, build_dir)
            preprocess_build_items(build_items, collect_metadata=True)
            mirror_source(
                build_items[0].staged_path,
                copy_source_to=copy_source_to,
                base_path=build_items[0].stage_root,
            )

            mirrored_path = copy_source_to / "TestQuestScript.psc"
            self.assertTrue(os.path.exists(mirrored_path))
            mirrored_text = mirrored_path.read_text(encoding="utf-8")

        self.assertNotIn("$LinkQuest", mirrored_text)
        self.assertIn("TestQuestScript Function GetSelf() Global", mirrored_text)


if __name__ == "__main__":
    unittest.main()