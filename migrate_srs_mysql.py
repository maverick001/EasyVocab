
import mysql.connector
import os

def migrate():
    print("Starting MySQL migration...")
    
    # Simple .env parser to avoid dependencies
    env_vars = {}
    env_path = '.env'
    if os.path.exists(env_path):
        print(f"Loading {env_path}...")
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        # Remove quotes if present
                        if v.startswith('"') and v.endswith('"'):
                            v = v[1:-1]
                        elif v.startswith("'") and v.endswith("'"):
                            v = v[1:-1]
                        env_vars[k] = v
        except Exception as e:
            print(f"Warning: Could not read .env: {e}")
    
    # Config
    DB_HOST = env_vars.get('DB_HOST', 'localhost')
    DB_PORT = int(env_vars.get('DB_PORT', 3306))
    DB_USER = env_vars.get('DB_USER', 'root')
    DB_PASSWORD = env_vars.get('DB_PASSWORD', '')
    DB_NAME = env_vars.get('DB_NAME', 'bkdict_db')
    
    print(f"Connecting to {DB_NAME} at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    
    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        if conn.is_connected():
            print("Connected successfully.")
            cursor = conn.cursor()
            
            columns_to_add = [
                ("next_review_date", "DATETIME DEFAULT NULL"),
                ("srs_interval", "INT DEFAULT 0"),
                ("srs_repetitions", "INT DEFAULT 0"),
                ("srs_ease_factor", "FLOAT DEFAULT 2.5")
            ]
            
            # Check existing columns
            cursor.execute("DESCRIBE words")
            existing_cols = [row[0] for row in cursor.fetchall()]
            
            for col_name, col_def in columns_to_add:
                if col_name not in existing_cols:
                    print(f"Adding column: {col_name}")
                    cursor.execute(f"ALTER TABLE words ADD COLUMN {col_name} {col_def}")
                    print(f"  + Added {col_name}")
                else:
                    print(f"  - Column {col_name} already exists")
            
            conn.commit()
            print("Migration completed successfully.")
            
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    migrate()
