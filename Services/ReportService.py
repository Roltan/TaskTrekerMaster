from Services.B24Service import B24Service
from Model.User import User
from Model.Timer import Timer
from telegram import Update
from telegram.ext import ContextTypes

class ReportService:
    def __init__(self):
        self.b24 = B24Service()
        self.user_model = User()
        self.timer_model = Timer()

    async def tracker_all_timer(self, user_id, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Трекает все таймеры с запросом недостающих данных"""
        # Получаем таймеры через модель
        today_timers = self.timer_model.get_today_timers(user_id)
        user_data = self.user_model.get_user_by_id(user_id)

        if not today_timers:
            return "На сегодня нет активных таймеров"

        if not user_data or not user_data.get('b24_id'):
            return "У вас нет доступа в Битрикс"

        # Сохраняем состояние для диалога
        context.user_data['pending_timers'] = today_timers
        context.user_data['current_timer_index'] = 0
        context.user_data['user_b24_id'] = user_data['b24_id']
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
        
        # Получаем актуальные данные из БД
        current_timer = self.timer_model.get_timer(update.effective_user.id, timer['name'])
        
        # Проверяем, что таймер найден
        if not current_timer:
            await update.message.reply_text(f"❌ Таймер \"{timer['name']}\" не найден в базе данных. Пропускаем.")
            # Переходим к следующему таймеру
            context.user_data['current_timer_index'] += 1
            await self._process_next_timer(update, context)
            return
        
        if not current_timer.get('task_id'):
            # Запрашиваем ID задачи
            await update.message.reply_text(
                f"❓ У таймера \"{timer['name']}\" не указан ID задачи.\n"
                f"Пожалуйста, введите ID задачи:"
            )
            context.user_data['awaiting_task_id'] = True
        elif not current_timer.get('comment'):
            # Запрашиваем комментарий
            await update.message.reply_text(
                f"❓ У таймера \"{timer['name']}\" (ID: {current_timer['task_id']}) нет комментария.\n"
                f"Пожалуйста, введите комментарий:"
            )
            context.user_data['awaiting_comment'] = True
        else:
            # Все данные есть, отправляем в Битрикс
            await self._send_to_bitrix(update, context, current_timer)

    async def _send_to_bitrix(self, update: Update, context: ContextTypes.DEFAULT_TYPE, timer=None):
        """Отправляет таймер в Битрикс"""
        if timer is None:
            timer = context.user_data['current_timer']
        
        user_b24_id = context.user_data['user_b24_id']
        
        try:
            success = self.b24.addTime(
                timer['task_id'], 
                user_b24_id, 
                timer['total_seconds'], 
                timer.get('comment', '')
            )
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
        
        # Сбрасываем флаг сразу
        context.user_data.pop('awaiting_task_id', None)
        
        try:
            task_id = int(update.message.text)
            timer_name = context.user_data['current_timer']['name']
            
            # Обновляем task_id в базе данных
            success = self.timer_model.update(
                {"task_id": task_id},
                {"user_id": user_id, "name": timer_name}
            )
            
            if success:
                await update.message.reply_text(f"✅ ID задачи для \"{timer_name}\" установлен: {task_id}")
                
                # Обновляем текущий таймер в контексте
                context.user_data['current_timer']['task_id'] = task_id
                
                # Проверяем, нужен ли еще комментарий
                current_timer = self.timer_model.get_timer(user_id, timer_name)  # Используем user_id
                if current_timer and not current_timer.get('comment'):
                    await update.message.reply_text(
                        f"❓ Теперь введите комментарий для таймера \"{timer_name}\":"
                    )
                    context.user_data['awaiting_comment'] = True
                else:
                    # Все данные есть, отправляем в Битрикс
                    await self._send_to_bitrix(update, context)
            else:
                await update.message.reply_text("❌ Ошибка при обновлении ID задачи")
                # Продолжаем со следующим таймером
                context.user_data['current_timer_index'] += 1
                await self._process_next_timer(update, context)
                
        except ValueError:
            await update.message.reply_text("❌ ID задачи должен быть числом. Попробуйте еще раз:")
            # Возвращаем флаг ожидания
            context.user_data['awaiting_task_id'] = True

    async def handle_comment_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает ответ с комментарием"""
        user_id = update.effective_user.id
        
        # Сбрасываем флаг сразу
        context.user_data.pop('awaiting_comment', None)
        
        comment = update.message.text
        timer_name = context.user_data['current_timer']['name']
        
        # Обновляем комментарий в базе данных
        success = self.timer_model.update(
            {"comment": comment},
            {"user_id": user_id, "name": timer_name}
        )
        
        if success:
            await update.message.reply_text(f"✅ Комментарий для \"{timer_name}\" сохранен")
            
            # Обновляем текущий таймер в контексте
            context.user_data['current_timer']['comment'] = comment
            
            # Все данные теперь есть, отправляем в Битрикс
            await self._send_to_bitrix(update, context)
        else:
            await update.message.reply_text("❌ Ошибка при сохранении комментария")
            # Продолжаем со следующим таймером
            context.user_data['current_timer_index'] += 1
            await self._process_next_timer(update, context)