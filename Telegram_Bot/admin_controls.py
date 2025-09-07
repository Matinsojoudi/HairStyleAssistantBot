# admin_controls.py
# -*- coding: utf-8 -*- 

import sqlite3
import traceback
import re
from typing import Callable, Optional, Dict, Any, List

# ===== وابستگی‌های تزریقی با init =====
_bot = None
_settings = None
_types = None
_admin_markup = None
_main_markup = None
_back_markup = None

InlineKeyboardButton = None
InlineKeyboardMarkup = None

_check_return_2: Callable[[Any], bool] = lambda _m: False
_send_error_to_admin: Callable[[str], None] = lambda msg: None

# ===== State موقت برای ایجاد کانال/دکمه =====
_temp_data: Dict[int, Dict[str, Any]] = {}

# ===== وضعیت‌ها/تنظیمات کش‌شده =====
verify_active: bool = True
bot_active: bool = True
admin_username: Optional[str] = None
charge_doc_channel_id: Optional[str] = None
invite_diamond_count: Optional[int] = None

# ---------- init ----------
def init_admin_controls(
    *,
    bot,
    settings,
    tg_types_module,
    InlineKeyboardButton_cls,
    InlineKeyboardMarkup_cls,
    admin_markup=None,
    main_markup=None,
    back_markup=None,
    check_return_2: Callable[[Any], bool] = lambda _m: False,
    send_error_to_admin: Callable[[str], None] = lambda msg: None,
):
    """
    این تابع را در main.py یک‌بار صدا بزنید تا ماژول آماده شود.
    """
    global _bot, _settings, _types, _admin_markup, _main_markup, _back_markup
    global InlineKeyboardButton, InlineKeyboardMarkup
    global _check_return_2, _send_error_to_admin

    _bot = bot
    _settings = settings
    _types = tg_types_module
    _admin_markup = admin_markup
    _main_markup = main_markup
    _back_markup = back_markup
    InlineKeyboardButton = InlineKeyboardButton_cls
    InlineKeyboardMarkup = InlineKeyboardMarkup_cls
    _check_return_2 = check_return_2
    _send_error_to_admin = send_error_to_admin

    # جداول و تنظیمات اولیه
    _init_verify_status_db()
    _load_admin_username()
    _init_bot_status_db()
    _init_charge_doc_channel_db()
    _load_charge_doc_channel_id()
    _load_invite_diamond_setting()
    _ensure_channels_table()

# ---------- ابزار DB ----------
def _conn():
    return sqlite3.connect(_settings.database)

