import os, re, time, json, random, requests, logging, threading, traceback
import telebot
import sqlite3
import string
from confings import *
from datetime import datetime
from telebot.types import ChatMemberUpdated
from buttons import *
from env import settings
from telebot import types
from jdatetime import datetime as jdatetime, timedelta
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import pytz
import schedule
from helpers import *
from invites_and_content import *
from admin_controls import *
from payments import *
from services_and_profiles import *


IRAN_TZ = pytz.timezone('Asia/Tehran')

rezerve_msgs = "-1002830098505"

stop_event = threading.Event()

temp_data = {}
temp_invite = {}
keyboards = {}
contents = {}
admin_states = {}
delete_states = {}
user_states = {}
registered_cards = []
user_cart_selections = {}
user_color_selection = {}
user_product_view = {}
user_cart_temp = {}
user_registration_state = {}
user_selected_services = {}

verify_active = True
bot_active = True
invite_diamond_count = 5000
pay_panel = "-1002893953705"
ORDER_REPORT_GROUP_ID = "-1002700736439"

bot = telebot.TeleBot(settings.token)

def send_error_to_admin(text: str):
    bot.send_message(settings.matin, f"⚠️ Error:\n<code>{text}</code>")
    
    
def handle_hidden_start_msgs(start_msg, chat_id, message):
    if start_msg.startswith("upload_"):
        tracking_code = start_msg.split("upload_")[1]  # استخراج کد پیگیری از پیام
        file_info = get_file_from_db(tracking_code)
        
        if file_info:
            file_id, file_type, caption = file_info
            send_file_by_type(chat_id, file_id, file_type, caption)
        else:
            bot.reply_to(message, "فایلی با این کد پیگیری پیدا نشد.", reply_markup=main_markup)
        
    elif start_msg.startswith("invite_"):
        inviter_chat_id = start_msg.split("invite_")[1]

        Chat = message.chat.id
        Chat_id = message.from_user.id
        first_name = message.from_user.first_name if message.from_user.first_name else " "
        last_name = message.from_user.last_name if message.from_user.last_name else " "
        username = message.from_user.username if message.from_user.username else " "

        # جلوگیری از دعوت خود توسط خود
        if str(inviter_chat_id) == str(Chat_id):
            bot.send_message(
                chat_id,
                "❌ عزیزم نمیتونی خودتو به ربات دعوت کنی! 😊",
                parse_mode="HTML",
                reply_markup=main_markup
            )
            return

        if not check_user_existence(Chat_id):
            new_invite_to_bot(inviter_chat_id, Chat_id, first_name, last_name)
            save_info(Chat_id, first_name, last_name, Chat, username)
            update_inviter_chatid(inviter_chat_id, Chat_id)
            save_invitation(Chat_id, inviter_chat_id)
            bot.send_message(chat_id, text=welcome_msg, parse_mode="HTML",reply_markup=main_markup)                 

        else:
            new_invite_to_bot(inviter_chat_id, Chat_id, first_name, last_name)
            save_info(Chat_id, first_name, last_name, Chat, username)
            bot.send_message(chat_id, text=welcome_msg, parse_mode="HTML",reply_markup=main_markup)                 
                        
    else:
        bot.send_message(chat_id, text=welcome_msg, parse_mode="HTML",reply_markup=main_markup)




