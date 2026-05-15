import logging
import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import settings
from database.db_queries import (
    get_user, get_referral_count, get_user_orders,
    can_claim_daily_bonus, log_daily_bonus, update_user_balance,
    log_transaction, get_promo, redeem_promo, has_user_used_promo
)
from keyboards.reply_kb import get_main_menu
from states.user_states import EarnStates, TopUpStates

logger = logging.getLogger(__name__)
router = Router()

# ══════════════════════════════════════════════════════════════════
# 💳 KARTA MA'LUMOTLARI
# ══════════════════════════════════════════════════════════════════
CARD_NUMBER = "9860 6067 5238 6163"
CARD_OWNER  = "Shodiyev Artur"
CARD_BANK   = "HUMO"

CLICK_MERCHANT_ID = "SIZNING_CLICK_MERCHANT_ID"
CLICK_SERVICE_ID  = "SIZNING_CLICK_SERVICE_ID"
UZUM_MERCHANT_ID  = "SIZNING_UZUM_MERCHANT_ID"


def make_click_url(amount: int, invoice_id: str) -> str:
    return (
        f"https://my.click.uz/services/pay"
        f"?service_id={CLICK_SERVICE_ID}"
        f"&merchant_id={CLICK_MERCHANT_ID}"
        f"&amount={amount}"
        f"&transaction_param={invoice_id}"
    )


def make_uzum_url(amount: int, invoice_id: str) -> str:
    amount_tiyin = amount * 100
    return (
        f"https://checkout.paycom.uz"
        f"?merchant={UZUM_MERCHANT_ID}"
        f"&amount={amount_tiyin}"
        f"&account[order_id]={invoice_id}"
    )


# ══════════════════════════════════════════════════════════════════
# 🔧 XABARNI XAVFSIZ O'CHIRISH
# ══════════════════════════════════════════════════════════════════

async def safe_delete(bot: Bot, chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def delete_messages(bot: Bot, chat_id: int, message_ids: list):
    for mid in message_ids:
        if mid:
            await safe_delete(bot, chat_id, mid)


# ══════════════════════════════════════════════════════════════════
# 🔧 KLAVIATURALAR
# ══════════════════════════════════════════════════════════════════

def _topup_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Humo kartasi", callback_data="topup_humo"),
    )
    builder.row(
        InlineKeyboardButton(text="🔹 Click [Avto]", callback_data="topup_click"),
        InlineKeyboardButton(text="🍇 Uzum [Avto]",  callback_data="topup_uzum"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main"),
    )
    return builder.as_markup()


def _humo_card_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="topup_back"),
    )
    return builder.as_markup()


def _auto_pay_kb(pay_url: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 To'lovga o'tish", url=pay_url)
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="topup_back"),
    )
    return builder.as_markup()


def _admin_payment_kb(user_id: int, amount: int, invoice_id: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"✅ {amount:,} so'm — Tasdiqlash",
            callback_data=f"payadm_yes_{user_id}_{amount}_{invoice_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Rad etish",
            callback_data=f"payadm_no_{user_id}_{invoice_id}",
        )
    )
    return builder.as_markup()


def _earn_kb(can_bonus: bool):
    builder = InlineKeyboardBuilder()
    if can_bonus:
        builder.row(InlineKeyboardButton(
            text="🎁 Kunlik bonus olish",
            callback_data="daily_bonus",
        ))
    else:
        builder.row(InlineKeyboardButton(
            text="✅ Bugun olindi (24 soat)",
            callback_data="noop_bonus",
        ))
    builder.row(InlineKeyboardButton(
        text="🎟 Promo kod kiritish",
        callback_data="enter_promo",
    ))
    builder.row(InlineKeyboardButton(
        text="🔗 Referal havolani ko'rish",
        callback_data="show_ref_link",
    ))
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# 👤 HISOBIM
# ══════════════════════════════════════════════════════════════════

