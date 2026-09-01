"""
Central configuration for the Roman Urdu Scam SMS preprocessing pipeline.

Everything that a teacher / examiner might want to tweak lives here, so that
the actual preprocessing code stays short and readable.

Partner A (Data & Preprocessing Lead) owns this file.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# 1. PROJECT PATHS
# ---------------------------------------------------------------------------
# BASE_DIR points at the project root (the folder that contains "preprocessing").
BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Default dataset location and worksheet name.
DEFAULT_DATASET_PATH = RAW_DATA_DIR / "scam_msgs_authentic_1.xlsx"
SHEET_NAME = "Scam Messages"

# Output files produced by the pipeline.
CLEANED_DATASET_PATH = PROCESSED_DATA_DIR / "cleaned_dataset.csv"
TRAIN_DATASET_PATH = PROCESSED_DATA_DIR / "train.csv"
TEST_DATASET_PATH = PROCESSED_DATA_DIR / "test.csv"
VECTORIZER_PATH = OUTPUTS_DIR / "tfidf_vectorizer.pkl"
REPORT_PATH = OUTPUTS_DIR / "preprocessing_report.json"

# ---------------------------------------------------------------------------
# 2. DATASET COLUMNS
# ---------------------------------------------------------------------------
TEXT_COLUMN = "msg"                       # the raw SMS text
LABEL_COLUMN = "status"                   # the ML target  -> Scam / Genuine
SOURCE_COLUMN = "Authentic/Synthetic"     # analysis only, NEVER the target
CLEANED_TEXT_COLUMN = "cleaned_msg"       # produced by the pipeline

REQUIRED_COLUMNS = [TEXT_COLUMN, LABEL_COLUMN, SOURCE_COLUMN]

# ---------------------------------------------------------------------------
# 3. LABELS
# ---------------------------------------------------------------------------
# The only two labels allowed in the final dataset.
SCAM_LABEL = "Scam"
GENUINE_LABEL = "Genuine"
VALID_LABELS = [SCAM_LABEL, GENUINE_LABEL]

# Lowercase spellings that we accept and map onto the two canonical labels.
LABEL_MAP = {
    "scam": SCAM_LABEL,
    "fraud": SCAM_LABEL,
    "spam": SCAM_LABEL,
    "genuine": GENUINE_LABEL,
    "ham": GENUINE_LABEL,
    "legit": GENUINE_LABEL,
    "legitimate": GENUINE_LABEL,
    "normal": GENUINE_LABEL,
}

# Same idea for the Authentic/Synthetic column (used for reporting only).
SOURCE_MAP = {
    "authentic": "Authentic",
    "real": "Authentic",
    "synthetic": "Synthetic",
    "generated": "Synthetic",
}

# ---------------------------------------------------------------------------
# 4. DUPLICATE HANDLING
# ---------------------------------------------------------------------------
# What to do when the SAME message text appears with TWO DIFFERENT labels.
#   "drop"  -> remove every copy, because the correct label is unknown
#   "first" -> keep the first copy and its label
CONFLICTING_LABEL_POLICY = "drop"

# Many synthetic messages come from the SAME template and only differ by the
# amount and the link ("...bijli bill overdue hai, 500..." vs "...100,000...").
# After cleaning they become the identical string. If those twins are split
# across train and test, the test score is inflated because the model is graded
# on messages it already memorized.
#
#   False -> keep them (dataset stays large; the pipeline still REPORTS the
#            overlap so you know how optimistic the accuracy is)   [default]
#   True  -> also drop duplicates of the CLEANED text, giving a smaller but
#            much more honest evaluation
DEDUPLICATE_ON_CLEANED_TEXT = False

# ---------------------------------------------------------------------------
# 5. PLACEHOLDER TOKENS
# ---------------------------------------------------------------------------
# Instead of deleting URLs / phone numbers / amounts we swap them for a single
# word. This keeps the *information* ("there was a link here") without turning
# every unique link into its own TF-IDF feature.
URL_TOKEN = "urltoken"
PHONE_TOKEN = "phonetoken"
SHORTCODE_TOKEN = "shortcodetoken"
NUMBER_TOKEN = "numtoken"

PLACEHOLDER_TOKENS = [URL_TOKEN, PHONE_TOKEN, SHORTCODE_TOKEN, NUMBER_TOKEN]

# ---------------------------------------------------------------------------
# 6. NUMBER HANDLING
# ---------------------------------------------------------------------------
# How ordinary numbers are treated:
#   "token"  -> replace with NUMBER_TOKEN   (default)
#   "keep"   -> leave the digits untouched
#   "remove" -> delete them completely
NUMBER_MODE = "token"

# Replace long phone numbers with PHONE_TOKEN. In this dataset a phone number
# appears only in scam messages, so this is a very useful signal.
REPLACE_PHONE_NUMBERS = True

# Replace USSD codes such as *503# / *8171# with SHORTCODE_TOKEN.
REPLACE_USSD_CODES = True

# Well-known Pakistani SMS / service short codes that carry real meaning.
# These are PRESERVED as literal digits instead of becoming NUMBER_TOKEN,
# because "8171" (BISP) or "786" (Jazz) can genuinely help classification.
KNOWN_SHORT_CODES = {
    "8171",   # BISP / Ehsaas
    "786",    # Jazz
    "8000",
    "667",
    "3333",
    "1234",
}

# ---------------------------------------------------------------------------
# 7. TEXT CLEANING SWITCHES
# ---------------------------------------------------------------------------
LOWERCASE = True
REPLACE_URLS = True
REMOVE_PUNCTUATION = True
NORMALIZE_WHITESPACE = True
APPLY_ROMAN_URDU_NORMALIZATION = True
REMOVE_STOPWORDS = True

# Tokens shorter than this are dropped (a single stray letter is rarely useful).
MIN_TOKEN_LENGTH = 2

# ---------------------------------------------------------------------------
# 8. TRAIN / TEST SPLIT
# ---------------------------------------------------------------------------
TEST_SIZE = 0.20          # 80% training / 20% testing
RANDOM_STATE = 42         # fixed seed so the split is reproducible
STRATIFY = True           # keep the Scam/Genuine ratio in both halves

# ---------------------------------------------------------------------------
# 9. TF-IDF SETTINGS
# ---------------------------------------------------------------------------
# lowercase=False because our own cleaner has already lowercased the text.
TFIDF_SETTINGS = {
    "lowercase": False,
    "ngram_range": (1, 2),   # unigrams + bigrams; change to (1, 1) if required
    "min_df": 1,
    "max_df": 1.0,
    "sublinear_tf": True,
}
