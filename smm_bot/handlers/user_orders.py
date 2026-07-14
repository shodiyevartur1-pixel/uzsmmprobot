import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from database.db_queries import (
    get_user_orders, get_order_by_id,
    update_order_status, update_user_balance, log_transaction,
)

logger = logging.getLogger(__name__)
router = Router()

PER_PAGE = 5

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

# Bekor qilish/qayta tiklash faqat shu holatlarda ruxsat etiladi
ACTIONABLE_STATUSES = {"pending", "processing"}


class OrderActionStates(StatesGroup):
    waiting_for_info_id   = State()
    waiting_for_cancel_id = State()
    waiting_for_retry_id  = State()


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
        return text, InlineKeyboardBuilder().as_markup()

    lines = ["🆔 <b>Buyurtma idsi</b> — 📈 <b>Holat</b>"]
    for o in page_orders:
        if not isinstance(o, dict):
            o = dict(o)
        emoji = STATUS_MAP.get(o.get("status", "pending"), "⏳")
        sname = STATUS_NAME.get(o.get("status", "pending"), "Kutilmoqda")
        oid   = o.get("id", "?")
        lines.append(f"<code>{oid}</code> - {emoji} {sname}")

    text = "\n\n".join(lines)

    builder = InlineKeyboardBuilder()

    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"ord_page_{page - 1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1}/{(total - 1) // PER_PAGE + 1}",
        callback_data="ord_noop",
    ))
    if has_next:
        nav.append(InlineKeyboardButton(text="⏩", callback_data=f"ord_page_{page + 1}"))
    builder.row(*nav)

    builder.row(
        InlineKeyboardButton(text="♻️ Qayta tiklash", callback_data="ord_retry_ask"),
        InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="ord_cancel_ask"),
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Buyurtma ma'lumoti", callback_data="ord_info_ask"),
    )

    return text, builder.as_markup()


def _back_to_list_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="ord_page_0"))
    return builder.as_markup()


def _ask_id_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ord_page_0"))
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# 🔎 TAFSILOT MATNI
# ══════════════════════════════════════════════════════════════════

def _detail_text(order: dict) -> str:
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

    return (
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


async def _get_own_order(order_id: int, user_id: int):
    """Faqat shu foydalanuvchiga tegishli buyurtmani qaytaradi."""
    order = await get_order_by_id(order_id)
    if not order:
        return None
    if not isinstance(order, dict):
        order = dict(order)
    if order.get("user_id") != user_id:
        return None
    return order


# ══════════════════════════════════════════════════════════════════
# 📦 RO'YXAT / SAHIFALASH
# ══════════════════════════════════════════════════════════════════

@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders(message: Message, state: FSMContext):
    await state.clear()
    text, kb = await build_list(message.from_user.id, page=0)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("ord_page_"))
async def orders_page(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    page = int(callback.data.split("_")[2])
    text, kb = await build_list(callback.from_user.id, page=page)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "ord_noop")
async def ord_noop(callback: CallbackQuery):
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
# 🔍 BUYURTMA MA'LUMOTI
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ord_info_ask")
async def ord_info_ask(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderActionStates.waiting_for_info_id)
    await callback.message.edit_text(
        "🔍 <b>Buyurtma ma'lumoti</b>\n\n"
        "Buyurtma ID sini kiriting:",
        parse_mode="HTML",
        reply_markup=_ask_id_kb(),
    )
    await callback.answer()


@router.message(OrderActionStates.waiting_for_info_id)
async def ord_info_process(message: Message, state: FSMContext):
    try:
        oid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        return

    order = await _get_own_order(oid, message.from_user.id)
    await state.clear()

    if not order:
        await message.answer("❌ Bunday buyurtma topilmadi!", reply_markup=_back_to_list_kb())
        return

    await message.answer(_detail_text(order), parse_mode="HTML", reply_markup=_back_to_list_kb())


