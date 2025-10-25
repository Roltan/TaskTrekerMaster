from Class.Model import Model
from datetime import datetime

class Session(Model):
    def __init__(self, db_path: str = "timers.db"):
        super().__init__(db_path, "timer_sessions")

    def tableSchema(self):
        return [
            'user_id INTEGER NOT NULL',
            'timer_name TEXT NOT NULL',
            'start_time TIMESTAMP NOT NULL',
            'end_time TIMESTAMP',
            'duration_seconds REAL',
            'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'FOREIGN KEY (user_id, timer_name) REFERENCES timers (user_id, name)',
        ]
    
    def get_active_sessions(self, user_id: int):
        return self.read({"user_id": user_id, "end_time": None})
    
    def start_session(self, user_id: int, timer_name: str, start_time: datetime):
        result = self.create({
            "user_id": user_id,
            "timer_name": timer_name,
            "start_time": start_time
        })
        if result:
            return result
        return None
    
    def stop_session(self, session_id: int, end_time: datetime, duration_seconds: float):
        return self.update(
            {"end_time": end_time, "duration_seconds": duration_seconds},
            {"id": session_id}
        )