# payments.py
# -*- coding: utf-8 -*-

import sqlite3
import traceback
import random
import string
from typing import Callable, Optional, List, Any

# ===== (با init تزریق می‌شوند) =====
_bot = None
_settings = None
_types = None

_admin_markup = None
_main_markup = None
_back_markup = None


_payment_confirm_markup = None
_payment_not_confirm_markup = None


_pay_panel_chat_id: Optional[int] = None


_check_return_2: Callable[[Any], bool] = lambda _m: False
_send_error_to_admin: Callable[[str], None] = lambda msg: None

# اطلاعات کاربر
_search_user_first_name: Callable[[int], Optional[str]] = lambda _id: None
_search_user_last_name: Callable[[int], Optional[str]] = lambda _id: None
_search_user_username: Callable[[int], Optional[str]] = lambda _id: None
_search_user_phone_number: Callable[[int], Optional[str]] = lambda _id: None

# مالی
_add_money: Callable[[int, int], None] = lambda chat_id, amount: None
_give_gift_to_inviter_if_needed: Callable[[int], None] = lambda invited_chat_id: None

_admin_username_provider: Callable[[], Optional[str]] = lambda: None

# کارت‌ها (کش در حافظه)
_all_cards: List[tuple] = []  # [(owner, bank, card_number), ...]


# ========== INIT ==========
def init_payments(
    *,
    bot,
    settings,
    tg_types_module,
    admin_markup,
    main_markup,
    back_markup,
    payment_confirm_markup,
    payment_not_confirm_markup,
    pay_panel_chat_id: int,
    check_return_2: Callable[[Any], bool],
    send_error_to_admin: Callable[[str], None],
    search_user_first_name: Callable[[int], Optional[str]],
    search_user_last_name: Callable[[int], Optional[str]],
    search_user_username: Callable[[int], Optional[str]],
    search_user_phone_number: Callable[[int], Optional[str]],
    add_money: Callable[[int, int], None],
    give_gift_to_inviter_if_needed: Callable[[int], None],
    admin_username_provider: Callable[[], Optional[str]],
):
    global _bot, _settings, _types, _admin_markup, _main_markup, _back_markup
    global _payment_confirm_markup, _payment_not_confirm_markup, _pay_panel_chat_id
    global _check_return_2, _send_error_to_admin
    global _search_user_first_name, _search_user_last_name, _search_user_username, _search_user_phone_number
    global _add_money, _give_gift_to_inviter_if_needed, _admin_username_provider

    _bot = bot
    _settings = settings
    _types = tg_types_module

    _admin_markup = admin_markup
    _main_markup = main_markup
    _back_markup = back_markup

    _payment_confirm_markup = payment_confirm_markup
    _payment_not_confirm_markup = payment_not_confirm_markup
    _pay_panel_chat_id = pay_panel_chat_id

    _check_return_2 = check_return_2
    _send_error_to_admin = send_error_to_admin

    _search_user_first_name = search_user_first_name
    _search_user_last_name = search_user_last_name
    _search_user_username = search_user_username
    _search_user_phone_number = search_user_phone_number

    _add_money = add_money
    _give_gift_to_inviter_if_needed = give_gift_to_inviter_if_needed
    _admin_username_provider = admin_username_provider

    _create_transactions_table()
    _init_card_table()
    _load_cards()

# ========== DB UTILS ==========
def _conn():
    return sqlite3.connect(_settings.database)


# ========== TRANSACTIONS ==========
def _create_transactions_table():
    with _conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            amount INTEGER,
            tracking_code TEXT UNIQUE,
            status TEXT DEFAULT 'pending'
        )
        """)

def _save_money_info(chat_id: int, amount: int) -> str:
    tracking_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    with _conn() as conn:
        conn.execute("INSERT INTO transactions (chat_id, amount, tracking_code) VALUES (?, ?, ?)",
                     (chat_id, amount, tracking_code))
    return tracking_code

def update_transaction_status(tracking_code: str, status: str):
    with _conn() as conn:
        conn.execute("UPDATE transactions SET status = ? WHERE tracking_code = ?", (status, tracking_code))

def get_chat_id_by_tracking_code(tracking_code: str) -> Optional[int]:
    with _conn() as conn:
        cur = conn.execute("SELECT chat_id FROM transactions WHERE tracking_code = ?", (tracking_code,))
        row = cur.fetchone()
        return int(row[0]) if row else None

def get_amount_by_tracking_code(tracking_code: str) -> Optional[int]:
    with _conn() as conn:
        cur = conn.execute("SELECT amount FROM transactions WHERE tracking_code = ?", (tracking_code,))
        row = cur.fetchone()
        return int(row[0]) if row else None





