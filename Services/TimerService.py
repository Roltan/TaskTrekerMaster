from datetime import datetime
from Services.DatabaseService import DatabaseService

class TimerService:
    def __init__(self):
        self.db = DatabaseService()
        # Храним состояние для каждого пользователя
        self.user_states = {}  # {user_id: {'time_tracker': {}, 'active_sessions': {}}}
    
    def _get_user_state(self, user_id):
        """Получение или создание состояния пользователя"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                'time_tracker': {},
                'active_sessions': {}
            }
            self._sync_memory_with_db(user_id)
        return self.user_states[user_id]
    
    def _sync_memory_with_db(self, user_id):
        """Синхронизация памяти с данными из БД для пользователя"""
        state = self._get_user_state(user_id)
        state['time_tracker'] = self.db.get_today_timers(user_id)
        state['active_sessions'] = self.db.get_active_sessions(user_id)
    
    def get_reply_keyboard(self, user_id):
        from telegram import KeyboardButton, ReplyKeyboardMarkup
        
        buttons = []
        stats_button = [KeyboardButton("📊 Статистика")]
        
        # Всегда синхронизируем с БД перед отображением
        self._sync_memory_with_db(user_id)
        state = self._get_user_state(user_id)
        
        # Проверяем активный таймер по наличию активной сессии
        active_timer_exists = bool(state['active_sessions'])
        
        if active_timer_exists:
            # Показываем только кнопку остановки активного таймера
            for timer_name in state['active_sessions'].keys():
                buttons.append([KeyboardButton(f"⏹️ Стоп {timer_name}")])
                break  # Только один активный таймер
        else:
            # Показываем кнопки старта для всех сегодняшних таймеров пользователя
            for name in state['time_tracker']:
                buttons.append([KeyboardButton(f"▶️ Старт {name}")])
        
        return ReplyKeyboardMarkup(buttons + [stats_button], resize_keyboard=True)
    
    def start_timer(self, user_id, timer_name):
        """Запуск таймера с проверкой существования в БД"""
        # Синхронизируем с БД перед операцией
        self._sync_memory_with_db(user_id)
        state = self._get_user_state(user_id)
        
        if timer_name not in state['time_tracker']:
            return f"Таймер '{timer_name}' не найден в базе данных"
        
        # Проверяем по активным сессиям
        if timer_name in state['active_sessions']:
            return f"Таймер '{timer_name}' уже запущен!"
        
        # Запуск таймера
        now = datetime.now()
        start_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Сохраняем сессию в БД
        session_id = self.db.start_timer_session(user_id, timer_name, start_time_str)
        state['active_sessions'][timer_name] = session_id
        
        return f"Таймер '{timer_name}' запущен!"
    
    def stop_timer(self, user_id, timer_name):
        """Остановка таймера с сохранением в БД"""
        # Синхронизируем с БД перед операцией
        self._sync_memory_with_db(user_id)
        state = self._get_user_state(user_id)
        
        if timer_name not in state['time_tracker']:
            return f"Таймер '{timer_name}' не найден"
        
        if timer_name not in state['active_sessions']:
            return f"Таймер '{timer_name}' не был запущен!"
        
        # Останавливаем таймер
        now = datetime.now()
        session_id = state['active_sessions'][timer_name]
        
        # Получаем время начала сессии из БД
        start_time = self.db.get_session_start_time(session_id)
        if not start_time:
            return f"Ошибка: не найдено время начала сессии для таймера '{timer_name}'"
        
        last_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        delta = now - last_time
        duration_seconds = delta.total_seconds()
        
        # Обновляем общее время в БД
        self.db.add_time_to_timer(user_id, timer_name, duration_seconds)
        
        # Завершаем сессию в БД
        end_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.db.stop_timer_session(session_id, end_time_str, duration_seconds)
        del state['active_sessions'][timer_name]
        
        # Получаем актуальные данные из БД для отчета
        timer_data = self.db.get_timer(user_id, timer_name)
        total_seconds = timer_data['total_seconds'] if timer_data else 0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return (
            f"Таймер '{timer_name}' остановлен\n"
            f"Сессия: {duration_seconds/60:.1f} минут\n"
            f"Всего времени: {hours}h {minutes}m"
        )
    
    def create_timer(self, user_id, key, task_id, type):
        """Создание таймера через БД"""
        success = self.db.create_timer(user_id, key, task_id, type)
        if success:
            return f"Таймер '{key}' готов к запуску!"
        else:
            return f"Таймер '{key}' уже существует!"
    
    def add_minutes(self, user_id, timer_name, minutes):
        """Добавление времени через БД"""
        # Синхронизируем перед операцией
        self._sync_memory_with_db(user_id)
        state = self._get_user_state(user_id)
        
        if timer_name not in state['time_tracker']:
            return f"Таймер '{timer_name}' не найден"
        
        # Добавляем время через БД
        seconds_to_add = minutes * 60
        self.db.add_time_to_timer(user_id, timer_name, seconds_to_add)
        
        # Синхронизируем после изменения
        self._sync_memory_with_db(user_id)
        
        # Получаем актуальные данные для отчета
        timer_data = self.db.get_timer(user_id, timer_name)
        total_seconds = timer_data['total_seconds'] if timer_data else 0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return (
            f"К таймеру '{timer_name}' добавлено {minutes} минут\n"
            f"Всего времени: {hours}h {minutes}m"
        )
    
    def delete_timer(self, user_id, timer_name):
        """Удаление таймера из БД"""
        # Синхронизируем перед операцией
        self._sync_memory_with_db(user_id)
        state = self._get_user_state(user_id)
        
        if timer_name not in state['time_tracker']:
            return f"Таймер '{timer_name}' не найден"
        
        # Если таймер активен, останавливаем его
        if timer_name in state['active_sessions']:
            self.stop_timer(user_id, timer_name)
        
        # Удаляем из БД
        self.db.delete_timer(user_id, timer_name)
        
        # Синхронизируем после удаления
        self._sync_memory_with_db(user_id)
        
        return f"Таймер '{timer_name}' удален!"
    
    def get_statistics(self, user_id):
        """Получение статистики по сегодняшним таймерам пользователя"""
        self._sync_memory_with_db(user_id)
        state = self._get_user_state(user_id)
        
        if not state['time_tracker']:
            return "На сегодня нет активных таймеров"
        
        stats = []
        total_day_seconds = 0

        for key in state['time_tracker']:
            # Получаем актуальные данные из БД
            timer_data = self.db.get_timer(user_id, key)
            total_seconds = timer_data['total_seconds'] if timer_data else 0
            total_day_seconds += total_seconds
            
            total_hours = total_seconds / 3600
            hours = int(total_hours)
            minutes = int((total_hours - hours) * 60)
            
            # Статус по активным сессиям
            status = "⏳" if key in state['active_sessions'] else "⏹"
            stats.append(f"{status} [{key}] {total_hours:.2f}h ({hours}h {minutes}m)")
        
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
        self._sync_memory_with_db(user_id)
        state = self._get_user_state(user_id)
        
        for timer_name in list(state['active_sessions'].keys()):
            self.stop_timer(user_id, timer_name)
        
        return "Все таймеры остановлены и кнопки очищены"
    
    def get_detailed_statistics(self, user_id, timer_name):
        """Подробная статистика по конкретному таймеру пользователя"""
        self._sync_memory_with_db(user_id)
        state = self._get_user_state(user_id)
        
        if timer_name not in state['time_tracker']:
            return f"Таймер '{timer_name}' не найден"
        
        timer_data = self.db.get_timer(user_id, timer_name)
        if not timer_data:
            return f"Данные таймера '{timer_name}' не найдены"
        
        total_seconds = timer_data['total_seconds']
        total_hours = total_seconds / 3600
        hours = int(total_hours)
        minutes = int((total_hours - hours) * 60)
        
        status = "⏳ Запущен" if timer_name in state['active_sessions'] else "⏹ Остановлен"
        
        return (
            f"📊 Детальная статистика '{timer_name}':\n"
            f"Всего времени: {total_hours:.2f}h ({hours}h {minutes}m)\n"
            f"Статус: {status}"
        )