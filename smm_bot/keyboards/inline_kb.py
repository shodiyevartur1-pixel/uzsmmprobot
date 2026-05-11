from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ══════════════════════════════════════════════════════════════════
# OBUNA
# ══════════════════════════════════════════════════════════════════

def get_subscribe_keyboard(channels: List[str]) -> InlineKeyboardMarkup:
    """Majburiy obuna klaviaturasi."""
    builder = InlineKeyboardBuilder()
    for i, channel in enumerate(channels, start=1):
        display = channel if channel.startswith("@") else f"Kanal {i}"
        builder.row(
            InlineKeyboardButton(
                text=f"📢 {display} ga o'tish",
                url=f"https://t.me/{channel.lstrip('@')}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscribe")
    )
    return builder.as_markup()


def get_check_subscribe_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscribe")
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# KATEGORIYALAR
# ══════════════════════════════════════════════════════════════════

def get_categories_keyboard(categories: List[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(
            InlineKeyboardButton(
                text=cat["name"],
                callback_data=f"cat_{cat['id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main"))
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# XIZMATLAR
# ══════════════════════════════════════════════════════════════════

def get_services_keyboard(
    services: List[dict],
    category_id: str,
    page: int = 0,
    per_page: int = 10,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * per_page
    chunk = services[start: start + per_page]

    for svc in chunk:
        builder.row(
            InlineKeyboardButton(
                text=f"{svc['name'][:40]} | {svc['rate']} so'm/1000",
                callback_data=f"svc_{svc['service']}",
            )
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️", callback_data=f"svc_page_{category_id}_{page - 1}"
        ))
    if start + per_page < len(services):
        nav.append(InlineKeyboardButton(
            text="▶️", callback_data=f"svc_page_{category_id}_{page + 1}"
        ))
    if nav:
        builder.row(*nav)

    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"back_cat_{category_id}")
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# BUYURTMA
# ══════════════════════════════════════════════════════════════════

def get_confirm_order_keyboard(order_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data=f"confirm_order_{order_data}",
        ),
        InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_order"),
    )
    return builder.as_markup()


def get_order_actions_keyboard(order_id: int, api_order_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔄 Holat tekshirish",
            callback_data=f"check_order_{order_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Buyurtmalarim", callback_data="my_orders")
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# MAMLAKATLAR
# ══════════════════════════════════════════════════════════════════

def get_countries_keyboard(
    countries: List[dict],
    page: int = 0,
    per_page: int = 10,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * per_page

    for country in countries[start: start + per_page]:
        builder.row(
            InlineKeyboardButton(
                text=f"{country['flag']} {country['name']}",
                callback_data=f"country_{country['code']}",
            )
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️ Oldingi", callback_data=f"countries_page_{page - 1}"
        ))
    if start + per_page < len(countries):
        nav.append(InlineKeyboardButton(
            text="Keyingi ▶️", callback_data=f"countries_page_{page + 1}"
        ))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main"))
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# TO'LDIRISH (TOPUP)
# ══════════════════════════════════════════════════════════════════

def get_topup_keyboard() -> InlineKeyboardMarkup:
    """
    Tugmalar:
      🔹 Click [Avto]   🍇 Uzum [Avto]
      🟢 Paynet [Avto]
      ☎️ Admin orqali [5-20 daqiqada]
      🔙 Orqaga
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔹 Click [Avto]",               callback_data="topup_click"),
        InlineKeyboardButton(text="🍇 Uzum [Avto]",                callback_data="topup_uzum"),
    )
    builder.row(
        InlineKeyboardButton(text="🟢 Paynet [Avto]",              callback_data="topup_paynet"),
    )
    builder.row(
        InlineKeyboardButton(text="☎️ Admin orqali [5-20 daqiqada]", callback_data="topup_manual"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga",                     callback_data="back_main"),
    )
    return builder.as_markup()


def get_topup_amount_keyboard(back_cb: str = "topup_back") -> InlineKeyboardMarkup:
    """Foydalanuvchi miqdorni matn yozib yuboradi. Faqat Orqaga tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=back_cb))
    return builder.as_markup()


def get_payment_confirm_keyboard(
    payment_method: str,
    invoice_id: str,
    pay_url: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """
    To'lov havolasi + tekshirish + bekor qilish.
    payment_method: 'click' | 'uzum' | 'paynet'
    """
    builder = InlineKeyboardBuilder()

    labels = {
        "click":  "🔹 Click orqali to'lash",
        "uzum":   "🍇 Uzum orqali to'lash",
        "paynet": "🟢 Paynet orqali to'lash",
    }

    if pay_url:
        builder.row(
            InlineKeyboardButton(
                text=labels.get(payment_method, "💰 To'lash"),
                url=pay_url,
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="✅ To'lovni tekshirish",
            callback_data=f"check_payment_{payment_method}_{invoice_id}",
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="topup_back")
    )
    return builder.as_markup()


# ══════════════════════════════════════════════════════════════════
# ADMIN PANELI
# ══════════════════════════════════════════════════════════════════

def get_admin_user_actions(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ban_text = "✅ Banldan chiqarish" if is_banned else "🚫 Banlash"
    ban_cb   = f"unban_{user_id}" if is_banned else f"ban_{user_id}"
    builder.row(
        InlineKeyboardButton(text="➕ Balans qo'shish", callback_data=f"add_bal_{user_id}"),
        InlineKeyboardButton(text="➖ Balans ayirish",  callback_data=f"sub_bal_{user_id}"),
    )
    builder.row(InlineKeyboardButton(text=ban_text, callback_data=ban_cb))
    builder.row(
        InlineKeyboardButton(text="📨 Xabar yuborish", callback_data=f"msg_user_{user_id}")
    )
    return builder.as_markup()


def get_support_reply_keyboard(ticket_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💬 Javob berish",
            callback_data=f"reply_ticket_{ticket_id}_{user_id}",
        ),
        InlineKeyboardButton(
            text="✅ Yopish", callback_data=f"close_ticket_{ticket_id}"
        ),
    )
    return builder.as_markup()