"""
Обработчики для создания и редактирования анкет
"""
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter

from database.models import Database
import keyboards.keyboards as kb
from config import BotConfig


router = Router()


class ProfileCreation(StatesGroup):
    """Состояния создания анкеты"""
    name = State()
    age = State()
    gender = State()
    looking_for = State()
    city = State()
    bio = State()
    photos = State()
    video = State()


class ProfileEdit(StatesGroup):
    """Состояния редактирования анкеты"""
    name = State()
    age = State()
    city = State()
    bio = State()
    photos = State()
    video = State()


# === Начало регистрации ===

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: Database):
    """Команда /start"""
    user_id = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    await state.update_data(user_id=user_id)
    
    profile = await db.get_profile(user_id)
    if profile:
        await message.answer(
            "👋 С возвращением! Используй меню для навигации.",
            reply_markup=kb.get_main_menu()
        )
    else:
        await message.answer(
            "👋 Привет! Я бот для знакомств.\n\n"
            "Давай создадим твою анкету!\n"
            "Как тебя зовут?"
        )
        await state.set_state(ProfileCreation.name)


# === Создание анкеты ===

@router.message(ProfileCreation.name)
async def process_name(message: Message, state: FSMContext):
    """Получение имени"""
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Имя должно быть от 2 до 50 символов. Попробуй ещё раз:")
        return
    
    await state.update_data(name=name)
    await message.answer(f"Отлично, {name}! Сколько тебе лет?")
    await state.set_state(ProfileCreation.age)


@router.message(ProfileCreation.age)
async def process_age(message: Message, state: FSMContext):
    """Получение возраста"""
    try:
        age = int(message.text.strip())
        if age < 18 or age > 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ Укажи возраст числом от 18 до 100:")
        return
    
    await state.update_data(age=age)
    await message.answer(
        "Укажи свой пол:",
        reply_markup=kb.get_gender_keyboard()
    )
    await state.set_state(ProfileCreation.gender)


@router.callback_query(ProfileCreation.gender, F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """Получение пола"""
    gender = callback.data.replace("gender_", "")
    await state.update_data(gender=gender)
    
    await callback.message.edit_text(
        "Кого ты хочешь найти?",
        reply_markup=kb.get_looking_for_keyboard()
    )
    await state.set_state(ProfileCreation.looking_for)


@router.callback_query(ProfileCreation.looking_for, F.data.startswith("looking_"))
async def process_looking_for(callback: CallbackQuery, state: FSMContext):
    """Получение предпочтений"""
    looking_for = callback.data.replace("looking_", "")
    await state.update_data(looking_for=looking_for)
    
    await callback.message.edit_text("🏙 В каком городе ты находишься?")
    await state.set_state(ProfileCreation.city)


@router.message(ProfileCreation.city)
async def process_city(message: Message, state: FSMContext, config: BotConfig):
    """Получение города"""
    city = message.text.strip()
    if len(city) < 2 or len(city) > 100:
        await message.answer("❌ Название города должно быть от 2 до 100 символов:")
        return
    
    await state.update_data(city=city)
    await message.answer(
        f"📝 Расскажи о себе (макс. {config.max_bio_length} символов).\n"
        "Это поможет другим узнать тебя лучше!",
        reply_markup=kb.get_skip_keyboard("bio")
    )
    await state.set_state(ProfileCreation.bio)


@router.message(ProfileCreation.bio)
async def process_bio(message: Message, state: FSMContext, config: BotConfig):
    """Получение биографии"""
    bio = message.text.strip()
    if len(bio) > config.max_bio_length:
        await message.answer(f"❌ Описание слишком длинное. Максимум {config.max_bio_length} символов:")
        return
    
    await state.update_data(bio=bio)
    await ask_for_photos(message, state, config)


@router.callback_query(ProfileCreation.bio, F.data == "skip_bio")
async def skip_bio(callback: CallbackQuery, state: FSMContext, config: BotConfig):
    """Пропуск биографии"""
    await state.update_data(bio="")
    await callback.message.delete()
    await ask_for_photos(callback.message, state, config)


async def ask_for_photos(message: Message, state: FSMContext, config: BotConfig):
    """Запрос фотографий"""
    await state.update_data(photos=[])
    await message.answer(
        f"📷 Отправь до {config.max_photos} фотографий для анкеты.\n"
        "Когда закончишь, нажми кнопку «Готово».",
        reply_markup=kb.get_done_media_keyboard()
    )
    await state.set_state(ProfileCreation.photos)


@router.message(ProfileCreation.photos, F.content_type == ContentType.PHOTO)
async def process_photo(message: Message, state: FSMContext, config: BotConfig):
    """Получение фотографии"""
    data = await state.get_data()
    photos = data.get("photos", [])
    
    if len(photos) >= config.max_photos:
        await message.answer(f"❌ Максимум {config.max_photos} фотографий. Нажми «Готово» для продолжения.")
        return
    
    photo_id = message.photo[-1].file_id  # Берем фото в лучшем качестве
    photos.append(photo_id)
    await state.update_data(photos=photos)
    
    remaining = config.max_photos - len(photos)
    await message.answer(
        f"✅ Фото добавлено! ({len(photos)}/{config.max_photos})\n"
        f"Можешь добавить ещё {remaining} или нажать «Готово».",
        reply_markup=kb.get_done_media_keyboard()
    )


@router.callback_query(ProfileCreation.photos, F.data == "media_done")
async def photos_done(callback: CallbackQuery, state: FSMContext, config: BotConfig):
    """Завершение добавления фото"""
    data = await state.get_data()
    photos = data.get("photos", [])
    
    if not photos:
        await callback.answer("❌ Добавь хотя бы одно фото!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"🎥 Хочешь добавить короткое видео (до {config.max_video_duration} сек)?\n"
        "Это необязательно, но поможет выделиться!",
        reply_markup=kb.get_skip_keyboard("video")
    )
    await state.set_state(ProfileCreation.video)


@router.message(ProfileCreation.video, F.content_type.in_([ContentType.VIDEO, ContentType.VIDEO_NOTE]))
async def process_video(message: Message, state: FSMContext, db: Database, config: BotConfig):
    """Получение видео"""
    video = message.video or message.video_note
    
    if video.duration > config.max_video_duration:
        await message.answer(
            f"❌ Видео слишком длинное! Максимум {config.max_video_duration} секунд."
        )
        return
    
    await state.update_data(video=video.file_id)
    await finish_profile_creation(message, state, db)


@router.callback_query(ProfileCreation.video, F.data == "skip_video")
async def skip_video(callback: CallbackQuery, state: FSMContext, db: Database):
    """Пропуск видео"""
    await state.update_data(video=None)
    await callback.message.delete()
    await finish_profile_creation(callback.message, state, db)


async def finish_profile_creation(message: Message, state: FSMContext, db: Database):
    """Завершение создания анкеты"""
    data = await state.get_data()
    
    await db.create_profile(
        user_id=data["user_id"],
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        looking_for=data["looking_for"],
        city=data["city"],
        bio=data.get("bio", ""),
        photos=json.dumps(data.get("photos", [])),
        video=data.get("video")
    )
    
    await state.clear()
    await message.answer(
        "🎉 Отлично! Твоя анкета создана!\n\n"
        "Теперь ты можешь смотреть анкеты других пользователей "
        "и искать свою пару!",
        reply_markup=kb.get_main_menu()
    )


# === Просмотр и редактирование своей анкеты ===

@router.message(F.text == "👤 Моя анкета")
async def show_my_profile(message: Message, db: Database):
    """Показать свою анкету"""
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала создай анкету командой /start")
        return
    
    profile = await db.get_profile(user["id"])
    if not profile:
        await message.answer("❌ У тебя ещё нет анкеты. Создай её командой /start")
        return
    
    # Формируем текст анкеты
    photos = json.loads(profile["photos"]) if profile["photos"] else []
    gender_text = "👨 Мужчина" if profile["gender"] == "male" else "👩 Женщина"
    looking_text = "👨 мужчин" if profile["looking_for"] == "male" else "👩 женщин"
    visibility = "👁 Видна всем" if profile["is_visible"] else "🙈 Скрыта"
    
    text = (
        f"📋 <b>Твоя анкета:</b>\n\n"
        f"<b>{profile['name']}</b>, {profile['age']}\n"
        f"{gender_text}\n"
        f"🏙 {profile['city']}\n"
        f"🔍 Ищу: {looking_text}\n\n"
    )
    
    if profile["bio"]:
        text += f"📝 {profile['bio']}\n\n"
    
    text += f"📷 Фото: {len(photos)}\n"
    text += f"🎥 Видео: {'Есть' if profile['video'] else 'Нет'}\n"
    text += f"\n{visibility}"
    
    # Отправляем первое фото с анкетой
    if photos:
        await message.answer_photo(
            photo=photos[0],
            caption=text,
            parse_mode="HTML",
            reply_markup=kb.get_my_profile_keyboard()
        )
    else:
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=kb.get_my_profile_keyboard()
        )


