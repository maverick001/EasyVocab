-- ============================================
-- Table: app_settings
-- Key/value settings edited on the /settings page:
--   daily_target     whole number 1-1000 (default 100)
--   debt_enabled     1 or 0 (default 1)
--   debt_start_date  YYYY-MM-DD, or empty = from the first logged day
--   timezone         IANA name such as Australia/Sydney, or empty = fixed UTC+10
-- A missing row means "use the default", so this table can start empty.
-- (The app also creates it on startup and on the first save.)
-- ============================================

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key VARCHAR(64) NOT NULL PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
