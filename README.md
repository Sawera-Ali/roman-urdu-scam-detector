# Roman Urdu Scam / Fraud SMS Detector

A Machine Learning semester project that classifies a Roman Urdu SMS as **Scam** or **Genuine**.

This repository currently contains **Partner A's** work: the complete data and
preprocessing pipeline that turns the raw Excel dataset into ML-ready data.

---

## 1. Project purpose

Roman Urdu means Urdu written with English/Roman letters
(*"Aap ka account block ho jaye ga"*). Scam SMS in Pakistan are commonly written
this way: fake prize claims, fake bank/wallet alerts, account-blocking threats,
fake loan and job offers, and phishing links.

This is a **binary text classification** problem:

| Input | Output |
|---|---|
| A Roman Urdu SMS | `Scam` or `Genuine` |

---

## 2. Who does what

| Partner A (this code) | Partner B (not implemented here) |
|---|---|
| Load, validate and clean the dataset | Naive Bayes, SVM, Logistic Regression |
| Roman Urdu normalization + stopwords | Model training and evaluation |
| 80/20 train-test split | Accuracy, precision, recall, F1, confusion matrix |
| TF-IDF feature extraction | Model comparison and selection |
| Save processed data + vectorizer | Streamlit UI and live prediction |

Partner A trains **no models**. The deliverable is clean data plus a fitted
TF-IDF vectorizer.

---

## 3. Dataset structure

The dataset is an Excel file with a single worksheet named **`Scam Messages`**
and exactly three columns:

| Column | Meaning |
|---|---|
| `msg` | The SMS text. This is the input. |
| `status` | **The ML target.** `Scam` or `Genuine`. |
| `Authentic/Synthetic` | Whether the message is real or generated. **Used for reporting only — never as the target.** |

### Issues found in the actual data

The pipeline was built against the real file, not an idealised one. It detects
and reports all of the following automatically:

| Issue | Found | How it is handled |
|---|---|---|
| Inconsistent label casing (`scam`) | 9 rows | Normalized to `Scam` |
| Trailing whitespace in a label (`"Genuine "`) | 1 row | Trimmed and normalized |
| Inconsistent `Authentic/Synthetic` casing | 9 rows | Normalized to `Authentic` |
| Whitespace-only message | 1 row | Removed and reported |
| Exact duplicate messages | 4 rows | Removed and reported |
| **Same message with two different labels** | 1 pair | Both copies dropped (see below) |
| Broken/mojibake characters | 2 rows | Stripped during cleaning |

All counts are recomputed on every run — nothing is hard-coded.

---

## 4. How to place the dataset

```
data/raw/scam_msgs_authentic_1.xlsx
```

If your file lives elsewhere, pass it explicitly:

```bash
python run_preprocessing.py --file "C:/path/to/scam_msgs_authentic_1.xlsx"
```

---

## 5. How to run the preprocessing

```bash
pip install -r requirements.txt
python run_preprocessing.py
```

Useful options:

| Command | Effect |
|---|---|
| `python run_preprocessing.py` | Normal run |
| `python run_preprocessing.py --strict` | Also drop duplicate **cleaned** texts (leakage-free evaluation, see §12) |
| `python run_preprocessing.py --unigrams` | TF-IDF with unigrams only instead of unigrams + bigrams |
| `python run_preprocessing.py --no-save` | Run without writing files |
| `python -m unittest discover -s tests -v` | Run the 59 tests |

---

## 6. Preprocessing steps

Every message goes through this pipeline, in this exact order:

```
RAW SMS
  -> convert to string          (never crash on a blank or numeric cell)
  -> lowercase
  -> handle URLs                -> urltoken
  -> handle numbers             -> phonetoken / shortcodetoken / numtoken
  -> remove punctuation
  -> remove special characters
  -> normalize whitespace
  -> Roman Urdu spelling normalization
  -> tokenize
  -> remove Roman Urdu stopwords
  -> FINAL CLEANED SMS
```

