import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.filters import Command

from config import settings
from database.db_queries import (
    get_all_users, get_user, update_user_balance, 
    log_transaction, add_promo_code, get_stats
)
from states.user_states import AdminStates

logger = logging.getLogger(__name__)
router = Router()

# ── XAVFSIZLIK FILTRI ──────────────────────────────────────────────────────
async def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


# ── KLAVIATURALAR ──────────────────────────────────────────────────────────
def get_admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"))
    builder.row(
        InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="👥 Foydalanuvchi", callback_data="admin_user_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🎟 Promo yaratish", callback_data="admin_promo_menu"),
        InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings")
    )
    return builder.as_markup()


# ── ASOSIY MENYU ──────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not await is_admin(message.from_user.id):
        return
    await message.answer(
        "👑 <b>Admin Panel (V2 - Kuchaytirilgan)</b>\n\n"
        "Botni boshqarish markazi. Tanlang 👇",
        parse_mode="HTML",
        reply_markup=get_admin_main_kb()
    )


@router.callback_query(F.data == "admin_back")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "👑 <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=get_admin_main_kb()
    )
    await callback.answer()


# ── STATISTIKA ──────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    
    stats = await get_stats() # Bu funksiyani db_queries ga qo'shishingiz kerak
    
    await callback.message.edit_text(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats.get('total_users', 0)}</b>\n"
        f"📈 Kunlik faol: <b>{stats.get('active_today', 0)}</b>\n"
        f"💰 Umumiy balans: <b>{stats.get('total_balance', 0):,.0f} so'm</b>\n"
        f"💸 Jami sarflangan: <b>{stats.get('total_spent', 0):,.0f} so'm</b>\n"
        f"📦 Jami buyurtmalar: <b>{stats.get('total_orders', 0)}</b>",
        parse_mode="HTML",
        reply_markup=get_admin_main_kb()
    )
    await callback.answer()


