# Changelog


## [Unreleased]
### Changed
- **Coral Neo Theme**: the Glassmorphism theme is now "Coral Neo", a neumorphic look after a navy and coral UI kit: a light grey surface with large raised cards and inset wells, navy buttons, dropdowns and badges, and a coral-red gradient for the main actions. Dark mode keeps the same look on a slightly dimmer surface. The theme key and file keep the name `glassmorphism`, so saved selections carry over.
- **Static File Caching**: CSS, JS, theme and favicon URLs now carry a `?v=<content hash>` and are cached for a year by the browser and Vercel's CDN, so repeat page loads no longer fetch them through the Python function. Editing a file changes its hash, so changes still appear at once.
- **Sentry Sampling**: `SENTRY_TRACES_SAMPLE_RATE` now defaults to `0.5` (was `1.0`), halving the requests that wait on a Sentry upload.
- **Full Backups**: `scripts/backup_db.py` now also saves `categories`, `daily_word_reviews` and every stored word image (as files next to the JSON).
- **Faster Translation**: Gemini calls now use low reasoning effort (`GEMINI_REASONING_EFFORT`, default `low`), cutting a translation from roughly 10-50 seconds to about 2 seconds with the same quality. If a model rejects the setting the call is retried without it. Set the variable empty to restore each model's default.
- **Ghibli-Style Theme**: the Minimalist theme is now a hand-drawn cartoon countryside (sky, clouds, hills, a red gate, cream cards with ink outlines). The quiz page always uses this look, and dark mode is now one setting shared by both pages (`bkdict-theme`). The theme key and file keep the name `minimalist`, so saved selections carry over.
- **Cyberpunk Theme Upgrade**: neon HUD look on the vocab page (navy background, cut-corner panels, outlined neon buttons, Orbitron/Rajdhani fonts, dark dropdowns and windows). The Add New Word window title is now readable in Cyberpunk and Glassmorphism, and the review counter matches the IPA button beside it.
- **Word Debt Badge**: now matches the Word Today badge in size and style in every theme: yellow while there is debt (or the daily target is unmet), green when debt is 0 or below (or the target is met), with the number in red while yellow. The gap after each label is also wider.
- **Word Debt Can Go Negative**: debt is no longer floored at 0, so a surplus banks as credit (a negative number such as `-2`) and later missed days draw it down. The live count on the page follows the same rule as the server total.
- **Purple Quiz Me and Add Image**: both buttons are purple in every theme (Cyberpunk gets a new neon purple, Ghibli uses its lavender), and the Add Image button in the image window matches them.
- **Comma In Translations**: generated translations are joined with the Chinese comma instead of a semicolon, matching the Gemini prompt, in both the edit-translation and Add New Word flows.

### Security
- **Session Key Check**: on Vercel the app refuses to start if `SECRET_KEY` is missing or a public placeholder, instead of signing sessions with a value from the repo.

### Fixed
- **Latest-Edits Order**: reviewing a word no longer stamps its edit time 10 hours ahead, so a word reviewed hours ago no longer sorts above one edited just now. Words reviewed before this fix keep their old stamp until next edited or reviewed.
- **Leftover Images**: deleting a word, deleting a category or merging two entries now removes stored image bytes that no word uses any more.
- **Text Shown As Text**: quiz example sentences and the "word already exists" message are no longer inserted as HTML; a category name containing `'` no longer breaks the Go to Word button.
- **Arrow-Key Navigation**: holding an arrow key can no longer end on the wrong word when responses arrive out of order.
- **Silent API Errors**: routes that answer with a JSON 500 now write the traceback to the server log and report it to Sentry.
- **Category Move Counts As A Review**: moving a word to another category now bumps its review count and last-reviewed date (once per word per day, like other edits), so the history date and the counter no longer disagree.

### Added
- **Gemini-Written Quiz Options**: the wrong choices in multiple-choice mode are written by Gemini (`GEMINI_QUIZ_MODEL`, default `gemini-3.5-flash-lite`, about 1 to 5 s) as other members of the right answer's group, in its format: for `蓝色的` they write `黄色的`, `红色的`, `绿色的`; a word with no natural group gets words from the same topic. The group is taken from the answer's first (main) meaning, and the word's category in your list is sent as a topic hint. A word with `adj.` gets `adj.` options and a word with no prefix gets options with none, so the format never gives the answer away. Options that are a shade or near-synonym of the answer, or repeat one of its meanings of three or more characters (`浅蓝色的` next to `蓝色的`), are dropped, so a question can show fewer choices than the setting. The next question is fetched while you answer the current one, so the wait is mostly hidden. There is no database fallback: if Gemini fails, times out (8 s) or gives nothing usable, it is tried once more, and then the question shows "Couldn't generate the answer options. Please try again." Multiple-choice mode therefore needs `GOOGLE_API_KEY`; flashcard mode does not.
- **Optional Monitoring**: Sentry (errors, request timing) and Langfuse (Gemini call traces) turn on only when their keys are set in `.env` or on Vercel. Both are forced off under `SKIP_DB=true`, and a missing package or unreachable service never breaks a request.
- **Settings Page**: a new `/settings` page, reached from a Settings button on the vocab and quiz pages, for the daily target, turning word debt on or off, the debt start date, the timezone and the quiz session length. Values live in an `app_settings` table that is created on startup or on first save; a missing table, row or bad value falls back to the previous defaults.
- **Welcome Page Shortcuts**: pressing Enter on the welcome page does the same as clicking "Enter" (ignored while typing, on a focused button, with a window open, or on key repeat), and clicking the app title on the vocab page returns to the welcome page.

