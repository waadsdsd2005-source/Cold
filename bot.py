import os
import re
import time
import threading
import traceback
from decimal import Decimal
import telebot
from telebot import types
from flask import Flask
import utils
import admin

BOT_TOKEN = os.environ.get("BOT_TOKEN")

try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", getattr(admin, "ADMIN_ID", 0)))
except Exception:
    ADMIN_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home():
    return "SMART GOLD SYSTEM IS LIVE 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

MASTER_CARD = admin.MASTER_CARD
MONTHLY_PRICE = admin.MONTHLY_PRICE
COMPANY_HEADER = admin.COMPANY_HEADER
SUPPORT_NUMBER = "07766083622" 

USER_STATE = {}
INVOICE_DATA = {}

def fmt(value):
    """دالة لتنسيق الأرقام بفاصلة الآلاف وبدون تقريب عشوائي لتطابق الحاسبة بدقة"""
    try:
        d = Decimal(str(value))
        if d == d.to_integral_value():
            return f"{int(d):,}"
        else:
            formatted = f"{d:,.2f}"
            return formatted
    except Exception:
        return str(value)

TEXTS = {
    "welcome": "👋 أهلاً بك في عمالقة الصياغة <b>SMART GOLD SYSTEM</b>\n\nالمنظومة الذكية الأسرع والأدق لإدارة الحسابات بدقة الحاسبة التقليدية.\n🔑 <i>رقم عضويتك:</i> <b>#{serial} صايغ معتمد</b>\n\nاستخدم الأزرار أدناه للبدء بالعمليات 👇",
    "btn_sell": "🛍️ بيع للزبون",
    "btn_buy": "📥 شراء من الزبون",
    "btn_dollar": "💵 سعر الدولار والتعديل",
    "btn_info": "📖 معلومات النظام",
    "invoice_sell": "🧾 <b>فاتورة بيع ذهب للزبون</b> 🧾",
    "invoice_buy": "📥 <b>فاتورة شراء ذهب من الزبون</b> 📥",
    "shop": "🔷 المحل العامر: ",
    "weight_tot": "⚖️ الوزن الإجمالي بالغرام: {w} غرام",
    "wage_sell": "🔨 أجور صياغة الغرام: {wage} دينار",
    "total_iqd": "💵 <b>السعر الكلي بالدينار العراقي:</b>\n👉 <b>{total} دينار</b>",
    "total_usd": "💵 <b>صافي الحساب بالورق والدينار:</b>\n👉 <b>{usd} ورقة و {rem} دينار</b>",
    "footer": "نظام آراُمكي - دقة وأمان لحساباتك اليومية"
}

def notify_admin_error(user_id, error_msg, traceback_str=""):
    if not ADMIN_ID:
        return
    try:
        error_report = (
            f"🚨 <b>تقرير خطأ (Exception Alert)</b> 🚨\n\n"
            f"👤 <b>معرف المستخدم:</b> <code>{user_id}</code>\n"
            f"⚠️ <b>السبب:</b>\n<code>{error_msg}</code>\n\n"
            f"📜 <b>التفاصيل:</b>\n<pre>{traceback_str[:3000]}</pre>"
        )
        bot.send_message(ADMIN_ID, error_report, parse_mode="HTML")
    except Exception as e:
        print(f"Failed to send error notification to admin: {e}")

def to_english_numbers(text):
    if not text:
        return ""
    arabic_nums = str.maketrans('٠١ي٣٤٥٦٧٨٩', '0123456789')
    persian_nums = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    return text.translate(arabic_nums).translate(persian_nums)

def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton(TEXTS["btn_sell"]), types.KeyboardButton(TEXTS["btn_buy"]))
    markup.add(types.KeyboardButton(TEXTS["btn_dollar"]), types.KeyboardButton(TEXTS["btn_info"]))
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("🛠️ لوحة تحكم الإدارة (خاص)"))
    return markup

