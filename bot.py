import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from Services.TimerService import TimerService
from Services.B24Service import B24Service
from Services.ReportService import ReportService

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
timer_service = TimerService()
report_service = ReportService()  # Создаем экземпляр здесь

def get_user_id(update: Update):
    """Получение ID пользователя"""
    return update.effective_user.id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    # Очищаем все активные таймеры пользователя и кнопки
    clear_result = timer_service.clear_all_timers(user_id)
    
    await update.message.reply_text(
        f"{clear_result}\n\n"
        "Используйте команды:\n"
        "/new название - создать таймер\n"
        "/plus название минуты - добавить время\n" 
        "/stats название - детальная статистика\n"
        "/delete название - удалить таймер",
        reply_markup=timer_service.get_reply_keyboard(user_id)
    )

async def new_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    if not context.args or len(context.args) < 3:
        await update.message.reply_text("Укажите название, ID и тип: /new \"название с пробелами\" id type")
        return
    
    try:
        # Последние два аргумента - это ID и type
        task_id = int(context.args[-2])
        task_type = int(context.args[-1])
        
        # Всё что между "/new" и ID - это название
        key = ' '.join(context.args[:-2])
        
    except ValueError:
        await update.message.reply_text("ID и type должны быть числами")
        return
    except Exception as e:
        await update.message.reply_text(f"Ошибка формата: {e}")
        return
    
    result = timer_service.create_timer(user_id, key, task_id, task_type)
    await update.message.reply_text(
        result,
        reply_markup=timer_service.get_reply_keyboard(user_id)
    )

async def plus_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    if len(context.args) < 2:
        await update.message.reply_text("Используйте: /plus <название> <минуты>")
        return
    
    try:
        timer_name = ' '.join(context.args[:-1])
        minutes = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("Минуты должны быть числом")
        return
    
    result = timer_service.add_minutes(user_id, timer_name, minutes)
    await update.message.reply_text(
        result,
        reply_markup=timer_service.get_reply_keyboard(user_id)
    )

async def detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    if not context.args:
        await update.message.reply_text("Укажите название: /stats название")
        return
    
    timer_name = ' '.join(context.args)
    result = timer_service.get_detailed_statistics(user_id, timer_name)
    await update.message.reply_text(result)

async def delete_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    if not context.args:
        await update.message.reply_text("Укажите название: /delete название")
        return
    
    timer_name = ' '.join(context.args)
    result = timer_service.delete_timer(user_id, timer_name)
    await update.message.reply_text(
        result,
        reply_markup=timer_service.get_reply_keyboard(user_id)
    )

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик для диалогов и кнопок"""
    user_id = get_user_id(update)
    user_message = update.message.text

    # 1. Сначала проверяем, не находимся ли мы в диалоге с ReportService
    if context.user_data.get('awaiting_task_id'):
        await report_service.handle_task_id_response(update, context)
        return
        
    if context.user_data.get('awaiting_comment'):
        await report_service.handle_comment_response(update, context)
        return

    # 2. Если не в диалоге, обрабатываем кнопки и команды
    # Обработка статистики
    if user_message == "📊 Статистика":
        stats = timer_service.get_statistics(user_id)
        await update.message.reply_text(
            stats,
            reply_markup=timer_service.get_reply_keyboard(user_id)
        )
        return
    
    # Обработка отчёта
    if user_message == "Отчёт":
        result = await report_service.tracker_all_timer(user_id, update, context)
        if result != "DIALOG_STARTED":
            await update.message.reply_text(
                result,
                reply_markup=timer_service.get_reply_keyboard(user_id)
            )
        return
    
    # Обработка кнопок старта таймеров
    if user_message.startswith("▶️ Старт "):
        timer_name = user_message.replace("▶️ Старт ", "").strip()
        result = timer_service.start_timer(user_id, timer_name)
        await update.message.reply_text(
            result,
            reply_markup=timer_service.get_reply_keyboard(user_id)
        )
        return
    
    # Обработка кнопок остановки таймеров  
    if user_message.startswith("⏹️ Стоп "):
        timer_name = user_message.replace("⏹️ Стоп ", "").strip()
        result = timer_service.stop_timer(user_id, timer_name)
        await update.message.reply_text(
            result,
            reply_markup=timer_service.get_reply_keyboard(user_id)
        )
        return
    
    # Если сообщение не распознано
    await update.message.reply_text(
        "Команда не распознана",
        reply_markup=timer_service.get_reply_keyboard(user_id)
    )

def main():
    if not TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env файле")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_timer))
    app.add_handler(CommandHandler("plus", plus_minutes))
    app.add_handler(CommandHandler("stats", detailed_stats))
    app.add_handler(CommandHandler("delete", delete_timer))
    
    # Единый обработчик для всех сообщений (кнопок и диалогов)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    
    print("Бот запущен...")
    app.run_polling()

    # Обновляем токены Битрикса
    B24Service().refreshTokens()

if __name__ == "__main__":
    main()