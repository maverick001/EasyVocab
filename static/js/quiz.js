/**
 * BKDict Quiz Application
 * Handles quiz generation, user interaction, and scoring
 */

// Global state
let quizData = {
    words: [],
    questions: [],
    userAnswers: {}
};

// DOM Elements
const quizLoading = document.getElementById('quizLoading');
const quizError = document.getElementById('quizError');
const quizErrorText = document.getElementById('quizErrorText');
const quizQuestions = document.getElementById('quizQuestions');
const quizSubmitContainer = document.getElementById('quizSubmitContainer');
const quizResults = document.getElementById('quizResults');
const submitQuizBtn = document.getElementById('submitQuizBtn');
const retakeQuizBtn = document.getElementById('retakeQuizBtn');

/**
 * Initialize quiz on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    initializeQuiz();

    // Event listeners
    submitQuizBtn.addEventListener('click', submitQuiz);
    retakeQuizBtn.addEventListener('click', retakeQuiz);
});

/**
 * Initialize quiz by fetching random words and generating questions
 */
async function initializeQuiz() {
    try {
        showLoading();

        // Step 1: Fetch random words
        const wordsResponse = await fetch('/api/quiz/random-words?limit=10');
        const wordsData = await wordsResponse.json();

        if (!wordsData.success) {
            showError(wordsData.error);
            return;
        }

        if (wordsData.count === 0) {
            showError('No reviewed words found. Please review some words first by clicking the counter badge.');
            return;
        }

        quizData.words = wordsData.words;

        // Step 2: Generate quiz questions
        const quizResponse = await fetch('/api/quiz/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                words: quizData.words
            })
        });

        const quizResponseData = await quizResponse.json();

        if (!quizResponseData.success) {
            showError(quizResponseData.error);
            return;
        }

        quizData.questions = quizResponseData.questions;

        // Step 3: Display questions
        displayQuestions();

    } catch (error) {
        console.error('Quiz initialization error:', error);
        showError('Failed to load quiz. Please try again.');
    }
}

/**
 * Display quiz questions
 */
function displayQuestions() {
    quizLoading.style.display = 'none';
    quizQuestions.style.display = 'block';
    quizSubmitContainer.style.display = 'block';

    quizQuestions.innerHTML = '';

    quizData.questions.forEach((question, index) => {
        const questionCard = createQuestionCard(question, index);
        quizQuestions.appendChild(questionCard);
    });
}

/**
 * Create a question card element
 */
function createQuestionCard(question, index) {
    const card = document.createElement('div');
    card.className = 'quiz-question-card';
    card.id = `question-${index}`;

    const questionNumber = document.createElement('div');
    questionNumber.className = 'question-number';
    questionNumber.textContent = `Question ${index + 1} of ${quizData.questions.length}`;

    const questionText = document.createElement('h3');
    questionText.className = 'question-text';
    questionText.textContent = `What is the English word for "${question.translation}"?`;

    const optionsContainer = document.createElement('div');
    optionsContainer.className = 'question-options';

    question.options.forEach((option, optionIndex) => {
        const optionLabel = document.createElement('label');
        optionLabel.className = 'option-label';

        const optionInput = document.createElement('input');
        optionInput.type = 'radio';
        optionInput.name = `question-${index}`;
        optionInput.value = optionIndex;
        optionInput.className = 'option-input';

        optionInput.addEventListener('change', (e) => {
            quizData.userAnswers[index] = parseInt(e.target.value);
        });

        const optionText = document.createElement('span');
        optionText.className = 'option-text';
        optionText.textContent = option;

        optionLabel.appendChild(optionInput);
        optionLabel.appendChild(optionText);
        optionsContainer.appendChild(optionLabel);
    });

    card.appendChild(questionNumber);
    card.appendChild(questionText);
    card.appendChild(optionsContainer);

    return card;
}

/**
 * Submit quiz and show results
 */
