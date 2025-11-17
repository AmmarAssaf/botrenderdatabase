"""
نظام تسجيل المستخدمين - النسخة الكاملة
يعمل مع قاعدة بيانات Render PostgreSQL
"""

import os
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
    return """
    <html>
        <head>
            <title>نظام التسجيل - مؤسسة الترويج الإعلامي</title>
            <meta charset="utf-8">
        </head>
        <body>
            <div style="text-align: center; padding: 50px;">
                <h1>🤖 نظام التسجيل يعمل بنجاح</h1>
                <p>مؤسسة الترويج الإعلامي</p>
                <p><a href="/health">الحالة</a> | <a href="/stats">الإحصائيات</a></p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    db_status = "connected" if db.get_connection() else "disconnected"
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/stats')
def stats():
    users_count = db.get_users_count()
    return jsonify({
        "total_users": users_count,
        "system": "Media Promotion Bot",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

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
    
    # تنسيق رقم الهاتف
    if phone.startswith('0'):
        phone = '+966' + phone[1:]
    else:
        phone = '+966' + phone
    
    context.user_data['phone_number'] = phone
    
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
            user_id = query.from_user.id
            
            # حفظ البيانات في قاعدة البيانات
            db_result = db.add_user(user_data)
            
            if db_result:
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
                await query.message.reply_text("❌ حدث خطأ في حفظ البيانات في النظام.")
                
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات: {e}")
            await query.message.reply_text("❌ حدث خطأ في حفظ البيانات.")
    else:
        await query.message.reply_text("🔄 لنبدأ التسجيل من جديد:\n\nما هو اسمك الكامل؟")
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
• اسم المستخدم: @{user_data['telegram_username'] or 'غير متوفر'}
• تاريخ التسجيل: {user_data['registration_date'].strftime('%Y-%m-%d %H:%M:%S')}

💼 **الحالة:** ✅ {user_data['status']}
"""
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("❌ لم يتم العثور على ملفك الشخصي. استخدم /start للتسجيل.")
            
    except Exception as e:
        logger.error(f"خطأ في عرض الملف: {e}")
        await update.message.reply_text("❌ حدث خطأ في عرض الملف")

async def stats(update: Update, context: CallbackContext):
    """إحصائيات النظام"""
    try:
        total_users = db.get_users_count()
        
        message = f"""
📊 **إحصائيات النظام**

👥 **المستخدمين:**
• إجمالي المسجلين: {total_users}

🗃️ **التخزين:** قاعدة بيانات PostgreSQL
🚀 **الحالة:** نشط ✅
"""
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"خطأ في عرض الإحصائيات: {e}")
        await update.message.reply_text("❌ حدث خطأ في عرض الإحصائيات")

async def cancel(update: Update, context: CallbackContext) -> int:
    """إلغاء التسجيل"""
    await update.message.reply_text("❌ تم إلغاء التسجيل")
    return ConversationHandler.END

async def error_handler(update: Update, context: CallbackContext):
    """معالجة الأخطاء"""
    logger.error(f"حدث خطأ: {context.error}")

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
    print("🔧 جارٍ تهيئة قاعدة البيانات...")
    if db.init_db():
        print("✅ تم تهيئة قاعدة البيانات بنجاح")
    else:
        print("❌ فشل في تهيئة قاعدة البيانات")
        return
    
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
        application.add_error_handler(error_handler)
        
        print("=" * 50)
        print("🤖 نظام التسجيل مع قاعدة البيانات يعمل بنجاح!")
        print("🗃️ قاعدة بيانات: PostgreSQL (Render)")
        print("💰 مجاني تماماً!")
        print("⏰ 24/7 مستمر")
        print("=" * 50)
        
        # تشغيل البوت
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")

if __name__ == '__main__':
    main()
