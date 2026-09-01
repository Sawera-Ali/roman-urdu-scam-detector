"""
Roman Urdu Scam / Fraud SMS Detector - preprocessing package (Partner A).

This package turns the raw Excel dataset into ML-ready data:

    from preprocessing import run_preprocessing_pipeline

    results = run_preprocessing_pipeline()

    X_train_tfidf    = results["X_train_tfidf"]
    X_test_tfidf     = results["X_test_tfidf"]
    y_train          = results["y_train"]
    y_test           = results["y_test"]
    tfidf_vectorizer = results["tfidf_vectorizer"]

Partner B trains the models (Naive Bayes / SVM / Logistic Regression) and
builds the Streamlit UI. No model training happens in this package.
"""

from . import config
from .cleaner import (
    clean_text,
    normalize_whitespace,
    preprocess_text,
    remove_punctuation,
    remove_special_characters,
    remove_stopwords,
    replace_numbers,
    replace_urls,
    to_lowercase,
    tokenize,
)
from .data_loader import DatasetError, describe_dataset, load_dataset
from .feature_extraction import (
    create_tfidf_features,
    load_vectorizer,
    save_vectorizer,
    split_dataset,
    transform_new_messages,
)
from .pipeline import (
    build_statistics,
    preprocess_dataset,
    run_preprocessing_pipeline,
    show_samples,
)
from .roman_urdu_normalizer import ROMAN_URDU_NORMALIZATION, normalize_roman_urdu
from .stopwords import ACTIVE_STOPWORDS, PROTECTED_KEYWORDS, ROMAN_URDU_STOPWORDS
from .validator import (
    normalize_labels,
    remove_duplicates,
    remove_invalid_rows,
    validate_dataset,
)

__all__ = [
    "config",
    # loading
    "load_dataset",
    "describe_dataset",
    "DatasetError",
    # validation
    "validate_dataset",
    "normalize_labels",
    "remove_duplicates",
    "remove_invalid_rows",
    # cleaning
    "clean_text",
    "preprocess_text",
    "to_lowercase",
    "replace_urls",
    "replace_numbers",
    "remove_punctuation",
    "remove_special_characters",
    "normalize_whitespace",
    "tokenize",
    "remove_stopwords",
    "normalize_roman_urdu",
    "ROMAN_URDU_NORMALIZATION",
    "ROMAN_URDU_STOPWORDS",
    "ACTIVE_STOPWORDS",
    "PROTECTED_KEYWORDS",
    # features
    "split_dataset",
    "create_tfidf_features",
    "save_vectorizer",
    "load_vectorizer",
    "transform_new_messages",
    # pipeline
    "preprocess_dataset",
    "run_preprocessing_pipeline",
    "show_samples",
    "build_statistics",
]
