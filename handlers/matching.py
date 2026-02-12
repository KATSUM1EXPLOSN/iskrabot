"""
Обработчики для просмотра анкет и мэтчинга
"""
import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext

from database.models import Database
import keyboards.keyboards as kb
from config import BotConfig


router = Router()


async def format_profile_text(profile: dict) -> str:
    """Форматирование текста анкеты"""
    gender_emoji = "👨" if profile["gender"] == "male" else "👩"
    
    text = (
        f"{gender_emoji} <b>{profile['name']}</b>, {profile['age']}\n"
        f"🏙 {profile['city']}\n"
    )
    
    if profile.get("bio"):
        text += f"\n📝 {profile['bio']}"
    
    return text


async def send_profile(
    message: Message, 
    profile: dict, 
    db: Database,
    config: BotConfig,
    user_id: int
) -> bool:
    """
    Отправить анкету пользователю.
    Возвращает False если лимит просмотров исчерпан.
    """
    # Проверяем лимит просмотров
    view_limit = await db.get_view_limit(user_id)
    total_allowed = config.daily_views_limit + view_limit["extra_views"]
    
    if view_limit["views_used"] >= total_allowed:
        await message.answer(
            "😔 Лимит просмотров на сегодня исчерпан!\n\n"
            f"Использовано: {view_limit['views_used']}/{total_allowed}\n\n"
            "Ты можешь сбросить лимит или купить дополнительные просмотры:",
            reply_markup=kb.get_limit_reached_keyboard()
        )
        return False
    
    # Увеличиваем счетчик просмотров
    await db.increment_views(user_id)
    
    text = await format_profile_text(profile)
    photos = json.loads(profile["photos"]) if profile["photos"] else []
    
    # Отправляем медиа
    if profile.get("video"):
        # Если есть видео, отправляем его
        await message.answer_video(
            video=profile["video"],
            caption=text,
            parse_mode="HTML",
            reply_markup=kb.get_profile_actions_keyboard(profile["user_id"])
        )
    elif photos:
        if len(photos) == 1:
            await message.answer_photo(
                photo=photos[0],
                caption=text,
                parse_mode="HTML",
                reply_markup=kb.get_profile_actions_keyboard(profile["user_id"])
            )
        else:
            # Отправляем альбом фотографий
            media = [InputMediaPhoto(media=photo) for photo in photos]
            media[0].caption = text
            media[0].parse_mode = "HTML"
            
            await message.answer_media_group(media=media)
            # Кнопки отдельным сообщением
            await message.answer(
                "Оцени анкету:",
                reply_markup=kb.get_profile_actions_keyboard(profile["user_id"])
            )
    else:
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=kb.get_profile_actions_keyboard(profile["user_id"])
        )
    
    return True


@router.message(F.text == "👀 Смотреть анкеты")
async def start_viewing(message: Message, db: Database, config: BotConfig):
    """Начать просмотр анкет"""
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала создай анкету командой /start")
        return
    
    profile = await db.get_profile(user["id"])
    if not profile:
        await message.answer("❌ У тебя ещё нет анкеты. Создай её командой /start")
        return
    
    # Ищем подходящую анкету
    next_profile = await db.get_next_profile(
        user_id=user["id"],
        gender=profile["gender"],
        looking_for=profile["looking_for"]
    )
    
    if not next_profile:
        await message.answer(
            "😔 Пока нет подходящих анкет.\n"
            "Попробуй позже или расширь критерии поиска!",
            reply_markup=kb.get_no_profiles_keyboard()
        )
        return
    
    await send_profile(message, next_profile, db, config, user["id"])


@router.callback_query(F.data.startswith("like_"))
async def process_like(callback: CallbackQuery, db: Database, config: BotConfig, bot: Bot):
    """Обработка лайка"""
    target_user_id = int(callback.data.replace("like_", ""))
    
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    is_match = await db.add_like(user["id"], target_user_id, is_like=True)
    
    if is_match:
        # Уведомляем обоих пользователей о мэтче
        target_user = await db.get_user_by_telegram_id(target_user_id)
        my_profile = await db.get_profile(user["id"])
        target_profile = await db.get_profile(target_user_id)
        
        # Уведомление текущему пользователю
        await callback.message.answer(
            f"🎉 <b>У вас взаимная симпатия!</b>\n\n"
            f"Ты и <b>{target_profile['name']}</b> понравились друг другу!\n"
            f"Теперь вы можете начать общаться!",
            parse_mode="HTML",
            reply_markup=kb.get_match_keyboard(target_user["telegram_id"] if target_user else target_user_id)
        )
        
        # Уведомление второму пользователю
        if target_user:
            try:
                await bot.send_message(
                    chat_id=target_user["telegram_id"],
                    text=f"🎉 <b>У вас взаимная симпатия!</b>\n\n"
                         f"Ты и <b>{my_profile['name']}</b> понравились друг другу!\n"
                         f"Теперь вы можете начать общаться!",
                    parse_mode="HTML",
                    reply_markup=kb.get_match_keyboard(callback.from_user.id)
                )
            except Exception:
                pass  # Пользователь мог заблокировать бота
    
    await callback.answer("❤️ Лайк!")
    
    # Показываем следующую анкету
    await show_next_profile(callback, db, config)


