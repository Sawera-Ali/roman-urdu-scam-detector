"""
Tests for Partner A's preprocessing pipeline.

These use Python's built-in `unittest`, so no extra package is needed:

    python -m unittest discover -s tests -v

(They also run under pytest if you prefer:  pytest tests -v)
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

# Make sure the project root is importable when running from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from preprocessing import config
from preprocessing.cleaner import (
    clean_text,
    normalize_whitespace,
    preprocess_text,
    remove_punctuation,
    remove_stopwords,
    replace_numbers,
    replace_urls,
    to_lowercase,
    tokenize,
)
from preprocessing.feature_extraction import create_tfidf_features, split_dataset
from preprocessing.roman_urdu_normalizer import normalize_roman_urdu
from preprocessing.validator import (
    normalize_label_value,
    normalize_labels,
    remove_duplicates,
    remove_invalid_rows,
    validate_dataset,
)


# ---------------------------------------------------------------------------
# A few sample Roman Urdu SMS messages used across the tests
# ---------------------------------------------------------------------------
SAMPLE_MESSAGES = [
    "Aap ka JazzCash ACCOUNT block ho jaye ga!!! Verify karein: https://fake-link.com",
    "Mubarak ho! Aap ne Rs. 50,000 ka prize jeeta hai. Claim karein bit.ly/win-prize2",
    "Ammi kal 5 baje ghar aa jana, khana ready hai.",
    "Aap ka Easypaisa account balance Rs. 1000 hai. Statement app pe dekhein.",
    "Aap ka parcel customs mein hai, 25,000 fee bhejain 03021234567 par.",
    "Balance na-kafi? *503# mila k Collect Call service se MUFT baat karen.",
]
SAMPLE_LABELS = ["Scam", "Scam", "Genuine", "Genuine", "Scam", "Genuine"]


def build_sample_dataframe():
    """A small in-memory DataFrame shaped exactly like the real dataset."""
    return pd.DataFrame(
        {
            config.TEXT_COLUMN: SAMPLE_MESSAGES,
            config.LABEL_COLUMN: SAMPLE_LABELS,
            config.SOURCE_COLUMN: ["Synthetic"] * len(SAMPLE_MESSAGES),
        }
    )


# ---------------------------------------------------------------------------
# 1. LOWERCASE
# ---------------------------------------------------------------------------
class TestLowercase(unittest.TestCase):
    def test_lowercase_conversion(self):
        self.assertEqual(
            to_lowercase("Aap Ka JAZZCASH Account BLOCK Ho Jaye Ga!"),
            "aap ka jazzcash account block ho jaye ga!",
        )

    def test_clean_text_output_has_no_capitals(self):
        cleaned = clean_text("AAP KA ACCOUNT BLOCK HO JAYE GA")
        self.assertEqual(cleaned, cleaned.lower())


# ---------------------------------------------------------------------------
# 2. URL REPLACEMENT
# ---------------------------------------------------------------------------
class TestUrlHandling(unittest.TestCase):
    def test_https_url_becomes_token(self):
        result = replace_urls("aap ka account verify karein https://fake-site.com")
        self.assertIn(config.URL_TOKEN, result)
        self.assertNotIn("fake-site", result)

    def test_bitly_shortener(self):
        self.assertEqual(replace_urls("click https://bit.ly/4npwYsU"), "click urltoken")

    def test_www_url(self):
        self.assertEqual(replace_urls("visit www.telenor.com.pk/dl"), "visit urltoken")

    def test_bare_domain_without_http(self):
        # Scam messages in this dataset often omit "http://".
        self.assertEqual(replace_urls("pay karein ubl-update.co"), "pay karein urltoken")

    def test_url_is_replaced_not_deleted(self):
        # The information "this message had a link" must survive.
        self.assertIn(config.URL_TOKEN, preprocess_text("click here http://bit.ly/x"))

    def test_url_survives_full_pipeline(self):
        cleaned = clean_text("verify karein: https://fake-link.com")
        self.assertIn(config.URL_TOKEN, cleaned)
        self.assertNotIn(".com", cleaned)


# ---------------------------------------------------------------------------
# 3. NUMBER HANDLING
# ---------------------------------------------------------------------------
class TestNumberHandling(unittest.TestCase):
    def test_amount_becomes_numtoken(self):
        self.assertIn(config.NUMBER_TOKEN, replace_numbers("rs. 50000"))

    def test_amount_with_commas(self):
        self.assertEqual(replace_numbers("rs. 50,000"), "rs. numtoken")

    def test_phone_number_becomes_phonetoken(self):
        self.assertIn(config.PHONE_TOKEN, replace_numbers("rabta karen 03021234567"))

    def test_ussd_shortcode_preserved_as_token(self):
        # "*503#" must not be destroyed; it becomes a dedicated token.
        self.assertIn(config.SHORTCODE_TOKEN, replace_numbers("*503# mila k"))

    def test_known_short_code_is_kept(self):
        # 8171 (BISP) carries real meaning, so it stays as digits.
        self.assertIn("8171", replace_numbers("is number se 8171 pe sms karein"))

    def test_number_mode_keep(self):
        self.assertEqual(replace_numbers("rs 500", number_mode="keep"), "rs 500")

    def test_number_mode_remove(self):
        self.assertNotIn("500", replace_numbers("rs 500", number_mode="remove"))

    def test_bracket_number_placeholder(self):
        self.assertIn(config.PHONE_TOKEN, replace_numbers("apka ye number [Number] or"))


# ---------------------------------------------------------------------------
# 4. PUNCTUATION AND SPECIAL CHARACTERS
# ---------------------------------------------------------------------------
class TestPunctuation(unittest.TestCase):
    def test_exclamation_marks_removed(self):
        result = normalize_whitespace(remove_punctuation("congratulations!!! you won!!!"))
        self.assertEqual(result, "congratulations you won")

    def test_special_characters_removed(self):
        self.assertEqual(clean_text("***FREE*** Prize!!!"), "free prize")

    def test_meaningful_words_survive(self):
        cleaned = clean_text("Congratulations!!! You won!!!")
        for word in ("congratulations", "you", "won"):
            self.assertIn(word, cleaned)


# ---------------------------------------------------------------------------
# 5. WHITESPACE
# ---------------------------------------------------------------------------
class TestWhitespace(unittest.TestCase):
    def test_multiple_spaces_collapse(self):
        self.assertEqual(normalize_whitespace("aap     winner     hain"), "aap winner hain")

    def test_leading_and_trailing_spaces_removed(self):
        self.assertEqual(normalize_whitespace("   aap winner hain   "), "aap winner hain")

    def test_tabs_and_newlines(self):
        self.assertEqual(normalize_whitespace("aap\twinner\nhain"), "aap winner hain")


# ---------------------------------------------------------------------------
# 6. ROMAN URDU NORMALIZATION
# ---------------------------------------------------------------------------
class TestRomanUrduNormalization(unittest.TestCase):
    def test_known_variants_are_normalized(self):
        self.assertEqual(normalize_roman_urdu("ap kren"), "aap karein")

    def test_kia_becomes_kya(self):
        self.assertEqual(normalize_roman_urdu("kia hua"), "kya hua")

    def test_krna_becomes_karna(self):
        self.assertEqual(normalize_roman_urdu("verify krna hai"), "verify karna hai")

    def test_whole_words_only(self):
        # "ap" -> "aap" must NOT corrupt "apna" / "apni".
        self.assertEqual(normalize_roman_urdu("apna apni"), "apna apni")

    def test_brand_names_untouched(self):
        text = "jazzcash easypaisa sadapay nayapay telenor"
        self.assertEqual(normalize_roman_urdu(text), text)

    def test_scam_keywords_untouched(self):
        text = "free prize winner urgent verify account block loan click link reward otp"
        self.assertEqual(normalize_roman_urdu(text), text)

    def test_placeholder_tokens_untouched(self):
        text = "urltoken phonetoken numtoken shortcodetoken"
        self.assertEqual(normalize_roman_urdu(text), text)

    def test_custom_dictionary_is_supported(self):
        self.assertEqual(
            normalize_roman_urdu("hy test", mapping={"hy": "hai"}), "hai test"
        )


# ---------------------------------------------------------------------------
# 7. TOKENIZATION AND STOPWORDS
# ---------------------------------------------------------------------------
class TestTokenizationAndStopwords(unittest.TestCase):
    def test_tokenize(self):
        self.assertEqual(
            tokenize("account block verify link"),
            ["account", "block", "verify", "link"],
        )

    def test_stopwords_removed(self):
        tokens = ["aap", "ka", "account", "block", "ho", "jaye", "ga"]
        self.assertEqual(remove_stopwords(tokens), ["aap", "account", "block"])

    def test_scam_indicators_are_never_removed(self):
        indicators = [
            "free", "prize", "winner", "urgent", "verify",
            "account", "block", "loan", "click", "link", "reward", "otp",
        ]
        self.assertEqual(remove_stopwords(list(indicators)), indicators)

    def test_placeholder_tokens_are_never_removed(self):
        tokens = ["urltoken", "phonetoken", "numtoken", "shortcodetoken"]
        self.assertEqual(remove_stopwords(tokens), tokens)

    def test_short_tokens_dropped(self):
        self.assertNotIn("k", remove_stopwords(["k", "account"]))


# ---------------------------------------------------------------------------
# 8. FULL TEXT PIPELINE
# ---------------------------------------------------------------------------
class TestFullTextPipeline(unittest.TestCase):
    def test_end_to_end_example(self):
        cleaned = preprocess_text(
            "Aap ka JazzCash ACCOUNT block ho jaye ga!!! "
            "Verify karein: https://fake-link.com"
        )
        for expected in ("jazzcash", "account", "block", "verify", config.URL_TOKEN):
            self.assertIn(expected, cleaned)
        # stopwords are gone
        self.assertNotIn(" ka ", f" {cleaned} ")

    def test_handles_empty_and_missing_input(self):
        self.assertEqual(preprocess_text(""), "")
        self.assertEqual(preprocess_text("   "), "")
        self.assertEqual(preprocess_text(None), "")

    def test_handles_non_string_input(self):
        # A number in the Excel cell must not crash the pipeline.
        self.assertIsInstance(preprocess_text(12345), str)

    def test_output_is_a_string(self):
        for message in SAMPLE_MESSAGES:
            self.assertIsInstance(preprocess_text(message), str)


# ---------------------------------------------------------------------------
# 9. LABEL NORMALIZATION
# ---------------------------------------------------------------------------
class TestLabelNormalization(unittest.TestCase):
    def test_scam_spellings(self):
        for raw in ("scam", "Scam", "SCAM", "ScAm", "  scam  "):
            self.assertEqual(normalize_label_value(raw), "Scam")

    def test_genuine_spellings(self):
        for raw in ("genuine", "Genuine", "GENUINE", "GeNuInE", "Genuine "):
            self.assertEqual(normalize_label_value(raw), "Genuine")

    def test_unknown_label_is_invalid(self):
        self.assertIsNone(normalize_label_value("maybe"))
        self.assertIsNone(normalize_label_value(""))
        self.assertIsNone(normalize_label_value(None))

    def test_dataframe_labels_normalized(self):
        frame = build_sample_dataframe()
        frame.loc[0, config.LABEL_COLUMN] = "scam"
        frame.loc[2, config.LABEL_COLUMN] = "Genuine "
        normalized, info = normalize_labels(frame)
        self.assertTrue(set(normalized[config.LABEL_COLUMN]) <= {"Scam", "Genuine"})
        self.assertEqual(info["labels_normalized"], 2)
        self.assertEqual(info["invalid_labels"], 0)

    def test_invalid_labels_are_reported_and_removed(self):
        frame = build_sample_dataframe()
        frame.loc[1, config.LABEL_COLUMN] = "unknown-label"
        normalized, info = normalize_labels(frame)
        self.assertEqual(info["invalid_labels"], 1)
        cleaned, removal = remove_invalid_rows(normalized, verbose=False)
        self.assertEqual(removal["invalid_label_rows_removed"], 1)
        self.assertEqual(len(cleaned), len(frame) - 1)


# ---------------------------------------------------------------------------
# 10. VALIDATION AND DUPLICATES
# ---------------------------------------------------------------------------
class TestValidationAndDuplicates(unittest.TestCase):
    def test_validation_counts_are_dynamic(self):
        frame = build_sample_dataframe()
        report = validate_dataset(frame)
        self.assertEqual(report["initial_records"], len(frame))
        self.assertEqual(report["duplicate_messages"], 0)

    def test_empty_message_detected_and_removed(self):
        frame = build_sample_dataframe()
        frame.loc[len(frame)] = ["   ", "Scam", "Authentic"]
        self.assertEqual(validate_dataset(frame)["empty_messages"], 1)
        cleaned, info = remove_invalid_rows(frame, verbose=False)
        self.assertEqual(info["empty_messages_removed"], 1)

    def test_duplicate_removed_and_reported(self):
        frame = build_sample_dataframe()
        frame.loc[len(frame)] = [SAMPLE_MESSAGES[0], "Scam", "Synthetic"]
        deduped, info = remove_duplicates(frame, verbose=False)
        self.assertEqual(info["duplicates_removed"], 1)
        self.assertEqual(len(deduped), len(frame) - 1)

    def test_duplicate_detection_ignores_case_and_spacing(self):
        frame = build_sample_dataframe()
        frame.loc[len(frame)] = ["  " + SAMPLE_MESSAGES[2].upper() + " ", "Genuine", "Synthetic"]
        _, info = remove_duplicates(frame, verbose=False)
        self.assertEqual(info["duplicates_removed"], 1)

    def test_conflicting_labels_dropped(self):
        # Same text, two different labels -> ground truth is unknown.
        frame = build_sample_dataframe()
        frame.loc[len(frame)] = [SAMPLE_MESSAGES[0], "Genuine", "Synthetic"]
        deduped, info = remove_duplicates(frame, policy="drop", verbose=False)
        self.assertEqual(info["conflicting_label_groups"], 1)
        self.assertEqual(info["conflicting_rows_removed"], 2)
        self.assertNotIn(SAMPLE_MESSAGES[0], list(deduped[config.TEXT_COLUMN]))

    def test_conflicting_labels_keep_first(self):
        frame = build_sample_dataframe()
        frame.loc[len(frame)] = [SAMPLE_MESSAGES[0], "Genuine", "Synthetic"]
        deduped, info = remove_duplicates(frame, policy="first", verbose=False)
        self.assertEqual(info["conflicting_rows_removed"], 0)
        self.assertIn(SAMPLE_MESSAGES[0], list(deduped[config.TEXT_COLUMN]))


# ---------------------------------------------------------------------------
# 11. TRAIN / TEST SPLIT
# ---------------------------------------------------------------------------
class TestTrainTestSplit(unittest.TestCase):
    def setUp(self):
        # 100 rows so that an 80/20 split is exact and easy to check.
        self.frame = pd.DataFrame(
            {
                config.CLEANED_TEXT_COLUMN: [f"message number {i}" for i in range(100)],
                config.LABEL_COLUMN: ["Scam"] * 50 + ["Genuine"] * 50,
            }
        )

    def test_80_20_split_sizes(self):
        X_train, X_test, y_train, y_test = split_dataset(self.frame)
        self.assertEqual(len(X_train), 80)
        self.assertEqual(len(X_test), 20)
        self.assertEqual(len(y_train), 80)
        self.assertEqual(len(y_test), 20)

    def test_split_is_reproducible(self):
        first = split_dataset(self.frame)[0]
        second = split_dataset(self.frame)[0]
        self.assertEqual(list(first), list(second))

    def test_stratification_preserves_class_balance(self):
        _, _, y_train, y_test = split_dataset(self.frame)
        self.assertEqual(y_train.value_counts()["Scam"], 40)
        self.assertEqual(y_test.value_counts()["Scam"], 10)

    def test_no_row_is_lost_or_duplicated(self):
        X_train, X_test, _, _ = split_dataset(self.frame)
        self.assertEqual(len(set(X_train) | set(X_test)), 100)
        self.assertEqual(set(X_train) & set(X_test), set())


# ---------------------------------------------------------------------------
# 12. TF-IDF
# ---------------------------------------------------------------------------
class TestTfidf(unittest.TestCase):
    def setUp(self):
        self.X_train = pd.Series(
            [
                "aap account block verify urltoken",
                "free prize winner claim numtoken",
                "ammi ghar khana time",
                "balance statement app open karein",
            ]
        )
        self.X_test = pd.Series(
            [
                "account verify urltoken",
                "ghar khana totallyunseenword",
            ]
        )

    def test_shapes_match(self):
        X_train_tfidf, X_test_tfidf, vectorizer = create_tfidf_features(
            self.X_train, self.X_test
        )
        self.assertEqual(X_train_tfidf.shape[0], len(self.X_train))
        self.assertEqual(X_test_tfidf.shape[0], len(self.X_test))
        # Both matrices MUST have the same number of columns.
        self.assertEqual(X_train_tfidf.shape[1], X_test_tfidf.shape[1])

    def test_vocabulary_comes_from_training_only(self):
        # This is the data-leakage guard: a word that exists only in the test
        # set must never appear in the vocabulary.
        _, _, vectorizer = create_tfidf_features(self.X_train, self.X_test)
        self.assertNotIn("totallyunseenword", vectorizer.vocabulary_)

    def test_bigrams_are_created(self):
        _, _, vectorizer = create_tfidf_features(self.X_train, self.X_test)
        features = set(vectorizer.get_feature_names_out())
        self.assertIn("account", features)                 # unigram
        self.assertIn("account block", features)           # bigram

    def test_ngram_range_is_configurable(self):
        settings = dict(config.TFIDF_SETTINGS)
        settings["ngram_range"] = (1, 1)
        _, _, vectorizer = create_tfidf_features(self.X_train, self.X_test, settings)
        self.assertTrue(
            all(" " not in name for name in vectorizer.get_feature_names_out())
        )

    def test_values_are_numeric(self):
        X_train_tfidf, _, _ = create_tfidf_features(self.X_train, self.X_test)
        self.assertGreater(X_train_tfidf.nnz, 0)
        self.assertTrue((X_train_tfidf.data >= 0).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
