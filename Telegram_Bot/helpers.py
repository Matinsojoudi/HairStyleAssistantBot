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
