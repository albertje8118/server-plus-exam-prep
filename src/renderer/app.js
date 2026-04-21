const EXAM_SETTINGS = {
  questionCount: 90,
  durationMinutes: 90,
};

const state = {
  allQuestions: [],
  mode: 'practice',
  currentIndex: 0,
  visibleExplanations: new Set(),
  practice: {
    selections: new Map(),
    results: new Map(),
  },
  exam: {
    questions: [],
    answers: new Map(),
    flagged: new Set(),
    status: 'idle',
    remainingSeconds: EXAM_SETTINGS.durationMinutes * 60,
    timerId: null,
  },
};

const elements = {
  modePractice: document.getElementById('mode-practice'),
  modeExam: document.getElementById('mode-exam'),
  modeDescription: document.getElementById('mode-description'),
  summaryStrip: document.getElementById('summary-strip'),
  resetProgress: document.getElementById('reset-progress'),
  startExam: document.getElementById('start-exam'),
  newExam: document.getElementById('new-exam'),
  submitExam: document.getElementById('submit-exam'),
  sessionLabel: document.getElementById('session-label'),
  questionTitle: document.getElementById('question-title'),
  questionPosition: document.getElementById('question-position'),
  selectionMode: document.getElementById('selection-mode'),
  examClock: document.getElementById('exam-clock'),
  examIntro: document.getElementById('exam-intro'),
  questionText: document.getElementById('question-text'),
  questionMedia: document.getElementById('question-media'),
  optionsList: document.getElementById('options-list'),
  prevButton: document.getElementById('prev-button'),
  nextButton: document.getElementById('next-button'),
  clearSelection: document.getElementById('clear-selection'),
  flagQuestion: document.getElementById('flag-question'),
  checkButton: document.getElementById('check-button'),
  toggleExplanation: document.getElementById('toggle-explanation'),
  explanationPanel: document.getElementById('explanation-panel'),
  explanationText: document.getElementById('explanation-text'),
  explanationMedia: document.getElementById('explanation-media'),
  feedbackBanner: document.getElementById('feedback-banner'),
  navigatorTitle: document.getElementById('navigator-title'),
  navigatorCaption: document.getElementById('navigator-caption'),
  questionGrid: document.getElementById('question-grid'),
};

function isMultiSelect(question) {
  return question.answer.length > 1;
}

function getVisibleQuestions() {
  return state.mode === 'practice' ? state.allQuestions : state.exam.questions;
}

function getCurrentQuestion() {
  return getVisibleQuestions()[state.currentIndex];
}

function normalizeAnswerSet(answer) {
  return new Set(answer.split(''));
}

function isCorrectSelection(question, selectedLabels) {
  const expected = normalizeAnswerSet(question.answer);
  if (expected.size !== selectedLabels.size) {
    return false;
  }

  return [...selectedLabels].every((label) => expected.has(label));
}

function shuffleQuestions(questions) {
  const copy = [...questions];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
  }
  return copy;
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
}

function getPracticeSelection(questionId) {
  return new Set(state.practice.selections.get(questionId) || []);
}

function setPracticeSelection(questionId, labels) {
  state.practice.selections.set(questionId, [...labels].sort());
}

function getExamSelection(questionId) {
  return new Set(state.exam.answers.get(questionId) || []);
}

function setExamSelection(questionId, labels) {
  state.exam.answers.set(questionId, [...labels].sort());
}

function getSelection(questionId) {
  return state.mode === 'practice' ? getPracticeSelection(questionId) : getExamSelection(questionId);
}

function setSelection(questionId, labels) {
  if (state.mode === 'practice') {
    setPracticeSelection(questionId, labels);
    return;
  }

  setExamSelection(questionId, labels);
}

function getPracticeResult(questionId) {
  return state.practice.results.get(questionId) || null;
}

function isExamReview() {
  return state.mode === 'exam' && (state.exam.status === 'submitted' || state.exam.status === 'expired');
}

function getExamReviewResult(question) {
  if (!isExamReview()) {
    return null;
  }

  const selectedLabels = [...getExamSelection(question.id)].sort();
  return {
    selectedLabels,
    isCorrect: isCorrectSelection(question, new Set(selectedLabels)),
  };
}