def send_main_menu(message, user_id):
    try:
        markup = get_main_keyboard(user_id)
        serial = 145
        try:
            all_users = utils.get_all_goldsmiths()
            for u in all_users:
                if str(u.get('user_id')) == str(user_id):
                    serial = u.get('member_serial', 145)
                    break
        except Exception:
            pass
        
        bot.send_message(
            message.chat.id, 
            COMPANY_HEADER + TEXTS["welcome"].format(serial=serial), 
            parse_mode="HTML", 
            reply_markup=markup
        )
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    try:
        gs = utils.get_goldsmith(user_id) or {}
        is_admin = (user_id == ADMIN_ID)
        
        if not gs.get('is_registered', False):
            USER_STATE[user_id] = "WAITING_REGISTRATION_FULL"
            bot.send_message(
                message.chat.id, 
                f"{COMPANY_HEADER}🌟 <b>مرحباً بك في منظومة ARAMKY الاحترافية!</b> 🌟\n\n"
                "لتفعيل اشتراكك وتأمين حسابات محلك بدقة مطلقة، يرجى إرسال بياناتك بالترتيب التالي:\n\n"
                "🏢 <b>اسم المحل:</b> (مثال: مجوهرات الذهب الأخضر)\n"
                "📱 <b>رقم الهاتف:</b> (مثال: 07800000000)\n\n"
                "✍️ <i>أرسل المعلومات في رسالة واحدة:</i>", 
                parse_mode="HTML"
            )
            return

        remaining_days = gs.get('remaining_days', 0)
        if remaining_days <= 0 and not is_admin:
            show_subscription_form(message, expired=True)
            return

        USER_STATE.pop(user_id, None)
        send_main_menu(message, user_id)
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: message.text and message.text.strip() == TEXTS["btn_info"])
def show_system_info(message):
    user_id = message.from_user.id
    try:
        gs = utils.get_goldsmith(user_id) or {}
        remaining_days = gs.get('remaining_days', 0)
        info_text = (
            f"{COMPANY_HEADER}"
            "📖 <b>تفاصيل النظام ومعلومات الحساب:</b>\n\n"
            f"⏳ الأيام المتبقية للاشتراك: <b>{remaining_days} يوم</b>\n"
            "🔹 نظام حساب حر مباشر (سعر المثقال + الوزن + الأجور)\n"
            "🔹 مطابقة تامة لنتائج الحاسبة المكتبية بدون تقريب\n\n"
            f"📞 <b>الدعم الفني والطوارئ:</b> <code>{SUPPORT_NUMBER}</code>"
        )
        bot.send_message(message.chat.id, info_text, parse_mode="HTML")
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

def show_subscription_form(message, expired=False):
    user_id = message.from_user.id
    try:
        USER_STATE[user_id] = "WAITING_RECEIPT"
        prefix = "🚨 <b>انتهت فترتك التجريبية! يرجى التجديد للاستمرار:</b>\n\n" if expired else ""
        sub_text = (
            f"{COMPANY_HEADER}{prefix}"
            f"🔹 <b>الاشتراك الشهري:</b> <b>{MONTHLY_PRICE}</b>\n"
            f"🔹 <b>ماستر كارد التحويل:</b> <code>{MASTER_CARD}</code>\n"
            f"📞 <b>الدعم الفني:</b> <code>{SUPPORT_NUMBER}</code>\n\n"
            "📸 أرسل صورة وصل التحويل هنا لتفعيل اشتراكك."
        )
        bot.send_message(message.chat.id, sub_text, parse_mode="HTML")
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: message.text and message.text.strip() == "🛠️ لوحة تحكم الإدارة (خاص)")
def admin_panel_shortcut(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        try:
            admin.admin_panel_start(message, bot)
        except Exception as e:
            notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: message.text and message.text.strip() == TEXTS["btn_dollar"])
