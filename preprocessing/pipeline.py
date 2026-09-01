"""
The main preprocessing pipeline (Partner A's deliverable).

Running run_preprocessing_pipeline() performs every step in order:

     1. Load dataset                 9. Build the cleaned dataset
     2. Validate dataset            10. Split 80/20 (stratified)
     3. Normalize labels            11. Fit TF-IDF on TRAINING data only
     4. Remove invalid rows         12. Transform the test data
     5. Remove duplicates           13. Save processed datasets
     6. Clean text                  14. Save the TF-IDF vectorizer
     7. Normalize Roman Urdu        15. Generate the preprocessing report
     8. Remove stopwords            16. Return ML-ready outputs

It returns X_train_tfidf, X_test_tfidf, y_train, y_test and the fitted
vectorizer - the five things Partner B needs to train the models.

No model is trained here. That is Partner B's job.
"""

import json
import sys
from datetime import datetime

import pandas as pd

from . import config
from .cleaner import preprocess_text
from .data_loader import load_dataset
from .feature_extraction import (
    create_tfidf_features,
    save_vectorizer,
    split_dataset,
)
from .validator import (
    analyze_cleaned_duplicates,
    measure_train_test_overlap,
    normalize_labels,
    remove_duplicates,
    remove_invalid_rows,
    validate_dataset,
)


# ---------------------------------------------------------------------------
# Small logging helpers
# ---------------------------------------------------------------------------

def log(message, level="INFO"):
    """Print a timestamp-free, easy to read log line."""
    print(f"[{level}] {message}")


def safe_text(text, limit=None):
    """
    Make a string safe to print on a Windows console.

    Some authentic messages contain broken characters that the default
    Windows code page cannot display, which would crash print(). We replace
    anything non-printable rather than let the pipeline die on a log line.
    """
    text = str(text)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    if limit is not None and len(text) > limit:
        text = text[:limit] + "..."
    return text


# ---------------------------------------------------------------------------
# Dataset-level preprocessing
# ---------------------------------------------------------------------------

def preprocess_dataset(dataframe, text_column=None, cleaned_column=None):
    """
    Apply the full text pipeline to every message in the DataFrame.

    Adds a new column (default 'cleaned_msg') holding the final cleaned text.
    """
    if text_column is None:
        text_column = config.TEXT_COLUMN
    if cleaned_column is None:
        cleaned_column = config.CLEANED_TEXT_COLUMN

    dataframe = dataframe.copy()
    dataframe[cleaned_column] = dataframe[text_column].map(preprocess_text)
    return dataframe


def show_samples(dataframe, n=5, text_column=None, cleaned_column=None):
    """
    Print a few Original / Cleaned / Status examples so the preprocessing can
    be inspected by eye (useful for the project report and the viva).
    """
    if text_column is None:
        text_column = config.TEXT_COLUMN
    if cleaned_column is None:
        cleaned_column = config.CLEANED_TEXT_COLUMN

    print("\n" + "=" * 78)
    print("BEFORE / AFTER PREPROCESSING EXAMPLES")
    print("=" * 78)

    sample = dataframe.head(n) if len(dataframe) <= n else dataframe.sample(
        n, random_state=config.RANDOM_STATE
    )
    for _, row in sample.iterrows():
        print(f"\nStatus  : {row[config.LABEL_COLUMN]}")
        print(f"Original: {safe_text(row[text_column], 150)}")
        print(f"Cleaned : {safe_text(row[cleaned_column], 150)}")
    print("=" * 78 + "\n")


def build_statistics(dataframe):
    """Count labels and message sources dynamically (never hard-coded)."""
    label_counts = dataframe[config.LABEL_COLUMN].value_counts()
    source_counts = dataframe[config.SOURCE_COLUMN].value_counts()

    return {
        "total_records": int(len(dataframe)),
        "scam_count": int(label_counts.get(config.SCAM_LABEL, 0)),
        "genuine_count": int(label_counts.get(config.GENUINE_LABEL, 0)),
        "authentic_count": int(source_counts.get("Authentic", 0)),
        "synthetic_count": int(source_counts.get("Synthetic", 0)),
        "label_distribution": {str(k): int(v) for k, v in label_counts.items()},
        "source_distribution": {str(k): int(v) for k, v in source_counts.items()},
    }


# ---------------------------------------------------------------------------
# THE MAIN PIPELINE
# ---------------------------------------------------------------------------

