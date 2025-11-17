import os
import psycopg2

print("🚀 بدء تشغيل البرنامج...")

# الاتصال بقاعدة البيانات
try:
    DATABASE_URL = os.getenv('DATABASE_URL')
    print("📊 جارٍ الاتصال بقاعدة البيانات...")
    
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    print("✅ تم الاتصال بقاعدة البيانات!")
    
    # إنشاء الجدول
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS names (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("✅ تم إنشاء الجدول!")
    
    # إدخال اسم "عمار عساف"
    cur.execute("INSERT INTO names (name) VALUES ('عمار عساف')")
    conn.commit()
    print("✅ تم إدخال اسم 'عمار عساف'!")
    
    # عرض جميع الأسماء
    cur.execute("SELECT * FROM names ORDER BY created_at DESC")
    results = cur.fetchall()
    
    print("\n📋 الأسماء في قاعدة البيانات:")
    print("=" * 40)
    for row in results:
        print(f"ID: {row[0]} | الاسم: {row[1]} | التاريخ: {row[2]}")
    print("=" * 40)
    
    cur.close()
    conn.close()
    print("🎉 تم الانتهاء بنجاح!")
    
except Exception as e:
    print(f"❌ حدث خطأ: {e}")
