"""Quick script to show vocabulary statistics"""
import mysql.connector
from config import Config

conn = mysql.connector.connect(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    database=Config.DB_NAME
)

cursor = conn.cursor()
cursor.execute("SELECT category, COUNT(*) as count FROM words GROUP BY category ORDER BY count DESC")
categories = cursor.fetchall()

print("\n" + "="*70)
print("📂 Words by Category:")
print("─"*70)
total = 0
for cat, count in categories:
    print(f"   {cat:<30} {count:>6,} words")
    total += count
print("─"*70)
print(f"   {'TOTAL':<30} {total:>6,} words")
print("="*70 + "\n")

cursor.close()
conn.close()