def dollar_management_menu(message):
    user_id = message.from_user.id
    try:
        current_p = utils.get_goldsmith_prices(user_id) or {}
        usd_rate = current_p.get('usd_rate', 1530)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔄 تعديل سعر الدولار الجديد", callback_data="edit_price_usd"))
        
        text = (
            f"{COMPANY_HEADER}"
            f"💵 <b>إدارة سعر الصرف الحالي:</b>\n\n"
            f"السعر المخزن حالياً: <code>{fmt(usd_rate)}</code>\n\n"
            "اضغط الزر أدناه لتحديثه:"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.callback_query_handler(func=lambda call: call.data == "edit_price_usd")
def handle_dollar_edit_callback(call):
    user_id = call.from_user.id
    try:
        bot.answer_callback_query(call.id, text="⏳ يرجى إرسال السعر...")
        USER_STATE[user_id] = "WAITING_SINGLE_PRICE_VALUE"
        bot.send_message(call.message.chat.id, "📝 <b>أرسل سعر صرف 100$ الجديد أو سعر الورقة:</b>", parse_mode="HTML")
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: message.text and message.text.strip() == TEXTS["btn_sell"])
def customer_sell_init(message):
    user_id = message.from_user.id
    try:
        USER_STATE[user_id] = "WAITING_SELL_INPUTS"
        bot.send_message(
            message.chat.id, 
            f"{COMPANY_HEADER}🛍️ <b>حساب بيع للزبون (طريقة حرة دقيقة):</b>\n\n"
            "أرسل القيم التالية في رسالة واحدة (كل قيمة بسطر):\n\n"
            "1️⃣ سعر المثقال\n"
            "2️⃣ الوزن بالغرام\n"
            "3️⃣ أجور صياغة الغرام", 
            parse_mode="HTML"
        )
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: message.text and message.text.strip() == TEXTS["btn_buy"])
def customer_buy_init(message):
    user_id = message.from_user.id
    try:
        USER_STATE[user_id] = "WAITING_BUY_INPUTS"
        bot.send_message(
            message.chat.id, 
            f"{COMPANY_HEADER}📥 <b>حساب شراء (كسر) من الزبون:</b>\n\n"
            "أرسل القيم التالية في رسالة واحدة (كل قيمة بسطر):\n\n"
            "1️⃣ سعر شراء المثقال\n"
            "2️⃣ الوزن بالغرام\n"
            "3️⃣ أجور الكسر للغرام", 
            parse_mode="HTML"
        )
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_invoice", "cancel_invoice"])
def handle_invoice_confirmation(call):
    user_id = call.from_user.id
    try:
        if call.data == "confirm_invoice":
            bot.answer_callback_query(call.id, text="✅ تمت العملية بنجاح!")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, "✅ <b>تم اعتماد الفاتورة بنجاح!</b> 💛", parse_mode="HTML")
        else:
            bot.answer_callback_query(call.id, text="❌ تم إلغاء العملية")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, "❌ <b>تم إلغاء الفاتورة.</b>", parse_mode="HTML")
        INVOICE_DATA.pop(user_id, None)
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

