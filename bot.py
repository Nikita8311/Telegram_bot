import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Загружаем переменные окружения из файла .env (он должен лежать в той же папке)
load_dotenv()

# Получаем токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверка безопасности: если токен не найден, скрипт сразу остановится и выдаст ошибку
if not BOT_TOKEN:
    raise ValueError("ОШИБКА: Токен бота не найден! Убедитесь, что вы создали файл .env и добавили туда BOT_TOKEN.")

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных курсов
# months_installment - количество месяцев для рассрочки (6 для 1-3, 3 для 4-7)
COURSES = {
    "course_1": {"name": "Курс с 0-ля", "price": 350000, "months_installment": 6},
    "course_2": {"name": "Повышение квалификации", "price": 150000, "months_installment": 6},
    "course_3": {"name": "Сложные техники окрашивания", "price": 70000, "months_installment": 6},
    "course_4": {"name": "Total Blonde", "price": 25000, "months_installment": 3},
    "course_5": {"name": "Выход из чёрного", "price": 30000, "months_installment": 3},
    "course_6": {"name": "Наращивание волос", "price": 50000, "months_installment": 3},
    "course_7": {"name": "Стрижки", "price": 30000, "months_installment": 3},
}

# Вспомогательная функция для красивого форматирования чисел (100000 -> 100 000)
def format_price(price: float) -> str:
    return f"{int(price):,.0f}".replace(",", " ")

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """
    Обработчик команды /start. Приветствует и выводит список курсов.
    """
    welcome_text = (
        "👋 <b>Добро пожаловать в нашу академию!</b>\n\n"
        "Ниже представлен список наших закрытых Telegram-каналов с курсами.\n"
        "Выберите интересующее вас направление, чтобы узнать подробности и варианты оплаты:"
    )
    
    # Создаем клавиатуру со списком курсов
    builder = InlineKeyboardBuilder()
    for course_id, course_data in COURSES.items():
        builder.button(
            text=f"🎓 {course_data['name']}",
            callback_data=f"select_{course_id}"
        )
    # Располагаем кнопки по одной в ряд
    builder.adjust(1)
    
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("select_"))
async def process_course_selection(callback: CallbackQuery):
    """
    Обработчик выбора курса. Вычисляет цены и предлагает варианты оплаты.
    """
    # Извлекаем ID курса из callback_data (например, 'course_1' из 'select_course_1')
    course_id = callback.data.replace("select_", "")
    course = COURSES.get(course_id)
    
    if not course:
        await callback.answer("Ошибка: Курс не найден.", show_alert=True)
        return

    # Логика расчетов
    base_price = course["price"]
    months = course["months_installment"]
    
    # Рассрочка: наценка 20%
    installment_total_price = base_price * 1.20
    # Ежемесячный платеж
    monthly_payment = installment_total_price / months

    # Формируем текст с предложением
    text = (
        f"Вы выбрали: <b>«{course['name']}»</b>\n\n"
        f"Доступно два варианта оплаты:\n\n"
        f"<b>1️⃣ Оплата сразу (Полная стоимость)</b>\n"
        f"Стоимость: <b>{format_price(base_price)} руб.</b>\n\n"
        
        f"<b>2️⃣ Ежемесячная оплата (на {months} месяцев)</b>\n"
        f"<i>При рассрочке общая стоимость курса увеличивается на 20% и составит {format_price(installment_total_price)} руб.</i>\n"
        f"Сумма ежемесячного платежа: <b>{format_price(monthly_payment)} руб. / мес.</b>\n\n"
        f"Выберите удобный для вас вариант:"
    )

    # Создаем клавиатуру выбора оплаты
    builder = InlineKeyboardBuilder()
    
    # Кнопка полной оплаты
    builder.button(
        text=f"💳 Оплатить сразу ({format_price(base_price)} руб.)",
        callback_data=f"pay_full_{course_id}"
    )
    # Кнопка рассрочки
    builder.button(
        text=f"🔄 Рассрочка ({format_price(monthly_payment)} руб./мес)",
        callback_data=f"pay_sub_{course_id}"
    )
    # Кнопка возврата к списку
    builder.button(
        text="🔙 Назад к списку курсов",
        callback_data="back_to_list"
    )
    builder.adjust(1) # По одной кнопке в ряд

    # Обновляем сообщение (вместо отправки нового, редактируем старое)
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку оплаты.
    """
    # Разбираем callback_data
    parts = callback.data.split("_")
    payment_type = parts[1] # 'full' или 'sub'
    course_id = f"{parts[2]}_{parts[3]}"
    course = COURSES.get(course_id)

    if payment_type == "full":
        amount = course['price']
        payment_text = (
            f"🧾 <b>Счет на оплату сформирован!</b>\n"
            f"Курс: {course['name']}\n"
            f"Тип: Единоразовый платеж\n"
            f"К оплате: <b>{format_price(amount)} руб.</b>\n\n"
            f"<i>Здесь будет кнопка ЮKassa для оплаты (send_invoice)</i>"
        )
    else:
        amount = (course['price'] * 1.20) / course['months_installment']
        payment_text = (
            f"🧾 <b>Подписка на рассрочку сформирована!</b>\n"
            f"Курс: {course['name']}\n"
            f"Тип: Ежемесячный платеж (1 из {course['months_installment']})\n"
            f"К списанию сейчас: <b>{format_price(amount)} руб.</b>\n\n"
            f"<i>Здесь будет кнопка ЮKassa для привязки карты и первого платежа. "
            f"Дальнейшие списания будут происходить автоматически.</i>"
        )

    # Клавиатура с "оплатой" (эмуляция) и кнопкой отмены
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Демо: Оплатить (ЮKassa)", callback_data="demo_success")
    builder.button(text="❌ Отмена", callback_data=f"select_{course_id}")
    builder.adjust(1)

    await callback.message.edit_text(payment_text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "demo_success")
async def demo_success_payment(callback: CallbackQuery):
    """Демонстрация успешной оплаты и выдачи ссылки"""
    text = (
        "✅ <b>Оплата успешно прошла!</b>\n\n"
        "Вот ваша персональная ссылка для доступа в закрытый канал:\n"
        "👉 https://t.me/+AbCdEfGhIjKlMnOp\n\n"
        "<i>(В реальном боте здесь будет генерироваться одноразовая пригласительная ссылка с помощью create_chat_invite_link)</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")


@dp.callback_query(F.data == "back_to_list")
async def back_to_courses(callback: CallbackQuery):
    """Возврат к списку курсов"""
    # Удаляем старое меню
    await callback.message.delete()
    # Вызываем начальное меню заново
    await cmd_start(callback.message)


# --- ЗАПУСК БОТА ---
async def main():
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    # Удаляем вебхуки и запускаем поллинг (long-polling)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
