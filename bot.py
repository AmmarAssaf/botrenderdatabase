"""
نظام التسجيل المبسط - بدون تعقيد
يعمل مباشرة مع قاعدة بيانات Render
"""

import os
import logging
import psycopg2
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, CallbackQueryHandler
from flask import Flask
import threading

# الإعدادات الأساسية
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# حالات المحادثة
NAME, PHONE, EMAIL, CONFIRM = range(4)

# إدارة قاعدة البيانات
class Database:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv('DATABASE_URL'), sslmode='require')
        self.init_db()
    
    def init_db(self):
        with self.conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    name VARCHAR(200),
                    phone VARCHAR(20),
                    email VARCHAR(150),
                    reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
    
    def add_user(self, user_data):
        with self.conn.cursor() as cur:
            cur.execute('''
                INSERT INTO users (user_id, name, phone, email) 
                VALUES (%s, %s, %s, %s)
            ''', (user_data['user_id'], user_data['name'], user_data['phone'], user_data['email']))
            self.conn.commit()
    
    def user_exists(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute('SELECT 1 FROM users WHERE user_id = %s', (user_id,))
            return cur.fetchone() is not None

db = Database()

# خادم ويب بسيط
app = Flask(__name__)
@app.route('/')
def home(): return "✅ النظام شغال"
def run_web(): app.run(host='0.0.0.0', port=5000, debug=False)

# handlers البوت
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    if db.user_exists(user.id):
        await update.message.reply_text("🔄 أنت مسجل مسبقاً! استخدم /register لتسجيل جديد")
        return ConversationHandler.END
    
    context.user_data.clear()
    await update.message.reply_text("🆕 أدخل اسمك الكامل:")
    return NAME

async def get_name(update: Update, context: CallbackContext):
    context.user_data['name'] = update.message.text
    context.user_data['user_id'] = update.message.from_user.id
    await update.message.reply_text("📞 أدخل رقم هاتفك:")
    return PHONE

async def get_phone(update: Update, context: CallbackContext):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("📧 أدخل بريدك الإلكتروني:")
    return EMAIL

async def get_email(update: Update, context: CallbackContext):
    context.user_data['email'] = update.message.text
    user = context.user_data
    
    keyboard = [[InlineKeyboardButton("✅ تأكيد", callback_data="yes"),
                 InlineKeyboardButton("❌ إلغاء", callback_data="no")]]
    
    await update.message.reply_text(
        f"📋 تأكيد البيانات:\nالاسم: {user['name']}\nالهاتف: {user['phone']}\nالبريد: {user['email']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM

async def confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == "yes":
        db.add_user(context.user_data)
        await query.message.reply_text("🎉 تم التسجيل بنجاح!")
    else:
        await query.message.reply_text("❌ تم الإلغاء")
    
    return ConversationHandler.END

# التشغيل الرئيسي
def main():
    # تشغيل خادم الويب
    threading.Thread(target=run_web, daemon=True).start()
    
    # تشغيل البوت
    app = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT, get_name)],
            PHONE: [MessageHandler(filters.TEXT, get_phone)],
            EMAIL: [MessageHandler(filters.TEXT, get_email)],
            CONFIRM: [CallbackQueryHandler(confirm)]
        },
        fallbacks=[]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("register", start))
    
    print("🚀 البوت شغال!")
    app.run_polling()

if __name__ == '__main__':
    main()
