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


