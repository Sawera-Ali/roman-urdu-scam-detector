"""
SMS text cleaning for Roman Urdu scam detection.

The full pipeline for ONE message is:

    RAW SMS
      -> convert to string
      -> lowercase
      -> handle URLs          (replaced with urltoken)
      -> handle numbers       (phones / USSD codes / amounts)
      -> remove punctuation
      -> remove special characters
      -> normalize whitespace
      -> Roman Urdu spelling normalization
      -> tokenize
      -> remove Roman Urdu stopwords
      -> final cleaned SMS (a plain string, ready for TF-IDF)

URLs and numbers are handled BEFORE punctuation removal, otherwise stripping
"." and "/" would destroy "https://bit.ly/abc" and "*503#".
"""

import re

from . import config
from .roman_urdu_normalizer import normalize_roman_urdu
from .stopwords import remove_stopwords as _remove_stopwords

# ---------------------------------------------------------------------------
# Regular expressions (compiled once, reused for every message)
# ---------------------------------------------------------------------------

# 1. Full URLs that start with http:// , https:// or www.
_FULL_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)

# 2. "Bare" domains typed without http, e.g. "ubl-update.co", "bit.ly/xyz".
#    Scam SMS in this dataset use this style a lot, so we must catch it.
_TLDS = (
    "com|net|org|pk|co|io|ly|me|app|info|xyz|site|page|link|biz|online|store|"
    "shop|club|top|live|fun|pro|tk|cc"
)
_BARE_DOMAIN_RE = re.compile(
    r"\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:" + _TLDS + r")\b(?:/\S*)?",
    re.IGNORECASE,
)

# 3. The literal placeholder "[Number]" used in some authentic messages.
_BRACKET_NUMBER_RE = re.compile(r"\[\s*number\s*\]", re.IGNORECASE)

# 4. USSD / service codes such as *503#  *8171#  *692002#
_USSD_RE = re.compile(r"\*\s?\d{2,7}\s?#")

# 5. Pakistani mobile numbers: 03001234567, +923001234567, 0300-1234567 ...
_PHONE_RE = re.compile(r"(?:\+?92|0)[\s-]?3\d{2}[\s-]?\d{7}\b|\b\d{11}\b")

# 6. Any remaining run of digits, possibly with commas / dots ("10,000", "1.5")
_NUMBER_RE = re.compile(r"\d[\d,.]*")

# 7. Punctuation we want to delete (anything that is not a word char or space).
_PUNCTUATION_RE = re.compile(r"[^\w\s]|_")

# 8. Anything left that is not a latin letter, digit or space (mojibake, emoji).
_SPECIAL_CHAR_RE = re.compile(r"[^a-z0-9\s]", re.IGNORECASE)

# 9. Runs of whitespace.
_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Individual cleaning steps (each one is small and testable on its own)
# ---------------------------------------------------------------------------

def to_lowercase(text):
    """Turn 'Aap Ka JAZZCASH' into 'aap ka jazzcash'."""
    return text.lower()


def replace_urls(text, url_token=config.URL_TOKEN):
    """
    Swap every link for a single token.

    We do NOT delete links: the mere presence of a link is a strong scam
    signal. But we also do not want every unique link to become its own
    TF-IDF feature.

        "verify karein https://fake-site.com"  ->  "verify karein urltoken"
        "click ubl-update.co"                  ->  "click urltoken"
    """
    text = _FULL_URL_RE.sub(url_token, text)     # http:// https:// www.
    text = _BARE_DOMAIN_RE.sub(url_token, text)  # bare domains like bit.ly/x
    return text


