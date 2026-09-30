# ML integration audit

## Repository inspection

Inspected all five notebooks, the full preprocessing package, raw workbook, all three processed CSVs, all five serialized artifacts, preprocessing report, existing Flask frontend/backend, and preprocessing tests before replacing the application flow. Training notebooks, datasets, original preprocessing, and saved artifacts are preserved.

## Training and preprocessing

The preprocessing report describes 549 original records, validation and raw-text deduplication down to 543, then strict cleaned-text deduplication down to 238. The checked-in split contains 190 training and 48 test messages. The final cleaned dataset contains 195 synthetic and 43 authentic source examples. All 238 cleaned texts are reproduced exactly by `preprocessing.cleaner.preprocess_text`; the same check passes independently on train and test CSVs. No identical cleaned text overlaps between those split files. Related templates may still overlap semantically.

The old Flask `basic_clean()` lacked bare-domain replacement, spelling normalization, stopword removal, special-character handling, and the original number/shortcode behavior. It did not reproduce training text. Inference now calls the existing full preprocessing function.

## Notebook versus saved artifacts

`model_training1.ipynb` reads the strict split's `cleaned_msg` column, but its recorded run fits a new 535-feature vectorizer (`max_features=1500`, `min_df=2`, `max_df=.95`, unigrams/bigrams, sublinear TF).

- Naive Bayes: `MultinomialNB(alpha=1.0)`.
- Logistic Regression: five-fold weighted-F1 grid search over C, solver, and max iterations; recorded best C=1, solver=saga, max_iter=1000.
- SVM: five-fold weighted-F1 grid search over C, kernel, and gamma; recorded best C=1, linear kernel, gamma=scale, probability=True.

The notebook records identical held-out accuracy (47/48), scam precision (1.0), recall (21/22), and F1 (42/43) for all three. Recorded mean CV weighted-F1 is .947337 (NB), .963108 (LR), and .952611 (SVM). It selects Naive Bayes using the first maximum in a tied held-out F1 comparison. Vectorization happens before its CV, so CV folds share fitted vocabulary/IDF. Those CV results are not a fully isolated end-to-end evaluation.

The actual checked-in artifacts have **1,603 features**, not 535. The saved LR uses lbfgs, not the notebook's saga. The notebooks refer to `vectorizer.pkl`, which is absent. Consequently, the notebook's CV/AUC results cannot be attributed to the shipped estimators. The features/testing notebooks also skip preprocessing, use voting fractions as confidence, and add keyword risk scores. The statistics notebook logs sample text and includes manually supplied sample predictions. None of these experimental flows is used by the web application.

## Artifact pairing

- `outputs/my_vectorizer.pkl`: production TF-IDF vectorizer, lowercase=False, ngram_range=(1,2), min_df=1, max_df=1.0, sublinear_tf=True, 1,603 features.
- `outputs/tfidf_vectorizer.pkl`: original preprocessing artifact. Vocabulary indices and IDF weights are checked against the production vectorizer.
- `outputs/nb_model.pkl`: selected saved MultinomialNB, alpha=1, Genuine/Scam classes.
- `outputs/lr_model.pkl`: preserved LogisticRegression, C=1, lbfgs, max_iter=1000.
- `outputs/svm_model.pkl`: preserved linear SVC, C=1, probability=True.

Compatibility tests verify IDF against training document frequencies and compare NB's saved per-class feature counts with sums of the transformed current training rows. This is stronger evidence than feature-count matching alone and requires no retraining. All estimators were serialized with scikit-learn 1.7.2. The initially installed 1.9.0 could not predict with the saved SVM (`_effective_probability` missing); dependencies now pin 1.7.2.

## Selection and probabilities

Naive Bayes retains the notebook's selected algorithm and matches the checked-in held-out score when loaded with the saved 1,603-feature vectorizer. It is a simple existing classifier with genuine probability support. The notebook does not establish a unique winner; it reports a tie, and the different shipped artifacts preclude treating the notebook's higher LR CV score as evidence for the shipped LR.

The API uses `model.predict()` for the label and indexes `predict_proba()` by that exact label in `model.classes_`. It never substitutes vote counts, keyword scores, or hardcoded confidence. Probabilities are not independently calibrated; the UI states that limitation. Unknown-vocabulary input returns a validation response rather than a class-prior prediction.

## Privacy and scope

No submitted message text is persisted or included in API responses or application logs. Local analytics now persist only prediction, confidence, ID, and UTC timestamp; see ANALYTICS.md. Responses use `Cache-Control: no-store`; third-party assets and services are absent. The application does not authenticate senders or intercept SMS. Educational quiz answers are static examples, kept outside the classifier, datasets, and model artifacts.

## Verified shipped-artifact evaluation

Re-evaluated without training or modifying artifacts, using scikit-learn 1.7.2 and the existing 48-row test CSV:

| Saved model | Correct | Accuracy | Scam precision | Scam recall | Scam F1 |
| --- | --- | --- | --- | --- | --- |
| Naive Bayes | 47/48 | 97.92% | 100% | 95.45% | 97.67% |
| Logistic Regression | 47/48 | 97.92% | 100% | 95.45% | 97.67% |
| Linear SVM | 47/48 | 97.92% | 100% | 95.45% | 97.67% |

Each confusion matrix is [[26, 0], [1, 21]], in Genuine/Scam order. All three support predict_proba in the matching environment. These small held-out results do not establish real-world reliability. The public UI intentionally avoids an accuracy headline.

## Completed verification

- 68 unittest checks passed, including all 59 original preprocessing checks and 9 new integration checks.
- Every held-out message sent through the API matched direct saved-model predictions and predicted-class probabilities.
- Exact preprocessing parity on cleaned/train/test CSVs; equal vectorizer vocabulary indices and IDF weights; IDF and NB feature-count agreement with the training data.
- Flask started on localhost; homepage and all local static assets loaded.
- Headless Edge verified all navigation links, real scam/authentic results, empty and unknown-text errors, stale-result clearing, safe handling of HTML-like input, quiz feedback/score/restart, model information expansion, and mobile navigation.
- Layout overflow checks passed at 320, 390, 768, 1024, and 1440 pixels. Desktop/mobile screenshots were reviewed.
- No unexpected browser console errors or external requests. Quiz answers generated no prediction requests.

The local verification environment reuses installed scientific libraries because the C: temporary drive filled during installation. Flask, Playwright, and the matching scikit-learn are installed inside the workspace virtual environment; the global scikit-learn remains untouched. Temporary downloads were redirected to D:. The README documents the normal isolated setup for a fresh machine.
