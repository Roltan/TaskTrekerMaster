from Class.Model import Model

class User(Model):
    def __init__(self, db_path: str = "timers.db"):
        super().__init__(db_path, "users")

    def tableSchema(self):
        return [
            'user_id INTEGER NOT NULL',
            'b24_id INTEGER NOT NULL',
            'name TEXT',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'UNIQUE(user_id)',
        ]
    
    def get_user_by_id(self, user_id: int):
        return self.read_one({"user_id": user_id})
    
    def create_user(self, user_id: int, b24_id: int, name: str = None):
        return self.create({
            "user_id": user_id,
            "b24_id": b24_id,
            "name": name
        })