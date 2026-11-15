/**
 * Display names for categories.
 *
 * The database, the API and every <option value> keep the stored name (the
 * key). Only the text a person reads uses the display name (the value).
 * Loaded before app.js and quiz.js.
 */
const CATEGORY_DISPLAY_NAMES = {
    '政治': '人文',
    '军事': '航天',
};

/**
 * Name to show for a stored category name.
 * @param {string} name - category name as stored in the database
 * @returns {string} the display name, or the name itself when it has none
 */
function displayCategory(name) {
    return Object.prototype.hasOwnProperty.call(CATEGORY_DISPLAY_NAMES, name)
        ? CATEGORY_DISPLAY_NAMES[name]
        : name;
}

/**
 * Stored name for something the user typed. Typing a display name (人文)
 * means the category it stands for (政治), not a second category that would
 * show under the same name.
 * @param {string} name - category name as typed
 * @returns {string} the stored name
 */
function storedCategory(name) {
    const stored = Object.keys(CATEGORY_DISPLAY_NAMES)
        .find(key => CATEGORY_DISPLAY_NAMES[key] === name);
    return stored || name;
}

/**
 * Swap display names into a server message. The server always quotes a
 * category as: category "name". Nothing else in the text is touched.
 * @param {string} text - message or error text from the API
 * @returns {string} the text with category names replaced
 */
function displayCategoryInMessage(text) {
    if (typeof text !== 'string') return text;
    return text.replace(/(category ")([^"]*)(")/gi,
        (match, before, name, after) => before + displayCategory(name) + after);
}
