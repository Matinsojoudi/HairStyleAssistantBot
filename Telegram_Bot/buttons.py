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

