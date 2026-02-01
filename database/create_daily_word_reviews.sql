-- ============================================
-- Table: daily_word_reviews
-- Tracks which words have been counted for daily review each day
-- Used for deduplication (1 increment per word per day)
-- ============================================

CREATE TABLE IF NOT EXISTS daily_word_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word_id INT NOT NULL,
    review_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_word_day (word_id, review_date),
    INDEX idx_review_date (review_date)
);

-- Note: We don't add a foreign key to words table because:
-- 1. Words can be deleted, but we want to keep the review record
-- 2. This is for deduplication tracking only, not referential integrity
