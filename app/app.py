"""Local ScamGuard web app using the existing trained artifacts."""
from pathlib import Path
import sys
import warnings
import joblib
import numpy as np
from flask import Flask, jsonify, render_template, request
from sklearn.exceptions import InconsistentVersionWarning
from werkzeug.exceptions import HTTPException

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
from preprocessing.cleaner import preprocess_text
from app.analytics import AnalyticsError, ScanHistory

MAX_MESSAGE_LENGTH = 2000


def load_artifacts(directory):
    # Load only trusted repository artifacts; incompatible versions fail closed.
    with warnings.catch_warnings():
        warnings.simplefilter('error', InconsistentVersionWarning)
        vectorizer = joblib.load(directory / 'my_vectorizer.pkl')
        model = joblib.load(directory / 'nb_model.pkl')
    if set(model.classes_) != {'Scam', 'Genuine'}:
        raise ValueError('Unexpected model labels')
    probe = vectorizer.transform([preprocess_text('account verify karein')])
    if probe.shape[1] != model.n_features_in_:
        raise ValueError('Model and vectorizer feature counts differ')
    model.predict(probe)
    return model, vectorizer


def create_app(artifacts_dir=None, history_path=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 32 * 1024
    app.extensions['scan_history'] = ScanHistory(
        history_path if history_path is not None else BASE_DIR / 'data/scan_history.json')
    try:
        app.extensions['scan_history'].records()
    except AnalyticsError:
        app.logger.warning('Analytics unavailable; existing history left untouched.')
    try:
        app.extensions['classifier'] = load_artifacts(
            Path(artifacts_dir) if artifacts_dir else BASE_DIR / 'outputs')
    except Exception as error:
        app.extensions['classifier'] = None
        app.logger.error('Could not load ML artifacts (%s). Check files and dependency versions.',
                         type(error).__name__)

    @app.after_request
    def privacy_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; base-uri 'self'; "
            "form-action 'self'; frame-ancestors 'none'")
        return response

    @app.get('/')
    def home():
        return render_template('index.html', max_length=MAX_MESSAGE_LENGTH,
                               model_ready=app.extensions['classifier'] is not None)

    @app.get('/api/analytics')
    def analytics():
        try:
            return jsonify(app.extensions['scan_history'].summary())
        except AnalyticsError:
            return jsonify(error='Scan history could not be read. Existing data has been preserved. Check local storage and retry.'), 503

    @app.post('/predict')
    def predict():
        if not request.is_json:
            return jsonify(error='Send a JSON object containing a message.'), 415
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get('message'), str):
            return jsonify(error='Message must be a text string in a JSON object.'), 400
        message = data['message']
        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify(error=f'Use at most {MAX_MESSAGE_LENGTH:,} characters.'), 400
        if not message.strip():
            return jsonify(error='Paste or type a message first.'), 400
        artifacts = app.extensions['classifier']
        if artifacts is None:
            return jsonify(error='The message checker is temporarily unavailable. Please try again later.'), 503
        model, vectorizer = artifacts
        try:
            cleaned = preprocess_text(message)
            if not cleaned:
                return jsonify(error='Please enter a Roman Urdu message with meaningful words.'), 400
            vector = vectorizer.transform([cleaned])
            if vector.nnz == 0:
                return jsonify(error='The model does not recognize enough of this text to assess it. Try a complete Roman Urdu message.'), 422
            prediction = str(model.predict(vector)[0])
            if prediction not in {'Scam', 'Genuine'}:
                raise ValueError('Unexpected prediction')
            confidence = None
            if callable(getattr(model, 'predict_proba', None)):
                probabilities = model.predict_proba(vector)[0]
                probability = float(probabilities[list(model.classes_).index(prediction)])
                if np.isfinite(probability) and 0 <= probability <= 1:
                    confidence = round(probability * 100, 1)
            analytics_saved = True
            try:
                app.extensions['scan_history'].append(prediction, confidence)
            except AnalyticsError:
                analytics_saved = False
                app.logger.warning('Prediction succeeded but analytics could not be saved.')
            return jsonify(label=prediction, confidence=confidence, model_used='Naive Bayes',
                           analytics_saved=analytics_saved)
        except Exception as error:
            # Never log user text or exceptions that could contain it.
            app.logger.error('Prediction failed (%s)', type(error).__name__)
            return jsonify(error='We could not analyze this message. Please try again.'), 500

    @app.errorhandler(HTTPException)
    def http_error(error):
        message = 'Request is too large.' if error.code == 413 else error.name
        return jsonify(error=message), error.code

    return app


app = create_app()
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
