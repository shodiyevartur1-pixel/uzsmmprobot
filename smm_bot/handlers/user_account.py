import logging
import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import settings
from database.db_queries import (
    get_user, get_referral_count, get_user_orders,
    can_claim_daily_bonus, log_daily_bonus, update_user_balance,
    log_transaction, get_promo, redeem_promo, has_user_used_promo
)
from keyboards.inline_kb import (
    get_topup_keyboard,
    get_topup_amount_keyboard,
    get_payment_confirm_keyboard,
)
from keyboards.reply_kb import get_main_menu, get_cancel_button
from states.user_states import EarnStates, TopUpStates

logger = logging.getLogger(__name__)
router = Router()

# To'lov usuli nomlari (xabar matni uchun)
METHOD_LABELS = {
    "click":  ("🔹", "Click [Avto]"),
    "uzum":   ("🍇", "Uzum [Avto]"),
    "paynet": ("🟢", "Paynet [Avto]"),
}


# ── HISOBIM ──────────────────────────────────────────────────────
@router.message(F.text == "👤 Hisobim")
async def my_account(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user:
        return

    referrals = await get_referral_count(message.from_user.id)
    orders    = await get_user_orders(message.from_user.id, limit=1000)
    bot_info  = await bot.get_me()
    ref_link  = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"

    text = (
        f"👤 <b>Mening hisobim</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"👤 Ism: {user['full_name']}\n"
        f"─────────────────\n"
        f"💰 Balans: <b>{user['balance']:,.0f} so'm</b>\n"
        f"💸 Jami sarflangan: <b>{user['total_spent']:,.0f} so'm</b>\n"
        f"📦 Buyurtmalar: <b>{len(orders)} ta</b>\n"
        f"👥 Referallar: <b>{referrals} ta</b>\n"
        f"─────────────────\n"
        f"🔗 <b>Referal havola:</b>\n<code>{ref_link}</code>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Hisob to'ldirish",    callback_data="topup_quick"))
    builder.row(InlineKeyboardButton(text="📊 Operatsiyalar tarixi", callback_data="history_menu"))

    await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())


# ── HISOB TO'LDIRISH — 1-QADAM: usul tanlash ────────────────────
@router.message(F.text == "💳 Hisob To'ldirish")
async def topup_menu(message: Message):
    await _send_topup_menu(message, message.from_user.id)


@router.callback_query(F.data == "topup_quick")
async def topup_quick(callback: CallbackQuery):
    await _send_topup_menu(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "topup_back")
async def topup_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _send_topup_menu(callback.message, callback.from_user.id)
    await callback.answer()


async def _send_topup_menu(message: Message, user_id: int):
    """Asosiy to'lov usullari menyusi."""
    await message.answer(
        f"💳 <b>Hisob To'ldirish</b>\n"
        f"👤 ID raqam: <code>{user_id}</code>\n\n"
        f"To'lov usulini tanlang:",
        parse_mode="HTML",
        reply_markup=get_topup_keyboard(),
    )


# ── HISOB TO'LDIRISH — 2-QADAM: miqdor so'rash (avto usullar) ───
@router.callback_query(F.data.in_({"topup_click", "topup_uzum", "topup_paynet"}))
async def topup_auto_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.replace("topup_", "")          # click | uzum | paynet
    emoji, name = METHOD_LABELS[method]

    await state.update_data(method=method)
    await state.set_state(TopUpStates.waiting_for_amount)

    await callback.message.answer(
        f"💵 <b>Balansizni necha so'mga to'ldirmoqchisiz?</b>\n"
        f"📰 Minimal miqdor: <b>1 000 so'm</b>",
        parse_mode="HTML",
        reply_markup=get_topup_amount_keyboard(back_cb="topup_back"),
    )
    await callback.answer()


# ── HISOB TO'LDIRISH — 3-QADAM: miqdor kiritildi (avto) ─────────
@router.message(TopUpStates.waiting_for_amount)
async def process_topup_amount(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_menu())
        return

    try:
        amount = int(message.text.replace(" ", "").replace(",", "").replace(".", ""))
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting! Masalan: <b>50000</b>", parse_mode="HTML")
        return

    if amount < 1000:
        await message.answer("❌ Minimal miqdor: <b>1 000 so'm</b>", parse_mode="HTML")
        return

    data   = await state.get_data()
    method = data.get("method", "click")
    emoji, name = METHOD_LABELS.get(method, ("💳", method))

    # Unikal invoice ID
    invoice_id = f"{method.upper()}-{message.from_user.id}-{int(time.time())}"
    await state.update_data(amount=amount, invoice_id=invoice_id)
    await state.set_state(TopUpStates.waiting_for_payment_proof)

    # ── To'lov yo'riqnomasi ──────────────────────────────────────
    # pay_url — agar Click/Uzum/Paynet API integratsiyangiz bo'lsa
    # shu yerga to'lov havolasini qo'ying, yo'q bo'lsa None qoldiring.
    pay_url = None  # TODO: payment_api dan havola olish

    await message.answer(
        f"{emoji} <b>{name}</b> - qo'llanmasi.\n\n"
        f"⚠️ To'lov to'langandan keyin bot balansiga avtomatik tashlab beriladi.\n"
        f"💳 To'lov miqdori: <b>{amount:,} so'm</b>".replace(",", " "),
        parse_mode="HTML",
        reply_markup=get_payment_confirm_keyboard(method, invoice_id, pay_url),
    )


