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


