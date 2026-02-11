"""
Конфигурация бота для знакомств
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Настройки бота"""
    token: str
    admin_ids: list[int]
    
    # Лимиты просмотров
    daily_views_limit: int = 20
    views_reset_cost: int = 50  # Стоимость сброса в звездах
    extra_views_cost: int = 10  # Стоимость доп. просмотров в звездах
    extra_views_amount: int = 10  # Количество доп. просмотров
    
    # Настройки медиа
    max_photos: int = 5
    max_video_duration: int = 15  # секунд
    max_bio_length: int = 500


@dataclass
class DatabaseConfig:
    """Настройки базы данных"""
    path: str = "database/dating_bot.db"


# Загрузка конфигурации
def load_config() -> tuple[BotConfig, DatabaseConfig]:
    """Загружает конфигурацию из переменных окружения"""
    bot_config = BotConfig(
        token=os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"),
        admin_ids=[int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id],
    )
    db_config = DatabaseConfig()
    return bot_config, db_config


