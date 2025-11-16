"""
نظام تسجيل المستخدمين - النسخة الكاملة
مع قاعدة بيانات Render PostgreSQL
"""

import os
import logging
import psycopg2
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, CallbackQueryHandler
from flask import Flask
import threading
from urllib.parse import urlparse

# ==============================
# 🔧 الإعدادات الأساسية
# ==============================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# مراحل المحادثة
(NAME, PHONE, EMAIL, CONFIRMATION) = range(4)

# ==============================
# 🗄️ إدارة قاعدة البيانات
# ==============================
class DatabaseManager:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.init_database()

    def get_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        try:
            # تحليل رابط قاعدة البيانات لـ Render
            result = urlparse(self.database_url)
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port,
                sslmode='require'
            )
            return conn
        except Exception as e:
            logger.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
            return None

    def init_database(self):
        """تهيئة الجداول في قاعدة البيانات"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cursor:
                    # إنشاء جدول المستخدمين إذا لم يكن موجوداً
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT UNIQUE NOT NULL,
                            telegram_username VARCHAR(100),
                            full_name VARCHAR(200) NOT NULL,
                            phone_number VARCHAR(20) NOT NULL,
                            email VARCHAR(150) NOT NULL,
                            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(20) DEFAULT 'active'
                        )
                    ''')
                    
                    # إنشاء جدول للأنشطة
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS user_activities (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            activity_type VARCHAR(50) NOT NULL,
                            activity_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            details TEXT,
                            FOREIGN KEY (user_id) REFERENCES users(user_id)
                        )
                    ''')
                    
                    conn.commit()
                conn.close()
                logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
            else:
                logger.error("❌ فشل في تهيئة قاعدة البيانات")
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")

    def add_user(self, user_data):
        """إضافة مستخدم جديد إلى قاعدة البيانات"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO users 
                        (user_id, telegram_username, full_name, phone_number, email, registration_date)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (
                        user_data['user_id'],
                        user_data.get('telegram_username'),
                        user_data['full_name'],
                        user_data['phone_number'],
                        user_data['email'],
                        datetime.now()
                    ))
                    conn.commit()
                conn.close()
                logger.info(f"✅ تم إضافة مستخدم جديد: {user_data['user_id']}")
                return True
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة المستخدم: {e}")
        return False

    def get_user(self, user_id):
        """الحصول على بيانات مستخدم"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT * FROM users WHERE user_id = %s
                    ''', (user_id,))
                    user = cursor.fetchone()
                    
                    if user:
                        # تحويل النتيجة إلى قاموس
                        columns = [desc[0] for desc in cursor.description]
                        user_dict = dict(zip(columns, user))
                        conn.close()
                        return user_dict
                conn.close()
        except Exception as e:
            logger.error(f"❌ خطأ في جلب بيانات المستخدم: {e}")
        return None

    def user_exists(self, user_id):
        """التحقق من وجود المستخدم"""
        return self.get_user(user_id) is not None

    def get_total_users(self):
        """الحصول على عدد المستخدمين الإجمالي"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT COUNT(*) FROM users')
                    count = cursor.fetchone()[0]
                    conn.close()
                    return count
        except Exception as e:
            logger.error(f"❌ خطأ في عد المستخدمين: {e}")
        return 0

    def log_activity(self, user_id, activity_type, details=None):
        """تسجيل نشاط المستخدم"""
        try:
            conn = self.get_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO user_activities 
                        (user_id, activity_type, details)
                        VALUES (%s, %s, %s)
                    ''', (user_id, activity_type, details))
                    conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل النشاط: {e}")

# إنشاء كائن إدارة قاعدة البيانات
db = DatabaseManager()

# ==============================
# 🌐 خادم ويب للحفاظ على النشاط
# ==============================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 نظام التسجيل يعمل بنجاح مع قاعدة البيانات!"

@app.route('/ping')
def ping():
    return "pong"

@app.route('/health')
def health():
    return f"✅ النظام نشط - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

@app.route('/stats')
def stats():
    total_users = db.get_total_users()
    return f"👥 عدد المستخدمين المسجلين: {total_users}"

@app.route('/users')
def users_list():
    """قائمة المستخدمين (لأغراض التطوير فقط)"""
    try:
        conn = db.get_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT user_id, full_name, registration_date FROM users ORDER BY registration_date DESC LIMIT 10')
                users = cursor.fetchall()
                conn.close()
                
                users_html = "<h2>آخر 10 مستخدمين:</h2><ul>"
                for user in users:
                    users_html += f"<li>{user[1]} (ID: {user[0]}) - {user[2]}</li>"
                users_html += "</ul>"
                return users_html
    except Exception as e:
        return f"❌ خطأ: {e}"
    return "❌ لا يمكن الوصول للبيانات"

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ==============================
# 🤖 نظام التسجيل الرئيسي
# ==============================
async def start(update: Update, context: CallbackContext) -> int:
    """بدء عملية التسجيل"""
    user = update.message.from_user
    
    # التحقق من التسجيل المسبق
    if db.user_exists(user.id):
        user_data = db.get_user(user.id)
        await update.message.reply_text(
            f"🎉 أهلاً بعودتك {user.first_name}!\n"
            f"أنت مسجل مسبقاً في النظام منذ {user_data['registration_date'].strftime('%Y-%m-%d')}\n\n"
            "للتسجيل كمستخدم جديد، استخدم /register"
        )
        db.log_activity(user.id, 'start_command', 'مستخدم مسجل مسبقاً')
        return ConversationHandler.END
    
    context.user_data.clear()
    context.user_data['user_id'] = user.id
    context.user_data['telegram_username'] = user.username
    
    await update.message.reply_text(
        f"🆕 **مرحباً {user.first_name}!** 👋\n\n"
        "🏢 **أهلاً بك في نظام التسجيل بمؤسسة الترويج الإعلامي**\n\n"
        "📝 **ما هو اسمك الكامل؟**\n"
        "(الاسم الثلاثي)"
    )
    db.log_activity(user.id, 'start_registration')
    return NAME

async def get_name(update: Update, context: CallbackContext) -> int:
    """استقبال الاسم الكامل"""
    name = update.message.text.strip()
    
    if len(name) < 5:
        await update.message.reply_text("❌ الرجاء إدخال الاسم الكامل (الاسم الثلاثي)")
        return NAME
    
    context.user_data['full_name'] = name
    db.log_activity(context.user_data['user_id'], 'entered_name', name)
    
    await update.message.reply_text(
        f"✅ تم حفظ الاسم: {name}\n\n"
        "📞 **الآن، أدخل رقم هاتفك:**\n"
        "(مثال: 0512345678)"
    )
    return PHONE

async def get_phone(update: Update, context: CallbackContext) -> int:
    """استقبال رقم الهاتف"""
    phone = ''.join(filter(str.isdigit, update.message.text))
    
    if len(phone) < 8:
        await update.message.reply_text("❌ رقم الهاتف غير صحيح! الرجاء إدخال رقم صالح.")
        return PHONE
    
    # تنسيق رقم الهاتف
    if phone.startswith('0'):
        phone = f"+966{phone[1:]}"
    else:
        phone = f"+966{phone}"
    
    context.user_data['phone_number'] = phone
    db.log_activity(context.user_data['user_id'], 'entered_phone', phone)
    
    await update.message.reply_text(
        f"✅ تم حفظ رقم الهاتف\n\n"
        "📧 **أدخل بريدك الإلكتروني:**\n"
        "(مثال: name@example.com)"
    )
    return EMAIL

async def get_email(update: Update, context: CallbackContext) -> int:
    """استقبال البريد الإلكتروني"""
    email = update.message.text.strip().lower()
    
    if '@' not in email or '.' not in email:
        await update.message.reply_text("❌ البريد الإلكتروني غير صحيح! الرجاء إدخال بريد صالح.")
        return EMAIL
    
    context.user_data['email'] = email
    db.log_activity(context.user_data['user_id'], 'entered_email', email)
    return await show_confirmation(update, context)

async def show_confirmation(update: Update, context: CallbackContext) -> int:
    """عرض تأكيد البيانات"""
    user_data = context.user_data
    
    confirmation_text = f"""
📋 **الرجاء مراجعة بياناتك:**

👤 **البيانات الشخصية:**
• الاسم: {user_data.get('full_name')}
• الهاتف: {user_data.get('phone_number')}
• البريد: {user_data.get('email')}

✅ **هل البيانات صحيحة؟**
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، متابعة", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ إعادة التسجيل", callback_data="confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
    return CONFIRMATION

async def handle_confirmation(update: Update, context: CallbackContext) -> int:
    """معالجة تأكيد البيانات"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_yes":
        # حفظ البيانات في قاعدة البيانات
        try:
            user_data = context.user_data
            
            success = db.add_user({
                'user_id': user_data.get('user_id'),
                'telegram_username': user_data.get('telegram_username'),
                'full_name': user_data.get('full_name'),
                'phone_number': user_data.get('phone_number'),
                'email': user_data.get('email')
            })
            
            if success:
                await query.message.reply_text(
                    f"🎉 **تم التسجيل بنجاح!** ✅\n\n"
                    f"📊 **بياناتك:**\n"
                    f"• الاسم: {user_data.get('full_name')}\n"
                    f"• الهاتف: {user_data.get('phone_number')}\n"
                    f"• البريد: {user_data.get('email')}\n\n"
                    f"💼 **يمكنك الآن المشاركة في المهام**\n\n"
                    f"استخدم /profile لعرض ملفك الشخصي\n"
                    f"استخدم /stats لعرض الإحصائيات"
                )
                db.log_activity(user_data['user_id'], 'registration_completed')
                logger.info(f"تم تسجيل مستخدم جديد: {user_data['user_id']}")
            else:
                await query.message.reply_text("❌ حدث خطأ في حفظ البيانات في قاعدة البيانات.")
                
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات: {e}")
            await query.message.reply_text("❌ حدث خطأ في حفظ البيانات.")
    else:
        # إعادة التسجيل
        await query.message.reply_text("🔄 لنبدأ التسجيل من جديد...\n\nما هو اسمك الكامل؟")
        db.log_activity(context.user_data['user_id'], 'registration_restarted')
        return NAME
    
    return ConversationHandler.END

async def profile(update: Update, context: CallbackContext):
    """عرض الملف الشخصي"""
    try:
        user_id = update.effective_user.id
        
        user_data = db.get_user(user_id)
        if user_data:
            message = f"""
📋 **ملفك الشخصي**

👤 **المعلومات:**
• الاسم: {user_data['full_name']}
• الهاتف: {user_data['phone_number']}
• البريد: {user_data['email']}
• تاريخ التسجيل: {user_data['registration_date'].strftime('%Y-%m-%d %H:%M:%S')}

💼 **الحالة:** ✅ {user_data.get('status', 'نشط')}
"""
            db.log_activity(user_id, 'viewed_profile')
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ لم يتم العثور على ملفك الشخصي. استخدم /start للتسجيل.")
            
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ في عرض الملف")

async def stats(update: Update, context: CallbackContext):
    """إحصائيات النظام"""
    try:
        total_users = db.get_total_users()
        
        message = f"""
📊 **إحصائيات النظام**

👥 **المستخدمين:**
• إجمالي المسجلين: {total_users}

🗄️ **قاعدة البيانات:** ✅ نشطة
🚀 **النظام:** ⏰ 24/7 مستمر
"""
        db.log_activity(update.effective_user.id, 'viewed_stats')
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ في عرض الإحصائيات")

async def admin_stats(update: Update, context: CallbackContext):
    """إحصائيات للمسؤول (يمكن تطويره لاحقاً)"""
    try:
        user_id = update.effective_user.id
        # يمكن إضافة تحقق من صلاحيات المسؤول هنا
        
        total_users = db.get_total_users()
        
        message = f"""
👨‍💼 **الإحصائيات الإدارية**

📈 **المستخدمين:**
• الإجمالي: {total_users}

🔗 **رابط الإحصائيات:** 
{os.getenv('RENDER_SERVICE_URL', '')}/stats
"""
        db.log_activity(user_id, 'viewed_admin_stats')
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ في عرض الإحصائيات الإدارية")

async def cancel(update: Update, context: CallbackContext) -> int:
    """إلغاء التسجيل"""
    user_id = update.effective_user.id
    db.log_activity(user_id, 'registration_cancelled')
    await update.message.reply_text("❌ تم إلغاء التسجيل")
    return ConversationHandler.END

# ==============================
# 🎪 التشغيل الرئيسي
# ==============================
def main():
    """الدالة الرئيسية"""
    print("🚀 بدء تشغيل نظام التسجيل مع قاعدة البيانات...")
    
    # التحقق من المتغيرات
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN غير موجود")
        return
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL غير موجود")
        return
    
    print(f"✅ تم التعرف على قاعدة البيانات: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    
    # بدء خادم Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ خادم الويب يعمل على المنفذ 5000")
    
    try:
        # إنشاء وتشغيل البوت
        application = Application.builder().token(BOT_TOKEN).build()
        
        # نظام المحادثة للتسجيل
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start), CommandHandler('register', start)],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
                PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
                CONFIRMATION: [CallbackQueryHandler(handle_confirmation)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("profile", profile))
        application.add_handler(CommandHandler("stats", stats))
        application.add_handler(CommandHandler("admin", admin_stats))
        
        print("=" * 50)
        print("🤖 نظام التسجيل مع قاعدة البيانات يعمل بنجاح!")
        print(f"👥 المستخدمين المسجلين: {db.get_total_users()}")
        print("🗄️ قاعدة بيانات: ✅ PostgreSQL (Render)")
        print("🌐 خادم ويب: ✅ نشط")
        print("⏰ 24/7 مستمر")
        print("=" * 50)
        
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    main()
