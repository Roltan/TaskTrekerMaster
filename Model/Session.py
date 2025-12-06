from Class.Model import Model
from datetime import datetime

class Session(Model):
    def __init__(self, db_path: str = "timers.db"):
        super().__init__(db_path, "sessions")
    
    def tableSchema(self):
        return [
            'user_id INTEGER NOT NULL',
            'timer_name TEXT NOT NULL',
            'sub_timer_name TEXT',  # Добавляем поле для под-таймера
            'start_time TIMESTAMP NOT NULL',
            'end_time TIMESTAMP',
            'duration_seconds REAL'
        ]
    
    def start_session(self, user_id: int, timer_name: str, start_time: datetime, sub_timer_name: str = None):
        """Создать новую сессию"""
        data = {
            "user_id": user_id,
            "timer_name": timer_name,
            "start_time": start_time.isoformat()
        }
        
        if sub_timer_name:
            data["sub_timer_name"] = sub_timer_name
        
        return self.create(data)
    
    def get_active_sessions(self, user_id: int):
        """Получить активные сессии пользователя"""
        query = '''
            SELECT * FROM sessions 
            WHERE user_id = ? AND end_time IS NULL
        '''
        return self.execute_custom_query(query, [user_id])
    
    def get_active_sub_timer_session(self, user_id: int, parent_timer_name: str):
        """Получить активную сессию под-таймера для родительского таймера"""
        query = '''
            SELECT * FROM sessions 
            WHERE user_id = ? AND timer_name = ? AND sub_timer_name IS NOT NULL AND end_time IS NULL
        '''
        return self.execute_custom_query(query, [user_id, parent_timer_name])
    
    def stop_session(self, session_id: int, end_time: datetime, duration_seconds: float):
        """Завершить сессию"""
        return self.update(
            {"end_time": end_time.isoformat(), "duration_seconds": duration_seconds},
            {"id": session_id}
        )