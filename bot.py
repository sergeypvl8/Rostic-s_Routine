import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from datetime import time

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Токен бота — обязательно через переменную окружения!
API_TOKEN = os.environ["TELEGRAM_TOKEN"]

# Хранилище
user_tasks = {}

# Списки задач
MORNING_TASKS = [
    "Сделать качественный обход",
    "Подсчитай сейф и заполни журнал сейфа",
    "Заполни L3 check Mng",
    "Заполни PRODUCT FOCUS CHEK",
    "Заполни L1 Check",
    "Не забудь проверить качество жира и рассекатели",
    "Отправь отчет об обходе в чат региона",
    "Заполни вкладку ПРОДУКТЫ в DSR",
    "Заполни 3 OCL",
    "Заполни Журнал Здоровья",
    "Заполни журнал СИЗ",
    "Убедись, что DRS заполнен на 100%",
    "Посчитай сейф в конце смены с вечерним менеджером",
    "Отправь мини-пульс в чат региона",
    "Если были системки, то отправь фото в чат"
]

AFTERNOON_TASKS = [
    "Сделать качественный обход",
    "Подсчитай сейф с утренним менеджером и заполни журнал сейфа",
    "Заполни L3 check Mng",
    "Заполни PRODUCT FOCUS CHEK",
    "Заполни L1 Check",
    "Не забудь проверить качество жира, если нужно",
    "Отправь отчет об обходе в чат региона",
    "Заполни 3 OCL",
    "Заполни Журнал Здоровья",
    "Заполни журнал СИЗ",
    "Убедись, что DRS заполнен на 100%",
    "Закрой кассовую смену и собери документы",
    "Посчитай сейф в конце смены",
    "Убедись, что жир на утро качественный",
    "Отправь мини-пульс в чат региона",
    "Проверь ЗАКРЫТИЕ ПОЗИЦИЙ",
    "Не забудь сделать ЗАКАЗЫ после 00:00",
    "Заполни журнал Противопожарного осмотра ресторана",
    "Если были системки, то отправь фото в чат"
]

def create_task_keyboard(tasks, time_of_day, chat_id):
    """Создаёт клавиатуру задач."""
    if chat_id not in user_tasks:
        user_tasks[chat_id] = {}

    if time_of_day not in user_tasks[chat_id]:
        user_tasks[chat_id][time_of_day] = {i: False for i in range(len(tasks))}

    keyboard = []

    for i, task in enumerate(tasks):
        status = "✅" if user_tasks[chat_id][time_of_day][i] else "▫️"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {task}",
                callback_data=f"task_{time_of_day}_{i}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔄 Сбросить все", callback_data=f"reset_{time_of_day}")
    ])

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Привет! Я бот для ежедневных задач\n\n"
        "/morning – задачи на утро\n"
        "/afternoon – задачи на вечер\n"
        "/all – все задачи\n"
        "/set_daily – включить напоминания\n"
        "/stop_daily – выключить напоминания\n"
    )


async def task_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    data = query.data

    if data.startswith("task_"):
        _, time_of_day, idx = data.split("_")
        idx = int(idx)

        user_tasks[chat_id][time_of_day][idx] = not user_tasks[chat_id][time_of_day][idx]

        tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
        keyboard = create_task_keyboard(tasks, time_of_day, chat_id)

        await query.edit_message_reply_markup(reply_markup=keyboard)

    elif data.startswith("reset_"):
        _, time_of_day = data.split("_")
        tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
        user_tasks[chat_id][time_of_day] = {i: False for i in range(len(tasks))}

        keyboard = create_task_keyboard(tasks, time_of_day, chat_id)
        await query.edit_message_reply_markup(reply_markup=keyboard)


async def send_morning_tasks(update: Update, context):
    chat_id = update.effective_chat.id
    keyboard = create_task_keyboard(MORNING_TASKS, "morning", chat_id)
    await update.message.reply_text("📋 Задачи на утро:", reply_markup=keyboard)


async def send_afternoon_tasks(update: Update, context):
    chat_id = update.effective_chat.id
    keyboard = create_task_keyboard(AFTERNOON_TASKS, "afternoon", chat_id)
    await update.message.reply_text("📋 Задачи на вечер:", reply_markup=keyboard)


async def send_all_tasks(update: Update, context):
    chat_id = update.effective_chat.id
    await send_morning_tasks(update, context)
    await send_afternoon_tasks(update, context)


async def send_morning_daily(context):
    chat_id = context.job.chat_id
    keyboard = create_task_keyboard(MORNING_TASKS, "morning", chat_id)
    await context.bot.send_message(chat_id, "📋 Задачи на утро:", reply_markup=keyboard)


async def send_afternoon_daily(context):
    chat_id = context.job.chat_id
    keyboard = create_task_keyboard(AFTERNOON_TASKS, "afternoon", chat_id)
    await context.bot.send_message(chat_id, "📋 Задачи на вечер:", reply_markup=keyboard)


async def set_daily_tasks(update: Update, context):
    chat_id = update.effective_chat.id

    # Удаляем старые задачи
    jobs = (
        context.job_queue.get_jobs_by_name(f"{chat_id}_morning")
        + context.job_queue.get_jobs_by_name(f"{chat_id}_afternoon")
    )
    for job in jobs:
        job.schedule_removal()

    # Ставим утро и вечер
    context.job_queue.run_daily(
        send_morning_daily,
        time(hour=8, minute=0),
        chat_id=chat_id,
        name=f"{chat_id}_morning",
    )

    context.job_queue.run_daily(
        send_afternoon_daily,
        time(hour=16, minute=0),
        chat_id=chat_id,
        name=f"{chat_id}_afternoon",
    )

    await update.message.reply_text("✅ Напоминания включены!")


async def stop_daily_tasks(update: Update, context):
    chat_id = update.effective_chat.id
    jobs = (
        context.job_queue.get_jobs_by_name(f"{chat_id}_morning")
        + context.job_queue.get_jobs_by_name(f"{chat_id}_afternoon")
    )
    for job in jobs:
        job.schedule_removal()

    await update.message.reply_text("❌ Напоминания выключены!")


def main():
    application = Application.builder().token(API_TOKEN).build()

    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("morning", send_morning_tasks))
    application.add_handler(CommandHandler("afternoon", send_afternoon_tasks))
    application.add_handler(CommandHandler("all", send_all_tasks))
    application.add_handler(CommandHandler("set_daily", set_daily_tasks))
    application.add_handler(CommandHandler("stop_daily", stop_daily_tasks))
    application.add_handler(CallbackQueryHandler(task_button_callback))

    # Webhook для Render.com
    PORT = int(os.environ.get("PORT", 5000))
    WEBHOOK_URL = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{API_TOKEN}"

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=API_TOKEN,
        webhook_url=WEBHOOK_URL
    )


if __name__ == "__main__":
    main()
