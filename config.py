"""
Configuration file for BKDict Flask Application
Contains database connection settings and app configurations
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


# Session cookies are signed with SECRET_KEY. These values are public (this
# repo and .env.example), so anyone could forge a logged-in cookie with them.
DEV_SECRET_KEY = 'dev-secret-key-change-in-production'
PUBLIC_SECRET_KEYS = frozenset({DEV_SECRET_KEY, 'your-secret-key-here'})


def resolve_secret_key(environ):
    """
    Pick the session signing key.

    On Vercel a real SECRET_KEY is required: the app refuses to start rather
    than sign sessions with a publicly known value. Everywhere else (local
    runs, Docker, tests) a missing key falls back to the dev value.

    Args:
        environ: mapping of environment variables (os.environ)

    Returns:
        The key to sign sessions with

    Raises:
        RuntimeError: on Vercel when SECRET_KEY is missing or a public value
    """
    # The key is returned exactly as set: trimming it would change the signing
    # key and log out existing sessions. Whitespace is ignored only for the check.
    key = environ.get('SECRET_KEY') or ''
    if environ.get('VERCEL') and (not key.strip() or key.strip() in PUBLIC_SECRET_KEYS):
        raise RuntimeError(
            'SECRET_KEY is missing or set to a publicly known placeholder. '
            'Set a long random SECRET_KEY in the Vercel project environment '
            'variables, then redeploy.'
        )
    return key or DEV_SECRET_KEY


class Config:
    """
    Main configuration class for Flask application
    Uses environment variables for sensitive data (passwords, etc.)
    """

    # Flask Configuration
    SECRET_KEY = resolve_secret_key(os.environ)
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # Site Password Protection (set in environment to enable)
    SITE_PASSWORD = os.environ.get('SITE_PASSWORD')

    # MySQL Database Configuration
    # Default to None to ensure we fail visible if .env is not loaded
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_NAME = os.environ.get('DB_NAME')

    # Gemini API Configuration (OpenAI-compatible)
    GEMINI_API_KEY = os.environ.get('GOOGLE_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-4-hydrogen')
    # Model that writes the wrong options in multiple-choice quiz mode. A short
    # answer needs no big model: this one takes ~1s where gemini-4-hydrogen
    # takes ~3.4s.
    GEMINI_QUIZ_MODEL = os.environ.get('GEMINI_QUIZ_MODEL', 'gemini-3.5-flash-lite')
    GEMINI_TEMPERATURE = float(os.environ.get('GEMINI_TEMPERATURE', 0.9))
    # How much the model "thinks" before answering. 'low' cuts translation from
    # ~10-50s to ~2s with the same answers. Set empty to use each model's default.
    GEMINI_REASONING_EFFORT = os.environ.get('GEMINI_REASONING_EFFORT', 'low').strip()

    # Monitoring (Sentry errors/performance, Langfuse LLM traces).
    # Opt-in: each tool stays off until its keys are set. Everything is forced
    # off when SKIP_DB=true (the test suite), even if .env holds real keys.
    MONITORING_ENABLED = os.environ.get('SKIP_DB', '').lower() != 'true'
    MONITORING_ENVIRONMENT = (
        os.environ.get('SENTRY_ENVIRONMENT') or os.environ.get('VERCEL_ENV') or 'local'
    )
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    # Share of requests timed by Sentry. Each traced request is sent to Sentry
    # before the response returns on Vercel, so 1.0 slows every request.
    SENTRY_TRACES_SAMPLE_RATE = os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.5')
    LANGFUSE_PUBLIC_KEY = os.environ.get('LANGFUSE_PUBLIC_KEY')
    LANGFUSE_SECRET_KEY = os.environ.get('LANGFUSE_SECRET_KEY')

    # Database connection pool settings (for performance with large dataset)
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 5))
    DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))

    # File Upload Configuration
    # Use /tmp on Vercel because the root is read-only
    if os.environ.get('VERCEL'):
        UPLOAD_FOLDER = '/tmp'
    else:
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'xml'}

    # XML Import Configuration
    XML_BATCH_SIZE = 1000  # Insert records in batches of 1000 for performance

    @staticmethod
    def init_app(app):
        """
        Initialize application with additional configuration if needed
        """
        # Create upload folder if it doesn't exist
        try:
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        except Exception:
            # On Vercel this might fail if not in /tmp, but we handle it elsewhere
            pass


class DevelopmentConfig(Config):
    """Development environment specific configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production environment specific configuration"""
    DEBUG = False


# Configuration dictionary for easy selection
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
