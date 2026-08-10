from datetime import datetime
from Services.B24Service import B24Service
from Services.SubTimerService import SubTimerService
from Services.FolderService import FolderService
from Services.ScreenpipeService import screenpipe_service
from Model.User import User
from Model.Timer import Timer
from Model.Session import Session

class TimerService:
    def __init__(self):
        self.BABY_TIMER_NAME = "👶 BabyTime"
        self.b24 = B24Service()
        self.user_model = User()
        self.timer_model = Timer()
        self.session_model = Session()
        self.sub_timer_service = SubTimerService()
        self.folder_service = FolderService()
    
    def baby_time(self, user_id):
        """Остановить текущий таймер, создать/запустить BabyTime"""
        # Останавливаем активный таймер (если есть)
        active_sessions = self.session_model.get_active_sessions(user_id)
        for session in active_sessions:
            if not session.get('sub_timer_name'):
                self.stop_timer(user_id, session['timer_name'])
                break

        # Создаём таймер если не существует
        timer = self.timer_model.get_timer(user_id, self.BABY_TIMER_NAME)
        if not timer:
            self.timer_model.create_timer(user_id, self.BABY_TIMER_NAME, 0, 0)

        # Запускаем
        return self.start_timer(user_id, self.BABY_TIMER_NAME)

    def get_reply_keyboard(self, user_id):
        from telegram import KeyboardButton, ReplyKeyboardMarkup

        buttons = []
        stats_button = [KeyboardButton("📊 Статистика")]

        # Проверяем, запущен ли сейчас BabyTime
        active_sessions = self.session_model.get_active_sessions(user_id)
        baby_is_running = any(
            s['timer_name'] == self.BABY_TIMER_NAME and not s.get('sub_timer_name')
            for s in active_sessions
        )
        if not baby_is_running:
            stats_button.append(KeyboardButton("👶 BabyTime"))
        
        # Проверяем режим пользователя
        user_mode = self.folder_service.get_mode(user_id)
        
        # ПРОВЕРЯЕМ АКТИВНЫЕ СЕССИИ ПОД-ТАЙМЕРОВ
        active_sessions = self.session_model.get_active_sessions(user_id)
        active_sub_timer_session = None
        
        for session in active_sessions:
            if session.get('sub_timer_name'):
                active_sub_timer_session = session
                break
        
        if active_sub_timer_session:
            # ЕСТЬ АКТИВНЫЙ ПОД-ТАЙМЕР - показываем только кнопку остановки
            buttons.append([KeyboardButton(f"⏹️ Стоп {active_sub_timer_session['sub_timer_name']}")])
            return ReplyKeyboardMarkup(buttons + [stats_button], resize_keyboard=True)
        
        if user_mode['mode'] == 'folder':
            # РЕЖИМ ПАПКИ (без активных под-таймеров)
            parent_timer_name = user_mode['parent_timer']
            
            # Проверяем, что родительский таймер существует
            timer = self.timer_model.get_timer(user_id, parent_timer_name)
            if not timer:
                # Если таймер не найден, возвращаемся в нормальный режим
                self.folder_service.set_normal_mode(user_id)
                return self.get_reply_keyboard(user_id)
            
            sub_timers = self.sub_timer_service.get_sub_timers(user_id, parent_timer_name)
            
            # Кнопки для под-таймеров
            for sub_timer in sub_timers:
                buttons.append([KeyboardButton(f"▶️ Старт {sub_timer['name']}")])
            
            # Кнопка для запуска родительского таймера
            buttons.append([KeyboardButton(f"▶️ Запустить {parent_timer_name}")])
            
            # Кнопка возврата в нормальный режим
            buttons.append([KeyboardButton(f"🔙 Назад к таймерам")])
            
            return ReplyKeyboardMarkup(buttons + [stats_button], resize_keyboard=True)
        
        # НОРМАЛЬНЫЙ РЕЖИМ (без активных под-таймеров)
        # Получаем активные сессии напрямую из БД
        if bool(active_sessions):
            # Проверяем, есть ли активный под-таймер
            has_active_sub_timer = any(session.get('sub_timer_name') for session in active_sessions)
            
            if not has_active_sub_timer:
                # Показываем кнопки для активного таймера (только если нет активных под-таймеров)
                for session in active_sessions:
                    # Основная кнопка остановки
                    buttons.append([KeyboardButton(f"⏹️ Стоп {session['timer_name']}")])
                    # Кнопка создания под-таймера (только для обычных таймеров)
                    if not session.get('sub_timer_name'):
                        buttons.append([KeyboardButton(f"📁 Создать под-таймер")])
                    break  # Только один активный таймер
        else:
            # Показываем кнопки старта для всех сегодняшних таймеров пользователя
            today_timers = self.timer_model.get_today_timers(user_id)
            for timer in today_timers:
                if timer['name'] == self.BABY_TIMER_NAME:
                    continue
                # Проверяем, есть ли у таймера под-таймеры
                sub_timers = self.sub_timer_service.get_sub_timers(user_id, timer['name'])
                if sub_timers:
                    # У таймера есть под-таймеры - показываем как папку
                    buttons.append([KeyboardButton(f"📁 {timer['name']}")])
                else:
                    # Обычный таймер без под-таймеров
                    buttons.append([KeyboardButton(f"▶️ Старт {timer['name']}")])
            # buttons.append([KeyboardButton(f"Отчёт")])
        
        return ReplyKeyboardMarkup(buttons + [stats_button], resize_keyboard=True)
    
    def start_timer(self, user_id, timer_name):
        """Запуск таймера с проверкой существования в БД"""
        # Если пользователь в режиме папки, выходим из него при запуске таймера
        if self.folder_service.is_in_folder_mode(user_id):
            self.folder_service.set_normal_mode(user_id)

        # Проверяем существование таймера
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            return f"Таймер '{timer_name}' не найден в базе данных"

        # Проверяем активные сессии для этого таймера
        active_sessions = self.session_model.get_active_sessions(user_id)
        for session in active_sessions:
            if session['timer_name'] == timer_name:
                return f"Таймер '{timer_name}' уже запущен!"

        # Запуск таймера
        now = datetime.now()

        # Сохраняем сессию в БД
        session_id = self.session_model.start_session(user_id, timer_name, now)
        if not session_id:
            return f"Ошибка при запуске таймера '{timer_name}'"

        return f"Таймер '{timer_name}' запущен!"
    
    def stop_timer(self, user_id, timer_name):
        """Остановка таймера с сохранением в БД"""
        # Проверяем существование таймера
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            return f"Таймер '{timer_name}' не найден"
        
        # Ищем активную сессию для этого таймера
        active_sessions = self.session_model.get_active_sessions(user_id)
        session_id = None
        for session in active_sessions:
            if session['timer_name'] == timer_name and not session.get('sub_timer_name'):
                session_id = session['id']
                break
        
        if not session_id:
            # Проверяем, не является ли это сессией под-таймера
            for session in active_sessions:
                if session.get('sub_timer_name'):
                    return f"Сначала остановите под-таймер '{session['sub_timer_name']}'"
            return f"Таймер '{timer_name}' не был запущен!"
        
        # Останавливаем таймер
        now = datetime.now()
        
        # Получаем время начала сессии из БД
        session_data = self.session_model.read_one({"id": session_id})
        if not session_data:
            return f"Ошибка: не найдены данные сессии для таймера '{timer_name}'"
        
        start_time = datetime.fromisoformat(session_data['start_time'].replace('Z', '+00:00'))
        delta = now - start_time
        duration_seconds = delta.total_seconds()
        
        # ВСЁ время сессии добавляем к общему времени таймера
        # Под-таймеры не влияют на общее время родительского таймера
        self.timer_model.add_time_to_timer(user_id, timer_name, duration_seconds)
        
        # Завершаем сессию в БД
        success = self.session_model.stop_session(session_id, now, duration_seconds)
        if not success:
            return f"Ошибка при остановке таймера '{timer_name}'"

        # Сохраняем запись в Screenpipe Memory с тегом проекта
        screenpipe_service.save_task_memory(timer_name, start_time, now, duration_seconds)

        # Получаем актуальные данные из БД для отчета
        updated_timer = self.timer_model.get_timer(user_id, timer_name)
        total_seconds = updated_timer['total_seconds'] if updated_timer else 0
        total_minutes = total_seconds / 60
        hours = int(total_seconds // 3600)
        minutes = int(total_minutes % 60)
        
        # Добавляем информацию о под-таймерах, если они есть
        sub_timers = self.sub_timer_service.get_sub_timers(user_id, timer_name)
        if sub_timers:
            sub_timers_info = []
            
            for sub_timer in sub_timers:
                sub_minutes = sub_timer['duration_seconds'] / 60
                # Округляем до целых минут для единообразия
                sub_timers_info.append(f"    - {sub_timer['name']} - {int(round(sub_minutes))} мин")
            
            return (
                f"Таймер '{timer_name}' остановлен\n"
                f"Сессия: {duration_seconds/60:.1f} минут\n"
                f"Всего времени: {int(total_minutes)} мин\n"
                f"Под-таймеры:\n" + "\n".join(sub_timers_info)
            )
        
        return (
            f"Таймер '{timer_name}' остановлен\n"
            f"Сессия: {duration_seconds/60:.1f} минут\n"
            f"Всего времени: {hours}h {minutes}m"
        )
    
    def create_timer(self, user_id, key, task_id, timer_type):
        """Создание таймера через модель"""
        success = self.timer_model.create_timer(user_id, key, task_id, timer_type)
        if success:
            return f"Таймер '{key}' готов к запуску!"
        else:
            return f"Таймер '{key}' уже существует!"
    
    def add_minutes(self, user_id, timer_name, minutes):
        """Добавление времени через модель"""
        # Проверяем существование таймера
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            return f"Таймер '{timer_name}' не найден"
        
        # Добавляем время через модель
        seconds_to_add = minutes * 60
        self.timer_model.add_time_to_timer(user_id, timer_name, seconds_to_add)
        
        # Получаем актуальные данные для отчета
        updated_timer = self.timer_model.get_timer(user_id, timer_name)
        total_seconds = updated_timer['total_seconds'] if updated_timer else 0
        hours = int(total_seconds // 3600)
        minutes_total = int((total_seconds % 3600) // 60)
        
        return (
            f"К таймеру '{timer_name}' добавлено {minutes} минут\n"
            f"Всего времени: {hours}h {minutes_total}m"
        )
    
    def delete_timer(self, user_id, timer_name):
        """Удаление таймера из БД"""
        # Проверяем существование таймера
        timer = self.timer_model.get_timer(user_id, timer_name)
        if not timer:
            return f"Таймер '{timer_name}' не найден"
        
        # Если таймер активен, останавливаем его
        active_sessions = self.session_model.get_active_sessions(user_id)
        for session in active_sessions:
            if session['timer_name'] == timer_name:
                self.stop_timer(user_id, timer_name)
                break
        
        # Удаляем сессии таймера
        self.session_model.delete({"user_id": user_id, "timer_name": timer_name})
        
        # Удаляем сам таймер
        self.timer_model.delete({"user_id": user_id, "name": timer_name})
        
        return f"Таймер '{timer_name}' удален!"
    
    def get_statistics(self, user_id):
        """Получение статистики по сегодняшним таймерам пользователя с под-таймерами"""
        today_timers = self.timer_model.get_today_timers(user_id)
        
        if not today_timers:
            return "На сегодня нет активных таймеров"
        
        stats = []
        total_day_seconds = 0
        active_sessions = self.session_model.get_active_sessions(user_id)
        
        # Создаем множество активных таймеров и под-таймеров для быстрого поиска
        active_timer_names = {session['timer_name'] for session in active_sessions if not session.get('sub_timer_name')}
        active_sub_timer_names = {session['sub_timer_name'] for session in active_sessions if session.get('sub_timer_name')}

        for timer in today_timers:
            total_seconds = timer['total_seconds']
            total_day_seconds += total_seconds
            
            total_hours = total_seconds / 3600
            hours = int(total_hours)
            minutes = int((total_hours - hours) * 60)
            
            # Статус по активным сессиям
            timer_name = timer['name']
            status = "⏳" if timer_name in active_timer_names else "⏹"
            stats.append(f"{status} [{timer_name}] {total_hours:.2f}h ({hours}h {minutes}m)")
            
            # Получаем под-таймеры для этого таймера
            sub_timers = self.sub_timer_service.get_sub_timers(user_id, timer_name)
            
            if sub_timers:
                # Сортируем под-таймеры по времени создания
                sorted_sub_timers = sorted(sub_timers, key=lambda x: x.get('created_at', ''))
                
                for sub_timer in sorted_sub_timers:
                    sub_timer_name = sub_timer['name']
                    sub_seconds = sub_timer['duration_seconds']
                    sub_minutes = int(round(sub_seconds / 60))  # Время в минутах, округленное до целых
                    
                    # Статус для под-таймеров
                    sub_status = "⏳" if sub_timer_name in active_sub_timer_names else ""
                    stats.append(f"    {sub_status}- {sub_timer_name} - {sub_minutes}")
        
        # Подсчёт общего времени за день
        total_day_hours = total_day_seconds / 3600
        total_day_hours_int = int(total_day_hours)
        total_day_minutes = int((total_day_hours - total_day_hours_int) * 60)
        
        # Формируем итоговую статистику
        result = [
            "📊 Статистика на сегодня:",
            *stats,
            "",
            f"📈 **Всего за день: {total_day_hours:.2f}h ({total_day_hours_int}h {total_day_minutes}m)**"
        ]
        
        return "\n".join(result)

    def add_minutes_to_sub_timer(self, user_id, parent_timer_name, sub_timer_name, minutes):
        """Добавление времени к под-таймеру"""
        # Проверяем существование родительского таймера
        parent_timer = self.timer_model.get_timer(user_id, parent_timer_name)
        if not parent_timer:
            return f"Родительский таймер '{parent_timer_name}' не найден"
        
        # Добавляем время к под-таймеру через SubTimerService
        result = self.sub_timer_service.add_minutes_to_sub_timer(user_id, parent_timer_name, sub_timer_name, minutes)
        
        if not result:
            return f"Под-таймер '{sub_timer_name}' не найден в папке '{parent_timer_name}'"
        
        # Также добавляем время к родительскому таймеру
        seconds_to_add = minutes * 60
        self.timer_model.add_time_to_timer(user_id, parent_timer_name, seconds_to_add)
        
        # Получаем обновленные данные родителя
        updated_parent_timer = self.timer_model.get_timer(user_id, parent_timer_name)
        parent_total_seconds = updated_parent_timer['total_seconds'] if updated_parent_timer else 0
        parent_hours = int(parent_total_seconds // 3600)
        parent_minutes_total = int((parent_total_seconds % 3600) // 60)
        
        return (
            f"К под-таймеру '{parent_timer_name}:{sub_timer_name}' добавлено {minutes} минут\n"
            f"Всего под-таймера: {result['total_minutes']:.1f} минут\n"
            f"Всего родителя '{parent_timer_name}': {parent_hours}h {parent_minutes_total}m"
        )

    def clear_all_timers(self, user_id):
        """Очистка всех таймеров пользователя (для команды старт)"""
        # Останавливаем все активные таймеры
        active_sessions = self.session_model.get_active_sessions(user_id)
        
        for session in active_sessions:
            self.stop_timer(user_id, session['timer_name'])
        
        return "Все таймеры остановлены и кнопки очищены"