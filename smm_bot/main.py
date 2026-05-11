import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.db_setup import init_db
from handlers.user_start import router as start_router
from handlers.user_services import router as services_router
from handlers.user_account import router as account_router
from handlers.user_support import router as support_router
from handlers.user_orders import router as orders_router
from handlers.admin_panel import router as admin_router
from handlers.user_numbers import router as numbers_router

# BU YERDAGI dp.include_router(numbers_router) OCHIRIB TASHLANDI!

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 Bot ishga tushmoqda...")
    await init_db()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Barcha routerlarni shu yerga, dp yaratilganidan keyin yozamiz:
    dp.include_router(admin_router)
    dp.include_router(start_router)
    dp.include_router(services_router)
    dp.include_router(account_router)
    dp.include_router(support_router)
    dp.include_router(orders_router)
    dp.include_router(numbers_router)  # <--- SHU YERGA QO'SHDIK!

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())