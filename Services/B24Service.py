import requests
import os
from Services.EnvService import update_env_file
import threading

class B24Service:
    def refreshTokens(self):
        threading.Timer(3500, self.refreshTokens).start()
        try:
            response = requests.get(
                os.getenv('B24_BASE_URL') + 
                '/oauth/token/?grant_type=refresh_token'+
                '&client_id=' + os.getenv('CLIENT_ID') + 
                '&client_secret=' + os.getenv('B24_CLIENT_SECRET') +
                '&refresh_token=' + os.getenv('CRM_REFRESH'),
            )
            response_data = response.json()
            
            if response.status_code == 200 and 'access_token' in response_data:
                
                # Обновляем .env файл
                update_env_file(response_data['access_token'], response_data['refresh_token'])
                
                print("✅ Токены успешно обновлены!")
                return 1
                
            else:
                print(f"❌ Ошибка при обновлении токенов: {response_data}")
                return 0
                
        except Exception as e:
            print(f"❌ Ошибка при запросе: {e}")
            return 0

    def addTime(self, taskId, userId, time, comment):
        response = requests.post(
            os.getenv('B24_BASE_URL') + '/rest/task.elapseditem.add',
            json={
                'auth': os.getenv('CRM_TOKEN'),
                'TASKID': taskId,
                'ARFIELDS': {
                    "SECONDS": time, 
                    "COMMENT_TEXT": comment,
                    "USER_ID": userId
                }
            }
        )
        print(response)
        