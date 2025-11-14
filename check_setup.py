"""
BKDict Setup Verification Script
Run this script to check if your environment is properly configured
"""

import sys
import os


def check_python_version():
    """Check if Python version is 3.8 or higher"""
    print("Checking Python version...", end=" ")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False


def check_required_packages():
    """Check if required Python packages are installed"""
    print("\nChecking required packages:")
    packages = {
        'flask': 'Flask',
        'mysql.connector': 'mysql-connector-python',
        'dotenv': 'python-dotenv'
    }

    all_installed = True
    for module_name, package_name in packages.items():
        try:
            __import__(module_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} (not installed)")
            all_installed = False

    return all_installed


def check_env_file():
    """Check if .env file exists"""
    print("\nChecking environment configuration...", end=" ")
    if os.path.exists('.env'):
        print("✅ .env file found")
        return True
    else:
        print("❌ .env file not found")
        print("   Please copy .env.example to .env and configure your settings")
        return False


def check_directories():
    """Check if required directories exist"""
    print("\nChecking directory structure:")
    directories = [
        'templates',
        'static/css',
        'static/js',
        'database',
        'utils',
        'uploads'
    ]

    all_exist = True
    for directory in directories:
        if os.path.exists(directory):
            print(f"  ✅ {directory}/")
        else:
            print(f"  ❌ {directory}/ (missing)")
            all_exist = False

    return all_exist


def check_key_files():
    """Check if key application files exist"""
    print("\nChecking key files:")
    files = [
        'app.py',
        'config.py',
        'database/init_database.sql',
        'templates/index.html',
        'static/css/style.css',
        'static/js/app.js'
    ]

    all_exist = True
    for file in files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (missing)")
            all_exist = False

    return all_exist


def test_database_connection():
    """Test MySQL database connection"""
    print("\nTesting database connection...", end=" ")

    try:
        from config import Config
        import mysql.connector

        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )

        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [db[0] for db in cursor.fetchall()]

        if Config.DB_NAME in databases:
            print(f"✅ Connected to MySQL, database '{Config.DB_NAME}' exists")

            # Check if tables exist
            conn.database = Config.DB_NAME
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]

            if 'words' in tables and 'categories' in tables:
                print("  ✅ Required tables found (words, categories)")
            else:
                print("  ⚠️  Tables not found. Run database/init_database.sql")
        else:
            print(f"⚠️  Connected to MySQL, but database '{Config.DB_NAME}' not found")
            print("     Please run database/init_database.sql in MySQL Workbench")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Failed")
        print(f"   Error: {str(e)}")
        print("   Please check your .env file and ensure MySQL is running")
        return False


def main():
    """Run all checks"""
    print("=" * 60)
    print("  BKDict Setup Verification")
    print("=" * 60)

    checks = [
        check_python_version(),
        check_required_packages(),
        check_env_file(),
        check_directories(),
        check_key_files()
    ]

    # Only test database if other checks pass
    if all(checks):
        test_database_connection()

    print("\n" + "=" * 60)
    if all(checks):
        print("✅ Setup verification PASSED!")
        print("\nYou can now run the application:")
        print("  python app.py")
        print("\nOr use the launch script:")
        print("  start_bkdict.bat")
    else:
        print("❌ Setup verification FAILED!")
        print("\nPlease fix the issues above before running the application.")
        print("Refer to README.md for detailed setup instructions.")
    print("=" * 60)


if __name__ == '__main__':
    main()
