import os
import psycopg2
from psycopg2.extras import RealDictCursor

def view_database():
    print("👀 استعراض بيانات قاعدة البيانات...")
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL غير موجود")
        return
    
    try:
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        
        # استعراض الجداول
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cur.fetchall()
            
            print("\n📊 الجداول الموجودة في قاعدة البيانات:")
            for table in tables:
                print(f" - {table[0]}")
        
        # استعراض بيانات جدول users
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users ORDER BY created_at DESC;")
            users = cur.fetchall()
            
            print(f"\n👥 بيانات جدول users ({len(users)} سجل):")
            print("=" * 60)
            for user in users:
                print(f"ID: {user['id']} | الاسم: {user['name']} | التاريخ: {user['created_at']}")
            print("=" * 60)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")

if __name__ == '__main__':
    view_database()
