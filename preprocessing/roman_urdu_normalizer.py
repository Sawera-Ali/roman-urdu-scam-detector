"""
Roman Urdu spelling normalization.

Roman Urdu has NO fixed spelling standard, so the same word shows up in many
forms ("karein" / "kren" / "karen"). TF-IDF would treat each spelling as a
completely separate feature, which splits the signal and weakens the model.

This module maps a small, curated set of KNOWN variants onto one standard form.

IMPORTANT DESIGN RULE
---------------------
We are deliberately CONSERVATIVE. We only normalize variations that were
actually observed in this dataset (or that are extremely common in Roman Urdu
SMS). We do NOT touch:
    - brand names   (jazzcash, easypaisa, sadapay, nayapay, telenor ...)
    - English words
    - scam keywords (free, prize, verify, block, claim ...)
    - our placeholder tokens (urltoken, phonetoken, numtoken, shortcodetoken)

The dictionary is a plain Python dict, so it is easy to extend later.
"""

import re

# ---------------------------------------------------------------------------
# The normalization dictionary:  variant spelling -> standard spelling
# ---------------------------------------------------------------------------
# A value may contain a space (e.g. "apka" -> "aap ka"); the replacement is
# done on whole words only, so nothing inside a longer word is touched.
ROMAN_URDU_NORMALIZATION = {
    # --- "aap" (you) ---------------------------------------------------
    "ap": "aap",
    "apka": "aap ka",
    "aapka": "aap ka",
    "apki": "aap ki",
    "aapki": "aap ki",
    "apke": "aap ke",
    "aapke": "aap ke",

    # --- "hai" / "hain" (is / are) -------------------------------------
    "hy": "hai",
    "he": "hai",
    "hei": "hai",
    "hen": "hain",
    "hn": "hain",
    "han": "hain",

    # --- "kya" (what) ---------------------------------------------------
    "kia": "kya",
    "ky": "kya",

    # --- "karna" family (to do) -----------------------------------------
    "krna": "karna",
    "krne": "karne",
    "kren": "karein",
    "karen": "karein",
    "krein": "karein",
    "kre": "karein",
    "kro": "karo",
    "kr": "kar",

    # --- "nahi" (no / not) ----------------------------------------------
    "nhi": "nahi",
    "nai": "nahi",
    "nahin": "nahi",

    # --- "mein" (in) -----------------------------------------------------
    "me": "mein",
    "mai": "mein",
    "mn": "mein",

    # --- "se" (from) -----------------------------------------------------
    "sy": "se",
    "sey": "se",

    # --- "pe" (on) -------------------------------------------------------
    "py": "pe",
    "pr": "pe",

    # --- misc. common variants ------------------------------------------
    "or": "aur",
    "wo": "woh",
    "ye": "yeh",
    "zuroori": "zaroori",
    "zarori": "zaroori",
    "zaruri": "zaroori",
    "whatsap": "whatsapp",
    "wtsp": "whatsapp",
    "mubarik": "mubarak",
    "mubarek": "mubarak",
    "manzor": "manzoor",
    "manzur": "manzoor",
    "ehsas": "ehsaas",
    "emdad": "imdad",
    "fori": "fauri",
    "foran": "fauri",
    "jldi": "jaldi",
    "tarikh": "tareekh",
    "tarik": "tareekh",
    "mufat": "muft",
}

# Words that must NEVER be rewritten, even if someone adds them to the
# dictionary by mistake. Placeholder tokens live here.
PROTECTED_FROM_NORMALIZATION = {
    "urltoken",
    "phonetoken",
    "numtoken",
    "shortcodetoken",
}

# ---------------------------------------------------------------------------
# Build ONE compiled regex for speed.
# ---------------------------------------------------------------------------
# Sorting by length (longest first) makes sure that, if two variants overlap,
# the longer one is matched first.
_ACTIVE_VARIANTS = [
    variant
    for variant in ROMAN_URDU_NORMALIZATION
    if variant not in PROTECTED_FROM_NORMALIZATION
]
_VARIANT_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, _ACTIVE_VARIANTS), key=len, reverse=True)) + r")\b"
)


def normalize_roman_urdu(text, mapping=None):
    """
    Replace known Roman Urdu spelling variants with their standard form.

    Works on whole words only, so "apna" is NOT changed by the "ap" rule.

    Example:
        >>> normalize_roman_urdu("ap ka account block ho jaye ga kren")
        'aap ka account block ho jaye ga karein'
    """
    if not isinstance(text, str):
        text = str(text)

    # Fast path: the default dictionary uses the pre-compiled regex.
    if mapping is None:
        return _VARIANT_PATTERN.sub(
            lambda match: ROMAN_URDU_NORMALIZATION[match.group(0)], text
        )

    # Custom dictionary supplied by the caller (used in tests / experiments).
    active = [v for v in mapping if v not in PROTECTED_FROM_NORMALIZATION]
    if not active:
        return text
    pattern = re.compile(
        r"\b(" + "|".join(sorted(map(re.escape, active), key=len, reverse=True)) + r")\b"
    )
    return pattern.sub(lambda match: mapping[match.group(0)], text)


def normalize_tokens(tokens, mapping=None):
    """Apply the same normalization to an already-tokenized list of words."""
    table = ROMAN_URDU_NORMALIZATION if mapping is None else mapping
    normalized = []
    for token in tokens:
        if token in PROTECTED_FROM_NORMALIZATION:
            normalized.append(token)
        else:
            # A mapping value may be two words, so split it back out.
            normalized.extend(table.get(token, token).split())
    return normalized
