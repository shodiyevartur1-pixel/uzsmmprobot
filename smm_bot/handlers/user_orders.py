import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db_queries import get_user_orders

logger = logging.getLogger(__name__)
router = Router()

def format_order(order) -> str:
    """Bitta buyurtmani chiroyli qilib formatlaydi"""
    
    # SQLite Row ni oddiy dict (lug'at) ga aylantiramiz ki, .get() ishlashi uchun
    if not isinstance(order, dict):
        order = dict(order)

    status_emoji = {
        "pending": "⏳",
        "processing": "🔄",
        "completed": "✅",
        "cancelled": "❌",
        "partial": "♻️"
    }.get(order.get("status", "pending"), "⏳")

    # Narxni to'g'ri formatlash (51 -> 51,000 ga o'zgartiradi)
    price = order.get("price", 0)
    if isinstance(price, (int, float)):
        price_str = f"{price:,.0f} so'm"
    else:
        price_str = str(price)

    return (
        f"{status_emoji} <b>#{order.get('id', '?')}</b> — {order.get('service_name', 'Noma\'lum')}\n"
        f"💰 {price_str} | 📊 {order.get('quantity', 0)} ta\n"
        f"📅 {order.get('created_at', 'Sana yo\'q')}"
    )

@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders(message: Message):
    orders = await get_user_orders(message.from_user.id, limit=10)
    
    if not orders:
        await message.answer(
            "📦 <b>Sizda hali buyurtmalar yo'q!</b>\n\n"
            "Asosiy menyu orqali xizmatlarni tanlang.",
            parse_mode="HTML"
        )
        return

    # Barcha buyurtmalarni bitta chiroyli matnga aylantiramiz
    formatted_orders = "\n\n".join([format_order(order) for order in orders])
    
    text = (
        f"📦 <b>So'nggi buyurtmalaringiz:</b>\n\n"
        f"{formatted_orders}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"Jami: <b>{len(orders)}</b> ta buyurtma"
    )

    builder = InlineKeyboardBuilder()
    # Agar 10 tadan ko'p bo'lsa, keyingi sahifa tugmasi chiqadi
    if len(orders) == 10:
        builder.row(InlineKeyboardButton(text="➡️ Keyingi 10 ta", callback_data="orders_page_1"))
    builder.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_orders"))

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("orders_page_"))
async def orders_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    limit = 10
    offset = page * limit
    
    orders = await get_user_orders(callback.from_user.id, limit=limit, offset=offset)
    
    if not orders:
        await callback.answer("Boshqa buyurtmalar yo'q!", show_alert=True)
        return

    formatted_orders = "\n\n".join([format_order(order) for order in orders])
    
    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.row(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"orders_page_{page-1}"))
    if len(orders) == limit:
        builder.row(InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"orders_page_{page+1}"))
    builder.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"refresh_orders"))

    text = (
        f"📦 <b>Buyurtmalar (Sahifa {page+1}):</b>\n\n"
        f"{formatted_orders}"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "refresh_orders")
async def refresh_orders(callback: CallbackQuery):
    # Shu zahotiyoq holatni qayta yuklaydi
    orders = await get_user_orders(callback.from_user.id, limit=10)
    formatted_orders = "\n\n".join([format_order(order) for order in orders])
    
    text = (
        f"📦 <b>So'nggi buyurtmalaringiz:</b>\n\n"
        f"{formatted_orders}\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"Jami: <b>{len(orders)}</b> ta buyurtma"
    )

    builder = InlineKeyboardBuilder()
    if len(orders) == 10:
        builder.row(InlineKeyboardButton(text="➡️ Keyingi 10 ta", callback_data="orders_page_1"))
    builder.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_orders"))

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer("✅ Yangilandi!")