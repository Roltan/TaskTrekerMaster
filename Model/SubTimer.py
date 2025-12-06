from Class.Model import Model

class SubTimer(Model):
    def __init__(self, db_path: str = "timers.db"):
        super().__init__(db_path, "sub_timers")
    
    def tableSchema(self):
        return [
            'user_id INTEGER NOT NULL',
            'parent_timer_name TEXT NOT NULL',
            'name TEXT NOT NULL',
            'duration_seconds REAL DEFAULT 0',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        ]
    
    def get_total_duration_for_parent(self, user_id: int, parent_timer_name: str) -> float:
        """Получить общую длительность всех под-таймеров родителя"""
        query = '''
            SELECT SUM(duration_seconds) as total 
            FROM sub_timers 
            WHERE user_id = ? AND parent_timer_name = ?
        '''
        result = self.execute_custom_query(query, [user_id, parent_timer_name])
        return result[0]['total'] if result and result[0]['total'] else 0