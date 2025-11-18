-- ============================================
-- Add Word History Tracking
-- ============================================
-- This script creates a table to track word modification history

USE bkdict_db;

-- ============================================
-- Table: word_history
-- Stores historical snapshots of word modifications
-- ============================================
CREATE TABLE IF NOT EXISTS word_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word_id INT NOT NULL COMMENT 'Reference to words.id',
    word VARCHAR(255) NOT NULL COMMENT 'The word text at this point in time',
    translation TEXT NOT NULL COMMENT 'Translation at this point in time',
    sample_sentence TEXT DEFAULT NULL COMMENT 'Sample sentence at this point in time',
    category VARCHAR(100) NOT NULL COMMENT 'Category at this point in time',
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When this version was created',
    modification_type ENUM('created', 'updated', 'moved') NOT NULL DEFAULT 'updated' COMMENT 'Type of modification',

    -- Index for fast lookup by word_id
    INDEX idx_word_id (word_id),

    -- Index for sorting by modification time
    INDEX idx_modified_at (modified_at),

    -- Composite index for word history queries
    INDEX idx_word_id_modified (word_id, modified_at DESC)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Word modification history tracking';

-- ============================================
-- Populate initial history from existing words
-- (Creates 'created' records for all existing words)
-- ============================================
INSERT INTO word_history (word_id, word, translation, sample_sentence, category, modified_at, modification_type)
SELECT
    id,
    word,
    translation,
    sample_sentence,
    category,
    created_at,
    'created'
FROM words
WHERE NOT EXISTS (
    SELECT 1 FROM word_history WHERE word_history.word_id = words.id
);

SELECT 'Word history table created and populated!' AS status;
SELECT COUNT(*) AS total_history_records FROM word_history;
