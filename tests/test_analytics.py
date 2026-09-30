"""Real-model analytics integration and persistence checks; isolated history."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.app import BASE_DIR, create_app
from app.analytics import AnalyticsError, ScanHistory


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=BASE_DIR)
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'scan_history.json'
        self.app = create_app(history_path=self.path)
        self.client = self.app.test_client()
        self.store = self.app.extensions['scan_history']

    def scan(self, message):
        response = self.client.post('/predict', json={'message': message})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_real_predictions_counts_refresh_and_restart(self):
        self.assertEqual(json.loads(self.path.read_text()), [])
        self.assertEqual(self.client.get('/api/analytics').json['total_scans'], 0)
        scam = self.scan('Mubarak ho! Aap ne prize jeeta hai. Claim karne ke liye apni bank details bhejain.')
        self.assertEqual(scam['label'], 'Scam')
        self.assertEqual(len(self.store.records()), 1)
        genuine = self.scan('Kal meeting 11 baje hai office mein, time pe pohanch jana.')
        self.assertEqual(genuine['label'], 'Genuine')
        rows = self.store.records()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['confidence'], scam['confidence'])
        self.assertEqual(rows[1]['confidence'], genuine['confidence'])
        for row in rows:
            self.assertEqual(set(row), {'id', 'prediction', 'confidence', 'timestamp'})
        for _ in range(3):
            self.client.get('/')
            summary = self.client.get('/api/analytics').json
            self.assertEqual((summary['total_scans'], summary['total_scam'], summary['total_authentic']), (2, 1, 1))
            self.assertEqual(summary['scam_percentage'], 50)
        restarted = create_app(history_path=self.path).test_client()
        self.assertEqual(restarted.get('/api/analytics').json, summary)
        self.assertEqual(self.store.records(), rows)

    def test_invalid_requests_never_saved(self):
        for message in ('', '   ', '!!!', 'zqxvjk', 'x' * 2001, 4, None):
            self.assertNotEqual(self.client.post('/predict', json={'message': message}).status_code, 200)
        self.assertEqual(self.store.records(), [])
        with patch.object(self.app.extensions['classifier'][0], 'predict', side_effect=ValueError()):
            self.assertEqual(self.client.post('/predict', json={'message': 'account verify'}).status_code, 500)
        self.assertEqual(self.store.records(), [])

    def test_empty_missing_and_corrupt_files(self):
        self.path.write_text('', encoding='utf-8')
        self.assertEqual(self.client.get('/api/analytics').json['total_scans'], 0)
        self.path.unlink()
        self.assertEqual(self.client.get('/api/analytics').json['total_scans'], 0)
        self.store.append('Scam', 90)
        damaged = self.path.read_text() + 'broken'
        self.path.write_text(damaged, encoding='utf-8')
        self.assertEqual(self.client.get('/api/analytics').status_code, 503)
        prediction = self.scan('account verify karein')
        self.assertFalse(prediction['analytics_saved'])
        self.assertEqual(self.path.read_text(), damaged)

    def test_failed_atomic_write_preserves_history(self):
        self.store.append('Genuine', None)
        before = self.path.read_bytes()
        with patch('app.analytics.os.replace', side_effect=PermissionError()):
            prediction = self.scan('account verify karein')
        self.assertFalse(prediction['analytics_saved'])
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_concurrent_appends_keep_unique_records(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda _: self.store.append('Scam', 81.2), range(24)))
        rows = self.store.records()
        self.assertEqual([row['id'] for row in rows], list(range(1, 25)))
        summary = self.store.summary()
        self.assertEqual(summary['total_scans'], 24)
        self.assertEqual(len(summary['recent_scans']), 20)
        self.assertEqual(summary['recent_scans'][0]['id'], 5)

    def test_invalid_schema_is_not_erased(self):
        for data in ({}, [{'id': 1}], [{'id': 1, 'prediction': 'Scam', 'confidence': float('nan'), 'timestamp': '2026-09-30T12:00:00Z'}]):
            self.path.write_text(json.dumps(data))
            before = self.path.read_bytes()
            with self.assertRaises(AnalyticsError):
                self.store.append('Genuine', 80)
            self.assertEqual(before, self.path.read_bytes())


if __name__ == '__main__':
    unittest.main()
