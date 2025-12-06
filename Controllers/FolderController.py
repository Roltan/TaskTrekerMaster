from Class.Controller import Controller
from telegram import Update
from telegram.ext import ContextTypes
from Model.Timer import Timer
from Model.SubTimer import SubTimer
from Services.SubTimerRunnerService import SubTimerRunnerService

class FolderController(Controller):
    def __init__(self):
        super().__init__()
        self.timer_model = Timer()
        self.sub_timer_model = SubTimer()
        self.sub_timer_runner = SubTimerRunnerService()
    
    async def enter_folder_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Вход в режим папки (нажатие на папку)"""
        user_id = self.get_user_id(update)
        timer_name = update.message.text.replace("📁 ", "").strip()
        
        if not timer_name:
            await self.send_response(update, "Ошибка: не указано название таймера")
            return
        
        # Проверяем, что таймер существует и у него есть под-таймеры
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            await self.send_response(update, f"Таймер '{timer_name}' не найден")
            return
        
        sub_timers = self.sub_timer_model.read({"user_id": user_id, "parent_timer_name": timer_name})
        if not sub_timers:
            await self.send_response(update, f"У таймера '{timer_name}' нет под-таймеров")
            return
        
        # Переключаем в режим папки
        self.timer_service.folder_service.set_folder_mode(user_id, timer_name)
        
        await self.send_response(update, f"📂 Режим папки: {timer_name}\nВыберите под-таймер для запуска:")
    
    async def exit_folder_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выход из режима папки (кнопка Назад)"""
        user_id = self.get_user_id(update)
        
        # Возвращаем в нормальный режим
        self.timer_service.folder_service.set_normal_mode(user_id)
        
        await self.send_response(update, "Возврат к списку таймеров")
    
    async def start_sub_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск под-таймера в режиме папки"""
        user_id = self.get_user_id(update)
        
        # Проверяем, что пользователь в режиме папки
        if not self.timer_service.folder_service.is_in_folder_mode(user_id):
            await self.send_response(update, "Ошибка: не в режиме папки")
            return
        
        sub_timer_name = update.message.text.replace("▶️ Старт ", "").strip()
        
        if not sub_timer_name:
            await self.send_response(update, "Не указано название под-таймера")
            return
        
        # Получаем родительский таймер
        user_mode = self.timer_service.folder_service.get_mode(user_id)
        parent_timer_name = user_mode['parent_timer']
        
        if not parent_timer_name:
            await self.send_response(update, "Ошибка: родительский таймер не найден")
            return
        
        # Проверяем существование под-таймера перед запуском
        sub_timers = self.sub_timer_model.read({
            "user_id": user_id,
            "parent_timer_name": parent_timer_name,
            "name": sub_timer_name
        })
        
        if not sub_timers:
            await self.send_response(update, f"Под-таймер '{sub_timer_name}' не найден в папке '{parent_timer_name}'")
            return
        
        # Запускаем под-таймер
        result = self.sub_timer_runner.start_sub_timer(user_id, parent_timer_name, sub_timer_name)
        
        if result:
            await self.send_response(update, result)
        else:
            await self.send_response(update, f"❌ Ошибка при запуске под-таймера '{sub_timer_name}'")
    
    async def stop_sub_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановка под-таймера в режиме папки"""
        user_id = self.get_user_id(update)
        
        # Проверяем, что пользователь в режиме папки
        if not self.timer_service.folder_service.is_in_folder_mode(user_id):
            await self.send_response(update, "Ошибка: не в режиме папки")
            return
        
        sub_timer_name = update.message.text.replace("⏹️ Стоп ", "").strip()
        
        if not sub_timer_name:
            await self.send_response(update, "Не указано название под-таймера")
            return
        
        # Получаем родительский таймер
        user_mode = self.timer_service.folder_service.get_mode(user_id)
        parent_timer_name = user_mode['parent_timer']
        
        if not parent_timer_name:
            await self.send_response(update, "Ошибка: родительский таймер не найден")
            return
        
        # Останавливаем под-таймер
        result = self.sub_timer_runner.stop_sub_timer(user_id, parent_timer_name, sub_timer_name)
        await self.send_response(update, result)

    async def start_parent_timer_in_folder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск родительского таймера из режима папки"""
        user_id = self.get_user_id(update)
        
        # Проверяем, что пользователь в режиме папки
        if not self.timer_service.folder_service.is_in_folder_mode(user_id):
            await self.send_response(update, "Ошибка: не в режиме папки")
            return
        
        # Получаем родительский таймер из состояния
        user_mode = self.timer_service.folder_service.get_mode(user_id)
        parent_timer_name = user_mode['parent_timer']
        
        if not parent_timer_name:
            await self.send_response(update, "Ошибка: родительский таймер не найден")
            return
        
        # Запускаем родительский таймер
        result = self.timer_service.start_timer(user_id, parent_timer_name)
        
        # При запуске родительского таймера выходим из режима папки
        self.timer_service.folder_service.set_normal_mode(user_id)
        
        await self.send_response(update, result)