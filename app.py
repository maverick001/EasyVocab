"""
BKDict - Vocabulary Web Application
Main Flask application with REST API endpoints
Author: Built for vocabulary learning and management
"""

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    session,
    redirect,
    url_for,
)
from functools import wraps
import mysql.connector
from mysql.connector import pooling
import os
import requests
import platform
from werkzeug.utils import secure_filename
from config import Config
from utils import parse_and_import_xml, XMLParserError
from datetime import datetime, date, timedelta, timezone
from openai import OpenAI
from PIL import Image
import io
import time
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize Flask application
app = Flask(__name__)

app.config.from_object(Config)

# Initialize rate limiter for login protection
# 5 attempts per minute per IP - prevents brute force attacks
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],  # No default limit on other routes
    storage_uri="memory://",  # In-memory storage (resets on restart - OK for Vercel)
)

# Disable caching for development (prevents browser caching issues)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.after_request
def add_header(response):
    """Add headers to prevent caching"""
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response


# ============================================
# Password Protection
# ============================================


def login_required(f):
    """Decorator to require login for protected routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip if no password is set (allows open access during dev)
        if not app.config.get("SITE_PASSWORD"):
            return f(*args, **kwargs)
        # Check if user is logged in
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", error_message="Too many login attempts. Please wait a minute before trying again.")
def login():
    """Login page - checks password against SITE_PASSWORD env var"""
    # If no password set, redirect to main app
    if not app.config.get("SITE_PASSWORD"):
        return redirect(url_for("index"))

    # If already logged in, redirect to main app
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == app.config["SITE_PASSWORD"]:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Incorrect password. Please try again."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """Logout - clear session and redirect to login"""
    session.pop("logged_in", None)
    return redirect(url_for("login"))


# Initialize MySQL connection pool for better performance
db_pool = None


def init_db_pool():
    """
    Initialize MySQL connection pool
    Connection pooling improves performance for concurrent requests
    """
    global db_pool
    try:
        db_pool = pooling.MySQLConnectionPool(
            pool_name="bkdict_pool",
            pool_size=app.config["DB_POOL_SIZE"],
            pool_reset_session=True,
            host=app.config["DB_HOST"],
            port=app.config["DB_PORT"],
            user=app.config["DB_USER"],
            password=app.config["DB_PASSWORD"],
            database=app.config["DB_NAME"],
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
        )
        print("[OK] Database connection pool initialized successfully")
    except mysql.connector.Error as err:
        print(f"[ERROR] Error initializing database pool: {err}")
        raise


def get_db_connection():
    """
    Get a database connection from the pool

    Returns:
        MySQL connection object

    Raises:
        Exception if connection pool is not initialized
    """
    if db_pool is None:
        init_db_pool()
        # Schema is now managed by init_aiven_db.py and migrations
        # We no longer need to check this on every startup
    return db_pool.get_connection()


def ensure_word_history_table():
    """
    Ensure word_history table exists, create if it doesn't
    Also populates initial history from existing words
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Create word_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                word_id INT NOT NULL COMMENT 'Reference to words.id',
                word VARCHAR(255) NOT NULL COMMENT 'The word text at this point in time',
                translation TEXT NOT NULL COMMENT 'Translation at this point in time',
                example_sentence TEXT DEFAULT NULL COMMENT 'Example sentence at this point in time',
                category VARCHAR(100) NOT NULL COMMENT 'Category at this point in time',
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When this version was created',
                modification_type ENUM('created', 'updated', 'moved') NOT NULL DEFAULT 'updated' COMMENT 'Type of modification',

                INDEX idx_word_id (word_id),
                INDEX idx_modified_at (modified_at),
                INDEX idx_word_id_modified (word_id, modified_at DESC)
            ) ENGINE=InnoDB
            DEFAULT CHARSET=utf8mb4
            COLLATE=utf8mb4_unicode_ci
            COMMENT='Word modification history tracking'
        """)

        # Populate initial history from existing words (only if table was just created)
        cursor.execute("SELECT COUNT(*) FROM word_history")
        count = cursor.fetchone()[0]

        if count == 0:
            cursor.execute("""
                INSERT INTO word_history (word_id, word, translation, example_sentence, category, modified_at, modification_type)
                SELECT
                    id,
                    word,
                    translation,
                    example_sentence,
                    category,
                    created_at,
                    'created'
                FROM words
            """)
            connection.commit()
            print("[OK] Word history table initialized with existing words")

        cursor.close()
    except mysql.connector.Error as err:
        print(f"[ERROR] Error ensuring word_history table: {err}")
    finally:
        if connection:
            connection.close()


def ensure_image_file_column():
    """
    Ensure image_file column exists in words table
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Check if column exists
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'words'
            AND COLUMN_NAME = 'image_file'
        """,
            (app.config["DB_NAME"],),
        )

        if cursor.fetchone()[0] == 0:
            print("Adding image_file column to words table...")
            cursor.execute(
                "ALTER TABLE words ADD COLUMN image_file VARCHAR(255) DEFAULT NULL"
            )
            connection.commit()
            print(f"[OK] Image file column check completed")

        cursor.close()
    except mysql.connector.Error as err:
        print(f"[ERROR] Error ensuring image_file column: {err}")
    finally:
        if connection:
            connection.close()


def ensure_srs_columns():
    """
    Ensure SRS (Spaced Repetition System) columns exist in words table
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if columns exist
        cursor.execute("SHOW COLUMNS FROM words LIKE 'next_review_date'")
        if not cursor.fetchone():
            print("  + Adding next_review_date column...")
            cursor.execute(
                "ALTER TABLE words ADD COLUMN next_review_date DATETIME DEFAULT NULL"
            )

        cursor.execute("SHOW COLUMNS FROM words LIKE 'srs_interval'")
        if not cursor.fetchone():
            print("  + Adding srs_interval column...")
            cursor.execute("ALTER TABLE words ADD COLUMN srs_interval INT DEFAULT 0")

        cursor.execute("SHOW COLUMNS FROM words LIKE 'srs_repetitions'")
        if not cursor.fetchone():
            print("  + Adding srs_repetitions column...")
            cursor.execute("ALTER TABLE words ADD COLUMN srs_repetitions INT DEFAULT 0")

        cursor.execute("SHOW COLUMNS FROM words LIKE 'srs_ease_factor'")
        if not cursor.fetchone():
            print("  + Adding srs_ease_factor column...")
            cursor.execute(
                "ALTER TABLE words ADD COLUMN srs_ease_factor FLOAT DEFAULT 2.5"
            )

        conn.commit()
        print("[OK] SRS columns check completed")

    except Exception as e:
        print(f"[ERROR] Error checking SRS columns: {e}")
    finally:
        if conn:
            conn.close()


