# ScamGuard — Roman Urdu message checker

A local Flask application that checks manually pasted Roman Urdu messages with the repository's trained Naive Bayes classifier. Includes a responsive message checker, five-question Scam IQ quiz, practical Scam Guide, model information, and local scan analytics.

## Clone and run (Windows PowerShell)

Use Python 3.11 or newer (verified here with Python 3.14), Git, and an installed browser. The virtual environment is created locally; it is not included in the repository.

```powershell
git clone https://github.com/Sawera-Ali/roman-urdu-scam-detector.git
cd roman-urdu-scam-detector
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app/app.py
```

If PowerShell blocks activation, use the environment directly without changing execution policy:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app/app.py
```

### VS Code (Windows)

Open the cloned repository folder and install the recommended Microsoft Python and Python Debugger extensions. After creating `.venv` and installing requirements, select **ScamGuard: Run Flask app** in Run and Debug, then press **Ctrl+F5**. It runs `app/app.py` in the project environment and opens the Windows default external browser after the server responds. All shared launch paths are workspace-relative. Stop an existing server before starting another on port 5000. Browser startup diagnostics are local to `.venv/browser-launch.log`.

The terminal run command above also works on other platforms with that platform's virtual-environment Python; the shared Ctrl+F5/browser helper is Windows-specific.

Open http://127.0.0.1:5000. JavaScript is required for the checker and quiz. The app uses local assets, without external fonts, paid APIs, accounts, or a database. Submitted message text is not written to disk or application logs. Result, confidence, scan ID, and UTC time are saved locally in `data/scan_history.json`. Stop the server with Ctrl+C.

Use **scikit-learn 1.7.2**, the version that serialized the models. The app rejects mismatched estimator versions instead of silently returning potentially incompatible predictions. If the checker is unavailable, verify the dependency installation and the two artifacts below, then restart the server. Debug mode is disabled and the server binds to localhost.

## Actual inference path

```text
SMS → preprocessing.cleaner.preprocess_text
    → outputs/my_vectorizer.pkl (1,603 TF-IDF features)
    → outputs/nb_model.pkl (MultinomialNB)
    → Scam / Genuine (displayed as Authentic)
```

The shared preprocessing handles case, URLs, numbers, punctuation, Roman Urdu spelling normalization, tokenization, and stopwords. It reproduces every cleaned message in the checked-in CSV files exactly. Confidence is the predicted class's `predict_proba()` output, expressed as a percentage. It is an uncalibrated model estimate, not a verified probability that a sender is trustworthy.

The checker accepts up to 2,000 characters. Empty, malformed, excessive, and unrecognizable inputs get clear errors. Input with no vocabulary features is not assigned a misleading default label. The quiz uses separate fictional examples and never calls the model.

See [the ML integration audit](docs/ML_INTEGRATION.md) for artifact provenance, notebook differences, evaluation evidence, and limitations.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests include the existing preprocessing suite, exact CSV preprocessing parity, vectorizer and training-statistics compatibility, all held-out API predictions and probabilities, malformed input, length limits, and unavailable or failed models.

Optional browser checks (development only; starts an isolated temporary server and history):

```powershell
.venv\Scripts\python.exe -m pip install playwright
.venv\Scripts\python.exe tests/analytics_browser_check.py
```

The browser check uses installed Microsoft Edge in headless mode. Screenshots are saved under `.venv/browser-check/`.

## Repository layout

- `app/app.py`: Flask app factory, artifact loading, validation, prediction API.
- `app/templates/index.html`: public site and educational sections.
- `app/static/`: local CSS, checker interactions, and independent quiz.
- `preprocessing/`: original preprocessing package.
- `data/`: original raw workbook and processed datasets.
- `notebooks/`: preserved exploration, training, features, and testing notebooks.
- `outputs/`: preserved model files, vectorizers, report, and confusion matrix.
- `tests/`: preprocessing, integration, and optional browser checks.

## Existing preprocessing workflow

Preprocessing is **not needed to launch the application**. Its CLI remains available:

```powershell
python run_preprocessing.py --strict --no-save
```

Without `--no-save`, that command overwrites processed CSVs and the preprocessing vectorizer. The current checked-in data uses strict deduplication; the default configuration does not. Regenerating artifacts requires a deliberate, coordinated training workflow. The web app never trains, refits, or overwrites a model.

## Limitations

The dataset is small and mostly synthetic. Unseen spellings, unfamiliar topics, mixed scripts, and new scams can be misclassified. Always verify sensitive requests independently and keep OTPs, passwords, and PINs private. The application does not intercept SMS, authenticate senders, or provide institutional verification.

## Local analytics

Open **Dashboard** in the navigation. `GET /api/analytics` calculates totals and percentages across all saved scans and returns the latest 20 records in chronological order. The dashboard includes a Scam/Authentic donut, recent predicted-label confidence plot, and metadata-only history. Charts use local SVG with keyboard-accessible tooltips; no additional chart package or CDN is needed.

See [analytics storage and API](docs/ANALYTICS.md) for the exact schema, error recovery, and limitations. A fresh clone has no scan history. The app safely creates an empty `data/scan_history.json` on first launch; personal history is excluded from Git.
