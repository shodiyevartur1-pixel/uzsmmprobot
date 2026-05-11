import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import settings
from database.db_queries import (
    create_support_ticket, get_open_ticket,
    log_support_message, close_ticket, get_ticket_by_id
)
from keyboards.reply_kb import get_main_menu, get_cancel_button
from keyboards.inline_kb import get_support_reply_keyboard
from states.user_states import SupportStates, AdminStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "🆘 Yordam")
async def support_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🆘 <b>Yordam xizmati</b>\n\n"
        "Muammoingizni yozing, admin tez orada javob beradi.\n\n"
        "Bekor qilish uchun tugmani bosing 👇",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(SupportStates.waiting_for_message)


@router.message(F.text == "❌ Bekor qilish")
async def cancel_any(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is not None:
        await state.clear()
    await message.answer(
        "❌ Bekor qilindi.",
        reply_markup=get_main_menu(),
    )


@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    ticket_id = await create_support_ticket(message.from_user.id)

    media_id = None
    media_type = None
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.document:
        media_id = message.document.file_id
        media_type = "document"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"

    await log_support_message(
        ticket_id, message.from_user.id, False,
        message.text or message.caption, media_id, media_type
    )

    # Adminlarga yuborish
    for admin_id in settings.admin_ids_list:
        try:
            text = (
                f"🎫 <b>Yangi Support #{ticket_id}</b>\n\n"
                f"👤 {message.from_user.full_name}\n"
                f"🆔 ID: <code>{message.from_user.id}</code>\n"
                f"📝 Xabar: {message.text or message.caption or '[Media fayl]'}"
            )
            kb = get_support_reply_keyboard(ticket_id, message.from_user.id)

            if media_type == "photo":
                await bot.send_photo(admin_id, media_id, caption=text, parse_mode="HTML", reply_markup=kb)
            elif media_type == "document":
                await bot.send_document(admin_id, media_id, caption=text, parse_mode="HTML", reply_markup=kb)
            elif media_type == "video":
                await bot.send_video(admin_id, media_id, caption=text, parse_mode="HTML", reply_markup=kb)
            else:
                await bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=kb)
        except Exception as e:
            logger.error(f"Admin {admin_id} ga yuborishda xato: {e}")

    # Foydalanuvchiga tasdiqlash + asosiy menu qaytarish
    await message.answer(
        f"✅ <b>Xabaringiz yuborildi!</b>\n\n"
        f"🎫 Ticket raqami: <b>#{ticket_id}</b>\n"
        f"⏳ Admin tez orada javob beradi.",
        parse_mode="HTML",
        reply_markup=get_main_menu(),
    )
    await state.clear()


# ── ADMIN: Javob berish ───────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("reply_ticket_"))
async def admin_reply_ticket(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.admin_ids_list:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split("_")
    ticket_id = int(parts[2])
    user_id = int(parts[3])

    await state.update_data(reply_ticket_id=ticket_id, reply_user_id=user_id)
    await state.set_state(AdminStates.waiting_for_support_reply)

    await callback.message.answer(
        f"✏️ <b>Ticket #{ticket_id}</b> ga javob yozing:\n\n"
        f"Bekor qilish uchun ❌ tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_support_reply)
async def send_admin_reply(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_menu())
        return

    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")
    user_id = data.get("reply_user_id")

    if not ticket_id or not user_id:
        await state.clear()
        return

    await log_support_message(ticket_id, message.from_user.id, True, message.text)

    try:
        await bot.send_message(
            user_id,
            f"📩 <b>Ticket #{ticket_id} — Admin javobi:</b>\n\n"
            f"{message.text}",
            parse_mode="HTML",
        )
        await message.answer(
            f"✅ Javob foydalanuvchiga yuborildi!\n🎫 Ticket #{ticket_id}",
            reply_markup=get_main_menu(),
        )
    except Exception:
        await message.answer(
            "❌ Foydalanuvchiga yuborib bo'lmadi. (Bot bloklangandir)",
            reply_markup=get_main_menu(),
        )

    await state.clear()


# ── ADMIN: Ticketni yopish ────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("close_ticket_"))
async def admin_close_ticket(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in settings.admin_ids_list:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    ticket_id = int(callback.data.split("_")[2])
    ticket = await get_ticket_by_id(ticket_id)

    if not ticket:
        await callback.answer("Ticket topilmadi!", show_alert=True)
        return

    await close_ticket(ticket_id)

    try:
        await bot.send_message(
            ticket["user_id"],
            f"✅ <b>Ticket #{ticket_id} yopildi.</b>\n\n"
            f"Yana muammo bo'lsa 🆘 Yordam bo'limiga murojaat qiling.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.answer(f"✅ Ticket #{ticket_id} yopildi!", show_alert=True)