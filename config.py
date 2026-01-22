"""
Configuration file for BKDict Flask Application
Contains database connection settings and app configurations
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """
    Main configuration class for Flask application
    Uses environment variables for sensitive data (passwords, etc.)
    """

    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

    # MySQL Database Configuration
    # Default to None to ensure we fail visible if .env is not loaded
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_NAME = os.environ.get('DB_NAME')

    # Poe API Configuration (OpenAI-compatible)
    POE_API_KEY = os.environ.get('POE_API_KEY')
    POE_MODEL = os.environ.get('POE_MODEL', 'Claude-Haiku-4.5')
    POE_TEMPERATURE = float(os.environ.get('POE_TEMPERATURE', 0.7))

    # Database connection pool settings (for performance with large dataset)
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 5))
    DB_POOL_RECYCLE = int(os.environ.get('DB_POOL_RECYCLE', 3600))

    # File Upload Configuration
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
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


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