@router.message(F.text == "👤 Hisobim")
async def my_account(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    if not isinstance(user, dict):
        user = dict(user)

    referrals = await get_referral_count(message.from_user.id)
    orders    = await get_user_orders(message.from_user.id, limit=1000)
    bot_info  = await bot.get_me()
    ref_link  = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Hisob to'ldirish", callback_data="topup_quick"),
        InlineKeyboardButton(text="💰 Pul ishlash",      callback_data="earn_quick"),
    )

    await message.answer(
        f"👤 <b>Mening hisobim</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Ism: <b>{user['full_name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Balans: <b>{user['balance']:,.0f} so'm</b>\n"
        f"💸 Jami sarflangan: <b>{user['total_spent']:,.0f} so'm</b>\n"
        f"📦 Buyurtmalar: <b>{len(orders)} ta</b>\n"
        f"👥 Referallar: <b>{referrals} ta</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Referal havola:</b>\n"
        f"<code>{ref_link}</code>",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "topup_quick")
async def topup_quick_cb(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not isinstance(user, dict):
        user = dict(user)
    await safe_delete(callback.bot, callback.message.chat.id, callback.message.message_id)
    await callback.message.answer(
        f"💳 <b>Hisob To'ldirish</b>\n\n"
        f"💰 Joriy balans: <b>{user['balance']:,.0f} so'm</b>\n\n"
        f"To'lov usulini tanlang 👇",
        parse_mode="HTML",
        reply_markup=_topup_main_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "earn_quick")
async def earn_quick_cb(callback: CallbackQuery, bot: Bot):
    await safe_delete(bot, callback.message.chat.id, callback.message.message_id)
    await _send_earn_menu(callback.message, callback.from_user.id, bot)
    await callback.answer()


# ══════════════════════════════════════════════════════════════════
# 💳 HISOB TO'LDIRISH
# ══════════════════════════════════════════════════════════════════

@router.message(F.text == "💳 Hisob To'ldirish")
async def topup_menu(message: Message):
    user = await get_user(message.from_user.id)
    if not isinstance(user, dict):
        user = dict(user)

    # Avval reply menyu o'chiriladi, keyin to'lov ekrani chiqadi
    await message.answer(
        "⏳",
        reply_markup=ReplyKeyboardRemove(),
    )
    # O'sha "⏳" xabarini darhol o'chiramiz
    sent_remove = await message.answer(
        f"💳 <b>Hisob To'ldirish</b>\n\n"
        f"💰 Joriy balans: <b>{user['balance']:,.0f} so'm</b>\n\n"
        f"To'lov usulini tanlang 👇",
        parse_mode="HTML",
        reply_markup=_topup_main_kb(),
    )
    # ReplyKeyboardRemove xabarini o'chiramiz (faqat "⏳" xabari)
    try:
        await message.bot.delete_message(message.chat.id, sent_remove.message_id - 1)
    except Exception:
        pass


@router.callback_query(F.data == "topup_back")
async def topup_back_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_user(callback.from_user.id)
    if not isinstance(user, dict):
        user = dict(user)
    await safe_delete(callback.bot, callback.message.chat.id, callback.message.message_id)
    await callback.message.answer(
        f"💳 <b>Hisob To'ldirish</b>\n\n"
        f"💰 Joriy balans: <b>{user['balance']:,.0f} so'm</b>\n\n"
        f"To'lov usulini tanlang 👇",
        parse_mode="HTML",
        reply_markup=_topup_main_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_main_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_delete(callback.bot, callback.message.chat.id, callback.message.message_id)
    await callback.message.answer("🏠 Asosiy menyu", reply_markup=get_main_menu())
    await callback.answer()


# ── USUL TANLANDI → SUMMA SO'RASH ────────────────────────────────

@router.callback_query(F.data.in_({"topup_humo", "topup_click", "topup_uzum"}))
async def topup_method_selected(callback: CallbackQuery, state: FSMContext):
    method = callback.data.replace("topup_", "")
    await state.update_data(method=method)
    await state.set_state(TopUpStates.waiting_for_amount)

    labels = {
        "humo":  "💳 Humo kartasi",
        "click": "🔹 Click",
        "uzum":  "🍇 Uzum",
    }
    name = labels.get(method, "💳")

    await safe_delete(callback.bot, callback.message.chat.id, callback.message.message_id)

    # Faqat "Orqaga" inline tugma — reply keyboard YO'Q
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="topup_back"))

    sent = await callback.message.answer(
        f"{name} <b>orqali to'ldirish</b>\n\n"
        f"💵 Qancha so'm to'ldirmoqchisiz?\n"
        f"📌 Minimal: <b>2 000 so'm</b>\n\n"
        f"Summani kiriting (faqat raqam):\n"
        f"Masalan: 10000",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await state.update_data(amount_ask_msg_id=sent.message_id)
    await callback.answer()


# ── SUMMA KIRITILDI ───────────────────────────────────────────────

@router.message(TopUpStates.waiting_for_amount)
async def process_topup_amount(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    amount_ask_msg_id = data.get("amount_ask_msg_id")

    # Foydalanuvchi yozgan xabarni o'chiramiz (faqat raqam yoki noto'g'ri matn)
    await safe_delete(bot, message.chat.id, message.message_id)

    try:
        amount = int(
            message.text.strip()
            .replace(" ", "")
            .replace(",", "")
            .replace(".", "")
        )
    except ValueError:
        # Xato bo'lsa, summa so'rash xabarini yangilaymiz (o'chirib qayta yuborish)
        await safe_delete(bot, message.chat.id, amount_ask_msg_id)
        data_method = data.get("method", "humo")
        labels = {"humo": "💳 Humo kartasi", "click": "🔹 Click", "uzum": "🍇 Uzum"}
        name = labels.get(data_method, "💳")
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="topup_back"))
        sent = await message.answer(
            f"{name} <b>orqali to'ldirish</b>\n\n"
            f"❌ Faqat raqam kiriting!\n\n"
            f"💵 Qancha so'm to'ldirmoqchisiz?\n"
            f"📌 Minimal: <b>2 000 so'm</b>\n\n"
            f"Summani kiriting (faqat raqam):\n"
            f"Masalan: 10000",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
        await state.update_data(amount_ask_msg_id=sent.message_id)
        return

    if amount < 2000:
        await safe_delete(bot, message.chat.id, amount_ask_msg_id)
        data_method = data.get("method", "humo")
        labels = {"humo": "💳 Humo kartasi", "click": "🔹 Click", "uzum": "🍇 Uzum"}
        name = labels.get(data_method, "💳")
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="topup_back"))
        sent = await message.answer(
            f"{name} <b>orqali to'ldirish</b>\n\n"
            f"❌ Minimal summa: <b>2 000 so'm</b>\n\n"
            f"💵 Qancha so'm to'ldirmoqchisiz?\n"
            f"Summani kiriting (faqat raqam):\n"
            f"Masalan: 10000",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
        await state.update_data(amount_ask_msg_id=sent.message_id)
        return

    if amount > 10_000_000:
        await safe_delete(bot, message.chat.id, amount_ask_msg_id)
        data_method = data.get("method", "humo")
        labels = {"humo": "💳 Humo kartasi", "click": "🔹 Click", "uzum": "🍇 Uzum"}
        name = labels.get(data_method, "💳")
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="topup_back"))
        sent = await message.answer(
            f"{name} <b>orqali to'ldirish</b>\n\n"
            f"❌ Maksimal summa: <b>10 000 000 so'm</b>\n\n"
            f"💵 Qancha so'm to'ldirmoqchisiz?\n"
            f"Summani kiriting (faqat raqam):\n"
            f"Masalan: 10000",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
        await state.update_data(amount_ask_msg_id=sent.message_id)
        return

    method     = data.get("method", "humo")
    invoice_id = f"INV{message.from_user.id}{int(time.time())}"

    await state.update_data(amount=amount, invoice_id=invoice_id)
    await safe_delete(bot, message.chat.id, amount_ask_msg_id)

    # ── HUMO ─────────────────────────────────────────────────────
    if method == "humo":
        await state.set_state(TopUpStates.waiting_for_payment_proof)
        sent = await message.answer(
            f"💳 <b>HUMO TO'LOV</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 Bank: <b>ANOR BANK</b>\n"
            f"💳 Humo: <code>{CARD_NUMBER}</code>\n"
            f"📞 Ulangan raqam: <code>+998886636003</code>\n"
            f"👤 Karta egasi: <b>{CARD_OWNER}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💵 To'lov summasi: <b>{amount:,} so'm</b>\n\n"
            f"⚠️ Yuqoridagi kartaga pul o'tkazing va\n"
            f"📸 <b>to'lov chekining rasmini shu yerga yuboring!</b>",
            parse_mode="HTML",
            reply_markup=_humo_card_kb(),
        )
        await state.update_data(proof_ask_msg_id=sent.message_id)

    # ── CLICK ─────────────────────────────────────────────────────
    elif method == "click":
        await state.clear()
        await message.answer(
            f"🔵 <b>Click [ Avto ] orqali hisob to'ldirish!</b>\n\n"
            f"⚠️ To'lov to'langandan keyin bot balansiga avtomatik tashlab beriladi.\n\n"
            f"👤 ID raqam: <code>{message.from_user.id}</code>\n"
            f"💵 Summa: <b>{amount:,} so'm</b>\n\n"
            f"👇 Quyidagi tugmani bosib to'lovni amalga oshiring.",
            parse_mode="HTML",
            reply_markup=_auto_pay_kb(make_click_url(amount, invoice_id)),
        )

    # ── UZUM ──────────────────────────────────────────────────────
    elif method == "uzum":
        await state.clear()
        await message.answer(
            f"🍇 <b>Uzum [ Avto ] orqali hisob to'ldirish!</b>\n\n"
            f"⚠️ To'lov to'langandan keyin bot balansiga avtomatik tashlab beriladi.\n\n"
            f"👤 ID raqam: <code>{message.from_user.id}</code>\n"
            f"💵 Summa: <b>{amount:,} so'm</b>\n\n"
            f"👇 Quyidagi tugmani bosib to'lovni amalga oshiring.",
            parse_mode="HTML",
            reply_markup=_auto_pay_kb(make_uzum_url(amount, invoice_id)),
        )


# ── CHEKNI QABUL QILISH ───────────────────────────────────────────

@router.message(TopUpStates.waiting_for_payment_proof)
async def receive_payment_proof(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    proof_ask_msg_id = data.get("proof_ask_msg_id")

    if not (message.photo or message.document):
        await safe_delete(bot, message.chat.id, message.message_id)
        await message.answer(
            "❌ Iltimos, to'lov chekini <b>rasm</b> ko'rinishida yuboring!\n\n"
            "Screenshot olib yuboring 📸",
            parse_mode="HTML",
        )
        return

    amount     = data.get("amount", 0)
    invoice_id = data.get("invoice_id", "N/A")
    user       = message.from_user

    caption = (
        f"💰 <b>Yangi to'lov so'rovi! (HUMO)</b>\n\n"
        f"👤 {user.full_name}"
        f"{' (@' + user.username + ')' if user.username else ''}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"💵 Summa: <b>{amount:,} so'm</b>\n"
        f"🧾 Invoice: <code>{invoice_id}</code>"
    )

    for admin_id in settings.admin_ids_list:
        try:
            kb = _admin_payment_kb(user.id, amount, invoice_id)
            if message.photo:
                await bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            elif message.document:
                await bot.send_document(
                    admin_id,
                    message.document.file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
        except Exception as e:
            logger.error(f"Admin {admin_id} ga xabar yuborishda xato: {e}")

    await delete_messages(bot, message.chat.id, [
        message.message_id, proof_ask_msg_id
    ])

    await message.answer(
        f"✅ <b>Chek muvaffaqiyatli yuborildi!</b>\n\n"
        f"💵 Summa: <b>{amount:,} so'm</b>\n"
        f"🧾 Invoice: <code>{invoice_id}</code>\n\n"
        f"⏳ Admin <b>5–15 daqiqa</b> ichida hisobingizga qo'shadi!\n"
        f"📲 Tasdiqlangach sizga xabar keladi.",
        parse_mode="HTML",
        reply_markup=get_main_menu(),
    )
    await state.clear()


# ══════════════════════════════════════════════════════════════════
# ✅ ADMIN: TASDIQLASH
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("payadm_yes_"))
async def admin_confirm_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in settings.admin_ids_list:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    parts      = callback.data.split("_")
    user_id    = int(parts[2])
    amount     = int(parts[3])
    invoice_id = parts[4]

    await update_user_balance(user_id, amount, add=True)
    await log_transaction(
        user_id, amount, "deposit",
        f"To'lov tasdiqlandi. Invoice: {invoice_id}"
    )

    try:
        user_db = await get_user(user_id)
        if not isinstance(user_db, dict):
            user_db = dict(user_db)
        await bot.send_message(
            user_id,
            f"🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
            f"💰 <b>+{amount:,} so'm</b> hisobingizga qo'shildi!\n"
            f"💳 Joriy balans: <b>{user_db['balance']:,.0f} so'm</b>\n\n"
            f"🛒 Xizmatlardan foydalanishingiz mumkin!",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Foydalanuvchi {user_id} ga xabar yuborishda xato: {e}")

    try:
        old_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=old_caption + (
                f"\n\n✅ <b>TASDIQLANDI</b>\n"
                f"👤 @{callback.from_user.username or callback.from_user.id}"
            ),
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer(f"✅ {amount:,} so'm tasdiqlandi!", show_alert=True)


# ══════════════════════════════════════════════════════════════════
# ❌ ADMIN: RAD ETISH
# ══════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("payadm_no_"))
async def admin_reject_payment(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id not in settings.admin_ids_list:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    parts      = callback.data.split("_")
    user_id    = int(parts[2])
    invoice_id = parts[3]

    try:
        await bot.send_message(
            user_id,
            f"❌ <b>To'lovingiz rad etildi.</b>\n\n"
            f"🧾 Invoice: <code>{invoice_id}</code>\n\n"
            f"Muammo bo'lsa 🆘 Yordam bo'limiga murojaat qiling.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Foydalanuvchi {user_id} ga xabar yuborishda xato: {e}")

    try:
        old_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=old_caption + (
                f"\n\n❌ <b>RAD ETILDI</b>\n"
                f"👤 @{callback.from_user.username or callback.from_user.id}"
            ),
            parse_mode="HTML",
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.answer("❌ Rad etildi!", show_alert=True)


# ══════════════════════════════════════════════════════════════════
# 💰 PUL ISHLASH
# ══════════════════════════════════════════════════════════════════

@router.message(F.text == "💰 Pul ishlash")
async def earn_money(message: Message, bot: Bot):
    await _send_earn_menu(message, message.from_user.id, bot)


async def _send_earn_menu(message: Message, user_id: int, bot: Bot):
    bot_info  = await bot.get_me()
    ref_link  = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    referrals = await get_referral_count(user_id)
    can_bonus = await can_claim_daily_bonus(user_id)

    if can_bonus:
        bonus_status = "✅ Bugun olish mumkin!"
    else:
        bonus_status = "⏳ Keyingi bonus 24 soatdan so'ng"

    await message.answer(
        f"💰 <b>Pul ishlash usullari</b>\n\n"
        f"👥 <b>Referal tizimi</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Har bir taklif uchun: <b>{settings.REFERRAL_BONUS_AMOUNT:,} so'm</b>\n"
        f"Sizning referallaringiz: <b>{referrals} ta</b>\n"
        f"🔗 Havola:\n<code>{ref_link}</code>\n\n"
        f"🎁 <b>Kunlik bonus</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Har 24 soatda: <b>{settings.DAILY_BONUS_AMOUNT:,} so'm</b>\n"
        f"{bonus_status}\n\n"
        f"🎟 <b>Promo kod</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Maxsus kod orqali bonus oling",
        parse_mode="HTML",
        reply_markup=_earn_kb(can_bonus),
    )


@router.callback_query(F.data == "noop_bonus")
async def noop_bonus(callback: CallbackQuery):
    await callback.answer(
        "⏳ Siz bugun allaqachon bonus oldingiz!\n24 soatdan so'ng qayta urinib ko'ring.",
        show_alert=True,
    )


@router.callback_query(F.data == "daily_bonus")
async def claim_daily_bonus(callback: CallbackQuery, bot: Bot):
    can = await can_claim_daily_bonus(callback.from_user.id)
    if not can:
        await callback.answer(
            "⏳ Siz bugun allaqachon bonus oldingiz!\n24 soatdan so'ng qayta urinib ko'ring.",
            show_alert=True,
        )
        return

    amount = settings.DAILY_BONUS_AMOUNT
    await update_user_balance(callback.from_user.id, amount, add=True)
    await log_daily_bonus(callback.from_user.id)
    await log_transaction(callback.from_user.id, amount, "bonus", "Kunlik bonus")

    user = await get_user(callback.from_user.id)
    if not isinstance(user, dict):
        user = dict(user)

    await safe_delete(bot, callback.message.chat.id, callback.message.message_id)
    await callback.message.answer(
        f"🎉 <b>Kunlik bonus olindi!</b>\n\n"
        f"💰 +<b>{amount:,} so'm</b> qo'shildi\n"
        f"💳 Joriy balans: <b>{user['balance']:,.0f} so'm</b>",
        parse_mode="HTML",
    )
    await callback.answer("✅ Bonus olindi!")
    await _send_earn_menu(callback.message, callback.from_user.id, bot)


@router.callback_query(F.data == "show_ref_link")
async def show_ref_link(callback: CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    await callback.answer(
        f"🔗 Sizning referal havolangiz:\n{ref_link}",
        show_alert=True,
    )


@router.callback_query(F.data == "enter_promo")
async def enter_promo_cb(callback: CallbackQuery, state: FSMContext):
    await safe_delete(callback.bot, callback.message.chat.id, callback.message.message_id)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_promo"))

    sent = await callback.message.answer(
        "🎟 <b>Promo kodni kiriting:</b>\n\n"
        "Masalan: <code>SMM2025</code>",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await state.update_data(promo_ask_msg_id=sent.message_id)
    await state.set_state(EarnStates.waiting_for_promo)
    await callback.answer()


@router.callback_query(F.data == "cancel_promo")
async def cancel_promo_cb(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await safe_delete(bot, callback.message.chat.id, callback.message.message_id)
    await callback.message.answer("❌ Bekor qilindi.", reply_markup=get_main_menu())
    await callback.answer()


@router.message(EarnStates.waiting_for_promo)
async def process_promo_code(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    promo_ask_msg_id = data.get("promo_ask_msg_id")

    code  = message.text.strip().upper()
    promo = await get_promo(code)

    await delete_messages(bot, message.chat.id, [
        message.message_id, promo_ask_msg_id
    ])

    if not promo:
        await message.answer(
            "❌ <b>Bunday promo kod mavjud emas</b> yoki faol emas!\n\n"
            "Kodni to'g'ri kiritganingizni tekshiring.",
            parse_mode="HTML",
            reply_markup=get_main_menu(),
        )
        await state.clear()
        return

    if not isinstance(promo, dict):
        promo = dict(promo)

    already = await has_user_used_promo(message.from_user.id, promo["id"])
    if already:
        await message.answer(
            "❌ Siz bu promo kodni <b>allaqachon ishlatgansiz!</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu(),
        )
        await state.clear()
        return

    success = await redeem_promo(message.from_user.id, promo["id"])
    if success:
        amount = promo["amount"]
        await update_user_balance(message.from_user.id, amount, add=True)
        await log_transaction(
            message.from_user.id, amount, "bonus", f"Promo kod: {code}"
        )
        user = await get_user(message.from_user.id)
        if not isinstance(user, dict):
            user = dict(user)
        await message.answer(
            f"✅ <b>Promo kod qabul qilindi!</b>\n\n"
            f"🎟 Kod: <code>{code}</code>\n"
            f"💰 +<b>{amount:,.0f} so'm</b> qo'shildi\n"
            f"💳 Joriy balans: <b>{user['balance']:,.0f} so'm</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu(),
        )
    else:
        await message.answer(
            "❌ Xatolik yuz berdi yoki promo kod limiti tugagan.",
            reply_markup=get_main_menu(),
        )
    await state.clear()


# ══════════════════════════════════════════════════════════════════
# 🤝 HAMKORLIK
# ══════════════════════════════════════════════════════════════════

@router.message(F.text == "🤝 Hamkorlik")
async def partnership(message: Message, bot: Bot):
    bot_info = await bot.get_me()
    api_key  = f"USR{message.from_user.id}KEY"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📋 API kalitni nusxalash",
        callback_data="copy_api_key",
    ))

    await message.answer(
        f"🤝 <b>Hamkorlik (API)</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Base URL:\n"
        f"<code>https://t.me/{bot_info.username}</code>\n\n"
        f"🔑 API kalitingiz:\n"
        f"<code>{api_key}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📖 <b>API metodlari:</b>\n"
        f"• <code>GET /balance</code> — Balans\n"
        f"• <code>POST /order</code> — Buyurtma\n"
        f"• <code>GET /status/{{id}}</code> — Holat\n"
        f"• <code>GET /services</code> — Xizmatlar\n\n"
        f"📩 Batafsil: @ar1k_bro",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "copy_api_key")
async def copy_api_key_cb(callback: CallbackQuery):
    api_key = f"USR{callback.from_user.id}KEY"
    await callback.answer(f"🔑 API kalitingiz:\n{api_key}", show_alert=True)