# ══════════════════════════════════════════════════════════════════
# 🚫 BEKOR QILISH
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ord_cancel_ask")
async def ord_cancel_ask(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderActionStates.waiting_for_cancel_id)
    await callback.message.edit_text(
        "🚫 <b>Buyurtmani bekor qilish</b>\n\n"
        "Bekor qilinadigan buyurtma ID sini kiriting:\n"
        "<i>Faqat \"Kutilmoqda\" yoki \"Bajarilmoqda\" holatidagi buyurtmalar bekor qilinadi, "
        "pul avtomatik hisobingizga qaytariladi.</i>",
        parse_mode="HTML",
        reply_markup=_ask_id_kb(),
    )
    await callback.answer()


@router.message(OrderActionStates.waiting_for_cancel_id)
async def ord_cancel_process(message: Message, state: FSMContext):
    try:
        oid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        return

    order = await _get_own_order(oid, message.from_user.id)
    await state.clear()

    if not order:
        await message.answer("❌ Bunday buyurtma topilmadi!", reply_markup=_back_to_list_kb())
        return

    if order.get("status") not in ACTIONABLE_STATUSES:
        await message.answer(
            f"❌ Bu buyurtmani bekor qilib bo'lmaydi "
            f"(holati: {STATUS_NAME.get(order.get('status'), '—')}).",
            reply_markup=_back_to_list_kb(),
        )
        return

    charge = float(order.get("charge", 0))
    await update_order_status(oid, "cancelled")
    await update_user_balance(message.from_user.id, charge, add=True)
    await log_transaction(
        message.from_user.id, charge, "refund",
        f"Foydalanuvchi bekor qildi: buyurtma #{oid}"
    )

    await message.answer(
        f"✅ <b>Buyurtma #{oid} bekor qilindi!</b>\n\n"
        f"💰 <b>{charge:,.0f} so'm</b> hisobingizga qaytarildi.",
        parse_mode="HTML",
        reply_markup=_back_to_list_kb(),
    )


# ══════════════════════════════════════════════════════════════════
# ♻️ QAYTA TIKLASH
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ord_retry_ask")
async def ord_retry_ask(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderActionStates.waiting_for_retry_id)
    await callback.message.edit_text(
        "♻️ <b>Buyurtmani qayta tiklash</b>\n\n"
        "Qayta tiklanadigan buyurtma ID sini kiriting:\n"
        "<i>Xizmat, havola va miqdor bir xil qoladi, balansingizdan "
        "yana shu summa yechiladi.</i>",
        parse_mode="HTML",
        reply_markup=_ask_id_kb(),
    )
    await callback.answer()


@router.message(OrderActionStates.waiting_for_retry_id)
async def ord_retry_process(message: Message, state: FSMContext):
    try:
        oid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        return

    order = await _get_own_order(oid, message.from_user.id)
    await state.clear()

    if not order:
        await message.answer("❌ Bunday buyurtma topilmadi!", reply_markup=_back_to_list_kb())
        return

    charge = float(order.get("charge", 0))

    # ⚠️ DIQQAT: bu yerda haqiqiy SMM buyurtma yaratish funksiyasi chaqirilishi kerak
    # (odatda utils/smm_api.py va database/db_queries.py da bo'ladi — masalan
    # create_order(...) + smm_api orqali API'ga yuborish). Menda bu funksiyalarning
    # aniq nomi/imzosi yo'q, shuning uchun hozircha faqat ogohlantirish chiqadi —
    # user_services.py yoki utils/smm_api.py ni yuborsangiz, to'liq ulab beraman.
    # await message.answer(
    #     f"⚠️ <b>Qayta tiklash hali API'ga ulanmagan.</b>\n\n"
    #     f"Buyurtma #{oid} ma'lumotlari topildi "
    #     f"({order.get('service_name', 'Noma\\'lum')}, {charge:,.0f} so'm), "
    #     f"lekin yangi buyurtmani avtomatik yaratish uchun "
    #     f"<code>user_services.py</code> yoki <code>utils/smm_api.py</code> "
    #     f"faylini yuborishingiz kerak — shundan keyin to'liq ishlaydigan qilib beraman.",
    #     parse_mode="HTML",
    #     reply_markup=_back_to_list_kb(),
    # )