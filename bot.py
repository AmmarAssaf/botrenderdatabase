"""
نظام التسجيل المبسط - بدون مشاكل اعتماديات
"""

import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, CallbackQueryHandler
from flask import Flask
import threading
import sqlite3
import json
from datetime import datetime

# الإعدادات الأساسية
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# حالات المحادثة
NAME, PHONE, EMAIL, CONFIRM = range(4)

# قاعدة بيانات SQLite محلية (لا تحتاج psycopg2)
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('users.db', check_same_thread=False)
        self.init_db()
    
    def init_db(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    name TEXT,
                    phone TEXT,
                    email TEXT,
                    reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def add_user(self, user_data):
        with self.conn:
            self.conn.execute('''
                INSERT INTO users (user_id, name, phone, email) 
                VALUES (?, ?, ?, ?)
            ''', (user_data['user_id'], user_data['name'], user_data['phone'], user_data['email']))
    
    def user_exists(self, user_id):
        cursor = self.conn.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone() is not None

db = Database()

# خادم ويب بسيط
app = Flask(__name__)

@app.route('/')
def home(): 
    return "✅ النظام شغال على SQLite!"

@app.route('/stats')
def stats():
    cursor = db.conn.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    return f"👥 عدد المستخدمين: {count}"

def run_web(): 
    app.run(host='0.0.0.0', port=5000, debug=False)

# handlers البوت
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    
    if db.user_exists(user.id):
        await update.message.reply_text("🎉 أهلاً بعودتك! أنت مسجل مسبقاً.")
        return ConversationHandler.END
    
    context.user_data.clear()
    await update.message.reply_text("🆕 أهلاً بك! أدخل اسمك الكامل:")
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
    
    keyboard = [[InlineKeyboardButton("✅ تأكيد", callback_data="yes")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="no")]]
    
    await update.message.reply_text(
        f"📋 تأكيد البيانات:\n\nالاسم: {user['name']}\nالهاتف: {user['phone']}\nالبريد: {user['email']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM

async def confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == "yes":
        db.add_user(context.user_data)
        await query.message.reply_text("🎉 تم التسجيل بنجاح! ✅")
    else:
        await query.message.reply_text("❌ تم إلغاء التسجيل")
    
    return ConversationHandler.END

async def stats_cmd(update: Update, context: CallbackContext):
    cursor = db.conn.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    await update.message.reply_text(f"📊 عدد المسجلين: {count}")

# التشغيل الرئيسي
def main():
    # تشغيل خادم الويب
    threading.Thread(target=run_web, daemon=True).start()
    
    # تشغيل البوت
    app = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('register', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            CONFIRM: [CallbackQueryHandler(confirm)]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stats", stats_cmd))
    
    print("🚀 البوت شغال مع SQLite!")
    app.run_polling()

if __name__ == '__main__':
    main()
