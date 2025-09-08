# invites_and_content.py
# -*- coding: utf-8 -*-

import sqlite3
import traceback
import random
import string
from typing import Optional, Callable, Dict, Any, List

# وابستگی‌ها با init تزریق می‌شوند
_bot = None
_settings = None
_admin_markup = None
_main_markup = None
_back_markup = None
_types = None
InlineKeyboardButton = None
InlineKeyboardMarkup = None

_send_error_to_admin: Callable[[str], None] = lambda msg: None
_get_all_channels: Callable[[], List[str]] = lambda: []
_get_current_timestamp: Callable[[], str] = lambda: ""
_invite_diamond_count: int = 0  # مبلغ/امتیاز هدیه‌ی دعوت

# استیت موقت برای ساخت کیبورد شیشه‌ای
_contents: Dict[int, Dict[str, Any]] = {}
_keyboards: Dict[int, List[Dict[str, Any]]] = {}

def init_invites_and_content(
    *,
    bot,
    settings,
    admin_markup=None,
    main_markup=None,
    back_markup=None,
    tg_types_module=None,
    InlineKeyboardButton_cls=None,
    InlineKeyboardMarkup_cls=None,
    send_error_to_admin: Callable[[str], None]=lambda msg: None,
    get_all_channels: Callable[[], List[str]]=lambda: [],
    get_current_timestamp: Callable[[], str]=lambda: "",
    invite_diamond_count: int = 0,
):
    """
    این تابع را در main.py صدا بزن تا ماژول آماده‌ی استفاده شود.
    """
    global _bot, _settings, _admin_markup, _main_markup, _back_markup
    global _types, InlineKeyboardButton, InlineKeyboardMarkup
    global _send_error_to_admin, _get_all_channels, _get_current_timestamp, _invite_diamond_count

    _bot = bot
    _settings = settings
    _admin_markup = admin_markup
    _main_markup = main_markup
    _back_markup = back_markup
    _types = tg_types_module
    InlineKeyboardButton = InlineKeyboardButton_cls
    InlineKeyboardMarkup = InlineKeyboardMarkup_cls

    _send_error_to_admin = send_error_to_admin
    _get_all_channels = get_all_channels
    _get_current_timestamp = get_current_timestamp
    _invite_diamond_count = invite_diamond_count

    # تضمین جدول‌ها
    create_invitations_table()
    create_uploaded_files_table()

# ================= Utils =================
def _conn():
    return sqlite3.connect(_settings.database)

# ================= جدول دعوت‌ها =================
def create_invitations_table():
    with _conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invited_chat_id TEXT NOT NULL,
                inviter_chat_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                channels TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                gift_given INTEGER NOT NULL DEFAULT 0,
                gift_amount INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()

def update_inviter_chatid(inviter: int, invited: int):
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET inviter_chatid = ? WHERE chat_id = ?", (inviter, invited))
            conn.commit()
    except Exception as e:
        _bot.send_message(_settings.matin, f"خطا در بروزرسانی inviter_chatid: {e}")


def invitation_record_exists(invited_chat_id: int) -> bool:
    """
    بررسی وجود رکورد دعوت برای یک invited_chat_id
    """
    try:
        with _conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM invitations WHERE invited_chat_id = ?", (invited_chat_id,))
            return cur.fetchone() is not None
    except Exception:
        _bot.send_message(_settings.matin, "Error in invite check.")
        return False


# برای سازگاری با کد قدیمی که نام گمراه‌کننده داشت:
check_user_existence = invitation_record_exists


def new_invite_to_bot(inviter: int, invited: int, invited_Firstname: str, invited_Lastname: str):
    """
    اگر قبلاً رکورد دعوت برای invited وجود نداشت، شمارنده‌ی دعوت‌های inviter را بالا ببرد.
    """
    if not invitation_record_exists(invited):
        up_money_invite_number_for_invite(inviter, invited, invited_Firstname, invited_Lastname)


def save_invitation(invited_chat_id: int, inviter_chat_id: int):
    """
    ذخیره‌ی رکورد دعوت جدید (اگر قبلاً برای invited ذخیره نشده).
    """
    if invitation_record_exists(invited_chat_id):
        return
    try:
        channels = ",".join(_get_all_channels())
        timestamp = _get_current_timestamp()
        with _conn() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO invitations (invited_chat_id, inviter_chat_id, timestamp, channels, status, gift_given, gift_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (invited_chat_id, inviter_chat_id, timestamp, channels, 'active', 0, 0))
            conn.commit()
    except Exception:
        _send_error_to_admin(traceback.format_exc())


def give_gift_to_inviter_if_needed(invited_chat_id: int):
    """
    اگر برای دعوتِ این کاربر هدیه‌ای داده نشده بود، به دعوت‌کننده هدیه بده و وضعیت را آپدیت کن.
    """
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT inviter_chat_id, gift_given FROM invitations WHERE invited_chat_id = ?", (invited_chat_id,))
            row = c.fetchone()
            if not row:
                return
            inviter_chat_id, gift_given = row
            if gift_given:
                return

            gift_amount = int(_invite_diamond_count) if _invite_diamond_count else 0

            # افزایش موجودی دعوت‌کننده
            c.execute("SELECT money FROM users WHERE chat_id = ?", (inviter_chat_id,))
            money_row = c.fetchone()
            current_money = (money_row[0] if money_row and money_row[0] is not None else 0)
            new_money = current_money + gift_amount
            c.execute("UPDATE users SET money = ? WHERE chat_id = ?", (new_money, inviter_chat_id))

            # ثبت هدیه
            c.execute("UPDATE invitations SET gift_given = 1, gift_amount = ? WHERE invited_chat_id = ?", (gift_amount, invited_chat_id))
            conn.commit()

        # اطلاع به دعوت‌کننده
        if gift_amount > 0:
            _bot.send_message(inviter_chat_id, f"🎁 به خاطر فعال‌سازی کاربر دعوت‌شده، {gift_amount} به اعتبار شما افزوده شد!")
    except Exception:
        _send_error_to_admin(traceback.format_exc())


