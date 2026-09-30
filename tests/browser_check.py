"""Optional real-browser smoke checks. Start app/app.py first."""
from pathlib import Path
import os
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.environ.get('SCAMGUARD_TEST_URL', 'http://127.0.0.1:5000')
ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / '.venv' / 'browser-check'
ARTIFACTS.mkdir(parents=True, exist_ok=True)
os.environ['TEMP'] = str(ARTIFACTS)
os.environ['TMP'] = str(ARTIFACTS)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
        requests = []
        page.on('request', lambda request: requests.append(request.url))
        response = page.goto(BASE_URL, wait_until='networkidle')
        assert response.status == 200
        expect(page.locator('h1')).to_contain_text('Check before')
        for link in page.locator('#navigation a').all():
            target = link.get_attribute('href')
            link.click()
            assert page.evaluate('location.hash') == target
            expect(page.locator(target)).to_be_visible()
        page.locator('#navigation a[href="#home"]').click()
        page.screenshot(path=str(ARTIFACTS / 'desktop.png'), full_page=True)
        page.locator('#checkButton').click()
        expect(page.locator('#errorState')).to_contain_text('Paste or type')
        for example, title in [('prize', 'SCAM DETECTED'), ('reminder', 'LOOKS AUTHENTIC')]:
            page.locator(f'[data-example="{example}"]').click()
            page.locator('#checkButton').click()
            expect(page.locator('#resultKicker')).to_have_text(title)
            expect(page.locator('#confidenceValue')).to_have_text(__import__('re').compile(r'\d+\.\d%'))
        page.screenshot(path=str(ARTIFACTS / 'checker.png'), full_page=True)
        page.locator('#messageInput').fill('zqxvjk')
        expect(page.locator('#resultCard')).to_be_hidden()
        # Expected validation errors produce browser console errors; check separately.
        before = len(errors)
        page.locator('#checkButton').click()
        expect(page.locator('#errorState')).to_contain_text('does not recognize')
        del errors[before:]
        page.locator('#messageInput').fill('<script>alert(1)</script> account verify karein')
        page.locator('#checkButton').click()
        expect(page.locator('#resultCard')).to_be_visible()
        page.locator('#clearButton').click()
        expect(page.locator('#messageInput')).to_have_value('')
        before_quiz = len([url for url in requests if url.endswith('/predict')])
        for answer in ['Scam', 'Authentic', 'Scam', 'Scam', 'Authentic']:
            page.locator(f'[data-answer="{answer}"]').click()
            expect(page.locator('#quizFeedback')).to_be_visible()
            page.locator('#quizNext').click()
        expect(page.locator('#quizFinalScore')).to_have_text('Your Scam IQ: 5/5')
        assert len([url for url in requests if url.endswith('/predict')]) == before_quiz
        page.locator('#quizRestart').click()
        expect(page.locator('#quizScore')).to_have_text('Score: 0')
        page.locator('[data-answer="Authentic"]').click()
        expect(page.locator('#quizFeedback')).to_contain_text('This example is scam')
        expect(page.locator('#quizScore')).to_have_text('Score: 0')
        page.locator('summary').click()
        expect(page.locator('.technical div')).to_be_visible()
        for width in (320, 390, 768, 1024, 1440):
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}px'
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('#menuButton').click()
        expect(page.locator('#menuButton')).to_have_attribute('aria-expanded', 'true')
        page.locator('#navigation a[href="#checker"]').click()
        expect(page.locator('#menuButton')).to_have_attribute('aria-expanded', 'false')
        page.screenshot(path=str(ARTIFACTS / 'mobile.png'), full_page=True)
        assert not errors, errors
        assert all(url.startswith(BASE_URL) for url in requests), requests
        browser.close()
        print('Browser checks passed: navigation, real predictions, validation, quiz, responsive widths, console, local-only requests.')


if __name__ == '__main__':
    run()
