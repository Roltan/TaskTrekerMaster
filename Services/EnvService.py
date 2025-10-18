import os

def update_env_file(access_token, refresh_token):
    """Обновляет токены в .env файле"""
    
    # Читаем текущий .env файл
    env_path = '.env'
    env_lines = []
    
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as file:
            env_lines = file.readlines()
    
    # Обновляем или добавляем токены
    tokens_updated = {
        'CRM_TOKEN': access_token,
        'CRM_REFRESH': refresh_token
    }
    
    new_lines = []
    tokens_found = set()
    
    for line in env_lines:
        line_stripped = line.strip()
        if '=' in line_stripped:
            key = line_stripped.split('=')[0]
            if key in tokens_updated:
                new_lines.append(f"{key}={tokens_updated[key]}\n")
                tokens_found.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Добавляем отсутствующие токены
    for token_key, token_value in tokens_updated.items():
        if token_key not in tokens_found:
            new_lines.append(f"{token_key}={token_value}\n")
    
    # Записываем обратно в файл
    with open(env_path, 'w', encoding='utf-8') as file:
        file.writelines(new_lines)
    
    # Также обновляем переменные окружения в текущей сессии
    os.environ['CRM_TOKEN'] = access_token
    os.environ['CRM_REFRESH'] = refresh_token