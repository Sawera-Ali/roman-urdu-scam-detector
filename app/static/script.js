'use strict';
const $ = (selector) => document.querySelector(selector);
const input = $('#messageInput');
const form = $('#detectorForm');
const button = $('#checkButton');
const result = $('#resultCard');
const empty = $('#emptyResult');
const error = $('#errorState');
let activeRequest = null;
const examples = {
  prize: 'Mubarak ho! Aap ne prize jeeta hai. Claim karne ke liye apni bank details bhejain.',
  reminder: 'Kal meeting 11 baje hai office mein, time pe pohanch jana.'
};
function resetResult() {
  result.hidden = true;
  empty.hidden = false;
  error.hidden = true;
  $('#analyticsSaveWarning').hidden = true;
}
function showError(message) {
  error.textContent = message;
  error.hidden = false;
}
function updateInput() {
  $('#charCount').textContent = `${input.value.length} / ${input.maxLength}`;
  input.removeAttribute('aria-invalid');
  resetResult();
  if (activeRequest) activeRequest.abort();
}
input.addEventListener('input', updateInput);
document.querySelectorAll('[data-example]').forEach((example) => {
  example.addEventListener('click', () => {
    input.value = examples[example.dataset.example];
    updateInput();
    input.focus();
  });
});
$('#clearButton').addEventListener('click', () => {
  input.value = '';
  updateInput();
  input.focus();
});
function renderResult(data) {
  const scam = data.label === 'Scam';
  result.className = scam ? 'is-scam' : 'is-authentic';
  $('#resultIcon').textContent = scam ? '!' : '✓';
  $('#resultKicker').textContent = scam ? 'SCAM DETECTED' : 'LOOKS AUTHENTIC';
  $('#resultTitle').textContent = scam ? 'Pause. This may be a scam.' : 'This looks authentic.';
  $('#resultDescription').textContent = scam
    ? 'The model classified this message as a potential scam. Treat the request with caution.'
    : 'The model classified this message as authentic. This does not verify the sender or their request.';
  const hasConfidence = typeof data.confidence === 'number' && Number.isFinite(data.confidence)
    && data.confidence >= 0 && data.confidence <= 100;
  $('#confidenceBlock').hidden = !hasConfidence;
  $('#confidenceValue').textContent = hasConfidence ? `${data.confidence.toFixed(1)}%` : '';
  const advice = scam
    ? ['Do not click suspicious links.', 'Do not share OTPs, PINs, or passwords.', 'Verify the request through official channels.']
    : ['Verify sensitive requests with a known contact.', 'Keep OTPs, PINs, and passwords private.', 'Take extra care before sending money.'];
  $('#resultAdvice').replaceChildren(...advice.map((text) => {
    const item = document.createElement('li');
    item.textContent = text;
    return item;
  }));
  empty.hidden = true;
  result.hidden = false;
}
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (activeRequest) return;
  resetResult();
  const message = input.value;
  if (!message.trim() || message.length > input.maxLength) {
    showError(!message.trim() ? 'Paste or type a message first.' : `Use at most ${input.maxLength} characters.`);
    input.setAttribute('aria-invalid', 'true');
    input.focus();
    return;
  }
  const controller = new AbortController();
  activeRequest = controller;
  let timedOut = false;
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 15000);
  button.disabled = true;
  button.textContent = 'Analyzing message…';
  const spinner = document.createElement('span');
  spinner.className = 'loading-spinner';
  spinner.setAttribute('aria-hidden', 'true');
  button.append(spinner);
  $('#resultRegion').setAttribute('aria-busy', 'true');
  try {
    const response = await fetch('/predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }), signal: controller.signal
    });
    let data;
    try { data = await response.json(); }
    catch { throw new Error('The checker returned an unreadable response. Please try again.'); }
    if (!response.ok) throw new Error(data.error || 'We could not analyze this message.');
    if (!['Scam', 'Genuine'].includes(data.label)) throw new Error('The checker returned an unexpected result. Please try again.');
    document.dispatchEvent(new Event('scan-completed'));
    if (input.value === message && !controller.signal.aborted) {
      renderResult(data);
      if (data.analytics_saved === false) {
        $('#analyticsSaveWarning').textContent = 'Your prediction is ready, but its analytics could not be saved. Check local storage before trying again.';
        $('#analyticsSaveWarning').hidden = false;
      }
    }
  } catch (err) {
    if (timedOut) showError('The check took too long. Please try again.');
    else if (err.name !== 'AbortError') showError(err instanceof TypeError
      ? 'Could not connect to the local checker. Check that the app is running and try again.' : err.message);
  } finally {
    clearTimeout(timeout);
    activeRequest = null;
    button.disabled = false;
    button.textContent = 'Analyze Message →';
    $('#resultRegion').setAttribute('aria-busy', 'false');
  }
});
const menu = $('#menuButton');
const navigation = $('#navigation');
function closeMenu() {
  navigation.classList.remove('open');
  menu.setAttribute('aria-expanded', 'false');
  menu.setAttribute('aria-label', 'Open navigation');
}
menu.addEventListener('click', () => {
  const open = navigation.classList.toggle('open');
  menu.setAttribute('aria-expanded', String(open));
  menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
});
navigation.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && navigation.classList.contains('open')) { closeMenu(); menu.focus(); }
});
const sections = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    navigation.querySelectorAll('a').forEach((link) => {
      const active = link.hash === `#${entry.target.id}`;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  });
}, { rootMargin: '-15% 0px -60% 0px' });
document.querySelectorAll('main > section').forEach((section) => sections.observe(section));
