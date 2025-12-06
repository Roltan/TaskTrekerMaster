from Class.Controller import Controller
from telegram import Update
from telegram.ext import ContextTypes
from Services.SubTimerService import SubTimerService

class SubTimerController(Controller):
    def __init__(self):
        super().__init__()
        self.sub_timer_service = SubTimerService()
    
    async def create_sub_timer_dialog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало диалога создания под-таймера"""
        user_id = self.get_user_id(update)
        
        # Проверяем, есть ли активный таймер
        active_sessions = self.session_model.get_active_sessions(user_id)
        if not active_sessions:
            await self.send_response(update, "Нет активного таймера для создания под-таймера")
            return
        
        parent_timer_name = active_sessions[0]['timer_name']
        
        # Сохраняем данные в контексте
        context.user_data['awaiting_sub_timer_name'] = True
        context.user_data['parent_timer_name'] = parent_timer_name
        
        await self.send_response(update, f"Введите название для под-таймера (родитель: {parent_timer_name}):")
    
    async def handle_sub_timer_name_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка названия под-таймера от пользователя"""
        user_id = self.get_user_id(update)
        sub_timer_name = update.message.text.strip()
        
        if not sub_timer_name:
            await self.send_response(update, "Название не может быть пустым")
            return
        
        parent_timer_name = context.user_data.get('parent_timer_name')
        
        if not parent_timer_name:
            await self.send_response(update, "Ошибка: не найден родительский таймер")
            return
        
        # Проверяем, что родительский таймер все еще активен
        active_sessions = self.session_model.get_active_sessions(user_id)
        if not active_sessions or active_sessions[0]['timer_name'] != parent_timer_name:
            await self.send_response(update, "Родительский таймер больше не активен")
            return
        
        # Рассчитываем время для нового под-таймера
        duration_seconds = self.sub_timer_service.calculate_new_sub_timer_duration(user_id, parent_timer_name)
        
        if duration_seconds <= 0:
            await self.send_response(update, "Нет времени для записи в под-таймер")
            return
        
        # Создаем под-таймер
        success = self.sub_timer_service.create_sub_timer(
            user_id, 
            parent_timer_name, 
            sub_timer_name, 
            duration_seconds
        )
        
        if success:
            # Очищаем состояние диалога
            context.user_data.pop('awaiting_sub_timer_name', None)
            context.user_data.pop('parent_timer_name', None)
            
            minutes = duration_seconds / 60
            await self.send_response(update, f"✅ Под-таймер '{sub_timer_name}' создан с временем {int(round(minutes))} минут")
        else:
            await self.send_response(update, f"❌ Ошибка при создании под-таймера")