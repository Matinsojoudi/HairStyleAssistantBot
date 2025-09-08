# helpers.py
# -*- coding: utf-8 -*-

from typing import Callable, Optional, List
import sqlite3
import traceback
import time
import threading

try:
    import jdatetime
except ImportError:
    # اگر روی محیطی بدون jdatetime اجرا شد، حداقل کرش نکند
    from datetime import datetime as jdatetime  # fallback ناقص، بهتره jdatetime نصب باشد

# این‌ها با init_helpers تزریق می‌شوند:
_bot = None
_settings = None
_admin_markup = None
_main_markup = None
_stop_event: Optional[threading.Event] = None

# توابع خارجی که در کد شما استفاده شده و اینجا تزریق می‌کنیم:
_send_error_to_admin: Callable[[str], None] = lambda msg: None
_check_return_2: Callable[..., bool] = lambda *a, **k: False
_search_inviter_chatid: Callable[[int], Optional[int]] = lambda invited_id: None
_up_money_invite_number_for_invite: Callable[[int, int, str, str], None] = lambda *a, **k: None
_get_invitation_status: Callable[[int], str] = lambda invited_id: "inactive"
_check_user_existence: Callable[[int], bool] = lambda chat_id: False

# کلاس‌ها/انواع تلگرام را دیرهنگام از ماژول اصلی بگیریم تا وابستگی سخت ایجاد نشود
types = None
InlineKeyboardButton = None
InlineKeyboardMarkup = None


def init_helpers(
    *,
    bot,
    settings,
    admin_markup=None,
    main_markup=None,
    stop_event: Optional[threading.Event]=None,
    send_error_to_admin: Callable[[str], None]=lambda msg: None,
    check_return_2: Callable[..., bool]=lambda *a, **k: False,
    search_inviter_chatid: Callable[[int], Optional[int]]=lambda invited_id: None,
    up_money_invite_number_for_invite: Callable[[int, int, str, str], None]=lambda *a, **k: None,
    get_invitation_status: Callable[[int], str]=lambda invited_id: "inactive",
    check_user_existence: Callable[[int], bool]=lambda chat_id: False,
    tg_types_module=None,
    InlineKeyboardButton_cls=None,
    InlineKeyboardMarkup_cls=None,
):
    """
    این تابع را در main.py یک‌بار صدا بزنید تا تمام وابستگی‌ها به ماژول تزریق شود.
    """
    global _bot, _settings, _admin_markup, _main_markup, _stop_event
    global _send_error_to_admin, _check_return_2
    global _search_inviter_chatid, _up_money_invite_number_for_invite
    global _get_invitation_status, _check_user_existence
    global types, InlineKeyboardButton, InlineKeyboardMarkup

    _bot = bot
    _settings = settings
    _admin_markup = admin_markup
    _main_markup = main_markup
    _stop_event = stop_event or threading.Event()

    _send_error_to_admin = send_error_to_admin
    _check_return_2 = check_return_2
    _search_inviter_chatid = search_inviter_chatid
    _up_money_invite_number_for_invite = up_money_invite_number_for_invite
    _get_invitation_status = get_invitation_status
    _check_user_existence = check_user_existence

    types = tg_types_module
    InlineKeyboardButton = InlineKeyboardButton_cls
    InlineKeyboardMarkup = InlineKeyboardMarkup_cls

    # جدول لیست بلاک را مطمئن می‌سازیم ایجاد شده
    create_block_list_table()


# ================== ابزارهای تاریخ ==================
def get_current_timestamp():
    return jdatetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_current_date():
    return jdatetime.now().strftime("%Y-%m-%d")

# ================== DB Utils ==================
def _conn():
    return sqlite3.connect(_settings.database)

