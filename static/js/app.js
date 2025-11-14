/**
 * BKDict Vocabulary App - Frontend JavaScript
 * Handles all client-side interactions, API calls, and UI updates
 */

// ============================================
// Global State Management
// ============================================
const AppState = {
    currentCategory: null,
    currentIndex: 0,
    currentWord: null,
    totalInCategory: 0,
    isEditingTranslation: false,
    isEditingSample: false
};

// ============================================
// DOM Elements (cached for performance)
// ============================================
const Elements = {
    // Category selection
    categorySelect: null,
    categoryInfo: null,

    // Word card
    wordCard: null,
    wordDisplay: null,
    positionInfo: null,

    // Translation elements
    translationDisplay: null,
    translationEdit: null,
    translationInput: null,
    editTransBtn: null,
    saveTransBtn: null,
    cancelTransBtn: null,

    // Sample sentence elements
    sampleDisplay: null,
    sampleEdit: null,
    sampleInput: null,
    editSampleBtn: null,
    saveSampleBtn: null,
    cancelSampleBtn: null,

    // Navigation
    prevBtn: null,
    nextBtn: null,

    // Import section
    importBtn: null,
    importPanel: null,
    fileInput: null,
    uploadBtn: null,
    cancelUploadBtn: null,
    uploadStatus: null,

    // Messages
    welcomeMessage: null,
    loadingIndicator: null,
    errorMessage: null,
    errorText: null
};

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 BKDict Application Initializing...');

    // Cache DOM elements
    cacheDOMElements();

    // Setup event listeners
    setupEventListeners();

    // Load categories
    loadCategories();

    console.log('✅ Initialization complete');
});

/**
 * Cache all DOM elements for efficient access
 */
function cacheDOMElements() {
    // Category
    Elements.categorySelect = document.getElementById('categorySelect');
    Elements.categoryInfo = document.getElementById('categoryInfo');

    // Word card
    Elements.wordCard = document.getElementById('wordCard');
    Elements.wordDisplay = document.getElementById('wordDisplay');
    Elements.positionInfo = document.getElementById('positionInfo');

    // Translation
    Elements.translationDisplay = document.getElementById('translationDisplay');
    Elements.translationEdit = document.getElementById('translationEdit');
    Elements.translationInput = document.getElementById('translationInput');
    Elements.editTransBtn = document.getElementById('editTransBtn');
    Elements.saveTransBtn = document.getElementById('saveTransBtn');
    Elements.cancelTransBtn = document.getElementById('cancelTransBtn');

    // Sample
    Elements.sampleDisplay = document.getElementById('sampleDisplay');
    Elements.sampleEdit = document.getElementById('sampleEdit');
    Elements.sampleInput = document.getElementById('sampleInput');
    Elements.editSampleBtn = document.getElementById('editSampleBtn');
    Elements.saveSampleBtn = document.getElementById('saveSampleBtn');
    Elements.cancelSampleBtn = document.getElementById('cancelSampleBtn');

    // Navigation
    Elements.prevBtn = document.getElementById('prevBtn');
    Elements.nextBtn = document.getElementById('nextBtn');

    // Import
    Elements.importBtn = document.getElementById('importBtn');
    Elements.importPanel = document.getElementById('importPanel');
    Elements.fileInput = document.getElementById('fileInput');
    Elements.uploadBtn = document.getElementById('uploadBtn');
    Elements.cancelUploadBtn = document.getElementById('cancelUploadBtn');
    Elements.uploadStatus = document.getElementById('uploadStatus');

    // Messages
    Elements.welcomeMessage = document.getElementById('welcomeMessage');
    Elements.loadingIndicator = document.getElementById('loadingIndicator');
    Elements.errorMessage = document.getElementById('errorMessage');
    Elements.errorText = document.getElementById('errorText');
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Category selection
    Elements.categorySelect.addEventListener('change', handleCategoryChange);

    // Translation editing
    Elements.editTransBtn.addEventListener('click', () => toggleEditMode('translation', true));
    Elements.saveTransBtn.addEventListener('click', () => saveTranslation());
    Elements.cancelTransBtn.addEventListener('click', () => toggleEditMode('translation', false));

    // Sample sentence editing
    Elements.editSampleBtn.addEventListener('click', () => toggleEditMode('sample', true));
    Elements.saveSampleBtn.addEventListener('click', () => saveSample());
    Elements.cancelSampleBtn.addEventListener('click', () => toggleEditMode('sample', false));

    // Navigation buttons
    Elements.prevBtn.addEventListener('click', () => navigateWord(-1));
    Elements.nextBtn.addEventListener('click', () => navigateWord(1));

    // Keyboard navigation (Arrow keys)
    document.addEventListener('keydown', handleKeyboardNavigation);

    // Import functionality
    Elements.importBtn.addEventListener('click', toggleImportPanel);
    Elements.uploadBtn.addEventListener('click', uploadXMLFile);
    Elements.cancelUploadBtn.addEventListener('click', toggleImportPanel);
}

