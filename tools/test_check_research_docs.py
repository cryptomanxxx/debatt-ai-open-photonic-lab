import tempfile
import unittest
from pathlib import Path
from check_research_docs import validate


class ResearchDocsTests(unittest.TestCase):
    def test_valid(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / "research" / "test.md"
            p.parent.mkdir()
            (root / "data file.json").touch()
            p.write_text("# Title\n[Data](../data%20file.json#anchor)\n"
                         "[Remote](https://example.com)\n"
                         "[Section](#title)\n"
                         "```md\n[Example](missing.md)\n```\n"
                         "`[Example](missing.md)`\n", encoding="utf-8")
            self.assertEqual(validate(p, root), [])

    def test_broken(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / "test.md"
            p.write_text("[Missing](missing.md)\n[Outside](../outside)\n"
                         "~~~\n", encoding="utf-8")
            errors = validate(p, root)
            self.assertEqual(len(errors), 4)

    def test_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "empty.md"
            p.write_text(" \n", encoding="utf-8")
            self.assertEqual(validate(p, Path(d)), ["empty document"])


if __name__ == "__main__":
    unittest.main()