@bot.message_handler(func=lambda message: True)
def handle_text_inputs(message):
    user_id = message.from_user.id
    try:
        text = to_english_numbers(message.text.strip())
        state = USER_STATE.get(user_id)

        if state == "WAITING_REGISTRATION_FULL":
            loading = bot.send_message(message.chat.id, "⏳ <i>جاري تأسيس الحساب...</i>", parse_mode="HTML")
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            shop_name = lines[0] if len(lines) >= 1 else text
            phone = lines[1] if len(lines) >= 2 else "غير محدد"
            
            utils.register_goldsmith_details(user_id, shop_name, phone)
            USER_STATE.pop(user_id, None)
            bot.delete_message(message.chat.id, loading.message_id)
            bot.send_message(message.chat.id, "💎 <b>تم تسجيل محلك وتفعيل الفترة التجريبية بنجاح!</b>", parse_mode="HTML")
            send_main_menu(message, user_id)
            return

        if state == "WAITING_SINGLE_PRICE_VALUE":
            loading_msg = bot.send_message(message.chat.id, "⏳ <i>جاري تحديث سعر الدولار...</i>", parse_mode="HTML")
            if re.match(r'^\d+(\.\d+)?$', text):
                val = Decimal(text)
                usd_r = (val / Decimal('100') if val > Decimal('1000') else val)
                
                current_p = utils.get_goldsmith_prices(user_id) or {}
                utils.update_morning_prices(
                    user_id,
                    p24=float(current_p.get('price_24', 1020000)),
                    p22=float(current_p.get('price_22', 935000)),
                    p21=float(current_p.get('price_21', 900000)),
                    p18=float(current_p.get('price_18', 450000)),
                    p9=float(current_p.get('price_9', 400000)),
                    w24=float(current_p.get('wage_24', 3000)),
                    w22=float(current_p.get('wage_22', 3500)),
                    w21=float(current_p.get('wage_21', 4500)),
                    w18=float(current_p.get('wage_18', 7500)),
                    w9=float(current_p.get('wage_9', 2500)),
                    usd_r=float(usd_r)
                )
                USER_STATE.pop(user_id, None)
                bot.delete_message(message.chat.id, loading_msg.message_id)
                bot.send_message(message.chat.id, f"✅ <b>تم تحديث سعر الصرف بنجاح إلى:</b> <code>{fmt(usd_r * 100)}</code>", parse_mode="HTML")
            return

        if state == "WAITING_SELL_INPUTS":
            loading_msg = bot.send_message(message.chat.id, "⏳ <i>جاري الحساب بدقة الحاسبة...</i>", parse_mode="HTML")
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) == 3:
                mithqal_price = Decimal(lines[0])
                w = Decimal(lines[1])
                wage = Decimal(lines[2])
                
                gram_price = mithqal_price / Decimal('5')
                gram_full = gram_price + wage
                total_iqd = gram_full * w
                
                prices = utils.get_goldsmith_prices(user_id) or {}
                goldsmith = utils.get_goldsmith(user_id) or {}
                
                usd_rate_single = Decimal(str(prices.get('usd_rate', 1530)))
                sheet_price = usd_rate_single * Decimal('100') if usd_rate_single < Decimal('5000') else usd_rate_single
                usd_bills = int(total_iqd // sheet_price) if sheet_price > 0 else 0
                rem_iqd = total_iqd % sheet_price if sheet_price > 0 else total_iqd
                
                shop_name = goldsmith.get('full_name') or 'محلي الموقر'
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("✅ تأكيد العملية", callback_data="confirm_invoice"),
                    types.InlineKeyboardButton("❌ إلغاء العملية", callback_data="cancel_invoice")
                )
                
                invoice = (
                    f"{COMPANY_HEADER}{TEXTS['invoice_sell']}\n━━━━━━━━━━━━━━━━━\n"
                    f"{TEXTS['shop']}{shop_name}\n"
                    f"🟡 <b>سعر المثقال المعتمد:</b> <code>{fmt(mithqal_price)} دينار</code>\n"
                    f"{TEXTS['weight_tot'].format(w=float(w))}\n"
                    f"{TEXTS['wage_sell'].format(wage=fmt(wage))}\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"💰 <b>سعر غرام الصافي:</b> <code>{fmt(gram_price)} دينار</code>\n"
                    f"💵 <b>سعر غرام مع الأجور:</b> <code>{fmt(gram_full)} دينار</code>\n"
                    f"{TEXTS['total_iqd'].format(total=fmt(total_iqd))}\n\n"
                    f"{TEXTS['total_usd'].format(usd=usd_bills, rem=fmt(rem_iqd))}\n━━━━━━━━━━━━━━━━━\n{TEXTS['footer']}"
                )
                USER_STATE.pop(user_id, None)
                bot.delete_message(message.chat.id, loading_msg.message_id)
                bot.send_message(message.chat.id, invoice, parse_mode="HTML", reply_markup=markup)
            return

        if state == "WAITING_BUY_INPUTS":
            loading_msg = bot.send_message(message.chat.id, "⏳ <i>جاري الحساب...</i>", parse_mode="HTML")
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) == 3:
                mithqal_buy_price = Decimal(lines[0])
                w = Decimal(lines[1])
                wage_cut = Decimal(lines[2])
                
                gram_buy_price = mithqal_buy_price / Decimal('5')
                net_gram_price = gram_buy_price - wage_cut
                total_iqd = net_gram_price * w
                
                prices = utils.get_goldsmith_prices(user_id) or {}
                goldsmith = utils.get_goldsmith(user_id) or {}
                
                usd_rate_single = Decimal(str(prices.get('usd_rate', 1530)))
                sheet_price = usd_rate_single * Decimal('100') if usd_rate_single < Decimal('5000') else usd_rate_single
                usd_bills = int(total_iqd // sheet_price) if sheet_price > 0 else 0
                rem_iqd = total_iqd % sheet_price if sheet_price > 0 else total_iqd
                
                shop_name = goldsmith.get('full_name') or 'محلي الموقر'
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("✅ تأكيد العملية", callback_data="confirm_invoice"),
                    types.InlineKeyboardButton("❌ إلغاء العملية", callback_data="cancel_invoice")
                )
                
                invoice = (
                    f"{COMPANY_HEADER}{TEXTS['invoice_buy']}\n━━━━━━━━━━━━━━━━━\n"
                    f"{TEXTS['shop']}{shop_name}\n"
                    f"📥 <b>سعر شراء المثقال:</b> <code>{fmt(mithqal_buy_price)} دينار</code>\n"
                    f"{TEXTS['weight_tot'].format(w=float(w))}\n"
                    f"🔨 <b>أجور الخصم للغرام:</b> {fmt(wage_cut)} دينار\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"💰 <b>سعر غرام الكسر الصافي:</b> <code>{fmt(net_gram_price)} دينار</code>\n"
                    f"{TEXTS['total_iqd'].format(total=fmt(total_iqd))}\n\n"
                    f"{TEXTS['total_usd'].format(usd=usd_bills, rem=fmt(rem_iqd))}\n━━━━━━━━━━━━━━━━━\n{TEXTS['footer']}"
                )
                USER_STATE.pop(user_id, None)
                bot.delete_message(message.chat.id, loading_msg.message_id)
                bot.send_message(message.chat.id, invoice, parse_mode="HTML", reply_markup=markup)
            return
    except Exception as e:
        notify_admin_error(user_id, str(e), traceback.format_exc())

