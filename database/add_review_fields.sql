-- ============================================
-- BKDict Database Migration
-- Add review counter and tracking fields
-- ============================================

USE bkdict_db;

-- Add review counter field (defaults to 0)
ALTER TABLE words
ADD COLUMN review_count INT DEFAULT 0 COMMENT 'Number of times this word has been reviewed';

-- Add last reviewed timestamp field
ALTER TABLE words
ADD COLUMN last_reviewed TIMESTAMP NULL DEFAULT NULL COMMENT 'Last time this word was reviewed by user';

-- Add index for efficient querying by review stats
ALTER TABLE words
ADD INDEX idx_review_count (review_count);

ALTER TABLE words
ADD INDEX idx_last_reviewed (last_reviewed);

-- Verify the changes
DESCRIBE words;

SELECT 'Migration completed successfully!' AS status;