def replace_numbers(
    text,
    number_mode=None,
    replace_phone_numbers=None,
    replace_ussd_codes=None,
    known_short_codes=None,
):
    """
    Handle every kind of number that appears in an SMS.

    Order matters, from most specific to most general:
        1. "[Number]" placeholder       -> phonetoken
        2. USSD codes  (*503#)          -> shortcodetoken
        3. mobile numbers (03001234567) -> phonetoken
        4. known service codes (8171)   -> KEPT as digits, they carry meaning
        5. everything else (Rs 50,000)  -> numtoken
    """
    if number_mode is None:
        number_mode = config.NUMBER_MODE
    if replace_phone_numbers is None:
        replace_phone_numbers = config.REPLACE_PHONE_NUMBERS
    if replace_ussd_codes is None:
        replace_ussd_codes = config.REPLACE_USSD_CODES
    if known_short_codes is None:
        known_short_codes = config.KNOWN_SHORT_CODES

    # 1. "[Number]" is a masked phone number in the authentic messages.
    text = _BRACKET_NUMBER_RE.sub(config.PHONE_TOKEN, text)

    # 2. USSD short codes. Done before punctuation removal so "*" and "#" exist.
    if replace_ussd_codes:
        text = _USSD_RE.sub(config.SHORTCODE_TOKEN, text)

    # 3. Phone numbers.
    if replace_phone_numbers:
        text = _PHONE_RE.sub(config.PHONE_TOKEN, text)

    # 4 + 5. Remaining numbers.
    if number_mode == "keep":
        return text

    def _handle_number(match):
        raw_digits = re.sub(r"[^\d]", "", match.group(0))
        if raw_digits in known_short_codes:
            return raw_digits                      # preserve e.g. 8171 / 786
        if number_mode == "remove":
            return " "
        return config.NUMBER_TOKEN

    return _NUMBER_RE.sub(_handle_number, text)


def remove_punctuation(text):
    """Turn 'congratulations!!! you won!!!' into 'congratulations  you won   '."""
    return _PUNCTUATION_RE.sub(" ", text)


def remove_special_characters(text):
    """Drop anything left that is not a letter, digit or space (e.g. mojibake)."""
    return _SPECIAL_CHAR_RE.sub(" ", text)


def normalize_whitespace(text):
    """Turn 'aap     winner     hain  ' into 'aap winner hain'."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def tokenize(text):
    """Split a cleaned string into a list of words."""
    return text.split()


def remove_stopwords(tokens, stopwords=None, min_token_length=None):
    """Thin wrapper, so callers can import everything from this module."""
    if min_token_length is None:
        min_token_length = config.MIN_TOKEN_LENGTH
    return _remove_stopwords(
        tokens, stopwords=stopwords, min_token_length=min_token_length
    )


# ---------------------------------------------------------------------------
# The two functions the rest of the project actually calls
# ---------------------------------------------------------------------------

def clean_text(text):
    """
    Steps 1-7: raw SMS -> cleaned string (stopwords are still present).

    Example:
        clean_text("Aap ka ACCOUNT block!!! Verify: https://fake.com")
        -> "aap ka account block verify urltoken"
    """
    # Step 1 - always work with a string, never with NaN / float / None.
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Step 2 - lowercase
    if config.LOWERCASE:
        text = to_lowercase(text)

    # Step 3 - URLs (must run before punctuation removal)
    if config.REPLACE_URLS:
        text = replace_urls(text)

    # Step 4 - numbers (also before punctuation removal, for "*503#")
    text = replace_numbers(text)

    # Step 5 + 6 - punctuation and leftover special characters
    if config.REMOVE_PUNCTUATION:
        text = remove_punctuation(text)
        text = remove_special_characters(text)

    # Step 7 - whitespace
    if config.NORMALIZE_WHITESPACE:
        text = normalize_whitespace(text)

    return text


def preprocess_text(text):
    """
    The COMPLETE pipeline for one message: raw SMS -> final cleaned SMS.

    This is the single function that must also be used for any future unseen
    SMS, so that training data and prediction data are processed identically.
    """
    cleaned = clean_text(text)

    # Step 8 - Roman Urdu spelling normalization
    if config.APPLY_ROMAN_URDU_NORMALIZATION:
        cleaned = normalize_roman_urdu(cleaned)

    # Step 9 - tokenize
    tokens = tokenize(cleaned)

    # Step 10 - stopword removal
    if config.REMOVE_STOPWORDS:
        tokens = remove_stopwords(tokens)

    # Step 11 - back to a plain string for TfidfVectorizer
    return " ".join(tokens)
