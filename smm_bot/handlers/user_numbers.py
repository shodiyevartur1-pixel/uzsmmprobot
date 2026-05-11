import logging
import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import settings
from database.db_queries import get_user, update_user_balance, log_transaction
from keyboards.reply_kb import get_main_menu
from states.user_states import NumberStates

logger = logging.getLogger(__name__)
router = Router()

# Xizmatlar (qaysi app uchun raqam)
SERVICES = [
    {"code": "tg", "name": "📱 Telegram"},
    {"code": "wa", "name": "💬 WhatsApp"},
    {"code": "vk", "name": "🔵 VKontakte"},
    {"code": "go", "name": "🔴 Google"},
    {"code": "ig", "name": "🟣 Instagram"},
    {"code": "fb", "name": "🔵 Facebook"},
    {"code": "tt", "name": "⚫ TikTok"},
    {"code": "tw", "name": "🐦 Twitter"},
]

# 100 TACHA DAVLAT (MINIMAL NAARX 3000+)
ALL_COUNTRIES = [
    # Yevropa
    {"code": "ru", "name": "Rossiya", "flag": "🇷🇺", "price": 3500},
    {"code": "ua", "name": "Ukraina", "flag": "🇺🇦", "price": 3000},
    {"code": "kz", "name": "Qozog'iston", "flag": "🇰🇿", "price": 3200},
    {"code": "uz", "name": "O'zbekiston", "flag": "🇺🇿", "price": 3000},
    {"code": "gb", "name": "Britaniya", "flag": "🇬🇧", "price": 6000},
    {"code": "de", "name": "Germaniya", "flag": "🇩🇪", "price": 5500},
    {"code": "fr", "name": "Fransiya", "flag": "🇫🇷", "price": 5500},
    {"code": "it", "name": "Italiya", "flag": "🇮🇹", "price": 5000},
    {"code": "es", "name": "Ispaniya", "flag": "🇪🇸", "price": 5000},
    {"code": "pl", "name": "Polsha", "flag": "🇵🇱", "price": 4000},
    {"code": "nl", "name": "Niderlandiya", "flag": "🇳🇱", "price": 5000},
    {"code": "se", "name": "Shvetsiya", "flag": "🇸🇪", "price": 5500},
    {"code": "no", "name": "Norvegiya", "flag": "🇳🇴", "price": 6000},
    {"code": "fi", "name": "Finlandiya", "flag": "🇫🇮", "price": 5500},
    {"code": "dk", "name": "Daniya", "flag": "🇩🇰", "price": 5000},
    {"code": "cz", "name": "Chexiya", "flag": "🇨🇿", "price": 4000},
    {"code": "ro", "name": "Ruminiya", "flag": "🇷🇴", "price": 3500},
    {"code": "bg", "name": "Bolgariya", "flag": "🇧🇬", "price": 3500},
    {"code": "hu", "name": "Vengriya", "flag": "🇭🇺", "price": 4000},
    {"code": "at", "name": "Avstriya", "flag": "🇦🇹", "price": 5000},
    {"code": "be", "name": "Belgiya", "flag": "🇧🇪", "price": 5000},
    {"code": "ch", "name": "Shveytsariya", "flag": "🇨🇭", "price": 7000},
    {"code": "pt", "name": "Portugaliya", "flag": "🇵🇹", "price": 4500},
    {"code": "gr", "name": "Gretsiya", "flag": "🇬🇷", "price": 4500},
    {"code": "hr", "name": "Xorvatiya", "flag": "🇭🇷", "price": 4000},
    {"code": "sk", "name": "Slovakiya", "flag": "🇸🇰", "price": 3500},
    {"code": "si", "name": "Sloveniya", "flag": "🇸🇮", "price": 4000},
    {"code": "lt", "name": "Litva", "flag": "🇱🇹", "price": 3500},
    {"code": "lv", "name": "Latviya", "flag": "🇱🇻", "price": 3500},
    {"code": "ee", "name": "Estoniya", "flag": "🇪🇪", "price": 4000},
    {"code": "ie", "name": "Irlandiya", "flag": "🇮🇪", "price": 5500},
    {"code": "by", "name": "Belarus", "flag": "🇧🇾", "price": 3000},
    {"code": "md", "name": "Moldova", "flag": "🇲🇩", "price": 3000},
    {"code": "rs", "name": "Serbiya", "flag": "🇷🇸", "price": 3500},
    {"code": "me", "name": "Chernogoriya", "flag": "🇲🇪", "price": 4000},
    {"code": "ba", "name": "Bosniya", "flag": "🇧🇦", "price": 3500},
    {"code": "al", "name": "Albaniya", "flag": "🇦🇱", "price": 3500},
    {"code": "mk", "name": "Shimoliy Makedoniya", "flag": "🇲🇰", "price": 3000},
    {"code": "is", "name": "Islandiya", "flag": "🇮🇸", "price": 7000},
    {"code": "mt", "name": "Malta", "flag": "🇲🇹", "price": 5000},
    {"code": "cy", "name": "Kipr", "flag": "🇨🇾", "price": 4500},
    {"code": "lu", "name": "Lyuksemburg", "flag": "🇱🇺", "price": 6000},
    # Osiyo
    {"code": "us", "name": "AQSh", "flag": "🇺🇸", "price": 8000},
    {"code": "ca", "name": "Kanada", "flag": "🇨🇦", "price": 7000},
    {"code": "cn", "name": "Xitoy", "flag": "🇨🇳", "price": 3000},
    {"code": "jp", "name": "Yaponiya", "flag": "🇯🇵", "price": 7000},
    {"code": "kr", "name": "Koreya", "flag": "🇰🇷", "price": 6000},
    {"code": "in", "name": "Hindiston", "flag": "🇮🇳", "price": 3000},
    {"code": "id", "name": "Indoneziya", "flag": "🇮🇩", "price": 3000},
    {"code": "tr", "name": "Turkiya", "flag": "🇹🇷", "price": 3500},
    {"code": "sa", "name": "Saudiya Arabistoni", "flag": "🇸🇦", "price": 6000},
    {"code": "ae", "name": "BAA", "flag": "🇦🇪", "price": 7000},
    {"code": "il", "name": "Isroil", "flag": "🇮🇱", "price": 6000},
    {"code": "sg", "name": "Singapur", "flag": "🇸🇬", "price": 7000},
    {"code": "my", "name": "Malayziya", "flag": "🇲🇾", "price": 3500},
    {"code": "th", "name": "Tailand", "flag": "🇹🇭", "price": 3000},
    {"code": "vn", "name": "Vyetnam", "flag": "🇻🇳", "price": 3000},
    {"code": "ph", "name": "Filippin", "flag": "🇵🇭", "price": 3000},
    {"code": "pk", "name": "Pokiston", "flag": "🇵🇰", "price": 3000},
    {"code": "bd", "name": "Bangladesh", "flag": "🇧🇩", "price": 3000},
    {"code": "ir", "name": "Eron", "flag": "🇮🇷", "price": 4000},
    {"code": "iq", "name": "Iroq", "flag": "🇮🇶", "price": 3500},
    {"code": "jo", "name": "Iordaniya", "flag": "🇯🇴", "price": 4000},
    {"code": "kw", "name": "Kuveyt", "flag": "🇰🇼", "price": 5000},
    {"code": "qa", "name": "Qatar", "flag": "🇶🇦", "price": 7000},
    {"code": "bh", "name": "Bahrayn", "flag": "🇧🇭", "price": 5000},
    {"code": "om", "name": "Ummon", "flag": "🇴🇲", "price": 5000},
    {"code": "lk", "name": "Shri-Lanka", "flag": "🇱🇰", "price": 3000},
    {"code": "mm", "name": "Myanma", "flag": "🇲🇲", "price": 3000},
    {"code": "kg", "name": "Qirg'iziston", "flag": "🇰🇬", "price": 3000},
    {"code": "tj", "name": "Tojikiston", "flag": "🇹🇯", "price": 3000},
    {"code": "tm", "name": "Turkmaniston", "flag": "🇹🇲", "price": 3000},
    {"code": "mn", "name": "Mongoliya", "flag": "🇲🇳", "price": 3500},
    {"code": "af", "name": "Afg'oniston", "flag": "🇦🇫", "price": 3000},
    # Amerika
    {"code": "mx", "name": "Meksika", "flag": "🇲🇽", "price": 4000},
    {"code": "br", "name": "Braziliya", "flag": "🇧🇷", "price": 4000},
    {"code": "ar", "name": "Argentina", "flag": "🇦🇷", "price": 3500},
    {"code": "cl", "name": "Chili", "flag": "🇨🇱", "price": 4000},
    {"code": "co", "name": "Kolumbiya", "flag": "🇨🇴", "price": 3500},
    {"code": "pe", "name": "Peru", "flag": "🇵🇪", "price": 3500},
    {"code": "ve", "name": "Venesuela", "flag": "🇻🇪", "price": 3000},
    {"code": "cu", "name": "Kuba", "flag": "🇨🇺", "price": 4000},
    {"code": "ec", "name": "Ekvador", "flag": "🇪🇨", "price": 3500},
    {"code": "bo", "name": "Boliviya", "flag": "🇧🇴", "price": 3000},
    {"code": "uy", "name": "Urug'vay", "flag": "🇺🇾", "price": 4000},
    {"code": "py", "name": "Parag'vay", "flag": "🇵🇾", "price": 3000},
    # Afrika
    {"code": "za", "name": "JAR", "flag": "🇿🇦", "price": 4000},
    {"code": "ng", "name": "Nigeriya", "flag": "🇳🇬", "price": 3000},
    {"code": "eg", "name": "Misr", "flag": "🇪🇬", "price": 3500},
    {"code": "ke", "name": "Keniya", "flag": "🇰🇪", "price": 3000},
    {"code": "gh", "name": "Gana", "flag": "🇬🇭", "price": 3000},
    {"code": "dz", "name": "Jazoir", "flag": "🇩🇿", "price": 3500},
    {"code": "ma", "name": "Marokash", "flag": "🇲🇦", "price": 3500},
    {"code": "tn", "name": "Tunis", "flag": "🇹🇳", "price": 3500},
    {"code": "et", "name": "Efiopiya", "flag": "🇪🇹", "price": 3000},
    {"code": "tz", "name": "Tanzaniya", "flag": "🇹🇿", "price": 3000},
    # Okeaniya
    {"code": "au", "name": "Avstraliya", "flag": "🇦🇺", "price": 7000},
    {"code": "nz", "name": "Yangi Zelandiya", "flag": "🇳🇿", "price": 6500},
]

