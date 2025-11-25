"""
Diagnostic script to check daily_study_log data for word debt issues
"""
import mysql.connector
from config import Config
from datetime import date, timedelta

def check_debt_data():
    conn = None
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        
        # Get all daily logs
        cursor.execute("""
            SELECT date, review_count, last_updated
            FROM daily_study_log
            ORDER BY date DESC
            LIMIT 30
        """)
        
        logs = cursor.fetchall()
        
        print("\n" + "="*70)
        print("Daily Study Log - Last 30 Days")
        print("="*70)
        print(f"{'Date':<12} {'Reviews':<10} {'Debt':<10} {'Last Updated':<20}")
        print("-"*70)
        
        today = date.today()
        total_debt = 0
        
        for log in logs:
            log_date = log['date']
            if isinstance(log_date, str):
                log_date = date.fromisoformat(log_date)
            
            count = log['review_count']
            last_updated = log['last_updated']
            
            # Skip future dates
            if log_date > today:
                print(f"{log_date} <- FUTURE DATE (SKIPPED)")
                continue
            
            # Calculate contribution to debt
            if log_date == today:
                if count > 100:
                    contribution = -(count - 100)
                    total_debt -= (count - 100)
                else:
                    contribution = 0  # Today's deficit doesn't count yet
            else:
                contribution = 100 - count
                total_debt += contribution
            
            debt_str = f"+{contribution}" if contribution > 0 else f"{contribution}"
            today_marker = " <- TODAY" if log_date == today else ""
            
            print(f"{log_date} {count:>8}  {debt_str:>8}  {last_updated}{today_marker}")
        
        print("-"*70)
        print(f"Total Debt: {total_debt}")
        print("="*70)
        
        # Check for potential issues
        print("\nPotential Issues:")
        issues_found = False
        
        # Check for future dates
        cursor.execute("SELECT COUNT(*) as count FROM daily_study_log WHERE date > CURDATE()")
        future_count = cursor.fetchone()['count']
        if future_count > 0:
            print(f"⚠️  Found {future_count} entries with FUTURE dates!")
            issues_found = True
        
        # Check for duplicate dates
        cursor.execute("""
            SELECT date, COUNT(*) as count 
            FROM daily_study_log 
            GROUP BY date 
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} duplicate dates!")
            for dup in duplicates:
                print(f"   - {dup['date']}: {dup['count']} entries")
            issues_found = True
        
        # Check for very high review counts (possible data errors)
        cursor.execute("""
            SELECT date, review_count 
            FROM daily_study_log 
            WHERE review_count > 500
        """)
        high_counts = cursor.fetchall()
        if high_counts:
            print(f"⚠️  Found {len(high_counts)} days with unusually high review counts (>500)!")
            for hc in high_counts:
                print(f"   - {hc['date']}: {hc['review_count']} reviews")
            issues_found = True
        
        if not issues_found:
            print("✅ No obvious data issues found")
        
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_debt_data()
