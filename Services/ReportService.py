from Services.DatabaseService import DatabaseService
from Services.B24Service import B24Service
from telegram import Update
from telegram.ext import ContextTypes

class ReportService:
    def __init__(self):
        self.db = DatabaseService()
        self.b24 = B24Service()

    async def tracker_all_timer(self, user_id, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Трекает все таймеры с запросом недостающих данных"""
        state = self.db.get_today_timers(user_id)
        user_b24_id = self.db.getUser(user_id)['b24_id']

        if not state:
            return "На сегодня нет активных таймеров"

        if not user_b24_id:
            return "У вас нет доступа в Битрикс"

        # Сохраняем состояние для диалога
        context.user_data['pending_timers'] = list(state.values())
        context.user_data['current_timer_index'] = 0
        context.user_data['user_b24_id'] = user_b24_id
        context.user_data['tracked_timers'] = []
        context.user_data['error_timers'] = []

        # Начинаем диалог
        await self._process_next_timer(update, context)
        return "DIALOG_STARTED"

    async def _process_next_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает следующий таймер в очереди"""
        pending_timers = context.user_data['pending_timers']
        current_index = context.user_data['current_timer_index']
        
        if current_index >= len(pending_timers):
            # Все таймеры обработаны
            await self._finish_tracking(update, context)
            return
        
        timer = pending_timers[current_index]
        context.user_data['current_timer'] = timer
        
        if timer['task_id'] == 0:
            # Запрашиваем ID задачи
            await update.message.reply_text(
                f"❓ У таймера \"{timer['name']}\" не указан ID задачи.\n"
                f"Пожалуйста, введите ID задачи:"
            )
            context.user_data['awaiting_task_id'] = True
        elif not timer.get('comment'):
            # Запрашиваем комментарий
            await update.message.reply_text(
                f"❓ У таймера \"{timer['name']}\" (ID: {timer['task_id']}) нет комментария.\n"
                f"Пожалуйста, введите комментарий:"
            )
            context.user_data['awaiting_comment'] = True
        else:
            # Все данные есть, отправляем в Битрикс
            await self._send_to_bitrix(update, context, timer)

    async def _send_to_bitrix(self, update: Update, context: ContextTypes.DEFAULT_TYPE, timer=None):
        """Отправляет таймер в Битрикс"""
        if timer is None:
            timer = context.user_data['current_timer']
        
        user_b24_id = context.user_data['user_b24_id']
        
        try:
            success = self.b24.addTime(timer['task_id'], user_b24_id, timer['total_seconds'], timer.get('comment', ''))
            if success:
                context.user_data['tracked_timers'].append(timer['name'])
                await update.message.reply_text(f"✅ Таймер \"{timer['name']}\" успешно отправлен в Битрикс")
            else:
                context.user_data['error_timers'].append(timer['name'])
                await update.message.reply_text(f"❌ Ошибка отправки таймера \"{timer['name']}\"")
        except Exception as e:
            context.user_data['error_timers'].append(timer['name'])
            await update.message.reply_text(f"❌ Ошибка отправки таймера \"{timer['name']}\": {str(e)}")
        
        # Переходим к следующему таймеру
        context.user_data['current_timer_index'] += 1
        await self._process_next_timer(update, context)

    async def _finish_tracking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершает процесс трекинга и выводит итог"""
        tracked = context.user_data['tracked_timers']
        errors = context.user_data['error_timers']
        
        result_message = ["📊 **Итог трекинга:**"]
        
        if tracked:
            result_message.append("✅ Успешно отправлены:")
            for name in tracked:
                result_message.append(f"  • {name}")
        
        if errors:
            result_message.append("❌ Ошибки отправки:")
            for name in errors:
                result_message.append(f"  • {name}")
        
        if not tracked and not errors:
            result_message.append("ℹ️ Нет таймеров для отправки")
        
        await update.message.reply_text(
            "\n".join(result_message),
            reply_markup=self.get_reply_keyboard(update.effective_user.id)
        )
        
        # Очищаем временные данные
        for key in ['pending_timers', 'current_timer_index', 'user_b24_id', 
                    'tracked_timers', 'error_timers', 'current_timer',
                    'awaiting_task_id', 'awaiting_comment']:
            context.user_data.pop(key, None)

    def get_reply_keyboard(self, user_id):
        """Получение клавиатуры с кнопками"""
        # Импортируем TimerService здесь, чтобы избежать циклического импорта
        from Services.TimerService import TimerService
        return TimerService().get_reply_keyboard(user_id)

    # Обработчики для ответов пользователя
    async def handle_task_id_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает ответ с ID задачи"""
        user_id = update.effective_user.id
        try:
            task_id = int(update.message.text)
            timer = self.db.get_timer_by_name(user_id, context.user_data['current_timer']['name'])
            if not timer:
                await update.message.reply_text("❌ Ошибка: таймер не найден в базе данных")
                return
            timer['task_id'] = task_id
            
            # Обновляем в базе данных
            self.db.update_timer_task_id(user_id, timer['name'], task_id)
            
            await update.message.reply_text(f"✅ ID задачи для \"{timer['name']}\" установлен: {task_id}")
            
            # Проверяем комментарий
            if not timer.get('comment'):
                await update.message.reply_text(
                    f"❓ Теперь введите комментарий для таймера \"{timer['name']}\":"
                )
                context.user_data['awaiting_comment'] = True
            else:
                # Отправляем в Битрикс
                await self._send_to_bitrix(update, context, timer)
                
        except ValueError:
            await update.message.reply_text("❌ ID задачи должен быть числом. Попробуйте еще раз:")

    async def handle_comment_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает ответ с комментарием"""
        user_id = update.effective_user.id
        comment = update.message.text
        timer = self.db.get_timer_by_name(user_id, context.user_data['current_timer']['name'])
        if not timer:
            await update.message.reply_text("❌ Ошибка: таймер не найден в базе данных")
            return
        timer['comment'] = comment
        
        # Обновляем в базе данных
        self.db.update_timer_comment(user_id, timer['name'], comment)
        
        await update.message.reply_text(f"✅ Комментарий для \"{timer['name']}\" сохранен")
        
        # Отправляем в Битрикс
        await self._send_to_bitrix(update, context, timer)