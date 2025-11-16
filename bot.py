"""
نظام تسجيل المستخدمين - النسخة الكاملة
يعمل مع قاعدة بيانات Render PostgreSQL باستخدام pg8000
"""

import os
import logging
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, CallbackQueryHandler
from flask import Flask, jsonify
import threading
from database import db

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
# 🌐 خادم ويب للحفاظ على النشاط
# ==============================
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 نظام التسجيل يعمل بنجاح مع قاعدة البيانات (pg8000)!"

@app.route('/ping')
def ping():
    return "pong"

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "database": "connected" if db.get_connection() else "disconnected"
    })

@app.route('/stats')
def stats():
    users_count = db.get_users_count()
    return jsonify({
        "total_users": users_count,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/users')
def users_list():
    """عرض قائمة المستخدمين (لأغراض الإدارة)"""
    users = db.get_all_users()
    users_data = []
    for user in users:
        users_data.append({
            "user_id": user['user_id'],
            "full_name": user['full_name'],
            "phone_number": user['phone_number'],
            "email": user['email'],
            "registration_date": user['registration_date'].strftime('%Y-%m-%d %H:%M:%S'),
            "status": user['status']
        })
    return jsonify(users_data)

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ==============================
# 🤖 نظام التسجيل الرئيسي
# ==============================
async def start(update: Update, context: CallbackContext) -> int:
    """بدء عملية التسجيل"""
    user = update.message.from_user
    
    # تسجيل النشاط
    db.log_activity(user.id, 'start_command', 'استخدم أمر البدء')
    
    # التحقق من التسجيل المسبق
    existing_user = db.get_user(user.id)
    if existing_user:
        await update.message.reply_text(
            f"🎉 أهلاً بعودتك {user.first_name}!\n"
            "أنت مسجل مسبقاً في النظام.\n\n"
            "للتسجيل كمستخدم جديد، استخدم /register\n"
            "لعرض ملفك الشخصي، استخدم /profile"
        )
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
    return NAME

async def get_name(update: Update, context: CallbackContext) -> int:
    """استقبال الاسم الكامل"""
    name = update.message.text.strip()
    
    if len(name) < 5:
        await update.message.reply_text("❌ الرجاء إدخال الاسم الكامل (الاسم الثلاثي)")
        return NAME
    
    context.user_data['full_name'] = name
    
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
    
    context.user_data['phone_number'] = f"+966{phone}"  # افتراضي السعودية
    
    await update.message.reply_text(
        f"✅ تم حفظ رقم الهاتف\n\n"
        "📧 **أدخل بريدك الإلكتروني:**\n"
        "(مثال: name@example.com)"
    )
    return EMAIL

async def get_email(update: Update, context: CallbackContext) -> int:
    """استقبال البريد الإلكتروني"""
    email = update.message.text.strip()
    
    if '@' not in email or '.' not in email:
        await update.message.reply_text("❌ البريد الإلكتروني غير صحيح! الرجاء إدخال بريد صالح.")
        return EMAIL
    
    context.user_data['email'] = email
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
        [InlineKeyboardButton("❌ إلغاء", callback_data="confirm_no")]
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
            user_id = query.from_user.id
            
            # حفظ البيانات
            db_user_id = db.add_user(user_data)
            
            if db_user_id:
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
                logger.info(f"تم تسجيل مستخدم جديد: {user_id}")
            else:
                await query.message.reply_text("❌ حدث خطأ في حفظ البيانات في قاعدة البيانات.")
            
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات: {e}")
            await query.message.reply_text("❌ حدث خطأ في حفظ البيانات.")
    else:
        await query.message.reply_text("❌ تم إلغاء التسجيل")
    
    return ConversationHandler.END

async def profile(update: Update, context: CallbackContext):
    """عرض الملف الشخصي"""
    try:
        user_id = update.effective_user.id
        
        user_profile = db.get_user(user_id)
        if user_profile:
            message = f"""
📋 **ملفك الشخصي**

👤 **المعلومات:**
• الاسم: {user_profile['full_name']}
• الهاتف: {user_profile['phone_number']}
• البريد: {user_profile['email']}
• تاريخ التسجيل: {user_profile['registration_date'].strftime('%Y-%m-%d %H:%M:%S')}
• الحالة: {user_profile['status']}

💼 **آخر نشاط:** {user_profile['last_activity'].strftime('%Y-%m-%d %H:%M:%S')}
"""
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ لم يتم العثور على ملفك الشخصي. استخدم /start للتسجيل.")
            
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ في عرض الملف")

async def stats(update: Update, context: CallbackContext):
    """إحصائيات النظام"""
    try:
        total_users = db.get_users_count()
        
        message = f"""
📊 **إحصائيات النظام**

👥 **المستخدمين:**
• إجمالي المسجلين: {total_users}

🚀 **قاعدة البيانات:** ✅ نشطة
"""
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ في عرض الإحصائيات")

async def admin_stats(update: Update, context: CallbackContext):
    """إحصائيات للمشرفين"""
    try:
        user_id = update.effective_user.id
        # يمكنك إضافة تحقق من أن user_id هو المشرف
        
        total_users = db.get_users_count()
        all_users = db.get_all_users()
        
        message = f"""
📊 **إحصائيات المشرفين**

👥 **المستخدمين:**
• إجمالي المسجلين: {total_users}

📈 **آخر 5 مسجلين:**
"""
        
        for user in all_users[:5]:
            message += f"• {user['full_name']} - {user['registration_date'].strftime('%Y-%m-%d')}\n"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        await update.message.reply_text("❌ حدث خطأ في عرض إحصائيات المشرفين")

async def cancel(update: Update, context: CallbackContext) -> int:
    """إلغاء التسجيل"""
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
    
    # تهيئة قاعدة البيانات
    if not db.init_db():
        print("❌ فشل في تهيئة قاعدة البيانات")
        return
    
    # بدء خادم Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ خادم الويب يعمل")
    
    try:
        # إنشاء وتشغيل البوت
        application = Application.builder().token(BOT_TOKEN).build()
        
        # نظام المحادثة للتسجيل
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
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
        application.add_handler(CommandHandler("admin_stats", admin_stats))
        application.add_handler(CommandHandler("register", start))
        
        print("=" * 50)
        print("🤖 نظام التسجيل مع قاعدة البيانات يعمل بنجاح!")
        print("💰 مجاني تماماً!")
        print("⏰ 24/7 مستمر")
        print("🗄️ يستخدم قاعدة بيانات PostgreSQL على Render")
        print("=" * 50)
        
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    main()
