'use strict';
// Fictional educational examples. Never used as classifier rules or training data.
const quizQuestions = [
  { message: 'Aap lucky draw jeet gaye! Inaam lene ke liye pehle 2500 rupay processing fee bhejein.', answer: 'Scam', explanation: 'An unexpected prize that requires an upfront payment is a warning sign. Verify the promotion independently before sending money.' },
  { message: 'Salam Sara, library mein group study kal 4 baje rakh lein? Apni notes wali copy le aana.', answer: 'Authentic', explanation: 'This example is an ordinary study plan with no payment or private information request. In real life, still check that you recognize the sender.' },
  { message: 'Main wallet support se hoon. Aap ka account bachane ke liye SMS wala OTP mujhe abhi bata dein.', answer: 'Scam', explanation: 'An OTP can unlock an account or authorize a transaction. Do not share it with someone claiming to be support; contact the service yourself.' },
  { message: 'Aap ka interview select ho gaya. Job pakki karne ke liye aaj hi personal wallet mein registration fee bhejein.', answer: 'Scam', explanation: 'A guaranteed job combined with an urgent fee to a personal wallet deserves suspicion. Verify the employer through official contact details.' },
  { message: 'Ayesha, tumhari kitab mere paas hai. Agli class mein wapas le aaoon ga, yaad dila dena.', answer: 'Authentic', explanation: 'This example is a simple note about returning a book. It asks for no money, credentials, or link visit. Familiar wording alone never proves a sender is genuine.' }
];
(() => {
  const find = (selector) => document.querySelector(selector);
  let index = 0;
  let score = 0;
  let answered = false;
  const choices = [...document.querySelectorAll('[data-answer]')];
  function showQuestion() {
    answered = false;
    find('#quizContent').hidden = false;
    find('#quizComplete').hidden = true;
    find('#quizProgress').textContent = `QUESTION ${index + 1} OF ${quizQuestions.length}`;
    find('#quizScore').textContent = `Score: ${score}`;
    find('#quizBar').value = index;
    find('#quizMessage').textContent = `“${quizQuestions[index].message}”`;
    find('#quizFeedback').hidden = true;
    find('#quizNext').hidden = true;
    choices.forEach((choice) => { choice.disabled = false; choice.classList.remove('selected'); choice.removeAttribute('aria-pressed'); });
  }
  choices.forEach((choice) => choice.addEventListener('click', () => {
    if (answered) return;
    answered = true;
    const question = quizQuestions[index];
    const correct = choice.dataset.answer === question.answer;
    if (correct) score++;
    choices.forEach((item) => { item.disabled = true; item.setAttribute('aria-pressed', String(item === choice)); });
    choice.classList.add('selected');
    find('#quizScore').textContent = `Score: ${score}`;
    find('#quizBar').value = index + 1;
    find('#quizFeedback').textContent = `${correct ? 'Correct.' : `This example is ${question.answer.toLowerCase()}.`} ${question.explanation}`;
    find('#quizFeedback').hidden = false;
    find('#quizNext').textContent = index === quizQuestions.length - 1 ? 'See my score →' : 'Next question →';
    find('#quizNext').hidden = false;
    find('#quizNext').focus({ preventScroll: true });
  }));
  find('#quizNext').addEventListener('click', () => {
    if (!answered) return;
    index++;
    if (index < quizQuestions.length) { showQuestion(); choices[0].focus({ preventScroll: true }); return; }
    find('#quizContent').hidden = true;
    find('#quizComplete').hidden = false;
    find('#quizProgress').textContent = 'CHALLENGE COMPLETE';
    find('#quizFinalScore').textContent = `Your Scam IQ: ${score}/${quizQuestions.length}`;
    find('#quizSummary').textContent = score >= 4
      ? 'Good spotting! Keep the habit: pause, verify the sender, and keep your private codes to yourself.'
      : 'Every second look helps. Explore the Scam Guide, then try again to put what you learned into practice.';
    find('#quizComplete').focus({ preventScroll: true });
  });
  find('#quizRestart').addEventListener('click', () => { index = 0; score = 0; showQuestion(); choices[0].focus({ preventScroll: true }); });
  showQuestion();
})();
