import os
import psycopg2
from psycopg2.extras import RealDictCursor

def test_database():
    print("🚀 بدء اختبار قاعدة البيانات...")
    
    # الحصول على رابط قاعدة البيانات
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL غير موجود")
        return
    
    print(f"📊 رابط قاعدة البيانات: {DATABASE_URL[:50]}...")
    
    try:
        # تحويل الرابط ليكون متوافقاً
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        # الاتصال بقاعدة البيانات
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        print("✅ تم الاتصال بقاعدة البيانات بنجاح!")
        
        # إنشاء جدول إذا لم يكن موجوداً
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("✅ تم إنشاء الجدول بنجاح!")
        
        # إدخال اسم "عمار عساف"
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (name) VALUES (%s) RETURNING id;", ("عمار عساف",))
            user_id = cur.fetchone()[0]
            conn.commit()
            print(f"✅ تم إدخال الاسم 'عمار عساف' برقم ID: {user_id}")
        
        # استعراض جميع الأسماء
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users ORDER BY created_at DESC;")
            users = cur.fetchall()
            
            print("\n📋 جميع الأسماء في قاعدة البيانات:")
            print("-" * 40)
            for user in users:
                print(f"ID: {user['id']} | الاسم: {user['name']} | التاريخ: {user['created_at']}")
            print("-" * 40)
        
        # إحصائية بسيطة
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM users;")
            total_users = cur.fetchone()[0]
            print(f"\n📊 إجمالي عدد المستخدمين: {total_users}")
        
        conn.close()
        print("\n🎉 تم تنفيذ البرنامج بنجاح!")
        
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")

if __name__ == '__main__':
    test_database()
