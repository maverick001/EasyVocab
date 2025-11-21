-- ============================================
-- Trigger: after_review_increment
-- Automatically updates daily_study_log when words.review_count increases
-- Ensures data persistence across different app versions/git branches
-- ============================================

USE bkdict_db;

DROP TRIGGER IF EXISTS after_review_increment;

DELIMITER //

CREATE TRIGGER after_review_increment
AFTER UPDATE ON words
FOR EACH ROW
BEGIN
    DECLARE diff INT;
    SET diff = NEW.review_count - OLD.review_count;
    
    -- Only log if review_count actually increased
    IF diff > 0 THEN
        INSERT INTO daily_study_log (date, review_count)
        VALUES (CURDATE(), diff)
        ON DUPLICATE KEY UPDATE review_count = review_count + diff;
    END IF;
END //

DELIMITER ;
