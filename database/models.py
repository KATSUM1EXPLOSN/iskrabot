"""
Модели базы данных для бота знакомств
"""
import aiosqlite
from datetime import datetime, date
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class Gender(Enum):
    MALE = "male"
    FEMALE = "female"


@dataclass
class User:
    """Модель пользователя"""
    id: int
    telegram_id: int
    username: Optional[str]
    created_at: datetime
    is_active: bool = True
    is_banned: bool = False


@dataclass
class Profile:
    """Модель анкеты"""
    id: int
    user_id: int
    name: str
    age: int
    gender: Gender
    looking_for: Gender
    city: str
    bio: str
    photos: list[str]  # JSON список file_id
    video: Optional[str]  # file_id видео
    is_visible: bool = True
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class Like:
    """Модель лайка"""
    id: int
    from_user_id: int
    to_user_id: int
    is_like: bool  # True = лайк, False = дизлайк
    created_at: datetime


@dataclass
class Match:
    """Модель мэтча (взаимного лайка)"""
    id: int
    user1_id: int
    user2_id: int
    created_at: datetime


@dataclass
class ViewLimit:
    """Лимит просмотров пользователя"""
    id: int
    user_id: int
    date: date
    views_used: int
    extra_views: int  # Купленные дополнительные просмотры