@router.callback_query(F.data == "edit_profile")
async def edit_profile_menu(callback: CallbackQuery):
    """Меню редактирования анкеты"""
    await callback.message.edit_caption(
        caption="✏️ Что хочешь изменить?",
        reply_markup=kb.get_edit_profile_keyboard()
    )


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery, db: Database):
    """Вернуться к просмотру анкеты"""
    await callback.message.delete()
    # Имитируем нажатие на кнопку "Моя анкета"
    await show_my_profile(callback.message, db)


@router.callback_query(F.data == "edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование имени"""
    await callback.message.answer("📝 Введи новое имя:")
    await state.set_state(ProfileEdit.name)


@router.message(ProfileEdit.name)
async def process_edit_name(message: Message, state: FSMContext, db: Database):
    """Обработка нового имени"""
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Имя должно быть от 2 до 50 символов:")
        return
    
    user = await db.get_user_by_telegram_id(message.from_user.id)
    profile = await db.get_profile(user["id"])
    
    await db.create_profile(
        user_id=user["id"],
        name=name,
        age=profile["age"],
        gender=profile["gender"],
        looking_for=profile["looking_for"],
        city=profile["city"],
        bio=profile["bio"],
        photos=profile["photos"],
        video=profile["video"]
    )
    
    await state.clear()
    await message.answer("✅ Имя обновлено!", reply_markup=kb.get_main_menu())


@router.callback_query(F.data == "hide_profile")
async def toggle_profile_visibility(callback: CallbackQuery, db: Database):
    """Переключить видимость анкеты"""
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    profile = await db.get_profile(user["id"])
    
    new_visibility = not profile["is_visible"]
    await db.update_profile_visibility(user["id"], new_visibility)
    
    status = "видна всем" if new_visibility else "скрыта"
    await callback.answer(f"✅ Анкета теперь {status}", show_alert=True)
    await callback.message.delete()
    await show_my_profile(callback.message, db)


@router.callback_query(F.data == "delete_profile")
async def confirm_delete_profile(callback: CallbackQuery):
    """Подтверждение удаления анкеты"""
    await callback.message.edit_caption(
        caption="⚠️ Ты уверен, что хочешь удалить анкету?\n"
               "Это действие нельзя отменить!",
        reply_markup=kb.get_confirm_delete_keyboard()
    )


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery, db: Database):
    """Отмена удаления"""
    await callback.message.delete()
    await show_my_profile(callback.message, db)
