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


# ========== PAYMENT FLOW ==========
def handle_amount_selection(call):
    chat_id = call.from_user.id
    data = (call.data or "").split("_")[1] if "_" in (call.data or "") else ""

    if data == "ask":
        msg = _bot.send_message(chat_id, "لطفاً مبلغ دلخواه را (به تومان) ارسال کنید:", reply_markup=_back_markup)
        _bot.register_next_step_handler(msg, handle_custom_amount)
        return

    try:
        amount = int(data)
        send_payment_instruction(chat_id, amount)
    except Exception:
        _bot.send_message(chat_id, "❌ مقدار انتخابی نامعتبر است.", reply_markup=_main_markup)

def handle_custom_amount(message):
    chat_id = message.chat.id
    if _check_return_2(message):
        return
    try:
        amount = int((message.text or "").strip().replace(",", ""))
        if amount < 10000:
            _bot.send_message(chat_id, "❌ حداقل مبلغ باید ۱۰ هزار تومان باشد.", reply_markup=_back_markup)
            msg = _bot.send_message(chat_id, "مبلغ جدید را وارد کنید:", reply_markup=_back_markup)
            _bot.register_next_step_handler(msg, handle_custom_amount)
            return
        send_payment_instruction(chat_id, amount)
    except Exception:
        _bot.send_message(chat_id, "❌ لطفاً فقط عدد وارد کنید.", reply_markup=_back_markup)
        _bot.register_next_step_handler(message, handle_custom_amount)

def send_payment_instruction(chat_id: int, amount: int):
    msg = _bot.send_message(
        chat_id,
        f"""💳 شما در حال افزایش اعتبار به مبلغ <b>{amount:,}</b> تومان هستید.

لطفاً مبلغ را به یکی از شماره کارت‌های زیر واریز کنید:

{format_card_list()}

سپس عکس رسید را در همین قسمت ارسال نمایید.""",
        parse_mode="HTML",
        reply_markup=_back_markup
    )
    _bot.register_next_step_handler(msg, lambda m: send_receipt_to_admin(m, amount))

def send_receipt_to_admin(message, amount: int):
    chat_id = message.chat.id

    if _check_return_2(message):
        return

    if not getattr(message, "photo", None):
        _bot.send_message(chat_id, "❌ لطفاً فقط عکس فیش ارسال کنید.", reply_markup=_back_markup)
        _bot.register_next_step_handler(message, lambda m: send_receipt_to_admin(m, amount))
        return

    photo_id = message.photo[-1].file_id
    tracking_code = _save_money_info(chat_id, amount)

    markup = _types.InlineKeyboardMarkup()
    markup.add(
        _types.InlineKeyboardButton("✅ تایید", callback_data=f"confirm_{tracking_code}"),
        _types.InlineKeyboardButton("❌ رد", callback_data=f"notconfirm_{tracking_code}")
    )

    first = _search_user_first_name(chat_id) or ""
    last  = _search_user_last_name(chat_id) or ""
    full_name = (first + " " + last).strip() or "نامشخص"
    username = _search_user_username(chat_id) or "-"
    phone    = _search_user_phone_number(chat_id) or "نامشخص"

    caption = f"""💲 <b>پرداخت جدید</b>

💎 مبلغ: {amount:,} تومان
🏷 کد پیگیری: {tracking_code}
👤 کاربر: {full_name}
👤 آیدی: @{username}
📞 شماره: {phone}
🧾 چت آیدی: <code>{chat_id}</code>"""

    _bot.send_photo(_pay_panel_chat_id, photo=photo_id, caption=caption, reply_markup=markup, parse_mode="HTML")
    _bot.send_message(chat_id, f"✅ رسید شما ارسال شد. منتظر تایید ادمین بمانید.\nکد پیگیری: <code>{tracking_code}</code>",
                      parse_mode="HTML", reply_markup=_main_markup)

def handle_confirm_payment(call):
    tracking_code = (call.data or "").split("_")[1] if "_" in (call.data or "") else ""
    chat_id = get_chat_id_by_tracking_code(tracking_code)
    amount  = get_amount_by_tracking_code(tracking_code)

    if chat_id and amount:
        _add_money(chat_id, int(amount))
        update_transaction_status(tracking_code, "confirmed")
        _bot.send_message(chat_id, f"✅ پرداخت شما تایید شد و <b>{int(amount):,}</b> تومان به حسابتان افزوده شد.",
                          parse_mode="HTML", reply_markup=_main_markup)
        # هدیه برای دعوت‌کننده (در صورت نیاز)
        _give_gift_to_inviter_if_needed(chat_id)
        # به‌روزرسانی مارکاپ پیام ادمین
        _bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=_payment_confirm_markup)
    else:
        _bot.answer_callback_query(call.id, "❌ خطا در دریافت اطلاعات تراکنش.")

def handle_reject_payment(call):
    tracking_code = (call.data or "").split("_")[1] if "_" in (call.data or "") else ""
    chat_id = get_chat_id_by_tracking_code(tracking_code)
    update_transaction_status(tracking_code, "rejected")
    _bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=_payment_not_confirm_markup)

    if chat_id:
        admin_un = _admin_username_provider() or "ادمین"
        _bot.send_message(chat_id,
            f"❌ پرداخت شما رد شد.\nکد پیگیری: <code>{tracking_code}</code>\nبرای پشتیبانی با {admin_un} در تماس باشید.",
            parse_mode="HTML", reply_markup=_main_markup)
        _bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)







