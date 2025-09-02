from telebot.types import ReplyKeyboardMarkup
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from env import settings

back_markup = ReplyKeyboardMarkup(resize_keyboard=True)
back_markup.row("برگشت 🔙")

admin_markup = ReplyKeyboardMarkup(resize_keyboard=True)
admin_markup.row("🟢 بروزرسانی اطلاعات سایت 🟢")
admin_markup.row("📊 گزارش رزروها", "⚙️ افزایش اعتبار")
admin_markup.row("⚙️ تنظیم خدمات", "👥 افزودن پرسنل")
admin_markup.row("✏️ ویرایش خدمات", "👨‍💼 ویرایش پرسنل")
admin_markup.row("🚫 حذف لینک آپلودر", "📤 آپلود فایل جدید")
admin_markup.row("تنظیم کانال اطلاع رسانی", "👤 تنظیم آیدی پشتیبانی")
admin_markup.row("📋 مشاهده شماره کارت‌ها", "➕ ثبت شماره کارت جدید", "❌ حذف شماره کارت")
admin_markup.row("🖇 ایجاد دکمه شیشه ای", "⚙️ تنظیم مبلغ پاداش دعوت")
admin_markup.row("🟢 خاموش/روشن احراز هویت", "🔴 خاموش/روشن ربات")
admin_markup.row("❌ حذف کانال", "➕ افزودن کانال")
admin_markup.row("❌ حذف ادمین", "➕ افزودن ادمین")
admin_markup.row("📢 پیام همگانی", "📊 آمار ربات")
admin_markup.row("➰ منوی کاربر عادی")

main_markup = ReplyKeyboardMarkup(resize_keyboard=True)
main_markup.row("🗓️ رزرو وقت جدید", "📖 مشاهده رزروهای من")
main_markup.row("💳 افزایش موجودی", "👤 پروفایل من")
main_markup.row("♻️ تعرفه ها", "🎁 دعوت دوستان", "🎊 نفرات برتر")
main_markup.row("☎️ پشتیبانی")

back_markup = ReplyKeyboardMarkup(resize_keyboard=True)
back_markup.row("برگشت 🔙")


confrim_my_accunt = [[InlineKeyboardButton("تایید هویت", callback_data="verify_request")]]
keyboard_confrim_my_accunt = InlineKeyboardMarkup(confrim_my_accunt)

payment_button = [
    [InlineKeyboardButton("💎 10,000", callback_data="add_10000"),InlineKeyboardButton("💎 20,000", callback_data="add_20000")],
    [InlineKeyboardButton("💎 30,000", callback_data="add_30000"),InlineKeyboardButton("💎 50,000", callback_data="add_50000")],
    [InlineKeyboardButton("💎 100,000", callback_data="add_100000"),InlineKeyboardButton("💎 200,000", callback_data="add_200000")],
    [InlineKeyboardButton("💎 300,000", callback_data="add_300000"),InlineKeyboardButton("💎 500,000", callback_data="add_500000")],

    [InlineKeyboardButton("💳 مبلغ دلخواه", callback_data="add_ask")]
]
keyboard_payment_button = InlineKeyboardMarkup(payment_button)


payment_confirm_markup = InlineKeyboardMarkup()
payment_confirm_markup.add(InlineKeyboardButton("✅ پرداخت تایید شد.", url=settings.bot_link))

payment_not_confirm_markup = InlineKeyboardMarkup()
payment_not_confirm_markup.add(InlineKeyboardButton("❌ عدم تایید پرداخت.", url=settings.bot_link))


# کیبورد ادامه یا تمام
continue_markup = ReplyKeyboardMarkup(resize_keyboard=True)
continue_markup.row("✅ تمام شد", "➕ ادامه")
continue_markup.add("برگشت 🔙")

# کیبورد تایید
confirm_markup = ReplyKeyboardMarkup(resize_keyboard=True)
confirm_markup.row("✅ تایید", "❌ لغو")
