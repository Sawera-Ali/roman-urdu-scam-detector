"""Metadata-only JSON storage for a single-process local/demo server.

The lock coordinates threads, not separate worker processes. Serverless
production (including Vercel) requires durable external storage.
"""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile
import threading


class AnalyticsError(Exception):
    """Unreadable history is preserved rather than silently overwritten."""


class ScanHistory:
    _lock = threading.RLock()

    def __init__(self, path):
        self.path = Path(path)

    def _read(self):
        if not self.path.exists():
            self._write([])
        text = self.path.read_text(encoding='utf-8-sig')
        records = json.loads(text) if text.strip() else []
        if not isinstance(records, list):
            raise ValueError('History must be an array')
        ids = set()
        for record in records:
            if not isinstance(record, dict) or set(record) != {'id', 'prediction', 'confidence', 'timestamp'}:
                raise ValueError('Invalid record fields')
            if type(record['id']) is not int or record['id'] < 1 or record['id'] in ids:
                raise ValueError('Invalid record ID')
            ids.add(record['id'])
            if record['prediction'] not in ('Scam', 'Genuine'):
                raise ValueError('Invalid prediction')
            confidence = record['confidence']
            if confidence is not None and (type(confidence) not in (float, int)
                    or not math.isfinite(confidence) or not 0 <= confidence <= 100):
                raise ValueError('Invalid confidence')
            datetime.fromisoformat(record['timestamp'])
        return records

    def _write(self, records):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=self.path.parent, prefix=self.path.name + '.', suffix='.tmp', delete=False) as stream:
                temporary = stream.name
                json.dump(records, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def records(self):
        with self._lock:
            try:
                return self._read()
            except (OSError, ValueError, TypeError) as error:
                raise AnalyticsError('History is unavailable') from error

    def append(self, prediction, confidence):
        with self._lock:
            try:
                records = self._read()
                records.append({
                    'id': max((row['id'] for row in records), default=0) + 1,
                    'prediction': prediction, 'confidence': confidence,
                    'timestamp': datetime.now(timezone.utc).isoformat(timespec='microseconds'),
                })
                self._write(records)
            except (OSError, ValueError, TypeError) as error:
                raise AnalyticsError('History could not be saved') from error

    def summary(self):
        records = self.records()
        def chronological(record):
            timestamp = datetime.fromisoformat(record['timestamp'])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return timestamp.timestamp(), record['id']
        records.sort(key=chronological)
        total = len(records)
        scam = sum(row['prediction'] == 'Scam' for row in records)
        return {
            'total_scans': total, 'total_scam': scam, 'total_authentic': total - scam,
            'scam_percentage': round(scam / total * 100, 1) if total else 0,
            'authentic_percentage': round((total - scam) / total * 100, 1) if total else 0,
            'recent_scans': records[-20:], 'recent_limit': 20,
        }