@router.callback_query(F.data.startswith("dislike_"))
async def process_dislike(callback: CallbackQuery, db: Database, config: BotConfig):
    """Обработка дизлайка"""
    target_user_id = int(callback.data.replace("dislike_", ""))
    
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    await db.add_like(user["id"], target_user_id, is_like=False)
    
    await callback.answer("👎")
    
    # Показываем следующую анкету
    await show_next_profile(callback, db, config)


async def show_next_profile(callback: CallbackQuery, db: Database, config: BotConfig):
    """Показать следующую анкету"""
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    profile = await db.get_profile(user["id"])
    
    next_profile = await db.get_next_profile(
        user_id=user["id"],
        gender=profile["gender"],
        looking_for=profile["looking_for"]
    )
    
    if not next_profile:
        await callback.message.answer(
            "😔 Анкеты закончились!\n"
            "Попробуй позже или купи дополнительные просмотры.",
            reply_markup=kb.get_no_profiles_keyboard()
        )
        return
    
    success = await send_profile(callback.message, next_profile, db, config, user["id"])
    if not success:
        return  # Лимит исчерпан, сообщение уже отправлено


@router.callback_query(F.data == "stop_viewing")
async def stop_viewing(callback: CallbackQuery):
    """Остановить просмотр анкет"""
    await callback.message.delete()
    await callback.message.answer(
        "👋 Просмотр анкет остановлен.\n"
        "Возвращайся, когда будешь готов!",
        reply_markup=kb.get_main_menu()
    )


@router.callback_query(F.data == "refresh_profiles")
async def refresh_profiles(callback: CallbackQuery, db: Database, config: BotConfig):
    """Обновить список анкет"""
    await callback.answer("🔄 Обновляю...")
    await callback.message.delete()
    
    # Вызываем просмотр анкет заново
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    profile = await db.get_profile(user["id"])
    
    next_profile = await db.get_next_profile(
        user_id=user["id"],
        gender=profile["gender"],
        looking_for=profile["looking_for"]
    )
    
    if not next_profile:
        await callback.message.answer(
            "😔 Пока нет новых анкет.\n"
            "Попробуй позже!",
            reply_markup=kb.get_no_profiles_keyboard()
        )
        return
    
    await send_profile(callback.message, next_profile, db, config, user["id"])


# === Мэтчи ===

@router.message(F.text == "❤️ Мои мэтчи")
async def show_matches(message: Message, db: Database):
    """Показать список мэтчей"""
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала создай анкету командой /start")
        return
    
    matches = await db.get_user_matches(user["id"])
    
    if not matches:
        await message.answer(
            "💔 У тебя пока нет мэтчей.\n\n"
            "Продолжай смотреть анкеты — взаимная симпатия обязательно случится!"
        )
        return
    
    await message.answer(f"❤️ <b>Твои мэтчи ({len(matches)}):</b>", parse_mode="HTML")
    
    for match in matches[:10]:  # Показываем первые 10
        # Получаем профиль мэтча
        matched_user_id = match["user2_id"] if match["user1_id"] == user["id"] else match["user1_id"]
        matched_profile = await db.get_profile(matched_user_id)
        matched_user = await db.get_user_by_telegram_id(matched_user_id)
        
        if matched_profile and matched_user:
            photos = json.loads(matched_profile["photos"]) if matched_profile["photos"] else []
            text = f"<b>{matched_profile['name']}</b>, {matched_profile['age']} — {matched_profile['city']}"
            
            if photos:
                await message.answer_photo(
                    photo=photos[0],
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=kb.get_match_keyboard(matched_user["telegram_id"])
                )
            else:
                await message.answer(
                    text,
                    parse_mode="HTML",
                    reply_markup=kb.get_match_keyboard(matched_user["telegram_id"])
                )
