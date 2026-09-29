"""
Dataset validation, label normalization and duplicate removal.

This module answers the question: "is every row usable for training?"
It never trains anything - it only checks, cleans and reports.
"""

import pandas as pd

from . import config


# ---------------------------------------------------------------------------
# 1. LABEL NORMALIZATION
# ---------------------------------------------------------------------------

def _count_values(values):
    """Count a list of strings and return a plain {str: int} dict.

    pandas returns numpy integers, which json.dump() cannot serialize, so we
    convert them to built-in ints here.
    """
    if not values:
        return {}
    counts = pd.Series(values).value_counts()
    return {str(name): int(count) for name, count in counts.items()}


def normalize_label_value(value):
    """
    Turn one raw label into 'Scam', 'Genuine', or None if it is not valid.

    Handles the messy real-world spellings found in the Excel file, such as
    'scam', 'SCAM', 'Genuine ' (with a trailing space).
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("", "nan", "none"):
        return None
    return config.LABEL_MAP.get(text)


def normalize_source_value(value):
    """Same idea for the Authentic/Synthetic column (used for reporting only)."""
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("", "nan", "none"):
        return None
    return config.SOURCE_MAP.get(text, str(value).strip())


def normalize_labels(dataframe):
    """
    Normalize the 'status' column to exactly 'Scam' / 'Genuine'.

    Also normalizes 'Authentic/Synthetic' to 'Authentic' / 'Synthetic'.
    Rows whose label cannot be recognized keep the value None, so that
    remove_invalid_rows() can drop and report them afterwards.

    Returns (new_dataframe, info_dict).
    """
    dataframe = dataframe.copy()

    original_labels = list(dataframe[config.LABEL_COLUMN])

    # Build the normalized labels as a plain Python list. We deliberately do
    # NOT use Series.map() here, because pandas turns a returned None into NA,
    # which would make the "is None" checks below silently miss invalid rows.
    normalized_labels = [normalize_label_value(value) for value in original_labels]

    # Which raw spellings were actually changed? Useful for the report.
    changed = [
        str(raw)
        for raw, new in zip(original_labels, normalized_labels)
        if new is not None and str(raw) != new
    ]
    invalid = [
        str(raw)
        for raw, new in zip(original_labels, normalized_labels)
        if new is None
    ]

    dataframe[config.LABEL_COLUMN] = normalized_labels
    dataframe[config.SOURCE_COLUMN] = dataframe[config.SOURCE_COLUMN].map(
        normalize_source_value
    )

    info = {
        "labels_normalized": len(changed),
        "label_spellings_fixed": _count_values(changed),
        "invalid_labels": len(invalid),
        "invalid_label_values": _count_values(invalid),
    }
    return dataframe, info


# ---------------------------------------------------------------------------
# 2. VALIDATION (inspect only, change nothing)
# ---------------------------------------------------------------------------

def validate_dataset(dataframe):
    """
    Inspect the dataset and return a validation report as a dictionary.

    Everything is calculated from the data, nothing is hard-coded.
    """
    text_series = dataframe[config.TEXT_COLUMN]
    label_series = dataframe[config.LABEL_COLUMN]

    # A message counts as "empty" when it is blank or only whitespace.
    text_as_string = text_series.astype(str)
    is_missing_message = text_series.isna()
    is_empty_message = (~is_missing_message) & (text_as_string.str.strip() == "")

    is_missing_label = label_series.isna() | (
        label_series.astype(str).str.strip().str.lower().isin(["", "nan", "none"])
    )
    is_invalid_label = (~is_missing_label) & (
        ~label_series.map(normalize_label_value).isin(config.VALID_LABELS)
    )

    # Duplicates are detected on a normalized version of the raw text
    # (lowercased + whitespace collapsed) so that trivial spacing or casing
    # differences still count as the same message.
    duplicate_key = build_duplicate_key(text_series)
    duplicate_count = int(duplicate_key.duplicated().sum())

    report = {
        "initial_records": int(len(dataframe)),
        "missing_messages": int(is_missing_message.sum()),
        "empty_messages": int(is_empty_message.sum()),
        "missing_labels": int(is_missing_label.sum()),
        "invalid_labels": int(is_invalid_label.sum()),
        "duplicate_messages": duplicate_count,
    }

    # How many rows would survive if we dropped every problem row?
    problem_rows = (
        is_missing_message | is_empty_message | is_missing_label | is_invalid_label
    )
    survivors = dataframe[~problem_rows].copy()
    survivors["_key"] = build_duplicate_key(survivors[config.TEXT_COLUMN])
    survivors["_label"] = survivors[config.LABEL_COLUMN].map(normalize_label_value)

    # After de-duplication each distinct message contributes exactly one row...
    unique_messages = int(survivors["_key"].nunique())

    # ...except messages that carry two different labels. Their true label is
    # unknown, so config.CONFLICTING_LABEL_POLICY decides whether they survive.
    labels_per_key = survivors.groupby("_key")["_label"].nunique()
    conflicting_groups = int((labels_per_key > 1).sum())

    report["duplicate_messages"] = duplicate_count
    report["conflicting_label_groups"] = conflicting_groups
    if config.CONFLICTING_LABEL_POLICY == "drop":
        report["valid_records_after_cleaning"] = unique_messages - conflicting_groups
    else:
        report["valid_records_after_cleaning"] = unique_messages

    return report


def build_duplicate_key(text_series):
    """
    Build the key used to decide whether two raw messages are 'the same'.

    We lowercase, strip, and collapse repeated whitespace so that
    'Hello   World ' and 'hello world' are treated as one message.
    """
    return (
        text_series.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )


# ---------------------------------------------------------------------------
# 3. REMOVING UNUSABLE ROWS
# ---------------------------------------------------------------------------

def remove_invalid_rows(dataframe, verbose=True):
    """
    Drop rows that cannot be used for training:
        - missing message
        - empty / whitespace-only message
        - missing or unrecognized label

    Returns (new_dataframe, info_dict). Nothing is removed silently.
    """
    dataframe = dataframe.copy()
    starting_count = len(dataframe)

    text_as_string = dataframe[config.TEXT_COLUMN].astype(str)
    is_missing_message = dataframe[config.TEXT_COLUMN].isna()
    is_empty_message = (~is_missing_message) & (text_as_string.str.strip() == "")
    is_bad_label = ~dataframe[config.LABEL_COLUMN].isin(config.VALID_LABELS)

    if verbose:
        if int(is_missing_message.sum()):
            print(f"[WARNING] {int(is_missing_message.sum())} missing message(s) removed.")
        if int(is_empty_message.sum()):
            print(f"[WARNING] {int(is_empty_message.sum())} empty message(s) removed.")
        if int(is_bad_label.sum()):
            print(
                f"[WARNING] {int(is_bad_label.sum())} row(s) with invalid/missing "
                f"labels found and removed."
            )

    rows_to_drop = is_missing_message | is_empty_message | is_bad_label
    cleaned = dataframe[~rows_to_drop].reset_index(drop=True)

    info = {
        "missing_messages_removed": int(is_missing_message.sum()),
        "empty_messages_removed": int(is_empty_message.sum()),
        "invalid_label_rows_removed": int(is_bad_label.sum()),
        "records_before": int(starting_count),
        "records_after": int(len(cleaned)),
    }
    return cleaned, info


# ---------------------------------------------------------------------------
# 4. DUPLICATE REMOVAL
# ---------------------------------------------------------------------------

def remove_duplicates(dataframe, column=None, policy=None, verbose=True):
    """
    Remove duplicate messages, and deal with the tricky case where the SAME
    message carries TWO DIFFERENT labels.

    column : which column to compare (default: the raw 'msg' column)
    policy : what to do with a conflicting group
             "drop"  -> remove every copy (the true label is unknown)
             "first" -> keep the first copy

    Returns (new_dataframe, info_dict).
    """
    if column is None:
        column = config.TEXT_COLUMN
    if policy is None:
        policy = config.CONFLICTING_LABEL_POLICY

    dataframe = dataframe.copy()
    starting_count = len(dataframe)

    # Compare on a normalized key, not on the raw string.
    if column == config.TEXT_COLUMN:
        key = build_duplicate_key(dataframe[column])
    else:
        key = dataframe[column].astype(str)
    dataframe["_duplicate_key"] = key

    # --- find groups where the same text has more than one distinct label ---
    labels_per_key = dataframe.groupby("_duplicate_key")[config.LABEL_COLUMN].nunique()
    conflicting_keys = set(labels_per_key[labels_per_key > 1].index)

    conflicting_examples = []
    for conflict_key in list(conflicting_keys)[:10]:
        rows = dataframe[dataframe["_duplicate_key"] == conflict_key]
        conflicting_examples.append(
            {
                "text": str(rows[config.TEXT_COLUMN].iloc[0])[:160],
                "labels": sorted(set(rows[config.LABEL_COLUMN].astype(str))),
                "copies": int(len(rows)),
            }
        )

    rows_dropped_by_conflict = 0
    if conflicting_keys:
        if verbose:
            print(
                f"[WARNING] {len(conflicting_keys)} message(s) appear with MORE THAN "
                f"ONE label (contradictory ground truth)."
            )
            for example in conflicting_examples[:3]:
                print(
                    f"[WARNING]   labels={example['labels']} "
                    f"copies={example['copies']} :: {example['text'][:90]}"
                )
        if policy == "drop":
            is_conflicting = dataframe["_duplicate_key"].isin(conflicting_keys)
            rows_dropped_by_conflict = int(is_conflicting.sum())
            dataframe = dataframe[~is_conflicting]
            if verbose:
                print(
                    f"[WARNING] Policy='drop': removed all {rows_dropped_by_conflict} "
                    f"copies of contradictory message(s)."
                )

    # --- now remove the ordinary duplicates (identical text AND label) ------
    before_plain_dedup = len(dataframe)
    dataframe = dataframe.drop_duplicates(subset="_duplicate_key", keep="first")
    plain_duplicates_removed = before_plain_dedup - len(dataframe)

    if verbose and plain_duplicates_removed:
        print(f"[INFO] Removed {plain_duplicates_removed} duplicate message(s).")

    dataframe = dataframe.drop(columns="_duplicate_key").reset_index(drop=True)

    info = {
        "records_before": int(starting_count),
        "records_after": int(len(dataframe)),
        "duplicates_removed": int(plain_duplicates_removed),
        "conflicting_label_groups": int(len(conflicting_keys)),
        "conflicting_rows_removed": int(rows_dropped_by_conflict),
        "conflicting_examples": conflicting_examples,
        "conflicting_label_policy": policy,
    }
    return dataframe, info


# ---------------------------------------------------------------------------
# 5. NEAR-DUPLICATE / TEMPLATE CHECK  (data-leakage early warning)
# ---------------------------------------------------------------------------

def analyze_cleaned_duplicates(dataframe, cleaned_column=None):
    """
    Count how many rows share the SAME cleaned text.

    Why this matters
    ----------------
    Many synthetic messages are built from one template where only the amount
    and the link change, for example:

        "... bijli bill overdue hai, 500 abhi na bheja ...  meezan-alert.com"
        "... bijli bill overdue hai, 100,000 abhi na bheja ... ubl-update.co"

    After cleaning, both become the identical string
    "warning aap bijli bill overdue numtoken abhi bheja ... urltoken".

    If such twins land on opposite sides of the train/test split, the model is
    effectively tested on messages it already memorized, and the reported
    accuracy will look far better than the truth.

    This function only MEASURES the problem and reports it. Whether to drop
    these rows is controlled by config.DEDUPLICATE_ON_CLEANED_TEXT.
    """
    if cleaned_column is None:
        cleaned_column = config.CLEANED_TEXT_COLUMN

    cleaned = dataframe[cleaned_column].astype(str)
    group_sizes = cleaned.value_counts()
    repeated_groups = group_sizes[group_sizes > 1]

    return {
        "unique_cleaned_texts": int(cleaned.nunique()),
        "cleaned_duplicate_rows": int(cleaned.duplicated().sum()),
        "cleaned_duplicate_groups": int(len(repeated_groups)),
        "largest_template_group": int(repeated_groups.max()) if len(repeated_groups) else 0,
    }


def measure_train_test_overlap(train_texts, test_texts):
    """
    Count how many TEST messages have a cleaned text that also appears in TRAIN.

    This is the direct, honest measure of how much the test score is inflated
    by duplicated templates. 0 means a completely clean evaluation.
    """
    train_set = set(pd.Series(train_texts).astype(str))
    test_series = pd.Series(test_texts).astype(str)
    overlapping = test_series.isin(train_set)

    return {
        "test_records": int(len(test_series)),
        "test_records_also_in_train": int(overlapping.sum()),
        "test_overlap_percent": round(
            100.0 * float(overlapping.sum()) / len(test_series), 2
        )
        if len(test_series)
        else 0.0,
    }
