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
    currentSortBy: 'updated_at',  // Default sort by recent edits
    isEditingTranslation: false,
    isEditingSample: false,
    isEditingWord: false
};

// ============================================
// DOM Elements (cached for performance)
// ============================================
const Elements = {
    // Category selection
    categorySelect: null,
    categoryInfo: null,
    sortSelect: null,

    // Word card
    wordCard: null,
    wordDisplay: null,
    wordEdit: null,
    wordInput: null,
    editWordBtn: null,
    saveWordBtn: null,
    cancelWordBtn: null,
    positionInfo: null,
    reviewCounter: null,
    reviewCount: null,

    // Word actions
    changeCategorySelect: null,
    moveCategoryBtn: null,
    deleteWordBtn: null,

    // Translation elements
    translationDisplay: null,
    translationEdit: null,
    translationInput: null,
    saveTransBtn: null,
    cancelTransBtn: null,

    // Sample sentence elements (simplified)
    sampleDisplay: null,
    sampleEdit: null,
    sampleInput: null,
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

    // Add Word Modal
    addWordBtn: null,
    addWordModal: null,
    closeModalBtn: null,
    cancelModalBtn: null,
    submitWordBtn: null,
    newWord: null,
    newTranslation: null,
    newCategory: null,
    newSample: null,
    addWordStatus: null,

    // Search
    searchInput: null,
    searchBtn: null,
    clearSearchBtn: null,
    searchResults: null,
    searchResultsCount: null,
    searchResultsList: null,

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
    Elements.sortSelect = document.getElementById('sortSelect');

    // Word card
    Elements.wordCard = document.getElementById('wordCard');
    Elements.wordDisplay = document.getElementById('wordDisplay');
    Elements.wordEdit = document.getElementById('wordEdit');
    Elements.wordInput = document.getElementById('wordInput');
    Elements.editWordBtn = document.getElementById('editWordBtn');
    Elements.saveWordBtn = document.getElementById('saveWordBtn');
    Elements.cancelWordBtn = document.getElementById('cancelWordBtn');
    Elements.positionInfo = document.getElementById('positionInfo');
    Elements.reviewCounter = document.getElementById('reviewCounter');
    Elements.reviewCount = document.getElementById('reviewCount');

    // Word actions
    Elements.changeCategorySelect = document.getElementById('changeCategorySelect');
    Elements.moveCategoryBtn = document.getElementById('moveCategoryBtn');
    Elements.deleteWordBtn = document.getElementById('deleteWordBtn');

    // Translation
    Elements.translationDisplay = document.getElementById('translationDisplay');
    Elements.translationEdit = document.getElementById('translationEdit');
    Elements.translationInput = document.getElementById('translationInput');
    Elements.saveTransBtn = document.getElementById('saveTransBtn');
    Elements.cancelTransBtn = document.getElementById('cancelTransBtn');

    // Sample (simplified - single textarea)
    Elements.sampleDisplay = document.getElementById('sampleDisplay');
    Elements.sampleEdit = document.getElementById('sampleEdit');
    Elements.sampleInput = document.getElementById('sampleInput');
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

    // Add Word Modal
    Elements.addWordBtn = document.getElementById('addWordBtn');
    Elements.addWordModal = document.getElementById('addWordModal');
    Elements.closeModalBtn = document.getElementById('closeModalBtn');
    Elements.cancelModalBtn = document.getElementById('cancelModalBtn');
    Elements.submitWordBtn = document.getElementById('submitWordBtn');
    Elements.newWord = document.getElementById('newWord');
    Elements.newTranslation = document.getElementById('newTranslation');
    Elements.newCategory = document.getElementById('newCategory');
    Elements.newSample = document.getElementById('newSample');
    Elements.addWordStatus = document.getElementById('addWordStatus');

    // Search
    Elements.searchInput = document.getElementById('searchInput');
    Elements.searchBtn = document.getElementById('searchBtn');
    Elements.clearSearchBtn = document.getElementById('clearSearchBtn');
    Elements.searchResults = document.getElementById('searchResults');
    Elements.searchResultsCount = document.getElementById('searchResultsCount');
    Elements.searchResultsList = document.getElementById('searchResultsList');

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

    // Sort selection
    Elements.sortSelect.addEventListener('change', handleSortChange);

    // Word editing
    Elements.editWordBtn.addEventListener('click', () => toggleEditMode('word', true));
    Elements.saveWordBtn.addEventListener('click', () => saveWord());
    Elements.cancelWordBtn.addEventListener('click', () => toggleEditMode('word', false));

    // Translation editing - click on display to edit
    Elements.translationDisplay.addEventListener('click', () => toggleEditMode('translation', true));
    Elements.saveTransBtn.addEventListener('click', () => saveTranslation());
    Elements.cancelTransBtn.addEventListener('click', () => toggleEditMode('translation', false));

    // Sample sentence editing - click on display to edit
    Elements.sampleDisplay.addEventListener('click', () => toggleEditMode('sample', true));
    Elements.saveSampleBtn.addEventListener('click', () => saveSample());
    Elements.cancelSampleBtn.addEventListener('click', () => toggleEditMode('sample', false));

    // Navigation buttons
    Elements.prevBtn.addEventListener('click', () => navigateWord(-1));
    Elements.nextBtn.addEventListener('click', () => navigateWord(1));

    // Keyboard navigation (Arrow keys)
    document.addEventListener('keydown', handleKeyboardNavigation);

    // Word actions
    Elements.reviewCounter.addEventListener('click', () => incrementReviewCounter());
    Elements.moveCategoryBtn.addEventListener('click', () => changeWordCategory());
    Elements.deleteWordBtn.addEventListener('click', () => deleteCurrentWord());

    // Import functionality
    Elements.importBtn.addEventListener('click', toggleImportPanel);
    Elements.uploadBtn.addEventListener('click', uploadXMLFile);
    Elements.cancelUploadBtn.addEventListener('click', toggleImportPanel);

    // Add Word Modal
    Elements.addWordBtn.addEventListener('click', openAddWordModal);
    Elements.closeModalBtn.addEventListener('click', closeAddWordModal);
    Elements.cancelModalBtn.addEventListener('click', closeAddWordModal);
    Elements.submitWordBtn.addEventListener('click', submitNewWord);

    // Search functionality
    Elements.searchBtn.addEventListener('click', performSearch);
    Elements.clearSearchBtn.addEventListener('click', clearSearch);
    Elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
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

        const response = await fetch(`/api/words/${encodeURIComponent(category)}?index=${index}&sort_by=${AppState.currentSortBy}`);
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
 * Update word, translation, or sample sentence
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

            // Update local state instead of reloading to keep word on screen
            // (reloading would change position due to updated_at timestamp change)
            if ('word' in updates) {
                AppState.currentWord.word = updates.word;
                Elements.wordDisplay.textContent = updates.word;
            }
            if ('translation' in updates) {
                AppState.currentWord.translation = updates.translation;
                Elements.translationDisplay.textContent = updates.translation;
            }
            if ('sample_sentence' in updates) {
                AppState.currentWord.sample_sentence = updates.sample_sentence;
                // Redisplay samples with updated content
                displaySampleSentences(updates.sample_sentence);
            }

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
 * Update sample sentence display
 */
function displaySampleSentences(sampleText) {
    if (sampleText && sampleText.trim()) {
        // Parse sentences and display as numbered list
        const sentences = sampleText
            .split('\n')
            .map(s => s.trim())
            .filter(s => s.length > 0);

        if (sentences.length > 0) {
            const ol = document.createElement('ol');
            ol.className = 'sentences-display-list';
            sentences.forEach(sentence => {
                const li = document.createElement('li');
                li.textContent = sentence;
                li.className = 'sentence-item';
                ol.appendChild(li);
            });
            Elements.sampleDisplay.innerHTML = '';
            Elements.sampleDisplay.appendChild(ol);
            Elements.sampleDisplay.classList.remove('empty');
        } else {
            Elements.sampleDisplay.innerHTML = '<p class="empty-hint">No sample sentences yet. Click Edit to add some.</p>';
            Elements.sampleDisplay.classList.add('empty');
        }
    } else {
        Elements.sampleDisplay.innerHTML = '<p class="empty-hint">No sample sentences yet. Click Edit to add some.</p>';
        Elements.sampleDisplay.classList.add('empty');
    }

    // Update sample input textarea
    Elements.sampleInput.value = sampleText || '';
}

/**
 * Populate category dropdown with fetched categories
 */
function populateCategoryDropdown(categories) {
    // Populate main category selector
    Elements.categorySelect.innerHTML = '<option value="">-- Select a Category --</option>';

    categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.name;
        option.textContent = `${cat.name} (${cat.word_count} words)`;
        Elements.categorySelect.appendChild(option);
    });

    // Also populate the change category selector
    Elements.changeCategorySelect.innerHTML = '<option value="">-- Select Category --</option>';

    categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.name;
        option.textContent = cat.name;
        Elements.changeCategorySelect.appendChild(option);
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

    // Display review count
    const reviewCount = wordData.review_count || 0;
    Elements.reviewCount.textContent = reviewCount;

    // Display translation
    Elements.translationDisplay.textContent = wordData.translation;
    Elements.translationInput.value = wordData.translation;

    // Display sample sentences using helper function
    displaySampleSentences(wordData.sample_sentence);

    // Update word input
    Elements.wordInput.value = wordData.word;

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
 * Toggle edit mode for word, translation, or sample sentence
 */