// ============================================
// API Functions
// ============================================

/**
 * Load all categories from the server
 */
async function loadCategories() {
    try {
        showLoading(true);

        const response = await fetch('/api/categories');
        const data = await response.json();

        if (data.success && data.categories) {
            populateCategoryDropdown(data.categories);
            console.log(`✅ Loaded ${data.categories.length} categories`);
        } else {
            showError('Failed to load categories');
        }

    } catch (error) {
        console.error('Error loading categories:', error);
        showError('Network error while loading categories');
    } finally {
        showLoading(false);
    }
}

/**
 * Load a specific word from a category by index
 */
async function loadWord(category, index) {
    try {
        showLoading(true);
        hideError();

        const response = await fetch(`/api/words/${encodeURIComponent(category)}?index=${index}`);
        const data = await response.json();

        if (data.success && data.word) {
            displayWord(data.word);
            console.log(`✅ Loaded word: ${data.word.word}`);
        } else {
            showError(data.error || 'Failed to load word');
        }

    } catch (error) {
        console.error('Error loading word:', error);
        showError('Network error while loading word');
    } finally {
        showLoading(false);
    }
}

/**
 * Update word translation or sample sentence
 */
async function updateWord(wordId, updates) {
    try {
        showLoading(true);

        const response = await fetch(`/api/words/${wordId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });

        const data = await response.json();

        if (data.success) {
            console.log('✅ Word updated successfully');
            // Reload the word to get fresh data
            await loadWord(AppState.currentCategory, AppState.currentIndex);
            return true;
        } else {
            showError(data.error || 'Failed to update word');
            return false;
        }

    } catch (error) {
        console.error('Error updating word:', error);
        showError('Network error while updating word');
        return false;
    } finally {
        showLoading(false);
    }
}

// ============================================
// UI Update Functions
// ============================================

/**
 * Populate category dropdown with fetched categories
 */
function populateCategoryDropdown(categories) {
    Elements.categorySelect.innerHTML = '<option value="">-- Select a Category --</option>';

    categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.name;
        option.textContent = `${cat.name} (${cat.word_count} words)`;
        Elements.categorySelect.appendChild(option);
    });
}

/**
 * Display word data in the UI
 */
function displayWord(wordData) {
    // Update app state
    AppState.currentWord = wordData;
    AppState.currentIndex = wordData.current_index;
    AppState.totalInCategory = wordData.total_in_category;

    // Show word card, hide welcome message
    Elements.wordCard.style.display = 'block';
    Elements.welcomeMessage.style.display = 'none';

    // Display word
    Elements.wordDisplay.textContent = wordData.word;

    // Display translation
    Elements.translationDisplay.textContent = wordData.translation;
    Elements.translationInput.value = wordData.translation;

    // Display sample sentence
    if (wordData.sample_sentence && wordData.sample_sentence.trim()) {
        Elements.sampleDisplay.textContent = wordData.sample_sentence;
        Elements.sampleDisplay.classList.remove('empty');
    } else {
        Elements.sampleDisplay.textContent = 'No sample sentence yet. Click Edit to add one.';
        Elements.sampleDisplay.classList.add('empty');
    }
    Elements.sampleInput.value = wordData.sample_sentence || '';

    // Update position info
    Elements.positionInfo.textContent =
        `Word ${wordData.current_index + 1} of ${wordData.total_in_category}`;

    // Update navigation button states
    updateNavigationButtons();
}

/**
 * Update navigation button enabled/disabled states
 */
function updateNavigationButtons() {
    Elements.prevBtn.disabled = AppState.currentIndex === 0;
    Elements.nextBtn.disabled = AppState.currentIndex >= AppState.totalInCategory - 1;
}

/**
 * Toggle edit mode for translation or sample sentence
 */
function toggleEditMode(type, isEditing) {
    if (type === 'translation') {
        AppState.isEditingTranslation = isEditing;
        Elements.translationDisplay.style.display = isEditing ? 'none' : 'block';
        Elements.translationEdit.style.display = isEditing ? 'block' : 'none';
        Elements.editTransBtn.style.display = isEditing ? 'none' : 'inline-flex';

        if (isEditing) {
            Elements.translationInput.focus();
        }
    } else if (type === 'sample') {
        AppState.isEditingSample = isEditing;
        Elements.sampleDisplay.style.display = isEditing ? 'none' : 'block';
        Elements.sampleEdit.style.display = isEditing ? 'block' : 'none';
        Elements.editSampleBtn.style.display = isEditing ? 'none' : 'inline-flex';

        if (isEditing) {
            Elements.sampleInput.focus();
        }
    }
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    Elements.loadingIndicator.style.display = show ? 'block' : 'none';
}

/**
 * Show error message
 */
function showError(message) {
    Elements.errorText.textContent = message;
    Elements.errorMessage.style.display = 'flex';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        hideError();
    }, 5000);
}

/**
 * Hide error message
 */
function hideError() {
    Elements.errorMessage.style.display = 'none';
}

/**
 * Toggle import panel visibility
 */
function toggleImportPanel() {
    const isVisible = Elements.importPanel.style.display === 'block';
    Elements.importPanel.style.display = isVisible ? 'none' : 'block';
    Elements.uploadStatus.textContent = '';
    Elements.uploadStatus.className = 'upload-status';

    if (!isVisible) {
        Elements.fileInput.value = '';
    }
}

// ============================================
// Event Handlers
// ============================================

/**
 * Handle category selection change
 */
function handleCategoryChange(event) {
    const category = event.target.value;

    if (category) {
        AppState.currentCategory = category;
        AppState.currentIndex = 0;
        loadWord(category, 0);

        console.log(`📂 Category selected: ${category}`);
    } else {
        // No category selected - show welcome message
        Elements.wordCard.style.display = 'none';
        Elements.welcomeMessage.style.display = 'block';
        AppState.currentCategory = null;
    }
}

/**
 * Handle word navigation (prev/next)
 */
function navigateWord(direction) {
    if (!AppState.currentCategory) return;

    const newIndex = AppState.currentIndex + direction;

    // Check bounds
    if (newIndex < 0 || newIndex >= AppState.totalInCategory) return;

    AppState.currentIndex = newIndex;
    loadWord(AppState.currentCategory, newIndex);
}

/**
 * Handle keyboard navigation (arrow keys)
 */
function handleKeyboardNavigation(event) {
    // Ignore if user is typing in an input field
    if (event.target.tagName === 'TEXTAREA' || event.target.tagName === 'INPUT') {
        return;
    }

    // Ignore if no category selected
    if (!AppState.currentCategory) return;

    if (event.key === 'ArrowLeft') {
        event.preventDefault();
        navigateWord(-1);
    } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        navigateWord(1);
    }
}

/**
 * Save translation changes
 */
async function saveTranslation() {
    const newTranslation = Elements.translationInput.value.trim();

    if (!newTranslation) {
        showError('Translation cannot be empty');
        return;
    }

    const success = await updateWord(AppState.currentWord.id, {
        translation: newTranslation
    });

    if (success) {
        toggleEditMode('translation', false);
    }
}

/**
 * Save sample sentence changes
 */
async function saveSample() {
    const newSample = Elements.sampleInput.value.trim();

    const success = await updateWord(AppState.currentWord.id, {
        sample_sentence: newSample
    });

    if (success) {
        toggleEditMode('sample', false);
    }
}

/**
 * Upload XML file
 */
async function uploadXMLFile() {
    const file = Elements.fileInput.files[0];

    if (!file) {
        Elements.uploadStatus.textContent = '⚠️ Please select a file first';
        Elements.uploadStatus.className = 'upload-status error';
        return;
    }

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.xml')) {
        Elements.uploadStatus.textContent = '⚠️ Please select an XML file';
        Elements.uploadStatus.className = 'upload-status error';
        return;
    }

    try {
        Elements.uploadStatus.textContent = '⏳ Uploading and processing...';
        Elements.uploadStatus.className = 'upload-status';
        Elements.uploadBtn.disabled = true;

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            Elements.uploadStatus.textContent = `✅ ${data.message}`;
            Elements.uploadStatus.className = 'upload-status success';

            // Reload categories to show updated counts
            setTimeout(() => {
                loadCategories();
                toggleImportPanel();
            }, 2000);

            console.log('✅ Import successful:', data.stats);
        } else {
            Elements.uploadStatus.textContent = `❌ ${data.error}`;
            Elements.uploadStatus.className = 'upload-status error';
        }

    } catch (error) {
        console.error('Error uploading file:', error);
        Elements.uploadStatus.textContent = '❌ Network error during upload';
        Elements.uploadStatus.className = 'upload-status error';
    } finally {
        Elements.uploadBtn.disabled = false;
    }
}

// ============================================
// Utility Functions
// ============================================

/**
 * Escape HTML to prevent XSS attacks
 */
function escapeHTML(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Console Welcome Message
// ============================================
console.log(`
╔════════════════════════════════════════╗
║     BKDict Vocabulary Learning App     ║
║         Frontend Initialized           ║
╚════════════════════════════════════════╝
`);
