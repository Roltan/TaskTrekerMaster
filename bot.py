import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from Services.TimerService import TimerService

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
timerService = TimerService()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используйте /new название для создания таймера",
        reply_markup=timerService.get_reply_keyboard()
    )

async def new_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите название: /new название")
        return
    
    key = ' '.join(context.args)
    result = timerService.create_timer(key)
    await update.message.reply_text(
        result,
        reply_markup=timerService.get_reply_keyboard()
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
    
    result = timerService.add_minutes(timer_name, minutes)
    await update.message.reply_text(
        result,
        reply_markup=timerService.get_reply_keyboard()
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    # Обработка статистики
    if user_message == "📊 Статистика":
        stats = timerService.get_statistics()
        await update.message.reply_text(
            stats,
            reply_markup=timerService.get_reply_keyboard()
        )
        return
    
    # Обработка кнопок таймеров
    for timer_name in timerService.time_tracker:
        if user_message == f"▶️ Старт {timer_name}":
            result = timerService.start_timer(timer_name)
            await update.message.reply_text(
                result,
                reply_markup=timerService.get_reply_keyboard()
            )
            return
            
        elif user_message == f"⏹️ Стоп {timer_name}":
            result = timerService.stop_timer(timer_name)
            await update.message.reply_text(
                result,
                reply_markup=timerService.get_reply_keyboard()
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()