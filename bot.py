import os
import psycopg2

print("🚀 بدء البرنامج...")

try:
    # الحصول على رابط قاعدة البيانات
    DATABASE_URL = os.getenv('DATABASE_URL')
    print("📊 تم الحصول على رابط قاعدة البيانات")
    
    # تحويل الرابط ليكون متوافقاً
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # الاتصال بقاعدة البيانات
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    print("✅ تم الاتصال بقاعدة البيانات!")
    
    # إنشاء الجدول
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS names (id SERIAL PRIMARY KEY, name TEXT)")
    conn.commit()
    print("✅ تم إنشاء الجدول!")
    
    # إدخال اسم عمار عساف
    cur.execute("INSERT INTO names (name) VALUES (%s)", ("عمار عساف",))
    conn.commit()
    print("✅ تم إدخال الاسم: عمار عساف")
    
    # عرض البيانات
    cur.execute("SELECT * FROM names")
    results = cur.fetchall()
    
    print("\n📋 البيانات في الجدول:")
    print("=" * 30)
    for row in results:
        print(f"ID: {row[0]} | الاسم: {row[1]}")
    print("=" * 30)
    
    # إغلاق الاتصال
    cur.close()
    conn.close()
    print("🎉 تم الانتهاء بنجاح!")
    
except Exception as e:
    print(f"❌ حدث خطأ: {e}")
