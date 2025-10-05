from datetime import datetime, timedelta

class TimerService:
    def __init__(self):
        self.time_tracker = {}
        self.active_timer = None
    
    def get_reply_keyboard(self):
        from telegram import KeyboardButton, ReplyKeyboardMarkup
        
        buttons = []
        stats_button = [KeyboardButton("📊 Статистика")]
        
        # Проверяем, есть ли активный таймер
        active_timer_exists = any(timer["time_mark"] is not None for timer in self.time_tracker.values())
        
        if active_timer_exists:
            # Режим работы таймера - показываем только кнопку остановки активного
            for name, data in self.time_tracker.items():
                if data["time_mark"] is not None:
                    buttons.append([KeyboardButton(f"⏹️ Стоп {name}")])
                    break
        else:
            # Режим ожидания - показываем кнопки старта для всех таймеров
            for name in self.time_tracker:
                buttons.append([KeyboardButton(f"▶️ Старт {name}")])
        
        return ReplyKeyboardMarkup(buttons + [stats_button], resize_keyboard=True)
    
    def create_timer(self, key):
        if key not in self.time_tracker:
            self.time_tracker[key] = {
                "time_mark": None,
                "full_time": 0
            }
            return f"Таймер '{key}' готов к запуску!"
        else:
            return f"Таймер '{key}' уже существует!"
    
    def start_timer(self, timer_name):
        if timer_name not in self.time_tracker:
            return f"Таймер '{timer_name}' не найден"
        
        if self.time_tracker[timer_name]["time_mark"] is not None:
            return f"Таймер '{timer_name}' уже запущен!"
        
        # Запуск таймера
        self.time_tracker[timer_name]["time_mark"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.active_timer = timer_name
        return f"Таймер '{timer_name}' запущен!"
    
    def stop_timer(self, timer_name):
        if timer_name not in self.time_tracker:
            return f"Таймер '{timer_name}' не найден"
        
        if self.time_tracker[timer_name]["time_mark"] is None:
            return f"Таймер '{timer_name}' не был запущен!"
        
        # Остановка таймера
        now = datetime.now()
        last_time = datetime.strptime(self.time_tracker[timer_name]["time_mark"], "%Y-%m-%d %H:%M:%S")
        delta = now - last_time
        self.time_tracker[timer_name]["full_time"] += delta.total_seconds()
        self.time_tracker[timer_name]["time_mark"] = None
        self.active_timer = None
        
        total_seconds = self.time_tracker[timer_name]["full_time"]
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return (
            f"Таймер '{timer_name}' остановлен\n"
            f"Всего времени: {hours}h {minutes}m"
        )
    
    def add_minutes(self, timer_name, minutes):
        if timer_name not in self.time_tracker:
            return f"Таймер '{timer_name}' не найден"
        
        # Прибавляем минуты (переводим в секунды)
        self.time_tracker[timer_name]["full_time"] += minutes * 60
        
        total_seconds = self.time_tracker[timer_name]["full_time"]
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        return (
            f"К таймеру '{timer_name}' добавлено {minutes} минут\n"
            f"Всего времени: {hours}h {minutes}m"
        )
    
    def get_statistics(self):
        if not self.time_tracker:
            return "Нет активных таймеров"
        
        stats = []
        for key, data in self.time_tracker.items():
            total_hours = data["full_time"] / 3600
            hours = int(total_hours)
            minutes = int((total_hours - hours) * 60)
            status = "⏳" if data["time_mark"] else "⏹"
            stats.append(f"{status} [{key}] {total_hours:.2f}h ({hours}h {minutes}m)")
        
        return "Статистика:\n" + "\n".join(stats)
    
    def has_active_timer(self):
        return any(timer["time_mark"] is not None for timer in self.time_tracker.values())