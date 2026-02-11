"""
Клавиатуры для бота знакомств
"""
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# === Главное меню ===

def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="👀 Смотреть анкеты"),
        KeyboardButton(text="👤 Моя анкета")
    )
    builder.row(
        KeyboardButton(text="❤️ Мои мэтчи"),
        KeyboardButton(text="⭐ Магазин")
    )
    return builder.as_markup(resize_keyboard=True)


# === Регистрация ===

def get_gender_keyboard() -> InlineKeyboardMarkup:
    """Выбор пола"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👨 Мужчина", callback_data="gender_male"),
        InlineKeyboardButton(text="👩 Женщина", callback_data="gender_female")
    )
    return builder.as_markup()


def get_looking_for_keyboard() -> InlineKeyboardMarkup:
    """Кого ищем"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👨 Мужчин", callback_data="looking_male"),
        InlineKeyboardButton(text="👩 Женщин", callback_data="looking_female")
    )
    return builder.as_markup()


def get_skip_keyboard(field: str) -> InlineKeyboardMarkup:
    """Кнопка пропуска"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"skip_{field}")
    )
    return builder.as_markup()


def get_done_media_keyboard() -> InlineKeyboardMarkup:
    """Завершить добавление медиа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="media_done")
    )
    return builder.as_markup()


# === Просмотр анкет ===

def get_profile_actions_keyboard(profile_user_id: int) -> InlineKeyboardMarkup:
    """Кнопки действий при просмотре анкеты"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❤️", callback_data=f"like_{profile_user_id}"),
        InlineKeyboardButton(text="👎", callback_data=f"dislike_{profile_user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💤 Остановить", callback_data="stop_viewing")
    )
    return builder.as_markup()


def get_no_profiles_keyboard() -> InlineKeyboardMarkup:
    """Нет анкет для просмотра"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_profiles")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Купить просмотры", callback_data="buy_views")
    )
    return builder.as_markup()


def get_limit_reached_keyboard() -> InlineKeyboardMarkup:
    """Лимит просмотров исчерпан"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Сбросить лимит (50⭐)", callback_data="reset_limit")
    )
    builder.row(
        InlineKeyboardButton(text="➕ +10 просмотров (10⭐)", callback_data="buy_extra_views")
    )
    return builder.as_markup()


# === Мэтчи ===

def get_match_keyboard(matched_telegram_id: int) -> InlineKeyboardMarkup:
    """Кнопка перехода к чату с мэтчем"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💬 Написать", 
            url=f"tg://user?id={matched_telegram_id}"
        )
    )
    return builder.as_markup()


# === Моя анкета ===

def get_my_profile_keyboard() -> InlineKeyboardMarkup:
    """Управление своей анкетой"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")
    )
    builder.row(
        InlineKeyboardButton(text="📷 Изменить фото", callback_data="edit_photos"),
        InlineKeyboardButton(text="🎥 Изменить видео", callback_data="edit_video")
    )
    builder.row(
        InlineKeyboardButton(text="👁 Скрыть анкету", callback_data="hide_profile"),
        InlineKeyboardButton(text="🗑 Удалить анкету", callback_data="delete_profile")
    )
    return builder.as_markup()


def get_edit_profile_keyboard() -> InlineKeyboardMarkup:
    """Что редактировать в анкете"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Имя", callback_data="edit_name"),
        InlineKeyboardButton(text="🎂 Возраст", callback_data="edit_age")
    )
    builder.row(
        InlineKeyboardButton(text="🏙 Город", callback_data="edit_city"),
        InlineKeyboardButton(text="📄 Описание", callback_data="edit_bio")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")
    )
    return builder.as_markup()


def get_confirm_delete_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение удаления"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
    )
    return builder.as_markup()


# === Магазин ===

def get_shop_keyboard() -> InlineKeyboardMarkup:
    """Магазин"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Сброс лимита — 50⭐", callback_data="buy_reset")
    )
    builder.row(
        InlineKeyboardButton(text="➕ 10 просмотров — 10⭐", callback_data="buy_views_10")
    )
    builder.row(
        InlineKeyboardButton(text="➕ 50 просмотров — 40⭐", callback_data="buy_views_50")
    )
    builder.row(
        InlineKeyboardButton(text="➕ 100 просмотров — 70⭐", callback_data="buy_views_100")
    )
    return builder.as_markup()


# === Оплата ===

def get_payment_keyboard(payment_type: str, amount: int) -> InlineKeyboardMarkup:
    """Кнопка оплаты"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"💫 Оплатить {amount}⭐", 
            pay=True
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")
    )
    return builder.as_markup()
