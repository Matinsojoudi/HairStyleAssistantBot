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