function setFeedback(message, type = 'info') {
  elements.feedbackBanner.hidden = false;
  elements.feedbackBanner.textContent = message;
  elements.feedbackBanner.dataset.type = type;
}

function clearFeedback() {
  elements.feedbackBanner.hidden = true;
  elements.feedbackBanner.textContent = '';
  delete elements.feedbackBanner.dataset.type;
}

function renderSummaryCards(items) {
  elements.summaryStrip.innerHTML = '';

  items.forEach((item) => {
    const card = document.createElement('div');
    card.className = 'summary-card';

    const label = document.createElement('span');
    label.className = 'summary-label';
    label.textContent = item.label;

    const value = document.createElement('strong');
    value.className = 'summary-value';
    value.textContent = item.value;

    card.append(label, value);
    elements.summaryStrip.appendChild(card);
  });
}

function updateSummary() {
  if (state.mode === 'practice') {
    const total = state.allQuestions.length;
    const answered = state.practice.results.size;
    const correct = [...state.practice.results.values()].filter((item) => item.isCorrect).length;
    const accuracy = answered ? Math.round((correct / answered) * 100) : 0;

    renderSummaryCards([
      { label: 'Question Bank', value: String(total) },
      { label: 'Answered', value: String(answered) },
      { label: 'Correct', value: String(correct) },
      { label: 'Accuracy', value: `${accuracy}%` },
    ]);
    return;
  }

  const examQuestions = state.exam.questions.length;
  const answered = state.exam.answers.size;
  const flagged = state.exam.flagged.size;

  if (isExamReview()) {
    const correct = state.exam.questions.filter((question) => {
      const result = getExamReviewResult(question);
      return result?.isCorrect;
    }).length;
    const score = examQuestions ? Math.round((correct / examQuestions) * 100) : 0;

    renderSummaryCards([
      { label: 'Exam Questions', value: String(examQuestions) },
      { label: 'Correct', value: String(correct) },
      { label: 'Score', value: `${score}%` },
      { label: 'Flagged', value: String(flagged) },
    ]);
    return;
  }

  renderSummaryCards([
    { label: 'Exam Questions', value: String(examQuestions || EXAM_SETTINGS.questionCount) },
    { label: 'Answered', value: String(answered) },
    { label: 'Flagged', value: String(flagged) },
    { label: 'Time Left', value: formatTime(state.exam.remainingSeconds) },
  ]);
}

function renderImages(container, images, altPrefix) {
  container.innerHTML = '';
  container.hidden = !images.length;

  images.forEach((imageSource, index) => {
    const img = document.createElement('img');
    img.className = 'rendered-image';
    img.src = imageSource;
    img.alt = `${altPrefix} ${index + 1}`;
    img.loading = 'lazy';
    container.appendChild(img);
  });
}

function renderNavigator() {
  const questions = getVisibleQuestions();
  elements.questionGrid.innerHTML = '';

  if (!questions.length) {
    elements.navigatorCaption.textContent = state.mode === 'exam'
      ? 'Start a simulator session to generate a random 90-question exam.'
      : 'Loading questions.';
    return;
  }

  elements.navigatorCaption.textContent = state.mode === 'practice'
    ? 'Jump across the full bank. Reviewed questions stay color-coded.'
    : isExamReview()
      ? 'Review your submitted exam. Green is correct, red is wrong, gold is flagged.'
      : 'Track answered and flagged questions while the exam timer is running.';

  questions.forEach((question, index) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'nav-chip';
    chip.textContent = String(index + 1);

    if (index === state.currentIndex) {
      chip.classList.add('current');
    }

    if (state.mode === 'practice') {
      const result = getPracticeResult(question.id);
      if (result) {
        chip.classList.add(result.isCorrect ? 'correct' : 'wrong');
      }
    } else {
      if (state.exam.answers.has(question.id)) {
        chip.classList.add('answered');
      }
      if (state.exam.flagged.has(question.id)) {
        chip.classList.add('flagged');
      }
      if (isExamReview()) {
        const result = getExamReviewResult(question);
        if (result) {
          chip.classList.remove('answered');
          chip.classList.add(result.isCorrect ? 'correct' : 'wrong');
        }
      }
    }

    chip.addEventListener('click', () => {
      state.currentIndex = index;
      renderQuestion();
    });
    elements.questionGrid.appendChild(chip);
  });
}