def run_preprocessing_pipeline(
    file_path=None,
    save_outputs=True,
    show_examples=True,
    verbose=True,
):
    """
    Run every preprocessing step and return ML-ready data.

    Returns a dictionary containing:
        X_train_tfidf, X_test_tfidf, y_train, y_test, tfidf_vectorizer,
        plus the cleaned DataFrame and the full report.
    """
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_path": str(file_path or config.DEFAULT_DATASET_PATH),
    }

    # --- STEP 1: load ------------------------------------------------------
    log("Loading dataset...")
    dataframe = load_dataset(file_path)
    log("Dataset loaded successfully.")
    log(f"Initial records: {len(dataframe)}")
    report["initial_records"] = int(len(dataframe))
    report["columns"] = list(dataframe.columns)

    # --- STEP 2: validate (inspect only) -----------------------------------
    log("Validating dataset...")
    validation = validate_dataset(dataframe)
    report["validation"] = validation
    if verbose:
        for key, value in validation.items():
            log(f"  {key.replace('_', ' ').capitalize()}: {value}")

    # --- STEP 3: normalize labels -----------------------------------------
    log("Normalizing labels...")
    dataframe, label_info = normalize_labels(dataframe)
    report["label_normalization"] = label_info
    if label_info["labels_normalized"]:
        log(
            f"Fixed {label_info['labels_normalized']} inconsistent label spelling(s): "
            f"{label_info['label_spellings_fixed']}"
        )
    if label_info["invalid_labels"]:
        log(
            f"Invalid labels found and reported: {label_info['invalid_label_values']}",
            level="WARNING",
        )

    # --- STEP 4: remove invalid rows ---------------------------------------
    log("Removing invalid rows (missing / empty messages, bad labels)...")
    dataframe, invalid_info = remove_invalid_rows(dataframe, verbose=verbose)
    report["invalid_row_removal"] = invalid_info
    log(f"Records after removing invalid rows: {len(dataframe)}")

    # --- STEP 5: remove duplicates -----------------------------------------
    log("Removing duplicates...")
    dataframe, duplicate_info = remove_duplicates(dataframe, verbose=verbose)
    report["duplicate_removal"] = duplicate_info
    log(f"Records after removing duplicates: {len(dataframe)}")

    if len(dataframe) == 0:
        raise ValueError(
            "No usable records left after cleaning. Check the dataset contents."
        )

    # --- STEPS 6-8: clean text, normalize Roman Urdu, remove stopwords -----
    log("Cleaning SMS text...")
    log("Applying Roman Urdu normalization...")
    log("Removing Roman Urdu stopwords...")
    dataframe = preprocess_dataset(dataframe)

    # A message can become empty after cleaning (e.g. it was only digits).
    became_empty = dataframe[config.CLEANED_TEXT_COLUMN].str.strip() == ""
    if became_empty.any():
        log(
            f"{int(became_empty.sum())} message(s) became empty after cleaning "
            f"and were removed.",
            level="WARNING",
        )
        dataframe = dataframe[~became_empty].reset_index(drop=True)
    report["empty_after_cleaning_removed"] = int(became_empty.sum())

    # --- Template / near-duplicate check (data-leakage early warning) ------
    template_info = analyze_cleaned_duplicates(dataframe)
    report["cleaned_text_duplicates"] = template_info
    if template_info["cleaned_duplicate_rows"]:
        log(
            f"{template_info['cleaned_duplicate_rows']} record(s) share an identical "
            f"CLEANED text with another record "
            f"({template_info['cleaned_duplicate_groups']} template group(s), "
            f"largest group = {template_info['largest_template_group']} messages).",
            level="WARNING",
        )
        log(
            "These come from templates that differ only by amount/link. See "
            "config.DEDUPLICATE_ON_CLEANED_TEXT.",
            level="WARNING",
        )

    if config.DEDUPLICATE_ON_CLEANED_TEXT:
        log("Removing duplicates of the CLEANED text (strict mode)...")
        dataframe, cleaned_duplicate_info = remove_duplicates(
            dataframe, column=config.CLEANED_TEXT_COLUMN, verbose=verbose
        )
        report["cleaned_text_duplicate_removal"] = cleaned_duplicate_info
        log(f"Records after strict de-duplication: {len(dataframe)}")

    # --- STEP 9: final cleaned dataset -------------------------------------
    dataframe = dataframe.reset_index(drop=True)
    report["final_records"] = int(len(dataframe))
    report["statistics"] = build_statistics(dataframe)
    log(
        f"Final records: {len(dataframe)} "
        f"(Scam: {report['statistics']['scam_count']}, "
        f"Genuine: {report['statistics']['genuine_count']})"
    )

    if show_examples:
        show_samples(dataframe)

    # --- STEP 10: split 80/20 ---------------------------------------------
    log("Splitting dataset 80/20 (stratified)...")
    X_train, X_test, y_train, y_test = split_dataset(dataframe)
    log(f"Training records: {len(X_train)} | Testing records: {len(X_test)}")
    report["split"] = {
        "test_size": config.TEST_SIZE,
        "random_state": config.RANDOM_STATE,
        "stratified": config.STRATIFY,
        "training_records": int(len(X_train)),
        "testing_records": int(len(X_test)),
        "training_label_distribution": {
            str(k): int(v) for k, v in y_train.value_counts().items()
        },
        "testing_label_distribution": {
            str(k): int(v) for k, v in y_test.value_counts().items()
        },
    }

    # How much of the test set is a memorized twin of a training message?
    overlap = measure_train_test_overlap(X_train, X_test)
    report["train_test_overlap"] = overlap
    if overlap["test_records_also_in_train"]:
        log(
            f"{overlap['test_records_also_in_train']} of {overlap['test_records']} test "
            f"messages ({overlap['test_overlap_percent']}%) have a cleaned text that "
            f"also appears in training.",
            level="WARNING",
        )
        log(
            "Accuracy reported by Partner B will therefore be optimistic. Set "
            "config.DEDUPLICATE_ON_CLEANED_TEXT = True for a stricter evaluation.",
            level="WARNING",
        )

    # --- STEPS 11-12: TF-IDF (fit on train only!) --------------------------
    log("Fitting TF-IDF on training data...")
    log("Transforming test data...")
    X_train_tfidf, X_test_tfidf, vectorizer = create_tfidf_features(X_train, X_test)
    log(
        f"TF-IDF features: {X_train_tfidf.shape[1]} "
        f"(ngram_range={config.TFIDF_SETTINGS['ngram_range']})"
    )
    report["tfidf"] = {
        "settings": {
            key: (list(value) if isinstance(value, tuple) else value)
            for key, value in config.TFIDF_SETTINGS.items()
        },
        "n_features": int(X_train_tfidf.shape[1]),
        "train_matrix_shape": list(X_train_tfidf.shape),
        "test_matrix_shape": list(X_test_tfidf.shape),
        "fitted_on": "training data only (no data leakage)",
    }

    # --- STEPS 13-15: save everything --------------------------------------
    if save_outputs:
        log("Saving processed datasets...")
        config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        output_columns = [
            config.TEXT_COLUMN,
            config.CLEANED_TEXT_COLUMN,
            config.LABEL_COLUMN,
            config.SOURCE_COLUMN,
        ]
        dataframe[output_columns].to_csv(
            config.CLEANED_DATASET_PATH, index=False, encoding="utf-8"
        )

        train_frame = pd.DataFrame(
            {config.CLEANED_TEXT_COLUMN: X_train, config.LABEL_COLUMN: y_train}
        )
        test_frame = pd.DataFrame(
            {config.CLEANED_TEXT_COLUMN: X_test, config.LABEL_COLUMN: y_test}
        )
        # Keep the original message alongside, it helps when reading the CSV.
        train_frame[config.TEXT_COLUMN] = dataframe.loc[X_train.index, config.TEXT_COLUMN]
        test_frame[config.TEXT_COLUMN] = dataframe.loc[X_test.index, config.TEXT_COLUMN]

        column_order = [config.TEXT_COLUMN, config.CLEANED_TEXT_COLUMN, config.LABEL_COLUMN]
        train_frame[column_order].to_csv(
            config.TRAIN_DATASET_PATH, index=False, encoding="utf-8"
        )
        test_frame[column_order].to_csv(
            config.TEST_DATASET_PATH, index=False, encoding="utf-8"
        )

        log("Saving TF-IDF vectorizer...")
        save_vectorizer(vectorizer)

        log("Generating preprocessing report...")
        report["output_files"] = {
            "cleaned_dataset": str(config.CLEANED_DATASET_PATH),
            "train_dataset": str(config.TRAIN_DATASET_PATH),
            "test_dataset": str(config.TEST_DATASET_PATH),
            "tfidf_vectorizer": str(config.VECTORIZER_PATH),
            "preprocessing_report": str(config.REPORT_PATH),
        }
        with open(config.REPORT_PATH, "w", encoding="utf-8") as report_file:
            # default=str is a safety net: if any numpy/Path value slips in,
            # it is written as text instead of crashing the whole pipeline.
            json.dump(report, report_file, indent=4, ensure_ascii=False, default=str)

        log(f"Report saved to {config.REPORT_PATH}")

    log("Preprocessing completed successfully.")

    # --- STEP 16: return ML-ready outputs ----------------------------------
    return {
        "X_train_tfidf": X_train_tfidf,
        "X_test_tfidf": X_test_tfidf,
        "y_train": y_train,
        "y_test": y_test,
        "tfidf_vectorizer": vectorizer,
        # extras that are handy for the report / notebook
        "X_train_text": X_train,
        "X_test_text": X_test,
        "cleaned_dataframe": dataframe,
        "report": report,
    }
