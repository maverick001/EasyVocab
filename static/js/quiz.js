/**
 * BKDict Quiz Application - Flashcard & Multiple Choice
 */

// Global state
let currentWord = null;
let currentMode = 'flashcard'; // 'flashcard' or 'quiz'
let quizChartInstance = null;

// DOM Elements
const quizLoading = document.getElementById('quizLoading');
const quizError = document.getElementById('quizError');
const quizErrorText = document.getElementById('quizErrorText');
const quizEmpty = document.getElementById('quizEmpty');
const quizCard = document.getElementById('quizCard');
const categorySelect = document.getElementById('categorySelect');
const modeToggle = document.getElementById('modeToggle');
const modeLabel = document.getElementById('modeLabel');

// Card Elements
const wordDisplay = document.getElementById('wordDisplay');
const sentencesDisplay = document.getElementById('sentencesDisplay');
const translationDisplay = document.getElementById('translationDisplay');
const actionButtons = document.getElementById('actionButtons');

// Areas
const flashcardArea = document.getElementById('flashcardArea');
const quizArea = document.getElementById('quizArea');
const choicesContainer = document.getElementById('choicesContainer');
const feedbackArea = document.getElementById('feedbackArea');
const chartContainer = document.getElementById('chartContainer');

// Buttons
const rememberBtn = document.getElementById('rememberBtn');
const notRememberBtn = document.getElementById('notRememberBtn');
const nextBtn = document.getElementById('nextBtn');
const retryBtn = document.getElementById('retryBtn');

