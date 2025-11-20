-- ============================================
-- Update Schema for Word Debt Feature
-- ============================================

USE bkdict_db;

-- Table: daily_study_log
-- Tracks the number of words reviewed each day to calculate "Word Debt"
CREATE TABLE IF NOT EXISTS daily_study_log (
    date DATE PRIMARY KEY COMMENT 'The date of study',
    review_count INT DEFAULT 0 COMMENT 'Number of words reviewed on this date',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update time'
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Daily study activity log for debt calculation';