@dataclass
class Payment:
    """История платежей"""
    id: int
    user_id: int
    amount: int  # В звездах Telegram
    payment_type: str  # "reset_views" или "extra_views"
    telegram_payment_id: str
    created_at: datetime


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Подключение к базе данных"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        await self.create_tables()
    
    async def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            await self.connection.close()
    
    async def create_tables(self):
        """Создание таблиц"""
        await self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                is_banned BOOLEAN DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                looking_for TEXT NOT NULL,
                city TEXT NOT NULL,
                bio TEXT,
                photos TEXT DEFAULT '[]',
                video TEXT,
                is_visible BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                is_like BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_user_id) REFERENCES users(id),
                FOREIGN KEY (to_user_id) REFERENCES users(id),
                UNIQUE(from_user_id, to_user_id)
            );
            
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user1_id) REFERENCES users(id),
                FOREIGN KEY (user2_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS view_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                views_used INTEGER DEFAULT 0,
                extra_views INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, date)
            );
            
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                payment_type TEXT NOT NULL,
                telegram_payment_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_profiles_gender ON profiles(gender, looking_for);
            CREATE INDEX IF NOT EXISTS idx_profiles_city ON profiles(city);
            CREATE INDEX IF NOT EXISTS idx_likes_users ON likes(from_user_id, to_user_id);
        """)
        await self.connection.commit()
    
    # === Пользователи ===
    
    async def get_or_create_user(self, telegram_id: int, username: str = None) -> int:
        """Получить или создать пользователя, возвращает user_id"""
        cursor = await self.connection.execute(
            "SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        if row:
            return row["id"]
        
        cursor = await self.connection.execute(
            "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username)
        )
        await self.connection.commit()
        return cursor.lastrowid
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Получить пользователя по telegram_id"""
        cursor = await self.connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    # === Анкеты ===
    
    async def create_profile(self, user_id: int, name: str, age: int, 
                            gender: str, looking_for: str, city: str, 
                            bio: str, photos: str, video: str = None) -> int:
        """Создать анкету"""
        cursor = await self.connection.execute("""
            INSERT INTO profiles (user_id, name, age, gender, looking_for, city, bio, photos, video)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                age = excluded.age,
                gender = excluded.gender,
                looking_for = excluded.looking_for,
                city = excluded.city,
                bio = excluded.bio,
                photos = excluded.photos,
                video = excluded.video,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, name, age, gender, looking_for, city, bio, photos, video))
        await self.connection.commit()
        return cursor.lastrowid
    
    async def get_profile(self, user_id: int) -> Optional[dict]:
        """Получить анкету пользователя"""
        cursor = await self.connection.execute(
            "SELECT * FROM profiles WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def get_next_profile(self, user_id: int, gender: str, looking_for: str, city: str = None) -> Optional[dict]:
        """Получить следующую анкету для просмотра"""
        query = """
            SELECT p.*, u.telegram_id, u.username FROM profiles p
            JOIN users u ON p.user_id = u.id
            WHERE p.user_id != ?
            AND p.gender = ?
            AND p.looking_for = ?
            AND p.is_visible = 1
            AND u.is_active = 1
            AND u.is_banned = 0
            AND p.user_id NOT IN (
                SELECT to_user_id FROM likes WHERE from_user_id = ?
            )
        """
        params = [user_id, looking_for, gender, user_id]
        
        if city:
            query += " AND p.city = ?"
            params.append(city)
        
        query += " ORDER BY RANDOM() LIMIT 1"
        
        cursor = await self.connection.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def update_profile_visibility(self, user_id: int, is_visible: bool):
        """Обновить видимость анкеты"""
        await self.connection.execute(
            "UPDATE profiles SET is_visible = ? WHERE user_id = ?",
            (is_visible, user_id)
        )
        await self.connection.commit()
    
    # === Лайки и мэтчи ===
    
    async def add_like(self, from_user_id: int, to_user_id: int, is_like: bool) -> bool:
        """Добавить лайк/дизлайк, возвращает True если это мэтч"""
        await self.connection.execute("""
            INSERT OR REPLACE INTO likes (from_user_id, to_user_id, is_like)
            VALUES (?, ?, ?)
        """, (from_user_id, to_user_id, is_like))
        await self.connection.commit()
        
        if not is_like:
            return False
        
        # Проверяем взаимный лайк
        cursor = await self.connection.execute("""
            SELECT id FROM likes 
            WHERE from_user_id = ? AND to_user_id = ? AND is_like = 1
        """, (to_user_id, from_user_id))
        mutual = await cursor.fetchone()
        
        if mutual:
            # Создаем мэтч
            await self.connection.execute("""
                INSERT INTO matches (user1_id, user2_id) VALUES (?, ?)
            """, (min(from_user_id, to_user_id), max(from_user_id, to_user_id)))
            await self.connection.commit()
            return True
        
        return False
    
    async def get_user_matches(self, user_id: int) -> list[dict]:
        """Получить мэтчи пользователя"""
        cursor = await self.connection.execute("""
            SELECT m.*, 
                   CASE WHEN m.user1_id = ? THEN p2.* ELSE p1.* END as matched_profile,
                   CASE WHEN m.user1_id = ? THEN u2.telegram_id ELSE u1.telegram_id END as matched_telegram_id
            FROM matches m
            JOIN profiles p1 ON m.user1_id = p1.user_id
            JOIN profiles p2 ON m.user2_id = p2.user_id
            JOIN users u1 ON m.user1_id = u1.id
            JOIN users u2 ON m.user2_id = u2.id
            WHERE m.user1_id = ? OR m.user2_id = ?
            ORDER BY m.created_at DESC
        """, (user_id, user_id, user_id, user_id))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    # === Лимиты просмотров ===
    
    async def get_view_limit(self, user_id: int) -> dict:
        """Получить лимит просмотров на сегодня"""
        today = date.today().isoformat()
        cursor = await self.connection.execute("""
            SELECT * FROM view_limits WHERE user_id = ? AND date = ?
        """, (user_id, today))
        row = await cursor.fetchone()
        
        if row:
            return dict(row)
        
        # Создаем запись на сегодня
        await self.connection.execute("""
            INSERT INTO view_limits (user_id, date, views_used, extra_views)
            VALUES (?, ?, 0, 0)
        """, (user_id, today))
        await self.connection.commit()
        
        return {"user_id": user_id, "date": today, "views_used": 0, "extra_views": 0}
    
    async def increment_views(self, user_id: int):
        """Увеличить счетчик просмотров"""
        today = date.today().isoformat()
        await self.connection.execute("""
            UPDATE view_limits SET views_used = views_used + 1
            WHERE user_id = ? AND date = ?
        """, (user_id, today))
        await self.connection.commit()
    
    async def add_extra_views(self, user_id: int, amount: int):
        """Добавить дополнительные просмотры"""
        today = date.today().isoformat()
        await self.get_view_limit(user_id)  # Убедимся что запись существует
        await self.connection.execute("""
            UPDATE view_limits SET extra_views = extra_views + ?
            WHERE user_id = ? AND date = ?
        """, (amount, user_id, today))
        await self.connection.commit()
    
    async def reset_views(self, user_id: int):
        """Сбросить просмотры (после оплаты)"""
        today = date.today().isoformat()
        await self.connection.execute("""
            UPDATE view_limits SET views_used = 0
            WHERE user_id = ? AND date = ?
        """, (user_id, today))
        await self.connection.commit()
    
    # === Платежи ===
    
    async def add_payment(self, user_id: int, amount: int, payment_type: str, 
                         telegram_payment_id: str = None) -> int:
        """Записать платеж"""
        cursor = await self.connection.execute("""
            INSERT INTO payments (user_id, amount, payment_type, telegram_payment_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, amount, payment_type, telegram_payment_id))
        await self.connection.commit()
        return cursor.lastrowid