**URLs and numbers are handled before punctuation removal.** Stripping `.` and
`/` first would destroy `https://bit.ly/abc`, and stripping `*` and `#` would
destroy `*503#`.

### Worked example

```
Original : Aap ka JazzCash ACCOUNT block ho jaye ga!!! Verify karein: https://fake-link.com
Cleaned  : aap jazzcash account block verify karein urltoken
```

### Why tokens instead of deletion

URLs, phone numbers and amounts are **replaced, not deleted**, because their
*presence* is a strong signal, while their *exact value* is noise.

In this dataset that intuition is measurable:

| Feature | Scam messages | Genuine messages |
|---|---|---|
| Contains a URL | 130 | 4 |
| Contains a phone number | 76 | 0 |

If every unique link became its own feature, that signal would be split across
25 near-useless columns. As `urltoken`, it becomes one strong column.

| Pattern | Becomes | Reason |
|---|---|---|
| `https://bit.ly/x`, `www.x.pk`, `ubl-update.co` | `urltoken` | Bare domains without `http://` are common in scam SMS, so they are caught too |
| `03021234567`, `[Number]` | `phonetoken` | Appears only in scam messages here |
| `*503#`, `*8171#` | `shortcodetoken` | Genuine telecom service codes |
| `8171`, `786` | *kept as digits* | Well-known service codes that carry real meaning |
| `Rs. 50,000`, `2500` | `numtoken` | The amount itself is arbitrary |

Number handling is configurable via `NUMBER_MODE` (`token` / `keep` / `remove`)
and `KNOWN_SHORT_CODES` in `preprocessing/config.py`.

---

## 7. Roman Urdu normalization

Roman Urdu has no fixed spelling, so the same word appears in many forms.
TF-IDF would treat each spelling as a separate feature and split the signal.

`preprocessing/roman_urdu_normalizer.py` holds a plain, easy-to-extend dict:

```python
ROMAN_URDU_NORMALIZATION = {
    "ap": "aap",
    "kren": "karein",
    "karen": "karein",
    "kia": "kya",
    "krna": "karna",
    "sy": "se",
    "whatsap": "whatsapp",
    ...
}
```

The mapping is deliberately **conservative**. It only covers variants actually
observed in this dataset, and it never touches:

- brand names (`jazzcash`, `easypaisa`, `telenor`)
- English words
- scam keywords (`free`, `prize`, `verify`, `block`)
- the placeholder tokens (`urltoken`, `phonetoken`, ...)

Replacement is **whole-word only**, so the `ap -> aap` rule does not corrupt
`apna` or `apni`. A value may expand into two words (`apka -> aap ka`).

> **Note for the viva:** the rule `kia -> kya` was requested in the project
> specification and is implemented, but be aware that in Roman Urdu `kia` can
> mean either *"what"* (kya) or *"did"* (kiya). It affects 1 row here. Remove
> the line from the dictionary if your evaluator prefers strict accuracy.

---

## 8. Stopword removal

An English-only stopword list would be useless on Roman Urdu text, so
`preprocessing/stopwords.py` ships a custom list of ~107 Roman Urdu function
words (`ka`, `ke`, `ki`, `se`, `hai`, `hain`, `ye`, `woh`, `aur` ...).

A second list, `PROTECTED_KEYWORDS`, is checked **first** and always wins, so
words that actually separate the two classes can never be removed:

```
free  prize  winner  urgent  verify  account  block  loan  click  link
reward  otp  balance  statement  transaction  reminder  due  ...
plus urltoken, phonetoken, numtoken, shortcodetoken
```

Both lists are configurable through `get_stopwords(extra_stopwords=, keep_words=)`,
and stopword removal can be switched off entirely with
`config.REMOVE_STOPWORDS = False`.

---

## 9. TF-IDF feature extraction

TF-IDF (Term Frequency – Inverse Document Frequency) converts cleaned text into
numbers a model can use.

