# Local scan analytics

## Storage

`data/scan_history.json` is a UTF-8 JSON array, initialized to `[]` if missing. Each successful prediction appends exactly one record:

```json
[
  {
    "id": 1,
    "prediction": "Scam",
    "confidence": 94.2,
    "timestamp": "2026-09-30T13:20:00.000000+00:00"
  }
]
```

This is a schema example, not seeded data. Fields are:

- `id`: increasing integer, one above the largest saved ID.
- `prediction`: original model label, `Scam` or `Genuine`. The UI displays Genuine as Authentic.
- `confidence`: predicted-class probability percentage from the saved Naive Bayes model, or `null` if unavailable.
- `timestamp`: timezone-aware UTC ISO 8601 string. The browser displays local time. Legacy timestamps without an offset are interpreted as UTC.

No SMS text, text excerpts, cleaned text, sender details, or model features are stored. History is shared by everyone using this local app; it is not per-user. The file is ignored by Git. There is no database or external service.

Only successful model predictions append records. Validation errors and prediction failures do not. Dashboard requests, refreshes, navigation, and quiz answers never append records. Explicitly submitting the same message again is a new scan. A prediction that completes after a browser disconnect can still be recorded; network retries are not deduplicated.

## API and charts

`GET /api/analytics` returns:

```text
total_scans, total_scam, total_authentic,
scam_percentage, authentic_percentage,
recent_scans (latest 20, oldest first), recent_limit (20)
```

Summary totals cover the entire history. Empty history returns zero counts and empty recent scans. The UI shows an empty state rather than synthetic chart data. It refreshes on page load, successful predictions, dashboard navigation, window focus, and the Refresh analytics button.

Charts use local SVG and accessible labels, native hover titles, and a shared tooltip that responds to keyboard focus or touch. The donut uses exact counts; the confidence plot uses actual chronological records with fixed 0–100% axes. Null confidence values are omitted from the plot and marked Unavailable in the history table.

Risk severity is omitted: the predicted-class probability is uncalibrated and does not directly measure scam severity. Scam categories are omitted: the model predicts only Scam/Genuine.

## Failure handling and durability

Writes use a temporary file in the same directory, UTF-8 serialization, flush/fsync, and atomic replacement. A process-wide thread lock protects the read/append/write sequence. Empty files are treated as empty histories. Missing files are initialized. Invalid JSON or invalid records cause a 503 analytics response without erasing or replacing existing bytes. A failed write preserves the preceding history when replacement has not completed.

If storage is unavailable, the genuine ML prediction is still returned with `analytics_saved: false`. The UI warns that the result was not saved. Restore the JSON from a known good backup or repair it offline; the application deliberately does not silently discard corrupt history. No automated backup or retention policy is included.

This storage is suitable for a small single-process local/demo Flask server. It reads and rewrites the full file, so growing histories will slow down. Multiple server processes are not coordinated by the thread lock. Serverless production, including Vercel, requires durable external storage; local instance files are not a reliable persistence layer there.

## Verification

- 74 unit/integration tests: real Scam and Genuine predictions, exact record counts and genuine probabilities, refresh/recreated-app persistence, invalid-input exclusion, empty/missing files, corruption preservation, failed atomic replacement, and concurrent threaded writes.
- Isolated real-browser run: empty state, live totals (2/1/1 and 50%), donut and confidence marks, tooltip focus, history, refresh persistence, and widths 320–1440px.
- Existing browser checks passed for navigation, both ML result states, validation, quiz scoring/restart, technical section, mobile layout, console errors, and local-only requests.
- No tests add scans to the real history. Run `python -m unittest discover -s tests -q` and `python tests/analytics_browser_check.py` using the project virtual environment.
