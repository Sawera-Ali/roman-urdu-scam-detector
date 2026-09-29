"""
Train/test splitting and TF-IDF feature extraction.

THE MOST IMPORTANT RULE IN THIS FILE
------------------------------------
The TF-IDF vectorizer is fitted on the TRAINING TEXT ONLY.

    X_train_tfidf = vectorizer.fit_transform(X_train)   <- learns the vocabulary
    X_test_tfidf  = vectorizer.transform(X_test)        <- reuses it, never refits

Fitting on the whole dataset before splitting would leak information about the
test messages (their vocabulary and their IDF weights) into training. The test
score would then be optimistic and dishonest.
"""

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

from . import config


def split_dataset(
    dataframe,
    text_column=None,
    label_column=None,
    test_size=None,
    random_state=None,
    stratify=None,
):
    """
    Split the cleaned dataset into 80% training and 20% testing.

    Stratification keeps the Scam/Genuine ratio the same in both halves, which
    matters for a binary classification problem.

    Returns (X_train, X_test, y_train, y_test) where X are cleaned text
    strings and y are the 'Scam' / 'Genuine' labels.
    """
    if text_column is None:
        text_column = config.CLEANED_TEXT_COLUMN
    if label_column is None:
        label_column = config.LABEL_COLUMN
    if test_size is None:
        test_size = config.TEST_SIZE
    if random_state is None:
        random_state = config.RANDOM_STATE
    if stratify is None:
        stratify = config.STRATIFY

    features = dataframe[text_column]
    labels = dataframe[label_column]

    # Stratify only makes sense when every class has at least 2 members.
    stratify_on = labels if stratify and labels.value_counts().min() >= 2 else None
    if stratify and stratify_on is None:
        print("[WARNING] Not enough samples per class to stratify; splitting without it.")

    X_train, X_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_on,
    )
    return X_train, X_test, y_train, y_test


def create_tfidf_features(X_train, X_test, tfidf_settings=None):
    """
    Convert cleaned text into TF-IDF numeric vectors.

    TF-IDF in one line: a word scores high in a message when it appears often
    in THAT message (term frequency) but rarely across all other messages
    (inverse document frequency). So "verify" or "urltoken" get a high weight,
    while a word that appears everywhere gets a low one.

    Returns (X_train_tfidf, X_test_tfidf, vectorizer).
    """
    if tfidf_settings is None:
        tfidf_settings = config.TFIDF_SETTINGS

    vectorizer = TfidfVectorizer(**tfidf_settings)

    # FIT on training text only -> this learns the vocabulary and the IDF values.
    X_train_tfidf = vectorizer.fit_transform(X_train)

    # TRANSFORM the test text with the vectorizer that was already fitted.
    # Words that only exist in the test set are simply ignored, exactly as they
    # would be for a brand new SMS at prediction time.
    X_test_tfidf = vectorizer.transform(X_test)

    return X_train_tfidf, X_test_tfidf, vectorizer


def save_vectorizer(vectorizer, path=None):
    """
    Save the FITTED vectorizer so Partner B can reuse the identical vocabulary.

    A new SMS must never get its own new vectorizer, otherwise its feature
    columns would not line up with the trained model.
    """
    if path is None:
        path = config.VECTORIZER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, path)
    return path


def load_vectorizer(path=None):
    """Load the saved TF-IDF vectorizer from disk."""
    if path is None:
        path = config.VECTORIZER_PATH
    return joblib.load(path)


def transform_new_messages(messages, vectorizer=None):
    """
    Turn brand new, unseen SMS text into TF-IDF vectors for prediction.

    This is the function Partner B should call from the Streamlit app:

        vectors = transform_new_messages(["Aap ne 50000 jeeta hai!"])
        prediction = model.predict(vectors)

    It applies exactly the same cleaning as training, then reuses the SAVED
    vectorizer, so training and prediction stay perfectly consistent.
    """
    from .cleaner import preprocess_text     # imported here to avoid a cycle

    if isinstance(messages, str):
        messages = [messages]
    if vectorizer is None:
        vectorizer = load_vectorizer()

    cleaned_messages = [preprocess_text(message) for message in messages]
    return vectorizer.transform(cleaned_messages)
