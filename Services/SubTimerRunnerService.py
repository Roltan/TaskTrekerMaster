from datetime import datetime
from Model.SubTimer import SubTimer
from Model.Session import Session
from Model.Timer import Timer

class SubTimerRunnerService:
    def __init__(self):
        self.sub_timer_model = SubTimer()
        self.session_model = Session()
        self.timer_model = Timer()
    
    def start_sub_timer(self, user_id: int, parent_timer_name: str, sub_timer_name: str):
        """Запуск под-таймера"""
        # Проверяем существование под-таймера в таблице sub_timers
        sub_timers = self.sub_timer_model.read({
            "user_id": user_id,
            "parent_timer_name": parent_timer_name,
            "name": sub_timer_name
        })
        
        if not sub_timers:
            return None
        
        # Проверяем, не запущен ли уже под-таймер
        active_sessions = self.session_model.get_active_sessions(user_id)
        for session in active_sessions:
            if session.get('sub_timer_name') == sub_timer_name:
                return f"Под-таймер '{sub_timer_name}' уже запущен!"
        
        # Проверяем, что родительский таймер существует
        parent_timer = self.timer_model.get_timer(user_id, parent_timer_name)
        if not parent_timer:
            return f"Родительский таймер '{parent_timer_name}' не найден"
        
        # Запускаем под-таймер
        now = datetime.now()
        
        # Сохраняем сессию с пометкой, что это под-таймер
        session_id = self.session_model.start_session(
            user_id, 
            parent_timer_name,  # Основной таймер как родитель
            now,
            sub_timer_name=sub_timer_name  # Добавляем поле для под-таймера
        )
        
        if not session_id:
            return None
        
        return f"Под-таймер '{sub_timer_name}' запущен!"
    
    def stop_sub_timer(self, user_id: int, parent_timer_name: str, sub_timer_name: str):
        """Остановка под-таймера"""
        # Находим активную сессию под-таймера
        active_sessions = self.session_model.get_active_sessions(user_id)
        session_id = None
        
        for session in active_sessions:
            if session.get('sub_timer_name') == sub_timer_name:
                session_id = session['id']
                break
        
        if not session_id:
            return f"Под-таймер '{sub_timer_name}' не был запущен!"
        
        # Останавливаем под-таймер
        now = datetime.now()
        
        # Получаем время начала сессии
        session_data = self.session_model.read_one({"id": session_id})
        if not session_data:
            return f"Ошибка: не найдены данные сессии для под-таймера '{sub_timer_name}'"
        
        start_time = datetime.fromisoformat(session_data['start_time'].replace('Z', '+00:00'))
        delta = now - start_time
        duration_seconds = delta.total_seconds()
        
        # 1. Обновляем время под-таймера в БД
        existing_duration = session_data['duration_seconds'] if session_data['duration_seconds'] else 0
        new_duration = existing_duration + duration_seconds
        
        self.sub_timer_model.update(
            {"duration_seconds": new_duration},
            {"user_id": user_id, "parent_timer_name": parent_timer_name, "name": sub_timer_name}
        )
        
        # 2. ВРЕМЯ ПОД-ТАЙМЕРА ДОБАВЛЯЕТСЯ К РОДИТЕЛЬСКОМУ ТАЙМЕРУ
        self.timer_model.add_time_to_timer(user_id, parent_timer_name, duration_seconds)
        
        # 3. Завершаем сессию
        success = self.session_model.stop_session(session_id, now, duration_seconds)
        if not success:
            return f"Ошибка при остановке под-таймера '{sub_timer_name}'"
        
        # 4. Получаем обновленные данные для отчета
        parent_timer = self.timer_model.get_timer(user_id, parent_timer_name)
        parent_total_seconds = parent_timer['total_seconds'] if parent_timer else 0
        parent_minutes = parent_total_seconds / 60
        
        minutes = new_duration / 60
        return (
            f"Под-таймер '{sub_timer_name}' остановлен ({minutes:.1f} минут)\n"
            f"Добавлено к '{parent_timer_name}': {duration_seconds/60:.1f} минут\n"
            f"Всего '{parent_timer_name}': {parent_minutes:.1f} минут"
        )