def create_history_record(
    cursor,
    word_id,
    word_text,
    translation,
    example_sentence,
    category,
    modification_type="updated",
):
    """
    Create a history record for a word modification

    Args:
        cursor: MySQL cursor object
        word_id: ID of the word being modified
        word_text: Current word text
        translation: Current translation
        example_sentence: Current example sentence
        category: Current category
        modification_type: Type of modification ('created', 'updated', 'moved')
    """
    cursor.execute(
        """
        INSERT INTO word_history (word_id, word, translation, example_sentence, category, modification_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """,
        (
            word_id,
            word_text,
            translation,
            example_sentence,
            category,
            modification_type,
        ),
    )


def allowed_file(filename):
    """
    Check if uploaded file has allowed extension

    Args:
        filename: Name of the uploaded file

    Returns:
        Boolean indicating if file type is allowed
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


def increment_daily_counter(cursor, word_id=None):
    """
    Increment the daily study counter in daily_study_log.
    Uses AEST timezone (UTC+10) for consistent date handling.

    If word_id is provided, checks if this word was already counted today
    to ensure only 1 increment per word per day.

    Args:
        cursor: MySQL cursor object
        word_id: Optional word ID for deduplication (None = always increment)

    Returns:
        Boolean indicating if increment was applied
    """
    # Use AEST timezone (UTC+10) for date
    AEST = timezone(timedelta(hours=10))
    today_aest = datetime.now(AEST).strftime("%Y-%m-%d")

    # If word_id provided, try to check if already counted today
    # Wrapped in try-except in case daily_word_reviews table doesn't exist yet
    if word_id is not None:
        try:
            cursor.execute(
                """
                SELECT 1 FROM daily_word_reviews 
                WHERE word_id = %s AND review_date = %s
            """,
                (word_id, today_aest),
            )

            if cursor.fetchone():
                # Already counted today
                return False

            # Mark this word as reviewed today
            cursor.execute(
                """
                INSERT INTO daily_word_reviews (word_id, review_date)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE review_date = review_date
            """,
                (word_id, today_aest),
            )
        except Exception:
            # Table doesn't exist yet - skip deduplication, just increment
            pass

    # Increment the daily counter
    cursor.execute(
        """
        INSERT INTO daily_study_log (date, review_count)
        VALUES (%s, 1)
        ON DUPLICATE KEY UPDATE review_count = review_count + 1
    """,
        (today_aest,),
    )

    return True


# ============================================
# Web Routes
# ============================================


@app.context_processor
def inject_env_info():
    """
    Inject environment information into all templates.
    Priority: ENV_TYPE (explicit) > Vercel detection > platform detection
    """
    # Explicit ENV_TYPE takes highest priority (set in Docker or Vercel dashboard)
    env_type = os.environ.get("ENV_TYPE")

    if env_type:
        return dict(env_type=env_type)

    # Check for Vercel-specific environment variables
    if (
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or os.environ.get("VERCEL_URL")
    ):
        return dict(env_type="Vercel")

    # Platform-based detection
    system = platform.system()
    if system == "Windows":
        return dict(env_type="Windows")
    elif system == "Linux":
        # Linux without explicit ENV_TYPE = Cloud deployment (Vercel, Railway, etc.)
        return dict(env_type="Cloud")
    else:
        return dict(env_type=system)


@app.route("/")
@login_required
def index():
    """
    Serve the main vocabulary web application page

    Returns:
        Rendered HTML template
    """
    return render_template("index.html")


@app.route("/quiz")
@login_required
def quiz():
    """
    Serve the quiz page

    Returns:
        Rendered HTML template
    """
    return render_template("quiz.html")


@app.route("/favicon.ico")
def favicon():
    """
    Serve favicon

    Returns:
        Favicon file or 404
    """
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


# ============================================
# API Endpoints
# ============================================


@app.route("/api/categories", methods=["GET"])
def get_categories():
    """
    Get list of all categories with word counts

    Returns:
        JSON response:
        {
            "success": true,
            "categories": [
                {"name": "文化", "word_count": 120},
                {"name": "AI", "word_count": 85},
                ...
            ]
        }
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query category statistics using the view
        cursor.execute("""
            SELECT category AS name, word_count, last_updated
            FROM category_stats
            ORDER BY category
        """)

        categories = cursor.fetchall()

        return jsonify({"success": True, "categories": categories})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/images", methods=["GET"])
