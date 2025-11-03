from Class.Model import Model
from datetime import datetime, date

class Timer(Model):
    def __init__(self, db_path: str = "timers.db"):
        super().__init__(db_path, "timers")

    def tableSchema(self):
        return [
            'user_id INTEGER NOT NULL',
            'name TEXT NOT NULL',
            'total_seconds REAL DEFAULT 0',
            'task_id INTEGER',
            'comment TEXT',
            'report_id INTEGER',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        ]
    
    def get_timer(self, user_id: int, name: str):
        today = date.today().isoformat()
        return self.read_one({"user_id": user_id, "name": name, "DATE(created_at)": today})
    
    def get_today_timers(self, user_id: int):
        query = '''
            SELECT name, total_seconds, task_id, comment
            FROM timers 
            WHERE user_id = ? AND DATE(created_at) = DATE('now')
        '''
        return self.execute_custom_query(query, [user_id])
    
    def add_time_to_timer(self, user_id: int, name: str, seconds_to_add: float):
        query = '''
            UPDATE timers 
            SET total_seconds = total_seconds + ?, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = ? AND name = ?
        '''
        self.execute_custom_query(query, [seconds_to_add, user_id, name])
        return True
    
    def create_timer(self, user_id: int, name: str, task_id: str = '', timer_type: int = 2):
        comment_map = {3: 'кч', 2: 'нкч', 1: 'баги', 0: ''}
        comment = comment_map.get(timer_type, '')
        
        return self.create({
            "user_id": user_id,
            "name": name,
            "task_id": task_id,
            "comment": comment
        })