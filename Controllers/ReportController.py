from Class.Controller import Controller
from Services.ReportService import ReportService
from telegram import Update
from telegram.ext import ContextTypes

class ReportController(Controller):
    def __init__(self):
        super().__init__()
        self.report_service = ReportService()
    
    async def generate_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки отчёта"""
        user_id = self.get_user_id(update)
        result = await self.report_service.tracker_all_timer(user_id, update, context)
        
        if result != "DIALOG_STARTED":
            await self.send_response(update, result)
    
    async def handle_task_id_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ответа с ID задачи"""
        await self.report_service.handle_task_id_response(update, context)
    
    async def handle_comment_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ответа с комментарием"""
        await self.report_service.handle_comment_response(update, context)