function updateModeButtons() {
  elements.modePractice.classList.toggle('active', state.mode === 'practice');
  elements.modeExam.classList.toggle('active', state.mode === 'exam');
  elements.modePractice.disabled = state.exam.status === 'running';
}

function renderTopControls() {
  updateModeButtons();
  updateSummary();

  const examRunning = state.exam.status === 'running';
  const examReady = state.exam.questions.length > 0;

  elements.modeDescription.textContent = state.mode === 'practice'
    ? 'Practice mode shows the full extracted bank with instant scoring, explanations, and image-backed questions.'
    : 'Exam simulator uses CompTIA Server+ SK0-005 official timing: maximum 90 questions in 90 minutes.';

  elements.resetProgress.hidden = state.mode !== 'practice';
  elements.startExam.hidden = state.mode !== 'exam' || examRunning;
  elements.newExam.hidden = state.mode !== 'exam' || !examReady || examRunning;
  elements.submitExam.hidden = state.mode !== 'exam' || !examRunning;
  elements.examClock.hidden = state.mode !== 'exam';
  elements.examClock.textContent = formatTime(state.exam.remainingSeconds);
  elements.navigatorTitle.textContent = state.mode === 'practice' ? 'Browse All Questions' : 'Exam Navigator';
}

function renderOptions(question) {
  const selectedOptions = getSelection(question.id);
  const practiceResult = getPracticeResult(question.id);
  const reviewResult = getExamReviewResult(question);
  const correctLabels = normalizeAnswerSet(question.answer);
  const isLocked = Boolean(practiceResult) || isExamReview();

  elements.optionsList.innerHTML = '';

  question.options.forEach((option) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'option-button';
    button.dataset.label = option.label;

    if (selectedOptions.has(option.label)) {
      button.classList.add('selected');
    }

    if (practiceResult || reviewResult) {
      const selectedForCheck = new Set((practiceResult || reviewResult).selectedLabels);
      if (correctLabels.has(option.label)) {
        button.classList.add('correct');
      } else if (selectedForCheck.has(option.label)) {
        button.classList.add('wrong');
      }
    }

    button.disabled = isLocked;

    const label = document.createElement('span');
    label.className = 'option-label';
    label.textContent = option.label;

    const content = document.createElement('span');
    content.className = 'option-content';

    const text = document.createElement('span');
    text.className = 'option-text';
    text.textContent = option.text || `Option ${option.label}`;
    content.appendChild(text);

    if (option.images?.length) {
      const media = document.createElement('div');
      media.className = 'option-media';
      option.images.forEach((imageSource, index) => {
        const img = document.createElement('img');
        img.className = 'rendered-image';
        img.src = imageSource;
        img.alt = `Option ${option.label} image ${index + 1}`;
        img.loading = 'lazy';
        media.appendChild(img);
      });
      content.appendChild(media);
    }

    button.append(label, content);
    button.addEventListener('click', () => handleOptionClick(question, option.label));
    elements.optionsList.appendChild(button);
  });
}

function renderExplanation(question) {
  const explanationVisible = state.visibleExplanations.has(question.id);
  const canShowExplanation = state.mode === 'practice'
    ? Boolean(getPracticeResult(question.id))
    : isExamReview();

  elements.toggleExplanation.disabled = !canShowExplanation;
  elements.explanationText.textContent = question.explanation;
  renderImages(elements.explanationMedia, question.explanationImages || [], 'Explanation image');

  if (!canShowExplanation) {
    elements.explanationPanel.hidden = true;
    elements.toggleExplanation.textContent = 'See Explanation';
    return;
  }

  elements.explanationPanel.hidden = !explanationVisible;
  elements.toggleExplanation.textContent = explanationVisible ? 'Hide Explanation' : 'See Explanation';
}