def get_available_images():
    """
    Get list of available images in static/images/word_images

    Returns:
        JSON response with list of image filenames
    """
    try:
        images_dir = os.path.join(app.root_path, "static", "images", "word_images")

        # Try to create directory if it doesn't exist (fails on Vercel, which is fine)
        if not os.path.exists(images_dir):
            try:
                os.makedirs(images_dir)
            except Exception:
                pass  # Vercel is read-only, we just won't have the directory

        images = []
        for filename in os.listdir(images_dir):
            if allowed_file(filename):
                images.append(filename)

        return jsonify({"success": True, "images": sorted(images)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/words/<category>", methods=["GET"])
@app.route(
    "/api/words-query", methods=["GET"]
)  # Alternative endpoint for Vercel (uses ?category=)
def get_word_by_category(category=None):
    """
    Get a specific word from a category by index position

    Args:
        category: Category name (from URL path)

    Query Parameters:
        index: Position of word in category (0-based, default=0)
        sort_by: Sorting method - 'updated_at' (latest edits) or 'review_count' (most reviewed)
                 Default: 'updated_at'

    Returns:
        JSON response:
        {
            "success": true,
            "word": {
                "id": 123,
                "word": "example",
                "translation": "例子",
                "category": "文化",
                "sample_sentence": "This is an example.",
                "total_in_category": 120,
                "current_index": 0,
                "created_at": "2024-01-01 12:00:00",
                "updated_at": "2024-01-15 14:30:00"
            }
        }
    """
    conn = None
    try:
        # Get category from path param or query param (for Vercel compatibility)
        if category is None:
            category = request.args.get("category")
        if not category:
            return jsonify({"success": False, "error": "Category is required"}), 400

        # Get parameters from query string
        index = int(request.args.get("index", 0))
        sort_by = request.args.get("sort_by", "updated_at")  # Default to latest edits

        # Validate sort_by parameter
        if sort_by not in ["updated_at", "review_count", "updated_at_asc"]:
            sort_by = "updated_at"

        # Determine ORDER BY clause based on sort_by
        if sort_by == "updated_at":
            order_clause = "ORDER BY updated_at DESC, id DESC"
        elif sort_by == "updated_at_asc":
            order_clause = "ORDER BY updated_at ASC, id ASC"
        else:  # review_count
            order_clause = "ORDER BY review_count DESC, updated_at DESC, id DESC"

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get total count
        if category == "All":
            cursor.execute("SELECT COUNT(*) as total FROM words")
        else:
            cursor.execute(
                """
                SELECT COUNT(*) as total
                FROM words
                WHERE category = %s
            """,
                (category,),
            )

        count_result = cursor.fetchone()
        total_count = count_result["total"] if count_result else 0

        if total_count == 0:
            return jsonify({"success": False, "error": "No words found"}), 404

        # Ensure index is within bounds
        if index < 0:
            index = 0
        elif index >= total_count:
            index = total_count - 1

        # Get the word at the specified index
        if category == "All":
            query = f"""
                SELECT id, word, translation, category, example_sentence, image_file,
                       review_count, last_reviewed, created_at, updated_at
                FROM words
                {order_clause}
                LIMIT 1 OFFSET %s
            """
            cursor.execute(query, (index,))
        else:
            query = f"""
                SELECT id, word, translation, category, example_sentence, image_file,
                       review_count, last_reviewed, created_at, updated_at
                FROM words
                WHERE category = %s
                {order_clause}
                LIMIT 1 OFFSET %s
            """
            cursor.execute(query, (category, index))

        word = cursor.fetchone()

        if word:
            word["total_in_category"] = total_count
            word["current_index"] = index
            return jsonify({"success": True, "word": word})
        else:
            return jsonify({"success": False, "error": "Word not found"}), 404

    except ValueError:
        return jsonify({"success": False, "error": "Invalid index parameter"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words", methods=["POST"])
def add_word():
    """
    Add a new word to the database

    Request Body (JSON):
        {
            "word": "example",
            "translation": "示例",
            "example_sentence": "This is an example.\nAnother example.",  // optional
            "category": "日常词汇"
        }

    Returns:
        JSON response with success status and new word ID
    """
    conn = None
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Validate required fields
        word = data.get("word", "").strip()
        translation = data.get("translation", "").strip()
        category = data.get("category", "").strip()
        example_sentence = data.get("example_sentence", "").strip()

        if not word:
            return jsonify({"success": False, "error": "Word is required"}), 400

        if not translation:
            return jsonify({"success": False, "error": "Translation is required"}), 400

        if not category:
            return jsonify({"success": False, "error": "Category is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if word already exists in ANY category (global duplicate check)
        cursor.execute(
            """
            SELECT id, category FROM words
            WHERE word = %s
        """,
            (word,),
        )

        existing_word = cursor.fetchone()

        if existing_word:
            return jsonify(
                {
                    "success": False,
                    "error": f'Word "{word}" already exists in category "{existing_word["category"]}"',
                    "duplicate": True,
                    "existing_word_id": existing_word["id"],
                    "existing_category": existing_word["category"],
                }
            ), 409

        # Insert new word
        cursor.execute(
            """
            INSERT INTO words (word, translation, example_sentence, category, review_count, last_reviewed)
            VALUES (%s, %s, %s, %s, 2, NULL)
        """,
            (
                word,
                translation,
                example_sentence if example_sentence else None,
                category,
            ),
        )

        new_word_id = cursor.lastrowid

        # Create history record for new word
        create_history_record(
            cursor,
            new_word_id,
            word,
            translation,
            example_sentence if example_sentence else None,
            category,
            "created",
        )

        conn.commit()

        # Update category counts
        try:
            cursor.callproc("update_category_counts")

            # Increment daily review counter for the new word (AEST timezone)
            increment_daily_counter(cursor, new_word_id)

            conn.commit()
        except Exception:
            pass  # Non-critical

        return jsonify(
            {
                "success": True,
                "message": f'Word "{word}" added to category "{category}"',
                "word_id": new_word_id,
            }
        )

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words/search", methods=["GET"])
def search_words():
    """
    Search for words containing a specific sequence

    Query Parameters:
        q: Search query string (required)

    Returns:
        JSON response with matching words
    """
    conn = None
    try:
        query = request.args.get("q", "").strip()

        if not query:
            return jsonify({"success": False, "error": "Search query is required"}), 400

        if len(query) < 2:
            return jsonify(
                {
                    "success": False,
                    "error": "Search query must be at least 2 characters",
                }
            ), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Search for words containing the query in word OR translation
        # Prioritize matches in 'word' column over 'translation' column
        cursor.execute(
            """
            SELECT id, word, translation, category, review_count, example_sentence
            FROM words
            WHERE word LIKE %s OR translation LIKE %s
            ORDER BY 
                CASE 
                    WHEN word LIKE %s THEN 1 
                    ELSE 2 
                END,
                word ASC
            LIMIT 100
        """,
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        )

        results = cursor.fetchall()

        return jsonify(
            {"success": True, "query": query, "count": len(results), "results": results}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words/<int:word_id>/history", methods=["GET"])
def get_word_history(word_id):
    """
    Get modification history for a word

    Args:
        word_id: ID of the word (from URL path)

    Returns:
        JSON response with history records sorted by date (latest first)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get history records grouped by date (one record per day, latest from each day)
        cursor.execute(
            """
            SELECT
                id,
                word,
                translation,
                example_sentence,
                category,
                DATE(modified_at) as modified_date,
                modification_type
            FROM word_history
            WHERE word_id = %s
            AND id IN (
                SELECT MAX(id)
                FROM word_history
                WHERE word_id = %s
                GROUP BY DATE(modified_at)
            )
            ORDER BY modified_date DESC
        """,
            (word_id, word_id),
        )

        history_records = cursor.fetchall()

        # Convert date to string for JSON serialization
        for record in history_records:
            if record["modified_date"]:
                record["modified_date"] = record["modified_date"].strftime("%Y-%m-%d")

        return jsonify(
            {
                "success": True,
                "word_id": word_id,
                "count": len(history_records),
                "history": history_records,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words/<int:word_id>", methods=["GET"])
def get_word_details(word_id):
    """
    Get details for a specific word by ID, including uniqueness check
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get the word details
        cursor.execute(
            """
            SELECT id, word, translation, example_sentence, category, review_count, last_reviewed, image_file, created_at, updated_at
            FROM words
            WHERE id = %s
        """,
            (word_id,),
        )

        word = cursor.fetchone()

        if not word:
            return jsonify({"success": False, "error": "Word not found"}), 404

        # Check for other occurrences of the word string
        cursor.execute(
            """
            SELECT category
            FROM words
            WHERE word = %s AND id != %s
        """,
            (word["word"], word_id),
        )

        other_occurrences = cursor.fetchall()
        other_categories = [item["category"] for item in other_occurrences]

        return jsonify(
            {
                "success": True,
                "word": word,
                "other_categories": other_categories,
                "is_unique": len(other_categories) == 0,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words/<int:word_id>", methods=["PUT"])
def update_word(word_id):
    """
    Update word, translation, or example_sentence for a word

    Args:
        word_id: ID of the word to update (from URL path)

    Request Body (JSON):
        {
            "word": "updated word",                // optional
            "translation": "updated translation",  // optional
            "word": "updated word",                // optional
            "translation": "updated translation",  // optional
            "sample_sentence": "updated sentence", // optional
            "image_file": "image.png"              # optional
        }

    Returns:
        JSON response:
        {
            "success": true,
            "message": "Word updated successfully"
        }
    """
    conn = None
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # First, get the current word text and sample_sentence
        cursor.execute(
            "SELECT word, example_sentence, last_sample_review_date FROM words WHERE id = %s",
            (word_id,),
        )
        current_word_data = cursor.fetchone()

        if not current_word_data:
            return jsonify({"success": False, "error": "Word not found"}), 404

        current_word_text = current_word_data["word"]
        current_sample = current_word_data.get("example_sentence") or ""
        last_sample_date = current_word_data.get("last_sample_review_date")

        # Update fields across ALL instances of this word
        shared_update_fields = []
        shared_params = []

        if "image_file" in data:
            shared_update_fields.append("image_file = %s")
            # Handle empty string or null to remove image
            image_val = data["image_file"].strip() if data["image_file"] else None
            shared_params.append(image_val)

        if "translation" in data or "example_sentence" in data:
            if "translation" in data:
                shared_update_fields.append("translation = %s")
                shared_params.append(data["translation"])

            if "example_sentence" in data:
                new_sample = data["example_sentence"] or ""

                shared_update_fields.append("example_sentence = %s")
                shared_params.append(data["example_sentence"])

                # Check if sample sentence actually changed to trigger review increment
                if new_sample.strip() != current_sample.strip():
                    # Check daily cap
                    today = date.today()

                    if last_sample_date != today:
                        shared_update_fields.append("review_count = review_count + 1")
                        shared_update_fields.append("last_reviewed = NOW()")
                        shared_update_fields.append(
                            "last_sample_review_date = CURDATE()"
                        )

        if shared_update_fields:
            # Update ALL rows with the same word text
            shared_params.append(current_word_text)
            shared_update_query = f"""
                UPDATE words
                SET {", ".join(shared_update_fields)}
                WHERE word = %s
            """
            cursor.execute(shared_update_query, shared_params)

        # Update the word text itself only for this specific row
        if "word" in data:
            cursor.execute(
                """
                UPDATE words
                SET word = %s
                WHERE id = %s
            """,
                (data["word"], word_id),
            )

        # Get the updated word data for history record
        cursor.execute(
            """
            SELECT word, translation, example_sentence, category
            FROM words
            WHERE id = %s
        """,
            (word_id,),
        )
        updated_word = cursor.fetchone()

        # Create history record
        create_history_record(
            cursor,
            word_id,
            updated_word["word"],
            updated_word["translation"],
            updated_word["example_sentence"],
            updated_word["category"],
            "updated",
        )

        # Log daily review activity for edits (AEST timezone, 1 per word per day)
        increment_daily_counter(cursor, word_id)

        conn.commit()

        return jsonify({"success": True, "message": "Word updated successfully"})

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words/<int:word_id>/category", methods=["PUT"])
def change_word_category(word_id):
    """
    Move a word to a different category (or add to additional category)

    Note: Each word can exist in multiple categories, but shares one translation and sample sentence.
    This endpoint moves the word by creating it in the new category and removing it from the current category.

    Args:
        word_id: ID of the word to update (from URL path)

    Request Body (JSON):
        {
            "new_category": "AI"
        }

    Returns:
        JSON response with success status
    """
    conn = None
    try:
        data = request.get_json()

        if not data or "new_category" not in data:
            return jsonify({"success": False, "error": "new_category is required"}), 400

        new_category = data["new_category"].strip()

        if not new_category:
            return jsonify({"success": False, "error": "Category cannot be empty"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get current word information
        cursor.execute(
            """
            SELECT word, translation, example_sentence, category, review_count, last_reviewed
            FROM words
            WHERE id = %s
        """,
            (word_id,),
        )

        current_word = cursor.fetchone()

        if not current_word:
            return jsonify({"success": False, "error": "Word not found"}), 404

        # Check if word already exists in target category
        cursor.execute(
            """
            SELECT id FROM words
            WHERE word = %s AND category = %s
        """,
            (current_word["word"], new_category),
        )

        existing_word = cursor.fetchone()

        if existing_word:
            # Word already exists in target category - return error with special flag
            return jsonify(
                {
                    "success": False,
                    "error": f'Word "{current_word["word"]}" already exists in category "{new_category}"',
                    "duplicate": True,
                }
            ), 409

        # Word doesn't exist in target category - perform the move
        # Update category directly to preserve ID and last_daily_activity_date
        cursor.execute(
            "UPDATE words SET category = %s WHERE id = %s", (new_category, word_id)
        )

        # Create history record for the moved word
        create_history_record(
            cursor,
            word_id,
            current_word["word"],
            current_word["translation"],
            current_word["example_sentence"],
            new_category,
            "moved",
        )

        conn.commit()

        # Update category counts
        try:
            cursor.callproc("update_category_counts")
            conn.commit()
        except Exception:
            pass  # Non-critical

        return jsonify(
            {"success": True, "message": f'Word moved to category "{new_category}"'}
        )

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words/<int:word_id>", methods=["DELETE"])
def delete_word(word_id):
    """
    Delete a word from the database

    Query Parameters:
        scope: 'current_category' (default) or 'all_categories'
               - current_category: Delete only from current category
               - all_categories: Delete from all categories

    Args:
        word_id: ID of the word to delete (from URL path)

    Returns:
        JSON response with success status
        If word exists in multiple categories and scope is not specified,
        returns a special response requesting user confirmation
    """
    conn = None
    try:
        scope = request.args.get("scope", None)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # First, get the current word information
        cursor.execute(
            """
            SELECT word, category
            FROM words
            WHERE id = %s
        """,
            (word_id,),
        )

        current_word = cursor.fetchone()

        if not current_word:
            return jsonify({"success": False, "error": "Word not found"}), 404

        # Check if this word exists in other categories
        cursor.execute(
            """
            SELECT category
            FROM words
            WHERE word = %s AND id != %s
        """,
            (current_word["word"], word_id),
        )

        other_categories = cursor.fetchall()

        # If word exists in other categories and no scope specified, ask user
        if other_categories and scope is None:
            category_list = [cat["category"] for cat in other_categories]
            return jsonify(
                {
                    "success": False,
                    "requires_confirmation": True,
                    "word": current_word["word"],
                    "current_category": current_word["category"],
                    "other_categories": category_list,
                    "message": f'Word "{current_word["word"]}" also exists in {len(category_list)} other categor{"y" if len(category_list) == 1 else "ies"}',
                }
            ), 200

        # Perform deletion based on scope
        if scope == "all_categories":
            # Delete all instances of this word across all categories
            cursor.execute("DELETE FROM words WHERE word = %s", (current_word["word"],))
            rows_affected = cursor.rowcount
            message = f'Word "{current_word["word"]}" deleted from all categories'
        else:
            # Delete only from current category (default behavior)
            cursor.execute("DELETE FROM words WHERE id = %s", (word_id,))
            rows_affected = cursor.rowcount
            message = f'Word "{current_word["word"]}" deleted from category "{current_word["category"]}"'

        conn.commit()

        # Update category counts and log daily activity
        try:
            cursor.callproc("update_category_counts")
            # Log daily review activity for deletes (AEST timezone, 1 per word per day)
            increment_daily_counter(cursor, word_id)
            conn.commit()
        except Exception:
            pass  # Non-critical

        if rows_affected > 0:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "error": "Word not found"}), 404

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words/<int:word_id>/review", methods=["POST"])
def increment_review_counter(word_id):
    """
    Increment the review counter for a word and update last_reviewed and edit time

    Args:
        word_id: ID of the word to update (from URL path)

    Returns:
        JSON response with updated review_count
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Increment review_count and update last_reviewed and updated_at timestamps
        cursor.execute(
            """
            UPDATE words
            SET review_count = review_count + 1,
                last_reviewed = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """,
            (word_id,),
        )

        # Get updated word data for history
        cursor.execute(
            """
            SELECT word, translation, example_sentence, category, review_count, last_reviewed
            FROM words
            WHERE id = %s
        """,
            (word_id,),
        )

        result = cursor.fetchone()

        if result:
            # Create history record for review
            create_history_record(
                cursor,
                word_id,
                result["word"],
                result["translation"],
                result["example_sentence"],
                result["category"],
                "updated",
            )

            # Log daily review activity (AEST timezone, 1 per word per day)
            increment_daily_counter(cursor, word_id)

            conn.commit()

            return jsonify(
                {
                    "success": True,
                    "review_count": result["review_count"],
                    "last_reviewed": str(result["last_reviewed"])
                    if result["last_reviewed"]
                    else None,
                }
            )
        else:
            return jsonify({"success": False, "error": "Word not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/debt", methods=["GET"])
def get_word_debt():
    """
    Calculate and return total word debt and daily breakdown
    Debt = 100 - review_count for each day
    - Days with no activity get +100 debt
    - Days exceeding 100 get negative debt (surplus)
    - Today's deficit is not counted until the day ends
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get the earliest date from the database
        cursor.execute("""
            SELECT MIN(date) as earliest_date
            FROM daily_study_log
        """)
        result = cursor.fetchone()

        if not result or not result["earliest_date"]:
            # No records at all
            return jsonify({"success": True, "total_debt": 0, "breakdown": []})

        earliest_date = result["earliest_date"]
        if isinstance(earliest_date, datetime):
            earliest_date = earliest_date.date()

        # Get all daily logs as a dictionary for fast lookup
        cursor.execute("""
            SELECT date, review_count
            FROM daily_study_log
        """)
        logs = cursor.fetchall()

        # Create a lookup dictionary: date -> review_count
        daily_counts = {}
        for log in logs:
            log_date = log["date"]
            if isinstance(log_date, datetime):
                log_date = log_date.date()
            daily_counts[log_date] = log["review_count"]

        # Use AEST timezone (UTC+10) for consistent date handling
        AEST = timezone(timedelta(hours=10))
        today = datetime.now(AEST).date()
        total_debt = 0
        debt_breakdown = []

        # Iterate through every day from earliest_date to yesterday
        current_date = earliest_date
        while current_date < today:  # Exclude today
            count = daily_counts.get(current_date, 0)  # Default to 0 if no record

            # Deficit increases debt, surplus decreases debt
            daily_debt = 100 - count
            total_debt += daily_debt

            current_date += timedelta(days=1)

        # Handle today separately: only apply surplus if > 100
        today_count = daily_counts.get(today, 0)
        if today_count > 100:
            total_debt -= today_count - 100

        # Ensure total debt doesn't go below 0
        if total_debt < 0:
            total_debt = 0

        # Build breakdown for the past 20 days (starting from YESTERDAY, not today)
        # Today is excluded since user is still reviewing
        breakdown_date = today - timedelta(days=1)  # Start from yesterday
        for i in range(20):
            if breakdown_date < earliest_date:
                break

            count = daily_counts.get(breakdown_date, 0)
            daily_debt = 100 - count
            debt_breakdown.append(
                {"date": breakdown_date.strftime("%Y-%m-%d"), "debt": daily_debt}
            )

            breakdown_date -= timedelta(days=1)

        return jsonify(
            {"success": True, "total_debt": total_debt, "breakdown": debt_breakdown}
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/daily-count", methods=["GET"])
def get_daily_count():
    """
    Get today's word review count from the database
    This ensures the daily counter is consistent across all browsers

    Returns:
        JSON response:
        {
            "success": true,
            "count": 45
        }
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT review_count 
            FROM daily_study_log 
            WHERE date = CURDATE()
        """)
        result = cursor.fetchone()

        count = result["review_count"] if result else 0

        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


import re

# ... existing code ...


def clean_poe_response(text):
    """
    Remove "Thinking..." blocks from Poe/Gemini output.
    Strategy:
    1. Identify the *last* line that looks like a blockquote (>).
    2. Discard everything up to that line.
    3. Also handle cases where only the *Thinking...* header exists without quotes.
    4. If no thinking artifacts found, return original text.
    """
    if not text:
        return ""

    lines = text.strip().split("\n")

    # 1. Find the index of the LAST line that starts with '>'
    last_quote_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith(">"):
            last_quote_index = i

    # 2. Determine start index for content
    start_index = 0
    if last_quote_index != -1:
        # Content starts after the last quote
        start_index = last_quote_index + 1

    # Extract the candidate content
    candidate_lines = lines[start_index:]

    # 3. Check if the FIRST remaining line is a "Thinking..." header
    # (This handles case where there were no quotes, OR if the Thinking header was somehow after quotes logic??
    # Actually, mainly for case where there are NO quotes but there IS a *Thinking...* line)
    if candidate_lines:
        first_line = candidate_lines[0].strip()
        # Matches *Thinking...*, **Thinking...**, Thinking...
        # Also handle potential italics/bold markers
        if re.match(r"^[\s\*]*Thinking\.\.\.[\s\*]*$", first_line, re.IGNORECASE):
            candidate_lines = candidate_lines[1:]

    # 4. Filter out leading empty lines from the result
    final_lines = []
    has_content_started = False
    for line in candidate_lines:
        if not has_content_started and not line.strip():
            continue
        has_content_started = True
        final_lines.append(line)

    return "\n".join(final_lines).strip()


@app.route("/api/generate-sample", methods=["POST"])
def generate_sample_sentence():
    """
    Generate a example sentence using Poe API (OpenAI-compatible)

    Request Body (JSON):
        {
            "word": "example"
        }

    Returns:
        JSON response with generated sentence
    """
    try:
        data = request.get_json()

        if not data or "word" not in data:
            return jsonify({"success": False, "error": "Word is required"}), 400

        word = data["word"].strip()
        # Get model from request, fallback to config default
        model = data.get("model", app.config["POE_MODEL"])

        if not word:
            return jsonify({"success": False, "error": "Word cannot be empty"}), 400

        # Check Poe API Key
        if not app.config["POE_API_KEY"]:
            return jsonify(
                {
                    "success": False,
                    "error": "Poe API Key not configured. Please set POE_API_KEY in .env file.",
                }
            ), 500

        # Initialize OpenAI client with Poe API endpoint
        client = OpenAI(
            api_key=app.config["POE_API_KEY"], base_url="https://api.poe.com/v1/"
        )

        # Prepare prompt
        prompt = f'Create a simple, natural English sentence that uses the EXACT word or phrase "{word}" (including all words as shown). You must use "{word}" exactly as written, not variations or partial matches. Use simple language and vocabulary suitable for a high school student. Keep the sentence short and easy to understand. Only output the sentence, nothing else.'

        # Call Poe API via OpenAI SDK
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=app.config.get("POE_TEMPERATURE", 0.7),
        )

        if response.choices and response.choices[0].message.content:
            raw_content = response.choices[0].message.content.strip()
            # Clean up potential thinking process output
            generated_sentence = clean_poe_response(raw_content)

            return jsonify({"success": True, "sentence": generated_sentence})
        else:
            return jsonify(
                {"success": False, "error": "Poe returned empty response"}
            ), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate-translation", methods=["POST"])
def generate_translation():
    """
    Generate Chinese translation for a word using Poe API (OpenAI-compatible)
    Also supports reverse generation (Chinese -> English) via 'mode' parameter.

    Request Body (JSON):
        {
            "word": "example",
            "model": "Claude-Haiku-4.5",  # optional
            "mode": "normal" | "reverse"  # optional, default "normal"
        }

    Returns:
        JSON response with generated text in 'translation' field
    """
    try:
        data = request.get_json()

        if not data or "word" not in data:
            return jsonify({"success": False, "error": "Word/Text is required"}), 400

        word = data["word"].strip()
        # Get model from request, fallback to config default
        model = data.get("model", app.config["POE_MODEL"])
        mode = data.get("mode", "normal")

        if not word:
            return jsonify({"success": False, "error": "Text cannot be empty"}), 400

        # Check Poe API Key
        if not app.config["POE_API_KEY"]:
            return jsonify(
                {
                    "success": False,
                    "error": "Poe API Key not configured. Please set POE_API_KEY in .env file.",
                }
            ), 500

        # Initialize OpenAI client with Poe API endpoint
        client = OpenAI(
            api_key=app.config["POE_API_KEY"], base_url="https://api.poe.com/v1/"
        )

        # Prepare prompt based on mode
        if mode == "reverse":
            # Chinese -> English
            prompt = f"What is the English translation for the Chinese word '{word}'? Only list the 2 most common English words or short phrases. Separate them with a Chinese comma (，). Do not include any other explanations. Ensure both words begin with lowercase letters."
        else:
            # English -> Chinese
            prompt = f"What's the Chinese translation of '{word}'? Only list the 2 most common translations and ignore others. Separate them with a Chinese comma (，). Only list the translations in Chinese characters, no other explanations or phonetics are needed."

        # Call Poe API via OpenAI SDK
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=app.config.get("POE_TEMPERATURE", 0.7),
        )

        if response.choices and response.choices[0].message.content:
            raw_content = response.choices[0].message.content.strip()
            # Clean up potential thinking process output
            generated_text = clean_poe_response(raw_content)

            return jsonify({"success": True, "translation": generated_text})
        else:
            return jsonify(
                {"success": False, "error": "Poe returned empty response"}
            ), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/category/<category>/count", methods=["GET"])
def get_category_count(category):
    """
    Get total word count for a specific category

    Args:
        category: Category name (from URL path)

    Returns:
        JSON response:
        {
            "success": true,
            "category": "文化",
            "count": 120
        }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM words
            WHERE category = %s
        """,
            (category,),
        )

        result = cursor.fetchone()
        count = result["count"] if result else 0

        cursor.close()
        conn.close()

        return jsonify({"success": True, "category": category, "count": count})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/quiz/next-word", methods=["GET"])
def get_next_quiz_word():
    """
    Get the next word for quiz (oldest updated word with review_count >= 1)

    Query Parameters:
        category: Filter by specific category (optional) (default: 'All')

    Returns:
        JSON response with word data
    """
    conn = None
    try:
        category = request.args.get("category", "All")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Base query
        query = """
            SELECT id, word, translation, example_sentence, review_count, category, next_review_date, srs_interval
            FROM words
            WHERE review_count >= 1
        """
        params = []

        # Add category filter if not 'All'
        if category and category != "All":
            query += " AND category = %s"
            params.append(category)

        # Add SRS logic: Prioritize overdue items (next_review_date <= NOW)
        query += " AND (next_review_date <= NOW() OR next_review_date IS NULL)"

        # Add ordering and limit
        query += """
            ORDER BY 
                CASE WHEN next_review_date IS NULL THEN 1 ELSE 0 END, -- Null dates last
                next_review_date ASC, -- Overdue first
                updated_at ASC -- Tie breaker
            LIMIT 1
        """

        cursor.execute(query, params)
        word = cursor.fetchone()

        if not word:
            return jsonify(
                {
                    "success": False,
                    "error": "No words found for review in this category.",
                    "word": None,
                }
            ), 404

        return jsonify({"success": True, "word": word})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/quiz/result", methods=["POST"])
def submit_quiz_result():
    """
    Submit quiz result for a word

    Request Body:
        {
            "word_id": 123,
            "result": "remember" | "not_remember"
        }
    """
    conn = None
    try:
        data = request.get_json()

        if not data or "word_id" not in data or "result" not in data:
            return jsonify(
                {"success": False, "error": "Missing word_id or result"}
            ), 400

        word_id = data["word_id"]
        result = data["result"]

        if result not in ["remember", "not_remember"]:
            return jsonify({"success": False, "error": "Invalid result value"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get current SRS state
        cursor.execute(
            """
            SELECT review_count, srs_interval, srs_repetitions, srs_ease_factor 
            FROM words WHERE id = %s
        """,
            (word_id,),
        )
        word = cursor.fetchone()

        if not word:
            return jsonify({"success": False, "error": "Word not found"}), 404

        current_count = word["review_count"]

        # SRS Algorithm (Simplified SM-2)
        interval = word["srs_interval"] or 0
        repetitions = word["srs_repetitions"] or 0
        ease_factor = word["srs_ease_factor"] or 2.5

        if result == "remember":
            # Correct answer
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = int(interval * ease_factor)

            repetitions += 1
            # Update review count (legacy metric: DECREMENT to reduce debt)
            new_count = max(0, current_count - 1)

        else:
            # Incorrect answer
            repetitions = 0
            interval = 0
            # Decrease ease factor slightly for difficult words (min 1.3)
            ease_factor = max(1.3, ease_factor - 0.15)
            # Legacy metric: INCREMENT to increase debt
            new_count = current_count + 1

        # Calculate next review date
        if interval == 0:
            # Re-queue immediately (or very short delay like 1 min, but for now just NOW)
            next_review = datetime.now()
        else:
            next_review = datetime.now() + timedelta(days=interval)

        # Update word with new SRS data
        cursor.execute(
            """
            UPDATE words 
            SET review_count = %s,
                updated_at = CURRENT_TIMESTAMP,
                last_reviewed = CURRENT_TIMESTAMP,
                srs_interval = %s,
                srs_repetitions = %s,
                srs_ease_factor = %s,
                next_review_date = %s
            WHERE id = %s
        """,
            (new_count, interval, repetitions, ease_factor, next_review, word_id),
        )

        conn.commit()

        return jsonify(
            {
                "success": True,
                "word_id": word_id,
                "old_count": current_count,
                "new_count": new_count,
                "srs": {
                    "interval": interval,
                    "repetitions": repetitions,
                    "next_review": next_review.isoformat(),
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/upload", methods=["POST"])
def upload_xml():
    """
    Upload and import XML vocabulary file

    Request:
        multipart/form-data with 'file' field containing XML file

    Returns:
        JSON response:
        {
            "success": true,
            "stats": {
                "total_processed": 500,
                "added": 450,
                "skipped_duplicates": 50,
                "errors": 0
            },
            "message": "Import completed: 450 words added, 50 duplicates skipped"
        }
    """
    try:
        # Check if file is in request
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files["file"]

        # Check if filename is empty
        if file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Validate file type
        if not allowed_file(file.filename):
            return jsonify(
                {
                    "success": False,
                    "error": "Invalid file type. Only XML files are allowed.",
                }
            ), 400

        # Save file securely
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Parse and import XML
        conn = None
        try:
            conn = get_db_connection()
            stats = parse_and_import_xml(
                filepath, conn, batch_size=app.config["XML_BATCH_SIZE"]
            )

            # Clean up uploaded file
            os.remove(filepath)

            # Build response message
            message = f"Import completed: {stats['added']} words added"
            if stats["skipped_duplicates"] > 0:
                message += f", {stats['skipped_duplicates']} duplicates skipped"
            if stats["errors"] > 0:
                message += f", {stats['errors']} errors encountered"

            return jsonify({"success": True, "stats": stats, "message": message})

        except XMLParserError as e:
            # Clean up uploaded file on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify(
                {"success": False, "error": f"XML parsing error: {str(e)}"}
            ), 400
        finally:
            if conn:
                conn.close()

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# Application Initialization
# ============================================


@app.route("/api/words/<int:word_id>/position", methods=["GET"])
def get_word_position(word_id):
    """
    Get the index/position of a word within its category based on sort order

    Query Parameters:
        sort_by: Sort criteria (default: 'updated_at')

    Returns:
        JSON response with index, total_count, and category
    """
    conn = None
    try:
        sort_by = request.args.get("sort_by", "updated_at")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # First get the word's category
        cursor.execute("SELECT category FROM words WHERE id = %s", (word_id,))
        word_data = cursor.fetchone()

        if not word_data:
            return jsonify({"success": False, "error": "Word not found"}), 404

        category = word_data["category"]

        # Determine sort order
        order_clause = "updated_at DESC, id DESC"
        if sort_by == "review_count":
            order_clause = "review_count DESC, updated_at DESC, id DESC"
        elif sort_by == "updated_at_asc":
            order_clause = "updated_at ASC, id ASC"

        # Get all IDs in this category with the same sort order
        query = f"""
            SELECT id 
            FROM words 
            WHERE category = %s 
            ORDER BY {order_clause}
        """

        cursor.execute(query, (category,))
        all_words = cursor.fetchall()

        # Find index
        index = -1
        for i, w in enumerate(all_words):
            if w["id"] == word_id:
                index = i
                break

        if index == -1:
            return jsonify(
                {"success": False, "error": "Word not found in category list"}
            ), 500

        return jsonify(
            {
                "success": True,
                "index": index,
                "total_count": len(all_words),
                "category": category,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/words/<int:word_id>/image", methods=["POST"])
def upload_word_image(word_id):
    """
    Upload and process an image for a specific word

    1. Resizes image to 256x256
    2. Saves to static/images/word_images with unique name
    3. Updates database
    """
    conn = None
    try:
        if "image" not in request.files:
            return jsonify({"success": False, "error": "No image file provided"}), 400

        file = request.files["image"]

        if file.filename == "":
            return jsonify({"success": False, "error": "No selected file"}), 400

        if file:
            # Process image using Pillow
            try:
                # Open image from stream
                img = Image.open(file.stream)

                # Convert to RGB (required for JPEG)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Compress to ensure size < 500KB without resizing dimensions
                output_buffer = io.BytesIO()
                quality = 95
                img.save(output_buffer, format="JPEG", quality=quality)

                while output_buffer.tell() > 500 * 1024 and quality > 10:
                    output_buffer.seek(0)
                    output_buffer.truncate()
                    quality -= 5
                    img.save(output_buffer, format="JPEG", quality=quality)

                # Generate unique filename (using .jpg now)
                timestamp = int(time.time())
                filename = f"img_{word_id}_{timestamp}.jpg"
                save_path = os.path.join(
                    app.root_path, "static", "images", "word_images", filename
                )

                # Ensure directory exists
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                # Write to file
                with open(save_path, "wb") as f:
                    f.write(output_buffer.getvalue())

                # Update Database
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)

                # Get old image to delete later (optional cleanup)
                cursor.execute(
                    "SELECT image_file, word FROM words WHERE id = %s", (word_id,)
                )
                word_data = cursor.fetchone()

                if not word_data:
                    return jsonify({"success": False, "error": "Word not found"}), 404

                # Update word record
                cursor.execute(
                    "UPDATE words SET image_file = %s WHERE id = %s",
                    (filename, word_id),
                )
                conn.commit()

                return jsonify(
                    {
                        "success": True,
                        "message": "Image uploaded and processed",
                        "filename": filename,
                    }
                )

            except Exception as e:
                return jsonify(
                    {"success": False, "error": f"Image processing failed: {str(e)}"}
                ), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()


def create_app():
    """
    Application factory function

    Returns:
        Configured Flask application instance
    """
    Config.init_app(app)
    init_db_pool()
    return app


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize database connection pool
    init_db_pool()
    ensure_word_history_table()
    ensure_image_file_column()
    ensure_srs_columns()

    print(f"[START] BKDict application starting on {platform.system()}...")

    # Run Flask development server
    print("\n" + "=" * 50)
    print("  BKDict Vocabulary Web Application")
    print("=" * 50)
    print(f"  [URL] Server running on: http://localhost:5001")
    print(f"  [DB] Database: {app.config['DB_NAME']}")
    print(f"  [DEBUG] Debug mode: {app.config['DEBUG']}")
    print("=" * 50 + "\n")

    app.run(host="0.0.0.0", port=5001, debug=app.config["DEBUG"])
