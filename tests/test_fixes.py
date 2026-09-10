import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arabic_l10n_qa.cli import run_fixes  # noqa: E402
from arabic_l10n_qa.fixes import fix_mapping, fix_tree, fix_value  # noqa: E402


class FixValueTests(unittest.TestCase):
    def test_ascii_comma_becomes_arabic_comma(self):
        fixed, applied = fix_value("مرحبا, بالعالم")
        self.assertEqual(fixed, "مرحبا، بالعالم")
        self.assertIn("punctuation.ascii", applied)

    def test_ascii_question_mark_becomes_arabic(self):
        fixed, applied = fix_value("هل أنت متأكد?")
        self.assertEqual(fixed, "هل أنت متأكد؟")
        self.assertIn("punctuation.ascii", applied)

    def test_space_before_arabic_punctuation_is_removed(self):
        fixed, applied = fix_value("مرحبا ، بالعالم")
        self.assertEqual(fixed, "مرحبا، بالعالم")
        self.assertIn("punctuation.space_before", applied)

    def test_internal_double_space_collapses(self):
        fixed, applied = fix_value("مرحبا  بالعالم")
        self.assertEqual(fixed, "مرحبا بالعالم")
        self.assertIn("arabic.double_space", applied)

    def test_number_grouping_comma_is_preserved(self):
        fixed, applied = fix_value("السعر 1,000 دولار")
        self.assertEqual(fixed, "السعر 1,000 دولار")
        self.assertNotIn("punctuation.ascii", applied)

    def test_url_is_never_rewritten(self):
        value = "انظر https://example.com/a?b=1&c=2"
        fixed, applied = fix_value(value)
        self.assertEqual(fixed, value)
        self.assertEqual(applied, [])

    def test_email_is_never_rewritten(self):
        value = "راسل support@example.com"
        fixed, applied = fix_value(value)
        self.assertEqual(fixed, value)

    def test_placeholder_is_never_rewritten(self):
        value = "مرحبا {name}?"
        fixed, _ = fix_value(value)
        self.assertIn("{name}", fixed)
        self.assertTrue(fixed.endswith("؟"))

    def test_html_tag_is_never_rewritten(self):
        value = 'اقرأ <a href="x?a=1">الشروط</a>'
        fixed, _ = fix_value(value)
        self.assertIn('href="x?a=1"', fixed)

    def test_non_arabic_string_is_untouched(self):
        fixed, applied = fix_value("Hello, world?")
        self.assertEqual(fixed, "Hello, world?")
        self.assertEqual(applied, [])

    def test_non_string_is_untouched(self):
        fixed, applied = fix_value(123)  # type: ignore[arg-type]
        self.assertEqual(fixed, 123)
        self.assertEqual(applied, [])


class FixTreeTests(unittest.TestCase):
    def test_nested_structures_are_walked(self):
        data = {
            "app": {
                "title": "مرحبا, بالعالم",
                "items": ["عنصر واحد", "عنصر  اثنان"],
                "count": 3,
            }
        }
        fixed, counts = fix_tree(data)
        self.assertEqual(fixed["app"]["title"], "مرحبا، بالعالم")
        self.assertEqual(fixed["app"]["items"][1], "عنصر اثنان")
        self.assertEqual(fixed["app"]["count"], 3)
        self.assertEqual(counts["punctuation.ascii"], 1)
        self.assertEqual(counts["arabic.double_space"], 1)

    def test_structure_is_preserved(self):
        data = {"a": {"b": ["c"]}}
        fixed, _ = fix_tree(data)
        self.assertEqual(list(fixed), ["a"])
        self.assertEqual(list(fixed["a"]), ["b"])
        self.assertEqual(fixed["a"]["b"], ["c"])


class FixMappingTests(unittest.TestCase):
    def test_flat_mapping(self):
        fixed, counts = fix_mapping({"a": "مرحبا, بالعالم", "b": "ok"})
        self.assertEqual(fixed["a"], "مرحبا، بالعالم")
        self.assertEqual(fixed["b"], "ok")
        self.assertEqual(counts["punctuation.ascii"], 1)


class RunFixesCliTests(unittest.TestCase):
    def _write_temp(self, payload):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(payload, handle, ensure_ascii=False)
        handle.close()
        return Path(handle.name)

    def test_print_mode_does_not_touch_the_file(self):
        path = self._write_temp({"greeting": "مرحبا, بالعالم"})
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_fixes(str(path), write=False)
        self.assertEqual(code, 0)
        self.assertIn("مرحبا، بالعالم", out.getvalue())
        self.assertIn("punctuation.ascii", err.getvalue())
        self.assertIn("مرحبا, بالعالم", path.read_text(encoding="utf-8"))
        path.unlink()

    def test_write_mode_updates_the_file(self):
        path = self._write_temp({"greeting": "مرحبا, بالعالم"})
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_fixes(str(path), write=True)
        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8"))["greeting"],
            "مرحبا، بالعالم",
        )
        path.unlink()

    def test_non_json_target_is_rejected(self):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".po", delete=False, encoding="utf-8"
        )
        handle.write('msgid "a"\nmsgstr "b"\n')
        handle.close()
        path = Path(handle.name)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_fixes(str(path), write=False)
        self.assertEqual(code, 2)
        self.assertIn("JSON targets only", err.getvalue())
        path.unlink()

    def test_missing_file_returns_two(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_fixes("does-not-exist.json", write=False)
        self.assertEqual(code, 2)
        self.assertIn("file not found", err.getvalue())


if __name__ == "__main__":
    unittest.main()
