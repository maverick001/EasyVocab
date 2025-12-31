# Changelog


## [Unreleased]

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
