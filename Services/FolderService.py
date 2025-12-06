class FolderService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FolderService, cls).__new__(cls)
            cls._instance.user_states = {}
        return cls._instance
    
    def set_folder_mode(self, user_id: int, parent_timer_name: str):
        """Переключить пользователя в режим папки"""
        self.user_states[user_id] = {
            'mode': 'folder',
            'parent_timer': parent_timer_name
        }
    
    def set_normal_mode(self, user_id: int):
        """Переключить пользователя в нормальный режим"""
        if user_id in self.user_states:
            self.user_states[user_id]['mode'] = 'normal'
            self.user_states[user_id]['parent_timer'] = None
        else:
            self.user_states[user_id] = {
                'mode': 'normal',
                'parent_timer': None
            }
    
    def get_mode(self, user_id: int):
        """Получить текущий режим пользователя"""
        return self.user_states.get(user_id, {'mode': 'normal', 'parent_timer': None})
    
    def is_in_folder_mode(self, user_id: int):
        """Проверка, находится ли пользователь в режиме папки"""
        state = self.get_mode(user_id)
        return state['mode'] == 'folder'