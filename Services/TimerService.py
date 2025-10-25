from datetime import datetime
from Services.B24Service import B24Service
from Model.User import User
from Model.Timer import Timer
from Model.Session import Session

class TimerService:
    def __init__(self):
        self.b24 = B24Service()
        self.user_model = User()
        self.timer_model = Timer()
        self.session_model = Session()
    
    def get_reply_keyboard(self, user_id):
        from telegram import KeyboardButton, ReplyKeyboardMarkup
        
        buttons = []
        stats_button = [KeyboardButton("📊 Статистика")]
        
        # Получаем активные сессии напрямую из БД
        active_sessions = self.session_model.get_active_sessions(user_id)
        
        if bool(active_sessions):
            # Показываем только кнопку остановки активного таймера
            for session in active_sessions:
                buttons.append([KeyboardButton(f"⏹️ Стоп {session['timer_name']}")])
                break  # Только один активный таймер
        else:
            # Показываем кнопки старта для всех сегодняшних таймеров пользователя
            today_timers = self.timer_model.get_today_timers(user_id)
            for timer in today_timers:
                buttons.append([KeyboardButton(f"▶️ Старт {timer['name']}")])
            buttons.append([KeyboardButton(f"Отчёт")])
        
        return ReplyKeyboardMarkup(buttons + [stats_button], resize_keyboard=True)
    
    def start_timer(self, user_id, timer_name):
        """Запуск таймера с проверкой существования в БД"""
        # Проверяем существование таймера
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            return f"Таймер '{timer_name}' не найден в базе данных"
        
        # Проверяем активные сессии для этого таймера
        active_sessions = self.session_model.get_active_sessions(user_id)
        for session in active_sessions:
            if session['timer_name'] == timer_name:
                return f"Таймер '{timer_name}' уже запущен!"
        
        # Запуск таймера
        now = datetime.now()
        
        # Сохраняем сессию в БД
        session_id = self.session_model.start_session(user_id, timer_name, now)
        if not session_id:
            return f"Ошибка при запуске таймера '{timer_name}'"
        
        return f"Таймер '{timer_name}' запущен!"
    
    def stop_timer(self, user_id, timer_name):
        """Остановка таймера с сохранением в БД"""
        # Проверяем существование таймера
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            return f"Таймер '{timer_name}' не найден"
        
        # Ищем активную сессию для этого таймера
        active_sessions = self.session_model.get_active_sessions(user_id)
        session_id = None
        for session in active_sessions:
            if session['timer_name'] == timer_name:
                session_id = session['id']
                break
        
        if not session_id:
            return f"Таймер '{timer_name}' не был запущен!"
        
        # Останавливаем таймер
        now = datetime.now()
        
        # Получаем время начала сессии из БД
        session_data = self.session_model.read_one({"id": session_id})
        if not session_data:
            return f"Ошибка: не найдены данные сессии для таймера '{timer_name}'"
        
        start_time = datetime.fromisoformat(session_data['start_time'].replace('Z', '+00:00'))
        delta = now - start_time
        duration_seconds = delta.total_seconds()
        
        # Обновляем общее время в БД
        self.timer_model.add_time_to_timer(user_id, timer_name, duration_seconds)
        
        # Завершаем сессию в БД
        success = self.session_model.stop_session(session_id, now, duration_seconds)
        if not success:
            return f"Ошибка при остановке таймера '{timer_name}'"
        
        # Получаем актуальные данные из БД для отчета
        updated_timer = self.timer_model.get_timer(user_id, timer_name)
        total_seconds = updated_timer['total_seconds'] if updated_timer else 0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return (
            f"Таймер '{timer_name}' остановлен\n"
            f"Сессия: {duration_seconds/60:.1f} минут\n"
            f"Всего времени: {hours}h {minutes}m"
        )
    
    def create_timer(self, user_id, key, task_id, timer_type):
        """Создание таймера через модель"""
        success = self.timer_model.create_timer(user_id, key, task_id, timer_type)
        if success:
            return f"Таймер '{key}' готов к запуску!"
        else:
            return f"Таймер '{key}' уже существует!"
    
    def add_minutes(self, user_id, timer_name, minutes):
        """Добавление времени через модель"""
        # Проверяем существование таймера
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            return f"Таймер '{timer_name}' не найден"
        
        # Добавляем время через модель
        seconds_to_add = minutes * 60
        self.timer_model.add_time_to_timer(user_id, timer_name, seconds_to_add)
        
        # Получаем актуальные данные для отчета
        updated_timer = self.timer_model.get_timer(user_id, timer_name)
        total_seconds = updated_timer['total_seconds'] if updated_timer else 0
        hours = int(total_seconds // 3600)
        minutes_total = int((total_seconds % 3600) // 60)
        
        return (
            f"К таймеру '{timer_name}' добавлено {minutes} минут\n"
            f"Всего времени: {hours}h {minutes_total}m"
        )
    
    def delete_timer(self, user_id, timer_name):
        """Удаление таймера из БД"""
        # Проверяем существование таймера
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            return f"Таймер '{timer_name}' не найден"
        
        # Если таймер активен, останавливаем его
        active_sessions = self.session_model.get_active_sessions(user_id)
        for session in active_sessions:
            if session['timer_name'] == timer_name:
                self.stop_timer(user_id, timer_name)
                break
        
        # Удаляем сессии таймера
        self.session_model.delete({"user_id": user_id, "timer_name": timer_name})
        
        # Удаляем сам таймер
        self.timer_model.delete({"user_id": user_id, "name": timer_name})
        
        return f"Таймер '{timer_name}' удален!"
    
    def get_statistics(self, user_id):
        """Получение статистики по сегодняшним таймерам пользователя"""
        today_timers = self.timer_model.get_today_timers(user_id)
        
        if not today_timers:
            return "На сегодня нет активных таймеров"
        
        stats = []
        total_day_seconds = 0
        active_sessions = self.session_model.get_active_sessions(user_id)
        
        # Создаем множество активных таймеров для быстрого поиска
        active_timer_names = {session['timer_name'] for session in active_sessions}

        for timer in today_timers:
            total_seconds = timer['total_seconds']
            total_day_seconds += total_seconds
            
            total_hours = total_seconds / 3600
            hours = int(total_hours)
            minutes = int((total_hours - hours) * 60)
            
            # Статус по активным сессиям
            status = "⏳" if timer['name'] in active_timer_names else "⏹"
            stats.append(f"{status} [{timer['name']}] {total_hours:.2f}h ({hours}h {minutes}m)")
        
        # Подсчёт общего времени за день
        total_day_hours = total_day_seconds / 3600
        total_day_hours_int = int(total_day_hours)
        total_day_minutes = int((total_day_hours - total_day_hours_int) * 60)
        
        # Формируем итоговую статистику
        result = [
            "📊 Статистика на сегодня:",
            *stats,
            "",
            f"📈 **Всего за день: {total_day_hours:.2f}h ({total_day_hours_int}h {total_day_minutes}m)**"
        ]
        
        return "\n".join(result)

    def clear_all_timers(self, user_id):
        """Очистка всех таймеров пользователя (для команды старт)"""
        # Останавливаем все активные таймеры
        active_sessions = self.session_model.get_active_sessions(user_id)
        
        for session in active_sessions:
            self.stop_timer(user_id, session['timer_name'])
        
        return "Все таймеры остановлены и кнопки очищены"