function submitQuiz() {
    // Check if all questions are answered
    const answeredCount = Object.keys(quizData.userAnswers).length;

    if (answeredCount < quizData.questions.length) {
        const unanswered = quizData.questions.length - answeredCount;
        if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) {
            return;
        }
    }

    // Calculate score
    let correctCount = 0;
    const resultsData = [];

    quizData.questions.forEach((question, index) => {
        const userAnswer = quizData.userAnswers[index];
        const isCorrect = userAnswer === question.correct_answer;

        if (isCorrect) {
            correctCount++;
        }

        resultsData.push({
            questionIndex: index,
            translation: question.translation,
            options: question.options,
            userAnswer: userAnswer,
            correctAnswer: question.correct_answer,
            isCorrect: isCorrect
        });
    });

    // Display results
    displayResults(correctCount, resultsData);
}

/**
 * Display quiz results
 */
function displayResults(correctCount, resultsData) {
    // Hide questions and submit button
    quizQuestions.style.display = 'none';
    quizSubmitContainer.style.display = 'none';

    // Show results
    quizResults.style.display = 'block';

    // Update score
    const scoreValue = document.getElementById('scoreValue');
    scoreValue.textContent = `${correctCount}/${quizData.questions.length}`;

    // Add score class for styling
    const percentage = (correctCount / quizData.questions.length) * 100;
    if (percentage >= 80) {
        scoreValue.className = 'score-value score-excellent';
    } else if (percentage >= 60) {
        scoreValue.className = 'score-value score-good';
    } else {
        scoreValue.className = 'score-value score-needs-improvement';
    }

    // Display breakdown
    const resultsBreakdown = document.getElementById('resultsBreakdown');
    resultsBreakdown.innerHTML = '';

    resultsData.forEach((result) => {
        const resultCard = createResultCard(result);
        resultsBreakdown.appendChild(resultCard);
    });

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Create a result card element
 */
function createResultCard(result) {
    const card = document.createElement('div');
    card.className = `result-card ${result.isCorrect ? 'result-correct' : 'result-incorrect'}`;

    const header = document.createElement('div');
    header.className = 'result-header';

    const icon = document.createElement('span');
    icon.className = 'result-icon';
    icon.textContent = result.isCorrect ? '✅' : '❌';

    const translation = document.createElement('span');
    translation.className = 'result-word';
    translation.textContent = result.translation;

    header.appendChild(icon);
    header.appendChild(translation);

    const body = document.createElement('div');
    body.className = 'result-body';

    if (result.userAnswer !== undefined) {
        const yourAnswer = document.createElement('p');
        yourAnswer.className = 'result-your-answer';
        yourAnswer.innerHTML = `<strong>Your answer:</strong> ${result.options[result.userAnswer]}`;
        body.appendChild(yourAnswer);
    } else {
        const noAnswer = document.createElement('p');
        noAnswer.className = 'result-your-answer';
        noAnswer.innerHTML = `<strong>Your answer:</strong> <em>Not answered</em>`;
        body.appendChild(noAnswer);
    }

    if (!result.isCorrect) {
        const correctAnswer = document.createElement('p');
        correctAnswer.className = 'result-correct-answer';
        correctAnswer.innerHTML = `<strong>Correct answer:</strong> ${result.options[result.correctAnswer]}`;
        body.appendChild(correctAnswer);
    }

    card.appendChild(header);
    card.appendChild(body);

    return card;
}

/**
 * Retake quiz
 */
function retakeQuiz() {
    // Reset state
    quizData = {
        words: [],
        questions: [],
        userAnswers: {}
    };

    // Hide results
    quizResults.style.display = 'none';

    // Reinitialize quiz
    initializeQuiz();
}

/**
 * Show loading state
 */
function showLoading() {
    quizLoading.style.display = 'block';
    quizError.style.display = 'none';
    quizQuestions.style.display = 'none';
    quizSubmitContainer.style.display = 'none';
    quizResults.style.display = 'none';
}

/**
 * Show error state
 */
function showError(message) {
    quizLoading.style.display = 'none';
    quizError.style.display = 'block';
    quizErrorText.textContent = message;
    quizQuestions.style.display = 'none';
    quizSubmitContainer.style.display = 'none';
    quizResults.style.display = 'none';
}
