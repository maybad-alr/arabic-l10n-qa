import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from arabic_l10n_qa.checks import CheckOptions, check_pair  # noqa: E402


def codes(issues):
    return {issue.code for issue in issues}


class PunctuationSpacingTests(unittest.TestCase):
    def test_space_before_arabic_comma(self):
        issues = check_pair("k", None, "مرحبا ، بالعالم")
        self.assertIn("punctuation.space_before", codes(issues))

    def test_no_space_before_is_clean(self):
        issues = check_pair("k", None, "مرحبا، بالعالم")
        self.assertNotIn("punctuation.space_before", codes(issues))

    def test_missing_space_after_arabic_comma(self):
        issues = check_pair("k", None, "مرحبا،بالعالم")
        self.assertIn("punctuation.missing_space_after", codes(issues))

    def test_trailing_punctuation_is_clean(self):
        issues = check_pair("k", None, "مرحبا، بالعالم.")
        self.assertNotIn("punctuation.missing_space_after", codes(issues))

    def test_number_grouping_comma_is_not_flagged(self):
        # "1,000" uses the comma as a thousands separator, not as punctuation.
        issues = check_pair("k", None, "السعر 1,000 دولار")
        self.assertNotIn("punctuation.ascii", codes(issues))

    def test_prose_comma_is_still_flagged(self):
        issues = check_pair("k", None, "مرحبا, بالعالم")
        self.assertIn("punctuation.ascii", codes(issues))


class DigitStyleTests(unittest.TestCase):
    def test_mixed_digit_styles(self):
        issues = check_pair("k", None, "لديك ٢ رسائل و 3 تنبيهات")
        self.assertIn("digits.mixed_style", codes(issues))

    def test_consistent_arabic_indic_is_clean(self):
        issues = check_pair("k", None, "لديك ٢ رسائل و ٣ تنبيهات")
        self.assertNotIn("digits.mixed_style", codes(issues))

    def test_consistent_western_is_clean(self):
        issues = check_pair("k", None, "لديك 2 رسائل و 3 تنبيهات")
        self.assertNotIn("digits.mixed_style", codes(issues))


class BracketTests(unittest.TestCase):
    def test_unbalanced_parenthesis(self):
        issues = check_pair("k", None, "مرحبا (بك")
        self.assertIn("brackets.unbalanced", codes(issues))

    def test_balanced_parenthesis_is_clean(self):
        issues = check_pair("k", None, "مرحبا (بك)")
        self.assertNotIn("brackets.unbalanced", codes(issues))

    def test_unbalanced_guillemets(self):
        issues = check_pair("k", None, "قال «مرحبا")
        self.assertIn("brackets.unbalanced", codes(issues))

    def test_brackets_inside_placeholder_are_ignored(self):
        issues = check_pair("k", None, "استخدم {count} عناصر")
        self.assertNotIn("brackets.unbalanced", codes(issues))


class JoinerTests(unittest.TestCase):
    def test_zwj_is_flagged(self):
        issues = check_pair("k", None, "مرحبا\u200d بالعالم")
        self.assertIn("arabic.joiner_chars", codes(issues))

    def test_zwnj_is_flagged(self):
        issues = check_pair("k", None, "مرحبا\u200c بالعالم")
        self.assertIn("arabic.joiner_chars", codes(issues))

    def test_clean_string_is_not_flagged(self):
        issues = check_pair("k", None, "مرحبا بالعالم")
        self.assertNotIn("arabic.joiner_chars", codes(issues))


class RepeatedWordTests(unittest.TestCase):
    def test_repeated_word_is_flagged(self):
        issues = check_pair("k", None, "مرحبا في في العالم")
        self.assertIn("arabic.repeated_word", codes(issues))

    def test_natural_sentence_is_clean(self):
        issues = check_pair("k", None, "مرحبا في العالم")
        self.assertNotIn("arabic.repeated_word", codes(issues))

    def test_repeated_latin_is_ignored(self):
        issues = check_pair("k", None, "click click here مرحبا")
        self.assertNotIn("arabic.repeated_word", codes(issues))


class DoubleSpaceTests(unittest.TestCase):
    def test_double_space_is_flagged(self):
        issues = check_pair("k", None, "مرحبا  بالعالم")
        self.assertIn("arabic.double_space", codes(issues))

    def test_single_space_is_clean(self):
        issues = check_pair("k", None, "مرحبا بالعالم")
        self.assertNotIn("arabic.double_space", codes(issues))


class ToggleTests(unittest.TestCase):
    def test_new_checks_can_be_disabled(self):
        options = CheckOptions(
            check_digits=False,
            check_punctuation_spacing=False,
            check_brackets=False,
            check_joiners=False,
            check_repeated_words=False,
            check_double_space=False,
        )
        issues = check_pair("k", None, "مرحبا  في في (بك ٢ و 3\u200d ,", options)
        found = codes(issues)
        for code in (
            "digits.mixed_style",
            "punctuation.space_before",
            "brackets.unbalanced",
            "arabic.joiner_chars",
            "arabic.repeated_word",
            "arabic.double_space",
        ):
            self.assertNotIn(code, found)


if __name__ == "__main__":
    unittest.main()
