import os
from sqlalchemy import create_engine, text

print("🚀 بدء تشغيل البرنامج...")

try:
    # الحصول على رابط قاعدة البيانات
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if DATABASE_URL:
        print("📊 تم العثور على رابط قاعدة البيانات")
        
        # تحويل الرابط ليكون متوافقاً مع SQLAlchemy
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        # إنشاء محرك قاعدة البيانات
        engine = create_engine(DATABASE_URL)
        
        # الاتصال والتشغيل
        with engine.connect() as connection:
            print("✅ تم الاتصال بقاعدة البيانات!")
            
            # إنشاء الجدول
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS names (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.commit()
            print("✅ تم إنشاء الجدول!")
            
            # إدخال اسم عمار عساف
            connection.execute(text("INSERT INTO names (name) VALUES (:name)"), {"name": "عمار عساف"})
            connection.commit()
            print("✅ تم إدخال الاسم: عمار عساف")
            
            # عرض جميع الأسماء
            result = connection.execute(text("SELECT * FROM names ORDER BY created_at DESC"))
            names = result.fetchall()
            
            print("\n📋 الأسماء في قاعدة البيانات:")
            print("=" * 50)
            for name in names:
                print(f"ID: {name[0]} | الاسم: {name[1]} | التاريخ: {name[2]}")
            print("=" * 50)
            
        print("🎉 تم الانتهاء بنجاح!")
    else:
        print("❌ لم يتم العثور على رابط قاعدة البيانات")
        
except Exception as e:
    print(f"❌ حدث خطأ: {e}")
