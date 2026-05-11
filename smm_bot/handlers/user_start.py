import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ChatMemberLeft, ChatMemberBanned
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from config import settings
from database.db_queries import (
    create_or_update_user,
    get_user,
    update_user_balance,
    log_transaction,
    get_referral_count,
)
from keyboards.inline_kb import get_subscribe_keyboard, get_check_subscribe_keyboard
from keyboards.reply_kb import get_main_menu

logger = logging.getLogger(__name__)
router = Router()


async def check_subscription(bot: Bot, user_id: int) -> list[str]:
    """
    Check if user is subscribed to all required channels.
    Returns list of channels the user is NOT subscribed to.
    """
    not_subscribed = []
    for channel in settings.force_channels_list:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if isinstance(member, (ChatMemberLeft, ChatMemberBanned)):
                not_subscribed.append(channel)
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning(f"Could not check subscription for {channel}: {e}")
    return not_subscribed


def extract_referral_id(text: str) -> int | None:
    """Extract referral user_id from /start ref_USERID."""
    parts = text.split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            return int(parts[1][4:])
        except ValueError:
            return None
    return None


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user = message.from_user
    referrer_id = extract_referral_id(message.text or "")

    # Don't allow self-referral
    if referrer_id == user.id:
        referrer_id = None

    # Register/update user in DB (returns True if new user)
    is_new = await create_or_update_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        referrer_id=referrer_id,
    )

    # ── Handle referral bonus for NEW users ────────────────────────────────────
    if is_new and referrer_id:
        referrer = await get_user(referrer_id)
        if referrer and not referrer["is_banned"]:
            bonus = settings.REFERRAL_BONUS_AMOUNT
            await update_user_balance(referrer_id, bonus, add=True)
            await log_transaction(
                referrer_id, bonus, "referral",
                f"Referal bonusi: {user.full_name} ({user.id})"
            )
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉 <b>Yangi referal!</b>\n"
                    f"👤 {user.full_name} sizning havolangiz orqali qo'shildi.\n"
                    f"💰 Hisobingizga <b>{bonus:,} so'm</b> qo'shildi!",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    # ── Check force subscription ───────────────────────────────────────────────
    missing_channels = await check_subscription(bot, user.id)

    if missing_channels:
        await message.answer(
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "🔔 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz shart:\n\n"
            "✅ A'zo bo'lgach, <b>«✅ Tekshirish»</b> tugmasini bosing.",
            parse_mode="HTML",
            reply_markup=get_subscribe_keyboard(missing_channels),
        )
        return

    # ── Banned check ──────────────────────────────────────────────────────────
    db_user = await get_user(user.id)
    if db_user and db_user["is_banned"]:
        await message.answer(
            "🚫 <b>Siz bloklandingiz.</b>\n"
            "Murojaat uchun: @support",
            parse_mode="HTML",
        )
        return

    # ── Show main menu ────────────────────────────────────────────────────────
    await show_main_menu(message, user.full_name, is_new)


async def show_main_menu(message: Message, full_name: str, is_new: bool = False):
    greeting = (
        f"🎉 <b>Xush kelibsiz, {full_name}!</b>\n\n"
        if is_new
        else f"👋 <b>Salom, {full_name}!</b>\n\n"
    )
    await message.answer(
        greeting +
        "🤖 <b>SMM Pro Bot</b> — ijtimoiy tarmoqlar uchun xizmatlar va virtual raqamlar.\n\n"
        "📌 Kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=get_main_menu(),
    )


@router.callback_query(F.data == "check_subscribe")
async def check_subscribe_callback(callback: CallbackQuery, bot: Bot):
    """Re-check subscription when user presses the button."""
    await callback.answer("Tekshirilmoqda...", show_alert=False)

    missing_channels = await check_subscription(bot, callback.from_user.id)

    if missing_channels:
        await callback.message.edit_text(
            "❌ <b>Siz hali barcha kanallarga a'zo bo'lmadingiz.</b>\n\n"
            "🔔 Quyidagi kanallarga a'zo bo'lib, qayta tekshiring:\n",
            parse_mode="HTML",
            reply_markup=get_subscribe_keyboard(missing_channels),
        )
        return

    # ── Banned check ──────────────────────────────────────────────────────────
    db_user = await get_user(callback.from_user.id)
    if db_user and db_user["is_banned"]:
        await callback.message.edit_text(
            "🚫 <b>Siz bloklandingiz.</b>",
            parse_mode="HTML",
        )
        return

    await callback.message.delete()
    await show_main_menu(callback.message, callback.from_user.full_name)