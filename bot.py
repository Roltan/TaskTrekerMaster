import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from Controllers.TimerController import TimerController
from Controllers.ReportController import ReportController
from Controllers.SubTimerController import SubTimerController
from Controllers.FolderController import FolderController
from Services.B24Service import B24Service

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Создаем контроллеры
timer_controller = TimerController()
report_controller = ReportController()
sub_timer_controller = SubTimerController()
folder_controller = FolderController()

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик для диалогов и кнопок"""
    user_message = update.message.text

    # 1. Сначала проверяем, не находимся ли мы в диалоге
    if context.user_data.get('awaiting_task_id'):
        await report_controller.handle_task_id_response(update, context)
        return
        
    if context.user_data.get('awaiting_comment'):
        await report_controller.handle_comment_response(update, context)
        return
    
    # 2. Добавляем обработку диалога создания под-таймера
    if context.user_data.get('awaiting_sub_timer_name'):
        await sub_timer_controller.handle_sub_timer_name_response(update, context)
        return

    # 3. Обрабатываем специальные кнопки (не зависящие от режима)
    if user_message == "📊 Статистика":
        await timer_controller.show_statistics(update, context)
        return
    
    if user_message == "Отчёт":
        await report_controller.generate_report(update, context)
        return
    
    if user_message == "📁 Создать под-таймер":
        await sub_timer_controller.create_sub_timer_dialog(update, context)
        return
    
    # 4. Проверяем режим папки
    user_id = update.effective_user.id
    timer_service = timer_controller.timer_service
    
    if timer_service.folder_service.is_in_folder_mode(user_id):
        # РЕЖИМ ПАПКИ
        if user_message.startswith("▶️ Старт "):
            await folder_controller.start_sub_timer(update, context)
            return
        
        if user_message.startswith("⏹️ Стоп "):
            await folder_controller.stop_sub_timer(update, context)
            return
        
        if user_message.startswith("▶️ Запустить "):
            await folder_controller.start_parent_timer_in_folder(update, context)
            return
        
        if user_message == "🔙 Назад к таймерам":
            await folder_controller.exit_folder_mode(update, context)
            return
    else:
        # НОРМАЛЬНЫЙ РЕЖИМ
        if user_message.startswith("▶️ Старт "):
            await timer_controller.start_timer(update, context)
            return
        
        if user_message.startswith("⏹️ Стоп "):
            await timer_controller.stop_timer(update, context)
            return
        
        if user_message.startswith("📁 "):
            await folder_controller.enter_folder_mode(update, context)
            return
    
    # Если сообщение не распознано
    await timer_controller.send_response(update, "Команда не распознана")

def main():
    if not TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env файле")
        return
    
    # Обновляем токены Битрикса
    B24Service().refreshTokens()
    
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", timer_controller.start))
    app.add_handler(CommandHandler("new", timer_controller.create_timer))
    app.add_handler(CommandHandler("plus", timer_controller.add_minutes))
    app.add_handler(CommandHandler("delete", timer_controller.delete_timer))
    app.add_handler(CommandHandler("diff", timer_controller.diff_minutes))
    
    # Единый обработчик для всех сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()