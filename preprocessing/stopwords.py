"""
Roman Urdu stopword list.

Stopwords are extremely common words that carry little meaning on their own
("ka", "ke", "ki", "se", "hai"). Removing them shrinks the feature space and
lets TF-IDF focus on words that actually separate Scam from Genuine.

TWO IMPORTANT RULES
-------------------
1. An ENGLISH-only stopword list is useless here, because the messages are
   Roman Urdu. So we ship our own list.

2. We must NOT delete words that are strong scam / genuine indicators.
   PROTECTED_KEYWORDS below is checked FIRST, so those words always survive
   even if somebody adds them to the stopword list by accident.
"""

# ---------------------------------------------------------------------------
# Roman Urdu function words (pronouns, postpositions, helping verbs)
# ---------------------------------------------------------------------------
ROMAN_URDU_STOPWORDS = {
    # postpositions / particles
    "ka", "ki", "ke", "ko", "se", "me", "mein", "par", "pe", "pr", "tak",
    "ne", "na", "ho", "hi", "bhi", "to", "tou", "hy",
    # "to be"
    "hai", "hain", "hu", "hun", "hoon", "tha", "thi", "the", "thay",
    "ga", "gi", "ge", "gy", "hoga", "hogi", "honge",
    # pronouns / determiners
    "ye", "yeh", "wo", "woh", "is", "us", "in", "un", "iss", "uss",
    "jo", "ji", "yah", "vo",
    # conjunctions / fillers
    "aur", "ya", "agar", "magar", "lekin", "phir", "fir", "bs", "bas",
    "sab", "kuch", "kch", "koi", "kai", "har", "ek", "do",
    # very common light verbs
    "kar", "kare", "karo", "karna", "karne", "karta", "karti", "karte",
    "raha", "rahi", "rahe", "gaya", "gayi", "gaye", "jaye", "jana",
    "aa", "ja", "de", "le", "lo", "di", "dia", "diya",
    # English glue words that appear inside Roman Urdu SMS
    "the", "a", "an", "of", "for", "and", "or", "is", "are", "was", "to",
    "your", "you", "on", "at", "in", "it", "be", "will", "has", "have",
}

# ---------------------------------------------------------------------------
# Words that are NEVER removed, because they help classification.
# ---------------------------------------------------------------------------
PROTECTED_KEYWORDS = {
    # scam indicators
    "free", "muft", "prize", "inam", "winner", "win", "won", "jeet", "jeeta",
    "lottery", "bonus", "reward", "gift", "offer", "urgent", "fauri", "abhi",
    "jaldi", "verify", "verification", "confirm", "account", "block", "blocked",
    "band", "close", "suspend", "loan", "qarza", "click", "link", "otp", "pin",
    "password", "cnic", "atm", "card", "transfer", "bhejain", "bhejo", "send",
    "claim", "activate", "login", "update", "expire", "warning", "alert",
    "customs", "parcel", "fee", "charges", "tax", "refund", "whatsapp",
    "emergency", "penalty", "fine", "reactivate", "unlock", "security",
    # genuine indicators
    "balance", "statement", "transaction", "successful", "reminder", "due",
    "amount", "bill", "recharge", "package", "subscribe", "unsubscribe",
    "delivery", "order", "appointment", "class", "exam", "assignment",
    "meeting", "khana", "ammi", "abbu", "bhai", "behn",
    # brand / wallet names
    "jazzcash", "easypaisa", "sadapay", "nayapay", "jazz", "telenor", "ufone",
    "zong", "hbl", "ubl", "meezan", "bisp", "ehsaas", "bank",
    # our own placeholder tokens must always survive
    "urltoken", "phonetoken", "numtoken", "shortcodetoken",
}


def get_stopwords(extra_stopwords=None, keep_words=None):
    """
    Build the active stopword set.

    extra_stopwords : words to ADD to the list
    keep_words      : words to REMOVE from the list (i.e. keep them in the text)
    """
    stopwords = set(ROMAN_URDU_STOPWORDS)
    if extra_stopwords:
        stopwords.update(word.lower() for word in extra_stopwords)
    if keep_words:
        stopwords.difference_update(word.lower() for word in keep_words)
    # Protected keywords always win.
    stopwords.difference_update(PROTECTED_KEYWORDS)
    return stopwords


# The set actually used by the pipeline (protected words already removed).
ACTIVE_STOPWORDS = get_stopwords()


def remove_stopwords(tokens, stopwords=None, min_token_length=2):
    """
    Drop stopwords and very short tokens from a list of words.

    Example:
        >>> remove_stopwords(["aap", "ka", "account", "block", "ho", "jaye", "ga"])
        ['aap', 'account', 'block']
    """
    if stopwords is None:
        stopwords = ACTIVE_STOPWORDS

    kept = []
    for token in tokens:
        if token in PROTECTED_KEYWORDS:      # rule 2: protected words always stay
            kept.append(token)
            continue
        if token in stopwords:
            continue
        if len(token) < min_token_length:
            continue
        kept.append(token)
    return kept
