from datetime import datetime, date
from Model.SubTimer import SubTimer
from Model.Session import Session
from Model.Timer import Timer  # Добавляем импорт

class SubTimerService:
    def __init__(self):
        self.sub_timer_model = SubTimer()
        self.session_model = Session()
        self.timer_model = Timer()  # Добавляем доступ к таймерам
    
    def get_sub_timers(self, user_id: int, parent_timer_name: str):
        """Получить все под-таймеры для родительского таймера"""
        today = date.today().isoformat()
        return self.sub_timer_model.read({
            "user_id": user_id,
            "parent_timer_name": parent_timer_name,
            "DATE(created_at)": today
        })
    
    def get_total_duration_for_parent(self, user_id: int, parent_timer_name: str) -> float:
        """Получить общую длительность всех под-таймеров родителя"""
        return self.sub_timer_model.get_total_duration_for_parent(user_id, parent_timer_name)
    
    def create_sub_timer(self, user_id: int, parent_timer_name: str, name: str, duration_seconds: float = 0):
        """Создать под-таймер"""
        return self.sub_timer_model.create({
            "user_id": user_id,
            "parent_timer_name": parent_timer_name,
            "name": name,
            "duration_seconds": duration_seconds
        })
    
    def calculate_new_sub_timer_duration(self, user_id: int, parent_timer_name: str) -> float:
        """Рассчитать время для нового под-таймера"""
        # Получаем общее время родительского таймера на данный момент
        timer = self.timer_model.get_timer(user_id, parent_timer_name)
        if not timer:
            return 0
        
        total_timer_seconds = timer['total_seconds'] if timer['total_seconds'] else 0
        
        # Добавляем время текущей активной сессии (если есть)
        active_sessions = self.session_model.get_active_sessions(user_id)
        for session in active_sessions:
            if session['timer_name'] == parent_timer_name:
                start_time = datetime.fromisoformat(session['start_time'].replace('Z', '+00:00'))
                now = datetime.now()
                session_duration = (now - start_time).total_seconds()
                total_timer_seconds += session_duration
                break
        
        # Получаем общее время всех существующих под-таймеров
        existing_sub_timers_duration = self.get_total_duration_for_parent(user_id, parent_timer_name)
        print(existing_sub_timers_duration)
        # Время для нового под-таймера = всё время таймера - время существующих под-таймеров
        new_duration = total_timer_seconds - existing_sub_timers_duration
        
        return max(new_duration, 0)  # Не возвращаем отрицательные значения
    
    def add_minutes_to_sub_timer(self, user_id: int, parent_timer_name: str, sub_timer_name: str, minutes: int):
        """Добавить время к под-таймеру"""
        # Ищем под-таймер
        sub_timers = self.sub_timer_model.read({
            "user_id": user_id,
            "parent_timer_name": parent_timer_name,
            "name": sub_timer_name
        })
        
        if not sub_timers:
            return None
        
        sub_timer = sub_timers[0]
        seconds_to_add = minutes * 60
        current_duration = sub_timer['duration_seconds'] if sub_timer['duration_seconds'] else 0
        new_duration = current_duration + seconds_to_add
        
        # Проверяем, чтобы не уйти в отрицательное значение
        if new_duration < 0:
            new_duration = 0
            # Корректируем секунды для добавления
            seconds_to_add = -current_duration
        
        # Обновляем под-таймер
        success = self.sub_timer_model.update(
            {"duration_seconds": new_duration},
            {"user_id": user_id, "parent_timer_name": parent_timer_name, "name": sub_timer_name}
        )
        
        if not success:
            return None
        
        # Возвращаем не словарь, а просто данные для удобства
        return {
            'sub_timer_name': sub_timer_name,
            'added_minutes': seconds_to_add / 60,  # Корректированные минуты
            'total_minutes': new_duration / 60,
            'success': True
        }