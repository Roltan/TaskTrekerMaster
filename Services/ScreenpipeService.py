import os
import requests
from datetime import datetime
from typing import Optional, Dict


class ScreenpipeService:
    """Сервис для работы с Screenpipe API"""

    def __init__(self):
        self.api_url = "http://localhost:3030"
        self.api_key = os.getenv('SCREENPIPE_LOCAL_API_KEY', '')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Отладочный вывод
        if self.api_key:
            print(f"Screenpipe: ключ загружен (длина: {len(self.api_key)})")
        else:
            print("Screenpipe: ключ НЕ загружен из .env")

    def save_task_memory(self, timer_name: str, start_time: datetime, end_time: datetime, duration_seconds: float) -> bool:
        """
        Сохранить запись о задаче в Screenpipe Memory с тегом проекта

        Args:
            timer_name: Название таймера
            start_time: Время начала работы
            end_time: Время окончания работы
            duration_seconds: Длительность в секундах

        Returns:
            True если успешно, False при ошибке
        """
        if not self.api_key:
            print("SCREENPIPE_LOCAL_API_KEY не установлен, пропускаем сохранение в Screenpipe")
            return False

        try:
            duration_minutes = int(duration_seconds / 60)
            hours = int(duration_minutes // 60)
            minutes = int(duration_minutes % 60)

            # Формируем описание
            start_str = start_time.strftime("%H:%M")
            end_str = end_time.strftime("%H:%M")

            # Используем латиницу для совместимости с Screenpipe
            content = f"Task '{timer_name}': {start_str} - {end_str}, duration {hours}h {minutes}m"

            # Формируем запрос для создания Memory
            payload = {
                "content": content,
                "tags": [f"project:{timer_name}"],
                "source": "telegram-bot",
                "importance": 0.7
            }

            print(f"Screenpipe: отправка запроса к {self.api_url}/memories")
            print(f"Payload: {payload}")

            response = requests.post(
                f"{self.api_url}/memories",
                headers=self.headers,
                json=payload,
                timeout=10
            )

            print(f"Screenpipe: статус ответа {response.status_code}")

            if response.status_code == 200 or response.status_code == 201:
                print(f"Screenpipe: сохранена запись для '{timer_name}' ({duration_minutes} мин)")
                print(f"Ответ: {response.text}")
                return True
            else:
                print(f"Screenpipe: ошибка сохранения memory: {response.status_code}")
                if response.text:
                    print(f"Ответ: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Screenpipe: ошибка подключения: {e}")
            return False


# Singleton instance
screenpipe_service = ScreenpipeService()
