import os
import psycopg2
from urllib.parse import urlparse

print("🚀 بدء تشغيل البرنامج...")

try:
    # الحصول على رابط قاعدة البيانات
    DATABASE_URL = os.getenv('DATABASE_URL')
    print("📊 تم العثور على رابط قاعدة البيانات")
    
    # تحويل الرابط ليكون متوافقاً
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # الاتصال بقاعدة البيانات
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    print("✅ تم الاتصال بقاعدة البيانات!")
    
    # إنشاء الجدول
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS names (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("✅ تم إنشاء الجدول!")
    
    # إدخال اسم عمار عساف
    cur.execute("INSERT INTO names (name) VALUES (%s)", ("عمار عساف",))
    conn.commit()
    print("✅ تم إدخال الاسم: عمار عساف")
    
    # عرض جميع الأسماء
    cur.execute("SELECT * FROM names ORDER BY created_at DESC")
    names = cur.fetchall()
    
    print("\n📋 الأسماء في قاعدة البيانات:")
    print("=" * 50)
    for name in names:
        print(f"ID: {name[0]} | الاسم: {name[1]} | التاريخ: {name[2]}")
    print("=" * 50)
    
    # إغلاق الاتصال
    cur.close()
    conn.close()
    print("🎉 تم الانتهاء بنجاح!")
    
except Exception as e:
    print(f"❌ حدث خطأ: {e}")
