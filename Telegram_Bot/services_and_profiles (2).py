# services_and_profiles.py
# -*- coding: utf-8 -*-

import sqlite3
from typing import Any, Callable, Optional
import traceback
from datetime import datetime
import pytz

# ===== وابستگی‌ها =====
_bot = None
_settings = None
_types = None

_admin_markup = None
_main_markup = None
_back_markup = None
_continue_markup = None

_check_return_btn: Callable[[Any], bool] = lambda _m: False
_send_error_to_admin: Callable[[str], None] = lambda msg: None
_get_admin_ids: Callable[[], list] = lambda: []

# ========== INIT ==========
def init_services_and_profiles(
    *,
    bot,
    settings,
    tg_types_module,
    admin_markup,
    main_markup,
    back_markup,
    continue_markup,
    check_return_btn: Callable[[Any], bool],
    send_error_to_admin: Callable[[str], None],
    get_admin_ids: Callable[[], list],
):
    global _bot, _settings, _types, _admin_markup, _main_markup, _back_markup, _continue_markup
    global _check_return_btn, _send_error_to_admin, _get_admin_ids

    _bot = bot
    _settings = settings
    _types = tg_types_module
    _admin_markup = admin_markup
    _main_markup = main_markup
    _back_markup = back_markup
    _continue_markup = continue_markup

    _check_return_btn = check_return_btn
    _send_error_to_admin = send_error_to_admin
    _get_admin_ids = get_admin_ids

    create_tables()

# ========== DB ==========
def _conn():
    return sqlite3.connect(_settings.database)

def create_tables():
    """ایجاد تمام جداول مورد نیاز"""
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS user_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                duration INTEGER DEFAULT 60,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                staff_id INTEGER NOT NULL,
                services TEXT NOT NULL,
                day TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                total_price REAL NOT NULL,
                status TEXT DEFAULT 'confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(chat_id),
                FOREIGN KEY (staff_id) REFERENCES staff(id)
            )''')
            conn.commit()
    except Exception:
        _send_error_to_admin(traceback.format_exc())


# ========== Utilities ==========
def is_admin(chat_id) -> bool:
    try:
        chat_id = int(chat_id)
    except (ValueError, TypeError):
        return False
    if hasattr(_settings, "admin_list") and chat_id in getattr(_settings, "admin_list"):
        return True
    return chat_id in set(_get_admin_ids())

def check_return(message) -> bool:
    """بررسی دکمه بازگشت (نسخه مستقل برای این فلو)"""
    if getattr(message, "text", None) == "برگشت 🔙":
        chat_id = message.chat.id
        if is_admin(chat_id):
            _bot.send_message(chat_id, "🔙 بازگشت به پنل ادمین", reply_markup=_admin_markup)
        else:
            _bot.send_message(chat_id, "✅ به منوی اصلی برگشتید", reply_markup=_main_markup)
        return True
    return False

def get_current_datetime():
    iran_tz = pytz.timezone('Asia/Tehran')
    return datetime.now(iran_tz)

def get_weekday_name_fa(day_num: int) -> str:
    days = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه', 'یکشنبه']
    return days[day_num % 7]

# ========== Services Flow ==========
def get_service_name(message):
    if check_return(message):
        return
    chat_id = message.chat.id
    service_name = (message.text or "").strip()

    if len(service_name) < 2:
        msg = _bot.send_message(chat_id, "❌ نام خدمت باید حداقل 2 کاراکتر باشد. مجدداً وارد کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, get_service_name)
        return

    msg = _bot.send_message(
        chat_id,
        f"💰 قیمت خدمت «{service_name}» را به تومان وارد کنید:\n\nمثال: 50000",
        reply_markup=_back_markup
    )
    _bot.register_next_step_handler(msg, lambda m: get_service_price(m, service_name))

def get_service_price(message, service_name: str):
    if check_return(message):
        return
    chat_id = message.chat.id
    try:
        price = int((message.text or "").strip())
        if price <= 0:
            raise ValueError("positive")

        with _conn() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO services (name, price) VALUES (?, ?)", (service_name, price))
            conn.commit()

        _bot.send_message(
            chat_id,
            f"✅ خدمت جدید اضافه شد:\n\n📝 نام: {service_name}\n💰 قیمت: {price:,} تومان",
            reply_markup=_continue_markup
        )
        _bot.register_next_step_handler_by_chat_id(chat_id, ask_continue_service)
    except Exception:
        msg = _bot.send_message(chat_id, "❌ قیمت باید عدد صحیح باشد. مجدداً وارد کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, lambda m: get_service_price(m, service_name))

def ask_continue_service(message):
    if check_return(message):
        return
    chat_id = message.chat.id
    if message.text == "✅ تمام شد":
        _bot.send_message(chat_id, "✅ تنظیمات خدمات با موفقیت انجام شد", reply_markup=_admin_markup)
    elif message.text == "➕ ادامه":
        msg = _bot.send_message(chat_id, "💇🏻‍♂️ نام خدمت بعدی را وارد کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, get_service_name)
    else:
        msg = _bot.send_message(chat_id, "لطفاً از دکمه‌ها استفاده کنید:", reply_markup=_continue_markup)
        _bot.register_next_step_handler(msg, ask_continue_service)









