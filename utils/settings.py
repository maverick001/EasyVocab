"""
App settings: defaults, validation and the small pure helpers around them.

Kept free of Flask and database imports so tests can exercise it directly.
The values live in the MySQL table app_settings as plain strings; the helpers
here turn them into typed values and back.
"""

from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9, not used by this project but harmless
    ZoneInfo = None

CREATE_APP_SETTINGS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS app_settings (
        setting_key VARCHAR(64) NOT NULL PRIMARY KEY,
        setting_value VARCHAR(255) NOT NULL DEFAULT ''
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# The behaviour before settings existed: 100 words a day, debt always on and
# counted from the first logged day, days rolling over at a fixed UTC+10.
DEFAULT_SETTINGS = {
    "daily_target": 100,
    "debt_enabled": True,
    "debt_start_date": "",  # "" = from the first logged day
    "timezone": "",  # "" = fixed UTC+10 (no daylight saving)
    "quiz_choice_count": 4,  # answer choices shown in quiz mode
    "quiz_session_size": 0,  # words per quiz session; 0 = no limit (as before)
}

DAILY_TARGET_MIN = 1
DAILY_TARGET_MAX = 1000
QUIZ_CHOICES_MIN = 2
QUIZ_CHOICES_MAX = 6
QUIZ_SESSION_MAX = 200
HISTORY_RANGES = (7, 30, 90)

FIXED_AEST = timezone(timedelta(hours=10))


def resolve_timezone(name):
    """tzinfo for an IANA name; the fixed UTC+10 default for "" or an unknown name"""
    if not name or ZoneInfo is None:
        return FIXED_AEST
    try:
        return ZoneInfo(name)
    except Exception:
        return FIXED_AEST


def _is_valid_timezone(name):
    if ZoneInfo is None:
        return False
    try:
        ZoneInfo(name)
        return True
    except Exception:
        return False


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("1", "true", "yes", "on"):
        return True
    if isinstance(value, str) and value.strip().lower() in ("0", "false", "no", "off"):
        return False
    return None


INT_RANGES = {
    "daily_target": (DAILY_TARGET_MIN, DAILY_TARGET_MAX),
    "quiz_choice_count": (QUIZ_CHOICES_MIN, QUIZ_CHOICES_MAX),
    "quiz_session_size": (0, QUIZ_SESSION_MAX),
}


def _parse_whole_number(raw):
    """int for a whole number or digit string; None for anything else (bool too)"""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, float):
        return int(raw) if raw.is_integer() else None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def validate_settings(payload):
    """
    Check a (possibly partial) settings payload.

    Returns (clean, errors): clean holds typed values for the known keys that
    passed, errors maps a key to a message. Unknown keys are reported, never
    stored.
    """
    clean, errors = {}, {}
    if not isinstance(payload, dict):
        return clean, {"_": "Expected a JSON object"}

    for key, raw in payload.items():
        if key not in DEFAULT_SETTINGS:
            errors[key] = "Unknown setting"
            continue

        if key in INT_RANGES:
            low, high = INT_RANGES[key]
            number = _parse_whole_number(raw)
            if number is None:
                errors[key] = "Must be a whole number"
            elif not low <= number <= high:
                errors[key] = f"Must be between {low} and {high}"
            else:
                clean[key] = number

        elif key == "debt_enabled":
            flag = _parse_bool(raw)
            if flag is None:
                errors[key] = "Must be true or false"
                continue
            clean[key] = flag

        elif key == "debt_start_date":
            text = "" if raw is None else str(raw).strip()
            if text:
                try:
                    datetime.strptime(text, "%Y-%m-%d")
                except ValueError:
                    errors[key] = "Must be a date like 2026-01-31"
                    continue
            clean[key] = text

        elif key == "timezone":
            text = "" if raw is None else str(raw).strip()
            if text and not _is_valid_timezone(text):
                errors[key] = "Not a known timezone name (e.g. Australia/Sydney)"
                continue
            clean[key] = text

    return clean, errors


def serialize_setting(key, value):
    """Typed value to the string stored in app_settings"""
    if key == "debt_enabled":
        return "1" if value else "0"
    return str(value)


def parse_settings(stored):
    """
    Typed settings from a {key: string} mapping of stored rows.

    Missing or malformed values fall back to the default, so a bad row can
    never break the pages that read it.
    """
    result = dict(DEFAULT_SETTINGS)
    for key, raw in (stored or {}).items():
        if key not in DEFAULT_SETTINGS or not isinstance(raw, str):
            continue
        clean, errors = validate_settings({key: raw})
        if not errors:
            result[key] = clean[key]
    return result


def zero_fill_history(rows, today, days):
    """
    One {date, review_count} entry per day for the last `days` days, ending
    today, oldest first. Days with no row count as 0.
    """
    counts = {}
    for row in rows:
        day = row["date"]
        if isinstance(day, datetime):
            day = day.date()
        counts[day] = row["review_count"] or 0

    return [
        {
            "date": (today - timedelta(days=offset)).strftime("%Y-%m-%d"),
            "review_count": counts.get(today - timedelta(days=offset), 0),
        }
        for offset in range(days - 1, -1, -1)
    ]


def calculate_debt(daily_counts, earliest_date, today, target, start_date=None):
    """
    Total debt and the last 20 days' breakdown, as /api/debt reports them.

    Every day before today adds (target - count): a miss adds debt, a surplus
    pays it down. Today's shortfall is not counted until the day ends; only
    today's surplus over the target is. The total can go below 0: that is a
    credit, banked surplus that later misses draw down.

    start_date, when set and later than earliest_date, ignores everything
    before it.
    """
    first = earliest_date
    if start_date and start_date > first:
        first = start_date

    total_debt = 0
    current = first
    while current < today:
        total_debt += target - daily_counts.get(current, 0)
        current += timedelta(days=1)

    today_count = daily_counts.get(today, 0)
    if today_count > target:
        total_debt -= today_count - target

    breakdown = []
    day = today - timedelta(days=1)
    for _ in range(20):
        if day < first:
            break
        breakdown.append(
            {
                "date": day.strftime("%Y-%m-%d"),
                "debt": target - daily_counts.get(day, 0),
            }
        )
        day -= timedelta(days=1)

    return total_debt, breakdown


def parse_start_date(text):
    """date for a stored debt_start_date string, or None for ''"""
    if not text:
        return None
    return datetime.strptime(text, "%Y-%m-%d").date()
