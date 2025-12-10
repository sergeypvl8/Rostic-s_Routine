import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ApplicationBuilder
)
from datetime import time, datetime
import json
from pathlib import Path

# === КОНФИГУРАЦИЯ ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Токен из переменных окружения
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not API_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен в переменных окружения!")

# Проверка версии Python
import sys
logger.info(f"Python версия: {sys.version}")

# Константы
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

# === ХРАНЕНИЕ ДАННЫХ ===
class TaskStorage:
    """Класс для хранения состояния задач"""
    
    def __init__(self, storage_file="tasks_state.json"):
        self.storage_file = Path(storage_file)
        self.data = self._load_data()
    
    def _load_data(self):
        """Загрузка данных из файла"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
        return {}
    
    def _save_data(self):
        """Сохранение данных в файл"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
    
    def get_user_tasks(self, chat_id, time_of_day):
        """Получение задач пользователя"""
        if str(chat_id) not in self.data:
            self.data[str(chat_id)] = {}
        
        if time_of_day not in self.data[str(chat_id)]:
            tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
            self.data[str(chat_id)][time_of_day] = {
                str(i): False for i in range(len(tasks))
            }
            self._save_data()
        
        return self.data[str(chat_id)][time_of_day]
    
    def toggle_task(self, chat_id, time_of_day, task_index):
        """Переключение статуса задачи"""
        tasks = self.get_user_tasks(chat_id, time_of_day)
        tasks[str(task_index)] = not tasks[str(task_index)]
        self._save_data()
        return tasks[str(task_index)]
    
    def reset_tasks(self, chat_id, time_of_day):
        """Сброс всех задач"""
        tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
        self.data[str(chat_id)][time_of_day] = {
            str(i): False for i in range(len(tasks))
        }
        self._save_data()

storage = TaskStorage()

# === СОЗДАНИЕ КЛАВИАТУР ===
def create_task_keyboard(tasks, time_of_day, chat_id):
    """Создаёт клавиатуру задач с текущим состоянием"""
    user_tasks = storage.get_user_tasks(chat_id, time_of_day)
    
    keyboard = []
    for i, task in enumerate(tasks):
        status = "✅" if user_tasks.get(str(i), False) else "▫️"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {task}",
                callback_data=f"task_{time_of_day}_{i}"
            )
        ])
    
    # Кнопки управления
    keyboard.append([
        InlineKeyboardButton("🔄 Сбросить все", callback_data=f"reset_{time_of_day}"),
        InlineKeyboardButton("📊 Статистика", callback_data=f"stats_{time_of_day}")
    ])
    
    return InlineKeyboardMarkup(keyboard)

# === КОМАНДЫ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 *Привет! Я бот для ежедневных задач менеджера*

*Доступные команды:*
/morning – задачи на утро
/afternoon – задачи на вечер
/all – все задачи на сегодня
/set_daily – включить ежедневные напоминания
/stop_daily – выключить напоминания
/stats – статистика выполнения

*Как работать:*
1. Выберите список задач (утро/вечер)
2. Отмечайте выполненные задачи кликом
3. Сбрасывайте прогресс по необходимости

Удачи в работе! 🍔🚀
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def send_morning_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка задач на утро"""
    chat_id = update.effective_chat.id
    keyboard = create_task_keyboard(MORNING_TASKS, "morning", chat_id)
    
    completed = sum(1 for i in range(len(MORNING_TASKS)) 
                   if storage.get_user_tasks(chat_id, "morning").get(str(i), False))
    total = len(MORNING_TASKS)
    
    text = f"📋 *Задачи на утро*\n\nПрогресс: {completed}/{total} ({completed/total*100:.0f}%)"
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def send_afternoon_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка задач на вечер"""
    chat_id = update.effective_chat.id
    keyboard = create_task_keyboard(AFTERNOON_TASKS, "afternoon", chat_id)
    
    completed = sum(1 for i in range(len(AFTERNOON_TASKS)) 
                   if storage.get_user_tasks(chat_id, "afternoon").get(str(i), False))
    total = len(AFTERNOON_TASKS)
    
    text = f"📋 *Задачи на вечер*\n\nПрогресс: {completed}/{total} ({completed/total*100:.0f}%)"
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def send_all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка всех задач"""
    await send_morning_tasks(update, context)
    await asyncio.sleep(0.5)  # Небольшая задержка между сообщениями
    await send_afternoon_tasks(update, context)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    chat_id = update.effective_chat.id
    
    morning_completed = sum(1 for i in range(len(MORNING_TASKS)) 
                           if storage.get_user_tasks(chat_id, "morning").get(str(i), False))
    afternoon_completed = sum(1 for i in range(len(AFTERNOON_TASKS)) 
                             if storage.get_user_tasks(chat_id, "afternoon").get(str(i), False))
    
    text = f"""
📊 *Статистика выполнения*

*Утренние задачи:*
{morning_completed}/{len(MORNING_TASKS)} ({morning_completed/len(MORNING_TASKS)*100:.0f}%)

*Вечерние задачи:*
{afternoon_completed}/{len(AFTERNOON_TASKS)} ({afternoon_completed/len(AFTERNOON_TASKS)*100:.0f}%)

