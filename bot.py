import os
import psycopg2

def connect_db():
    database_url = os.getenv('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    return psycopg2.connect(database_url, sslmode='require')

def create_table():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS names (id SERIAL PRIMARY KEY, name TEXT);")
    conn.commit()
    conn.close()
    print("✅ تم إنشاء الجدول")

def add_name():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO names (name) VALUES ('عمار عساف');")
    conn.commit()
    conn.close()
    print("✅ تم إضافة اسم: عمار عساف")

def show_names():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM names;")
    names = cur.fetchall()
    conn.close()
    
    print("\n📋 الأسماء في قاعدة البيانات:")
    print("-" * 30)
    for name in names:
        print(f"ID: {name[0]} | الاسم: {name[1]}")
    print("-" * 30)
    return names

if __name__ == "__main__":
    print("🚀 بدء البرنامج...")
    create_table()
    add_name()
    show_names()
    print("🎉 تم الانتهاء!")
