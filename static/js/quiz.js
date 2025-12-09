/**
 * BKDict Quiz Application - Flashcard Style
 */

// Global state
let currentWord = null;

// DOM Elements
const quizLoading = document.getElementById('quizLoading');
const quizError = document.getElementById('quizError');
const quizErrorText = document.getElementById('quizErrorText');
const quizEmpty = document.getElementById('quizEmpty');
const quizCard = document.getElementById('quizCard');

const wordDisplay = document.getElementById('wordDisplay');
const sentencesDisplay = document.getElementById('sentencesDisplay');
const translationDisplay = document.getElementById('translationDisplay');
const actionButtons = document.getElementById('actionButtons');

const rememberBtn = document.getElementById('rememberBtn');
const notRememberBtn = document.getElementById('notRememberBtn');
const nextBtn = document.getElementById('nextBtn');
const retryBtn = document.getElementById('retryBtn');

/**
 * Initialize quiz on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    loadNextWord();

    // Event listeners
    rememberBtn.addEventListener('click', () => handleResult('remember'));
    notRememberBtn.addEventListener('click', () => handleResult('not_remember'));
    nextBtn.addEventListener('click', loadNextWord);
    retryBtn.addEventListener('click', loadNextWord);
});

/**
 * Load the next word for review
 */
async function loadNextWord() {
    try {
        showLoading();
        resetCard();

        const response = await fetch('/api/quiz/next-word');
        const data = await response.json();

        if (response.status === 404) {
            showEmpty();
            return;
        }

        if (!data.success) {
            showError(data.error || 'Failed to load word');
            return;
        }

        currentWord = data.word;
        displayWord(currentWord);

    } catch (error) {
        console.error('Error loading word:', error);
        showError('Network error. Please try again.');
    }
}

/**
 * Display the word on the card
 */
function displayWord(word) {
    quizLoading.style.display = 'none';
    quizError.style.display = 'none';
    quizEmpty.style.display = 'none';
    quizCard.style.display = 'flex';

    wordDisplay.textContent = word.word;

    // Format sample sentences (handle newlines)
    if (word.example_sentence) {
        sentencesDisplay.innerHTML = word.example_sentence.split('\n').map(s => `<p>${s}</p>`).join('');
    } else {
        sentencesDisplay.innerHTML = '<p><em>No example sentence available.</em></p>';
    }

    translationDisplay.textContent = word.translation;
}

/**
 * Handle user result (Remember / Not Remember)
 */
async function handleResult(result) {
    if (!currentWord) return;

    try {
        // Optimistic UI update: Show translation immediately
        showTranslation();

        const response = await fetch('/api/quiz/result', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word_id: currentWord.id,
                result: result
            })
        });

        const data = await response.json();

        if (!data.success) {
            console.error('Failed to save result:', data.error);
            // Optionally show a toast or small error, but don't block the flow
        }

    } catch (error) {
        console.error('Error saving result:', error);
    }
}

/**
 * Show translation and Next button, hide action buttons
 */
function showTranslation() {
    translationDisplay.style.display = 'block';
    actionButtons.style.display = 'none';
    nextBtn.style.display = 'block';
    nextBtn.focus(); // Focus next button for easy keyboard navigation
}

/**
 * Reset card state for next word
 */
function resetCard() {
    translationDisplay.style.display = 'none';
    actionButtons.style.display = 'flex';
    nextBtn.style.display = 'none';
    wordDisplay.textContent = '';
    sentencesDisplay.innerHTML = '';
    translationDisplay.textContent = '';
}

/**
 * Show loading state
 */
function showLoading() {
    quizLoading.style.display = 'block';
    quizError.style.display = 'none';
    quizEmpty.style.display = 'none';
    quizCard.style.display = 'none';
}

/**
 * Show error state
 */
function showError(message) {
    quizLoading.style.display = 'none';
    quizError.style.display = 'block';
    quizEmpty.style.display = 'none';
    quizCard.style.display = 'none';
    quizErrorText.textContent = message;
}

/**
 * Show empty state (no more words)
 */
function showEmpty() {
    quizLoading.style.display = 'none';
    quizError.style.display = 'none';
    quizEmpty.style.display = 'block';
    quizCard.style.display = 'none';
}
