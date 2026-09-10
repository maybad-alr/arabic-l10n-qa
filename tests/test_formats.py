import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arabic_l10n_qa.formats import (  # noqa: E402
    UnsupportedFormatError,
    load_file,
    load_file_with_source,
    parse_csv,
    parse_json,
    parse_po,
    parse_properties,
    parse_strings,
    supported_extensions,
)

try:
    import yaml  # noqa: F401

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class JsonTests(unittest.TestCase):
    def test_nested_flatten(self):
        data = parse_json('{"a": {"b": "1"}, "c": ["x", "y"]}')
        self.assertEqual(data, {"a.b": "1", "c.0": "x", "c.1": "y"})


class PoTests(unittest.TestCase):
    def test_simple_pair(self):
        text = 'msgid "Hello"\nmsgstr "مرحبا"\n'
        self.assertEqual(parse_po(text), {"Hello": "مرحبا"})

    def test_multiline_fragments_are_joined(self):
        text = (
            'msgid ""\n'
            '"A long "\n'
            '"sentence"\n'
            'msgstr ""\n'
            '"جملة "\n'
            '"طويلة"\n'
        )
        self.assertEqual(parse_po(text), {"A long sentence": "جملة طويلة"})

    def test_header_entry_is_skipped(self):
        text = 'msgid ""\nmsgstr "Content-Type: text/plain\\n"\n'
        self.assertEqual(parse_po(text), {})

    def test_comments_and_plural_ignored(self):
        text = (
            "# translator comment\n"
            "#: src/a.ts:1\n"
            'msgid "One file"\n'
            'msgid_plural "Many files"\n'
            'msgstr[0] "ملف واحد"\n'
        )
        self.assertEqual(parse_po(text), {"One file": "ملف واحد"})

    def test_escaped_newline(self):
        text = 'msgid "Line1\\nLine2"\nmsgstr "سطر1\\nسطر2"\n'
        self.assertEqual(parse_po(text), {"Line1\nLine2": "سطر1\nسطر2"})


class PropertiesTests(unittest.TestCase):
    def test_equals_and_colon(self):
        text = "# comment\napp.title=عنوان\napp.sub: فرعي\n"
        self.assertEqual(
            parse_properties(text), {"app.title": "عنوان", "app.sub": "فرعي"}
        )

    def test_bang_comment(self):
        self.assertEqual(parse_properties("! note\nk=v\n"), {"k": "v"})


class StringsTests(unittest.TestCase):
    def test_ios_strings(self):
        text = '/* c */\n"app.title" = "العنوان";\n"app.ok" = "حسنًا";\n'
        self.assertEqual(
            parse_strings(text), {"app.title": "العنوان", "app.ok": "حسنًا"}
        )


class CsvTests(unittest.TestCase):
    def test_header_row_is_skipped(self):
        text = "key,value\napp.title,العنوان\n"
        self.assertEqual(parse_csv(text), {"app.title": "العنوان"})

    def test_no_header(self):
        self.assertEqual(parse_csv("app.title,العنوان\n"), {"app.title": "العنوان"})


@unittest.skipUnless(HAS_YAML, "PyYAML is not installed")
class YamlTests(unittest.TestCase):
    """YAML support is optional, so these tests skip without PyYAML."""

    def test_nested_keys_are_flattened(self):
        from arabic_l10n_qa.formats import parse_yaml

        data = parse_yaml("app:\n  title: عنوان\n  ok: حسنًا\n")
        self.assertEqual(data, {"app.title": "عنوان", "app.ok": "حسنًا"})

    def test_empty_document_is_empty_mapping(self):
        from arabic_l10n_qa.formats import parse_yaml

        self.assertEqual(parse_yaml(""), {})


class DispatchTests(unittest.TestCase):
    def test_unsupported_extension_raises(self):
        with self.assertRaises(UnsupportedFormatError):
            load_file(Path(__file__).resolve().parents[1] / "pyproject.toml")

    def test_supported_extensions_include_po_and_strings(self):
        extensions = supported_extensions()
        self.assertIn(".po", extensions)
        self.assertIn(".strings", extensions)
        self.assertIn(".json", extensions)

    def test_load_po_example_file(self):
        root = Path(__file__).resolve().parents[1]
        ar = load_file(root / "examples" / "ar.po")
        en = load_file(root / "examples" / "en.po")
        self.assertEqual(set(en), set(ar))
        self.assertEqual(ar["Loading, please wait"], "جارٍ التحميل، انتظر من فضلك")


class EndToEndTests(unittest.TestCase):
    def test_po_files_produce_expected_defects(self):
        from arabic_l10n_qa.report import build_report

        root = Path(__file__).resolve().parents[1]
        # A single Arabic .po file carries its English source in the msgid,
        # so it can be validated without a second file.
        source, target = load_file_with_source(root / "examples" / "ar.po")
        self.assertIsNotNone(source)
        issues = build_report(source, target)
        codes = {issue.code for issue in issues}
        # The .po example deliberately drops the <b> tags around "terms".
        self.assertIn("html.mismatch", codes)

    def test_json_has_no_embedded_source(self):
        root = Path(__file__).resolve().parents[1]
        source, target = load_file_with_source(root / "examples" / "ar.json")
        self.assertIsNone(source)
        self.assertIn("app.title", target)


if __name__ == "__main__":
    unittest.main()