- **TF** — how often a word appears in *this* message.
- **IDF** — how *rare* that word is across all messages.

A word scores high when it is frequent here but rare elsewhere, so `verify` or
`urltoken` get large weights, while a word appearing in every message gets a
small one.

Configuration (in `config.TFIDF_SETTINGS`, all adjustable):

```python
TfidfVectorizer(
    lowercase=False,      # our cleaner already lowercased the text
    ngram_range=(1, 2),   # unigrams + bigrams
    min_df=1,
    sublinear_tf=True,
)
```

`ngram_range=(1, 2)` lets the model learn single words (`account`, `prize`) as
well as two-word phrases (`account block`, `free prize`, `verify account`),
which are often far more informative than either word alone. Switch to
unigrams only with `python run_preprocessing.py --unigrams`.

---

## 10. 80/20 train-test split

```python
train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)
```

- **`test_size=0.20`** — 80% train, 20% test.
- **`random_state=42`** — the split is identical on every run, so results are reproducible.
- **`stratify=y`** — the Scam/Genuine ratio is preserved in both halves, which
  matters for binary classification. Verified: the class balance in train and
  test matches the full dataset to within 0.3%.

---

## 11. Data leakage prevention

**This is the single most important rule in the pipeline.**

The dataset is split *before* TF-IDF is fitted, and the vectorizer only ever
learns from the training text:

```python
# 1. split FIRST
X_train, X_test, y_train, y_test = train_test_split(...)

# 2. FIT on training data only -> learns vocabulary + IDF weights
X_train_tfidf = tfidf.fit_transform(X_train)

# 3. TRANSFORM the test data with that already-fitted vectorizer
X_test_tfidf = tfidf.transform(X_test)
```

**Never do this:**

```python
tfidf.fit_transform(all_messages)   # WRONG - test vocabulary leaks into training
X_train, X_test = train_test_split(...)
```

Fitting on everything would let the vectorizer see the test messages' words and
IDF statistics, making the reported accuracy optimistic and dishonest.

This is enforced by two automated tests
(`test_vocabulary_comes_from_training_only`) and verified on the real data:
**50 words appear only in the test set, and 0 of them are in the vocabulary.**

---

## 12. A second, subtler leakage risk (important)

The pipeline reports a warning you should not ignore:

```
[WARNING] 305 record(s) share an identical CLEANED text with another record
          (60 template group(s), largest group = 18 messages).
[WARNING] 75 of 109 test messages (68.81%) have a cleaned text that also
          appears in training.
```

**What is happening.** Most synthetic messages were generated from about 60
templates where only the amount and the link change:

```
"Warning: Aap ka bijli bill overdue hai, 500 abhi na bheja ... meezan-alert.com"
"Warning: Aap ka bijli bill overdue hai, 100,000 abhi na bheja ... ubl-update.co"
```

Once amounts become `numtoken` and links become `urltoken`, both collapse to the
**identical** cleaned string. When a random split puts one copy in training and
its twin in the test set, the model is graded on messages it has effectively
already memorized.

**What this means.** The accuracy Partner B reports in the default mode will be
optimistically high. That is worth stating honestly in the project report — it
is a property of the dataset, not a bug in the code.

**Two supported modes:**

| Mode | Records | Test overlap | Use for |
|---|---|---|---|
| Default | 543 | 68.8% | Matching the original dataset size |
| `--strict` | 238 | 0% | An honest, leakage-free accuracy figure |

```bash
python run_preprocessing.py --strict
```

Recommendation: report **both** numbers. Showing that you found the template
duplication, measured it, and quantified its effect is a stronger result than a
single inflated accuracy score.

---

## 13. Project structure

