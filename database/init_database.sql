-- ============================================
-- BKDict Vocabulary Database Initialization
-- ============================================
-- This script creates the database and tables for the BKDict vocabulary web app
-- Designed to handle 30,000+ words across 20+ categories

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS bkdict_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE bkdict_db;

-- ============================================
-- Table: words
-- Stores vocabulary words with translations and sample sentences
-- ============================================
CREATE TABLE IF NOT EXISTS words (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(255) NOT NULL COMMENT 'The English word or phrase',
    translation TEXT NOT NULL COMMENT 'Chinese translation with CDATA content',
    category VARCHAR(100) NOT NULL COMMENT 'Category/tag for the word (e.g., 文化, AI)',
    sample_sentence TEXT DEFAULT NULL COMMENT 'Example sentence using the word (user-added)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',

    -- Unique constraint: same word can exist in different categories, but not duplicates in same category
    UNIQUE KEY unique_word_category (word, category),

    -- Index for fast category-based queries (critical for 30k+ words)
    INDEX idx_category (category),

    -- Index for word search
    INDEX idx_word (word),

    -- Composite index for category browsing with ordering
    INDEX idx_category_word (category, word)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Main vocabulary storage table';

-- ============================================
-- Table: categories
-- Stores category metadata and word counts (for quick reference)
-- ============================================
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE COMMENT 'Category name (e.g., 文化, AI)',
    word_count INT DEFAULT 0 COMMENT 'Number of words in this category',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last time category was modified',

    INDEX idx_name (name)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Category tracking and statistics';

-- ============================================
-- View: category_stats
-- Provides real-time category statistics
-- ============================================
CREATE OR REPLACE VIEW category_stats AS
SELECT
    category,
    COUNT(*) AS word_count,
    MAX(updated_at) AS last_updated
FROM words
GROUP BY category
ORDER BY category;

-- ============================================
-- Stored Procedure: update_category_counts
-- Updates the category word counts (call after bulk imports)
-- ============================================
DELIMITER //

CREATE PROCEDURE IF NOT EXISTS update_category_counts()
BEGIN
    -- Clear existing category data
    TRUNCATE TABLE categories;

    -- Insert current category statistics
    INSERT INTO categories (name, word_count, last_updated)
    SELECT
        category,
        COUNT(*) AS word_count,
        MAX(updated_at) AS last_updated
    FROM words
    GROUP BY category;
END //

DELIMITER ;

-- ============================================
-- Initial Data Check
-- ============================================
SELECT 'Database initialization complete!' AS status;
SELECT COUNT(*) AS total_words FROM words;
SELECT COUNT(DISTINCT category) AS total_categories FROM words;