@bot.message_handler(func=lambda message: message.text == "⚙️ تنظیم خدمات")
def setup_services(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ شما دسترسی لازم ندارید", reply_markup=main_markup)
        return
    
    msg = bot.send_message(chat_id, 
                          "💇🏻‍♂️ لطفاً نام خدمت مورد نظر را وارد کنید:\n\n"
                          "مثال: کوتاهی مو، رنگ مو، اپیلاسیون و...", 
                          reply_markup=back_markup)
    bot.register_next_step_handler(msg, get_service_name)

# بخش مدیریت پرسنل (ادمین)
@bot.message_handler(func=lambda message: message.text == "👥 افزودن پرسنل")
def add_staff(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ شما دسترسی لازم ندارید", reply_markup=main_markup)
        return
    
    msg = bot.send_message(chat_id, 
                          "👨‍💼 لطفاً نام پرسنل را وارد کنید:\n\n"
                          "مثال: آقای احمدی، خانم رضایی", 
                          reply_markup=back_markup)
    bot.register_next_step_handler(msg, get_staff_name)


@bot.message_handler(func=lambda message: message.text == "🗓️ رزرو وقت جدید")
def new_reservation(message):
    chat_id = message.chat.id

    # اگر کاربر در حال ثبت‌نام بوده، روند قبلی پاک شود
    if chat_id in user_registration_state:
        del user_registration_state[chat_id]

    # بررسی وجود اطلاعات کاربر
    if not check_user_info_exists(chat_id):
        # شروع فرآیند ثبت اطلاعات
        user_registration_state[chat_id] = 'waiting_for_full_name'
        bot.send_message(chat_id, 
                        "👋 سلام! برای رزرو وقت، ابتدا باید اطلاعات شما ثبت شود.\n\n"
                        "📝 <b>لطفاً نام کامل خود را وارد کنید:</b>", 
                        parse_mode="HTML", reply_markup=back_markup)
        return

    # ادامه روند در صورت وجود اطلاعات کاربر
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT money FROM users WHERE chat_id=?", (chat_id,))
            result = c.fetchone()
            if not result or result[0] <= 0:
                bot.send_message(chat_id, 
                               "❌ موجودی حساب شما کافی نیست\n\n"
                               "لطفاً ابتدا حساب خود را شارژ کنید", 
                               reply_markup=main_markup)
                return
    except Exception as e:
        bot.send_message(chat_id, "❌ خطا در بررسی موجودی", reply_markup=main_markup)
        return

    # نمایش لیست پرسنل
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT id, name FROM staff WHERE is_active=1")
            staff_list = c.fetchall()

            if not staff_list:
                bot.send_message(chat_id, "❌ هیچ پرسنلی ثبت نشده است", reply_markup=main_markup)
                return

            markup = telebot.types.InlineKeyboardMarkup()
            for staff_id, staff_name in staff_list:
                markup.add(telebot.types.InlineKeyboardButton(
                    f"👤 {staff_name}", 
                    callback_data=f"select_staff_{staff_id}"
                ))
            markup.add(telebot.types.InlineKeyboardButton(f"❌ خروج از منوی رزرو", callback_data=f"delete_button_1"))

            bot.send_message(chat_id, 
                           "👥 <b>پرسنل مورد نظر خود را انتخاب کنید:</b>", 
                           parse_mode="HTML", reply_markup=markup)

    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در نمایش پرسنل: {e}", reply_markup=main_markup)

@bot.message_handler(func=lambda message: message.chat.id in user_registration_state)
def handle_registration(message):
    if check_return(message):
        chat_id = message.chat.id
        if chat_id in user_registration_state:
            del user_registration_state[chat_id]
        return
    
    chat_id = message.chat.id
    state = user_registration_state.get(chat_id)
    
    if state == 'waiting_for_full_name':
        # ذخیره نام کامل
        full_name = message.text.strip()
        if len(full_name) < 3:
            bot.send_message(chat_id, "❌ نام کامل باید حداقل 3 کاراکتر باشد. لطفاً دوباره وارد کنید:")
            return
        
        user_registration_state[chat_id] = {'step': 'waiting_for_phone', 'full_name': full_name}
    
        bot.send_message(chat_id,
                         f"✅ نام کامل: <b>{full_name}</b>\n\n"
                         "📱 <b>لطفاً شماره تلفن خود را ارسال کنید:</b>\n",
                         parse_mode="HTML", reply_markup=back_markup)
    
    elif isinstance(state, dict) and state.get('step') == 'waiting_for_phone':
        # پردازش شماره تلفن
        phone_number = None
        
        if message.contact:
            phone_number = message.contact.phone_number
        else:
            # بررسی فرمت شماره تلفن
            phone_text = message.text.strip()
            # حذف کاراکترهای اضافی
            phone_cleaned = ''.join(filter(str.isdigit, phone_text))
            
            if len(phone_cleaned) >= 10:
                phone_number = phone_cleaned
            else:
                bot.send_message(chat_id, 
                               "❌ شماره تلفن نامعتبر است. لطفاً شماره صحیح وارد کنید:", 
                               reply_markup=back_markup)
                return
        
        # ذخیره اطلاعات در دیتابیس
        if save_user_info(chat_id, state['full_name'], phone_number):
            # پاک کردن state
            del user_registration_state[chat_id]
            
            bot.send_message(chat_id, 
                           "✅ <b>اطلاعات شما با موفقیت ثبت شد!</b>\n\n"
                           f"👤 نام کامل: {state['full_name']}\n"
                           f"📱 تلفن: {phone_number}\n\n"
                           "🗓️ حالا می‌توانید وقت رزرو کنید.", 
                           parse_mode="HTML", reply_markup=main_markup)
            
            # بازگشت به فرآیند رزرو
            new_reservation(message)
        else:
            bot.send_message(chat_id, 
                           "❌ خطا در ثبت اطلاعات. لطفاً دوباره تلاش کنید.", 
                           reply_markup=main_markup)
            if chat_id in user_registration_state:
                del user_registration_state[chat_id]



# انتخاب پرسنل
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_staff_'))
def select_staff(call):
    chat_id = call.message.chat.id
    staff_id = int(call.data.split('_')[2])
    
    try:
        # دریافت نام پرسنل
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM staff WHERE id=?", (staff_id,))
            result = c.fetchone()
            if not result:
                bot.answer_callback_query(call.id, "❌ پرسنل یافت نشد")
                return
            staff_name = result[0]
        
        bot.edit_message_text(
            f"✅ پرسنل انتخاب شده: <b>{staff_name}</b>", 
            chat_id, call.message.message_id, parse_mode="HTML"
        )
        
        # نمایش خدمات
        show_services(chat_id, staff_id)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا: {e}", reply_markup=main_markup)

def show_services(chat_id, staff_id):
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT id, name, price FROM services WHERE is_active=1")
            services = c.fetchall()
            
            if not services:
                bot.send_message(chat_id, "❌ هیچ خدماتی ثبت نشده است", reply_markup=main_markup)
                return
            
            markup = telebot.types.InlineKeyboardMarkup()
            for service_id, service_name, price in services:
                markup.add(telebot.types.InlineKeyboardButton(
                    f"💇🏻‍♂️ {service_name} - {price:,} تومان", 
                    callback_data=f"toggle_service_{staff_id}_{service_id}"
                ))
            markup.add(telebot.types.InlineKeyboardButton(
                "✅ ادامه و انتخاب روز", 
                callback_data=f"confirm_services_{staff_id}"
            ))
            markup.add(telebot.types.InlineKeyboardButton(f"❌ خروج از منوی رزرو", callback_data=f"delete_button_1"))

            bot.send_message(chat_id, 
                           "💇🏻‍♂️ <b>خدمات مورد نظر خود را انتخاب کنید:</b>\n\n"
                           "می‌توانید چندین خدمت انتخاب کنید", 
                           parse_mode="HTML", reply_markup=markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در نمایش خدمات: {e}", reply_markup=main_markup)

# انتخاب خدمات
@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_service_'))
def toggle_service(call):
    chat_id = call.message.chat.id
    parts = call.data.split('_')
    staff_id = int(parts[2])
    service_id = int(parts[3])
    
    # مدیریت خدمات انتخابی
    if chat_id not in user_selected_services:
        user_selected_services[chat_id] = {'staff_id': staff_id, 'services': []}
    
    if service_id in user_selected_services[chat_id]['services']:
        user_selected_services[chat_id]['services'].remove(service_id)
    else:
        user_selected_services[chat_id]['services'].append(service_id)
    
    # به‌روزرسانی کیبورد
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT id, name, price FROM services WHERE is_active=1")
            services = c.fetchall()
            
            markup = telebot.types.InlineKeyboardMarkup()
            for s_id, s_name, price in services:
                if s_id in user_selected_services[chat_id]['services']:
                    text = f"✅ {s_name} - {price:,} تومان"
                else:
                    text = f"💇🏻‍♂️ {s_name} - {price:,} تومان"
                
                markup.add(telebot.types.InlineKeyboardButton(
                    text, 
                    callback_data=f"toggle_service_{staff_id}_{s_id}"
                ))
            
            markup.add(telebot.types.InlineKeyboardButton(
                "✅ ادامه", 
                callback_data=f"confirm_services_{staff_id}"
            ))
            
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطا: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_services_'))
def confirm_services(call):
    chat_id = call.message.chat.id
    staff_id = int(call.data.split('_')[2])
    
    if chat_id not in user_selected_services or not user_selected_services[chat_id]['services']:
        bot.answer_callback_query(call.id, "❌ لطفاً حداقل یک خدمت انتخاب کنید")
        return
    
    bot.edit_message_text(
        "✅ خدمات انتخاب شدند", 
        chat_id, call.message.message_id
    )
    
    # نمایش روزهای هفته
    show_weekdays(chat_id, staff_id)

def show_weekdays(chat_id, staff_id):
    markup = telebot.types.InlineKeyboardMarkup()
    days = [
        ('saturday', 'شنبه'), ('sunday', 'یکشنبه'),
        ('monday', 'دوشنبه'), ('tuesday', 'سه‌شنبه'),
        ('wednesday', 'چهارشنبه'), ('thursday', 'پنج‌شنبه'),
        ('friday', 'جمعه')
    ]
    
    # دو روز در هر ردیف
    for i in range(0, len(days), 2):
        row = []
        for j in range(2):
            if i + j < len(days):
                day_en, day_fa = days[i + j]
                row.append(telebot.types.InlineKeyboardButton(
                    f"📅 {day_fa}", 
                    callback_data=f"select_day_{staff_id}_{day_en}"
                ))
        markup.row(*row)
    
    markup.add(telebot.types.InlineKeyboardButton(f"❌ خروج از منوی رزرو", callback_data=f"delete_button_1"))
    bot.send_message(chat_id, 
                   "📅 <b>روز مورد نظر خود را انتخاب کنید:</b>", 
                   parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_day_'))
def select_day(call):
    chat_id = call.message.chat.id
    parts = call.data.split('_')
    staff_id = int(parts[2])
    day_en = parts[3]

    # تاریخ و زمان جاری
    current_dt = get_current_datetime()

    # تبدیل روز هفته پایتون (دوشنبه = 0) به شمسی (شنبه = 0)
    def gregorian_to_iranian_weekday(py_weekday):
        return (py_weekday + 2) % 7  # چون شنبه = 5 در پایتون، پس (5+2)%7 = 0 (شنبه)

    # نگاشت روزهای انگلیسی به شماره هفته با شروع از شنبه
    day_mapping = {
        'saturday': 0,
        'sunday': 1,
        'monday': 2,
        'tuesday': 3,
        'wednesday': 4,
        'thursday': 5,
        'friday': 6
    }

    selected_day_num = day_mapping[day_en]
    current_day_num = gregorian_to_iranian_weekday(current_dt.weekday())

    # اگر روز انتخابی قبل از امروز باشد
    if selected_day_num < current_day_num:
        bot.answer_callback_query(call.id, "❌ نمی‌توان برای روزهای گذشته رزرو انجام داد")
        return

    bot.edit_message_text(
        f"✅ روز انتخاب شده: {get_weekday_name_fa(selected_day_num)}", 
        chat_id, call.message.message_id
    )

    # نمایش ساعات قابل رزرو
    show_time_slots(chat_id, staff_id, day_en)

    
def show_time_slots(chat_id, staff_id, day):
    try:
        # دریافت زمان فعلی ایران
        current_dt = get_current_datetime()
        current_hour = current_dt.hour
        current_minute = current_dt.minute
        
        # نقشه روزهای انگلیسی به شماره روز هفته پایتون
        day_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        selected_day_num = day_mapping[day]
        current_day_num = current_dt.weekday()
        is_today = (selected_day_num == current_day_num)

        # دریافت ساعات رزرو شده برای این پرسنل و روز
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT time_slot FROM reservations WHERE staff_id=? AND day=?", 
                     (staff_id, day))
            # لیست دقیق ساعت‌های رزرو شده
            reserved_slots = set(row[0].strip() for row in c.fetchall())

        markup = telebot.types.InlineKeyboardMarkup()
        available_slots = 0

        for hour in range(8, 24, 2):
            row_buttons = []
            for h in [hour, hour + 1]:
                if h >= 24:
                    break

                time_slot = f"{h:02d}:00:{h+1:02d}:00"
                is_past_time = False

                if is_today:
                    if h < current_hour:
                        is_past_time = True
                    elif h == current_hour and current_minute > 0:
                        is_past_time = True

                # بررسی رزرو شدن
                is_reserved = time_slot in reserved_slots

                # تعیین دکمه‌ها
                if is_past_time:
                    text = f"⏰ {time_slot}"
                    callback_data = "past_time"
                elif is_reserved:
                    text = f"✅ {time_slot}"
                    callback_data = f"reserved_{staff_id}_{day}_{h}"
                else:
                    text = f"🔘 {time_slot}"
                    callback_data = f"select_time_{staff_id}_{day}_{h}"
                    available_slots += 1

                row_buttons.append(telebot.types.InlineKeyboardButton(text, callback_data=callback_data))
            
            if row_buttons:
                markup.row(*row_buttons)
                
        markup.add(telebot.types.InlineKeyboardButton(f"❌ خروج از منوی رزرو", callback_data=f"delete_button_1"))
        # پیام راهنما
        guide_text = "🕐 <b>ساعت مورد نظر خود را انتخاب کنید:</b>\n\n"
        guide_text += "🔘 قابل رزرو (از این ساعت‌ها انتخاب کنید)\n"
        guide_text += "✅ رزرو شده (غیرقابل انتخاب)\n"
        if is_today:
            guide_text += "⏰ گذشته (غیرقابل رزرو)\n"

        if available_slots == 0:
            if is_today:
                guide_text += "\n❌ <b>تمام ساعات امروز رزرو شده یا گذشته‌اند.</b>"
            else:
                guide_text += "\n❌ <b>تمام ساعات این روز قبلاً رزرو شده‌اند.</b>"
        else:
            guide_text += f"\n✨ <b>{available_slots} ساعت قابل رزرو موجود است.</b>"

        bot.send_message(chat_id, guide_text, parse_mode="HTML", reply_markup=markup)

    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در نمایش ساعات: {e}", reply_markup=main_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reserved_'))
def reserved_slot_with_suggestion(call):
    """پاسخ به انتخاب ساعت رزرو شده با پیشنهاد ساعت‌های آزاد"""
    bot.answer_callback_query(call.id, "❌ این ساعت رزرو شده است! لطفاً از ساعت‌هایی که علامت 🔘 دارند انتخاب کنید", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'reserved')
def reserved_slot(call):
    bot.answer_callback_query(call.id, "❌ این ساعت قبلاً رزرو شده است", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'past_time')
def past_time_slot(call):
    bot.answer_callback_query(call.id, "⏰ نمی‌توان برای ساعات گذشته رزرو انجام داد", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_time_'))
def select_time(call):
    chat_id = call.message.chat.id
    parts = call.data.split('_')
    staff_id = int(parts[2])
    day = parts[3]
    hour = int(parts[4])
    
    # بررسی مجدد اینکه ساعت در گذشته نباشد (امنیت اضافی)
    current_dt = get_current_datetime()
    
    day_mapping = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    selected_day_num = day_mapping[day]
    current_day_num = current_dt.weekday()
    is_today = (selected_day_num == current_day_num)
    
    if is_today:
        current_hour = current_dt.hour
        current_minute = current_dt.minute
        
        if hour < current_hour or (hour == current_hour and current_minute > 0):
            bot.answer_callback_query(call.id, "⏰ این ساعت در گذشته است و قابل رزرو نیست", show_alert=True)
            return
    
    # بررسی دوباره که ساعت رزرو نشده باشد
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            time_slot = f"{hour:02d}:00-{hour+1:02d}:00"
            c.execute("SELECT id FROM reservations WHERE staff_id=? AND day=? AND time_slot=?", 
                     (staff_id, day, time_slot))
            if c.fetchone():
                bot.answer_callback_query(call.id, "❌ این ساعت به تازگی رزرو شده است", show_alert=True)
                return
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطا در بررسی: {e}", show_alert=True)
        return
    
    time_slot = f"{hour:02d}:00-{hour+1:02d}:00"
    
    bot.edit_message_text(
        f"✅ ساعت انتخاب شده: {time_slot}", 
        chat_id, call.message.message_id
    )
    
    # نمایش خلاصه نهایی
    show_final_summary(chat_id, staff_id, day, time_slot)

def show_final_summary(chat_id, staff_id, day, time_slot):
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # دریافت اطلاعات پرسنل
            c.execute("SELECT name FROM staff WHERE id=?", (staff_id,))
            result = c.fetchone()
            if not result:
                bot.send_message(chat_id, "❌ خطا در یافتن پرسنل", reply_markup=main_markup)
                return
            staff_name = result[0]
            
            # دریافت اطلاعات خدمات انتخابی
            service_ids = user_selected_services[chat_id]['services']
            if not service_ids:
                bot.send_message(chat_id, "❌ هیچ خدماتی انتخاب نشده", reply_markup=main_markup)
                return
                
            placeholders = ','.join(['?'] * len(service_ids))
            c.execute(f"SELECT name, price FROM services WHERE id IN ({placeholders})", service_ids)
            services = c.fetchall()
            
            total_price = sum(price for _, price in services)
            services_text = '\n'.join([f"💇🏻‍♂️ {name} - {price:,} تومان" for name, price in services])
            
            # نام روز به فارسی
            day_mapping = {
                'saturday': 'شنبه', 'sunday': 'یکشنبه', 'monday': 'دوشنبه',
                'tuesday': 'سه‌شنبه', 'wednesday': 'چهارشنبه', 
                'thursday': 'پنج‌شنبه', 'friday': 'جمعه'
            }
            
            summary_text = f"""
📋 <b>خلاصه رزرو شما:</b>

👤 <b>پرسنل:</b> {staff_name}
📅 <b>روز:</b> {day_mapping[day]}
🕐 <b>ساعت:</b> {time_slot}

💇🏻‍♂️ <b>خدمات:</b>
{services_text}

💰 <b>مبلغ کل:</b> {total_price:,} تومان

آیا مطمئن هستید که می‌خواهید رزرو خود را انجام دهید؟
"""
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton(
                    "✅ تایید رزرو", 
                    callback_data=f"confirm_reservation_{staff_id}_{day}_{time_slot.replace(':', '-')}"
                ),
                telebot.types.InlineKeyboardButton(
                    "❌ لغو", 
                    callback_data="cancel_reservation"
                )
            )
            
            bot.send_message(chat_id, summary_text, parse_mode="HTML", reply_markup=markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در نمایش خلاصه: {e}", reply_markup=main_markup)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_reservation')
def cancel_reservation(call):
    chat_id = call.message.chat.id
    
    # پاک کردن خدمات انتخابی
    if chat_id in user_selected_services:
        del user_selected_services[chat_id]
    
    bot.edit_message_text("❌ رزرو لغو شد", chat_id, call.message.message_id)
    bot.send_message(chat_id, "✅ به منوی اصلی برگشتید ", reply_markup=main_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_reservation_'))
def confirm_reservation(call):
    chat_id = call.message.chat.id
    parts = call.data.split('_')
    staff_id = int(parts[2])
    day = parts[3]
    time_slot = parts[4].replace('-', ':')
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # بررسی دوباره که ساعت رزرو نشده باشد
            c.execute("SELECT id FROM reservations WHERE staff_id=? AND day=? AND time_slot=?", 
                     (staff_id, day, time_slot))
            if c.fetchone():
                bot.answer_callback_query(call.id, "❌ این ساعت به تازگی توسط شخص دیگری رزرو شده است")
                bot.edit_message_text("❌ متأسفانه این ساعت به تازگی رزرو شده است. لطفاً ساعت دیگری انتخاب کنید.", 
                                    chat_id, call.message.message_id)
                return
            
            # بررسی موجودی کاربر
            c.execute("SELECT money FROM users WHERE chat_id=?", (chat_id,))
            result = c.fetchone()
            if not result:
                bot.answer_callback_query(call.id, "❌ کاربر یافت نشد")
                return
            user_money = result[0]
            
            # محاسبه قیمت کل
            if chat_id not in user_selected_services:
                bot.answer_callback_query(call.id, "❌ خدماتی انتخاب نشده")
                return
                
            service_ids = user_selected_services[chat_id]['services']
            placeholders = ','.join(['?'] * len(service_ids))
            c.execute(f"SELECT price FROM services WHERE id IN ({placeholders})", service_ids)
            total_price = sum(row[0] for row in c.fetchall())
            
            if user_money < total_price:
                bot.answer_callback_query(call.id, "❌ موجودی شما کافی نیست")
                return
            
            # ثبت رزرو
            services_json = ','.join(map(str, service_ids))
            created_at = get_current_datetime().strftime("%Y-%m-%d %H:%M:%S")
            
            c.execute("""INSERT INTO reservations 
                        (user_id, staff_id, services, day, time_slot, total_price, status, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?)""",
                     (chat_id, staff_id, services_json, day, time_slot, total_price, created_at))
            
            # کسر مبلغ از حساب کاربر
            new_balance = user_money - total_price
            c.execute("UPDATE users SET money=? WHERE chat_id=?", (new_balance, chat_id))
            
            conn.commit()
            
            # اطلاع به کاربر
            bot.edit_message_text(
                f"✅ رزرو شما با موفقیت انجام شد!\n\n"
                f"💰 مبلغ {total_price:,} تومان از حساب شما کسر شد\n"
                f"💳 موجودی باقیمانده: {new_balance:,} تومان",
                chat_id, call.message.message_id
            )
            
            # ارسال اطلاعات رزرو به ادمین
            send_reservation_to_admin(chat_id, staff_id, day, time_slot, service_ids, total_price)
            
            # پاک کردن خدمات انتخابی
            if chat_id in user_selected_services:
                del user_selected_services[chat_id]
            
            bot.send_message(chat_id, "✅ به منوی اصلی برگشتید ", reply_markup=main_markup)

            try:
                # اطلاعات رزرو
                payload = {
                    "database_name": settings.database,     # نام دیتابیس فعلی، مثلاً 'barbershop1.db'
                    "reservation": {
                        "user_id": chat_id,
                        "staff_id": staff_id,
                        "services": service_ids,            # لیست آیدی سرویس‌ها
                        "day": day,
                        "time_slot": time_slot,
                        "total_price": total_price,
                        "created_at": created_at,           # زمان رزرو
                    }
                }
                headers = {"Authorization": ";suirw[gjvno;hwiw[ue99348tylulig;]]"}
                requests.post(
                    "https://api.telbotland.ir/api/new_reservation",
                    json=payload,
                    headers=headers,
                    timeout=3
                )
            except Exception as e:
                print(f"Error sending reservation to internal server: {e}")

    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در ثبت رزرو: {e}", reply_markup=main_markup)

def send_reservation_to_admin(user_chat_id, staff_id, day, time_slot, service_ids, total_price):
    """ارسال اطلاعات رزرو جدید به ادمین"""
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # اطلاعات کاربر از جدول users
            c.execute("SELECT first_name, last_name, user_name FROM users WHERE chat_id=?", (user_chat_id,))
            user_info = c.fetchone()
            if user_info:
                user_name = f"{user_info[0]} {user_info[1] or ''}".strip()
                username = f"@{user_info[2]}" if user_info[2] else "ندارد"
            else:
                user_name = "نامشخص"
                username = "ندارد"
            
            # اطلاعات کامل کاربر از جدول user_info
            c.execute("SELECT full_name, phone_number FROM user_info WHERE chat_id=?", (user_chat_id,))
            user_detail = c.fetchone()
            if user_detail:
                full_name = user_detail[0]
                phone_number = user_detail[1]
            else:
                full_name = user_name
                phone_number = "ثبت نشده"
            
            # اطلاعات پرسنل
            c.execute("SELECT name FROM staff WHERE id=?", (staff_id,))
            staff_result = c.fetchone()
            staff_name = staff_result[0] if staff_result else "نامشخص"
            
            # اطلاعات خدمات
            placeholders = ','.join(['?'] * len(service_ids))
            c.execute(f"SELECT name FROM services WHERE id IN ({placeholders})", service_ids)
            services_names = [row[0] for row in c.fetchall()]
            
            # نام روز
            day_mapping = {
                'saturday': 'شنبه', 'sunday': 'یکشنبه', 'monday': 'دوشنبه',
                'tuesday': 'سه‌شنبه', 'wednesday': 'چهارشنبه', 
                'thursday': 'پنج‌شنبه', 'friday': 'جمعه'
            }
            
            admin_message = f"""
🔔 <b>رزرو جدید دریافت شد!</b>

👤 <b>نام کامل:</b> {full_name}
📞 <b>شماره تلفن:</b> {phone_number}
🏷️ <b>یوزرنیم:</b> {username}
🏷️ <b>آیدی عددی:</b> <code>{user_chat_id}</code>

👨‍💼 <b>پرسنل:</b> {staff_name}
📅 <b>روز:</b> {day_mapping.get(day, day)}
🕐 <b>ساعت:</b> {time_slot}

💇🏻‍♂️ <b>خدمات:</b>
{chr(10).join([f"• {service}" for service in services_names])}

💰 <b>مبلغ کل:</b> {total_price:,} تومان

📅 <b>تاریخ ثبت:</b> {get_current_datetime().strftime('%Y/%m/%d - %H:%M')}
"""
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔧 مدیریت رزرو", callback_data=f"mngres_{user_chat_id}_{day}_{time_slot.replace(':','-')}"))


            try:
                bot.send_message(rezerve_msgs, admin_message, parse_mode="HTML", reply_markup=markup)
            except Exception as e:
                print(f"خطا در ارسال به کانال ادمین: {e}")
        
    except Exception as e:
        print(f"خطا در ارسال به ادمین: {e}")
        
        
@bot.callback_query_handler(func=lambda call: call.data.startswith('mngres_'))
def manage_reservation(call):
    _, user_chat_id, day, time_slot = call.data.split("_", 3)

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("❌ لغو رزرو", callback_data=f"cnclres_{user_chat_id}_{day}_{time_slot}"),
        InlineKeyboardButton("🔙 منوی مدیریت", callback_data=f"backadm_mngres_{user_chat_id}_{day}_{time_slot}")
    )

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cnclres_'))
def cancel_reservation_admin(call):
    _, user_chat_id, day, time_slot = call.data.split("_", 3)

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💰 برگشت کل مبلغ", callback_data=f"rfndf_{user_chat_id}_{day}_{time_slot}"),
        InlineKeyboardButton("💳 کارمزد 15%", callback_data=f"rfndp_{user_chat_id}_{day}_{time_slot}")
    )
    markup.add(
        InlineKeyboardButton("🔙 منوی مدیریت", callback_data=f"backadm_cnclres_{user_chat_id}_{day}_{time_slot}")
    )

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    
@bot.callback_query_handler(func=lambda call: call.data.startswith(('rfndf_', 'rfndp_')))
def process_refund(call):
    action, user_chat_id, day, time_slot = call.data.split("_", 3)
    user_chat_id = int(user_chat_id)
    db_time_slot = time_slot.replace('-', ':')

    with sqlite3.connect(settings.database) as conn:
        c = conn.cursor()
        # پیدا کردن رزرو فعال
        c.execute("SELECT id, total_price, status FROM reservations WHERE user_id=? AND day=? AND time_slot=?",
                  (user_chat_id, day, db_time_slot))
        reservation = c.fetchone()

        if not reservation:
            bot.answer_callback_query(call.id, "❌ رزرو پیدا نشد یا قبلاً لغو شده است.", show_alert=True)
            return

        reservation_id, total_price, status = reservation

        # اگر همین الان حذف شده بود (به هر دلیل)
        if status == "cancelled":
            bot.answer_callback_query(call.id, "این رزرو قبلاً لغو شده است.", show_alert=True)
            return

        # محاسبه مبلغ بازگشتی و متن اطلاع‌رسانی
        if action == "rfndp":
            refund_amount = int(total_price * 0.85)
            fee = total_price - refund_amount
            refund_text = f"۱۵٪ کارمزد به مبلغ {fee:,} تومان کسر شد و مابقی ({refund_amount:,} تومان) به حساب شما بازگردانده شد."
        else:
            refund_amount = total_price
            refund_text = f"کل مبلغ ({refund_amount:,} تومان) به حساب شما بازگردانده شد."

        # واریز مبلغ به کیف پول کاربر
        c.execute("UPDATE users SET money = money + ? WHERE chat_id = ?", (refund_amount, user_chat_id))
        # حذف رزرو از دیتابیس
        c.execute("DELETE FROM reservations WHERE id=?", (reservation_id,))
        conn.commit()

    # پیام به مشتری
    try:
        bot.send_message(user_chat_id,
            f"""❌ رزرو شما لغو شد.

{refund_text}

💳 مبلغ بازگشتی به کیف پول شما واریز شد و قابل استفاده برای رزرو بعدی است.

اگر سوال یا مشکلی داشتید، با پشتیبانی تماس بگیرید:
☎️ <b>+98 912 687 4628</b>
""", parse_mode="HTML", reply_markup=main_markup)
    except Exception as e:
        print(f"خطا در ارسال پیام به کاربر: {e}")

    # پیام به ادمین
    bot.edit_message_text("✅ عملیات لغو رزرو و حذف از دیتابیس با موفقیت انجام شد.", call.message.chat.id, call.message.message_id)



@bot.callback_query_handler(func=lambda call: call.data.startswith('backadm_'))
def back_to_previous_menu(call):
    parts = call.data.split("_", 2)
    previous_menu = parts[1]

    if previous_menu == "mngres":
        _, _, user_chat_id, day, time_slot = call.data.split("_", 4)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔧 مدیریت رزرو", callback_data=f"mngres_{user_chat_id}_{day}_{time_slot}"))
    elif previous_menu == "cnclres":
        _, _, user_chat_id, day, time_slot = call.data.split("_", 4)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔧 مدیریت رزرو", callback_data=f"mngres_{user_chat_id}_{day}_{time_slot}"))
    else:
        bot.answer_callback_query(call.id, "❌ منوی قبلی پیدا نشد.")
        return

    # --- بررسی ویرایش نکردن اگر markup تغییری نکرده ---
    if call.message.reply_markup and call.message.reply_markup.to_dict() == markup.to_dict():
        # همین markup قبلاً بوده! هیچ ویرایشی انجام نده فقط یه تایید بده
        bot.answer_callback_query(call.id, "در همین منو قرار دارید.")
    else:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)




@bot.message_handler(func=lambda message: message.text == "📋 رزروهای من")
def my_reservations(message):
    chat_id = message.chat.id
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("""SELECT r.id, s.name, r.day, r.time_slot, r.total_price, r.status, r.created_at
                        FROM reservations r
                        JOIN staff s ON r.staff_id = s.id
                        WHERE r.user_id = ?
                        ORDER BY r.created_at DESC
                        LIMIT 10""", (chat_id,))
            reservations = c.fetchall()
            
            if not reservations:
                bot.send_message(chat_id, "📋 شما هیچ رزروی ندارید", reply_markup=main_markup)
                return
            
            # نام روزها
            day_mapping = {
                'saturday': 'شنبه', 'sunday': 'یکشنبه', 'monday': 'دوشنبه',
                'tuesday': 'سه‌شنبه', 'wednesday': 'چهارشنبه', 
                'thursday': 'پنج‌شنبه', 'friday': 'جمعه'
            }
            
            message_text = "📋 <b>رزروهای شما:</b>\n\n"
            
            for i, (res_id, staff_name, day, time_slot, price, status, created_at) in enumerate(reservations, 1):
                status_emoji = "✅" if status == "confirmed" else "❌"
                day_fa = day_mapping.get(day, day)
                
                message_text += f"{i}. {status_emoji} <b>{staff_name}</b>\n"
                message_text += f"   📅 {day_fa} - 🕐 {time_slot}\n"
                message_text += f"   💰 {price:,} تومان\n"
                message_text += f"   📅 {created_at}\n\n"
            
            bot.send_message(chat_id, message_text, parse_mode="HTML", reply_markup=main_markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در نمایش رزروها: {e}", reply_markup=main_markup)


create_tables()




# مشاهده رزروهای کاربر
@bot.message_handler(func=lambda message: message.text == "📖 مشاهده رزروهای من")
def view_my_reservations(message):
    chat_id = message.chat.id
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("""SELECT r.id, s.name, r.day, r.time_slot, r.total_price, r.created_at
                        FROM reservations r 
                        JOIN staff s ON r.staff_id = s.id 
                        WHERE r.user_id = ? 
                        ORDER BY r.created_at DESC 
                        LIMIT 5""", (chat_id,))
            reservations = c.fetchall()
            
            if not reservations:
                bot.send_message(chat_id, 
                               "📋 شما هیچ رزرو فعالی ندارید\n\n"
                               "برای رزرو جدید از دکمه «🗓️ رزرو وقت جدید» استفاده کنید", 
                               reply_markup=main_markup)
                return
            
            # نام روزها
            day_mapping = {
                'saturday': 'شنبه', 'sunday': 'یکشنبه', 'monday': 'دوشنبه',
                'tuesday': 'سه‌شنبه', 'wednesday': 'چهارشنبه', 
                'thursday': 'پنج‌شنبه', 'friday': 'جمعه'
            }
            
            reservations_text = "📋 <b>رزروهای شما:</b>\n\n"
            
            for i, (res_id, staff_name, day, time_slot, price, created_at) in enumerate(reservations, 1):
                reservations_text += f"""
<b>{i}.</b> 
👨‍💼 <b>پرسنل:</b> {staff_name}
📅 <b>روز:</b> {day_mapping.get(day, day)}
🕐 <b>ساعت:</b> {time_slot}
💰 <b>مبلغ:</b> {price:,} تومان
📅 <b>تاریخ ثبت:</b> {created_at}
➖➖➖➖➖➖➖➖➖➖
"""
            
            bot.send_message(chat_id, reservations_text, parse_mode="HTML", reply_markup=main_markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در نمایش رزروها: {e}", reply_markup=main_markup)

# مشاهده موجودی حساب

# بازگشت به منوی اصلی برای ادمین
@bot.message_handler(func=lambda message: message.text == "🔙 بازگشت به منوی اصلی")
def back_to_main(message):
    chat_id = message.chat.id
    if is_admin(chat_id):
        bot.send_message(chat_id, "🏠 منوی اصلی", reply_markup=main_markup)
    else:
        bot.send_message(chat_id, "🏠 منوی اصلی", reply_markup=main_markup)

# گزارش رزروها برای ادمین
@bot.message_handler(func=lambda message: message.text == "📊 گزارش رزروها")
def reservation_report(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ شما دسترسی لازم ندارید", reply_markup=main_markup)
        return
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # تعداد کل رزروها
            c.execute("SELECT COUNT(*) FROM reservations")
            total_reservations = c.fetchone()[0]
            
            # درآمد کل
            c.execute("SELECT SUM(total_price) FROM reservations")
            total_income = c.fetchone()[0] or 0
            
            # رزروهای امروز
            today = get_current_datetime().strftime("%Y-%m-%d")
            c.execute("SELECT COUNT(*) FROM reservations WHERE DATE(created_at) = ?", (today,))
            today_reservations = c.fetchone()[0]
            
            # درآمد امروز
            c.execute("SELECT SUM(total_price) FROM reservations WHERE DATE(created_at) = ?", (today,))
            today_income = c.fetchone()[0] or 0
            
            report_text = f"""
📊 <b>گزارش رزروها:</b>

📈 <b>کل:</b>
🗓️ تعداد رزروها: {total_reservations}
💰 درآمد کل: {total_income:,} تومان

📅 <b>امروز:</b>
🗓️ تعداد رزروها: {today_reservations}
💰 درآمد امروز: {today_income:,} تومان

📅 <b>تاریخ گزارش:</b> {get_current_datetime().strftime('%Y/%m/%d - %H:%M')}
"""
            
            bot.send_message(chat_id, report_text, parse_mode="HTML", reply_markup=admin_markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در تهیه گزارش: {e}", reply_markup=admin_markup)

# تابع ریست هفتگی رزروها
def reset_weekly_reservations():
    """ریست کردن رزروها در روز جمعه ساعت 23:59"""
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM reservations")
            conn.commit()
            print(f"✅ رزروها با موفقیت ریست شدند - {get_current_datetime()}")
            
            # اطلاع به ادمین‌ها
            reset_message = f"""
🔄 <b>ریست هفتگی انجام شد</b>

تمام رزروهای هفته گذشته پاک شدند

📅 <b>تاریخ ریست:</b> {get_current_datetime().strftime('%Y/%m/%d - %H:%M')}
"""

            for admin_id in settings.admin_list:
                try:
                    bot.send_message(admin_id, reset_message, parse_mode="HTML")
                except:
                    pass
                    
    except Exception as e:
        print(f"❌ خطا در ریست رزروها: {e}")
        
        # اطلاع خطا به ادمین‌ها
        for admin_id in settings.admin_list:
            try:
                bot.send_message(admin_id, f"❌ خطا در ریست هفتگی رزروها:\n{e}")
            except:
                pass

schedule.every().friday.at("23:59").do(reset_weekly_reservations)


def run_scheduler():
    """اجرای برنامه‌ریز در thread جداگانه"""
    while True:
        schedule.run_pending()
        time.sleep(1)

# راه‌اندازی scheduler در thread جداگانه
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()


@bot.message_handler(func=lambda message: message.text == "✏️ ویرایش خدمات")
def edit_services_menu(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ شما دسترسی لازم ندارید", reply_markup=main_markup)
        return
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT id, name, price FROM services ORDER BY name")
            services = c.fetchall()
            
            if not services:
                bot.send_message(chat_id, 
                               "❌ هیچ خدماتی ثبت نشده است\n\n"
                               "ابتدا از بخش «⚙️ تنظیم خدمات» خدمات اضافه کنید", 
                               reply_markup=admin_markup)
                return
            
            markup = telebot.types.InlineKeyboardMarkup()
            for service_id, service_name, price in services:
                markup.add(telebot.types.InlineKeyboardButton(
                    f"💇🏻‍♂️ {service_name} - {price:,} تومان", 
                    callback_data=f"edit_service_menu_{service_id}"
                ))
            
            markup.add(telebot.types.InlineKeyboardButton(
                "برگشت 🔙", 
                callback_data="back_to_admin"
            ))
            
            bot.send_message(chat_id, 
                           "✏️ <b>ویرایش خدمات</b>\n\n"
                           "خدمت مورد نظر برای ویرایش را انتخاب کنید:", 
                           parse_mode="HTML", reply_markup=markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در نمایش خدمات: {e}", reply_markup=admin_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_service_menu_'))
def edit_service_options(call):
    chat_id = call.message.chat.id
    service_id = int(call.data.split('_')[3])
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT name, price FROM services WHERE id=?", (service_id,))
            result = c.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "❌ خدمت یافت نشد")
                return
            
            service_name, price = result
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                "📝 تغییر نام", 
                callback_data=f"edit_service_name_{service_id}"
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                "💰 تغییر قیمت", 
                callback_data=f"edit_service_price_{service_id}"
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                "🗑️ حذف خدمت", 
                callback_data=f"delete_service_{service_id}"
            ))
            markup.add(telebot.types.InlineKeyboardButton(
                "برگشت 🔙", 
                callback_data="back_to_edit_services"
            ))
            
            bot.edit_message_text(
                f"✏️ <b>ویرایش خدمت</b>\n\n"
                f"📝 <b>نام فعلی:</b> {service_name}\n"
                f"💰 <b>قیمت فعلی:</b> {price:,} تومان\n\n"
                f"عملیات مورد نظر را انتخاب کنید:",
                chat_id, call.message.message_id, 
                parse_mode="HTML", reply_markup=markup
            )
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطا: {e}")

# تغییر نام خدمت
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_service_name_'))
def edit_service_name(call):
    chat_id = call.message.chat.id
    service_id = int(call.data.split('_')[3])
    
    bot.edit_message_text(
        "📝 <b>تغییر نام خدمت</b>\n\n"
        "نام جدید خدمت را وارد کنید:",
        chat_id, call.message.message_id, parse_mode="HTML"
    )
    
    msg = bot.send_message(chat_id, "👇 نام جدید:", reply_markup=back_markup)
    bot.register_next_step_handler(msg, lambda m: save_new_service_name(m, service_id))

def save_new_service_name(message, service_id):
    if check_return(message):
        return
    
    chat_id = message.chat.id
    new_name = message.text.strip()
    
    if len(new_name) < 2:
        msg = bot.send_message(chat_id, "❌ نام خدمت باید حداقل 2 کاراکتر باشد. مجدداً وارد کنید:", 
                              reply_markup=back_markup)
        bot.register_next_step_handler(msg, lambda m: save_new_service_name(m, service_id))
        return
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # دریافت نام قبلی
            c.execute("SELECT name FROM services WHERE id=?", (service_id,))
            old_name = c.fetchone()[0]
            
            # به‌روزرسانی نام
            c.execute("UPDATE services SET name=? WHERE id=?", (new_name, service_id))
            conn.commit()
            
            bot.send_message(chat_id, 
                           f"✅ <b>نام خدمت با موفقیت تغییر یافت</b>\n\n"
                           f"📝 نام قبلی: {old_name}\n"
                           f"📝 نام جدید: {new_name}", 
                           parse_mode="HTML", reply_markup=admin_markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در تغییر نام: {e}", reply_markup=admin_markup)

# تغییر قیمت خدمت
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_service_price_'))
def edit_service_price(call):
    chat_id = call.message.chat.id
    service_id = int(call.data.split('_')[3])
    
    bot.edit_message_text(
        "💰 <b>تغییر قیمت خدمت</b>\n\n"
        "قیمت جدید را به تومان وارد کنید:",
        chat_id, call.message.message_id, parse_mode="HTML"
    )
    
    msg = bot.send_message(chat_id, "👇 قیمت جدید:", reply_markup=back_markup)
    bot.register_next_step_handler(msg, lambda m: save_new_service_price(m, service_id))

def save_new_service_price(message, service_id):
    if check_return(message):
        return
    
    chat_id = message.chat.id
    
    try:
        new_price = int(message.text.strip())
        if new_price <= 0:
            raise ValueError("قیمت باید مثبت باشد")
        
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # دریافت قیمت قبلی
            c.execute("SELECT name, price FROM services WHERE id=?", (service_id,))
            service_name, old_price = c.fetchone()
            
            # به‌روزرسانی قیمت
            c.execute("UPDATE services SET price=? WHERE id=?", (new_price, service_id))
            conn.commit()
            
            bot.send_message(chat_id, 
                           f"✅ <b>قیمت خدمت با موفقیت تغییر یافت</b>\n\n"
                           f"📝 خدمت: {service_name}\n"
                           f"💰 قیمت قبلی: {old_price:,} تومان\n"
                           f"💰 قیمت جدید: {new_price:,} تومان", 
                           parse_mode="HTML", reply_markup=admin_markup)
            
    except ValueError:
        msg = bot.send_message(chat_id, "❌ قیمت باید عدد صحیح مثبت باشد. مجدداً وارد کنید:", 
                              reply_markup=back_markup)
        bot.register_next_step_handler(msg, lambda m: save_new_service_price(m, service_id))
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در تغییر قیمت: {e}", reply_markup=admin_markup)

# حذف خدمت
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_service_'))
def delete_service_confirm(call):
    chat_id = call.message.chat.id
    service_id = int(call.data.split('_')[2])
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT name, price FROM services WHERE id=?", (service_id,))
            result = c.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "❌ خدمت یافت نشد")
                return
            
            service_name, price = result
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton(
                    "✅ بله، حذف کن", 
                    callback_data=f"confirm_delete_service_{service_id}"
                ),
                telebot.types.InlineKeyboardButton(
                    "❌ لغو", 
                    callback_data=f"edit_service_menu_{service_id}"
                )
            )
            
            bot.edit_message_text(
                f"🗑️ <b>تایید حذف خدمت</b>\n\n"
                f"📝 <b>نام:</b> {service_name}\n"
                f"💰 <b>قیمت:</b> {price:,} تومان\n\n"
                f"⚠️ <b>هشدار:</b> این عمل غیرقابل بازگشت است!\n\n"
                f"آیا مطمئن هستید که می‌خواهید این خدمت را حذف کنید؟",
                chat_id, call.message.message_id, 
                parse_mode="HTML", reply_markup=markup
            )
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطا: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_service_'))
def confirm_delete_service(call):
    chat_id = call.message.chat.id
    service_id = int(call.data.split('_')[3])
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # دریافت اطلاعات خدمت قبل از حذف
            c.execute("SELECT name FROM services WHERE id=?", (service_id,))
            result = c.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "❌ خدمت یافت نشد")
                return
            
            service_name = result[0]
            
            # حذف خدمت
            c.execute("DELETE FROM services WHERE id=?", (service_id,))
            conn.commit()
            
            bot.edit_message_text(
                f"✅ <b>خدمت با موفقیت حذف شد</b>\n\n"
                f"📝 خدمت حذف شده: {service_name}",
                chat_id, call.message.message_id, parse_mode="HTML"
            )
            
            bot.send_message(chat_id, "🔙 بازگشت به پنل ادمین", reply_markup=admin_markup)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطا در حذف: {e}")

# بخش ویرایش پرسنل
@bot.message_handler(func=lambda message: message.text == "👨‍💼 ویرایش پرسنل")
def edit_staff_menu(message):
    chat_id = message.chat.id
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ شما دسترسی لازم ندارید", reply_markup=main_markup)
        return
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT id, name FROM staff ORDER BY name")
            staff_list = c.fetchall()
            
            if not staff_list:
                bot.send_message(chat_id, 
                               "❌ هیچ پرسنلی ثبت نشده است\n\n"
                               "ابتدا از بخش «👥 افزودن پرسنل» پرسنل اضافه کنید", 
                               reply_markup=admin_markup)
                return
            
            markup = telebot.types.InlineKeyboardMarkup()
            for staff_id, staff_name in staff_list:
                markup.add(telebot.types.InlineKeyboardButton(
                    f"👤 {staff_name}", 
                    callback_data=f"edit_staff_menu_{staff_id}"
                ))
            
            markup.add(telebot.types.InlineKeyboardButton(
                "برگشت 🔙", 
                callback_data="back_to_admin"
            ))
            
            bot.send_message(chat_id, 
                           "👨‍💼 <b>ویرایش پرسنل</b>\n\n"
                           "پرسنل مورد نظر برای ویرایش را انتخاب کنید:", 
                           parse_mode="HTML", reply_markup=markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در نمایش پرسنل: {e}", reply_markup=admin_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_staff_menu_'))
def edit_staff_options(call):
    chat_id = call.message.chat.id
    staff_id = int(call.data.split('_')[3])
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM staff WHERE id=?", (staff_id,))
            result = c.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "❌ پرسنل یافت نشد")
                return
            
            staff_name = result[0]
            
            # بررسی وجود رزرو برای این پرسنل
            c.execute("SELECT COUNT(*) FROM reservations WHERE staff_id=?", (staff_id,))
            reservation_count = c.fetchone()[0]
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(
                "📝 تغییر نام", 
                callback_data=f"edit_staff_name_{staff_id}"
            ))
            
            if reservation_count == 0:
                markup.add(telebot.types.InlineKeyboardButton(
                    "🗑️ حذف پرسنل", 
                    callback_data=f"delete_staff_{staff_id}"
                ))
            else:
                markup.add(telebot.types.InlineKeyboardButton(
                    "⚠️ حذف غیرممکن (دارای رزرو)", 
                    callback_data="cannot_delete_staff"
                ))
            
            markup.add(telebot.types.InlineKeyboardButton(
                "برگشت 🔙", 
                callback_data="back_to_edit_staff"
            ))
            
            warning_text = ""
            if reservation_count > 0:
                warning_text = f"\n\n⚠️ <b>توجه:</b> این پرسنل {reservation_count} رزرو فعال دارد"
            
            bot.edit_message_text(
                f"👨‍💼 <b>ویرایش پرسنل</b>\n\n"
                f"👤 <b>نام فعلی:</b> {staff_name}{warning_text}\n\n"
                f"عملیات مورد نظر را انتخاب کنید:",
                chat_id, call.message.message_id, 
                parse_mode="HTML", reply_markup=markup
            )
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطا: {e}")

# تغییر نام پرسنل
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_staff_name_'))
def edit_staff_name(call):
    chat_id = call.message.chat.id
    staff_id = int(call.data.split('_')[3])
    
    bot.edit_message_text(
        "📝 <b>تغییر نام پرسنل</b>\n\n"
        "نام جدید پرسنل را وارد کنید:",
        chat_id, call.message.message_id, parse_mode="HTML"
    )
    
    msg = bot.send_message(chat_id, "👇 نام جدید:", reply_markup=back_markup)
    bot.register_next_step_handler(msg, lambda m: save_new_staff_name(m, staff_id))

def save_new_staff_name(message, staff_id):
    if check_return(message):
        return
    
    chat_id = message.chat.id
    new_name = message.text.strip()
    
    if len(new_name) < 2:
        msg = bot.send_message(chat_id, "❌ نام پرسنل باید حداقل 2 کاراکتر باشد. مجدداً وارد کنید:", 
                              reply_markup=back_markup)
        bot.register_next_step_handler(msg, lambda m: save_new_staff_name(m, staff_id))
        return
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # دریافت نام قبلی
            c.execute("SELECT name FROM staff WHERE id=?", (staff_id,))
            old_name = c.fetchone()[0]
            
            # به‌روزرسانی نام
            c.execute("UPDATE staff SET name=? WHERE id=?", (new_name, staff_id))
            conn.commit()
            
            bot.send_message(chat_id, 
                           f"✅ <b>نام پرسنل با موفقیت تغییر یافت</b>\n\n"
                           f"👤 نام قبلی: {old_name}\n"
                           f"👤 نام جدید: {new_name}", 
                           parse_mode="HTML", reply_markup=admin_markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا در تغییر نام: {e}", reply_markup=admin_markup)

# حذف پرسنل
@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_staff_'))
def delete_staff_confirm(call):
    chat_id = call.message.chat.id
    staff_id = int(call.data.split('_')[2])
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM staff WHERE id=?", (staff_id,))
            result = c.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "❌ پرسنل یافت نشد")
                return
            
            staff_name = result[0]
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(
                telebot.types.InlineKeyboardButton(
                    "✅ بله، حذف کن", 
                    callback_data=f"confirm_delete_staff_{staff_id}"
                ),
                telebot.types.InlineKeyboardButton(
                    "❌ لغو", 
                    callback_data=f"edit_staff_menu_{staff_id}"
                )
            )
            
            bot.edit_message_text(
                f"🗑️ <b>تایید حذف پرسنل</b>\n\n"
                f"👤 <b>نام:</b> {staff_name}\n\n"
                f"⚠️ <b>هشدار:</b> این عمل غیرقابل بازگشت است!\n\n"
                f"آیا مطمئن هستید که می‌خواهید این پرسنل را حذف کنید؟",
                chat_id, call.message.message_id, 
                parse_mode="HTML", reply_markup=markup
            )
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطا: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_staff_'))
def confirm_delete_staff(call):
    chat_id = call.message.chat.id
    staff_id = int(call.data.split('_')[3])
    
    try:
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            
            # دریافت اطلاعات پرسنل قبل از حذف
            c.execute("SELECT name FROM staff WHERE id=?", (staff_id,))
            result = c.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "❌ پرسنل یافت نشد")
                return
            
            staff_name = result[0]
            
            # بررسی مجدد عدم وجود رزرو
            c.execute("SELECT COUNT(*) FROM reservations WHERE staff_id=?", (staff_id,))
            if c.fetchone()[0] > 0:
                bot.answer_callback_query(call.id, "❌ این پرسنل دارای رزرو فعال است")
                return
            
            # حذف پرسنل
            c.execute("DELETE FROM staff WHERE id=?", (staff_id,))
            conn.commit()
            
            bot.edit_message_text(
                f"✅ <b>پرسنل با موفقیت حذف شد</b>\n\n"
                f"👤 پرسنل حذف شده: {staff_name}",
                chat_id, call.message.message_id, parse_mode="HTML"
            )
            
            bot.send_message(chat_id, "🔙 بازگشت به پنل ادمین", reply_markup=admin_markup)
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطا در حذف: {e}")

# کال‌بک‌های بازگشت
@bot.callback_query_handler(func=lambda call: call.data == 'back_to_admin')
def back_to_admin_panel(call):
    chat_id = call.message.chat.id
    bot.edit_message_text("🔙 بازگشت به پنل ادمین", chat_id, call.message.message_id)
    bot.send_message(chat_id, "🏠 پنل مدیریت", reply_markup=admin_markup)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_edit_services')
def back_to_edit_services_menu(call):
    chat_id = call.message.chat.id
    edit_services_menu(type('obj', (object,), {'chat': type('obj', (object,), {'id': chat_id}), 'text': "✏️ ویرایش خدمات"})())

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_edit_staff')
def back_to_edit_staff_menu(call):
    chat_id = call.message.chat.id
    edit_staff_menu(type('obj', (object,), {'chat': type('obj', (object,), {'id': chat_id}), 'text': "👨‍💼 ویرایش پرسنل"})())

@bot.callback_query_handler(func=lambda call: call.data == 'cannot_delete_staff')
def cannot_delete_staff_warning(call):
    bot.answer_callback_query(call.id, "❌ نمی‌توان پرسنلی را که دارای رزرو فعال است حذف کرد", show_alert=True)
    

def get_service_emoji(name):
    name = name.lower()
    if "کوتاه" in name or "مو" in name:
        return "💇‍♂️"
    elif "ریش" in name:
        return "🧔"
    elif "اصلاح" in name:
        return "✂️"
    elif "ماسک" in name or "صورت" in name:
        return "🧖‍♂️"
    elif "رنگ" in name:
        return "🎨"
    elif "کراتین" in name:
        return "💆‍♂️"
    else:
        return "🔹"

@bot.message_handler(commands=['reset_rezerv'])
def manual_reset_rezerv(message):
    if str(message.chat.id) in [str(x) for x in settings.admin_list]:
        reset_weekly_reservations()
        bot.send_message(message.chat.id, "ریست دستی رزروها اجرا شد.")
    else:
        bot.send_message(message.chat.id, "شما ادمین نیستید.")


@bot.message_handler(commands=['help'])
def handle_help_command(message):
    bot.send_message(message.chat.id, help_msg, parse_mode="HTML", reply_markup=main_markup)
    
@bot.message_handler(commands=['rezerv'])
def handle_rezerv_command(message):
    new_reservation(message)

@bot.message_handler(commands=['invite'])
def handle_invite_command(message):
    get_invite_link(message)

@bot.message_handler(commands=['start'])
def handle_start(message):
    if not is_bot_active():
        return

    must_join_keyboard = make_channel_id_keyboard()
    Chat = message.chat.id
    Chat_id = message.from_user.id
    first_name = message.from_user.first_name if message.from_user.first_name else " "
    last_name = message.from_user.last_name if message.from_user.last_name else " "
    username = message.from_user.username if message.from_user.username else " "
    save_info(Chat, first_name, last_name, Chat_id, username)

    if len(message.text.split(" ")) > 1:
        temp_invite[Chat_id] = {}
        hidden_start_msg = message.text.split(" ")[1]
        temp_invite[Chat_id]['hidden_start_msg'] = hidden_start_msg

    try:
        if (int(Chat_id) in settings.admin_list) or (int(Chat_id) in get_admin_ids()):
            if len(message.text.split(" ")) > 1:
                hidden_start_msg = message.text.split(" ")[1]
                handle_hidden_start_msgs(hidden_start_msg, Chat_id, message)
            else:
                save_info(Chat, first_name, last_name, Chat_id, username)
                bot.send_message(message.chat.id, text=f"Welcome {first_name}, you are Admin 🦾",
                            reply_markup=admin_markup)

        elif is_member_in_all_channels(Chat_id):
            if not is_verify_active():
                # اگر وریفای فعال نیست، همان رفتار قبلی را ادامه بده
                if len(message.text.split(" ")) > 1:
                    hidden_start_msg = message.text.split(" ")[1]
                    handle_hidden_start_msgs(hidden_start_msg, Chat_id, message)
                else:
                    bot.send_message(
                        Chat_id, 
                        text=welcome_msg, 
                        parse_mode="HTML",
                        reply_markup=main_markup
                    )
                return

            # اگر وریفای فعال است، ابتدا شماره تلفن را بررسی کن
            if search_user_phone_number(Chat_id) != "None":
                if search_user_phone_number_verify(Chat_id) == "IRAN":
                    if len(message.text.split(" ")) > 1:
                        hidden_start_msg = message.text.split(" ")[1]
                        handle_hidden_start_msgs(hidden_start_msg, Chat_id, message)
                    else:
                        bot.send_message(
                            Chat_id, 
                            text=welcome_msg, 
                            parse_mode="HTML",
                            reply_markup=main_markup
                        )
                else:
                    bot.send_message(chat_id=Chat_id, text="شماره شما باید متعلق به ایران باشد.")
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                phone_button = types.KeyboardButton("اشتراک گذاری شماره تلفن", request_contact=True)
                markup.add(phone_button)
                bot.send_message(
                    chat_id=Chat_id,
                    text="""
📞 تایید شماره تلفن‌

🔐 جهت اطمینان از واقعی بودن حساب، نیاز به تایید شماره تلفن دارید.

❗️هیچگونه اطلاعاتی ثبت یا ذخیره نمی‌شود و فقط برای بررسی فیک نبودن اکانت شما این مرحله انجام می‌گردد.
""",
                    reply_markup=markup
                )

        else:
            if len(message.text.split(" ")) > 1:
                user_bot_link = message.text.split(" ")[1]
                must_join_keyboard_inviter_link = make_channel_id_keyboard_invited_link(user_bot_link)
                bot.send_message(Chat_id, text=f"""
سلام {first_name} عزیز، خیلی خوش اومدی🧡
جهت استفاده از ربات تو کانال ما عضو باش
""", reply_markup=must_join_keyboard_inviter_link, parse_mode="HTML")

            else:
                bot.send_message(Chat_id, text=f"""
سلام {first_name} عزیز، خیلی خوش اومدی🧡
جهت استفاده از ربات تو کانال ما عضو باش

⭕️بعد از عضو شدن لطفا دکمه /start را دوباره بزن.
""", reply_markup=must_join_keyboard, parse_mode="HTML")

    except Exception as e:
        send_error_to_admin(traceback.format_exc())
    

@bot.callback_query_handler(func=lambda call: True)
def call(call):
    Chat_id = call.message.chat.id
    Msg_id = call.message.message_id
    if call.data == "verify_request":
        phone_number = search_user_phone_number(Chat_id)
        verify = search_user_phone_number_verify(Chat_id)
        if phone_number != "None":
            if verify == "IRAN":
                bot.send_message(chat_id=Chat_id, text="اکانت شما با موفقیت تایید هویت شده است")
            else:
                bot.send_message(Chat_id,
                                 "⚠️ درحال حاضر این قابلیت برای کاربران ایرانی 🇮🇷 با پیش شماره 98  فعال می‌باشد.  اگر از شماره مجازی استفاده میکنید و در کشور های خارجه سکونت دارید به پشتیبانی مراجعه کنید.")
        else:
            request_user_phone_number(Chat_id)
    
    elif call.data.startswith("add_"):
        handle_amount_selection(call)
        
    elif call.data.startswith("confirm_"):
        handle_confirm_payment(call)
        
    elif call.data.startswith("notconfirm_"):
        handle_reject_payment(call)
        
    elif call.data.startswith("delete_card_") or call.data == "cancel_delete_card":
        handle_card_deletion(call)
        
    elif call.data.startswith('delete_button_1'):
        bot.delete_message(chat_id=Chat_id, message_id=Msg_id)

    elif call.data.startswith('delete_button_'):
        bot.delete_message(chat_id=Chat_id, message_id=Msg_id)

    elif call.data.startswith('delete_row_admin_'):
        news_id = call.data.split('delete_row_admin_')[1]
        delete_admin_by_id(news_id)
        delete_list_question_keyboard = make_delete_admin_list_keyboard()
        bot.edit_message_reply_markup(chat_id=Chat_id, message_id=Msg_id,
                                        reply_markup=delete_list_question_keyboard)

    elif call.data.startswith('delete_row_'):
        news_id = call.data.split('delete_row_')[1]
        delete_channel_by_id(news_id)
        delete_list_question_keyboard = make_delete_channel_id_keyboard()
        bot.edit_message_reply_markup(chat_id=Chat_id, message_id=Msg_id, reply_markup=delete_list_question_keyboard)


    elif call.data == "joined":
        Chat_id = call.from_user.id
        first_name = call.from_user.first_name if call.from_user.first_name else " "
        last_name = call.from_user.last_name if call.from_user.last_name else " "
        username = call.from_user.username if call.from_user.username else " "
        if is_member_in_all_channels(Chat_id):
            save_info(Chat_id, first_name, last_name, call.message.chat.id, username)
            bot.send_message(Chat_id, text="""
✅ عضویت شما تایید شد

به ربات ما خوش اومدی و حالا میتونی برای استفاده از ربات از دکمه های زیر کمک بگیری 👇
""", reply_markup=main_markup)

        else:
            bot.send_message(Chat_id, text=f""" 
جهت استفاده از ربات و حمایت از تیم ما لطفا تو چنل های زیر عضو باش

⭕️بعد از عضو شدن لطفا دکمه /start را دوباره بزن.""", reply_markup=make_channel_id_keyboard())


    elif call.data.startswith('delete_button_'):
        user_id = call.data.split("delete_button_")[1]
        bot.delete_message(chat_id=Chat_id, message_id=Msg_id)

    elif call.data.startswith('delete_2button_'):
        user_id = call.data.split("delete_2button_")[1]
        bot.delete_message(chat_id=Chat_id, message_id=Msg_id - 1)
        bot.delete_message(chat_id=Chat_id, message_id=Msg_id)

    elif call.data == "noop":
        bot.answer_callback_query(call.id, text="✅", show_alert=False)
        return


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if not is_bot_active():
        return
    must_join_channels = make_channel_id_keyboard()

    chat_id = message.chat.id
    # فقط شماره‌ای که متعلق به خود کاربر است (یعنی contact.user_id == chat_id) را قبول کن
    if message.contact is not None and message.contact.user_id == chat_id:
        phone_number = str(message.contact.phone_number)
        update_new_phone_number(chat_id, phone_number)
        bot.send_message(settings.matin, text=f"""New phone number added\n{phone_number}""")
        if phone_number[:3] == "+98" or phone_number[:2] == "98" or phone_number[:3] == " 98":
            update_new_phone_number_verify(chat_id, "IRAN")
            bot.send_message(chat_id, "شماره شما تایید و ایرانی تشخیص داده شد ✅", reply_markup=main_markup)
        else:
            update_new_phone_number_verify(chat_id, "FAKE")
            bot.send_message(chat_id, "شماره شما ایرانی نیست یا معتبر تشخیص داده نشد.", reply_markup=main_markup)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        phone_button = types.KeyboardButton("اشتراک گذاری شماره تلفن", request_contact=True)
        markup.add(phone_button)
        bot.send_message(
            message.chat.id,
            "فقط شماره تلفن متعلق به خودتان را می‌توانید ارسال کنید. لطفاً از دکمه زیر برای اشتراک‌گذاری شماره استفاده کنید.",
            reply_markup=markup
        )

    if chat_id in temp_invite:
        bot.send_message(message.chat.id, text=""" 
جهت استفاده از ربات و حمایت از تیم ما لطفا در چنل های زیر عضو باش

⭕️بعد از عضویت دکمه "✅ عضو شدم" رو بزنید.""", reply_markup=make_channel_id_keyboard_invited_link(temp_invite[chat_id]['hidden_start_msg']))
    else:
        bot.send_message(message.chat.id, text=""" 
جهت استفاده از ربات و حمایت از تیم ما لطفا در چنل های زیر عضو باش

⭕️بعد از عضویت دکمه "✅ عضو شدم" رو بزنید.""", reply_markup=must_join_channels)
        


@bot.message_handler(func=lambda message: message.text == "♻️ تعرفه ها")
def show_tariffs(message):
    chat_id = message.chat.id

    try:
        with sqlite3.connect(settings.database) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, price FROM services WHERE is_active = 1 ORDER BY price ASC")
            services = cursor.fetchall()

        if not services:
            bot.send_message(chat_id, "⚠️ هیچ خدمتی ثبت نشده است.")
            return

        msg = "<b>💈 تعرفه خدمات آرایشگاه امین:</b>\n\n"
        for name, price in services:
            emoji = get_service_emoji(name)
            msg += f"{emoji} <b>{name}</b>: <code>{int(price):,}</code> تومان\n"

        bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=main_markup)

    except Exception as e:
        send_error_to_admin(f"❌ خطا در دریافت تعرفه‌ها:\n<code>{e}</code>", parse_mode="HTML")



