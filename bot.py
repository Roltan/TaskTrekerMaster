import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from Services.TimerService import TimerService

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
timer_service = TimerService()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # База данных автоматически создается при инициализации DatabaseService
    # Очищаем все активные таймеры и кнопки
    clear_result = timer_service.clear_all_timers()
    
    # Получаем количество сегодняшних таймеров
    today_timers_count = len(timer_service.time_tracker)
    
    await update.message.reply_text(
        f"{clear_result}\n"
        f"📅 Загружено таймеров на сегодня: {today_timers_count}\n\n"
        "Используйте команды:\n"
        "/new название - создать таймер\n"
        "/plus название минуты - добавить время\n" 
        "/stats название - детальная статистика\n"
        "/delete название - удалить таймер",
        reply_markup=timer_service.get_reply_keyboard()
    )

async def new_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите название: /new название")
        return
    
    key = ' '.join(context.args)
    result = timer_service.create_timer(key)
    await update.message.reply_text(
        result,
        reply_markup=timer_service.get_reply_keyboard()
    )

async def plus_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Используйте: /plus <название> <минуты>")
        return
    
    try:
        timer_name = ' '.join(context.args[:-1])
        minutes = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("Минуты должны быть числом")
        return
    
    result = timer_service.add_minutes(timer_name, minutes)
    await update.message.reply_text(
        result,
        reply_markup=timer_service.get_reply_keyboard()
    )

async def detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите название: /stats название")
        return
    
    timer_name = ' '.join(context.args)
    result = timer_service.get_detailed_statistics(timer_name)
    await update.message.reply_text(result)

async def delete_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите название: /delete название")
        return
    
    timer_name = ' '.join(context.args)
    result = timer_service.delete_timer(timer_name)
    await update.message.reply_text(
        result,
        reply_markup=timer_service.get_reply_keyboard()
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    # Обработка статистики
    if user_message == "📊 Статистика":
        stats = timer_service.get_statistics()
        await update.message.reply_text(
            stats,
            reply_markup=timer_service.get_reply_keyboard()
        )
        return
    
    # Обработка кнопок таймеров
    for timer_name in timer_service.time_tracker:
        if user_message == f"▶️ Старт {timer_name}":
            result = timer_service.start_timer(timer_name)
            await update.message.reply_text(
                result,
                reply_markup=timer_service.get_reply_keyboard()
            )
            return
            
        elif user_message == f"⏹️ Стоп {timer_name}":
            result = timer_service.stop_timer(timer_name)
            await update.message.reply_text(
                result,
                reply_markup=timer_service.get_reply_keyboard()
            )
            return

def main():
    if not TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env файле")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_timer))
    app.add_handler(CommandHandler("plus", plus_minutes))
    app.add_handler(CommandHandler("stats", detailed_stats))
    app.add_handler(CommandHandler("delete", delete_timer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()