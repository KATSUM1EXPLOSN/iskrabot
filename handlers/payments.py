"""
Обработчики платежей через Telegram Stars
"""
from aiogram import Router, F
from aiogram.types import (
    Message, 
    CallbackQuery,
    LabeledPrice,
    PreCheckoutQuery,
    ContentType
)

from database import Database
from keyboards import keyboards as kb
from config import BotConfig


router = Router()


# Цены на товары (в звездах Telegram)
PRICES = {
    "reset": 50,      # Сброс лимита
    "views_10": 10,   # +10 просмотров
    "views_50": 40,   # +50 просмотров  
    "views_100": 70,  # +100 просмотров
}

VIEWS_AMOUNTS = {
    "views_10": 10,
    "views_50": 50,
    "views_100": 100,
}


@router.message(F.text == "⭐ Магазин")
async def show_shop(message: Message, db: Database, config: BotConfig):
    """Показать магазин"""
    user = await db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала создай анкету командой /start")
        return
    
    view_limit = await db.get_view_limit(user["id"])
    total_allowed = config.daily_views_limit + view_limit["extra_views"]
    
    await message.answer(
        "⭐ <b>Магазин</b>\n\n"
        f"📊 Твой лимит сегодня: {view_limit['views_used']}/{total_allowed}\n\n"
        "Выбери, что хочешь приобрести:",
        parse_mode="HTML",
        reply_markup=kb.get_shop_keyboard()
    )


@router.callback_query(F.data == "buy_reset")
@router.callback_query(F.data == "reset_limit")
async def buy_reset_limit(callback: CallbackQuery):
    """Покупка сброса лимита"""
    await send_invoice(
        callback.message,
        title="Сброс лимита просмотров",
        description="Сбрось счетчик просмотров и начни заново!",
        payload="reset_limit",
        amount=PRICES["reset"]
    )
    await callback.answer()


@router.callback_query(F.data == "buy_views_10")
@router.callback_query(F.data == "buy_extra_views")
@router.callback_query(F.data == "buy_views")
async def buy_views_10(callback: CallbackQuery):
    """Покупка 10 просмотров"""
    await send_invoice(
        callback.message,
        title="+10 просмотров",
        description="Получи дополнительные 10 просмотров анкет!",
        payload="extra_views_10",
        amount=PRICES["views_10"]
    )
    await callback.answer()


@router.callback_query(F.data == "buy_views_50")
async def buy_views_50(callback: CallbackQuery):
    """Покупка 50 просмотров"""
    await send_invoice(
        callback.message,
        title="+50 просмотров",
        description="Получи дополнительные 50 просмотров анкет!",
        payload="extra_views_50",
        amount=PRICES["views_50"]
    )
    await callback.answer()


@router.callback_query(F.data == "buy_views_100")
async def buy_views_100(callback: CallbackQuery):
    """Покупка 100 просмотров"""
    await send_invoice(
        callback.message,
        title="+100 просмотров",
        description="Получи дополнительные 100 просмотров анкет!",
        payload="extra_views_100",
        amount=PRICES["views_100"]
    )
    await callback.answer()


async def send_invoice(
    message: Message,
    title: str,
    description: str,
    payload: str,
    amount: int
):
    """Отправить инвойс для оплаты звездами"""
    await message.answer_invoice(
        title=title,
        description=description,
        payload=payload,
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=title, amount=amount)],
        # Для Telegram Stars provider_token не нужен
    )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Подтверждение платежа перед оплатой"""
    # Здесь можно добавить дополнительные проверки
    await pre_checkout_query.answer(ok=True)


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: Message, db: Database, config: BotConfig):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    user = await db.get_user_by_telegram_id(message.from_user.id)
    
    if payload == "reset_limit":
        # Сброс лимита просмотров
        await db.reset_views(user["id"])
        await db.add_payment(
            user_id=user["id"],
            amount=PRICES["reset"],
            payment_type="reset_views",
            telegram_payment_id=payment.telegram_payment_charge_id
        )
        await message.answer(
            "✅ Лимит просмотров успешно сброшен!\n"
            "Теперь ты можешь продолжить смотреть анкеты.",
            reply_markup=kb.get_main_menu()
        )
    
    elif payload.startswith("extra_views_"):
        # Добавление просмотров
        views_type = payload.replace("extra_", "")  # views_10, views_50, views_100
        views_amount = VIEWS_AMOUNTS.get(views_type, 10)
        price = PRICES.get(views_type, 10)
        
        await db.add_extra_views(user["id"], views_amount)
        await db.add_payment(
            user_id=user["id"],
            amount=price,
            payment_type="extra_views",
            telegram_payment_id=payment.telegram_payment_charge_id
        )
        await message.answer(
            f"✅ Добавлено {views_amount} дополнительных просмотров!\n"
            "Приятного поиска!",
            reply_markup=kb.get_main_menu()
        )


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery):
    """Отмена платежа"""
    await callback.message.delete()
    await callback.message.answer(
        "❌ Покупка отменена.",
        reply_markup=kb.get_main_menu()
    )
    await callback.answer()