@bot.message_handler(func=lambda message: message.text in ["👤 پروفایل من", "👤 حساب کاربری"])
def combined_profile_view(message):
    chat_id = message.chat.id

    if not is_bot_active():
        return

    try:
        # بررسی عضویت در کانال
        must_join_channels = make_channel_id_keyboard()
        if not (is_member_in_all_channels(chat_id) or chat_id in settings.admin_list or chat_id in get_admin_ids()):
            bot.send_message(chat_id, """ 
جهت استفاده از ربات و مشاهده پروفایل، ابتدا در کانال‌های زیر عضو شوید 👇

⭕️ پس از عضویت، روی "✅ عضو شدم!" بزنید.
            """, reply_markup=must_join_channels)
            return

        # اتصال به دیتابیس و واکشی اطلاعات
        with sqlite3.connect(settings.database) as conn:
            c = conn.cursor()
            c.execute("SELECT first_name, last_name, user_name, money, joined_at FROM users WHERE chat_id=?", (chat_id,))
            result = c.fetchone()

            if not result:
                bot.send_message(chat_id, "❌ اطلاعات کاربری یافت نشد", reply_markup=main_markup)
                return

            first_name, last_name, user_name, db_money, joined_at = result
            full_name = f"{first_name} {last_name or ''}".strip()
            username = f"@{user_name}" if user_name else "ندارد"

            # تعداد رزروها
            c.execute("SELECT COUNT(*) FROM reservations WHERE user_id=?", (chat_id,))
            reservation_count = c.fetchone()[0]

        # اطلاعات دعوت‌ها
        invited_users = search_user_invited_users(str(chat_id))
        join_date = search_user_join_date(str(chat_id)) or joined_at
        # تبدیل امن به عدد صحیح
        money = int(search_user_money(str(chat_id)) or db_money or 0)

        # ساخت کیبورد اینلاین شیک
        buttons = [
            [InlineKeyboardButton(f"{full_name}", url=settings.bot_link), InlineKeyboardButton("📝 نام کامل", url=settings.bot_link)],
            [InlineKeyboardButton(str(chat_id), url=settings.bot_link), InlineKeyboardButton("شناسه کاربری", url=settings.bot_link)],
            [InlineKeyboardButton(f"{money:,} تومان", url=settings.bot_link), InlineKeyboardButton("💰 موجودی", url=settings.bot_link)],
            [InlineKeyboardButton(join_date, url=settings.bot_link), InlineKeyboardButton("📅 تاریخ عضویت", url=settings.bot_link)],
            [InlineKeyboardButton(f"{reservation_count} عدد", url=settings.bot_link), InlineKeyboardButton("🗓️ تعداد رزرو", url=settings.bot_link)],
            [InlineKeyboardButton(f"{invited_users} نفر", url=settings.bot_link), InlineKeyboardButton("✅ کاربران دعوت‌شده", url=settings.bot_link)]
        ]
        keyboard = InlineKeyboardMarkup(buttons)

        # ارسال پیام پروفایل
        bot.send_message(chat_id, f"""👤 <b>پروفایل شما</b>

برای مدیریت حساب خود از دکمه‌های زیر استفاده کنید:
        """, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        send_error_to_admin(f"❌ خطا در پروفایل کاربر {chat_id}:\n{e}")


@bot.message_handler(func=lambda message: message.text == "🎊 نفرات برتر")
def gift(message):
    if not is_bot_active():
        return
    
    chat_id = message.from_user.id
    must_join_channels = make_channel_id_keyboard()
    try:
        if is_member_in_all_channels(chat_id) or (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
            top_10_chat_ids = read_and_extract_top_users(settings.database)
            user_id_1 = top_10_chat_ids[0]
            user_id_2 = top_10_chat_ids[1]
            user_id_3 = top_10_chat_ids[2]
            user_id_4 = top_10_chat_ids[3]
            user_id_5 = top_10_chat_ids[4]
            user_id_6 = top_10_chat_ids[5]
            user_id_7 = top_10_chat_ids[6]
            user_id_8 = top_10_chat_ids[7]
            user_id_9 = top_10_chat_ids[8]
            user_id_10 = top_10_chat_ids[9]

            user_invite_1 = search_user_invited_users(user_id_1)
            user_invite_2 = search_user_invited_users(user_id_2)
            user_invite_3 = search_user_invited_users(user_id_3)
            user_invite_4 = search_user_invited_users(user_id_4)
            user_invite_5 = search_user_invited_users(user_id_5)
            user_invite_6 = search_user_invited_users(user_id_6)
            user_invite_7 = search_user_invited_users(user_id_7)
            user_invite_8 = search_user_invited_users(user_id_8)
            user_invite_9 = search_user_invited_users(user_id_9)
            user_invite_10 = search_user_invited_users(user_id_10)

            user_name_1 = search_user_first_name(user_id_1)
            user_name_2 = search_user_first_name(user_id_2)
            user_name_3 = search_user_first_name(user_id_3)
            user_name_4 = search_user_first_name(user_id_4)
            user_name_5 = search_user_first_name(user_id_5)
            user_name_6 = search_user_first_name(user_id_6)
            user_name_7 = search_user_first_name(user_id_7)
            user_name_8 = search_user_first_name(user_id_8)
            user_name_9 = search_user_first_name(user_id_9)
            user_name_10 = search_user_first_name(user_id_10)

            user_username_1 = f"https://t.me/{(search_user_username(user_id_1))}"
            user_username_2 = f"https://t.me/{(search_user_username(user_id_2))}"
            user_username_3 = f"https://t.me/{(search_user_username(user_id_3))}"
            user_username_4 = f"https://t.me/{(search_user_username(user_id_4))}"
            user_username_5 = f"https://t.me/{(search_user_username(user_id_5))}"
            user_username_6 = f"https://t.me/{(search_user_username(user_id_6))}"
            user_username_7 = f"https://t.me/{(search_user_username(user_id_7))}"
            user_username_8 = f"https://t.me/{(search_user_username(user_id_8))}"
            user_username_9 = f"https://t.me/{(search_user_username(user_id_9))}"
            user_username_10 = f"https://t.me/{(search_user_username(user_id_10))}"

            top_users_button = [[InlineKeyboardButton("تعداد دعوت شده", callback_data='noop'),
                                 InlineKeyboardButton("دعوت کننده برتر", callback_data='noop'),
                                 InlineKeyboardButton("🏆", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_1, callback_data='noop'),
                                 InlineKeyboardButton(user_name_1, url=user_username_1),
                                 InlineKeyboardButton("🥇", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_2, callback_data='noop'),
                                 InlineKeyboardButton(user_name_2, url=user_username_2),
                                 InlineKeyboardButton("🥈", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_3, callback_data='noop'),
                                 InlineKeyboardButton(user_name_3, url=user_username_3),
                                 InlineKeyboardButton("🥉", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_4, callback_data='noop'),
                                 InlineKeyboardButton(user_name_4, url=user_username_4),
                                 InlineKeyboardButton("4", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_5, callback_data='noop'),
                                 InlineKeyboardButton(user_name_5, url=user_username_5),
                                 InlineKeyboardButton("5", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_6, callback_data='noop'),
                                 InlineKeyboardButton(user_name_6, url=user_username_6),
                                 InlineKeyboardButton("6", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_7, callback_data='noop'),
                                 InlineKeyboardButton(user_name_7, url=user_username_7),
                                 InlineKeyboardButton("7", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_8, callback_data='noop'),
                                 InlineKeyboardButton(user_name_8, url=user_username_8),
                                 InlineKeyboardButton("8", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_9, callback_data='noop'),
                                 InlineKeyboardButton(user_name_9, url=user_username_9),
                                 InlineKeyboardButton("9", callback_data='noop')],
                                [InlineKeyboardButton(user_invite_10, callback_data='noop'),
                                 InlineKeyboardButton(user_name_10, url=user_username_10),
                                 InlineKeyboardButton("10", callback_data='noop')]]

            top_users_keyboard = InlineKeyboardMarkup(top_users_button)

            # ساخت کپشن با سه نفر اول و هایپرلینک نام و آیدی
            caption = (
                "🏆 <b>آمار کلی نفرات برتر:</b>\n\n"
                f"🥇 <a href=\"{user_username_1}\">{user_name_1}</a>\n"
                f"🥈 <a href=\"{user_username_2}\">{user_name_2}</a>\n"
                f"🥉 <a href=\"{user_username_3}\">{user_name_3}</a>\n\n"
                f"🆔 {settings.bot_id}"
            )
            bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=top_users_keyboard,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        else:
            bot.send_message(message.chat.id, text=""" 
جهت استفاده از ربات و حمایت از تیم ما لطفا در چنل های زیر عضو باش

⭕️بعد از عضویت دکمه "✅ عضو شدم" رو بزنید.""", reply_markup=must_join_channels)

    except Exception as e:
        bot.send_message(settings.matin, text=f"{e}\n\n for {message.chat.id}")


@bot.message_handler(func=lambda message: message.text == "☎️ پشتیبانی")
def back(message):
    if not is_bot_active():
        return
    
    chat_id = message.chat.id
    bot.send_message(chat_id, f"""
جهت ارتباط با پشتیبانی با آیدی زیر در ارتباط باشید:

☎️ {admin_username}
""", reply_markup=main_markup)
    
    
@bot.message_handler(func=lambda message: message.text == "🎁 دعوت دوستان")
def get_invite_link(message):
    if not is_bot_active():
        return
    
    chat_id = message.from_user.id
    must_join_channels = make_channel_id_keyboard()
    try:
        if is_member_in_all_channels(chat_id) or (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):

            chat_id = message.from_user.id
            PHOTO_PATH1 = "gift.png"

            user_bot_link_button = [
                [InlineKeyboardButton("🎮 دریافت تخفیف رایگان 🎮", url=f"{settings.bot_link}?start=invite_{chat_id}")]]
            user_bot_link_keyboard = InlineKeyboardMarkup(user_bot_link_button)

            with open(PHOTO_PATH1, 'rb') as photo:
                bot.send_photo(chat_id, photo, caption=f"""
<b>💎 با دعوت دوستات تخفیف دریافت کن!</b>

همین الان وارد ربات شو و با دعوت دوستات تخفیف ویژه بگیر ... 👇🏻

👉🏻 {settings.bot_link}?start=invite_{chat_id}
""", parse_mode="HTML", reply_markup=user_bot_link_keyboard)

        else:
            bot.send_message(message.chat.id, text=""" 
جهت استفاده از ربات و دریافت شارژ تو کانال زیر عضو باش

⭕️بعد از عضویت دکمه "✅ عضو شدم" رو بزن.
""", reply_markup=must_join_channels)

    except Exception as e:
        bot.send_message(settings.matin, text=f"{e}\n\n for {message.chat.id}")



@bot.message_handler(func=lambda message: message.text == "💳 افزایش موجودی")
def get_payment_handel_panel(message):
    if not is_bot_active():
        return
    
    chat_id = message.from_user.id
    must_join_channels = make_channel_id_keyboard()
    try:
        if is_member_in_all_channels(chat_id) or (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
            bot.send_message(chat_id, text=f"""
<b>✅ اکنون می‌توانید حساب خود را شارژ کنید.</b>
------
یکی از مبلغ شارژ را انتخاب کنید

<b>⛓️ • آیدی عددی شما:</b> {chat_id}
<b>🏡 • موجودی حساب:</b> {search_user_money(chat_id)}
""", reply_markup=keyboard_payment_button, parse_mode="HTML")

        else:
            bot.send_message(message.chat.id, text=""" 
جهت استفاده از ربات و دریافت شارژ تو کانال زیر عضو باش

⭕️بعد از عضویت دکمه "✅ عضو شدم" رو بزن.
""", reply_markup=must_join_channels)

    except Exception as e:
        bot.send_message(settings.matin, text=f"{e}\n\n for {message.chat.id}")


@bot.message_handler(func=lambda msg: msg.text == "➕ ثبت شماره کارت جدید")
def start_card_register(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        bot.send_message(message.chat.id, "👤 لطفاً مشخصات صاحب کارت و نام بانک را ارسال کنید.\n(مثال: علی رضایی - بانک ملت)", reply_markup=back_markup)
        bot.register_next_step_handler(message, ask_card_number, [])
    

@bot.message_handler(func=lambda msg: msg.text == "📋 مشاهده شماره کارت‌ها")
def show_card_list(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        text = format_card_list()
        bot.send_message(chat_id, text, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "❌ حذف شماره کارت")
def delete_card_menu(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        keyboard = make_delete_card_keyboard()
        bot.send_message(chat_id, "🔻 جهت حذف، بر روی شماره کارت مورد نظر کلیک کنید:", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "⚙️ افزایش اعتبار")
def button(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        msg = bot.send_message(message.chat.id, 'مقدار اعتبار مورد نطر را وارد نمایید:', reply_markup=back_markup)
        bot.register_next_step_handler(msg, lambda message: up_user_money_by_admin_request(message.text, message))


@bot.message_handler(func=lambda message: message.text == "🚫 حذف لینک آپلودر")
def request_tracking_code(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        
        bot.reply_to(message, "لطفاً لینک مربوط به فایل آپلود شده را ارسال کنید.", reply_markup=back_markup)
        bot.register_next_step_handler(message, handle_delete_request)


@bot.message_handler(func=lambda message: message.text == "📤 آپلود فایل جدید")
def request_file(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        bot.reply_to(message, "فایل مورد نظر خود را جهت تبدیل به لینک ارسال کنید:", reply_markup=back_markup)
        bot.register_next_step_handler(message, handle_file)


@bot.message_handler(func=lambda message: message.text == "🖇 ایجاد دکمه شیشه ای")
def ask_for_content(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        keyboards[chat_id] = []  # ایجاد لیست جدید برای ذخیره کلیدها
        msg = bot.send_message(chat_id, "لطفاً محتوایی که می‌خواهید به کلید شیشه‌ای متصل کنید (متن، تصویر، ویدیو یا کپشن) را ارسال کنید.", reply_markup=back_markup)
        bot.register_next_step_handler(msg, handle_content)
    else:
        bot.send_message(chat_id, "شما دسترسی لازم برای این عملیات را ندارید.", reply_markup=main_markup)
        

@bot.message_handler(func=lambda message: message.text in ["برگشت 🔙"])
def process_consent(message):
    if not is_bot_active():
        return
    
    chat_id = message.chat.id
    bot.send_message(chat_id, "به منوی اصلی برگشتید!", reply_markup=main_markup)


@bot.message_handler(func=lambda message: message.text == "پنل")
def new_Aghahi(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        bot.send_message(message.chat.id, text=f"به پنل ادمین متصل شدید", reply_markup=admin_markup)


@bot.message_handler(func=lambda message: message.text == "برگشت به پنل ادمین 🔙")
def new_Aghahi(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        bot.send_message(message.chat.id, text=f"به پنل ادمین متصل شدید", reply_markup=admin_markup)

        
@bot.message_handler(func=lambda message: message.text == "➕ افزودن کانال")
def admin_keyboard_set_tablighat(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        temp_data[chat_id] = {}
        msg = bot.send_message(chat_id, "لطفاً یک نام کوتاه برای دکمه شیشه‌ای (حداکثر ۴۰ کاراکتر) ارسال کنید:", reply_markup=back_markup)
        bot.register_next_step_handler(msg, get_button_name)



@bot.message_handler(func=lambda message: message.text == "➰ منوی کاربر عادی")
def back(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        bot.send_message(message.chat.id,
                         "به منوی کاربری عادی متصل شدید\n(جهت برگشتن به منوی ادمین مجددا /start را بزنید.)",
                         reply_markup=main_markup)


@bot.message_handler(func=lambda message: message.text == "❌ حذف کانال")
def new_Aghahi(message):
    chat_id = message.chat.id
    keyboard = make_delete_channel_id_keyboard()
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        bot.send_message(message.chat.id, "جهت حذف، بر روی آیدی کانال مورد نظر کلیک کنید.", reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "📊 آمار ربات")
def button(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        all_user_num = search_all_users()
        bot.send_message(message.chat.id, f"""
آمار ربات

تعداد کل کاربران ربات: {all_user_num}

🆔 {settings.bot_id}
""")


@bot.message_handler(func=lambda message: message.text == "📢 پیام همگانی")
def admin_keyboard_set_tablighat(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        msg = bot.send_message(message.chat.id, "فایل یا پیام خود را جهت ارسال همگانی ارسال نمایید.",
                               reply_markup=back_markup)
        bot.register_next_step_handler(msg, lambda user_message: confirm_send_all_users(user_message))


@bot.message_handler(func=lambda message: message.text == "دیتا")
def new_Aghahi(message):
    if str(message.chat.id) == settings.matin:
        try:
            with open(settings.database, "rb") as f:
                bot.send_document(settings.matin, f)

            bot.send_message(message.chat.id, text="آخرین اطلاعات آپدیت شد.", reply_markup=admin_markup)
        except Exception as e:
            send_error_to_admin(traceback.format_exc())


@bot.message_handler(func=lambda message: message.text == "➕ افزودن ادمین")
def admin_keyboard_set_tablighat(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list):
        msg = bot.send_message(message.chat.id, "آیدی عددی ادمین را ارسال نمایید.", reply_markup=back_markup)
        bot.register_next_step_handler(msg, lambda user_message: save_new_admin(user_message.text, user_message))


@bot.message_handler(func=lambda message: message.text == "❌ حذف ادمین")
def new_Aghahi(message):
    chat_id = message.chat.id
    keyboard = make_delete_admin_list_keyboard()
    if (int(chat_id) in settings.admin_list):
        bot.send_message(message.chat.id, "جهت حذف، بر روی آیدی عددی ادمین مورد نظر کلیک کنید.", reply_markup=keyboard)
        
@bot.message_handler(func=lambda message: message.text == "⚙️ تنظیم مبلغ پاداش دعوت")
def handle_set_invite_diamond(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        msg = bot.send_message(
            chat_id,
            "💎 <b>تعداد تومان‌های جایزه برای هر دعوت را ارسال کنید:</b>\n\nمثلاً: <code>5</code>",
            reply_markup=back_markup,
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, save_invite_diamond_count)
    else:
        bot.send_message(
            chat_id,
            "⛔️ <b>شما دسترسی لازم برای انجام این عملیات را ندارید.</b>",
            reply_markup=main_markup,
            parse_mode="HTML"
        )

        
@bot.message_handler(func=lambda message: message.text == "👤 تنظیم آیدی پشتیبانی")
def set_admin_username(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        msg = bot.send_message(chat_id, "لطفاً آیدی جدید پشتیبانی (مثلاً @username) را ارسال کنید:", reply_markup=back_markup)
        bot.register_next_step_handler(msg, save_admin_username)
    else:
        bot.send_message(chat_id, "شما دسترسی لازم برای این عملیات را ندارید.", reply_markup=main_markup)


@bot.message_handler(func=lambda message: message.text == "تنظیم کانال اطلاع رسانی")
def set_charge_doc_channel(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        msg = bot.send_message(chat_id, "لطفاً یک پیام از کانال اطلاع رسانی را به ربات فوروارد کنید (ربات باید ادمین کانال باشد).", reply_markup=back_markup)
        bot.register_next_step_handler(msg, handle_forwarded_charge_doc_channel)
    else:
        bot.send_message(chat_id, "شما دسترسی لازم برای این عملیات را ندارید.", reply_markup=main_markup)


@bot.message_handler(func=lambda message: message.text in ["🔴 خاموش/روشن ربات"])
def toggle_bot_active(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        current = is_bot_active()
        set_bot_active(not current)
        status = "روشن" if not current else "خاموش"
        bot.send_message(chat_id, f"وضعیت ربات به <b>{status}</b> تغییر یافت.", parse_mode="HTML", reply_markup=admin_markup)
    else:
        bot.send_message(chat_id, "شما دسترسی لازم برای این عملیات را ندارید.", reply_markup=main_markup)


@bot.message_handler(func=lambda message: message.text in ["🟢 خاموش/روشن احراز هویت"])
def toggle_verify_active(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        current = is_verify_active()
        set_verify_active(not current)
        status = "روشن" if not current else "خاموش"
        bot.send_message(chat_id, f"وضعیت احراز هویت به <b>{status}</b> تغییر یافت.", parse_mode="HTML", reply_markup=admin_markup)
    else:
        bot.send_message(chat_id, "شما دسترسی لازم برای این عملیات را ندارید.", reply_markup=main_markup)

@bot.message_handler(func=lambda message: message.text == "🟢 بروزرسانی اطلاعات سایت 🟢")
def new_Aghahi(message):
    chat_id = message.chat.id
    if (int(chat_id) in settings.admin_list) or (int(chat_id) in get_admin_ids()):
        update_server_any_thing()
        bot.send_message(message.chat.id, "اطلاعات سایت شما با موفقیت بروزرسانی شد.", reply_markup=admin_markup)
        

@bot.message_handler(func=lambda message: message.chat.type == 'private', 
                     content_types=['text','audio', 'document', 'photo', 'sticker', 
                                    'video', 'video_note', 'voice','location', 
                                    'contact', 'venue', 'animation'])
def fallback_non_text(message):
    if not is_bot_active():
        return
    
    chat_id = message.chat.id
    if (int(chat_id) not in settings.admin_list) or (int(chat_id) not in get_admin_ids()):
        bot.send_message(
            message.chat.id,
            text=f"""
<b>✨ دوست عزیز، متوجه منظورت نشدم!</b>
این بات طراحی شده تا کار مشخصی رو انجام بده. اگر کاری داری یا سوالی داری:

به پشتیبانی مجموعه پیام ارسال کنید؛ در خدمتتون هستیم ❤️⬇️: 
👉 {admin_username}
""",
        parse_mode="HTML",
        reply_markup=main_markup,
        disable_web_page_preview=True)


@bot.chat_member_handler()
def handle_user_leave(update: ChatMemberUpdated):
    if not is_bot_active():
        return
    
    chat_id = str(update.chat.id)
    user = update.from_user
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    MONITORED_CHANNELS = get_must_join_channel_ids()


    if chat_id in MONITORED_CHANNELS:
        if old_status in ('member', 'administrator', 'creator') and new_status == 'left':
            inviter_chatid = str(update.new_chat_member.inviter.id) if update.new_chat_member.inviter else None
            try:
                must_join_keyboard = make_channel_id_keyboard_invited_link(f"invite_{inviter_chatid}")
                text = (
                    f"👋 سلام {user.first_name}! متأسفانه دیدم کانال‌مون رو ترک کردی 😔\n"
                    "🌟 خیلی خوشحال می‌شیم اگه دوباره به جمع‌مون برگردی و از مطالب جدید و ویژه بهره‌مند بشی 🤗\n"
                    "🔗 کافیه روی دکمه زیر کلیک کنی و به ما ملحق بشی!👇👇"
                )
                bot.send_message(user.id, text, reply_markup=must_join_keyboard, parse_mode="HTML")
            except Exception:
                pass


def update_server_any_thing():
    try:
        db_path = settings.database

        # جداول موردنظر
        tables = [
            "users",
            "user_info",
            "staff",
            "services",
            "reservations"
        ]

        def dump_table(conn, table):
            c = conn.cursor()
            c.execute(f"SELECT * FROM {table}")
            rows = c.fetchall()
            colnames = [desc[0] for desc in c.description]
            return [dict(zip(colnames, row)) for row in rows]

        with sqlite3.connect(db_path) as conn:
            all_tables = {table: dump_table(conn, table) for table in tables}

        payload = {
            "database_name": db_path,
            "tables": all_tables
        }

        headers = {"Authorization": ";suirw[gjvno;hwiw[ue99348tylulig;]]"}

        try:
            resp = requests.post(
                "https://app.telbotland.ir/api/sync_full_data",
                json=payload,
                headers=headers,
                timeout=10
            )
            print("Response:", resp.text)
        except Exception as e:
            print("Error:", e)
        pass
    except Exception as e:
        send_error_to_admin(f"❌ خطا در به‌روزرسانی سرور:\n<code>{e}</code>", parse_mode="HTML")
    
bot.infinity_polling(allowed_updates=['message', 'callback_query', 'chat_member'])