"""Run browser checks against a temporary local server and isolated scan history."""
from pathlib import Path
import os
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.app import create_app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect

ARTIFACTS = ROOT / '.venv' / 'browser-check'
ARTIFACTS.mkdir(exist_ok=True)
os.environ['TEMP'] = str(ARTIFACTS)
os.environ['TMP'] = str(ARTIFACTS)

with tempfile.TemporaryDirectory(dir=ROOT / '.venv') as directory:
    history = Path(directory) / 'history.json'
    server = make_server('127.0.0.1', 0, create_app(history_path=history), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url + '/#dashboard')
            expect(page.locator('#analyticsEmpty')).to_be_visible()
            expect(page.locator('#totalScans')).to_have_text('0')
            for example in ('prize', 'reminder'):
                page.locator(f'[data-example="{example}"]').click()
                page.locator('#checkButton').click()
                expect(page.locator('#resultCard')).to_be_visible()
                expect(page.locator('#checkButton')).to_be_enabled()
            expect(page.locator('#totalScans')).to_have_text('2')
            expect(page.locator('#totalScam')).to_have_text('1')
            expect(page.locator('#totalAuthentic')).to_have_text('1')
            expect(page.locator('#scamRate')).to_have_text('50%')
            expect(page.locator('#scanHistory tr')).to_have_count(2)
            expect(page.locator('#distributionChart circle')).to_have_count(2)
            expect(page.locator('#confidenceChart circle')).to_have_count(2)
            page.locator('#distributionChart circle').first.focus()
            expect(page.locator('#chartTooltip')).to_contain_text('Scam: 1 scans (50%)')
            page.reload()
            expect(page.locator('#totalScans')).to_have_text('2')
            page.locator('#dashboard').scroll_into_view_if_needed()
            page.screenshot(path=str(ARTIFACTS / 'analytics-desktop.png'))
            for width in (320, 390, 768, 1024, 1440):
                page.set_viewport_size({'width': width, 'height': 1000})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('#dashboard').scroll_into_view_if_needed()
            page.screenshot(path=str(ARTIFACTS / 'analytics-mobile.png'))
            assert not errors, errors
            browser.close()
        # Existing navigation, checker, quiz, guide, and responsive smoke checks.
        os.environ['SCAMGUARD_TEST_URL'] = url
        import browser_check
        browser_check.run()
        print('Analytics browser checks passed; all test history was isolated.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