ITEMS_PER_PAGE = 10

# ── KLAVIATURALAR ──────────────────────────────────────────────────────────

def get_numbers_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 TOP 10 davlatlar", callback_data="num_top10"))
    builder.row(InlineKeyboardButton(text="💸 Arzon raqamlar", callback_data="num_cheap"))
    builder.row(InlineKeyboardButton(text="🌍 Barcha davlatlar", callback_data="num_all_0"))
    return builder.as_markup()


def get_countries_kb(countries: list):
    builder = InlineKeyboardBuilder()
    for c in countries:
        builder.row(InlineKeyboardButton(
            text=f"{c['flag']} {c['name']} — {c['price']:,} so'm",
            callback_data=f"numcountry_{c['code']}_{c['price']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_numbers"))
    return builder.as_markup()


def get_paginated_countries_kb(page: int = 0):
    builder = InlineKeyboardBuilder()
    
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_items = ALL_COUNTRIES[start:end]
    
    for c in current_items:
        builder.row(InlineKeyboardButton(
            text=f"{c['flag']} {c['name']} — {c['price']:,} so'm",
            callback_data=f"numcountry_{c['code']}_{c['price']}"
        ))
        
    total_pages = (len(ALL_COUNTRIES) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"num_all_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"num_all_{page+1}"))
        
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_numbers"))
    return builder.as_markup()


def get_services_kb(country_code: str, price: int):
    builder = InlineKeyboardBuilder()
    for svc in SERVICES:
        builder.row(InlineKeyboardButton(
            text=svc["name"],
            callback_data=f"numsvc_{country_code}_{svc['code']}_{price}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_numbers"))
    return builder.as_markup()


# ── HANDLERLAR ─────────────────────────────────────────────────────────────

@router.message(F.text == "📱 Nomer olish")
async def numbers_menu(message: Message):
    await message.answer(
        "🌍 <b>Mavjud davlatlar ro'yxati:</b>\nNarxlar 3000 so'mdan boshlanadi!",
        parse_mode="HTML",
        reply_markup=get_numbers_main_keyboard(),
    )


@router.callback_query(F.data == "back_to_numbers")
async def back_to_numbers(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🌍 <b>Mavjud davlatlar ro'yxati:</b>",
        parse_mode="HTML",
        reply_markup=get_numbers_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "num_top10")
async def show_top10(callback: CallbackQuery):
    # Eng qimmat 10 ta davlat (TOP qilish uchun)
    top_countries = sorted(ALL_COUNTRIES, key=lambda x: x['price'], reverse=True)[:10]
    await callback.message.edit_text(
        "📊 <b>TOP 10 davlatlar (Eng mashhurlari):</b>\n\nDavlatni tanlang 👇",
        parse_mode="HTML",
        reply_markup=get_countries_kb(top_countries),
    )
    await callback.answer()


@router.callback_query(F.data == "num_cheap")
async def show_cheap(callback: CallbackQuery):
    # Eng arzon 10 ta davlat
    cheap_countries = sorted(ALL_COUNTRIES, key=lambda x: x['price'])[:10]
    await callback.message.edit_text(
        "💸 <b>Arzon raqamlar:</b>\n\nDavlatni tanlang 👇",
        parse_mode="HTML",
        reply_markup=get_countries_kb(cheap_countries),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("num_all_"))
async def show_all_paginated(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        "🌍 <b>Barcha davlatlar ro'yxati:</b>",
        parse_mode="HTML",
        reply_markup=get_paginated_countries_kb(page),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("numcountry_"))
async def select_country(callback: CallbackQuery):
    parts = callback.data.split("_")
    country_code = parts[1]
    price = int(parts[2])

    country = next((c for c in ALL_COUNTRIES if c["code"] == country_code), None)
    name = country["name"] if country else country_code
    flag = country["flag"] if country else "🌍"

    await callback.message.edit_text(
        f"{flag} <b>{name}</b> uchun qaysi xizmat?\n\n"
        f"💰 Narx: <b>{price:,} so'm</b>",
        parse_mode="HTML",
        reply_markup=get_services_kb(country_code, price),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("numsvc_"))
async def select_service_for_number(callback: CallbackQuery, state: FSMContext, bot: Bot):
    parts = callback.data.split("_")
    country_code = parts[1]
    svc_code = parts[2]
    price = int(parts[3])

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Xato! Foydalanuvchi topilmadi.", show_alert=True)
        return

    if user["balance"] < price:
        await callback.answer(
            f"❌ Balans yetarli emas!\nKerak: {price:,} so'm\nBalans: {user['balance']:,.0f} so'm",
            show_alert=True
        )
        return

    country = next((c for c in ALL_COUNTRIES if c["code"] == country_code), None)
    svc = next((s for s in SERVICES if s["code"] == svc_code), None)

    # Balansdan ayirish
    await update_user_balance(callback.from_user.id, price, add=False)
    await log_transaction(callback.from_user.id, price, "order", f"Virtual raqam: {country_code}-{svc_code}")

    # Demo raqam (real API bilan almashtiriladi)
    phone = f"+{_country_code_to_phone(country_code)}XXXXXXX"

    # FSM ga narxni saqlab qo'yamiz (bekor qilsa pulni qaytarish uchun)
    await state.update_data(order_price=price, order_country=country_code)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔄 SMS kutish", callback_data=f"wait_sms_{country_code}"
    ))
    builder.row(InlineKeyboardButton(
        text="❌ Raqamni bekor qilish", callback_data="cancel_number"
    ))

    await callback.message.edit_text(
        f"✅ <b>Raqam ajratildi!</b>\n\n"
        f"🌍 Davlat: {country['flag'] if country else ''} {country['name'] if country else country_code}\n"
        f"📱 Xizmat: {svc['name'] if svc else svc_code}\n"
        f"📞 Raqam: <code>{phone}</code>\n\n"
        f"⏳ SMS kodni kuting (20 daqiqa)...\n"
        f"💰 To'landi: <b>{price:,} so'm</b>",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


def _country_code_to_phone(code: str) -> str:
    phones = {
        "ru": "7", "uz": "998", "kz": "7", "us": "1",
        "gb": "44", "ua": "380", "in": "91", "id": "62",
        "tr": "90", "de": "49", "bd": "880", "pk": "92",
        "ng": "234", "ph": "63", "br": "55", "cn": "86",
        "jp": "81", "kr": "82", "ae": "971", "sa": "966",
    }
    return phones.get(code, "0")


@router.callback_query(F.data.startswith("wait_sms_"))
async def wait_sms(callback: CallbackQuery):
    await callback.answer("⏳ SMS hali kelmadi. Biroz kuting...", show_alert=True)


# BEKOR QILISH TUGMASI (PULNI QAYTARADI)
@router.callback_query(F.data == "cancel_number")
async def cancel_number(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    price = data.get("order_price", 0)
    
    if price > 0:
        # Pulni hisobga qaytarish
        await update_user_balance(callback.from_user.id, price, add=True)
        await log_transaction(callback.from_user.id, price, "refund", "Raqam bekor qilindi")
    
    await state.clear()
    
    await callback.message.edit_text(
        f"❌ <b>Raqam bekor qilindi.</b>\n\n"
        f"💰 {price:,} so'm hisobingizga qaytarildi.\n\n"
        "Qayta urinib ko'ring.",
        parse_mode="HTML",
        reply_markup=get_numbers_main_keyboard()
    )
    await callback.answer("Pulingiz qaytarildi!", show_alert=True)


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()