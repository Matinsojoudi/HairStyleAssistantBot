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