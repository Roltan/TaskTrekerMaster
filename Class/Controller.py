from telegram import Update
from telegram.ext import ContextTypes
from Services.TimerService import TimerService

class Controller:
    def __init__(self):
        self.timer_service = TimerService()
    
    def get_user_id(self, update: Update):
        """Получение ID пользователя"""
        return update.effective_user.id
    
    async def send_response(self, update: Update, message: str):
        """Отправка ответа с клавиатурой"""
        user_id = self.get_user_id(update)
        await update.message.reply_text(
            message,
            reply_markup=self.timer_service.get_reply_keyboard(user_id)
        )