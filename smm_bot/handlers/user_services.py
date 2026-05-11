import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import settings
from database.db_queries import (
    get_user, update_user_balance, update_total_spent,
    create_order, log_transaction
)
from keyboards.reply_kb import get_main_menu, get_cancel_button
from states.user_states import OrderStates

logger = logging.getLogger(__name__)
router = Router()

# Kategoriyalar (rasmga mos)
CATEGORIES = [
    {"id": "telegram", "name": "🔵 Telegram"},
    {"id": "instagram", "name": "🟣 Instagram"},
    {"id": "youtube", "name": "🔴 YouTube"},
    {"id": "tiktok", "name": "⚫ TikTok"},
    {"id": "uzbek_tg", "name": "🇺🇿 UZBEK TG XIZMAT..."},
    {"id": "premium_obuna", "name": "🌟 PREMIUM OBUNAC..."},
    {"id": "texnik", "name": "🛍 Tekin Xizmatlar"},
    {"id": "pubg", "name": "🎫 PUBG UC"},
    {"id": "tg_premium", "name": "💠 TG Premium"},
]


def get_categories_keyboard():
    builder = InlineKeyboardBuilder()
    # 2 ta qator qilib chiqarish
    cats = CATEGORIES[:8]
    for i in range(0, len(cats), 2):
        row = cats[i:i+2]
        builder.row(*[
            InlineKeyboardButton(text=c["name"], callback_data=f"cat_{c['id']}")
            for c in row
        ])
    # Texnik xizmatlar alohida qator
    builder.row(InlineKeyboardButton(
        text="🛍 Tekin Xizmatlar", callback_data="cat_texnik"
    ))
    builder.row(
        InlineKeyboardButton(text="🎫 PUBG UC", callback_data="cat_pubg"),
        InlineKeyboardButton(text="💠 TG Premium", callback_data="cat_tg_premium"),
    )
    builder.row(InlineKeyboardButton(
        text="📋 Xizmatlar Ro'yxati ↗", callback_data="all_services"
    ))
    builder.row(InlineKeyboardButton(
        text="🔍 Qidirish", callback_data="search_service"
    ))
    return builder.as_markup()


def get_services_kb(services: list, cat_id: str):
    builder = InlineKeyboardBuilder()
    for svc in services[:15]:
        name = svc.get("name", "")[:35]
        rate = float(svc.get("rate", 0))
        builder.row(InlineKeyboardButton(
            text=f"{name} | {rate:.1f}$",
            callback_data=f"svc_{svc['service']}_{cat_id}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cats"))
    return builder.as_markup()


import aiohttp

