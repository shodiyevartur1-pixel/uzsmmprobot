from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_subscribe_keyboard(channels: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for channel in channels:
        display = channel if channel.startswith("@") else f"Kanal {channels.index(channel)+1}"
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


def get_categories_keyboard(categories: List[dict]) -> InlineKeyboardMarkup:
    """categories: [{'id': ..., 'name': ...}, ...]"""
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


def get_services_keyboard(services: List[dict], category_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for svc in services[:20]:  # limit to 20 per page
        builder.row(
            InlineKeyboardButton(
                text=f"{svc['name'][:40]} | {svc['rate']} so'm/1000",
                callback_data=f"svc_{svc['service']}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"back_cat_{category_id}")
    )
    return builder.as_markup()


def get_confirm_order_keyboard(order_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_order_{order_data}"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_order"),
    )
    return builder.as_markup()


def get_countries_keyboard(countries: List[dict], page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    per_page = 10
    start = page * per_page
    for country in countries[start:start + per_page]:
        builder.row(
            InlineKeyboardButton(
                text=f"{country['flag']} {country['name']}",
                callback_data=f"country_{country['code']}",
            )
        )
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"countries_page_{page-1}")
        )
    if start + per_page < len(countries):
        nav_buttons.append(
            InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"countries_page_{page+1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main"))
    return builder.as_markup()


def get_order_actions_keyboard(order_id: int, api_order_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔄 Holat tekshirish",
            callback_data=f"check_order_{order_id}",
        )
    )
    builder.row(InlineKeyboardButton(text="🔙 Buyurtmalarim", callback_data="my_orders"))
    return builder.as_markup()


def get_topup_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Payme orqali", callback_data="topup_payme"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 Click orqali", callback_data="topup_click"),
    )
    builder.row(
        InlineKeyboardButton(text="🏦 Admin orqali (Manual)", callback_data="topup_manual"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main"))
    return builder.as_markup()


def get_admin_user_actions(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ban_text = "✅ Banldan chiqarish" if is_banned else "🚫 Banlash"
    ban_cb = f"unban_{user_id}" if is_banned else f"ban_{user_id}"
    builder.row(
        InlineKeyboardButton(text="➕ Balans qo'shish", callback_data=f"add_bal_{user_id}"),
        InlineKeyboardButton(text="➖ Balans ayirish", callback_data=f"sub_bal_{user_id}"),
    )
    builder.row(InlineKeyboardButton(text=ban_text, callback_data=ban_cb))
    builder.row(InlineKeyboardButton(text="📨 Xabar yuborish", callback_data=f"msg_user_{user_id}"))
    return builder.as_markup()


def get_support_reply_keyboard(ticket_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💬 Javob berish", callback_data=f"reply_ticket_{ticket_id}_{user_id}"
        ),
        InlineKeyboardButton(
            text="✅ Yopish", callback_data=f"close_ticket_{ticket_id}"
        ),
    )
    return builder.as_markup()