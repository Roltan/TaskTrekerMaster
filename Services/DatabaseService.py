import sqlite3
import os
from datetime import datetime

class DatabaseService:
    def __init__(self, db_path="timers.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    b24_id INTEGER NOT NULL,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS timers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    total_seconds REAL DEFAULT 0,
                    task_id INTEGER,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS timer_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timer_name TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_seconds REAL,
                    FOREIGN KEY (user_id, timer_name) REFERENCES timers (user_id, name)
                )
            ''')
            conn.commit()
    
    def create_timer(self, user_id, name, task_id='', type=2):
        """Создание нового таймера для пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                if (type == 2): comment = 'кч'
                if (type == 1): comment = 'нкч'
                if (type == 0): comment = 'баги'

                cursor.execute(
                    'INSERT INTO timers (user_id, name, task_id, comment) VALUES (?, ?, ?, ?)',
                    (user_id, name, task_id, comment)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Таймер уже существует у этого пользователя
                return False
    
    def get_today_timers(self, user_id):
        """Получение таймеров пользователя, созданных сегодня"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, total_seconds 
                FROM timers 
                WHERE user_id = ? AND DATE(created_at) = DATE('now')
            ''', (user_id,))
            timers = {}
            for row in cursor.fetchall():
                timers[row[0]] = {
                    'total_seconds': row[1]
                }
            return timers

    def get_timer(self, user_id, name):
        """Получение данных таймера пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT name, total_seconds FROM timers WHERE user_id = ? AND name = ?',
                (user_id, name)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'total_seconds': result[1]
                }
            return None
    
    def add_time_to_timer(self, user_id, name, seconds_to_add):
        """Добавление времени к таймеру пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE timers SET total_seconds = total_seconds + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND name = ?',
                (seconds_to_add, user_id, name)
            )
            conn.commit()
    
    def start_timer_session(self, user_id, timer_name, start_time):
        """Начало сессии таймера пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO timer_sessions (user_id, timer_name, start_time) VALUES (?, ?, ?)',
                (user_id, timer_name, start_time)
            )
            conn.commit()
            return cursor.lastrowid
    
    def stop_timer_session(self, session_id, end_time, duration_seconds):
        """Завершение сессии таймера"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE timer_sessions SET end_time = ?, duration_seconds = ? WHERE id = ?',
                (end_time, duration_seconds, session_id)
            )
            conn.commit()
    
    def delete_timer(self, user_id, name):
        """Удаление таймера пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Сначала удаляем связанные сессии
            cursor.execute('DELETE FROM timer_sessions WHERE user_id = ? AND timer_name = ?', (user_id, name))
            # Затем удаляем таймер
            cursor.execute('DELETE FROM timers WHERE user_id = ? AND name = ?', (user_id, name))
            conn.commit()
    
    def get_active_sessions(self, user_id):
        """Получение всех активных сессий пользователя (с пустым end_time)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timer_name 
                FROM timer_sessions 
                WHERE user_id = ? AND end_time IS NULL
            ''', (user_id,))
            active_sessions = {}
            for row in cursor.fetchall():
                active_sessions[row[1]] = row[0]  # timer_name -> session_id
            return active_sessions

    def get_session_start_time(self, session_id):
        """Получение времени начала сессии"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT start_time FROM timer_sessions WHERE id = ?', (session_id,))
            result = cursor.fetchone()
            return result[0] if result else None