/**
 * Initialize quiz on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
    }

    // Theme Toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            const newTheme = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
            localStorage.setItem('theme', newTheme);
            if (quizChartInstance) {
                quizChartInstance.options.scales.x.ticks.color = newTheme === 'dark' ? '#fff' : '#666';
                quizChartInstance.options.scales.y.ticks.color = newTheme === 'dark' ? '#fff' : '#666';
                quizChartInstance.update();
            }
        });
    }

    // Mode Toggle
    modeToggle.addEventListener('change', (e) => {
        currentMode = e.target.checked ? 'quiz' : 'flashcard';
        modeLabel.textContent = currentMode === 'quiz' ? 'Multiple Choice Mode' : 'Flashcard Mode';
        
        // Setup UI for mode
        if (currentMode === 'quiz') {
            flashcardArea.style.display = 'none';
            quizArea.style.display = 'block';
            chartContainer.style.display = 'block';
            loadQuizStats();
        } else {
            flashcardArea.style.display = 'block';
            quizArea.style.display = 'none';
            chartContainer.style.display = 'none';
        }

        // Reload word for new mode
        loadNextWord();
    });

    await loadCategories();
    loadNextWord();

    // Event listeners
    rememberBtn.addEventListener('click', () => handleResult('remember'));
    notRememberBtn.addEventListener('click', () => handleResult('not_remember'));
    nextBtn.addEventListener('click', loadNextWord);
    retryBtn.addEventListener('click', loadNextWord);

    // Category change listener
    categorySelect.addEventListener('change', () => {
        loadNextWord();
    });
});

/**
 * Load categories for dropdown
 */
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();

        if (data.success && data.categories) {
            while (categorySelect.options.length > 1) {
                categorySelect.remove(1);
            }

            data.categories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.name;
                option.textContent = `${cat.name} (${cat.word_count})`;
                categorySelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

/**
 * Load the next word for review
 */
async function loadNextWord() {
    try {
        showLoading();
        resetCard();

        const category = categorySelect.value;
        const response = await fetch(`/api/quiz/next-word?category=${encodeURIComponent(category)}&mode=${currentMode}`);
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

    // sentences
    if (word.example_sentence) {
        sentencesDisplay.innerHTML = word.example_sentence.split('\n').map(s => `<p>${s}</p>`).join('');
    } else {
        sentencesDisplay.innerHTML = '<p><em>No example sentence available.</em></p>';
    }

    if (currentMode === 'flashcard') {
        translationDisplay.textContent = word.translation;
    } else {
        // Quiz Mode: Render Choices
        renderChoices(word.options);
    }
}

/**
 * Render Multiple Choice Options
 */
function renderChoices(options) {
    choicesContainer.innerHTML = '';
    
    if (!options || options.length === 0) {
        choicesContainer.innerHTML = '<p>Error: No options available.</p>';
        return;
    }

    options.forEach(optionText => {
        const btn = document.createElement('button');
        btn.className = 'quiz-choice-btn';
        btn.textContent = optionText;
        btn.onclick = () => handleChoiceSelection(btn, optionText);
        choicesContainer.appendChild(btn);
    });
}

/**
 * Handle Choice Selection (Quiz Mode)
 */
function handleChoiceSelection(btn, selectedText) {
    // Disable all buttons
    const allBtns = choicesContainer.querySelectorAll('button');
    allBtns.forEach(b => b.disabled = true);

    const isCorrect = selectedText === currentWord.translation;

    if (isCorrect) {
        btn.classList.add('correct');
        feedbackArea.textContent = "Correct! +1 Mark";
        feedbackArea.style.color = "#10b981";
        // Submit 'correct' result
        submitResult('correct');
    } else {
        btn.classList.add('incorrect');
        feedbackArea.textContent = `Incorrect. The correct answer is: ${currentWord.translation}`;
        feedbackArea.style.color = "#ef4444";
        
        // Highlight correct one
        allBtns.forEach(b => {
             if (b.textContent === currentWord.translation) {
                 b.classList.add('correct');
             }
        });
        
        // Submit 'incorrect' result (no score)
        submitResult('incorrect');
    }

    feedbackArea.style.display = 'block';
    nextBtn.style.display = 'block';
    nextBtn.focus();
}

/**
 * Handle user result (Flashcard Mode)
 */
async function handleResult(result) {
    if (!currentWord) return;
    try {
        // Optimistic UI update: Show translation
        translationDisplay.style.display = 'block';
        actionButtons.style.display = 'none';
        nextBtn.style.display = 'block';
        nextBtn.focus(); 

        await submitResult(result);

    } catch (error) {
        console.error('Error saving result:', error);
    }
}

/**
 * Submit result to API
 */
async function submitResult(result) {
    try {
        const response = await fetch('/api/quiz/result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                word_id: currentWord.id,
                result: result,
                mode: currentMode
            })
        });
        
        const data = await response.json();
        if (!data.success) {
            console.error('Failed to save result:', data.error);
        } else if (currentMode === 'quiz' && result === 'correct') {
            // Update chart if we got a point
            loadQuizStats();
        }
    } catch (error) {
        console.error('Error submitting result:', error);
    }
}

/**
 * Reset card state for next word
 */
function resetCard() {
    translationDisplay.style.display = 'none';
    actionButtons.style.display = 'flex';
    nextBtn.style.display = 'none';
    feedbackArea.style.display = 'none';
    wordDisplay.textContent = '';
    sentencesDisplay.innerHTML = '';
    translationDisplay.textContent = '';
    choicesContainer.innerHTML = '';
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

/**
 * Load and Render Chart
 */
async function loadQuizStats() {
    try {
        const response = await fetch('/api/quiz/stats');
        const data = await response.json();
        
        if (data.success && data.stats) {
            renderChart(data.stats);
        }
    } catch (error) {
        console.error("Error loading stats", error);
    }
}

function renderChart(stats) {
    const ctx = document.getElementById('quizChart').getContext('2d');
    
    // Destroy previous instance if exists
    if (quizChartInstance) {
        quizChartInstance.destroy();
    }
    
    const labels = stats.map(s => s.date);
    const values = stats.map(s => s.score);

    // Detect theme
    const isDark = document.body.classList.contains('dark-mode');
    const textColor = isDark ? '#fff' : '#666';

    quizChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Daily Marks',
                data: values,
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: textColor },
                    grid: { color: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }
                },
                x: {
                    ticks: { color: textColor },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { labels: { color: textColor } }
            }
        }
    });
}