# ── FOYDALANUVCHI BOSHQARUVI ───────────────────────────────────────────────
@router.callback_query(F.data == "admin_user_menu")
async def user_menu(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    
    await callback.message.edit_text(
        "👥 <b>Foydalanuvchi boshqaruvi</b>\n\n"
        "Boshqarmoqchi bo'lgan foydalanuvchining ID raqamini kiriting:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return await state.clear()

    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting (ID)!")
        return

    user = await get_user(user_id)
    if not user:
        await message.answer("❌ Bunday ID li foydalanuvchi bazada topilmadi!")
        return

    # sqlite3.Row ni dict ga o'tkazamiz
    if not isinstance(user, dict):
        user = dict(user)

    await state.update_data(target_user_id=user_id)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Balans qo'shish", callback_data="admin_add_balance"))
    builder.row(InlineKeyboardButton(text="➖ Balans ayirish", callback_data="admin_sub_balance"))
    builder.row(InlineKeyboardButton(text="📩 Xabar yuborish", callback_data="admin_msg_user"))
    builder.row(InlineKeyboardButton(text="🚫 Ban qilish", callback_data="admin_ban_user"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))

    await message.answer(
        f"👤 <b>Foydalanuvchi topildi:</b>\n\n"
        f"🆔 ID: <code>{user.get('user_id')}</code>\n"
        f"👤 Ism: {user.get('full_name')}\n"
        f"💰 Balans: <b>{user.get('balance', 0):,.0f} so'm</b>\n\n"
        f"Amalni tanlang 👇",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("admin_add_balance") | F.data.startswith("admin_sub_balance"))
async def ask_balance_amount(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    action = "qo'shish" if "add" in callback.data else "ayirish"
    await state.update_data(balance_action=callback.data)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_back"))
    
    await callback.message.edit_text(
        f"💰 Qancha summa {action} kerak?\n\n"
        "Faqat raqam kiriting:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AdminStates.waiting_for_balance_amount)
    await callback.answer()


@router.message(AdminStates.waiting_for_balance_amount)
async def process_balance_update(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return await state.clear()

    try:
        amount = int(message.text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Faqat musbat raqam kiriting!")
        return

    data = await state.get_data()
    user_id = data.get('target_user_id')
    action = data.get('balance_action')

    is_add = "add" in action
    
    # Bazaga yozamiz
    await update_user_balance(user_id, amount, add=is_add)
    
    # Tranzaksiya logi
    log_type = "admin_add" if is_add else "admin_subtract"
    await log_transaction(user_id, amount, log_type, f"Admin: {message.from_user.id}")

    # Foydalanuvchiga xabar yuboramiz
    try:
        text = f"💰 Hisobingizga {amount:,} so'm qo'shildi!" if is_add else f"💰 Hisobingizdan {amount:,} so'm yechildi!"
        await bot.send_message(user_id, text)
    except Exception:
        pass

    await message.answer(
        f"✅ <b>Muvaffaqiyatli!</b>\n\n"
        f"{'Qo\'shildi' if is_add else 'Ayirildi'}: {amount:,} so'm\n"
        f"Foydalanuvchi: <code>{user_id}</code>",
        parse_mode="HTML",
        reply_markup=get_admin_main_kb()
    )
    await state.clear()


# ── FOYDALANUVCHIGA XABAR YUBORISH ─────────────────────────────────────────
@router.callback_query(F.data == "admin_msg_user")
async def ask_user_message(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_back"))
    
    await callback.message.edit_text(
        "📩 <b>Foydalanuvchiga shaxsiy xabar yuborish</b>\n\n"
        "Xabar matnini kiriting:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AdminStates.waiting_for_user_message)
    await callback.answer()


@router.message(AdminStates.waiting_for_user_message)
async def send_message_to_user(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return await state.clear()
    
    data = await state.get_data()
    user_id = data.get('target_user_id')
    
    try:
        await bot.send_message(
            user_id, 
            f"✉️ <b>Admindan xabar:</b>\n\n{message.text}",
            parse_mode="HTML"
        )
        await message.answer("✅ Xabar muvaffaqiyatli yuborildi!", reply_markup=get_admin_main_kb())
    except Exception as e:
        await message.answer(f"❌ Xabar yuborilmadi. Foydalanuvchi botni bloklagan bo'lishi mumkin.\nXato: {e}", reply_markup=get_admin_main_kb())
    
    await state.clear()


# ── TO'LOVLARNI TASDIQLASH ─────────────────────────────────────────────────
@router.message(F.text.startswith("/addbalance_"))
async def approve_payment(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    try:
        _, user_id_str, amount_str = message.text.split("_")
        user_id = int(user_id_str)
        amount = int(amount_str)
        
        await update_user_balance(user_id, amount, add=True)
        await log_transaction(user_id, amount, "topup", "Admin tomonidan tasdiqlandi")
        
        # Foydalanuvchiga xabar
        await bot.send_message(
            user_id,
            f"✅ <b>To'lov tasdiqlandi!</b>\n\n"
            f"💰 Hisobingizga {amount:,} so'm qo'shildi.",
            parse_mode="HTML"
        )
        
        await message.answer(f"✅ To'lov tasdiqlandi: +{amount:,} so'm (ID: {user_id})", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


@router.message(F.text.startswith("/reject_"))
async def reject_payment(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    try:
        _, user_id_str, request_id = message.text.split("_")
        user_id = int(user_id_str)
        
        await bot.send_message(
            user_id,
            "❌ <b>To'lov rad etildi!</b>\n\n"
            "Chek noto'g'ri yoki to'lov amalga oshmagan. Qayta urinib ko'ring.",
            parse_mode="HTML"
        )
        
        await message.answer(f"❌ To'lov rad etildi (ID: {user_id})", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


# ── XABAR YUBORISH (BROADCAST) ─────────────────────────────────────────────
@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_back"))
    
    await callback.message.edit_text(
        "📢 <b>Barchaga xabar yuborish</b>\n\n"
        "Yubormoqchi bo'lgan xabaringizni (matn, rasm, video) yuboring:\n\n"
        "⚠️ Xabar katta bo'lsa ham, bot barchaga yuboradi.",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return await state.clear()

    # Barcha foydalanuvchilarni olamiz
    users = await get_all_users() # Bu funksiyani db_queries ga qo'shing
    success = 0
    blocked = 0

    status_msg = await message.answer("⏳ <b>Xabar yuborilmoqda...</b>\n\nBiroz kuting.", parse_mode="HTML")

    for user in users:
        # sqlite3.Row yoki dict ekanligini tekshiramiz
        user_id = user['user_id'] if isinstance(user, dict) else user[0]
        
        if user_id == message.from_user.id: # O'ziga yubormaslik
            continue
            
        try:
            await message.copy_to(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05) # Telegram limit uchun
        except Exception:
            blocked += 1 # Botni bloklaganlar

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborish tugadi!</b>\n\n"
        f"📤 Yetkazildi: <b>{success}</b> ta\n"
        f"🚫 Bloklaganlar: <b>{blocked}</b> ta",
        parse_mode="HTML",
        reply_markup=get_admin_main_kb()
    )
    await state.clear()


# ── PROMOKOD YARATISH ──────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_promo_menu")
async def promo_menu(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    
    await callback.message.edit_text(
        "🎟 <b>Promokod yaratish</b>\n\n"
        "Yangi promo kod nomini kiriting (masalan: SMM2024):",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AdminStates.waiting_for_promo_code)
    await callback.answer()


@router.message(AdminStates.waiting_for_promo_code)
async def process_promo_code(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return await state.clear()
    
    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    
    await message.answer(
        f"🎟 Kod: <code>{code}</code>\n\n"
        "💰 Bu kod uchun qancha summa bo'lsin? (Faqat raqam):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_promo_amount)


@router.message(AdminStates.waiting_for_promo_amount)
async def process_promo_amount(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return await state.clear()
    
    try:
        amount = int(message.text.replace(" ", ""))
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Faqat musbat raqam kiriting!")
        return
    
    await state.update_data(promo_amount=amount)
    
    await message.answer(
        f"💰 Summa: {amount:,} so'm\n\n"
        "🔄 Necha marta ishlatish mumkin? (Faqat raqam):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_promo_uses)


@router.message(AdminStates.waiting_for_promo_uses)
async def process_promo_uses(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return await state.clear()
    
    try:
        max_uses = int(message.text.replace(" ", ""))
        if max_uses <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Faqat musbat raqam kiriting!")
        return
    
    data = await state.get_data()
    code = data.get('promo_code')
    amount = data.get('promo_amount')
    
    # Bazaga yozamiz
    await add_promo_code(code, amount, max_uses)
    
    await message.answer(
        f"✅ <b>Promo kod muvaffaqiyatli yaratildi!</b>\n\n"
        f"🎟 Kod: <code>{code}</code>\n"
        f"💰 Summa: {amount:,} so'm\n"
        f"🔄 Limit: {max_uses} ta\n\n"
        f"Foydalanuvchilar endi bu kodni ishlatishi mumkin!",
        parse_mode="HTML",
        reply_markup=get_admin_main_kb()
    )
    await state.clear()


# ── SOZLAMALAR ──────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    
    await callback.message.edit_text(
        "⚙️ <b>Bot Sozlamalari</b>\n\n"
        f"🎁 Kunlik bonus: <b>{settings.DAILY_BONUS_AMOUNT:,} so'm</b>\n"
        f"👥 Referal bonusi: <b>{settings.REFERRAL_BONUS_AMOUNT:,} so'm</b>\n"
        f"💳 Minimal to'ldirish: <b>{settings.MIN_DEPOSIT:,} so'm</b>\n\n"
        f"<i>Sozlamalarni o'zgartirish uchun config.py faylini tahrirlang.</i>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# ── BAN QILISH (TAYYOR STRUKTURA) ──────────────────────────────────────────
@router.callback_query(F.data == "admin_ban_user")
async def ban_user(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    
    data = await state.get_data()
    user_id = data.get('target_user_id')
    
    # Bu yerga database da ban qilish funksiyasini yozasiz: await ban_user_db(user_id)
    
    await callback.message.edit_text(
        f"🚫 <b>Foydalanuvchi ban qilindi!</b>\n\n"
        f"ID: <code>{user_id}</code>\n\n"
        f"<i>(Hozircha bu demo, bazaga ban funksiyasini qo'shishingiz kerak)</i>",
        parse_mode="HTML",
        reply_markup=get_admin_main_kb()
    )
    await state.clear()
    await callback.answer()