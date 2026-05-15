import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db_queries import get_user_orders, get_order_by_id

logger = logging.getLogger(__name__)
router = Router()

PER_PAGE = 8

STATUS_MAP = {
    "pending":    "⏳",
    "processing": "🔄",
    "completed":  "✅",
    "cancelled":  "❌",
    "partial":    "♻️",
}

STATUS_NAME = {
    "pending":    "Kutilmoqda",
    "processing": "Bajarilmoqda",
    "completed":  "Bajarildi",
    "cancelled":  "Bekor qilindi",
    "partial":    "Qisman bajarildi",
}


# ══════════════════════════════════════════════════════════════════
# 📋 RO'YXAT SAHIFASI
# ══════════════════════════════════════════════════════════════════

async def build_list(user_id: int, page: int):
    all_orders  = await get_user_orders(user_id, limit=1000)
    total       = len(all_orders)
    page_orders = all_orders[page * PER_PAGE: (page + 1) * PER_PAGE]
    has_prev    = page > 0
    has_next    = total > (page + 1) * PER_PAGE

    if not page_orders:
        text = (
            "📦 <b>Buyurtmalarim</b>\n\n"
            "📭 Hali hech qanday buyurtma yo'q.\n\n"
            "🛒 Xizmatlar bo'limidan buyurtma bering!"
        )
        builder = InlineKeyboardBuilder()
        return text, builder.as_markup()

    # ── Matn: faqat qisqa qator har buyurtma uchun ───────────────
    lines = []
    for o in page_orders:
        if not isinstance(o, dict):
            o = dict(o)
        emoji  = STATUS_MAP.get(o.get("status", "pending"), "⏳")
        oid    = o.get("id", "?")
        charge = float(o.get("charge", 0))
        sname  = o.get("service_name", "Noma'lum")[:22]
        lines.append(f"{emoji} <b>#{oid}</b> — {sname} | {charge:,.0f} so'm")

    start = page * PER_PAGE + 1
    end   = min((page + 1) * PER_PAGE, total)
    body  = "\n".join(lines)

    text = (
        f"📦 <b>Buyurtmalarim</b>  [{start}–{end} / {total}]\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{body}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 ID tugmasini bosib to'liq ma'lumot oling"
    )

    # ── Tugmalar: har buyurtma uchun ID tugmasi ───────────────────
    builder = InlineKeyboardBuilder()
    row = []
    for o in page_orders:
        if not isinstance(o, dict):
            o = dict(o)
        oid   = o.get("id", "?")
        emoji = STATUS_MAP.get(o.get("status", "pending"), "⏳")
        row.append(InlineKeyboardButton(
            text=f"{emoji} #{oid}",
            callback_data=f"ord_detail_{oid}",
        ))
        if len(row) == 4:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    # ── Navigatsiya ───────────────────────────────────────────────
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"ord_page_{page - 1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1} / {(total - 1) // PER_PAGE + 1}",
        callback_data="ord_noop"
    ))
    if has_next:
        nav.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"ord_page_{page + 1}"
        ))
    builder.row(*nav)
    builder.row(InlineKeyboardButton(
        text="🔄 Yangilash",
        callback_data=f"ord_refresh_{page}"
    ))

    return text, builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# 🔎 TAFSILOT SAHIFASI
# ══════════════════════════════════════════════════════════════════

async def build_detail(order_id: int, user_id: int):
    order = await get_order_by_id(order_id)
    if not order:
        return None, None

    if not isinstance(order, dict):
        order = dict(order)

    if order.get("user_id") != user_id:
        return None, None

    emoji   = STATUS_MAP.get(order.get("status", "pending"), "⏳")
    sname   = order.get("status", "pending")
    charge  = float(order.get("charge", 0))
    qty     = int(order.get("quantity", 0))
    created = str(order.get("created_at", ""))[:16]
    updated = str(order.get("updated_at", ""))[:16]
    service = order.get("service_name", "Noma'lum")
    oid     = order.get("id", "?")
    link    = order.get("link", "")
    api_id  = order.get("api_order_id") or "—"
    status  = STATUS_NAME.get(sname, "Kutilmoqda")

    text = (
        f"🔎 <b>Buyurtma #{oid}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔧 <b>Xizmat:</b> {service}\n"
        f"🔗 <b>Havola:</b>\n<code>{link}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Miqdor:</b> {qty:,} ta\n"
        f"💰 <b>To'langan:</b> {charge:,.0f} so'm\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} <b>Holat:</b> {status}\n"
        f"🏷 <b>API ID:</b> <code>{api_id}</code>\n"
        f"📅 <b>Yaratilgan:</b> {created}\n"
        f"🔁 <b>Yangilangan:</b> {updated}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔄 Holatni yangilash",
        callback_data=f"ord_check_{oid}",
    ))
    builder.row(InlineKeyboardButton(
        text="🔙 Ro'yxatga qaytish",
        callback_data="ord_page_0",
    ))

    return text, builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# 📦 HANDLERLAR
# ══════════════════════════════════════════════════════════════════

@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders(message: Message):
    text, kb = await build_list(message.from_user.id, page=0)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("ord_page_"))
async def orders_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    text, kb = await build_list(callback.from_user.id, page=page)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("ord_refresh_"))
async def orders_refresh(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    text, kb = await build_list(callback.from_user.id, page=page)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer("✅ Yangilandi!")


@router.callback_query(F.data.startswith("ord_detail_"))
async def order_detail(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    text, kb = await build_detail(order_id, callback.from_user.id)

    if not text:
        await callback.answer("❌ Buyurtma topilmadi!", show_alert=True)
        return

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("ord_check_"))
async def order_check(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    text, kb = await build_detail(order_id, callback.from_user.id)

    if not text:
        await callback.answer("❌ Buyurtma topilmadi!", show_alert=True)
        return

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer("🔄 Yangilandi!")


@router.callback_query(F.data == "ord_noop")
async def ord_noop(callback: CallbackQuery):
    await callback.answer()
    
    