# ── ADMIN ORQALI TO'LDIRISH ───────────────────────────────────────
@router.callback_query(F.data == "topup_manual")
async def topup_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TopUpStates.waiting_for_amount)
    await state.update_data(method="manual")

    await callback.message.answer(
        "🏦 <b>Admin orqali to'ldirish</b>\n\n"
        f"To'ldirmoqchi bo'lgan summani kiriting (so'mda):\n"
        f"📰 Minimal: <b>{settings.MIN_DEPOSIT:,} so'm</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_button(),
    )
    await callback.answer()


# ── TO'LOV TEKSHIRISH (avto usullar uchun) ───────────────────────
@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery, state: FSMContext):
    # Masalan: check_payment_click_CLICK-123-1234567890
    parts      = callback.data.split("_", 3)   # ['check', 'payment', 'click', 'CLICK-...']
    method     = parts[2] if len(parts) > 2 else "?"
    invoice_id = parts[3] if len(parts) > 3 else "?"

    # TODO: payment_api orqali haqiqiy tekshirish
    # Hozircha foydalanuvchiga kutish xabari
    await callback.answer(
        "⏳ To'lov tekshirilmoqda... Iltimos bir oz kuting.",
        show_alert=True,
    )


# ── CHEK YUBORISH (manual to'lov uchun) ──────────────────────────
@router.message(TopUpStates.waiting_for_payment_proof)
async def process_payment_proof(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_menu())
        return

    data       = await state.get_data()
    amount     = data.get("amount", 0)
    invoice_id = data.get("invoice_id", "N/A")
    user       = message.from_user

    caption = (
        f"🆕 <b>Yangi to'lov so'rovi!</b>\n\n"
        f"🆔 So'rov ID: <code>{invoice_id}</code>\n"
        f"─────────────────\n"
        f"👤 Foydalanuvchi: {user.full_name} (@{user.username})\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"💰 Summa: <b>{amount:,} so'm</b>\n"
        f"─────────────────\n"
        f"✅ Tasdiqlash: <code>/addbalance_{user.id}_{amount}</code>\n"
        f"❌ Rad etish: <code>/reject_{user.id}_{invoice_id}</code>"
    )

    for admin_id in settings.admin_ids_list:
        try:
            if message.photo:
                await bot.send_photo(admin_id, message.photo[-1].file_id,
                                     caption=caption, parse_mode="HTML")
            elif message.document:
                await bot.send_document(admin_id, message.document.file_id,
                                        caption=caption, parse_mode="HTML")
            else:
                await bot.send_message(admin_id,
                                       caption + f"\n\n📝 Xabar: {message.text}",
                                       parse_mode="HTML")
        except Exception as e:
            logger.error(f"Adminga xabar yuborishda xato: {e}")

    await message.answer(
        "✅ <b>So'rovingiz qabul qilindi!</b>\n\n"
        f"🆔 So'rov ID: <code>{invoice_id}</code>\n"
        "⏱ Admin tekshirib, 5-20 daqiqa ichida hisobingizga qo'shadi.",
        parse_mode="HTML",
        reply_markup=get_main_menu(),
    )
    await state.clear()


# ── PUL ISHLASH ──────────────────────────────────────────────────
@router.message(F.text == "💰 Pul ishlash")
async def earn_money(message: Message, bot: Bot):
    bot_info  = await bot.get_me()
    ref_link  = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    referrals = await get_referral_count(message.from_user.id)
    can_bonus = await can_claim_daily_bonus(message.from_user.id)

    bonus_btn_text = "✅ Kunlik bonus olindi" if not can_bonus else "🎃 Kunlik bonus olish"

    await message.answer(
        f"💰 <b>Pul ishlash usullari</b>\n\n"
        f"👥 <b>Referal tizimi</b>\n"
        f"Har bir do'stingiz uchun: <b>{settings.REFERRAL_BONUS_AMOUNT:,} so'm</b>\n"
        f"Sizning referallaringiz: <b>{referrals} ta</b>\n"
        f"🔗 Havola: <code>{ref_link}</code>\n\n"
        f"🎃 <b>Kunlik bonus</b>: {settings.DAILY_BONUS_AMOUNT:,} so'm\n"
        f"🎟 <b>Promo kod</b>: Maxsus kodlar orqali bonus oling",
        parse_mode="HTML",
        reply_markup=_earn_keyboard(bonus_btn_text),
    )


