from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🛒 Xizmatlar"),
        KeyboardButton(text="📱 Nomer olish"),
    )
    builder.row(
        KeyboardButton(text="👤 Hisobim"),
        KeyboardButton(text="📦 Buyurtmalarim"),
    )
    builder.row(
        KeyboardButton(text="💰 Pul ishlash"),
        KeyboardButton(text="💳 Hisob To'ldirish"),
    )
    builder.row(
        # KeyboardButton(text="🤝 Hamkorlik"),
        KeyboardButton(text="🆘 Yordam"),
    )
    return builder.as_markup(resize_keyboard=True)


def get_admin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Statistika"),
        KeyboardButton(text="👥 Foydalanuvchilar"),
    )
    builder.row(
        KeyboardButton(text="📢 Xabar yuborish"),
        KeyboardButton(text="🎁 Promo Kodlar"),
    )
    builder.row(
        KeyboardButton(text="⚙️ Sozlamalar"),
        KeyboardButton(text="📦 Buyurtmalar"),
    )
    builder.row(
        KeyboardButton(text="🎫 Yordam Chatlari"),
        KeyboardButton(text="🏠 Asosiy Menu"),
    )
    return builder.as_markup(resize_keyboard=True)


def get_back_button(text: str = "🔙 Orqaga") -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=text))
    return builder.as_markup(resize_keyboard=True)


def get_cancel_button() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)