def get_invitation_status(invited_chat_id: int) -> Optional[str]:
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT status FROM invitations WHERE invited_chat_id = ?", (invited_chat_id,))
            res = c.fetchone()
            return res[0] if res else None
    except Exception:
        _send_error_to_admin(traceback.format_exc())
        return None


def update_invitation_status(invited_chat_id: int):
    """
    اگر رکوردی وجود دارد و وضعیت inactive بود، active کن.
    """
    if not invitation_record_exists(invited_chat_id):
        return
    try:
        if get_invitation_status(invited_chat_id) == "inactive":
            with _conn() as conn:
                c = conn.cursor()
                c.execute("UPDATE invitations SET status = ? WHERE invited_chat_id = ?", ("active", invited_chat_id))
                conn.commit()
    except Exception:
        _send_error_to_admin(traceback.format_exc())


def up_money_invite_number_for_invite(chat_id: int, invited: int, invited_Firstname: str, invited_Lastname: str):
    """
    +1 به invited_users در جدول users و اطلاع رسانی به دعوت‌کننده؛ سپس وضعیت دعوت را آپدیت می‌کند.
    """
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT invited_users FROM users WHERE chat_id = ?", (chat_id,))
            row = c.fetchone()
            invited_users_value = (row[0] if row and row[0] is not None else 0) + 1
            c.execute("UPDATE users SET invited_users = ? WHERE chat_id = ?", (invited_users_value, chat_id))
            conn.commit()

        # پیام به دعوت‌کننده
        del_btn_kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ متوجه شدم", callback_data=f"delete_button_{chat_id}")]])
        _bot.send_message(
            chat_id,
            f"کاربر {invited_Firstname} {invited_Lastname}\nبا لینک دعوت شما به ربات پیوست.",
            reply_markup=del_btn_kb
        )

        update_invitation_status(invited)
    except Exception as e:
        _bot.send_message(_settings.matin, f"خطا در افزایش تعداد کاربران دعوت شده: {e}")


def search_inviter_chatid(chat_id: int) -> Optional[int]:
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT inviter_chatid FROM users WHERE chat_id=?", (chat_id,))
            row = c.fetchone()
            return row[0] if row else None
    except Exception as e:
        _bot.send_message(_settings.matin, text=f"new error in search_inviter_chatid\n\n{e}")
        return None


def search_user_invited_users(chat_id: int) -> Optional[int]:
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT invited_users FROM users WHERE chat_id=?", (chat_id,))
            row = c.fetchone()
            return row[0] if row else None
    except Exception as e:
        _bot.send_message(_settings.matin, text=f"new error in search_user_invited_users\n\n{e}")

# ================= فایل‌های آپلودی =================
def create_uploaded_files_table():
    try:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    caption TEXT,
                    tracking_code TEXT NOT NULL UNIQUE
                )
            """)
            conn.commit()
    except sqlite3.Error:
        _send_error_to_admin(traceback.format_exc())  

def save_file_to_db(file_id: str, file_type: str, caption: str, tracking_code: str):
    create_uploaded_files_table()
    try:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO uploaded_files (file_id, file_type, caption, tracking_code)
                VALUES (?, ?, ?, ?)
            """, (file_id, file_type, caption, tracking_code))
            conn.commit()
    except sqlite3.Error:
        _send_error_to_admin(traceback.format_exc())


def get_file_from_db(tracking_code: str):
    try:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_id, file_type, caption FROM uploaded_files WHERE tracking_code = ?", (tracking_code,))
            return cursor.fetchone()  # (file_id, file_type, caption) or None
    except sqlite3.Error:
        _send_error_to_admin(traceback.format_exc())
        return None


def delete_file_by_tracking_code(tracking_code: str) -> bool:
    try:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM uploaded_files WHERE tracking_code = ?", (tracking_code,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        _send_error_to_admin(traceback.format_exc())
        return False


def generate_tracking_code(length: int = 10) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def extract_tracking_code(link: str) -> Optional[str]:
    # انتظار:  ?start=upload_XXXXXXXXXX
    if not link or (not link.startswith(str(_settings.bot_link))):
        return None
    try:
        return link.split("upload_")[1]
    except IndexError:
        return None


def send_file_by_type(chat_id: int, file_id: str, file_type: str, caption: Optional[str]):
    caption = (caption or "").strip() or " "
    try:
        if file_type == "photo":
            _bot.send_photo(chat_id, file_id, caption=caption, reply_markup=_main_markup)
        elif file_type == "video":
            _bot.send_video(chat_id, file_id, caption=caption, reply_markup=_main_markup)
        elif file_type == "audio":
            _bot.send_audio(chat_id, file_id, caption=caption, reply_markup=_main_markup)
        elif file_type == "document":
            _bot.send_document(chat_id, file_id, caption=caption, reply_markup=_main_markup)
        elif file_type == "voice":
            _bot.send_voice(chat_id, file_id, caption=caption, reply_markup=_main_markup)
        elif file_type == "video_note":
            _bot.send_video_note(chat_id, file_id, reply_markup=_main_markup)
        elif file_type == "text":
            _bot.send_message(chat_id, caption, reply_markup=_main_markup)
        else:
            _bot.send_message(chat_id, "نوع فایل پشتیبانی نمی‌شود.", reply_markup=_main_markup)
    except Exception:
        _send_error_to_admin(traceback.format_exc()) 

   