function renderQuestion() {
  renderTopControls();

  const questions = getVisibleQuestions();
  const question = getCurrentQuestion();
  elements.examIntro.hidden = !(state.mode === 'exam' && state.exam.status === 'idle' && !questions.length);

  if (!question) {
    elements.sessionLabel.textContent = state.mode === 'practice' ? 'Practice Bank' : 'Exam Simulator';
    elements.questionTitle.textContent = state.mode === 'practice' ? 'Loading question bank...' : 'Ready to start a timed exam';
    elements.questionPosition.textContent = 'Question 0 / 0';
    elements.selectionMode.textContent = 'Official target: 90 questions / 90 minutes';
    elements.questionText.textContent = state.mode === 'practice'
      ? 'The extracted questions are still loading.'
      : 'Start the simulator to pull a random 90-question exam from your local database.';
    renderImages(elements.questionMedia, [], 'Question image');
    elements.optionsList.innerHTML = '';
    elements.prevButton.disabled = true;
    elements.nextButton.disabled = true;
    elements.clearSelection.disabled = true;
    elements.flagQuestion.hidden = true;
    elements.checkButton.hidden = true;
    elements.toggleExplanation.disabled = true;
    elements.explanationPanel.hidden = true;
    clearFeedback();
    renderNavigator();
    return;
  }

  const selectedOptions = getSelection(question.id);
  const practiceResult = getPracticeResult(question.id);
  const reviewResult = getExamReviewResult(question);
  const isExamRunning = state.mode === 'exam' && state.exam.status === 'running';
  const isPractice = state.mode === 'practice';

  elements.sessionLabel.textContent = isPractice
    ? 'Practice Bank'
    : isExamRunning
      ? 'Timed Exam Session'
      : 'Exam Review';
  elements.questionTitle.textContent = `Question ${question.questionID}`;
  elements.questionPosition.textContent = `Question ${state.currentIndex + 1} / ${questions.length}`;
  elements.selectionMode.textContent = isMultiSelect(question) ? 'Multiple answer' : 'Single answer';
  elements.questionText.textContent = question.question;
  renderImages(elements.questionMedia, question.questionImages || [], 'Question image');

  elements.prevButton.disabled = state.currentIndex === 0;
  elements.nextButton.disabled = state.currentIndex === questions.length - 1;
  elements.clearSelection.disabled = !selectedOptions.size || Boolean(practiceResult) || isExamReview();
  elements.flagQuestion.hidden = state.mode !== 'exam' || !isExamRunning;
  elements.flagQuestion.textContent = state.exam.flagged.has(question.id) ? 'Unflag' : 'Flag for Review';
  elements.checkButton.hidden = !(isPractice && isMultiSelect(question));
  elements.checkButton.disabled = Boolean(practiceResult) || selectedOptions.size === 0;

  if (isPractice && practiceResult) {
    setFeedback(
      practiceResult.isCorrect ? 'Correct answer.' : `Wrong answer. Correct answer: ${question.answer}`,
      practiceResult.isCorrect ? 'success' : 'error'
    );
  } else if (isExamRunning) {
    setFeedback(
      state.exam.flagged.has(question.id)
        ? 'Flagged for review. Finish the full exam before revealing answers.'
        : 'Simulator mode hides correctness until you submit or the timer expires.',
      'info'
    );
  } else if (reviewResult) {
    const correct = state.exam.questions.filter((item) => getExamReviewResult(item)?.isCorrect).length;
    setFeedback(
      reviewResult.isCorrect
        ? `Correct. Review score: ${correct} / ${state.exam.questions.length}.`
        : `Incorrect. Correct answer: ${question.answer}. Review score: ${correct} / ${state.exam.questions.length}.`,
      reviewResult.isCorrect ? 'success' : 'error'
    );
  } else {
    clearFeedback();
  }

  renderOptions(question);
  renderExplanation(question);
  renderNavigator();
}

function checkPracticeQuestion() {
  const question = getCurrentQuestion();
  if (!question) {
    return;
  }

  const selectedLabels = [...getPracticeSelection(question.id)].sort();
  if (!selectedLabels.length) {
    return;
  }

  state.practice.results.set(question.id, {
    selectedLabels,
    isCorrect: isCorrectSelection(question, new Set(selectedLabels)),
  });
  renderQuestion();
}

function handleOptionClick(question, label) {
  if (state.mode === 'practice' && getPracticeResult(question.id)) {
    return;
  }

  if (isExamReview()) {
    return;
  }

  const selectedOptions = getSelection(question.id);
  if (isMultiSelect(question)) {
    if (selectedOptions.has(label)) {
      selectedOptions.delete(label);
    } else {
      selectedOptions.add(label);
    }
    setSelection(question.id, selectedOptions);
    renderQuestion();
    return;
  }

  const nextSelection = new Set([label]);
  setSelection(question.id, nextSelection);
  if (state.mode === 'practice') {
    checkPracticeQuestion();
    return;
  }

  renderQuestion();
}

