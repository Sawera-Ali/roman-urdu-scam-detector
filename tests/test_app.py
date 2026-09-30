"""Integration checks against the real, unchanged trained artifacts."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import joblib
import numpy as np
import pandas as pd
from app.app import BASE_DIR, app, create_app
from app.analytics import ScanHistory

from preprocessing.cleaner import preprocess_text


class TestArtifactCompatibility(unittest.TestCase):
    def test_preprocessing_matches_all_saved_rows(self):
        for filename in ('train.csv', 'test.csv', 'cleaned_dataset.csv'):
            data = pd.read_csv(BASE_DIR / 'data' / 'processed' / filename)
            self.assertEqual(data.msg.map(preprocess_text).tolist(), data.cleaned_msg.tolist())

    def test_vectorizers_and_training_statistics_match(self):
        vectorizer = joblib.load(BASE_DIR / 'outputs/my_vectorizer.pkl')
        original = joblib.load(BASE_DIR / 'outputs/tfidf_vectorizer.pkl')
        self.assertEqual(vectorizer.vocabulary_, original.vocabulary_)
        np.testing.assert_array_equal(vectorizer.idf_, original.idf_)
        train = pd.read_csv(BASE_DIR / 'data/processed/train.csv')
        # Verify fitted IDF against training document frequencies without refitting.
        counts = vectorizer.transform(train.cleaned_msg)
        frequencies = np.asarray((counts > 0).sum(axis=0)).ravel()
        np.testing.assert_allclose(vectorizer.idf_, np.log((1 + len(train)) / (1 + frequencies)) + 1)
        model = joblib.load(BASE_DIR / 'outputs/nb_model.pkl')
        self.assertEqual(model.n_features_in_, counts.shape[1])
        for index, label in enumerate(model.classes_):
            np.testing.assert_allclose(model.feature_count_[index],
                                       np.asarray(counts[(train.status == label).to_numpy()].sum(axis=0)).ravel())


class TestWebApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.model, cls.vectorizer = app.extensions['classifier']

    def setUp(self):
        directory = tempfile.TemporaryDirectory(dir=BASE_DIR)
        self.addCleanup(directory.cleanup)
        replacement = patch.dict(app.extensions, scan_history=ScanHistory(Path(directory.name) / 'history.json'))
        replacement.start()
        self.addCleanup(replacement.stop)

    def test_home_and_assets(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        for anchor in ('home', 'checker', 'scam-iq', 'guide', 'how-it-works', 'about'):
            self.assertIn(f'id="{anchor}"', response.text)
        for asset in ('style.css', 'script.js', 'quiz.js'):
            with self.client.get('/static/' + asset) as asset_response:
                self.assertEqual(asset_response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_all_held_out_predictions_and_probabilities_use_saved_model(self):
        data = pd.read_csv(BASE_DIR / 'data/processed/test.csv')
        vectors = self.vectorizer.transform(data.cleaned_msg)
        predictions = self.model.predict(vectors)
        probabilities = self.model.predict_proba(vectors)
        for index, row in data.iterrows():
            response = self.client.post('/predict', json={'message': row.msg})
            self.assertEqual(response.status_code, 200)
            result = response.get_json()
            self.assertEqual(result['label'], predictions[index])
            label_index = list(self.model.classes_).index(predictions[index])
            self.assertEqual(result['confidence'], round(float(probabilities[index, label_index]) * 100, 1))
            self.assertNotIn('cleaned', result)
            self.assertNotIn('message', result)

    def test_invalid_payloads(self):
        for body in ({}, [], 'message', None, 9, {'message': None}, {'message': 5},
                     {'message': []}, {'message': ''}, {'message': '   '},
                     {'message': '!!!'}, {'message': 'hai ka ki'}, {'message': 'x' * 2001}):
            import json
            with self.subTest(body=body):
                response = self.client.post('/predict', data=json.dumps(body), content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertIsInstance(response.get_json()['error'], str)
        self.assertEqual(self.client.post('/predict', data='{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/predict', data='hello').status_code, 415)
        self.assertEqual(self.client.post('/predict', json={'message': 'zqxvjk'}).status_code, 422)
        self.assertEqual(self.client.post('/predict', data='x' * 40000, content_type='application/json').status_code, 413)

    def test_length_boundary(self):
        self.assertEqual(self.client.post('/predict', json={'message': 'account ' * 250}).status_code, 200)

    def test_missing_and_corrupt_models(self):
        with tempfile.TemporaryDirectory(dir=BASE_DIR) as directory:
            for corrupt in (False, True):
                if corrupt:
                    Path(directory, 'my_vectorizer.pkl').write_bytes(b'not a pickle')
                with self.assertLogs('app.app', level='ERROR'):
                    broken = create_app(directory).test_client()
                self.assertEqual(broken.get('/').status_code, 200)
                response = broken.post('/predict', json={'message': 'account verify karein'})
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(directory, response.text)

    def test_prediction_failure_does_not_leak_details(self):
        with patch.object(self.model, 'predict', side_effect=RuntimeError('private message')):
            with self.assertLogs('app.app', level='ERROR') as logs:
                response = self.client.post('/predict', json={'message': 'account verify karein'})
            self.assertEqual(response.status_code, 500)
            self.assertNotIn('private message', response.text + ''.join(logs.output))

    def test_no_probability_support(self):
        class ClassifierWithoutProbability:
            def predict(self, vector):
                return TestWebApp.model.predict(vector)
        with patch.dict(app.extensions, classifier=(ClassifierWithoutProbability(), self.vectorizer)):
            response = self.client.post('/predict', json={'message': 'account verify karein'})
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.get_json()['confidence'])


if __name__ == '__main__':
    unittest.main()
