import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================= НАСТРОЙКИ БОТА =================

# 1. Токен вашего бота (получить у @BotFather)
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА_ОТ_BOTFATHER"

# 2. Токен провайдера ЮKassa (получить у @BotFather -> Bot Settings -> Payments -> YooKassa)
PROVIDER_TOKEN = "ВАШ_ТОКЕН_ЮKASSA_ОТ_BOTFATHER"

# ================= ДАННЫЕ О КУРСАХ =================
# Структура: 'ID_курса': {'название', 'цена_в_рублях', 'ссылка_на_канал'}
COURSES = {
    "course_1": {
        "title": "Курс с нуля",
        "price": 5000, # Цена в рублях (без копеек)
        "link": "https://t.me/+UniqLink1",
        "description": "Базовый курс для начинающих мастеров."
    },
    "course_2": {
        "title": "Повышение квалификации",
        "price": 7000,
        "link": "https://t.me/+UniqLink2",
        "description": "Курс для мастеров с опытом работы."
    },
    "course_3": {
        "title": "Выход из черного",
        "price": 6000,
        "link": "https://t.me/+UniqLink3",
        "description": "Секреты и техники безопасного выхода из черного цвета."
    },
    "course_4": {
        "title": "Наращивание волос",
        "price": 10000,
        "link": "https://t.me/+UniqLink4",
        "description": "Полный курс по капсульному наращиванию."
    },
    "course_5": {
        "title": "Сложные техники окрашивания",
        "price": 8500,
        "link": "https://t.me/+UniqLink5",
        "description": "Airtouch, Shatush, Balayage."
    },
    "course_6": {
        "title": "Стрижки",
        "price": 4000,
        "link": "https://t.me/+UniqLink6",
        "description": "Современные женские стрижки."
    },
    "course_7": {
        "title": "Total Blonde",
        "price": 5500,
        "link": "https://t.me/+UniqLink7",
        "description": "Идеальный блонд без повреждения волос."
    }
}

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= ОБРАБОТЧИКИ =================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """
    Обработчик команды /start.
    Выводит приветствие и клавиатуру с выбором курсов.
    """
    builder = InlineKeyboardBuilder()
    
    # Создаем кнопки для каждого курса динамически из словаря COURSES
    for course_id, course_data in COURSES.items():
        builder.button(
            text=course_data["title"],
            callback_data=f"buy_{course_id}" # callback_data будет вида buy_course_1
        )
    
    # Располагаем кнопки по одной в ряд
    builder.adjust(1)
    
    welcome_text = (
        f"Здравствуйте, {message.from_user.first_name}! 👋\n\n"
        "Добро пожаловать в нашу академию красоты. Выберите интересующий вас курс из списка ниже, "
        "чтобы узнать подробности и произвести оплату."
    )
    
    await message.answer(welcome_text, reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("buy_"))
async def process_course_selection(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку курса.
    Формирует и отправляет счет на оплату (Invoice).
    """
    # Получаем ID курса из callback_data (отрезаем 'buy_')
    course_id = callback.data.replace("buy_", "")
    course = COURSES.get(course_id)
    
    if not course:
        await callback.answer("Ошибка: Курс не найден.", show_alert=True)
        return
    
    # Убираем часики на кнопке в Telegram
    await callback.answer()
    
    # Цена в Telegram Payments указывается в минимальных единицах валюты (копейках)
    # Поэтому умножаем цену в рублях на 100
    price_in_kopecks = course["price"] * 100
    prices = [LabeledPrice(label=course["title"], amount=price_in_kopecks)]
    
    # Отправляем счет
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=course["title"],
        description=course["description"],
        payload=course_id, # Важный параметр! Сюда мы кладем ID курса, чтобы после оплаты понять, за что заплатили
        provider_token=PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter="course-payment"
    )

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """
    Обязательный обработчик Telegram Payments.
    Telegram спрашивает бота за секунду до списания денег: "Всё ок? Товар еще в наличии?"
    Мы должны ответить ok=True, чтобы оплата прошла.
    """
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """
    Обработчик успешной оплаты.
    Срабатывает после того, как ЮKassa подтвердила платеж.
    """
    # Достаем payload (наш ID курса), который мы передавали в send_invoice
    purchased_course_id = message.successful_payment.invoice_payload
    course = COURSES.get(purchased_course_id)
    
    if course:
        # Формируем сообщение с секретной ссылкой
        success_text = (
            f"🎉 Поздравляем с успешной оплатой!\n\n"
            f"Вы приобрели курс: <b>{course['title']}</b>.\n\n"
            f"Ваша индивидуальная ссылка для доступа к материалам канала:\n"
            f"{course['link']}\n\n"
            f"Успешного обучения! 📚"
        )
        await message.answer(success_text, parse_mode="HTML")
    else:
        # На случай непредвиденных сбоев
        await message.answer("Оплата прошла успешно, но произошла ошибка с выдачей ссылки. Пожалуйста, обратитесь к администратору.")

# ================= ЗАПУСК БОТА =================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен и готов к работе!")
    # Запускаем поллинг (опрос серверов Telegram)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")
