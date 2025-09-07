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

# ---------- آیدی پشتیبانی ----------

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

# ---------- تنظیم جایزه دعوت ----------
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