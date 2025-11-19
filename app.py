"""
BKDict - Vocabulary Web Application
Main Flask application with REST API endpoints
Author: Built for vocabulary learning and management
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import mysql.connector
from mysql.connector import pooling
import os
import requests
from werkzeug.utils import secure_filename
from config import Config
from utils import parse_and_import_xml, XMLParserError

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)

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
            pool_size=app.config['DB_POOL_SIZE'],
            pool_reset_session=True,
            host=app.config['DB_HOST'],
            port=app.config['DB_PORT'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD'],
            database=app.config['DB_NAME'],
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        print("✓ Database connection pool initialized successfully")
    except mysql.connector.Error as err:
        print(f"✗ Error initializing database pool: {err}")
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
        raise Exception("Database pool not initialized")
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
                sample_sentence TEXT DEFAULT NULL COMMENT 'Sample sentence at this point in time',
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
            """)
            connection.commit()
            print("✓ Word history table initialized with existing words")

        cursor.close()
    except mysql.connector.Error as err:
        print(f"✗ Error ensuring word_history table: {err}")
    finally:
        if connection:
            connection.close()


def create_history_record(cursor, word_id, word_text, translation, sample_sentence, category, modification_type='updated'):
    """
    Create a history record for a word modification

    Args:
        cursor: MySQL cursor object
        word_id: ID of the word being modified
        word_text: Current word text
        translation: Current translation
        sample_sentence: Current sample sentence
        category: Current category
        modification_type: Type of modification ('created', 'updated', 'moved')
    """
    cursor.execute("""
        INSERT INTO word_history (word_id, word, translation, sample_sentence, category, modification_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (word_id, word_text, translation, sample_sentence, category, modification_type))


def allowed_file(filename):
    """
    Check if uploaded file has allowed extension

    Args:
        filename: Name of the uploaded file

    Returns:
        Boolean indicating if file type is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# ============================================
# Web Routes
# ============================================

@app.route('/')
def index():
    """
    Serve the main vocabulary web application page

    Returns:
        Rendered HTML template
    """
    return render_template('index.html')


@app.route('/quiz')
def quiz():
    """
    Serve the quiz page

    Returns:
        Rendered HTML template
    """
    return render_template('quiz.html')


@app.route('/favicon.ico')
def favicon():
    """
    Serve favicon

    Returns:
        Favicon file or 404
    """
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


# ============================================
# API Endpoints
# ============================================

@app.route('/api/categories', methods=['GET'])
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

        return jsonify({
            'success': True,
            'categories': categories
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/words/<category>', methods=['GET'])
def get_word_by_category(category):
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
        # Get parameters from query string
        index = int(request.args.get('index', 0))
        sort_by = request.args.get('sort_by', 'updated_at')  # Default to latest edits

        # Validate sort_by parameter
        if sort_by not in ['updated_at', 'review_count']:
            sort_by = 'updated_at'

        # Determine ORDER BY clause based on sort_by
        if sort_by == 'updated_at':
            order_clause = "ORDER BY updated_at DESC, id DESC"
        else:  # review_count
            order_clause = "ORDER BY review_count DESC, updated_at DESC, id DESC"

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get total count in category
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM words
            WHERE category = %s
        """, (category,))

        count_result = cursor.fetchone()
        total_count = count_result['total'] if count_result else 0

        if total_count == 0:
            return jsonify({
                'success': False,
                'error': 'No words found in this category'
            }), 404

        # Ensure index is within bounds
        if index < 0:
            index = 0
        elif index >= total_count:
            index = total_count - 1

        # Get the word at the specified index
        # Using LIMIT with OFFSET for pagination with dynamic sorting
        query = f"""
            SELECT id, word, translation, category, sample_sentence,
                   review_count, last_reviewed, created_at, updated_at
            FROM words
            WHERE category = %s
            {order_clause}
            LIMIT 1 OFFSET %s
        """
        cursor.execute(query, (category, index))

        word = cursor.fetchone()

        if word:
            word['total_in_category'] = total_count
            word['current_index'] = index
            return jsonify({
                'success': True,
                'word': word
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Word not found'
            }), 404

    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid index parameter'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/words', methods=['POST'])
def add_word():
    """
    Add a new word to the database

    Request Body (JSON):
        {
            "word": "example",
            "translation": "示例",
            "sample_sentence": "This is an example.\nAnother example.",  // optional
            "category": "日常词汇"
        }

    Returns:
        JSON response with success status and new word ID
    """
    conn = None
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate required fields
        word = data.get('word', '').strip()
        translation = data.get('translation', '').strip()
        category = data.get('category', '').strip()
        sample_sentence = data.get('sample_sentence', '').strip()

        if not word:
            return jsonify({
                'success': False,
                'error': 'Word is required'
            }), 400

        if not translation:
            return jsonify({
                'success': False,
                'error': 'Translation is required'
            }), 400

        if not category:
            return jsonify({
                'success': False,
                'error': 'Category is required'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if word already exists in this category
        cursor.execute("""
            SELECT id FROM words
            WHERE word = %s AND category = %s
        """, (word, category))

        existing_word = cursor.fetchone()

        if existing_word:
            return jsonify({
                'success': False,
                'error': f'Word "{word}" already exists in category "{category}"',
                'duplicate': True
            }), 409

        # Insert new word
        cursor.execute("""
            INSERT INTO words (word, translation, sample_sentence, category, review_count, last_reviewed)
            VALUES (%s, %s, %s, %s, 0, NULL)
        """, (word, translation, sample_sentence if sample_sentence else None, category))

        new_word_id = cursor.lastrowid

        # Create history record for new word
        create_history_record(
            cursor,
            new_word_id,
            word,
            translation,
            sample_sentence if sample_sentence else None,
            category,
            'created'
        )

        conn.commit()

        # Update category counts
        try:
            cursor.callproc('update_category_counts')
            conn.commit()
        except Exception:
            pass  # Non-critical

        return jsonify({
            'success': True,
            'message': f'Word "{word}" added to category "{category}"',
            'word_id': new_word_id
        })

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/words/search', methods=['GET'])
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
        query = request.args.get('q', '').strip()

        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400

        if len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Search query must be at least 2 characters'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Search for words containing the query (case-insensitive)
        cursor.execute("""
            SELECT id, word, translation, category, review_count, sample_sentence
            FROM words
            WHERE word LIKE %s
            ORDER BY word ASC
            LIMIT 100
        """, (f'%{query}%',))

        results = cursor.fetchall()

        return jsonify({
            'success': True,
            'query': query,
            'count': len(results),
            'results': results
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/words/<int:word_id>/history', methods=['GET'])
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
        cursor.execute("""
            SELECT
                id,
                word,
                translation,
                sample_sentence,
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
        """, (word_id, word_id))

        history_records = cursor.fetchall()

        # Convert date to string for JSON serialization
        for record in history_records:
            if record['modified_date']:
                record['modified_date'] = record['modified_date'].strftime('%Y-%m-%d')

        return jsonify({
            'success': True,
            'word_id': word_id,
            'count': len(history_records),
            'history': history_records
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/words/<int:word_id>', methods=['PUT'])
def update_word(word_id):
    """
    Update word, translation, or sample sentence for a word

    Args:
        word_id: ID of the word to update (from URL path)

    Request Body (JSON):
        {
            "word": "updated word",                // optional
            "translation": "updated translation",  // optional
            "sample_sentence": "updated sentence"  // optional
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
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # First, get the current word text
        cursor.execute("SELECT word FROM words WHERE id = %s", (word_id,))
        current_word_data = cursor.fetchone()

        if not current_word_data:
            return jsonify({
                'success': False,
                'error': 'Word not found'
            }), 404

        current_word_text = current_word_data['word']

        # Update translation and sample_sentence across ALL instances of this word
        if 'translation' in data or 'sample_sentence' in data:
            shared_update_fields = []
            shared_params = []

            if 'translation' in data:
                shared_update_fields.append('translation = %s')
                shared_params.append(data['translation'])

            if 'sample_sentence' in data:
                shared_update_fields.append('sample_sentence = %s')
                shared_params.append(data['sample_sentence'])

            if shared_update_fields:
                # Update ALL rows with the same word text
                shared_params.append(current_word_text)
                shared_update_query = f"""
                    UPDATE words
                    SET {', '.join(shared_update_fields)}
                    WHERE word = %s
                """
                cursor.execute(shared_update_query, shared_params)

        # Update the word text itself only for this specific row
        if 'word' in data:
            cursor.execute("""
                UPDATE words
                SET word = %s
                WHERE id = %s
            """, (data['word'], word_id))

        # Get the updated word data for history record
        cursor.execute("""
            SELECT word, translation, sample_sentence, category
            FROM words
            WHERE id = %s
        """, (word_id,))
        updated_word = cursor.fetchone()

        # Create history record
        create_history_record(
            cursor,
            word_id,
            updated_word['word'],
            updated_word['translation'],
            updated_word['sample_sentence'],
            updated_word['category'],
            'updated'
        )

        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Word updated successfully'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/words/<int:word_id>/category', methods=['PUT'])
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

        if not data or 'new_category' not in data:
            return jsonify({
                'success': False,
                'error': 'new_category is required'
            }), 400

        new_category = data['new_category'].strip()

        if not new_category:
            return jsonify({
                'success': False,
                'error': 'Category cannot be empty'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get current word information
        cursor.execute("""
            SELECT word, translation, sample_sentence, category, review_count, last_reviewed
            FROM words
            WHERE id = %s
        """, (word_id,))

        current_word = cursor.fetchone()

        if not current_word:
            return jsonify({
                'success': False,
                'error': 'Word not found'
            }), 404

        # Check if word already exists in target category
        cursor.execute("""
            SELECT id FROM words
            WHERE word = %s AND category = %s
        """, (current_word['word'], new_category))

        existing_word = cursor.fetchone()

        if existing_word:
            # Word already exists in target category - return error with special flag
            return jsonify({
                'success': False,
                'error': f'Word "{current_word["word"]}" already exists in category "{new_category}"',
                'duplicate': True
            }), 409

        # Word doesn't exist in target category - perform the move
        # Step 1: Insert word into new category
        cursor.execute("""
            INSERT INTO words (word, translation, sample_sentence, category, review_count, last_reviewed)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            current_word['word'],
            current_word['translation'],
            current_word['sample_sentence'],
            new_category,
            current_word['review_count'],
            current_word['last_reviewed']
        ))

        new_word_id = cursor.lastrowid

        # Create history record for the moved word
        create_history_record(
            cursor,
            new_word_id,
            current_word['word'],
            current_word['translation'],
            current_word['sample_sentence'],
            new_category,
            'moved'
        )

        # Step 2: Delete word from current category
        cursor.execute("DELETE FROM words WHERE id = %s", (word_id,))

        conn.commit()

        # Update category counts
        try:
            cursor.callproc('update_category_counts')
            conn.commit()
        except Exception:
            pass  # Non-critical

        return jsonify({
            'success': True,
            'message': f'Word moved to category "{new_category}"'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/words/<int:word_id>', methods=['DELETE'])
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
        scope = request.args.get('scope', None)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # First, get the current word information
        cursor.execute("""
            SELECT word, category
            FROM words
            WHERE id = %s
        """, (word_id,))

        current_word = cursor.fetchone()

        if not current_word:
            return jsonify({
                'success': False,
                'error': 'Word not found'
            }), 404

        # Check if this word exists in other categories
        cursor.execute("""
            SELECT category
            FROM words
            WHERE word = %s AND id != %s
        """, (current_word['word'], word_id))

        other_categories = cursor.fetchall()

        # If word exists in other categories and no scope specified, ask user
        if other_categories and scope is None:
            category_list = [cat['category'] for cat in other_categories]
            return jsonify({
                'success': False,
                'requires_confirmation': True,
                'word': current_word['word'],
                'current_category': current_word['category'],
                'other_categories': category_list,
                'message': f'Word "{current_word["word"]}" also exists in {len(category_list)} other categor{"y" if len(category_list) == 1 else "ies"}'
            }), 200

        # Perform deletion based on scope
        if scope == 'all_categories':
            # Delete all instances of this word across all categories
            cursor.execute("DELETE FROM words WHERE word = %s", (current_word['word'],))
            rows_affected = cursor.rowcount
            message = f'Word "{current_word["word"]}" deleted from all categories'
        else:
            # Delete only from current category (default behavior)
            cursor.execute("DELETE FROM words WHERE id = %s", (word_id,))
            rows_affected = cursor.rowcount
            message = f'Word "{current_word["word"]}" deleted from category "{current_word["category"]}"'

        conn.commit()

        # Update category counts
        try:
            cursor.callproc('update_category_counts')
            conn.commit()
        except Exception:
            pass  # Non-critical

        if rows_affected > 0:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Word not found'
            }), 404

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/words/<int:word_id>/review', methods=['POST'])
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
        cursor.execute("""
            UPDATE words
            SET review_count = review_count + 1,
                last_reviewed = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (word_id,))

        # Get updated word data for history
        cursor.execute("""
            SELECT word, translation, sample_sentence, category, review_count, last_reviewed
            FROM words
            WHERE id = %s
        """, (word_id,))

        result = cursor.fetchone()

        if result:
            # Create history record for review
            create_history_record(
                cursor,
                word_id,
                result['word'],
                result['translation'],
                result['sample_sentence'],
                result['category'],
                'updated'
            )

            conn.commit()

            return jsonify({
                'success': True,
                'review_count': result['review_count'],
                'last_reviewed': str(result['last_reviewed']) if result['last_reviewed'] else None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Word not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/generate-sample', methods=['POST'])
def generate_sample_sentence():
    """
    Generate a sample sentence using Ollama AI

    Request Body (JSON):
        {
            "word": "example"
        }

    Returns:
        JSON response with generated sentence
    """
    try:
        data = request.get_json()

        if not data or 'word' not in data:
            return jsonify({
                'success': False,
                'error': 'Word is required'
            }), 400

        word = data['word'].strip()

        if not word:
            return jsonify({
                'success': False,
                'error': 'Word cannot be empty'
            }), 400

        # Prepare prompt for Ollama
        prompt = f'Create a natural English sentence that uses the EXACT word or phrase "{word}" (including all words as shown). You must use "{word}" exactly as written, not variations or partial matches. Only output the sentence, nothing else.'

        # Call Ollama API
        ollama_url = "http://localhost:11434/api/generate"
        ollama_payload = {
            "model": "gemma3n:e2b",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(ollama_url, json=ollama_payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            generated_sentence = result.get('response', '').strip()

            return jsonify({
                'success': True,
                'sentence': generated_sentence
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Ollama API error: {response.status_code}'
            }), 500

    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Ollama request timed out. Please try again.'
        }), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Cannot connect to Ollama server. Please ensure Ollama is running on port 11434.'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/category/<category>/count', methods=['GET'])
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

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM words
            WHERE category = %s
        """, (category,))

        result = cursor.fetchone()
        count = result['count'] if result else 0

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'category': category,
            'count': count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/quiz/random-words', methods=['GET'])
def get_random_quiz_words():
    """
    Get random words for quiz (only words with review_count > 0)

    Query Parameters:
        limit: Number of words to return (default=10)

    Returns:
        JSON response:
        {
            "success": true,
            "count": 10,
            "words": [
                {"id": 1, "word": "example", "translation": "例子"},
                ...
            ]
        }
    """
    conn = None
    try:
        limit = int(request.args.get('limit', 10))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get random words with review_count > 0
        cursor.execute("""
            SELECT id, word, translation
            FROM words
            WHERE review_count > 0
            ORDER BY RAND()
            LIMIT %s
        """, (limit,))

        words = cursor.fetchall()

        if not words:
            return jsonify({
                'success': False,
                'error': 'No reviewed words found. Please review some words first by clicking the counter badge.',
                'count': 0
            }), 404

        return jsonify({
            'success': True,
            'count': len(words),
            'words': words
        })

    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid limit parameter'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/quiz/generate', methods=['POST'])
def generate_quiz():
    """
    Generate quiz questions using Ollama AI

    Request Body (JSON):
        {
            "words": [
                {"id": 1, "word": "example", "translation": "例子"},
                ...
            ]
        }

    Returns:
        JSON response with quiz questions:
        {
            "success": true,
            "questions": [
                {
                    "word_id": 1,
                    "word": "example",
                    "options": ["例子", "错误1", "错误2", "错误3"],
                    "correct_answer": 0
                },
                ...
            ]
        }
    """
    try:
        data = request.get_json()

        if not data or 'words' not in data:
            return jsonify({
                'success': False,
                'error': 'Words array is required'
            }), 400

        words = data['words']

        if not words or len(words) == 0:
            return jsonify({
                'success': False,
                'error': 'At least one word is required'
            }), 400

        questions = []

        # Generate questions for each word using Ollama
        for word_data in words:
            correct_word = word_data.get('word', '')
            translation = word_data.get('translation', '')
            word_id = word_data.get('id')

            # Prepare prompt for Ollama to generate 2 plausible wrong English words
            prompt = f'''For the Chinese translation "{translation}" (correct English word: {correct_word}), generate 2 plausible but INCORRECT English words that could mislead someone.

Requirements:
- Each wrong answer should be a realistic English word that sounds plausible for this Chinese meaning
- They should be different from the correct answer: {correct_word}
- Output ONLY 2 English words, one per line, nothing else
- No numbering, no explanations, just the words'''

            # Call Ollama API
            ollama_url = "http://localhost:11434/api/generate"
            ollama_payload = {
                "model": "gemma3n:e2b",
                "prompt": prompt,
                "stream": False
            }

            response = requests.post(ollama_url, json=ollama_payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()

                # Parse the 2 wrong answers
                wrong_answers = [line.strip() for line in generated_text.split('\n') if line.strip()][:2]

                # Ensure we have exactly 2 wrong answers
                while len(wrong_answers) < 2:
                    wrong_answers.append(f"option{len(wrong_answers) + 1}")

                # Create options array with correct answer and 2 wrong answers (3 total)
                options = [correct_word] + wrong_answers[:2]

                # Shuffle options but remember correct answer position
                import random
                correct_index = 0
                indices = list(range(3))
                random.shuffle(indices)
                shuffled_options = [options[i] for i in indices]
                correct_answer_index = indices.index(correct_index)

                questions.append({
                    'word_id': word_id,
                    'translation': translation,
                    'options': shuffled_options,
                    'correct_answer': correct_answer_index
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Ollama API error: {response.status_code}'
                }), 500

        return jsonify({
            'success': True,
            'questions': questions
        })

    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Ollama request timed out. Please try again.'
        }), 500
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Cannot connect to Ollama server. Please ensure Ollama is running on port 11434.'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload', methods=['POST'])
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
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']

        # Check if filename is empty
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Only XML files are allowed.'
            }), 400

        # Save file securely
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Parse and import XML
        conn = None
        try:
            conn = get_db_connection()
            stats = parse_and_import_xml(
                filepath,
                conn,
                batch_size=app.config['XML_BATCH_SIZE']
            )

            # Clean up uploaded file
            os.remove(filepath)

            # Build response message
            message = f"Import completed: {stats['added']} words added"
            if stats['skipped_duplicates'] > 0:
                message += f", {stats['skipped_duplicates']} duplicates skipped"
            if stats['errors'] > 0:
                message += f", {stats['errors']} errors encountered"

            return jsonify({
                'success': True,
                'stats': stats,
                'message': message
            })

        except XMLParserError as e:
            # Clean up uploaded file on error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                'success': False,
                'error': f'XML parsing error: {str(e)}'
            }), 400
        finally:
            if conn:
                conn.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# Application Initialization
# ============================================

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

if __name__ == '__main__':
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize database connection pool
    init_db_pool()

    # Ensure word history table exists
    ensure_word_history_table()

    # Run Flask development server
    print("\n" + "="*50)
    print("  BKDict Vocabulary Web Application")
    print("="*50)
    print(f"  🌐 Server running on: http://localhost:5000")
    print(f"  📚 Database: {app.config['DB_NAME']}")
    print(f"  🔧 Debug mode: {app.config['DEBUG']}")
    print("="*50 + "\n")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
