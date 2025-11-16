-- ============================================
-- Add Indexes for Sorting Performance
-- ============================================
-- This migration adds composite indexes for efficient sorting
-- by updated_at and review_count within categories

USE bkdict_db;

-- Add composite index for sorting by updated_at (latest edits)
-- This allows fast queries like: ORDER BY category, updated_at DESC
CREATE INDEX idx_category_updated
ON words (category, updated_at DESC);

-- Add composite index for sorting by review_count (most reviewed)
-- This allows fast queries like: ORDER BY category, review_count DESC
CREATE INDEX idx_category_review
ON words (category, review_count DESC, updated_at DESC);

-- Verify indexes were created
SHOW INDEX FROM words WHERE Key_name IN ('idx_category_updated', 'idx_category_review');

SELECT 'Sorting indexes added successfully!' AS status;