*Общий прогресс:*
{(morning_completed + afternoon_completed)}/{(len(MORNING_TASKS) + len(AFTERNOON_TASKS))}
({(morning_completed + afternoon_completed)/(len(MORNING_TASKS) + len(AFTERNOON_TASKS))*100:.0f}%)
    """
    await update.message.reply_text(text, parse_mode='Markdown')

# === ОБРАБОТЧИК КНОПОК ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    data = query.data
    
    if data.startswith("task_"):
        _, time_of_day, task_idx = data.split("_")
        task_idx = int(task_idx)
        
        # Переключаем задачу
        is_completed = storage.toggle_task(chat_id, time_of_day, task_idx)
        
        # Обновляем сообщение
        tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
        keyboard = create_task_keyboard(tasks, time_of_day, chat_id)
        
        # Пересчитываем прогресс
        completed = sum(1 for i in range(len(tasks)) 
                       if storage.get_user_tasks(chat_id, time_of_day).get(str(i), False))
        total = len(tasks)
        
        text = f"📋 *Задачи на {'утро' if time_of_day == 'morning' else 'вечер'}*\n\n"
        text += f"Прогресс: {completed}/{total} ({completed/total*100:.0f}%)\n"
        text += f"✓ Задача {'отмечена' if is_completed else 'снята'}"
        
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='Markdown')
    
    elif data.startswith("reset_"):
        _, time_of_day = data.split("_")
        
        # Сбрасываем задачи
        storage.reset_tasks(chat_id, time_of_day)
        
        # Обновляем сообщение
        tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
        keyboard = create_task_keyboard(tasks, time_of_day, chat_id)
        
        text = f"📋 *Задачи на {'утро' if time_of_day == 'morning' else 'вечер'}*\n\n"
        text += f"Прогресс: 0/{len(tasks)} (0%)\n"
        text += "✓ Все задачи сброшены"
        
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='Markdown')
    
    elif data.startswith("stats_"):
        _, time_of_day = data.split("_")
        
        tasks = MORNING_TASKS if time_of_day == "morning" else AFTERNOON_TASKS
        completed = sum(1 for i in range(len(tasks)) 
                       if storage.get_user_tasks(chat_id, time_of_day).get(str(i), False))
        total = len(tasks)
        
        text = f"📊 *Статистика {'утренних' if time_of_day == 'morning' else 'вечерних'} задач*\n\n"
        text += f"Выполнено: {completed}/{total}\n"
        text += f"Прогресс: {completed/total*100:.1f}%\n\n"
        
        # Показываем выполненные задачи
        if completed > 0:
            text += "*Выполнено:*\n"
            for i, task in enumerate(tasks):
                if storage.get_user_tasks(chat_id, time_of_day).get(str(i), False):
                    text += f"✅ {task}\n"
        
        await query.edit_message_text(text=text, parse_mode='Markdown')

# === ЕЖЕДНЕВНЫЕ НАПОМИНАНИЯ ===
async def send_morning_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Отправка утреннего напоминания"""
    chat_id = context.job.chat_id
    keyboard = create_task_keyboard(MORNING_TASKS, "morning", chat_id)
    
    text = "🌅 *Доброе утро!* Время отметить утренние задачи!"
    await context.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')

async def send_afternoon_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Отправка вечернего напоминания"""
    chat_id = context.job.chat_id
    keyboard = create_task_keyboard(AFTERNOON_TASKS, "afternoon", chat_id)
    
    text = "🌇 *Добрый вечер!* Проверь вечерние задачи!"
    await context.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='Markdown')

async def set_daily_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение ежедневных напоминаний"""
    chat_id = update.effective_chat.id
    
    # Удаляем старые задачи
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    
    # Устанавливаем утреннее напоминание (8:00)
    context.job_queue.run_daily(
        send_morning_reminder,
        time(hour=8, minute=0, second=0),
        chat_id=chat_id,
        name=str(chat_id)
    )
    
    # Устанавливаем вечернее напоминание (16:00)
    context.job_queue.run_daily(
        send_afternoon_reminder,
        time(hour=16, minute=0, second=0),
        chat_id=chat_id,
        name=str(chat_id)
    )
    
    await update.message.reply_text(
        "✅ *Ежедневные напоминания установлены!*\n\n"
        "Утро: 8:00\nВечер: 16:00\n\n"
        "Используйте /stop_daily для отключения.",
        parse_mode='Markdown'
    )

async def stop_daily_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отключение ежедневных напоминаний"""
    chat_id = update.effective_chat.id
    
    # Удаляем все задачи для этого чата
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    
    await update.message.reply_text(
        "❌ *Напоминания отключены.*\n\n"
        "Используйте /set_daily для повторного включения.",
        parse_mode='Markdown'
    )

# === ОСНОВНАЯ ФУНКЦИЯ ===
def main():
    """Основная функция запуска бота"""
    
    # Создаем приложение с современным билдером
    application = ApplicationBuilder() \
        .token(API_TOKEN) \
        .post_init(post_init) \
        .post_stop(post_stop) \
        .build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("morning", send_morning_tasks))
    application.add_handler(CommandHandler("afternoon", send_afternoon_tasks))
    application.add_handler(CommandHandler("all", send_all_tasks))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("set_daily", set_daily_reminders))
    application.add_handler(CommandHandler("stop_daily", stop_daily_reminders))
    
    # Добавляем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запускаем бота
    # Проверяем, работаем ли на Render
    if os.getenv("RENDER"):
        # На Render используем вебхук
        port = int(os.getenv("PORT", 5000))
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}"
        
        logger.info(f"Запуск на Render, порт: {port}, вебхук: {webhook_url}")
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=API_TOKEN,
            webhook_url=f"{webhook_url}/{API_TOKEN}"
        )
    else:
        # Локально используем polling
        logger.info("Локальный запуск с polling")
        application.run_polling()

async def post_init(application: Application):
    """Действия после инициализации"""
    logger.info("Бот инициализирован")
    logger.info(f"Всего задач: утренних - {len(MORNING_TASKS)}, вечерних - {len(AFTERNOON_TASKS)}")

async def post_stop(application: Application):
    """Действия перед остановкой"""
    logger.info("Бот останавливается...")
    storage._save_data()  # Сохраняем данные

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