def create_block_list_table():
    with _conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS block_list (
                chat_id INTEGER PRIMARY KEY
            )
        """)
        conn.commit()

# ================== Users ==================
def save_info(user_id, first_name, last_name, chat_id, user_name):
    try:
        update_block_list(chat_id, "delete")
        with _conn() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                            chat_id INTEGER PRIMARY KEY,
                            user_id INTEGER,
                            money INTEGER,
                            invited_users INTEGER,
                            inviter_chatid INTEGER,
                            phone_number TEXT,
                            verify TEXT,
                            joined_at TEXT,
                            first_name TEXT,
                            last_name TEXT,
                            user_name TEXT
                        )''')

            c.execute("SELECT 1 FROM users WHERE chat_id=?", (chat_id,))
            exists = c.fetchone() is not None

            if exists:
                c.execute("""UPDATE users
                             SET first_name=?, last_name=?, user_name=?
                             WHERE chat_id=?""",
                          (first_name, last_name, user_name, chat_id))
            else:
                joined_at = str(get_current_date())
                c.execute("""INSERT INTO users
                             (chat_id, user_id, money, invited_users, inviter_chatid,
                              phone_number, verify, joined_at, first_name, last_name, user_name)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                          (chat_id, user_id, 0, 0, None, None, None, joined_at,
                           first_name, last_name, user_name))
            conn.commit()

        update_invited_channels(chat_id, first_name, last_name)
    except sqlite3.Error as e:
        _bot.send_message(_settings.matin, f"An error occurred in save_info for {chat_id}:\n{e}")

def search_all_users() -> int:
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        return int(c.fetchone()[0])

