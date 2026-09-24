# Roman Urdu Scam Detector

This project detects whether a Roman Urdu SMS is likely a scam or genuine message using a machine learning pipeline based on text preprocessing and TF-IDF features.

The repository focuses on the data preparation and preprocessing stage, which converts raw SMS messages into clean, model-ready text before a classifier is trained.

## Project goal

Roman Urdu is widely used in Pakistan for SMS and WhatsApp messages. Many scam messages use this style of language, often containing fake prize claims, OTP alerts, blocked-account warnings, phishing links, and fake bank notifications.

The goal is to build a binary classifier:

- Input: Roman Urdu SMS message
- Output: Scam or Genuine

## What this project includes

- Raw dataset handling and validation
- Label normalization and duplicate removal
- Roman Urdu text cleaning and normalization
- URL, phone number, and amount tokenization
- Stopword removal for Roman Urdu
- TF-IDF vectorization for model training
- Train/test split preparation
- Output files for downstream model training

## Tech stack

- Python
- Pandas
- NumPy
- scikit-learn
- OpenPyXL
- Flask (for the demo app)

## Repository structure

```text
roman-urdu-scam-detector/
├── app/
│   ├── app.py
│   ├── static/
│   └── templates/
├── data/
│   ├── processed/
│   └── raw/
├── notebooks/
├── outputs/
├── preprocessing/
│   ├── __init__.py
│   ├── cleaner.py
│   ├── config.py
│   ├── data_loader.py
│   ├── feature_extraction.py
│   ├── pipeline.py
│   ├── roman_urdu_normalizer.py
│   ├── stopwords.py
│   └── validator.py
├── tests/
├── app.py
├── README.md
├── requirements.txt
├── run_preprocessing.py
└── .gitignore
```

## Dataset

The dataset should be placed in:

```text
data/raw/
```

The preprocessing pipeline expects an Excel file containing SMS text and label columns, then saves the processed outputs into the processed folder.

## Setup

1. Create a virtual environment (optional but recommended)
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run preprocessing

From the project root:

```bash
python run_preprocessing.py
```

Optional arguments:

```bash
python run_preprocessing.py --file "data/raw/your_dataset.xlsx"
python run_preprocessing.py --strict
python run_preprocessing.py --unigrams
python run_preprocessing.py --no-save
python run_preprocessing.py --quiet
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Application demo

The Flask app is in:

```text
app/app.py
```

To run it:

```bash
python app/app.py
```

Then open the local URL shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

## Generated outputs

After preprocessing, the project generates:

- cleaned_dataset.csv
- train.csv
- test.csv
- tfidf_vectorizer.pkl
- preprocessing_report.json

These are used by the downstream model-training phase.

## Notes

- This repository focuses on data cleaning and preparation.
- No final model training is done here; the processed outputs are intended for the next stage of the project.
- The preprocessing pipeline is designed to reduce leakage and preserve important scam signals such as links, numbers, and alert words.

## Summary

This project converts noisy Roman Urdu scam messages into structured text features that a classifier can use. It is a complete preprocessing foundation for a scam detection system and is ready to be extended with Naive Bayes, SVM, Logistic Regression, or similar models.
