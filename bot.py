"""
Telegram бот для знакомств
Главный файл запуска
"""
import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from database import Database
from handlers import profile_router, matching_router, payments_router


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Загружаем конфигурацию
    bot_config, db_config = load_config()
    
    # Создаем директорию для БД если её нет
    db_path = Path(db_config.path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Инициализируем базу данных
    db = Database(db_config.path)
    await db.connect()
    logger.info("База данных подключена")
    
    # Создаем бота и диспетчер
    bot = Bot(
        token=bot_config.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем роутеры
    dp.include_router(profile_router)
    dp.include_router(matching_router)
    dp.include_router(payments_router)
    
    # Middleware для передачи зависимостей
    @dp.message.middleware()
    @dp.callback_query.middleware()
    async def inject_dependencies(handler, event, data):
        data["db"] = db
        data["config"] = bot_config
        return await handler(event, data)
    
    @dp.pre_checkout_query.middleware()
    async def inject_db_pre_checkout(handler, event, data):
        data["db"] = db
        data["config"] = bot_config
        return await handler(event, data)
    
    try:
        logger.info("Бот запущен!")
        # Удаляем вебхук и начинаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.disconnect()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
