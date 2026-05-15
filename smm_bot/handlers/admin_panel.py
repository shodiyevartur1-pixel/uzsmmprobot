import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters import Command

from config import settings
from database.db_queries import (
    get_user, get_all_users, get_user_count, get_total_stats,
    ban_user, update_user_balance, set_user_balance, log_transaction,
    create_promo, get_all_promos, delete_promo,
    get_all_orders, get_order_by_id, update_order_status,
    get_all_open_tickets, get_setting, set_setting
)
from keyboards.reply_kb import get_main_menu, get_admin_menu, get_cancel_button
from states.user_states import AdminStates

logger = logging.getLogger(__name__)
router = Router()

STATUS_EMOJI = {
    "pending":    "⏳",
    "processing": "🔄",
    "completed":  "✅",
    "cancelled":  "❌",
    "partial":    "⚠️",
}


# ══════════════════════════════════════════════════════════════════════════════
# 🔐 ADMIN TEKSHIRUVI
# ══════════════════════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


# ══════════════════════════════════════════════════════════════════════════════
# /admin KOMANDASI
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def admin_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q!")
        return
    await message.answer(
        "👑 <b>Admin Panel</b>\n\n"
        "Kerakli bo'limni tanlang 👇",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# ⚡ TEZKOR BALANS (quick command)
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text.regexp(r"^/addbalance_(\d+)_(\d+)$"))
async def quick_add_balance(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split("_")
    user_id = int(parts[1])
    amount  = float(parts[2])

    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return

    await update_user_balance(user_id, amount, add=True)
    await log_transaction(user_id, amount, "deposit", "Admin tomonidan qo'shildi")

    new_balance = (user["balance"] or 0) + amount
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>Hisobingiz to'ldirildi!</b>\n\n"
            f"💰 +{amount:,.0f} so'm qo'shildi\n"
            f"💳 Joriy balans: <b>{new_balance:,.0f} so'm</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    name = user.get("full_name") or str(user_id)
    await message.answer(f"✅ {name} ga {amount:,.0f} so'm qo'shildi!")


# ══════════════════════════════════════════════════════════════════════════════
# 📊 STATISTIKA
# ══════════════════════════════════════════════════════════════════════════════

def _stats_text(users: dict, stats: dict, orders: list) -> str:
    completed = sum(1 for o in orders if o["status"] == "completed")
    pending   = sum(1 for o in orders if o["status"] == "pending")
    return (
        "📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"   • Jami: <b>{users['total']:,}</b>\n"
        f"   • Faol (7 kun): <b>{users['active']:,}</b>\n"
        f"   • Banned: <b>{users['banned']:,}</b>\n\n"
        f"💰 <b>Moliyaviy:</b>\n"
        f"   • Umumiy balans: <b>{stats['total_balance']:,.0f} so'm</b>\n"
        f"   • Jami sarflangan: <b>{stats['total_spent']:,.0f} so'm</b>\n\n"
        f"📦 <b>Buyurtmalar:</b>\n"
        f"   • Jami: <b>{stats['total_orders']:,}</b>\n"
        f"   • Bajarilgan: <b>{completed:,}</b>\n"
        f"   • Kutilmoqda: <b>{pending:,}</b>"
    )


def _stats_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_stats"))
    return builder.as_markup()


@router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    users  = await get_user_count()
    stats  = await get_total_stats()
    orders = await get_all_orders(limit=1000)
    await message.answer(
        _stats_text(users, stats, orders),
        parse_mode="HTML",
        reply_markup=_stats_keyboard(),
    )


@router.callback_query(F.data == "refresh_stats")
async def refresh_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    users  = await get_user_count()
    stats  = await get_total_stats()
    orders = await get_all_orders(limit=1000)
    await callback.message.edit_text(
        _stats_text(users, stats, orders),
        parse_mode="HTML",
        reply_markup=_stats_keyboard(),
    )
    await callback.answer("✅ Yangilandi!")


# ══════════════════════════════════════════════════════════════════════════════
# 👥 FOYDALANUVCHILAR
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "👥 <b>Foydalanuvchi boshqaruvi</b>\n\n"
        "Foydalanuvchi ID sini kiriting:",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(AdminStates.waiting_for_user_id)


@router.message(AdminStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        return

    user = await get_user(uid)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return

    from database.db_queries import get_referral_count, get_user_orders
    refs   = await get_referral_count(uid)
    orders = await get_user_orders(uid, limit=1000)

    status   = "🚫 BANNED" if user.get("is_banned") else "✅ Faol"
    joined   = (user.get("joined_at")    or "")[:10] or "—"
    last_act = (user.get("last_active")  or "")[:10] or "—"

    username = user.get('username') or 'yoq'

    await message.answer(
    f"👤 <b>Foydalanuvchi ma'lumoti</b>\n\n"
    f"🆔 ID: <code>{user['user_id']}</code>\n"
    f"👤 Ism: {user.get('full_name') or '—'}\n"
    f"📛 Username: @{username}\n"
    f"💰 Balans: <b>{user.get('balance', 0):,.0f} so'm</b>\n"
    f"💸 Sarflagan: <b>{user.get('total_spent', 0):,.0f} so'm</b>\n"
    f"📦 Buyurtmalar: <b>{len(orders)}</b>\n"
    f"👥 Referallar: <b>{refs}</b>\n"
    f"📅 Ro'yxatdan: {joined}\n"
    f"🕐 So'nggi faollik: {last_act}\n"
    f"⚡ Holat: {status}",
    parse_mode="HTML",
    reply_markup=_user_actions_kb(uid, bool(user.get("is_banned"))),
)
    await state.clear()


def _user_actions_kb(user_id: int, is_banned: bool):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Balans qo'sh", callback_data=f"adm_addbal_{user_id}"),
        InlineKeyboardButton(text="➖ Balans ayr",   callback_data=f"adm_subbal_{user_id}"),
    )
    if is_banned:
        builder.row(InlineKeyboardButton(
            text="✅ Banldan chiqar", callback_data=f"adm_unban_{user_id}"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="🚫 Banlash", callback_data=f"adm_ban_{user_id}"
        ))
    builder.row(InlineKeyboardButton(
        text="📨 Xabar yuborish", callback_data=f"adm_msg_{user_id}"
    ))
    return builder.as_markup()


@router.callback_query(F.data.startswith("adm_ban_"))
async def admin_ban(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[2])
    await ban_user(uid, True)
    try:
        await bot.send_message(uid, "🚫 Siz botdan bloklandingiz.")
    except Exception:
        pass
    await callback.answer("✅ Foydalanuvchi banlandi!", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=_user_actions_kb(uid, True))


@router.callback_query(F.data.startswith("adm_unban_"))
async def admin_unban(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[2])
    await ban_user(uid, False)
    try:
        await bot.send_message(uid, "✅ Sizning blokirovkangiz olib tashlandi!")
    except Exception:
        pass
    await callback.answer("✅ Ban olib tashlandi!", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=_user_actions_kb(uid, False))


@router.callback_query(F.data.startswith("adm_addbal_"))
async def admin_add_balance_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[2])
    await state.update_data(target_user_id=uid, balance_action="add")
    await callback.message.answer(
        f"➕ <b>Balans qo'shish</b>\n"
        f"Foydalanuvchi ID: <code>{uid}</code>\n\n"
        f"Summani kiriting (so'mda):",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(AdminStates.waiting_for_balance_amount)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_subbal_"))
async def admin_sub_balance_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[2])
    await state.update_data(target_user_id=uid, balance_action="sub")
    await callback.message.answer(
        f"➖ <b>Balans ayirish</b>\n"
        f"Foydalanuvchi ID: <code>{uid}</code>\n\n"
        f"Summani kiriting (so'mda):",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(AdminStates.waiting_for_balance_amount)
    await callback.answer()


@router.message(AdminStates.waiting_for_balance_amount)
async def process_balance_amount(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return
    try:
        amount = float(message.text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Musbat raqam kiriting!")
        return

    data   = await state.get_data()
    uid    = data["target_user_id"]
    action = data["balance_action"]
    user   = await get_user(uid)

    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        await state.clear()
        return

    balance = user.get("balance", 0) or 0

    if action == "add":
        await update_user_balance(uid, amount, add=True)
        await log_transaction(uid, amount, "deposit", f"Admin qo'shdi: {message.from_user.id}")
        desc   = f"➕ {amount:,.0f} so'm qo'shildi"
        notify = f"✅ Hisobingizga <b>{amount:,.0f} so'm</b> qo'shildi!"
        new_bal = balance + amount
    else:
        if balance < amount:
            await message.answer(
                f"❌ Foydalanuvchi balansi yetarli emas!\n"
                f"Balans: <b>{balance:,.0f} so'm</b>",
                parse_mode="HTML",
            )
            return
        await update_user_balance(uid, amount, add=False)
        await log_transaction(uid, amount, "deduct", f"Admin ayirdi: {message.from_user.id}")
        desc    = f"➖ {amount:,.0f} so'm ayirildi"
        notify  = f"⚠️ Hisobingizdan <b>{amount:,.0f} so'm</b> ayirildi."
        new_bal = balance - amount

    try:
        await bot.send_message(uid, notify, parse_mode="HTML")
    except Exception:
        pass

    name = user.get("full_name") or str(uid)
    await message.answer(
        f"✅ <b>Bajarildi!</b>\n\n"
        f"👤 {name} (<code>{uid}</code>)\n"
        f"{desc}\n"
        f"💳 Yangi balans: <b>{new_bal:,.0f} so'm</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )
    await state.clear()


@router.callback_query(F.data.startswith("adm_msg_"))
async def admin_msg_user_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    uid = int(callback.data.split("_")[2])
    await state.update_data(target_user_id=uid)
    await callback.message.answer(
        f"📨 ID <code>{uid}</code> ga xabar yozing:",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(AdminStates.waiting_for_user_message)
    await callback.answer()


@router.message(AdminStates.waiting_for_user_message)
async def send_msg_to_user(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return
    data = await state.get_data()
    uid  = data["target_user_id"]
    try:
        await bot.send_message(
            uid,
            f"📨 <b>Admin xabari:</b>\n\n{message.text}",
            parse_mode="HTML",
        )
        await message.answer("✅ Xabar yuborildi!", reply_markup=get_admin_menu())
    except Exception:
        await message.answer("❌ Xabar yuborib bo'lmadi!", reply_markup=get_admin_menu())
    await state.clear()


# ══════════════════════════════════════════════════════════════════════════════
# 📢 BROADCAST
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📢 <b>Broadcast xabar</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing.\n"
        "📸 Rasm, 🎥 Video yoki matn yuborishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(AdminStates.waiting_for_broadcast_message)


@router.message(AdminStates.waiting_for_broadcast_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return

    try:
        users = await get_all_users()
    except Exception as e:
        logger.error(f"get_all_users xato: {e}")
        await message.answer(f"❌ Foydalanuvchilarni olishda xato:\n<code>{e}</code>", parse_mode="HTML")
        await state.clear()
        return

    total = len(users)
    if total == 0:
        await message.answer("❌ Foydalanuvchilar topilmadi!")
        await state.clear()
        return

    sent   = 0
    failed = 0

    progress_msg = await message.answer(f"⏳ Yuborilmoqda...\n0 / {total}")

    for i, user in enumerate(users):
        uid = user["user_id"] if isinstance(user, dict) else user[0]
        try:
            if message.photo:
                await bot.send_photo(
                    uid,
                    message.photo[-1].file_id,
                    caption=message.caption or "",
                    parse_mode="HTML",
                )
            elif message.video:
                await bot.send_video(
                    uid,
                    message.video.file_id,
                    caption=message.caption or "",
                    parse_mode="HTML",
                )
            elif message.document:
                await bot.send_document(
                    uid,
                    message.document.file_id,
                    caption=message.caption or "",
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(uid, message.text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

        if (i + 1) % 20 == 0:
            try:
                await progress_msg.edit_text(f"⏳ Yuborilmoqda...\n{i + 1} / {total}")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await progress_msg.edit_text(
        f"✅ <b>Broadcast yakunlandi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent}</b>\n"
        f"❌ Xato: <b>{failed}</b>\n"
        f"👥 Jami: <b>{total}</b>",
        parse_mode="HTML",
    )
    await message.answer("✅ Broadcast tugadi!", reply_markup=get_admin_menu())
    await state.clear()


# ══════════════════════════════════════════════════════════════════════════════
# 🎁 PROMO KODLAR
# ══════════════════════════════════════════════════════════════════════════════

def _promo_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Yangi promo kod",  callback_data="create_promo"))
    builder.row(InlineKeyboardButton(text="🗑 Promo o'chirish",  callback_data="delete_promo_list"))
    return builder.as_markup()


@router.message(F.text == "🎁 Promo Kodlar")
async def promo_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    promos = await get_all_promos()
    text = "🎁 <b>Promo Kodlar</b>\n\n"
    if promos:
        for p in promos:
            status = "✅" if p["is_active"] else "❌"
            text += (
                f"{status} <code>{p['code']}</code>\n"
                f"   💰 {p['amount']:,.0f} so'm | "
                f"👥 {p['used_count']}/{p['max_uses']} marta\n\n"
            )
    else:
        text += "Hozircha promo kodlar yo'q.\n"
    await message.answer(text, parse_mode="HTML", reply_markup=_promo_keyboard())


@router.callback_query(F.data == "create_promo")
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "🎁 <b>Yangi promo kod yaratish</b>\n\n"
        "Promo kod nomini kiriting:\n"
        "<i>Masalan: BONUS2025</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(AdminStates.waiting_for_promo_code)
    await callback.answer()


@router.message(AdminStates.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return
    code = message.text.strip().upper()
    if len(code) < 3:
        await message.answer("❌ Kod kamida 3 ta harf bo'lishi kerak!")
        return
    await state.update_data(promo_code=code)
    await message.answer(
        f"✅ Kod: <code>{code}</code>\n\n💰 Summani kiriting (so'mda):",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_promo_amount)


@router.message(AdminStates.waiting_for_promo_amount)
async def process_promo_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return
    try:
        amount = float(message.text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Musbat raqam kiriting!")
        return
    await state.update_data(promo_amount=amount)
    await message.answer(
        f"💰 Summa: <b>{amount:,.0f} so'm</b>\n\n👥 Necha marta ishlatilsin? (1–10000):",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_promo_uses)


@router.message(AdminStates.waiting_for_promo_uses)
async def process_promo_uses(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return
    try:
        uses = int(message.text.strip())
        if uses < 1 or uses > 10000:
            raise ValueError
    except ValueError:
        await message.answer("❌ 1 dan 10000 gacha raqam kiriting!")
        return

    data   = await state.get_data()
    code   = data["promo_code"]
    amount = data["promo_amount"]

    success = await create_promo(code, amount, uses)
    if success:
        await message.answer(
            f"✅ <b>Promo kod yaratildi!</b>\n\n"
            f"🎟 Kod: <code>{code}</code>\n"
            f"💰 Summa: <b>{amount:,.0f} so'm</b>\n"
            f"👥 Foydalanish: <b>{uses} marta</b>",
            parse_mode="HTML",
            reply_markup=get_admin_menu(),
        )
    else:
        await message.answer(
            "❌ Bu kod allaqachon mavjud! Boshqa nom tanlang.",
            reply_markup=get_admin_menu(),
        )
    await state.clear()


@router.callback_query(F.data == "delete_promo_list")
async def delete_promo_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    promos = await get_all_promos()
    if not promos:
        await callback.answer("Promo kodlar yo'q!", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for p in promos:
        builder.row(InlineKeyboardButton(
            text=f"🗑 {p['code']} ({p['amount']:,.0f} so'm)",
            callback_data=f"del_promo_{p['id']}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_promo"))
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("del_promo_"))
async def confirm_delete_promo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    promo_id = int(callback.data.split("_")[2])
    await delete_promo(promo_id)
    await callback.answer("✅ Promo kod o'chirildi!", show_alert=True)

    promos = await get_all_promos()
    text = "🎁 <b>Promo Kodlar</b>\n\n"
    if promos:
        for p in promos:
            status = "✅" if p["is_active"] else "❌"
            text += f"{status} <code>{p['code']}</code> — {p['amount']:,.0f} so'm\n"
    else:
        text += "Hozircha promo kodlar yo'q."
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_promo_keyboard())


@router.callback_query(F.data == "back_promo")
async def back_promo(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=_promo_keyboard())
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════════
# 📦 BUYURTMALAR
# ══════════════════════════════════════════════════════════════════════════════

def _orders_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏳ Kutilmoqda",  callback_data="orders_filter_pending"),
        InlineKeyboardButton(text="🔄 Jarayonda",   callback_data="orders_filter_processing"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Bajarilgan",  callback_data="orders_filter_completed"),
        InlineKeyboardButton(text="❌ Bekor",        callback_data="orders_filter_cancelled"),
    )
    builder.row(
        InlineKeyboardButton(text="🔍 ID qidirish", callback_data="search_order_admin"),
    )
    return builder.as_markup()


def _orders_filter_kb(status: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="orders_back_main"))
    return builder.as_markup()


def _order_manage_kb(order_id: int, user_id: int, charge: float, status: str):
    builder = InlineKeyboardBuilder()
    if status not in ("completed", "cancelled"):
        builder.row(
            InlineKeyboardButton(
                text="✅ Bajarildi",
                callback_data=f"ordstatus_completed_{order_id}_{user_id}_{int(charge)}",
            ),
            InlineKeyboardButton(
                text="❌ Bekor",
                callback_data=f"ordstatus_cancelled_{order_id}_{user_id}_{int(charge)}",
            ),
        )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="orders_back_main"))
    return builder.as_markup()


def _format_order_detail(o) -> str:
    if not isinstance(o, dict):
        o = dict(o)
    e       = STATUS_EMOJI.get(o["status"], "❓")
    created = (o.get("created_at") or "")[:16] or "—"
    return (
        f"📦 <b>Buyurtma #{o['id']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 User ID: <code>{o['user_id']}</code>\n"
        f"🔧 Xizmat: {o.get('service_name') or '—'}\n"
        f"🔗 Havola: <code>{o.get('link') or '—'}</code>\n"
        f"📊 Miqdor: {o.get('quantity') or 0:,}\n"
        f"💰 Summa: {o.get('charge') or 0:,.0f} so'm\n"
        f"{e} Holat: {o['status']}\n"
        f"📅 Sana: {created}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


@router.message(F.text == "📦 Buyurtmalar")
async def admin_orders(message: Message):
    if not is_admin(message.from_user.id):
        return

    all_orders = await get_all_orders(limit=10000)
    all_orders = [dict(o) if not isinstance(o, dict) else o for o in all_orders]
    counts = {
        "pending":    sum(1 for o in all_orders if o["status"] == "pending"),
        "processing": sum(1 for o in all_orders if o["status"] == "processing"),
        "completed":  sum(1 for o in all_orders if o["status"] == "completed"),
        "cancelled":  sum(1 for o in all_orders if o["status"] == "cancelled"),
    }

    await message.answer(
        f"📦 <b>Buyurtmalar</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Kutilmoqda:  <b>{counts['pending']}</b> ta\n"
        f"🔄 Jarayonda:   <b>{counts['processing']}</b> ta\n"
        f"✅ Bajarilgan:  <b>{counts['completed']}</b> ta\n"
        f"❌ Bekor:       <b>{counts['cancelled']}</b> ta\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Jami: <b>{len(all_orders)}</b> ta\n\n"
        f"Kategoriyani tanlang 👇",
        parse_mode="HTML",
        reply_markup=_orders_main_kb(),
    )


@router.callback_query(F.data == "orders_back_main")
async def orders_back_main(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    all_orders = await get_all_orders(limit=10000)
    counts = {
        "pending":    sum(1 for o in all_orders if o["status"] == "pending"),
        "processing": sum(1 for o in all_orders if o["status"] == "processing"),
        "completed":  sum(1 for o in all_orders if o["status"] == "completed"),
        "cancelled":  sum(1 for o in all_orders if o["status"] == "cancelled"),
    }
    await callback.message.edit_text(
        f"📦 <b>Buyurtmalar</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Kutilmoqda:  <b>{counts['pending']}</b> ta\n"
        f"🔄 Jarayonda:   <b>{counts['processing']}</b> ta\n"
        f"✅ Bajarilgan:  <b>{counts['completed']}</b> ta\n"
        f"❌ Bekor:       <b>{counts['cancelled']}</b> ta\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Jami: <b>{len(all_orders)}</b> ta\n\n"
        f"Kategoriyani tanlang 👇",
        parse_mode="HTML",
        reply_markup=_orders_main_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("orders_filter_"))
async def orders_filter(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    status = callback.data.replace("orders_filter_", "")
    orders = await get_all_orders(status=status, limit=20)

    titles = {
        "pending":    "⏳ Kutilayotgan buyurtmalar",
        "processing": "🔄 Jarayondagi buyurtmalar",
        "completed":  "✅ Bajarilgan buyurtmalar",
        "cancelled":  "❌ Bekor qilingan buyurtmalar",
    }

    if not orders:
        await callback.answer("Bu kategoriyada buyurtma yo'q!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for o in orders:
        if not isinstance(o, dict):
            o = dict(o)
        e     = STATUS_EMOJI.get(o["status"], "❓")
        charge = o.get("charge") or 0
        label  = f"{e} #{o['id']} · {(o.get('service_name') or '')[:22]} · {charge:,.0f} so'm"
        builder.row(InlineKeyboardButton(
            text=label,
            callback_data=f"order_view_{o['id']}",
        ))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="orders_back_main"))

    await callback.message.edit_text(
        f"{titles.get(status, '📦 Buyurtmalar')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Jami: <b>{len(orders)}</b> ta (oxirgi 20)\n\n"
        f"Batafsil ko'rish uchun bosing 👇",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_view_"))
async def order_view(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    order_id = int(callback.data.split("_")[2])
    order    = await get_order_by_id(order_id)
    if not order:
        await callback.answer("❌ Buyurtma topilmadi!", show_alert=True)
        return
    if not isinstance(order, dict):
        order = dict(order)

    charge = order.get("charge") or 0
    status = order.get("status") or "pending"

    await callback.message.edit_text(
        _format_order_detail(order),
        parse_mode="HTML",
        reply_markup=_order_manage_kb(order_id, order["user_id"], charge, status),
    )
    await callback.answer()


@router.callback_query(F.data == "search_order_admin")
async def search_order_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.answer(
        "🔍 Buyurtma ID sini kiriting:",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(AdminStates.waiting_for_order_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_order_id)
async def process_order_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return
    try:
        oid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        return

    order = await get_order_by_id(oid)
    if not order:
        await message.answer("❌ Buyurtma topilmadi!")
        await state.clear()
        return
    if not isinstance(order, dict):
        order = dict(order)

    charge = order.get("charge") or 0
    status = order.get("status") or "pending"

    await message.answer(
        _format_order_detail(order),
        parse_mode="HTML",
        reply_markup=_order_manage_kb(order["id"], order["user_id"], charge, status),
    )
    await state.clear()


@router.callback_query(F.data.startswith("ordstatus_completed_"))
async def mark_order_completed(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts    = callback.data.split("_")
    oid      = int(parts[2])
    await update_order_status(oid, "completed")
    await callback.answer("✅ Buyurtma bajarildi deb belgilandi!", show_alert=True)

    order = await get_order_by_id(oid)
    if order:
        if not isinstance(order, dict):
            order = dict(order)
        await callback.message.edit_text(
            _format_order_detail(order),
            parse_mode="HTML",
            reply_markup=_order_manage_kb(oid, order["user_id"], order.get("charge") or 0, "completed"),
        )


@router.callback_query(F.data.startswith("ordstatus_cancelled_"))
async def cancel_order_admin(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    parts   = callback.data.split("_")
    oid     = int(parts[2])
    user_id = int(parts[3])
    charge  = float(parts[4])

    await update_order_status(oid, "cancelled")
    await update_user_balance(user_id, charge, add=True)
    await log_transaction(user_id, charge, "refund", f"Buyurtma #{oid} bekor — qaytarildi")

    try:
        await bot.send_message(
            user_id,
            f"♻️ <b>Buyurtma #{oid} bekor qilindi.</b>\n\n"
            f"💰 <b>{charge:,.0f} so'm</b> hisobingizga qaytarildi.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.answer("✅ Bekor qilindi, balans qaytarildi!", show_alert=True)

    order = await get_order_by_id(oid)
    if order:
        if not isinstance(order, dict):
            order = dict(order)
        await callback.message.edit_text(
            _format_order_detail(order),
            parse_mode="HTML",
            reply_markup=_order_manage_kb(oid, user_id, charge, "cancelled"),
        )


# ══════════════════════════════════════════════════════════════════════════════
# 🎫 SUPPORT CHATLAR
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🎫 Yordam Chatlari")
async def admin_support_tickets(message: Message):
    if not is_admin(message.from_user.id):
        return
    tickets = await get_all_open_tickets()
    if not tickets:
        await message.answer("🎫 Ochiq support ticketlar yo'q.")
        return

    text = "🎫 <b>Ochiq Support Ticketlar:</b>\n\n"
    builder = InlineKeyboardBuilder()
    for t in tickets:
        name = t.get("full_name") or str(t["user_id"])
        text += f"#{t['id']} | 👤 {name} (<code>{t['user_id']}</code>)\n"
        builder.row(InlineKeyboardButton(
            text=f"#{t['id']} — {name[:20]}",
            callback_data=f"reply_ticket_{t['id']}_{t['user_id']}",
        ))

    await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())


# ══════════════════════════════════════════════════════════════════════════════
# ⚙️ SOZLAMALAR
# ══════════════════════════════════════════════════════════════════════════════

def _settings_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🎁 Kunlik bonusni o'zgartir", callback_data="set_daily_bonus"
    ))
    builder.row(InlineKeyboardButton(
        text="👥 Referal bonusni o'zgartir", callback_data="set_ref_bonus"
    ))
    builder.row(InlineKeyboardButton(
        text="📢 Kanallarni o'zgartir", callback_data="set_channels"
    ))
    return builder.as_markup()


@router.message(F.text == "⚙️ Sozlamalar")
async def admin_settings(message: Message):
    if not is_admin(message.from_user.id):
        return
    daily    = await get_setting("daily_bonus")    or str(getattr(settings, "DAILY_BONUS_AMOUNT", 500))
    ref      = await get_setting("referral_bonus") or str(getattr(settings, "REFERRAL_BONUS_AMOUNT", 5000))
    channels = await get_setting("force_channels") or getattr(settings, "FORCE_CHANNELS", "—")

    await message.answer(
        "⚙️ <b>Bot Sozlamalari</b>\n\n"
        f"🎁 Kunlik bonus: <b>{daily} so'm</b>\n"
        f"👥 Referal bonus: <b>{ref} so'm</b>\n"
        f"📢 Majburiy kanallar: <b>{channels}</b>",
        parse_mode="HTML",
        reply_markup=_settings_keyboard(),
    )


@router.callback_query(F.data.startswith("set_"))
async def setting_change_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    key = callback.data[4:]
    labels = {
        "daily_bonus": "🎁 Kunlik bonus (so'mda)",
        "ref_bonus":   "👥 Referal bonus (so'mda)",
        "channels":    "📢 Kanallar (@kanal1,@kanal2)",
    }
    await state.update_data(setting_key=key)
    await callback.message.answer(
        f"✏️ <b>{labels.get(key, key)}</b>\n\nYangi qiymatni kiriting:",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(AdminStates.waiting_for_setting_value)
    await callback.answer()


@router.message(AdminStates.waiting_for_setting_value)
async def process_setting_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=get_admin_menu())
        return
    data  = await state.get_data()
    key   = data["setting_key"]
    value = message.text.strip()
    await set_setting(key, value)
    await message.answer(
        f"✅ <b>Sozlama yangilandi!</b>\n\n"
        f"🔑 Kalit: <code>{key}</code>\n"
        f"📝 Yangi qiymat: <code>{value}</code>",
        parse_mode="HTML",
        reply_markup=get_admin_menu(),
    )
    await state.clear()


# ══════════════════════════════════════════════════════════════════════════════
# 🏠 ASOSIY MENU
# ══════════════════════════════════════════════════════════════════════════════

@router.message(F.text == "🏠 Asosiy Menu")
async def back_to_main(message: Message):
    await message.answer("🏠 Asosiy menuga qaytdingiz.", reply_markup=get_main_menu())