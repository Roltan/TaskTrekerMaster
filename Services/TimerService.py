from datetime import datetime
from Services.DatabaseService import DatabaseService

class TimerService:
    def __init__(self):
        self.db = DatabaseService()
        self._sync_memory_with_db()
        self.active_timer = None
        self.active_sessions = {}
    
    def _sync_memory_with_db(self):
        """Синхронизация памяти с данными из БД"""
        self.time_tracker = self.db.get_today_timers()
        # Получаем активные сессии из БД
        self.active_sessions = self.db.get_active_sessions()
    
    def get_reply_keyboard(self):
        from telegram import KeyboardButton, ReplyKeyboardMarkup
        
        buttons = []
        stats_button = [KeyboardButton("📊 Статистика")]
        
        # Всегда синхронизируем с БД перед отображением
        self._sync_memory_with_db()
        
        # 🔥 ИСПРАВЛЕНИЕ: Проверяем активный таймер по наличию активной сессии
        active_timer_exists = bool(self.active_sessions)
        
        if active_timer_exists:
            # Показываем только кнопку остановки активного таймера
            for timer_name in self.active_sessions.keys():
                buttons.append([KeyboardButton(f"⏹️ Стоп {timer_name}")])
                break  # Только один активный таймер
        else:
            # Показываем кнопки старта для всех сегодняшних таймеров
            for name in self.time_tracker:
                buttons.append([KeyboardButton(f"▶️ Старт {name}")])
        
        return ReplyKeyboardMarkup(buttons + [stats_button], resize_keyboard=True)
    
    def start_timer(self, timer_name):
        """Запуск таймера с проверкой существования в БД"""
        # Синхронизируем с БД перед операцией
        self._sync_memory_with_db()
        
        if timer_name not in self.time_tracker:
            return f"Таймер '{timer_name}' не найден в базе данных"
        
        # 🔥 ИСПРАВЛЕНИЕ: Проверяем по активным сессиям
        if timer_name in self.active_sessions:
            return f"Таймер '{timer_name}' уже запущен!"
        
        # Запуск таймера
        now = datetime.now()
        start_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Сохраняем сессию в БД
        session_id = self.db.start_timer_session(timer_name, start_time_str)
        self.active_sessions[timer_name] = session_id
        
        return f"Таймер '{timer_name}' запущен!"
    
    def stop_timer(self, timer_name):
        """Остановка таймера с сохранением в БД"""
        # Синхронизируем с БД перед операцией
        self._sync_memory_with_db()
        
        if timer_name not in self.time_tracker:
            return f"Таймер '{timer_name}' не найден"
        
        # 🔥 ИСПРАВЛЕНИЕ: Проверяем по активным сессиям
        if timer_name not in self.active_sessions:
            return f"Таймер '{timer_name}' не был запущен!"
        
        # Останавливаем таймер
        now = datetime.now()
        session_id = self.active_sessions[timer_name]
        
        # Получаем время начала сессии из БД
        start_time = self.db.get_session_start_time(session_id)
        if not start_time:
            return f"Ошибка: не найдено время начала сессии для таймера '{timer_name}'"
        
        last_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        delta = now - last_time
        duration_seconds = delta.total_seconds()
        
        # Обновляем общее время в БД
        self.db.add_time_to_timer(timer_name, duration_seconds)
        
        # Завершаем сессию в БД
        end_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.db.stop_timer_session(session_id, end_time_str, duration_seconds)
        del self.active_sessions[timer_name]
        
        # Получаем актуальные данные из БД для отчета
        timer_data = self.db.get_timer(timer_name)
        total_seconds = timer_data['total_seconds'] if timer_data else 0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return (
            f"Таймер '{timer_name}' остановлен\n"
            f"Сессия: {duration_seconds/60:.1f} минут\n"
            f"Всего времени: {hours}h {minutes}m"
        )
    
    def create_timer(self, key):
        """Создание таймера через БД"""
        success = self.db.create_timer(key)
        if success:
            # Синхронизируем с БД после создания
            self._sync_memory_with_db()
            return f"Таймер '{key}' готов к запуску!"
        else:
            return f"Таймер '{key}' уже существует!"
    
    def add_minutes(self, timer_name, minutes):
        """Добавление времени через БД"""
        # Синхронизируем перед операцией
        self._sync_memory_with_db()
        
        if timer_name not in self.time_tracker:
            return f"Таймер '{timer_name}' не найден"
        
        # Добавляем время через БД
        seconds_to_add = minutes * 60
        self.db.add_time_to_timer(timer_name, seconds_to_add)
        
        # Синхронизируем после изменения
        self._sync_memory_with_db()
        
        # Получаем актуальные данные для отчета
        timer_data = self.db.get_timer(timer_name)
        total_seconds = timer_data['total_seconds'] if timer_data else 0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return (
            f"К таймеру '{timer_name}' добавлено {minutes} минут\n"
            f"Всего времени: {hours}h {minutes}m"
        )
    
    def delete_timer(self, timer_name):
        """Удаление таймера из БД"""
        # Синхронизируем перед операцией
        self._sync_memory_with_db()
        
        if timer_name not in self.time_tracker:
            return f"Таймер '{timer_name}' не найден"
        
        # Если таймер активен, останавливаем его
        if timer_name in self.active_sessions:
            self.stop_timer(timer_name)
        
        # Удаляем из БД
        self.db.delete_timer(timer_name)
        
        # Синхронизируем после удаления
        self._sync_memory_with_db()
        
        return f"Таймер '{timer_name}' удален!"
    
    def get_statistics(self):
        """Получение статистики по сегодняшним таймерам"""
        self._sync_memory_with_db()
        
        if not self.time_tracker:
            return "На сегодня нет активных таймеров"
        
        stats = []
        for key, data in self.time_tracker.items():
            # Получаем актуальные данные из БД
            timer_data = self.db.get_timer(key)
            if timer_data:
                total_seconds = timer_data['total_seconds']
            else:
                total_seconds = 0
            
            total_hours = total_seconds / 3600
            hours = int(total_hours)
            minutes = int((total_hours - hours) * 60)
            
            # 🔥 ИСПРАВЛЕНИЕ: Статус по активным сессиям
            status = "⏳" if key in self.active_sessions else "⏹"
            stats.append(f"{status} [{key}] {total_hours:.2f}h ({hours}h {minutes}m)")
        
        return "📊 Статистика на сегодня:\n" + "\n".join(stats)
    
    def clear_all_timers(self):
        """Очистка всех таймеров (для команды старт)"""
        # Останавливаем все активные таймеры
        for timer_name in list(self.active_sessions.keys()):
            self.stop_timer(timer_name)
        
        return "Все таймеры остановлены и кнопки очищены"
    
    def has_active_timer(self):
        """Проверка активных таймеров через БД"""
        self._sync_memory_with_db()
        return bool(self.active_sessions)
    
    def get_detailed_statistics(self, timer_name):
        """Подробная статистика по конкретному таймеру"""
        if timer_name not in self.time_tracker:
            return f"Таймер '{timer_name}' не найден"
        
        timer_data = self.db.get_timer(timer_name)
        if not timer_data:
            return f"Данные таймера '{timer_name}' не найдены"
        
        total_seconds = timer_data['total_seconds']
        total_hours = total_seconds / 3600
        hours = int(total_hours)
        minutes = int((total_hours - hours) * 60)
        
        status = "⏳ Запущен" if timer_name in self.active_sessions else "⏹ Остановлен"
        
        return (
            f"📊 Детальная статистика '{timer_name}':\n"
            f"Всего времени: {total_hours:.2f}h ({hours}h {minutes}m)\n"
            f"Статус: {status}"
        )