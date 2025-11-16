import os
import logging
import pg8000
from pg8000 import Connection, Cursor
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        
    def get_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        try:
            # تحويل DATABASE_URL إلى شكل يتعرف عليه pg8000
            # مثال: postgresql://user:pass@host:port/dbname
            if self.database_url.startswith('postgresql://'):
                # إزالة البادئة
                conn_str = self.database_url.replace('postgresql://', '')
                # تقسيم الجزء user:pass@host:port/dbname
                parts = conn_str.split('@')
                user_pass = parts[0].split(':')
                host_port_db = parts[1].split('/')
                host_port = host_port_db[0].split(':')
                
                user = user_pass[0]
                password = user_pass[1]
                host = host_port[0]
                port = int(host_port[1]) if len(host_port) > 1 else 5432
                database = host_port_db[1]
                
                conn = pg8000.connect(
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    database=database
                )
                return conn
            else:
                logger.error("صيغة DATABASE_URL غير معروفة")
                return None
        except Exception as e:
            logger.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
            return None
    
    def init_db(self):
        """تهيئة الجداول في قاعدة البيانات"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cur:
                    # جدول المستخدمين
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT UNIQUE NOT NULL,
                            telegram_username VARCHAR(100),
                            full_name VARCHAR(200) NOT NULL,
                            phone_number VARCHAR(20) NOT NULL,
                            email VARCHAR(150) NOT NULL,
                            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(20) DEFAULT 'active',
                            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # جدول سجل النشاطات
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS user_activity (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            activity_type VARCHAR(50) NOT NULL,
                            activity_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            details TEXT,
                            FOREIGN KEY (user_id) REFERENCES users(user_id)
                        );
                    """)
                    
                    # إنشاء فهارس لتحسين الأداء
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON users(user_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_user_id ON user_activity(user_id);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_date ON user_activity(activity_date);")
                    
                conn.commit()
                conn.close()
                logger.info("✅ تم تهيئة جداول قاعدة البيانات بنجاح")
                return True
            else:
                logger.error("❌ فشل في الاتصال بقاعدة البيانات لتهيئة الجداول")
                return False
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
            return False
    
    def add_user(self, user_data):
        """إضافة مستخدم جديد"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cur:
                    # إدخال المستخدم أو تحديثه إذا كان موجودًا
                    cur.execute("""
                        INSERT INTO users 
                        (user_id, telegram_username, full_name, phone_number, email) 
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                        telegram_username = EXCLUDED.telegram_username,
                        full_name = EXCLUDED.full_name,
                        phone_number = EXCLUDED.phone_number,
                        email = EXCLUDED.email,
                        last_activity = CURRENT_TIMESTAMP
                        RETURNING id;
                    """, (
                        user_data['user_id'],
                        user_data['telegram_username'],
                        user_data['full_name'],
                        user_data['phone_number'],
                        user_data['email']
                    ))
                    
                    result = cur.fetchone()
                    user_id = result[0] if result else None
                    
                    # تسجيل النشاط
                    cur.execute("""
                        INSERT INTO user_activity (user_id, activity_type, details)
                        VALUES (%s, %s, %s)
                    """, (user_data['user_id'], 'registration', 'تم تسجيل المستخدم الجديد'))
                    
                conn.commit()
                conn.close()
                logger.info(f"✅ تم إضافة/تحديث المستخدم: {user_data['user_id']}")
                return user_id
            return None
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة المستخدم: {e}")
            return None
    
    def get_user(self, user_id):
        """جلب بيانات مستخدم"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, user_id, telegram_username, full_name, phone_number, email, 
                               registration_date, status, last_activity
                        FROM users WHERE user_id = %s
                    """, (user_id,))
                    row = cur.fetchone()
                    if row:
                        columns = ['id', 'user_id', 'telegram_username', 'full_name', 'phone_number', 
                                  'email', 'registration_date', 'status', 'last_activity']
                        user = dict(zip(columns, row))
                        return user
                conn.close()
            return None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب بيانات المستخدم: {e}")
            return None
    
    def get_all_users(self):
        """جلب جميع المستخدمين"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, user_id, telegram_username, full_name, phone_number, email, 
                               registration_date, status, last_activity
                        FROM users ORDER BY registration_date DESC
                    """)
                    rows = cur.fetchall()
                    columns = ['id', 'user_id', 'telegram_username', 'full_name', 'phone_number', 
                              'email', 'registration_date', 'status', 'last_activity']
                    users = [dict(zip(columns, row)) for row in rows]
                conn.close()
                return users
            return []
        except Exception as e:
            logger.error(f"❌ خطأ في جلب جميع المستخدمين: {e}")
            return []
    
    def get_users_count(self):
        """عدد المستخدمين المسجلين"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM users")
                    count = cur.fetchone()[0]
                conn.close()
                return count
            return 0
        except Exception as e:
            logger.error(f"❌ خطأ في جلب عدد المستخدمين: {e}")
            return 0
    
    def log_activity(self, user_id, activity_type, details=None):
        """تسجيل نشاط المستخدم"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_activity (user_id, activity_type, details)
                        VALUES (%s, %s, %s)
                    """, (user_id, activity_type, details))
                    
                    # تحديث وقت النشاط الأخير
                    cur.execute("""
                        UPDATE users SET last_activity = CURRENT_TIMESTAMP 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                conn.commit()
                conn.close()
                return True
            return False
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل النشاط: {e}")
            return False

# إنشاء كائن قاعدة بيانات عالمي
db = Database()
