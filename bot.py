import os
from urllib.parse import urlparse

print("🚀 بدء البرنامج...")

try:
    # استيراد المكتبة
    import pg8000
    
    # الحصول على رابط قاعدة البيانات
    DATABASE_URL = os.getenv('DATABASE_URL')
    print("📊 تم الحصول على رابط قاعدة البيانات")
    
    # تحليل الرابط
    url = urlparse(DATABASE_URL)
    
    # إعداد بيانات الاتصال
    conn_info = {
        'host': url.hostname,
        'port': url.port,
        'user': url.username,
        'password': url.password,
        'database': url.path[1:],  # إزالة الـ / من البداية
    }
    
    # الاتصال بقاعدة البيانات
    conn = pg8000.connect(**conn_info)
    print("✅ تم الاتصال بقاعدة البيانات!")
    
    # إنشاء الجدول
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS names (id SERIAL PRIMARY KEY, name TEXT)")
    conn.commit()
    print("✅ تم إنشاء الجدول!")
    
    # إدخال اسم عمار عساف
    cursor.execute("INSERT INTO names (name) VALUES ('عمار عساف')")
    conn.commit()
    print("✅ تم إدخال الاسم: عمار عساف")
    
    # عرض البيانات
    cursor.execute("SELECT * FROM names")
    results = cursor.fetchall()
    
    print("\n📋 البيانات في الجدول:")
    print("=" * 30)
    for row in results:
        print(f"ID: {row[0]} | الاسم: {row[1]}")
    print("=" * 30)
    
    # إغلاق الاتصال
    cursor.close()
    conn.close()
    print("🎉 تم الانتهاء بنجاح!")
    
except Exception as e:
    print(f"❌ حدث خطأ: {e}")