function toggleEditMode(type, isEditing) {
    if (type === 'word') {
        AppState.isEditingWord = isEditing;
        document.getElementById('wordDisplayContainer').style.display = isEditing ? 'none' : 'flex';
        Elements.wordEdit.style.display = isEditing ? 'flex' : 'none';

        if (isEditing) {
            Elements.wordInput.focus();
            Elements.wordInput.select();
        }
    } else if (type === 'translation') {
        AppState.isEditingTranslation = isEditing;
        Elements.translationDisplay.style.display = isEditing ? 'none' : 'block';
        Elements.translationEdit.style.display = isEditing ? 'block' : 'none';

        if (isEditing) {
            Elements.translationInput.focus();
        }
    } else if (type === 'sample') {
        AppState.isEditingSample = isEditing;
        Elements.sampleDisplay.style.display = isEditing ? 'none' : 'block';
        Elements.sampleEdit.style.display = isEditing ? 'block' : 'none';

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
 * Handle sort method change
 */
function handleSortChange(event) {
    const sortBy = event.target.value;

    if (AppState.currentCategory) {
        AppState.currentSortBy = sortBy;
        AppState.currentIndex = 0;  // Reset to first word in new sort order
        loadWord(AppState.currentCategory, 0);

        console.log(`🔄 Sort changed to: ${sortBy}`);
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
 * Save word changes
 */
async function saveWord() {
    const newWord = Elements.wordInput.value.trim();

    if (!newWord) {
        showError('Word cannot be empty');
        return;
    }

    const success = await updateWord(AppState.currentWord.id, {
        word: newWord
    });

    if (success) {
        toggleEditMode('word', false);
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
 * Save sample sentence changes (simplified - single textarea)
 */
async function saveSample() {
    // Get textarea value directly (each line is a separate sentence)
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
// Add Word Modal Functions
// ============================================

/**
 * Open the Add Word modal and populate category dropdown
 */
function openAddWordModal() {
    // Clear previous values
    Elements.newWord.value = '';
    Elements.newTranslation.value = '';
    Elements.newSample.value = '';
    Elements.addWordStatus.textContent = '';
    Elements.addWordStatus.className = 'form-status';

    // Populate category dropdown
    Elements.newCategory.innerHTML = '<option value="">-- Select Category --</option>';

    // Get categories from the main category select
    const mainSelect = Elements.categorySelect;
    for (let i = 1; i < mainSelect.options.length; i++) {  // Skip first "-- Select --" option
        const option = document.createElement('option');
        option.value = mainSelect.options[i].value;
        option.textContent = mainSelect.options[i].textContent;
        Elements.newCategory.appendChild(option);
    }

    // Show modal
    Elements.addWordModal.style.display = 'flex';
}

/**
 * Close the Add Word modal
 */
function closeAddWordModal() {
    Elements.addWordModal.style.display = 'none';
}

/**
 * Submit new word to backend
 */
async function submitNewWord() {
    // Get values
    const word = Elements.newWord.value.trim();
    const translation = Elements.newTranslation.value.trim();
    const category = Elements.newCategory.value.trim();
    const sample = Elements.newSample.value.trim();

    // Validate required fields
    if (!word) {
        Elements.addWordStatus.textContent = '⚠️ Word is required';
        Elements.addWordStatus.className = 'form-status error';
        return;
    }

    if (!translation) {
        Elements.addWordStatus.textContent = '⚠️ Translation is required';
        Elements.addWordStatus.className = 'form-status error';
        return;
    }

    if (!category) {
        Elements.addWordStatus.textContent = '⚠️ Category is required';
        Elements.addWordStatus.className = 'form-status error';
        return;
    }

    try {
        Elements.submitWordBtn.disabled = true;
        Elements.addWordStatus.textContent = '⏳ Adding word...';
        Elements.addWordStatus.className = 'form-status';

        const response = await fetch('/api/words', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word: word,
                translation: translation,
                category: category,
                sample_sentence: sample
            })
        });

        const data = await response.json();

        if (data.success) {
            Elements.addWordStatus.textContent = `✅ ${data.message}`;
            Elements.addWordStatus.className = 'form-status success';

            // Reload categories to update counts
            await loadCategories();

            // Close modal after 1.5 seconds
            setTimeout(() => {
                closeAddWordModal();

                // If the word was added to current category, reload it
                if (AppState.currentCategory === category) {
                    loadWord(category, 0);  // Load first word (the newly added one if sorted by recent edits)
                }
            }, 1500);

            console.log(`✅ Word "${word}" added successfully`);
        } else {
            if (data.duplicate) {
                Elements.addWordStatus.textContent = `⚠️ ${data.error}`;
            } else {
                Elements.addWordStatus.textContent = `❌ ${data.error}`;
            }
            Elements.addWordStatus.className = 'form-status error';
        }

    } catch (error) {
        console.error('Error adding word:', error);
        Elements.addWordStatus.textContent = '❌ Network error while adding word';
        Elements.addWordStatus.className = 'form-status error';
    } finally {
        Elements.submitWordBtn.disabled = false;
    }
}

// ============================================
// Search Functions
// ============================================

/**
 * Perform word search
 */
async function performSearch() {
    const query = Elements.searchInput.value.trim();

    if (!query) {
        showError('Please enter a search query');
        return;
    }

    if (query.length < 2) {
        showError('Search query must be at least 2 characters');
        return;
    }

    try {
        hideError();
        showLoading(true);

        const response = await fetch(`/api/words/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success) {
            displaySearchResults(data);
            Elements.clearSearchBtn.style.display = 'inline-block';
            console.log(`✅ Found ${data.count} results for "${query}"`);
        } else {
            showError(data.error || 'Search failed');
        }

    } catch (error) {
        console.error('Error searching:', error);
        showError('Network error during search');
    } finally {
        showLoading(false);
    }
}

/**
 * Display search results
 */
function displaySearchResults(data) {
    // Show search results panel
    Elements.searchResults.style.display = 'block';
    Elements.wordCard.style.display = 'none';
    Elements.welcomeMessage.style.display = 'none';

    // Update header
    Elements.searchResultsCount.textContent = `Found ${data.count} result${data.count !== 1 ? 's' : ''} for "${data.query}"`;

    // Clear previous results
    Elements.searchResultsList.innerHTML = '';

    if (data.count === 0) {
        Elements.searchResultsList.innerHTML = `
            <div class="search-no-results">
                <p>No words found containing "${data.query}"</p>
                <p>Try a different search term</p>
            </div>
        `;
        return;
    }

    // Display results
    data.results.forEach(result => {
        const item = document.createElement('div');
        item.className = 'search-result-item';
        item.innerHTML = `
            <div class="search-result-word">${escapeHTML(result.word)}</div>
            <div class="search-result-translation">${escapeHTML(result.translation)}</div>
            <div class="search-result-meta">
                <span class="search-result-category">${escapeHTML(result.category)}</span>
                <span>Reviews: ${result.review_count}</span>
            </div>
        `;

        // Click to view word details
        item.addEventListener('click', () => {
            viewSearchResult(result);
        });

        Elements.searchResultsList.appendChild(item);
    });
}

/**
 * View a search result (load the word in its category)
 */
async function viewSearchResult(result) {
    try {
        // Set category
        AppState.currentCategory = result.category;
        Elements.categorySelect.value = result.category;

        // Hide search results
        Elements.searchResults.style.display = 'none';
        Elements.wordCard.style.display = 'block';

        // Load words in the category and find this word's index
        const response = await fetch(`/api/words/${encodeURIComponent(result.category)}?index=0&sort_by=${AppState.currentSortBy}`);
        const data = await response.json();

        if (data.success) {
            // Find the index of the clicked word
            const wordResponse = await fetch(`/api/words/${encodeURIComponent(result.category)}?sort_by=${AppState.currentSortBy}`);
            const wordData = await wordResponse.json();

            // Simple approach: just load the first word and let user navigate
            // Or we could find the exact index, but that would require additional API support
            displayWord(data.word);
            console.log(`✅ Viewing "${result.word}" in category "${result.category}"`);
        }

    } catch (error) {
        console.error('Error viewing search result:', error);
        showError('Failed to load word details');
    }
}

/**
 * Clear search and return to category view
 */
function clearSearch() {
    Elements.searchInput.value = '';
    Elements.clearSearchBtn.style.display = 'none';
    Elements.searchResults.style.display = 'none';

    // Show welcome or current category
    if (AppState.currentCategory) {
        Elements.wordCard.style.display = 'block';
    } else {
        Elements.welcomeMessage.style.display = 'block';
    }
}

// ============================================
// Word Actions Functions
// ============================================

/**
 * Increment review counter for current word
 */
async function incrementReviewCounter() {
    if (!AppState.currentWord) return;

    try {
        const response = await fetch(`/api/words/${AppState.currentWord.id}/review`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            // Update the display with new count
            Elements.reviewCount.textContent = data.review_count;

            // Add visual feedback
            Elements.reviewCounter.style.transform = 'translateY(-50%) scale(1.2)';
            setTimeout(() => {
                Elements.reviewCounter.style.transform = 'translateY(-50%) scale(1)';
            }, 200);

            console.log(`✅ Review count updated: ${data.review_count}`);
        } else {
            showError(data.error || 'Failed to update review count');
        }

    } catch (error) {
        console.error('Error incrementing review counter:', error);
        showError('Network error while updating review count');
    }
}

/**
 * Change category of current word
 */
async function changeWordCategory() {
    if (!AppState.currentWord) return;

    const newCategory = Elements.changeCategorySelect.value;

    if (!newCategory) {
        showError('Please select a category first');
        return;
    }

    if (newCategory === AppState.currentWord.category) {
        showError('Word is already in this category');
        return;
    }

    try {
        const response = await fetch(`/api/words/${AppState.currentWord.id}/category`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                new_category: newCategory
            })
        });

        const data = await response.json();

        if (data.success) {
            console.log(`✅ ${data.message}`);

            // Save current category before reloading
            const savedCategory = AppState.currentCategory;

            // Reload categories to update counts
            await loadCategories();

            // Restore category selection in dropdown
            if (savedCategory) {
                Elements.categorySelect.value = savedCategory;
            }

            // Navigate to next word in current category
            navigateWord(1);

        } else {
            // Check if this is a duplicate word error
            if (data.duplicate) {
                // Show popup warning for duplicate
                alert(data.error || 'This word already exists in the target category');
            } else {
                showError(data.error || 'Failed to change category');
            }
        }

    } catch (error) {
        console.error('Error changing category:', error);
        showError('Network error while changing category');
    }
}

/**
 * Delete current word
 */
async function deleteCurrentWord() {
    if (!AppState.currentWord) return;

    // Basic confirmation first
    if (!confirm(`Are you sure you want to delete "${AppState.currentWord.word}"?`)) {
        return;
    }

    try {
        // Check if word exists in other categories
        const checkResponse = await fetch(`/api/words/${AppState.currentWord.id}`, {
            method: 'DELETE'
        });

        const checkData = await checkResponse.json();

        // If word exists in other categories, ask user for scope choice
        if (checkData.requires_confirmation) {
            const otherCats = checkData.other_categories.join('\n   - ');

            // Show prompt with three clear options
            const promptMessage = `Word "${checkData.word}" also exists in other categories:\n   - ${otherCats}\n\nChoose deletion scope:\n  1 = Delete only from "${checkData.current_category}"\n  2 = Delete from ALL categories\n  3 = Cancel (do not delete)\n\nEnter your choice (1, 2, or 3):`;

            const userChoice = prompt(promptMessage);

            if (userChoice === '1') {
                // Delete only from current category
                await performDelete(AppState.currentWord.id, 'current_category');
            } else if (userChoice === '2') {
                // Delete from all categories
                await performDelete(AppState.currentWord.id, 'all_categories');
            } else {
                // User chose 3 or cancelled - do nothing
                console.log('Deletion cancelled by user');
            }
        } else if (checkData.success) {
            // Word was deleted successfully (only existed in current category)
            await handleDeleteSuccess(checkData.message);
        } else {
            // Some other error occurred
            showError(checkData.error || 'Failed to delete word');
        }

    } catch (error) {
        console.error('Error deleting word:', error);
        showError('Network error while deleting word');
    }
}

/**
 * Perform actual deletion with specified scope
 */
async function performDelete(wordId, scope) {
    try {
        const response = await fetch(`/api/words/${wordId}?scope=${scope}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            await handleDeleteSuccess(data.message);
        } else {
            showError(data.error || 'Failed to delete word');
        }

    } catch (error) {
        console.error('Error deleting word:', error);
        showError('Network error while deleting word');
    }
}

/**
 * Handle successful deletion - reload categories and navigate
 */
async function handleDeleteSuccess(message) {
    console.log(`✅ ${message}`);

    // Save current category before reloading
    const savedCategory = AppState.currentCategory;

    // Reload categories to update counts
    await loadCategories();

    // Restore category selection in dropdown
    if (savedCategory) {
        Elements.categorySelect.value = savedCategory;
    }

    // Load the same index (which will now show the next word)
    if (savedCategory && AppState.totalInCategory > 1) {
        // If we deleted the last word, go to previous
        if (AppState.currentIndex >= AppState.totalInCategory - 1) {
            AppState.currentIndex = Math.max(0, AppState.currentIndex - 1);
        }
        await loadWord(savedCategory, AppState.currentIndex);
    } else {
        // No more words in this category
        Elements.wordCard.style.display = 'none';
        Elements.welcomeMessage.style.display = 'block';
        AppState.currentCategory = null;
        Elements.categorySelect.value = '';
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
