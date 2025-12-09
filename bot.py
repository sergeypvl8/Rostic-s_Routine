import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, CallbackContext
from datetime import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

API_TOKEN = os.environ.get('TELEGRAM_TOKEN', '7306181828:AAH7aa9zHAv9V0PW-yxJgtiFo_Pq42SSOzI')

# Храним статус задач для каждого пользователя
user_tasks = {}

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
    "Если были системки, то отправь в фото в чат"
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
    "Закрой кассовую смены и собери документы",
    "Посчитай сейф в конце смены",
    "Убедись, что жир на утро качественный",
    "Отправь мини-пульс в чат региона",
    "Проверь ЗАКРЫТИЕ ПОЗИЦИЙ",
    "не забудь сделать ЗАКАЗЫ после 00:00",
    "Заполни журнал Противопожарного осмотра ресторана", 
    "Если были системки, то отправь в фото в чат"
]

def create_task_keyboard(tasks, time_of_day, chat_id):
    keyboard = []
    
    if chat_id not in user_tasks:
        user_tasks[chat_id] = {}
    if time_of_day not in user_tasks[chat_id]:
        user_tasks[chat_id][time_of_day] = {i: False for i in range(len(tasks))}
    
    for i, task in enumerate(tasks):
        status = "✅" if user_tasks[chat_id][time_of_day][i] else "▫️"
        keyboard.append([InlineKeyboardButton(f"{status} {task}", callback_data=f"task_{time_of_day}_{i}")])
    
    keyboard.append([InlineKeyboardButton("🔄 Сбросить все", callback_data=f"reset_{time_of_day}")])
    
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я буду присылать тебе задачи с возможностью отметки:\n"
        "• Утром в 8:00 - задачи на первую половину дня\n"
        "• Днем в 16:00 - задачи на вторую половину дня\n\n"
        "Используй /morning для утренних задач\n"
        "Используй /afternoon для вечерних задач\n"
        "Используй /all для всех задач сразу\n"
        "Используй /set_daily для автоматических напоминаний"
    )

async def task_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    
    if data.startswith("task_"):
        _, time_of_day, task_index = data.split("_")
        task_index = int(task_index)
        
        user_tasks[chat_id][time_of_day][task_index] = not user_tasks[chat_id][time_of_day][task_index]
        
        tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
        keyboard = create_task_keyboard(tasks, time_of_day, chat_id)
        
        await query.edit_message_reply_markup(reply_markup=keyboard)
    
    elif data.startswith("reset_"):
        _, time_of_day = data.split("_")
        tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
        user_tasks[chat_id][time_of_day] = {i: False for i in range(len(tasks))}
        
        keyboard = create_task_keyboard(tasks, time_of_day, chat_id)
        await query.edit_message_reply_markup(reply_markup=keyboard)

async def send_morning_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keyboard = create_task_keyboard(MORNING_TASKS, "morning", chat_id)
    await update.message.reply_text("📋 Задачи на утро:", reply_markup=keyboard)

async def send_afternoon_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    keyboard = create_task_keyboard(AFTERNOON_TASKS, "afternoon", chat_id)
    await update.message.reply_text("📋 Задачи на вечер:", reply_markup=keyboard)

async def send_all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    morning_keyboard = create_task_keyboard(MORNING_TASKS, "morning", chat_id)
    afternoon_keyboard = create_task_keyboard(AFTERNOON_TASKS, "afternoon", chat_id)
    
    await update.message.reply_text("📋 Задачи на утро:", reply_markup=morning_keyboard)
    await update.message.reply_text("📋 Задачи на вечер:", reply_markup=afternoon_keyboard)

async def send_morning_daily(context: CallbackContext):
    chat_id = context.job.chat_id
    try:
        keyboard = create_task_keyboard(MORNING_TASKS, "morning", chat_id)
        await context.bot.send_message(chat_id=chat_id, text="📋 Задачи на утро:", reply_markup=keyboard)
        logger.info(f"Отправили утренние задачи в чат {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки утренних задач: {e}")

async def send_afternoon_daily(context: CallbackContext):
    chat_id = context.job.chat_id
    try:
        keyboard = create_task_keyboard(AFTERNOON_TASKS, "afternoon", chat_id)
        await context.bot.send_message(chat_id=chat_id, text="📋 Задачи на вечер:", reply_markup=keyboard)
        logger.info(f"Отправили вечерние задачи в чат {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки вечерних задач: {e}")

async def set_daily_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # Удаляем старые jobs если есть
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    
    # Устанавливаем утренние задачи в 8:00
    context.job_queue.run_daily(
        send_morning_daily,
        time(hour=8, minute=0),
        chat_id=chat_id,
        name=f"{chat_id}_morning"
    )
    
    # Устанавливаем вечерние задачи в 16:00
    context.job_queue.run_daily(
        send_afternoon_daily, 
        time(hour=16, minute=0),
        chat_id=chat_id,
        name=f"{chat_id}_afternoon"
    )
    
    await update.message.reply_text(
        "✅ Напоминания установлены!\n"
        "Буду присылать:\n"
        "• Утренние задачи в 8:00\n"
        "• Вечерние задачи в 16:00\n\n"
        "Используй:\n"
        "/morning - утренние задачи\n"
        "/afternoon - вечерние задачи\n"
        "/all - все задачи сразу"
    )

async def stop_daily_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_jobs = context.job_queue.get_jobs_by_name(f"{chat_id}_morning")
    current_jobs += context.job_queue.get_jobs_by_name(f"{chat_id}_afternoon")
    
    for job in current_jobs:
        job.schedule_removal()
    
    await update.message.reply_text("❌ Ежедневные напоминания остановлены")

def main():
    application = Application.builder().token(API_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("morning", send_morning_tasks))
    application.add_handler(CommandHandler("afternoon", send_afternoon_tasks))
    application.add_handler(CommandHandler("all", send_all_tasks))
    application.add_handler(CommandHandler("set_daily", set_daily_tasks))
    application.add_handler(CommandHandler("stop_daily", stop_daily_tasks))
    application.add_handler(CallbackQueryHandler(task_button_callback))
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
