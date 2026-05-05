from Class.Controller import Controller
from telegram import Update
from telegram.ext import ContextTypes
from Services.SubTimerService import SubTimerService

class TimerController(Controller):
    def __init__(self):
        super().__init__()
        self.sub_timer_service = SubTimerService()

    async def baby_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки BabyTime"""
        user_id = self.get_user_id(update)
        result = self.timer_service.baby_time(user_id)
        keyboard = self.timer_service.get_reply_keyboard(user_id)
        await update.message.reply_text(result, reply_markup=keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = self.get_user_id(update)
        clear_result = self.timer_service.clear_all_timers(user_id)
        
        message = (
            f"{clear_result}\n\n"
            "Используйте команды:\n"
            "/new название - создать таймер\n"
            "/plus название минуты - добавить время\n" 
            "/diff название минуты - убавить время\n" 
            "/delete название - удалить таймер\n"
        )
        await self.send_response(update, message)
    
    async def create_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /new"""
        user_id = self.get_user_id(update)
        
        # Валидация
        if not context.args or len(context.args) < 3:
            await self.send_response(update, "Укажите название, ID и тип: /new \"название с пробелами\" id type")
            return
        
        try:
            # Парсинг аргументов
            task_id = int(context.args[-2])
            task_type = int(context.args[-1])
            key = ' '.join(context.args[:-2])
            
            # Валидация типа
            if task_type not in [0, 1, 2, 3]:
                await self.send_response(update, "Тип должен быть числом от 0 до 3")
                return
                
        except ValueError:
            await self.send_response(update, "ID и type должны быть числами")
            return
        except Exception as e:
            await self.send_response(update, f"Ошибка формата: {e}")
            return
        
        # Вызов сервиса
        result = self.timer_service.create_timer(user_id, key, task_id, task_type)
        await self.send_response(update, result)
    
    async def add_minutes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /plus"""
        user_id = self.get_user_id(update)
        
        # Валидация
        if len(context.args) < 2:
            await self.send_response(update, "Используйте:\n/plus <название> <минуты>\n/plus <родитель:подтаймер> <минуты>")
            return
        
        try:
            timer_name = ' '.join(context.args[:-1])
            minutes = int(context.args[-1])
            
            # Валидация минут
            if minutes <= 0:
                await self.send_response(update, "Минуты должны быть положительным числом")
                return
                
        except ValueError:
            await self.send_response(update, "Минуты должны быть числом")
            return
        
        # Проверяем, является ли это под-таймером (формат "родитель:подтаймер")
        if ':' in timer_name:
            # Это под-таймер
            parts = timer_name.split(':')
            if len(parts) != 2:
                await self.send_response(update, "Неверный формат. Используйте: /plus родитель:подтаймер минуты")
                return
            
            parent_timer_name, sub_timer_name = parts[0].strip(), parts[1].strip()
            
            if not parent_timer_name or not sub_timer_name:
                await self.send_response(update, "Не указано название родителя или под-таймера")
                return
            
            # Вызываем метод для добавления времени к под-таймеру через TimerService
            result = self.timer_service.add_minutes_to_sub_timer(user_id, parent_timer_name, sub_timer_name, minutes)
            await self.send_response(update, result)
        else:
            # Это обычный таймер
            # Вызов сервиса
            result = self.timer_service.add_minutes(user_id, timer_name, minutes)
            await self.send_response(update, result)

    async def diff_minutes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /diff"""
        user_id = self.get_user_id(update)
        
        # Валидация
        if len(context.args) < 2:
            await self.send_response(update, "Используйте:\n/diff <название> <минуты>\n/diff <родитель:подтаймер> <минуты>")
            return
        
        try:
            timer_name = ' '.join(context.args[:-1])
            minutes = int(context.args[-1])
            
            # Валидация минут
            if minutes <= 0:
                await self.send_response(update, "Минуты должны быть положительным числом")
                return
                
        except ValueError:
            await self.send_response(update, "Минуты должны быть числом")
            return
        
        # Проверяем, является ли это под-таймером (формат "родитель:подтаймер")
        if ':' in timer_name:
            # Это под-таймер
            parts = timer_name.split(':')
            if len(parts) != 2:
                await self.send_response(update, "Неверный формат. Используйте: /diff родитель:подтаймер минуты")
                return
            
            parent_timer_name, sub_timer_name = parts[0].strip(), parts[1].strip()
            
            if not parent_timer_name or not sub_timer_name:
                await self.send_response(update, "Не указано название родителя или под-таймера")
                return
            
            # Вызываем метод для вычитания времени из под-таймера (отрицательное значение)
            result = self.timer_service.add_minutes_to_sub_timer(user_id, parent_timer_name, sub_timer_name, -minutes)
            await self.send_response(update, result)
        else:
            # Это обычный таймер
            # Вызов сервиса с отрицательным значением
            result = self.timer_service.add_minutes(user_id, timer_name, -1 * minutes)
            await self.send_response(update, result)
    
    async def delete_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /delete"""
        user_id = self.get_user_id(update)
        
        # Валидация
        if not context.args:
            await self.send_response(update, "Укажите название: /delete название")
            return
        
        timer_name = ' '.join(context.args)
        
        # Вызов сервиса
        result = self.timer_service.delete_timer(user_id, timer_name)
        await self.send_response(update, result)
    
    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки статистики"""
        user_id = self.get_user_id(update)
        stats = self.timer_service.get_statistics(user_id)
        await self.send_response(update, stats)
    
    async def start_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки старта таймера"""
        user_id = self.get_user_id(update)
        timer_name = update.message.text.replace("▶️ Старт ", "").strip()
        
        # Сначала проверяем, не пытается ли пользователь запустить под-таймер в режиме папки
        # if self.timer_service.folder_service.is_in_folder_mode(user_id):
        #     # Пользователь в режиме папки - передаем управление в FolderController
        #     from Controllers.FolderController import FolderController
        #     folder_controller = FolderController()
        #     await folder_controller.start_sub_timer(update, context)
        #     return
        
        # Если не в режиме папки, продолжаем обычную логику
        if not timer_name:
            await self.send_response(update, "Не указано название таймера")
            return
        
        # Вызов сервиса
        result = self.timer_service.start_timer(user_id, timer_name)
        await self.send_response(update, result)
    
    async def stop_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки остановки таймера"""
        user_id = self.get_user_id(update)
        timer_name = update.message.text.replace("⏹️ Стоп ", "").strip()
        
        # Валидация
        if not timer_name:
            await self.send_response(update, "Не указано название таймера")
            return
        
        # Вызов сервиса
        result = self.timer_service.stop_timer(user_id, timer_name)
        await self.send_response(update, result)