```
roman-urdu-scam-detector/
├── data/
│   ├── raw/
│   │   └── scam_msgs_authentic_1.xlsx      <- put the dataset here
│   └── processed/
│       ├── cleaned_dataset.csv             <- msg, cleaned_msg, status, Authentic/Synthetic
│       ├── train.csv                       <- 80%
│       └── test.csv                        <- 20%
│
├── preprocessing/
│   ├── __init__.py                 exports the public API
│   ├── config.py                   every tunable setting in one place
│   ├── data_loader.py              load_dataset() + clear error messages
│   ├── validator.py                validation, labels, duplicates, leakage checks
│   ├── cleaner.py                  the text cleaning pipeline
│   ├── roman_urdu_normalizer.py    spelling-variant dictionary
│   ├── stopwords.py                Roman Urdu stopwords + protected keywords
│   ├── feature_extraction.py       split + TF-IDF + save/load vectorizer
│   └── pipeline.py                 the main end-to-end pipeline
│
├── outputs/
│   ├── tfidf_vectorizer.pkl        the FITTED vectorizer (Partner B needs this)
│   └── preprocessing_report.json   all statistics, computed dynamically
│
├── notebooks/
│   └── data_exploration.ipynb      dataset statistics and charts for the report
│
├── tests/
│   └── test_preprocessing.py       59 tests
│
├── run_preprocessing.py            command-line entry point
├── requirements.txt
└── README.md
```

---

## 14. Generated files

| File | Contents |
|---|---|
| `data/processed/cleaned_dataset.csv` | `msg`, `cleaned_msg`, `status`, `Authentic/Synthetic` |
| `data/processed/train.csv` | 80% split: `msg`, `cleaned_msg`, `status` |
| `data/processed/test.csv` | 20% split: `msg`, `cleaned_msg`, `status` |
| `outputs/tfidf_vectorizer.pkl` | The fitted `TfidfVectorizer` |
| `outputs/preprocessing_report.json` | Every statistic, all computed dynamically |

---

## 15. How Partner B receives the data

### Option A — call the pipeline directly (recommended)

```python
from preprocessing import run_preprocessing_pipeline

results = run_preprocessing_pipeline()

X_train_tfidf    = results["X_train_tfidf"]      # sparse matrix (434, 1656)
X_test_tfidf     = results["X_test_tfidf"]       # sparse matrix (109, 1656)
y_train          = results["y_train"]            # 'Scam' / 'Genuine'
y_test           = results["y_test"]
tfidf_vectorizer = results["tfidf_vectorizer"]   # already fitted

# Partner B's part starts here:
from sklearn.naive_bayes import MultinomialNB
model = MultinomialNB()
model.fit(X_train_tfidf, y_train)
predictions = model.predict(X_test_tfidf)
```

### Option B — load the saved CSV files

```python
import pandas as pd
from preprocessing.feature_extraction import load_vectorizer

train = pd.read_csv("data/processed/train.csv")
test  = pd.read_csv("data/processed/test.csv")

vectorizer    = load_vectorizer()                        # the SAME fitted one
X_train_tfidf = vectorizer.transform(train["cleaned_msg"])
X_test_tfidf  = vectorizer.transform(test["cleaned_msg"])
y_train, y_test = train["status"], test["status"]
```

### Predicting a brand new SMS (for the Streamlit app)

Use this helper so a new message goes through **exactly** the same cleaning and
the **same saved vocabulary**:

```python
from preprocessing.feature_extraction import transform_new_messages

vectors = transform_new_messages("Aap ne 50000 ka prize jeeta hai! bit.ly/claim")
prediction = model.predict(vectors)     # -> array(['Scam'])
```

Never fit a new vectorizer for a new message — its feature columns would not
line up with the trained model.

---

## 16. Current results

Produced by the last run against the real dataset (recomputed every run):

```
Initial records ............ 549
Empty messages removed ....... 1
Duplicates removed ........... 3
Contradictory copies dropped . 2
Final records .............. 543   (Scam: 278, Genuine: 265)
Authentic: 43   Synthetic: 500

Training records ........... 434
Testing records ............ 109
TF-IDF features ........... 1656   (unigrams + bigrams)
```
