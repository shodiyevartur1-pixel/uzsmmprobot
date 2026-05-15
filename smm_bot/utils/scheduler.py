import asyncio
import logging
import aiohttp
from aiogram import Bot

from config import settings
from database.db_queries import get_all_orders, update_order_status, update_user_balance, log_transaction

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 300  # har 5 daqiqada

STATUS_MAP = {
    "Pending":    "pending",
    "Processing": "processing",
    "In progress": "processing",
    "Completed":  "completed",
    "Canceled":   "cancelled",
    "Cancelled":  "cancelled",
    "Partial":    "partial",
}

STATUS_MSG = {
    "completed":  "✅ <b>Buyurtmangiz bajarildi!</b>",
    "cancelled":  "❌ <b>Buyurtmangiz bekor qilindi!</b>",
    "partial":    "♻️ <b>Buyurtmangiz qisman bajarildi!</b>",
}


async def check_order_status(session: aiohttp.ClientSession, api_order_id: str) -> str | None:
    """Peakerr dan buyurtma holatini oladi."""
    try:
        async with session.post(
            settings.SMM_API_URL,
            data={
                "key":    settings.SMM_API_KEY,
                "action": "status",
                "order":  api_order_id,
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            data = await resp.json()
            raw_status = data.get("status", "")
            return STATUS_MAP.get(raw_status)
    except Exception as e:
        logger.error(f"Status tekshirishda xato (order {api_order_id}): {e}")
        return None


async def notify_user(bot: Bot, order: dict, new_status: str):
    """Foydalanuvchiga xabar yuboradi."""
    msg = STATUS_MSG.get(new_status)
    if not msg:
        return

    charge = float(order.get("charge", 0) or 0)
    refund_text = ""

    # Bekor qilinsa — pulni qaytaramiz
    if new_status == "cancelled" and charge > 0:
        await update_user_balance(order["user_id"], charge, add=True)
        await log_transaction(
            order["user_id"], charge, "refund",
            f"Qaytarish — #{order['id']}: {order.get('service_name','')}"
        )
        refund_text = f"\n💸 <b>{charge:,.0f} so'm</b> balansga qaytarildi."

    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"{msg}\n\n"
                f"🆔 Buyurtma: <b>#{order['id']}</b>\n"
                f"🛍 Xizmat: <b>{order.get('service_name', '')}</b>\n"
                f"📊 Miqdor: <b>{int(order.get('quantity', 0)):,} ta</b>\n"
                f"💰 To'langan: <b>{charge:,.0f} so'm</b>"
                f"{refund_text}"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Foydalanuvchiga xabar yuborishda xato: {e}")


async def run_scheduler(bot: Bot):
    """Asosiy scheduler loop — har 5 daqiqada ishlaydi."""
    logger.info("✅ Scheduler ishga tushdi")

    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        try:
            # Faqat processing va pending + api_order_id bor buyurtmalar
            orders = await get_all_orders(status="processing", limit=100)
            pending = await get_all_orders(status="pending", limit=100)
            all_orders = list(orders) + list(pending)

            if not all_orders:
                continue

            logger.info(f"🔍 {len(all_orders)} ta buyurtma tekshirilmoqda...")

            async with aiohttp.ClientSession() as session:
                for order in all_orders:
                    if not isinstance(order, dict):
                        order = dict(order)

                    api_order_id = order.get("api_order_id")
                    if not api_order_id:
                        continue

                    new_status = await check_order_status(session, str(api_order_id))
                    if not new_status:
                        continue

                    current_status = order.get("status", "pending")
                    if new_status == current_status:
                        continue

                    # Statusni yangilash
                    await update_order_status(order["id"], new_status)
                    logger.info(f"📦 #{order['id']} → {new_status}")

                    # Foydalanuvchiga xabar
                    await notify_user(bot, order, new_status)

                    # So'rovlar orasida kichik pauza
                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Scheduler xatosi: {e}")