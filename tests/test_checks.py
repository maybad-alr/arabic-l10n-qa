import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arabic_l10n_qa.checks import CheckOptions, Severity, check_pair  # noqa: E402


def codes(issues):
    return {issue.code for issue in issues}


class PlaceholderTests(unittest.TestCase):
    def test_placeholder_mismatch_is_error(self):
        issues = check_pair("k", "Hello {name}", "مرحبًا")
        self.assertIn("placeholder.mismatch", codes(issues))
        self.assertTrue(any(i.severity is Severity.ERROR for i in issues))

    def test_matching_placeholders_ok(self):
        issues = check_pair("k", "Hello {name}", "مرحبًا {name}")
        self.assertNotIn("placeholder.mismatch", codes(issues))

    def test_percent_and_dollar_placeholders(self):
        issues = check_pair("k", "You have %d items, $TOTAL$", "لديك %d عناصر، $TOTAL$")
        self.assertNotIn("placeholder.mismatch", codes(issues))

    def test_multiset_placeholder_order_does_not_matter(self):
        issues = check_pair("k", "{a} then {b}", "{b} ثم {a}")
        self.assertNotIn("placeholder.mismatch", codes(issues))

    def test_duplicate_placeholder_count_matters(self):
        issues = check_pair("k", "{a} and {a}", "{a} و {a} و {a}")
        self.assertIn("placeholder.mismatch", codes(issues))


class MarkupTests(unittest.TestCase):
    def test_html_mismatch(self):
        issues = check_pair("k", "Read <b>terms</b>", "اقرأ الشروط")
        self.assertIn("html.mismatch", codes(issues))

    def test_url_mismatch(self):
        issues = check_pair("k", "See https://a.example", "انظر https://b.example")
        self.assertIn("url.mismatch", codes(issues))

    def test_email_mismatch(self):
        issues = check_pair("k", "Mail a@x.com", "راسل b@x.com")
        self.assertIn("email.mismatch", codes(issues))


class ArabicProseTests(unittest.TestCase):
    def test_ascii_comma_in_arabic(self):
        issues = check_pair("k", "Hello, world", "مرحبا, بالعالم")
        self.assertIn("punctuation.ascii", codes(issues))

    def test_arabic_comma_is_clean(self):
        issues = check_pair("k", "Hello, world", "مرحبا\u060c بالعالم")
        self.assertNotIn("punctuation.ascii", codes(issues))

    def test_ascii_question_mark(self):
        issues = check_pair("k", "Are you sure?", "هل أنت متأكد?")
        self.assertIn("punctuation.ascii", codes(issues))

    def test_bidi_controls_flagged(self):
        issues = check_pair("k", "ok", "مرحبا\u202e")
        self.assertIn("bidi.control_chars", codes(issues))

    def test_mixed_script_without_space(self):
        issues = check_pair("k", "Open app", "افتحapp")
        self.assertIn("script.mixed_spacing", codes(issues))

    def test_mixed_script_with_space_ok(self):
        issues = check_pair("k", "Open app", "افتح app")
        self.assertNotIn("script.mixed_spacing", codes(issues))

    def test_ellipsis_hint(self):
        issues = check_pair("k", "Loading...", "جارٍ التحميل...")
        self.assertIn("typography.ellipsis", codes(issues))

    def test_tatweel_hint(self):
        issues = check_pair("k", "test", "مـــرحبا")
        self.assertIn("arabic.tatweel", codes(issues))

    def test_empty_is_error(self):
        issues = check_pair("k", "Hello", "   ")
        self.assertIn("empty.translation", codes(issues))

    def test_untranslated_identical(self):
        issues = check_pair("k", "Upload a file", "Upload a file")
        self.assertIn("untranslated.identical", codes(issues))

    def test_untranslated_can_be_ignored(self):
        issues = check_pair(
            "k",
            "LocalizationHub",
            "LocalizationHub",
            CheckOptions(ignore_untranslated_values=("LocalizationHub",)),
        )
        self.assertNotIn("untranslated.identical", codes(issues))

    def test_whitespace_edge_mismatch(self):
        issues = check_pair("k", "Hello ", "مرحبا")
        self.assertIn("whitespace.edge", codes(issues))


if __name__ == "__main__":
    unittest.main()