def _earn_keyboard(bonus_text: str):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=bonus_text,                    callback_data="daily_bonus"))
    builder.row(InlineKeyboardButton(text="🎟 Promo kod kiritish",       callback_data="enter_promo"))
    builder.row(InlineKeyboardButton(text="📋 Referal havolani nusxalash", callback_data="copy_ref_link"))
    return builder.as_markup()


@router.callback_query(F.data == "copy_ref_link")
async def copy_ref_link(callback: CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    await callback.answer(ref_link, show_alert=True)


@router.callback_query(F.data == "daily_bonus")
async def claim_daily_bonus(callback: CallbackQuery):
    can = await can_claim_daily_bonus(callback.from_user.id)
    if not can:
        await callback.answer(
            "⏱ Siz bugun allaqachon bonus oldingiz! 24 soatdan so'ng qayta urinib ko'ring.",
            show_alert=True,
        )
        return

    amount = settings.DAILY_BONUS_AMOUNT
    await update_user_balance(callback.from_user.id, amount, add=True)
    await log_daily_bonus(callback.from_user.id)
    await log_transaction(callback.from_user.id, amount, "bonus", "Kunlik bonus")
    user = await get_user(callback.from_user.id)

    await callback.message.answer(
        f"🎉 <b>Kunlik bonus muvaffaqiyatli olindi!</b>\n\n"
        f"💰 +{amount:,} so'm qo'shildi\n"
        f"💳 Joriy balans: <b>{user['balance']:,.0f} so'm</b>",
        parse_mode="HTML",
    )
    await earn_money(callback.message, callback.bot)


@router.callback_query(F.data == "enter_promo")
async def enter_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🎟 <b>Promo kodni kiriting:</b>\n\nMasalan: SMM2024",
        reply_markup=get_cancel_button(),
    )
    await state.set_state(EarnStates.waiting_for_promo)
    await callback.answer()


@router.message(EarnStates.waiting_for_promo)
async def process_promo(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_menu())
        return

    code  = message.text.strip().upper()
    promo = await get_promo(code)

    if not promo:
        await message.answer("❌ Bunday promo kod mavjud emas yoki faol emas!")
        return

    already_used = await has_user_used_promo(message.from_user.id, promo["id"])
    if already_used:
        await message.answer("❌ Siz bu promo kodni allaqachon ishlatgansiz!")
        return

    success = await redeem_promo(message.from_user.id, promo["id"])
    if success:
        amount = promo["amount"]
        await update_user_balance(message.from_user.id, amount, add=True)
        await log_transaction(message.from_user.id, amount, "bonus", f"Promo kod: {code}")
        user = await get_user(message.from_user.id)
        await message.answer(
            f"✅ <b>Promo kod qabul qilindi!</b>\n\n"
            f"🎟 Kod: <code>{code}</code>\n"
            f"💰 +{amount:,.0f} so'm qo'shildi\n"
            f"💳 Joriy balans: <b>{user['balance']:,.0f} so'm</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu(),
        )
    else:
        await message.answer("❌ Xatolik yuz berdi yoki promo kod limiti tugagan.")

    await state.clear()


# ── TARIX ────────────────────────────────────────────────────────
@router.callback_query(F.data == "history_menu")
async def history_menu(callback: CallbackQuery):
    await callback.message.answer(
        "📊 <b>Operatsiyalar tarixi</b>\n\n"
        "Hozircha hech qanday operatsiya mavjud emas.\n"
        "Tez orada to'liq tarix funksiyasi qo'shiladi!",
        parse_mode="HTML",
    )
    await callback.answer()


# ── HAMKORLIK ────────────────────────────────────────────────────
@router.message(F.text == "🤝 Hamkorlik")
async def partnership(message: Message):
    pass


@router.callback_query(F.data == "copy_api_key")
async def copy_api_key(callback: CallbackQuery):
    api_key = f"USR_{callback.from_user.id}_KEY_{hash(str(callback.from_user.id))}"
    await callback.answer(api_key, show_alert=True)


# ── NOOP ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()