const scamExample =
  'Congratulations! Aap ne 50000 ka prize jeeta hai, claim karein: bit.ly/win2024';

const genuineExample =
  'Kal meeting 11 baje hai office mein, time pe pohanch jana.';

const $ = (selector) => document.querySelector(selector);

const messageInput = $('#messageInput');
const resultCard = $('#resultCard');
const errorState = $('#errorState');
const checkButton = $('#checkButton');
const charCount = $('#charCount');

let selectedModel =
  document.querySelector('[data-model].active')?.dataset.model || 'nb';

/* --------------------------------------------------------------------
   Turns the real cleaned text + label from the backend into a short,
   honest explanation line — based on what the model actually saw,
   not a fake pre-classification heuristic.
   -------------------------------------------------------------------- */
function explainResult(cleaned, scam) {
  const indicators = [];

  if (cleaned.includes('urltoken')) indicators.push('an unfamiliar link');
  if (cleaned.includes('phonetoken')) indicators.push('a phone number');
  if (/\b(verify|block|urgent|prize|jeeta|otp|password|account)\b/.test(cleaned)) {
    indicators.push('reward or account-pressure language');
  }

  if (scam) {
    return `The model picked up on ${
      indicators.length
        ? indicators.join(', ')
        : 'word patterns commonly found in suspicious messages'
    }. Avoid opening the link or sharing an OTP.`;
  }

  return 'No strong reward, payment, or account-verification signal was found in the cleaned text. Still verify anything important through a known contact.';
}

async function classifyMessage(message, model) {
  const response = await fetch('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, model }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || 'Kuch ghalat ho gaya.');
  }

  const scam = data.label === 'Scam';

  return {
    scam,
    confidence: data.confidence,
    cleaned: data.cleaned,
    model: data.model_used,
    explanation: explainResult(data.cleaned, scam),
  };
}

function renderResult(result) {
  resultCard.hidden = false;

  resultCard.className = `result-card ${result.scam ? 'is-scam' : ''}`;

  const confidenceBlock =
    result.confidence !== null && result.confidence !== undefined
      ? `
    <div class="confidence">
      <div class="confidence-meta">
        <span>Model confidence · ${result.model}</span>
        <strong>${result.confidence}%</strong>
      </div>

      <div class="confidence-track">
        <div class="confidence-fill" style="width: ${result.confidence}%"></div>
      </div>
    </div>
  `
      : `
    <div class="confidence">
      <div class="confidence-meta">
        <span>${result.model} prediction</span>
      </div>
    </div>
  `;

  resultCard.innerHTML = `
    <div class="result-header">
      <div class="result-icon">
        ${result.scam ? '!' : '✓'}
      </div>

      <div>
        <h4>
          ${result.scam ? 'This looks like a scam' : 'No strong scam signal found'}
        </h4>

        <p>
          ${
            result.scam
              ? 'Treat this message as unsafe.'
              : 'Still verify anything important through a known contact.'
          }
        </p>
      </div>
    </div>

    ${confidenceBlock}

    <div class="result-explanation">
      <strong>Why it landed here:</strong>
      ${result.explanation}
    </div>

    <button class="cleaned-toggle" id="cleanedToggle" type="button" aria-expanded="false">
      What the model saw <span>⌄</span>
    </button>

    <pre class="cleaned-text" id="cleanedText" hidden>${result.cleaned}</pre>
  `;

  const cleanedToggle = $('#cleanedToggle');
  const cleanedText = $('#cleanedText');

  cleanedToggle.addEventListener('click', () => {
    const isHidden = cleanedText.hidden;
    cleanedText.hidden = !isHidden;
    cleanedToggle.setAttribute('aria-expanded', String(isHidden));
  });
}

function showError(message) {
  errorState.hidden = false;
  errorState.textContent = `!  ${message}`;
}

messageInput.addEventListener('input', () => {
  charCount.textContent = `${messageInput.value.length} / 500`;
  errorState.hidden = true;
});

document.querySelectorAll('[data-model]').forEach((button) => {
  if (button.disabled) return;

  button.addEventListener('click', () => {
    selectedModel = button.dataset.model;

    document.querySelectorAll('[data-model]').forEach((option) => {
      const active = option === button;
      option.classList.toggle('active', active);
      option.setAttribute('aria-checked', String(active));
    });
  });
});

document.querySelectorAll('[data-example]').forEach((button) => {
  button.addEventListener('click', () => {
    messageInput.value =
      button.dataset.example === 'scam' ? scamExample : genuineExample;

    messageInput.dispatchEvent(new Event('input'));

    resultCard.hidden = true;
    messageInput.focus();
  });
});

$('#detectorForm').addEventListener('submit', async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();

  if (!message) {
    resultCard.hidden = true;
    showError('Paste or type a message first. A message is needed before the models can inspect it.');
    return;
  }

  errorState.hidden = true;
  resultCard.hidden = true;

  checkButton.disabled = true;
  checkButton.innerHTML = `
    <span class="loading-spinner"></span>
    Reading the signal...
  `;

  try {
    const result = await classifyMessage(message, selectedModel);
    renderResult(result);
  } catch (err) {
    showError(err.message);
  } finally {
    checkButton.disabled = false;
    checkButton.innerHTML = `
      <span class="scan-icon">⌕</span>
      Check this message
    `;
  }
});

/* Mobile navigation */

const menuButton = $('#menuButton');
const mobileNav = $('#mobileNav');

menuButton.addEventListener('click', () => {
  const isOpen = mobileNav.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(isOpen));
  menuButton.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
});

mobileNav.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    mobileNav.classList.remove('open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open navigation');
  });
});

/* Scroll reveal animations */

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 },
);

document.querySelectorAll('.reveal').forEach((element) => {
  observer.observe(element);
});