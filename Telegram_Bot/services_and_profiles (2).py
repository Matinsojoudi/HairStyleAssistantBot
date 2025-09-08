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