function moveQuestion(offset) {
  const nextIndex = state.currentIndex + offset;
  const questions = getVisibleQuestions();
  if (nextIndex < 0 || nextIndex >= questions.length) {
    return;
  }

  state.currentIndex = nextIndex;
  renderQuestion();
}

function clearSelection() {
  const question = getCurrentQuestion();
  if (!question) {
    return;
  }

  if (state.mode === 'practice' && getPracticeResult(question.id)) {
    return;
  }

  if (isExamReview()) {
    return;
  }

  if (state.mode === 'practice') {
    state.practice.selections.delete(question.id);
  } else {
    state.exam.answers.delete(question.id);
  }

  renderQuestion();
}

function resetProgress() {
  state.practice.results.clear();
  state.practice.selections.clear();
  state.visibleExplanations.clear();
  state.currentIndex = 0;
  renderQuestion();
}

function stopExamTimer() {
  if (state.exam.timerId) {
    window.clearInterval(state.exam.timerId);
    state.exam.timerId = null;
  }
}

function finishExam(status) {
  stopExamTimer();
  state.exam.status = status;
  state.visibleExplanations.clear();
  renderQuestion();
}

function startExamTimer() {
  stopExamTimer();
  state.exam.timerId = window.setInterval(() => {
    state.exam.remainingSeconds -= 1;
    if (state.exam.remainingSeconds <= 0) {
      state.exam.remainingSeconds = 0;
      finishExam('expired');
      return;
    }
    renderTopControls();
  }, 1000);
}

function startExamSession() {
  const sampleSize = Math.min(EXAM_SETTINGS.questionCount, state.allQuestions.length);
  state.mode = 'exam';
  state.currentIndex = 0;
  state.visibleExplanations.clear();
  state.exam.questions = shuffleQuestions(state.allQuestions).slice(0, sampleSize);
  state.exam.answers.clear();
  state.exam.flagged.clear();
  state.exam.remainingSeconds = EXAM_SETTINGS.durationMinutes * 60;
  state.exam.status = 'running';
  startExamTimer();
  renderQuestion();
}

function switchMode(mode) {
  if (mode === state.mode) {
    return;
  }

  if (mode === 'practice' && state.exam.status === 'running') {
    return;
  }

  state.mode = mode;
  state.currentIndex = 0;
  state.visibleExplanations.clear();
  renderQuestion();
}

function toggleFlag() {
  const question = getCurrentQuestion();
  if (!question || state.mode !== 'exam' || state.exam.status !== 'running') {
    return;
  }

  if (state.exam.flagged.has(question.id)) {
    state.exam.flagged.delete(question.id);
  } else {
    state.exam.flagged.add(question.id);
  }
  renderQuestion();
}

function toggleExplanation() {
  const question = getCurrentQuestion();
  if (!question) {
    return;
  }

  if (state.visibleExplanations.has(question.id)) {
    state.visibleExplanations.delete(question.id);
  } else {
    state.visibleExplanations.add(question.id);
  }
  renderQuestion();
}

elements.modePractice.addEventListener('click', () => switchMode('practice'));
elements.modeExam.addEventListener('click', () => switchMode('exam'));
elements.prevButton.addEventListener('click', () => moveQuestion(-1));
elements.nextButton.addEventListener('click', () => moveQuestion(1));
elements.clearSelection.addEventListener('click', () => clearSelection());
elements.flagQuestion.addEventListener('click', () => toggleFlag());
elements.checkButton.addEventListener('click', () => checkPracticeQuestion());
elements.resetProgress.addEventListener('click', () => resetProgress());
elements.startExam.addEventListener('click', () => startExamSession());
elements.newExam.addEventListener('click', () => startExamSession());
elements.submitExam.addEventListener('click', () => finishExam('submitted'));
elements.toggleExplanation.addEventListener('click', () => toggleExplanation());

window.addEventListener('beforeunload', () => stopExamTimer());

async function initialize() {
  try {
    state.allQuestions = await window.examApi.listQuestions();
    renderQuestion();
  } catch (error) {
    elements.questionTitle.textContent = 'Failed to load questions';
    elements.questionText.textContent = error.message;
  }
}

initialize();