async def fetch_services_by_category(category_keyword: str) -> list:
    """SMM API dan xizmatlarni olish"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(settings.SMM_API_URL, data={
                "key": settings.SMM_API_KEY,
                "action": "services"
            }) as resp:
                data = await resp.json()
                if isinstance(data, list):
                    keyword = category_keyword.lower()
                    filtered = [
                        s for s in data
                        if keyword in s.get("name", "").lower() or
                           keyword in s.get("category", "").lower()
                    ]
                    return filtered[:20]
    except Exception as e:
        logger.error(f"API xato: {e}")
    return []


# Demo xizmatlar (API ishlamasa)
DEMO_SERVICES = {
    "telegram": [
        {"service": "1", "name": "Telegram Members (Real)", "rate": "0.50", "min": "100", "max": "10000"},
        {"service": "2", "name": "Telegram Views (Fast)", "rate": "0.10", "min": "500", "max": "100000"},
        {"service": "3", "name": "Telegram Reactions ❤️", "rate": "0.20", "min": "10", "max": "5000"},
        {"service": "4", "name": "Telegram Post Share", "rate": "0.30", "min": "100", "max": "10000"},
    ],
    "instagram": [
        {"service": "10", "name": "Instagram Followers (Real)", "rate": "1.20", "min": "100", "max": "50000"},
        {"service": "11", "name": "Instagram Likes (Fast)", "rate": "0.15", "min": "50", "max": "10000"},
        {"service": "12", "name": "Instagram Views", "rate": "0.08", "min": "500", "max": "100000"},
        {"service": "13", "name": "Instagram Comments", "rate": "2.00", "min": "10", "max": "1000"},
    ],
    "youtube": [
        {"service": "20", "name": "YouTube Views (HQ)", "rate": "0.80", "min": "1000", "max": "500000"},
        {"service": "21", "name": "YouTube Likes", "rate": "0.50", "min": "100", "max": "10000"},
        {"service": "22", "name": "YouTube Subscribers", "rate": "3.00", "min": "100", "max": "5000"},
    ],
    "tiktok": [
        {"service": "30", "name": "TikTok Followers", "rate": "0.90", "min": "100", "max": "50000"},
        {"service": "31", "name": "TikTok Likes", "rate": "0.20", "min": "100", "max": "50000"},
        {"service": "32", "name": "TikTok Views", "rate": "0.05", "min": "1000", "max": "500000"},
    ],
    "pubg": [
        {"service": "40", "name": "PUBG 60 UC", "rate": "1.50", "min": "1", "max": "100"},
        {"service": "41", "name": "PUBG 325 UC", "rate": "5.00", "min": "1", "max": "100"},
        {"service": "42", "name": "PUBG 660 UC", "rate": "9.00", "min": "1", "max": "100"},
    ],
    "tg_premium": [
        {"service": "50", "name": "TG Premium 1 oy", "rate": "4.00", "min": "1", "max": "100"},
        {"service": "51", "name": "TG Premium 3 oy", "rate": "10.00", "min": "1", "max": "100"},
        {"service": "52", "name": "TG Premium 6 oy", "rate": "18.00", "min": "1", "max": "100"},
    ],
    "uzbek_tg": [
        {"service": "60", "name": "O'zbek Telegram Members", "rate": "2.00", "min": "100", "max": "10000"},
        {"service": "61", "name": "O'zbek Telegram Views", "rate": "0.30", "min": "500", "max": "50000"},
    ],
    "premium_obuna": [
        {"service": "70", "name": "Premium Obuna 1 oy", "rate": "3.50", "min": "1", "max": "100"},
        {"service": "71", "name": "Premium Obuna 3 oy", "rate": "9.00", "min": "1", "max": "100"},
    ],
    "texnik": [
        {"service": "80", "name": "Akkaunt yaratish", "rate": "1.00", "min": "1", "max": "10"},
        {"service": "81", "name": "Texnik yordam", "rate": "5.00", "min": "1", "max": "1"},
    ],
}

USD_TO_SOM = 12700  # 1 USD = 12700 so'm


@router.message(F.text == "🛒 Xizmatlar")
async def services_menu(message: Message):
    await message.answer(
        "✅ <b>@uzSmmProbot</b> sizga Tezkor Arzon va Sifatli xizmatlarni taqdim etadi!\n\n"
        "📌 <b>Quyidagi tarmoqlar birini tanlang.</b>",
        parse_mode="HTML",
        reply_markup=get_categories_keyboard(),
    )


@router.callback_query(F.data == "back_to_cats")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "✅ <b>@uzSmmProbot</b> sizga Tezkor Arzon va Sifatli xizmatlarni taqdim etadi!\n\n"
        "📌 <b>Quyidagi tarmoqlar birini tanlang.</b>",
        parse_mode="HTML",
        reply_markup=get_categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def show_category_services(callback: CallbackQuery):
    cat_id = callback.data[4:]
    cat_name = next((c["name"] for c in CATEGORIES if c["id"] == cat_id), cat_id)
    services = DEMO_SERVICES.get(cat_id, [])

    if not services:
        await callback.answer("Hozircha xizmatlar yo'q!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for svc in services:
        rate_som = float(svc["rate"]) * USD_TO_SOM / 1000
        builder.row(InlineKeyboardButton(
            text=f"{svc['name']} | {rate_som:.0f} so'm/1000",
            callback_data=f"svc_{svc['service']}_{cat_id}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cats"))

    await callback.message.edit_text(
        f"{cat_name} <b>xizmatlari:</b>\n\n"
        "Kerakli xizmatni tanlang 👇",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("svc_"))
async def show_service_detail(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    svc_id = parts[1]
    cat_id = parts[2] if len(parts) > 2 else "telegram"

    # Xizmat topish
    svc = None
    for cat_services in DEMO_SERVICES.values():
        for s in cat_services:
            if s["service"] == svc_id:
                svc = s
                break

    if not svc:
        await callback.answer("Xizmat topilmadi!", show_alert=True)
        return

    rate_som = float(svc["rate"]) * USD_TO_SOM / 1000

    await state.update_data(
        service_id=svc_id,
        service_name=svc["name"],
        rate=float(svc["rate"]),
        min_qty=int(svc["min"]),
        max_qty=int(svc["max"]),
        cat_id=cat_id,
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"cat_{cat_id}"))

    await callback.message.edit_text(
        f"📋 <b>{svc['name']}</b>\n\n"
        f"💰 Narx: <b>{rate_som:.1f} so'm / 1000 ta</b>\n"
        f"📊 Min: <b>{int(svc['min']):,}</b> | Max: <b>{int(svc['max']):,}</b>\n\n"
        f"🔗 Havola yuboring (link):\n"
        f"<i>Masalan: https://t.me/username</i>",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(OrderStates.waiting_for_link)
    await callback.answer()


@router.message(OrderStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_menu())
        return

    link = message.text.strip()
    if not link.startswith("http"):
        await message.answer(
            "❌ Noto'g'ri havola! http:// yoki https:// bilan boshlang.\n\n"
            "Masalan: https://t.me/username"
        )
        return

    data = await state.get_data()
    await state.update_data(link=link)

    await message.answer(
        f"✅ Havola qabul qilindi!\n\n"
        f"📊 Miqdorni kiriting:\n"
        f"Min: <b>{data['min_qty']:,}</b> | Max: <b>{data['max_qty']:,}</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(OrderStates.waiting_for_quantity)


@router.message(OrderStates.waiting_for_quantity)
async def process_quantity(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_menu())
        return

    try:
        qty = int(message.text.replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        return

    data = await state.get_data()

    if qty < data["min_qty"] or qty > data["max_qty"]:
        await message.answer(
            f"❌ Miqdor noto'g'ri!\n"
            f"Min: <b>{data['min_qty']:,}</b> | Max: <b>{data['max_qty']:,}</b>",
            parse_mode="HTML",
        )
        return

    rate_som = data["rate"] * USD_TO_SOM / 1000
    total = rate_som * qty

    await state.update_data(quantity=qty, total=total)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_order"),
    )

    await message.answer(
        f"📋 <b>Buyurtma ma'lumotlari:</b>\n\n"
        f"🔧 Xizmat: <b>{data['service_name']}</b>\n"
        f"🔗 Havola: <code>{data['link']}</code>\n"
        f"📊 Miqdor: <b>{qty:,}</b>\n"
        f"💰 Narx: <b>{rate_som:.1f} so'm/1000</b>\n"
        f"💳 Jami: <b>{total:,.0f} so'm</b>\n\n"
        f"Tasdiqlaysizmi?",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(OrderStates.confirming_order)


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Buyurtma bekor qilindi.", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    user = await get_user(user_id)

    if not user:
        await callback.answer("Xato!", show_alert=True)
        return

    total = data["total"]

    if user["balance"] < total:
        await callback.message.edit_text(
            f"❌ <b>Balans yetarli emas!</b>\n\n"
            f"💳 Sizning balans: <b>{user['balance']:,.0f} so'm</b>\n"
            f"💰 Kerakli summa: <b>{total:,.0f} so'm</b>\n\n"
            f"💳 Hisob To'ldirish bo'limiga o'ting!",
            parse_mode="HTML",
        )
        await state.clear()
        await callback.answer()
        return

    # Balansdan ayirish
    await update_user_balance(user_id, total, add=False)
    await update_total_spent(user_id, total)

    # Buyurtma saqlash
    order_id = await create_order(
        user_id=user_id,
        service_id=data["service_id"],
        service_name=data["service_name"],
        link=data["link"],
        quantity=data["quantity"],
        charge=total,
        api_order_id=None,
    )
    await log_transaction(user_id, total, "order", f"Buyurtma #{order_id}: {data['service_name']}")

    # API ga yuborish
    api_order_id = await place_smm_order(
        data["service_id"], data["link"], data["quantity"]
    )

    updated_user = await get_user(user_id)

    await callback.message.edit_text(
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma: <b>#{order_id}</b>\n"
        f"🔧 Xizmat: <b>{data['service_name']}</b>\n"
        f"🔗 Havola: <code>{data['link']}</code>\n"
        f"📊 Miqdor: <b>{data['quantity']:,}</b>\n"
        f"💰 To'landi: <b>{total:,.0f} so'm</b>\n"
        f"💳 Qoldiq: <b>{updated_user['balance']:,.0f} so'm</b>\n\n"
        f"⏳ Bajarilish vaqti: 1-24 soat",
        parse_mode="HTML",
    )
    await state.clear()
    await callback.answer("✅ Buyurtma qabul qilindi!")


async def place_smm_order(service_id: str, link: str, quantity: int):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(settings.SMM_API_URL, data={
                "key": settings.SMM_API_KEY,
                "action": "add",
                "service": service_id,
                "link": link,
                "quantity": quantity,
            }) as resp:
                data = await resp.json()
                return data.get("order")
    except Exception as e:
        logger.error(f"SMM API order xato: {e}")
        return None


@router.callback_query(F.data == "all_services")
async def all_services_list(callback: CallbackQuery):
    text = "📋 <b>Barcha xizmatlar ro'yxati:</b>\n\n"
    for cat in CATEGORIES:
        svcs = DEMO_SERVICES.get(cat["id"], [])
        if svcs:
            text += f"{cat['name']}:\n"
            for s in svcs[:3]:
                rate_som = float(s["rate"]) * USD_TO_SOM / 1000
                text += f"  • {s['name']} — {rate_som:.0f} so'm/1000\n"
            text += "\n"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cats"))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "search_service")
async def search_service(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔍 Qidirish uchun kalit so'z kiriting:\n"
        "Masalan: <i>followers, views, likes</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(OrderStates.waiting_for_link)
    await callback.answer()