### Removed
- **Unused API Routes**: `GET /api/category/<category>/count`, `POST /api/upload` (the Import button uses `/api/upload-local`) and the path form `GET /api/words/<category>` (the page uses `/api/words-query?category=…`, which stays). Nothing in the app called them.


## [1.6.1] - 2026-02-09
### Added
- **Login Rate Limiting**: Added brute force protection on login page (5 attempts/minute per IP) using Flask-Limiter.

### Security
- Prevents password guessing attacks by temporarily blocking IPs after failed login attempts.


## [1.6.0] - 2026-02-02
### Fixed
- **Word Debt Timezone**: Fixed word debt calculation to use AEST timezone (UTC+10) instead of server time, ensuring consistent dates between local and Vercel deployments.
- **Daily Counter Sync**: Daily review counter now syncs to database for all actions: add, review, edit, and delete. Previously only "add word" was tracked.
- **Mobile Modal Display**: Fixed "Add New Word" modal on mobile (Galaxy S23) where submit button was cut off. Modal is now scrollable with sticky footer.

### Added
- **Word Deduplication**: Each word now counts only once per day toward the daily counter, preventing duplicate increments.
- **GitHub Actions CI/CD**: Added automated testing on Windows/Ubuntu and auto-merge to main branch when tests pass.

### Changed
- **Daily Counter Architecture**: Replaced MySQL trigger with explicit Python code for reliability across deployments.


## [1.5.0] - 2026-01-25
### Added
- **Docker Support**: Added Docker files to run the app in WSL2 environment.
- **Add Word from Search**: Added "Add Word" button in search results panel for quick word addition.
- **Word Uniqueness Check**: Added confirmation dialog showing if a word is the only record when deleting.

### Fixed
- **Mobile Category Display**: Fixed category dropdown not appearing on mobile devices.
- **Vercel Environment Detection**: Improved detection logic to correctly identify Vercel deployment environment.
- **Environment Badge**: Fixed frontpage badge to show correct environment (Local/Cloud).

### Changed
- **Default Review Count**: New manually added words now start with review_count = 2.
- **UI Layout**: Swapped control row and word section positions for better UX.
## [1.4.0] - 2026-01-09
### Added
- **Mobile Responsive**: Added mobile responsive design for improved readability in low-light environments. 
- **Translation Search**: Added translation search function to search words translations in entire MySQL DB. 
- **New Vocabulary Category**: Added a new vocabulary category for better classification of vocabulary.


## [1.3.0] - 2025-12-28
### Added
- **Dark Mode**: Added dark mode toggle for improved readability in low-light environments.
- **New Vocabulary Category**: Imported December 2025 vocabulary into `202512_New` category.

### Changed
- **AI Model Upgrade**: Upgraded to `gemini-3-flash` for improved performance and response quality.
- **UI Improvements**: Minor user interface enhancements.

### Repository
- **GitHub Publication**: Cleaned up repository for public release.
- **Security**: Removed unnecessary files (xml data, database backups, configuration) from version control.
- **Documentation**: Updated README with improved setup instructions.


## [1.2.0] - 2025-12-07
### Added
- **Poe API Integration**: Replaced Gemini API with Poe API for generating sample sentences.
  - Implemented using OpenAI SDK (`fastapi-poe` was considered but OpenAI SDK was chosen for simplicity).
  - Added configuration for `POE_API_KEY`, `POE_MODEL` (default: `Claude-Haiku-4.5`), and `POE_TEMPERATURE`.
- **UI Improvements**: Added word count display to the "Move to Category" dropdown (e.g., "Category Name (123)").

### Fixed
- **Daily Badge Bug**: Fixed an issue where adding a new word did not increment the daily progress counter (via `bugfix/adding_word_no_count`).
- **Poe Model Name**: Corrected model name from `Claude-3.5-Haiku` to `Claude-Haiku-4.5`.

## [1.1.0] - 2025-12-06
### Changed
- **Server Port**: Changed default Flask server port to 5001.
- **Word Debt Calculation**: 
  - Refined logic to calculate debt for every natural day (including days with no activity).
  - Debt starts calculating from the earliest record in the database.
  - Dropdown now displays the past 20 days starting from **yesterday** (today is excluded as reviews are ongoing).
  - Added color coding: Red for debt (missed quota), Green for surplus (exceeded quota).

### Added
- **Word Debt Dropdown**: Added detailed daily breakdown to the Word Debt UI.

## [1.0.0] - 2025-11-20
### Added
- Initial release of EasyVocab Vocabulary Builder.
- Basic CRUD operations for words.
- Category management.
- Gemini API integration (initial version).
