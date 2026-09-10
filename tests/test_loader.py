import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arabic_l10n_qa.loader import flatten, load_json_file  # noqa: E402
from arabic_l10n_qa.report import build_report, counts_by_severity, format_report  # noqa: E402


class FlattenTests(unittest.TestCase):
    def test_nested(self):
        data = {"a": {"b": "1"}, "c": [{"d": "2"}]}
        self.assertEqual(dict(flatten(data)), {"a.b": "1", "c.0.d": "2"})

    def test_examples_load(self):
        root = Path(__file__).resolve().parents[1]
        en = load_json_file(root / "examples" / "en.json")
        ar = load_json_file(root / "examples" / "ar.json")
        self.assertEqual(set(en), set(ar))


class ReportTests(unittest.TestCase):
    def test_missing_and_extra_keys(self):
        source = {"a": "Hello", "b": "World"}
        target = {"a": "مرحبا", "c": "عالم"}
        issues = build_report(source, target)
        codes = {i.code for i in issues}
        self.assertIn("missing.key", codes)
        self.assertIn("extra.key", codes)

    def test_json_report_shape(self):
        issues = build_report({"a": "Hello"}, {"a": "مرحبا"})
        rendered = format_report(issues, fmt="json")
        self.assertIn('"summary"', rendered)
        self.assertIn('"total"', rendered)

    def test_counts(self):
        issues = build_report({"a": "Hello {x}"}, {"a": "مرحبا"})
        summary = counts_by_severity(issues)
        self.assertGreaterEqual(summary["error"], 1)


if __name__ == "__main__":
    unittest.main()