admin.register_admin_handlers(bot)

# نظام إرسال رسالة تذكير صباحية للصاغة كل يوم الساعة 10:00 صباحاً
def morning_reminder_scheduler():
    while True:
        try:
            now = time.localtime()
            # فحص إذا كان الوقت الساعة 10:00 صباحاً
            if now.tm_hour == 10 and now.tm_min == 0:
                all_users = utils.get_all_goldsmiths()
                for u in all_users:
                    u_id = u.get('user_id')
                    if u_id:
                        try:
                            bot.send_message(
                                u_id,
                                f"{COMPANY_HEADER}☀️ <b>صباح الخير ومبارك رزقكم!</b>\n\n"
                                "جاهزون لإدارة حسابات اليوم بدقة تامة ومطابقة للحاسبة. أرسل العمليات مباشرة عبر الأزرار أدناه 💛",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
                time.sleep(60) # الانتظار دقيقة حتى لا تتكرر الرسالة في نفس الدقيقة
        except Exception as e:
            print(f"Reminder error: {e}")
        time.sleep(30)

if __name__ == "__main__":
    # تشغيل خيط التذكير الصباحي في الخلفية
    reminder_thread = threading.Thread(target=morning_reminder_scheduler)
    reminder_thread.daemon = True
    reminder_thread.start()

    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    bot.infinity_polling(skip_pending=True)
