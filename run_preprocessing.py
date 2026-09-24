"""
Command-line entry point for Partner A's preprocessing pipeline.

Usage
-----
    python run_preprocessing.py
    python run_preprocessing.py --file data/raw/scam_msgs_authentic_1.xlsx
    python run_preprocessing.py --strict        (also drop duplicate CLEANED texts)
    python run_preprocessing.py --unigrams      (TF-IDF with unigrams only)

After it finishes you will have:
    data/processed/cleaned_dataset.csv
    data/processed/train.csv
    data/processed/test.csv
    outputs/tfidf_vectorizer.pkl
    outputs/preprocessing_report.json
"""

import argparse
import sys

from preprocessing import config
from preprocessing.data_loader import DatasetError
from preprocessing.pipeline import run_preprocessing_pipeline


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Preprocess the Roman Urdu scam SMS dataset (Partner A)."
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Path to the Excel dataset (default: data/raw/scam_msgs_authentic_1.xlsx)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also remove rows whose CLEANED text duplicates another row. "
             "Gives a smaller dataset but an honest, leakage-free test score.",
    )
    parser.add_argument(
        "--unigrams",
        action="store_true",
        help="Use unigram-only TF-IDF instead of unigrams + bigrams.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Run the pipeline without writing any files to disk.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Hide the before/after preprocessing examples.",
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()

    # Apply the command-line overrides to the shared configuration.
    if arguments.strict:
        config.DEDUPLICATE_ON_CLEANED_TEXT = True
    if arguments.unigrams:
        config.TFIDF_SETTINGS["ngram_range"] = (1, 1)

    print("=" * 78)
    print("ROMAN URDU SCAM / FRAUD SMS DETECTOR - PREPROCESSING (PARTNER A)")
    print("=" * 78)

    try:
        results = run_preprocessing_pipeline(
            file_path=arguments.file,
            save_outputs=not arguments.no_save,
            show_examples=not arguments.quiet,
        )
    except DatasetError as error:
        print(f"\n{error}")
        return 1
    except Exception as error:                      # keep the message readable
        print(f"\n[ERROR] Preprocessing failed: {error}")
        return 1

    # A short summary of what Partner B receives.
    report = results["report"]
    print("\n" + "=" * 78)
    print("HANDOVER TO PARTNER B")
    print("=" * 78)
    print(f"  X_train_tfidf    : {results['X_train_tfidf'].shape}  (sparse matrix)")
    print(f"  X_test_tfidf     : {results['X_test_tfidf'].shape}  (sparse matrix)")
    print(f"  y_train          : {len(results['y_train'])} labels")
    print(f"  y_test           : {len(results['y_test'])} labels")
    print(f"  tfidf_vectorizer : fitted on training data only")
    print(f"  TF-IDF features  : {report['tfidf']['n_features']}")
    print("\n  Partner B can now run:")
    print("      model.fit(X_train_tfidf, y_train)")
    print("      predictions = model.predict(X_test_tfidf)")
    print("=" * 78)

    return 0


if __name__ == "__main__":
    sys.exit(main())
