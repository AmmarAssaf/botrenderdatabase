import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        
    def get_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        try:
            # تحويل connection string ليكون متوافقاً مع Render
            conn_str = self.database_url
            if conn_str.startswith('postgres://'):
                conn_str = conn_str.replace('postgres://', 'postgresql://', 1)
            
            conn = psycopg2.connect(conn_str, sslmode='require')
            return conn
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
                            details TEXT
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
                    if user_id:
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
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                    user = cur.fetchone()
                conn.close()
                return dict(user) if user else None
            return None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب بيانات المستخدم: {e}")
            return None
    
    def get_all_users(self):
        """جلب جميع المستخدمين"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM users ORDER BY registration_date DESC")
                    users = cur.fetchall()
                conn.close()
                return [dict(user) for user in users]
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
                    
                    # تحديث وقت النشاط الأخير في جدول المستخدمين
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