# ================== Invites / Channels ==================
def update_invited_channels(invited_chat_id, first_name, last_name):
    if _check_user_existence(invited_chat_id):
        try:
            new_channels = ",".join(get_all_channels())
            with _conn() as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE invitations
                    SET channels = ?
                    WHERE invited_chat_id = ?
                """, (new_channels, invited_chat_id))
                conn.commit()

            if _get_invitation_status(invited_chat_id) == "inactive":
                inviter = _search_inviter_chatid(invited_chat_id)
                _up_money_invite_number_for_invite(inviter, invited_chat_id, first_name, last_name)

        except Exception:
            _send_error_to_admin(traceback.format_exc())


def get_all_channels() -> List[str]:
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT channel_id FROM channels")
            channels = [row[0] for row in c.fetchall() if row[0] and str(row[0]).startswith("-100")]
            return channels
    except Exception:
        _send_error_to_admin(traceback.format_exc())
        return []


def is_member_in_all_channels(chat_id) -> bool:
    for channel_id in get_all_channels():
        member = _bot.get_chat_member(channel_id, chat_id)
        if member.status not in ['member', 'administrator', 'creator']:
            return False
    return True


def is_member_channel(chat_id, channel_id) -> bool:
    member = _bot.get_chat_member(channel_id, chat_id)
    return member.status in ['member', 'administrator', 'creator']


def delete_channel_by_id(channel_id):
    with _conn() as conn:
        c = conn.cursor()
        try:
            c.execute("DELETE FROM channels WHERE id=?", (channel_id,))
            conn.commit()
            _bot.send_message(_settings.matin, f"Channel with id {channel_id} deleted successfully.")
        except Exception:
            conn.rollback()
            _send_error_to_admin(traceback.format_exc())


def make_delete_channel_id_keyboard():
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM channels ORDER BY id")
            rows = c.fetchall()

        keyboard = []
        for row in rows:
            # انتظار می‌رود ستون اول id و ستون دوم نام دکمه باشد؛ اگر اسکیما متفاوت است، مطابق DB خودتان تنظیم کنید
            # مثال: (id, button_name, link_type, link, channel_chat_id)
            row_id, button_name = row[0], row[1]
            keyboard.append([InlineKeyboardButton(button_name, callback_data=f"delete_row_{row_id}")])

        keyboard.append([InlineKeyboardButton("❌ خروج از منوی حذف کانال", callback_data="delete_button_1")])
        return InlineKeyboardMarkup(keyboard)
    except Exception:
        _send_error_to_admin(traceback.format_exc())
        return None


def make_channel_id_keyboard():
    try:
        keyboard = []
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT button_name, link FROM channels ORDER BY id DESC LIMIT 10")
            latest_channels = c.fetchall()

        for name, link in latest_channels:
            keyboard.append([types.InlineKeyboardButton(name, url=link)])

        keyboard.append([types.InlineKeyboardButton("✅ عضو شدم!", url=f"{_settings.bot_link}?start=invite_{_settings.matin}")])

        return types.InlineKeyboardMarkup(keyboard)
    except Exception:
        _send_error_to_admin(traceback.format_exc())
        return None

# ================== Admin List ==================
def save_new_admin(admin_id, message):
    if admin_id == "برگشت 🔙":
        _bot.send_message(message.chat.id, "به منوی ادمین برگشتید.", reply_markup=_admin_markup)
        return

    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("BEGIN TRANSACTION")
            c.execute('''CREATE TABLE IF NOT EXISTS admin_list (
                            id INTEGER PRIMARY KEY,
                            admin_id INTEGER
                        )''')
            c.execute("INSERT INTO admin_list (admin_id) VALUES (?)", (admin_id,))
            conn.commit()
        _bot.send_message(message.chat.id, "ادمین مورد نظر با موفقیت افزوده شد.", reply_markup=_admin_markup)
    except Exception:
        _send_error_to_admin(traceback.format_exc())
        _bot.send_message(message.chat.id, "Error in save_new_admin.", reply_markup=_admin_markup)


def make_delete_admin_list_keyboard():
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM admin_list ORDER BY id")
            rows = c.fetchall()

        keyboard = []
        for row in rows:
            # انتظار: (id, admin_id)
            row_id, admin_id = row[0], row[1]
            keyboard.append([InlineKeyboardButton(str(admin_id), callback_data=f"delete_row_admin_{row_id}")])

        keyboard.append([InlineKeyboardButton("❌ خروج از منوی حذف ادمین", callback_data="delete_button_1")])
        return InlineKeyboardMarkup(keyboard)
    except Exception:
        _send_error_to_admin(traceback.format_exc())
        return None


def delete_admin_by_id(admin_id):
    with _conn() as conn:
        c = conn.cursor()
        try:
            c.execute("DELETE FROM admin_list WHERE id=?", (admin_id,))
            conn.commit()
            _bot.send_message(_settings.matin, f"Admin with id {admin_id} deleted successfully.")
        except Exception:
            conn.rollback()
            _send_error_to_admin(traceback.format_exc())


def get_admin_ids():
    return get_ids_from_db("admin_list", "admin_id")


def get_ids_from_db(table_name, column_name) -> List[int]:
    try:
        with _conn() as conn:
            c = conn.cursor()
            c.execute(f"SELECT {column_name} FROM {table_name}")
            return [row[0] for row in c.fetchall()]
    except Exception as e:
        _bot.send_message(_settings.matin, f"Error in get_ids_from_db: {e}")
        return []


def check_admin_id_exists(admin_id) -> bool:
    with _conn() as conn:
        c = conn.cursor()
        c.execute('SELECT 1 FROM crush_admin_info WHERE admin_id = ?', (admin_id,))
        return c.fetchone() is not None

# ================== Block List ==================
def update_block_list(chat_id, operation: str) -> bool:
    with _conn() as conn:
        c = conn.cursor()
        if operation.lower() == "add":
            c.execute("SELECT chat_id FROM block_list WHERE chat_id = ?", (chat_id,))
            if not (c.fetchone()):
                c.execute("INSERT INTO block_list (chat_id) VALUES (?)", (chat_id,))
                conn.commit()
                return True
        elif operation.lower() == "delete":
            c.execute("SELECT chat_id FROM block_list WHERE chat_id = ?", (chat_id,))
            if c.fetchone():
                c.execute("DELETE FROM block_list WHERE chat_id = ?", (chat_id,))
                conn.commit()
                return True
        return False


# ================== Broadcast ==================
def confirm_send_all_users(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton("✔ مطمئن هستم"))
    keyboard.add(types.KeyboardButton("❌ انصراف از ارسال"))

    msg = _bot.send_message(message.chat.id, "آیا مطمئن هستید که می‌خواهید این پیام را همگانی ارسال کنید؟", reply_markup=keyboard)
    _bot.register_next_step_handler(msg, lambda response: process_confirmation_send_all_users(response, message))


def process_confirmation_send_all_users(user_response, original_message):
    if user_response.text == "✔ مطمئن هستم":
        send_all_users(original_message)
    else:
        _bot.send_message(user_response.chat.id, "❌ ارسال پیام همگانی لغو شد.", reply_markup=_admin_markup)


def send_admin_public_msg(message):
    chat_id = message.chat.id
    if message.content_type == 'text':
        _bot.send_message(chat_id, message.text, reply_markup=_main_markup)
    elif message.content_type == 'photo':
        caption = message.caption if message.caption else " "
        _bot.send_photo(chat_id, message.photo[-1].file_id, caption=caption, reply_markup=_main_markup)
    elif message.content_type == 'video':
        caption = message.caption if message.caption else " "
        _bot.send_video(chat_id, message.video.file_id, caption=caption, reply_markup=_main_markup)
    elif message.content_type == 'audio':
        caption = message.caption if message.caption else " "
        _bot.send_audio(chat_id, message.audio.file_id, caption=caption, reply_markup=_main_markup)
    elif message.content_type == 'document':
        caption = message.caption if message.caption else " "
        _bot.send_document(chat_id, message.document.file_id, caption=caption, reply_markup=_main_markup)
    elif message.content_type == 'sticker':
        _bot.send_sticker(chat_id, message.sticker.file_id, reply_markup=_main_markup)
    elif message.content_type == 'voice':
        caption = message.caption if message.caption else " "
        _bot.send_voice(chat_id, message.voice.file_id, caption=caption, reply_markup=_main_markup)
    elif message.content_type == 'animation':
        caption = message.caption if message.caption else " "
        _bot.send_animation(chat_id, message.animation.file_id, caption=caption, reply_markup=_main_markup)
    elif message.content_type == 'video_note':
        _bot.send_video_note(chat_id, message.video_note.file_id, reply_markup=_main_markup)


def send_all_users(message):
    if _check_return_2(message):
        return

    # اعلان شروع
    with _conn() as conn:
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(chat_id) FROM users WHERE chat_id NOT IN (SELECT chat_id FROM block_list)")
            total_users = c.fetchone()[0]

            groups_of_20 = total_users // 20
            remainder = total_users % 20
            send_time = groups_of_20 * 1.5
            if remainder > 0:
                send_time += 1.5
            estimated_time = round(send_time / 60, 2)

            start_message = (
                f"🚀 عملیات ارسال پیام همگانی آغاز شد!\n\n"
                f"👥 تعداد کل کاربران فعال: {total_users}\n"
                f"⏳ زمان تقریبی اتمام ارسال: {estimated_time} دقیقه."
            )

            _bot.send_message(message.chat.id, start_message, reply_markup=_admin_markup)
            _bot.send_message(_settings.matin, start_message, reply_markup=_admin_markup)

            emergency_markup = InlineKeyboardMarkup()
            emergency_markup.add(InlineKeyboardButton("⛔ توقف اضطراری", callback_data="confirm_stop_broadcast"))

            send_admin_public_msg(message)
            _bot.send_message(message.chat.id, "⚠ جهت توقف اضطراری دکمه زیر را کلیک کنید:", reply_markup=emergency_markup)

        except Exception as e:
            _bot.send_message(_settings.matin, text=f"❌ Error during calculating total users:\n{e}")
            return

    # اجرای ارسال در نخ جدا
    _stop_event.clear()

    def _worker():
        with _conn() as conn:
            c = conn.cursor()
            try:
                c.execute("SELECT chat_id FROM users WHERE chat_id NOT IN (SELECT chat_id FROM block_list)")
                all_chat_ids = c.fetchall()

                not_send = 0
                batch_20 = 0
                progress = 0

                for idx, (chat_id,) in enumerate(all_chat_ids):
                    if _stop_event.is_set():
                        _bot.send_message(message.chat.id, "⛔ عملیات ارسال پیام متوقف شد!")
                        _bot.send_message(message.chat.id, f"🔘 ارسال پیام متوقف شد! تعداد ارسال‌شده: {progress} نفر")
                        _bot.send_message(_settings.matin, "⛔ عملیات ارسال پیام متوقف شد!")
                        _bot.send_message(_settings.matin, f"🔘 ارسال پیام متوقف شد! تعداد ارسال‌شده: {progress} نفر")
                        return

                    try:
                        # فوروارد/بازارسال همان پیام ادمین به کاربر
                        if message.content_type == 'text':
                            _bot.send_message(chat_id, message.text, reply_markup=_main_markup)
                        elif message.content_type == 'photo':
                            caption = message.caption if message.caption else " "
                            _bot.send_photo(chat_id, message.photo[-1].file_id, caption=caption, reply_markup=_main_markup)
                        elif message.content_type == 'video':
                            caption = message.caption if message.caption else " "
                            _bot.send_video(chat_id, message.video.file_id, caption=caption, reply_markup=_main_markup)
                        elif message.content_type == 'audio':
                            caption = message.caption if message.caption else " "
                            _bot.send_audio(chat_id, message.audio.file_id, caption=caption, reply_markup=_main_markup)
                        elif message.content_type == 'document':
                            caption = message.caption if message.caption else " "
                            _bot.send_document(chat_id, message.document.file_id, caption=caption, reply_markup=_main_markup)
                        elif message.content_type == 'sticker':
                            _bot.send_sticker(chat_id, message.sticker.file_id, reply_markup=_main_markup)
                        elif message.content_type == 'voice':
                            caption = message.caption if message.caption else " "
                            _bot.send_voice(chat_id, message.voice.file_id, caption=caption, reply_markup=_main_markup)
                        elif message.content_type == 'animation':
                            caption = message.caption if message.caption else " "
                            _bot.send_animation(chat_id, message.animation.file_id, caption=caption, reply_markup=_main_markup)
                        elif message.content_type == 'video_note':
                            _bot.send_video_note(chat_id, message.video_note.file_id, reply_markup=_main_markup)

                        batch_20 += 1
                        progress += 1

                        if batch_20 == 20:
                            time.sleep(1.5)
                            batch_20 = 0

                        if progress % 1000 == 0:
                            progress_message = f"✅ گزارش پیشرفت: تاکنون پیام به {progress} نفر ارسال شد."
                            _bot.send_message(_settings.matin, text=progress_message)
                            if hasattr(_settings, "admin"):
                                _bot.send_message(_settings.admin, text=progress_message)

                    except Exception:
                        not_send += 1
                        update_block_list(chat_id, "add")
                        continue

                sent = total_users - not_send
                final_message = (
                    f"🎉 عملیات ارسال پیام تکمیل شد!\n\n"
                    f"✅ پیام شما به {sent} نفر از کل {total_users} کاربر ارسال شد."
                )
                _bot.send_message(message.chat.id, text=final_message, reply_markup=_admin_markup)
                _bot.send_message(_settings.matin, text=final_message, reply_markup=_admin_markup)

            except Exception as e:
                _bot.send_message(_settings.matin, text=f"❌ Error during sending messages:\n{e}")

    threading.Thread(target=_worker, daemon=True).start()