def _ensure_channels_table():
    with _conn() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        button_name TEXT NOT NULL,
                        link_type TEXT NOT NULL,
                        link TEXT NOT NULL,
                        channel_id TEXT
                    )''')
        conn.commit()

# ---------- فلو ساخت دکمه/کانال ----------
def get_button_name(message):
    if _check_return_2(message):
        return
    chat_id = message.chat.id
    name = (message.text or "").strip()
    if len(name) > 40:
        msg = _bot.send_message(chat_id, "نام دکمه نباید بیشتر از ۴۰ کاراکتر باشد. لطفاً مجدداً ارسال کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, get_button_name)
        return
    _temp_data.setdefault(chat_id, {})
    _temp_data[chat_id]['button_name'] = name
    msg = _bot.send_message(chat_id, "لینک شما برای تلگرام است یا سایر موارد؟", reply_markup=create_selection_markup())
    _bot.register_next_step_handler(msg, handle_link_type)


def handle_link_type(message):
    if _check_return_2(message):
        return
    chat_id = message.chat.id
    selection = (message.text or "").strip()
    _temp_data.setdefault(chat_id, {})
    _temp_data[chat_id]["link_type"] = selection

    if selection == "تلگرام":
        msg = _bot.send_message(chat_id, "باشه! لینک یا آیدی کانال/گروه تلگرامی را بفرست (ربات باید ادمین باشد).", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, get_telegram_link)
    elif selection == "سایر موارد":
        msg = _bot.send_message(chat_id, "لینک سایت/ربات/اینستاگرام یا هر لینک دیگر را ارسال کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, get_other_link)
    else:
        # انتخاب نامعتبر
        msg = _bot.send_message(chat_id, "گزینه معتبر نیست. «تلگرام» یا «سایر موارد» را انتخاب کنید.", reply_markup=create_selection_markup())
        _bot.register_next_step_handler(msg, handle_link_type)


def get_telegram_link(message):
    if _check_return_2(message):
        return

    chat_id = message.chat.id
    link = (message.text or "").strip()

    # پشتیبانی از @id
    if link.startswith("@"):
        link = f"https://t.me/{link[1:]}"

    # ولیدیشن لینک تلگرام
    if not re.match(r"^https://t\.me/\S+$", link):
        msg = _bot.send_message(chat_id, "لینک یا آیدی معتبر ارسال کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, get_telegram_link)
        return

    _temp_data.setdefault(chat_id, {})
    _temp_data[chat_id]['link'] = link
    msg = _bot.send_message(chat_id, "یک پیام از کانال/گروه فوروارد کن یا آیدی عددی را بفرست (باید با -100 شروع شود):", reply_markup=_back_markup)
    _bot.register_next_step_handler(msg, get_telegram_id)


def get_telegram_id(message):
    if _check_return_2(message):
        return

    chat_id = message.chat.id
    _temp_data.setdefault(chat_id, {})

    if getattr(message, "forward_from_chat", None):
        _temp_data[chat_id]["channel_id"] = message.forward_from_chat.id
    elif (message.text or "").startswith("-100"):
        _temp_data[chat_id]["channel_id"] = (message.text or "").strip()
    else:
        msg = _bot.send_message(chat_id, "آیدی عددی باید با -100 شروع شود. لطفاً مجدداً ارسال کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, get_telegram_id)
        return

    _save_channel_row(chat_id)


def get_other_link(message):
    if _check_return_2(message):
        return

    chat_id = message.chat.id
    link = (message.text or "").strip()
    _temp_data.setdefault(chat_id, {})
    _temp_data[chat_id]["link"] = link

    _save_channel_row(chat_id)


def _save_channel_row(chat_id: int):
    try:
        data = _temp_data.get(chat_id, {})
        with _conn() as conn:
            c = conn.cursor()
            c.execute("BEGIN TRANSACTION")
            c.execute('''CREATE TABLE IF NOT EXISTS channels (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            button_name TEXT NOT NULL,
                            link_type TEXT NOT NULL,
                            link TEXT NOT NULL,
                            channel_id TEXT
                        )''')
            c.execute("INSERT INTO channels (button_name, link_type, link, channel_id) VALUES (?, ?, ?, ?)",
                      (data.get("button_name"), data.get("link_type"), data.get("link"), data.get("channel_id")))
            conn.commit()
        _bot.send_message(chat_id, "✅ اطلاعات با موفقیت ذخیره شد.", reply_markup=_admin_markup)
        _temp_data.pop(chat_id, None)
    except Exception as e:
        _bot.send_message(chat_id, "❌ خطا در ذخیره اطلاعات", reply_markup=_admin_markup)
        _bot.send_message(_settings.matin, f"❌ خطا در ذخیره اطلاعات: {e}", reply_markup=_admin_markup)


def create_selection_markup():
    markup = _types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row("تلگرام", "سایر موارد")
    markup.row("برگشت 🔙")
    return markup

# ---------- کیف پول/اعتبار ----------
def less_user_money(chat_id: int, num: float) -> bool:
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT money FROM users WHERE chat_id = ?", (chat_id,))
            row = c.fetchone()
            money_value = float(row[0]) if row and row[0] is not None else 0.0
            num = float(num)

            if money_value >= num:
                new_money_value = money_value - num
                c.execute("UPDATE users SET money = ? WHERE chat_id = ?", (new_money_value, chat_id))
                conn.commit()
                return True
            else:
                _bot.send_message(chat_id=chat_id, text="اعتبار شما جهت انجام این عملیات کافی نمی‌باشد، لطفاً ابتدا اعتبار خود را افزایش دهید.")
                return False
    except Exception as e:
        _bot.send_message(_settings.matin, f"خطا در کاهش اعتبار: {e}")
        return False


def add_money(chat_id: int, amount: int):
    amount = int(amount)
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT money FROM users WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        current_money = row[0] if row and row[0] is not None else 0
        new_money = current_money + amount
        # UPSERT
        c.execute("""INSERT INTO users (chat_id, money) VALUES (?, ?)
                     ON CONFLICT(chat_id) DO UPDATE SET money = excluded.money""",
                  (chat_id, new_money))
        conn.commit()


def up_user_money_by_admin_request(num: int, message):
    if _check_return_2(message):
        return
    msg = _bot.send_message(message.chat.id, text="لطفا چت آیدی فرد مورد نظر را وارد نمایید:")
    _bot.register_next_step_handler(msg, lambda m: up_user_money_by_admin(chat_id=m.text, num=num, message=message))


def up_user_money_by_admin(chat_id: str, num: int, message):
    if chat_id == "برگشت 🔙":
        _bot.send_message(message.chat.id, "به منوی ادمین برگشتید.", reply_markup=_admin_markup)
        return
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT money FROM users WHERE chat_id = ?", (chat_id,))
            row = c.fetchone()
            money_value = int(row[0]) if row and row[0] is not None else 0
            new_money_value = money_value + int(num)
            c.execute("UPDATE users SET money = ? WHERE chat_id = ?", (new_money_value, chat_id))
            conn.commit()

        _bot.send_message(int(chat_id), f'اعتبار شما افزایش یافت.\nمقدار کل اعتبار شما: {new_money_value}', reply_markup=_main_markup)
        _bot.send_message(message.chat.id, f'تومان ({chat_id}) افزایش یافت.\nمقدار کل اعتبار: {new_money_value}', reply_markup=_main_markup)
    except Exception as e:
        _bot.send_message(_settings.matin, f"خطا در افزایش امتیاز: {e}")


def read_and_extract_top_users(database_path: str) -> Optional[List[int]]:
    conn = sqlite3.connect(database_path)
    c = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        c.execute("SELECT chat_id, invited_users FROM users")
        data = c.fetchall()
        sorted_data = sorted(data, key=lambda x: (x[1] or 0), reverse=True)
        top_10_users = [int(chat_id) for chat_id, _ in sorted_data[:10]]
        conn.commit()
        return top_10_users
    except Exception as e:
        _bot.send_message(_settings.matin, f"Error occurred: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def search_user_join_date(chat_id: int) -> Optional[str]:
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT joined_at FROM users WHERE chat_id=?", (chat_id,))
            row = c.fetchone()
            return row[0] if row else None
    except Exception as e:
        _bot.send_message(_settings.matin, text=f"new error in search_user_join_date\n\n{e}")
        return None

# ---------- کانال‌های ضروری عضویت ----------
def get_must_join_channel_ids() -> List[str]:
    channel_ids: List[str] = []
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT channel_id FROM channels WHERE channel_id IS NOT NULL")
            for (cid,) in c.fetchall():
                if cid:
                    channel_ids.append(cid)
    except Exception:
        _send_error_to_admin(traceback.format_exc())
    return channel_ids

# ---------- وضعیت‌های تایید شماره/بات ----------
def _init_verify_status_db():
    global verify_active
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS bot_status (
                    key TEXT PRIMARY KEY,
                    value INTEGER
                )
            """)
            c.execute("INSERT OR IGNORE INTO bot_status (key, value) VALUES ('verify_active', 1)")
            conn.commit()
            c.execute("SELECT value FROM bot_status WHERE key='verify_active'")
            row = c.fetchone()
            verify_active = (row[0] == 1) if row else True
    except Exception:
        _send_error_to_admin(traceback.format_exc())

def set_verify_active(value: bool):
    global verify_active
    verify_active = value
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("UPDATE bot_status SET value=? WHERE key='verify_active'", (1 if value else 0,))
            conn.commit()
    except Exception:
        _send_error_to_admin(traceback.format_exc())

def is_verify_active() -> bool:
    return verify_active

def _init_bot_status_db():
    global bot_active
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS bot_status (
                    key TEXT PRIMARY KEY,
                    value INTEGER
                )
            """)
            c.execute("INSERT OR IGNORE INTO bot_status (key, value) VALUES ('bot_active', 1)")
            conn.commit()
            c.execute("SELECT value FROM bot_status WHERE key='bot_active'")
            row = c.fetchone()
            bot_active = (row[0] == 1) if row else True
    except Exception:
        _send_error_to_admin(traceback.format_exc())

def set_bot_active(value: bool):
    global bot_active
    bot_active = value
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("UPDATE bot_status SET value=? WHERE key='bot_active'", (1 if value else 0,))
            conn.commit()
    except Exception:
        _send_error_to_admin(traceback.format_exc())

def is_bot_active() -> bool:
    return bot_active

# ---------- آیدی پشتیبانی ----------
def save_admin_username(message):
    global admin_username
    if _check_return_2(message):
        return
    chat_id = message.chat.id
    username = (message.text or "").strip()
    if not username.startswith("@"):
        msg = _bot.send_message(chat_id, "آیدی باید با @ شروع شود. لطفاً مجدداً ارسال کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, save_admin_username)
        return
    admin_username = username
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            c.execute("""
                INSERT INTO bot_settings (key, value) VALUES ('admin_username', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (username,))
            conn.commit()
        _bot.send_message(chat_id, f"آیدی پشتیبانی با موفقیت به {username} تغییر یافت.", reply_markup=_admin_markup)
    except Exception as e:
        _bot.send_message(_settings.matin, f"خطا در ذخیره آیدی پشتیبانی: {e}")

def _load_admin_username():
    global admin_username
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            c.execute("SELECT value FROM bot_settings WHERE key='admin_username'")
            row = c.fetchone()
            if row:
                admin_username = row[0]
    except Exception:
        pass

# ---------- کانال مدارک شارژ ----------
def _init_charge_doc_channel_db():
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS charge_doc_channel (
                    id INTEGER PRIMARY KEY,
                    channel_id TEXT
                )
            """)
            conn.commit()
    except Exception:
        _send_error_to_admin(traceback.format_exc())

def save_charge_doc_channel_id(channel_id: int):
    global charge_doc_channel_id
    _init_charge_doc_channel_db()
    charge_doc_channel_id = str(channel_id)
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO charge_doc_channel (id, channel_id) VALUES (1, ?)
                ON CONFLICT(id) DO UPDATE SET channel_id=excluded.channel_id
            """, (str(channel_id),))
            conn.commit()
    except Exception:
        _send_error_to_admin(traceback.format_exc())

def _load_charge_doc_channel_id():
    global charge_doc_channel_id
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT channel_id FROM charge_doc_channel WHERE id=1")
            row = c.fetchone()
            if row and row[0]:
                charge_doc_channel_id = row[0]
    except Exception:
        pass

def handle_forwarded_charge_doc_channel(message):
    if _check_return_2(message):
        return
    chat_id = message.chat.id
    if not getattr(message, "forward_from_chat", None):
        msg = _bot.send_message(
            chat_id,
            "⚠️ <b>لطفاً حتماً یک پیام از کانال را به ربات فوروارد کنید.</b>\n\n"
            "🔹 <b>قبل از فوروارد کردن پیام، باید ربات را به عنوان <u>ادمین</u> در آن کانال اضافه کنید.</b>\n"
            "در غیر این صورت ربات نمی‌تواند کانال را شناسایی کند.\n\n"
            "✅ مراحل: ۱) ربات را ادمین کنید ۲) یک پیام از همان کانال فوروارد کنید.",
            reply_markup=_back_markup,
            parse_mode="HTML"
        )
        _bot.register_next_step_handler(msg, handle_forwarded_charge_doc_channel)
        return
    channel_id = message.forward_from_chat.id
    try:
        _bot.send_message(channel_id, "✅ ربات با موفقیت در این کانال تنظیم شد.")
        save_charge_doc_channel_id(channel_id)
        _bot.send_message(chat_id, f"کانال اطلاع‌رسانی تنظیم شد.\nChat ID: <code>{channel_id}</code>", parse_mode="HTML", reply_markup=_admin_markup)
    except Exception:
        _bot.send_message(chat_id, "❌ ربات باید ادمین کانال باشد؛ عملیات متوقف شد.", reply_markup=_admin_markup)
        _send_error_to_admin(traceback.format_exc())

# ---------- تنظیم جایزه دعوت ----------
def save_invite_diamond_count(message):
    global invite_diamond_count
    if _check_return_2(message):
        return

    chat_id = message.chat.id
    diamond_count = (message.text or "").strip()

    if not diamond_count.isdigit():
        msg = _bot.send_message(
            chat_id,
            "❗️ <b>لطفاً فقط یک عدد ارسال کنید.</b>\nمثلاً: <code>5</code>",
            reply_markup=_back_markup,
            parse_mode="HTML"
        )
        _bot.register_next_step_handler(msg, save_invite_diamond_count)
        return

    invite_diamond_count = int(diamond_count)

    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS invite_diamond_config (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT
                )
            """)
            c.execute("""
                INSERT INTO invite_diamond_config (setting_key, setting_value)
                VALUES ('invite_reward', ?)
                ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value
            """, (diamond_count,))
            conn.commit()

        _bot.send_message(
            chat_id,
            f"✅ <b>مبلغ اعتبار جایزه به</b> <code>{diamond_count}</code> <b>تنظیم شد.</b>",
            reply_markup=_admin_markup,
            parse_mode="HTML"
        )
    except Exception:
        _send_error_to_admin(traceback.format_exc())
        
def _load_invite_diamond_setting():
    global invite_diamond_count
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS invite_diamond_config (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT
                )
            """)
            c.execute("SELECT setting_value FROM invite_diamond_config WHERE setting_key='invite_reward'")
            row = c.fetchone()
            if row:
                try:
                    invite_diamond_count = int(row[0])
                except ValueError:
                    invite_diamond_count = None
    except Exception:
        pass