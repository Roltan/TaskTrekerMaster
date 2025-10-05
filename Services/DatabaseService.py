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
                CREATE TABLE IF NOT EXISTS timers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    total_seconds REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS timer_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timer_name TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_seconds REAL,
                    FOREIGN KEY (timer_name) REFERENCES timers (name)
                )
            ''')
            conn.commit()
    
    def create_timer(self, name):
        """Создание нового таймера"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO timers (name) VALUES (?)',
                    (name,)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Таймер уже существует
                return False
    
    def get_today_timers(self):
        """Получение таймеров, созданных сегодня"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, total_seconds 
                FROM timers 
                WHERE DATE(created_at) = DATE('now')
            ''')
            timers = {}
            for row in cursor.fetchall():
                timers[row[0]] = {
                    'total_seconds': row[1],
                }
            return timers

    def get_timer(self, name):
        """Получение данных таймера"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT name, total_seconds FROM timers WHERE name = ?',
                (name,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'name': result[0],
                    'total_seconds': result[1]
                }
            return None

    def add_time_to_timer(self, name, seconds_to_add):
        """Добавление времени к таймеру"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE timers SET total_seconds = total_seconds + ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?',
                (seconds_to_add, name)
            )
            conn.commit()
    
    def start_timer_session(self, timer_name, start_time):
        """Начало сессии таймера"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO timer_sessions (timer_name, start_time) VALUES (?, ?)',
                (timer_name, start_time)
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
    
    def delete_timer(self, name):
        """Удаление таймера"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Сначала удаляем связанные сессии
            cursor.execute('DELETE FROM timer_sessions WHERE timer_name = ?', (name,))
            # Затем удаляем таймер
            cursor.execute('DELETE FROM timers WHERE name = ?', (name,))
            conn.commit()
    
    def get_active_sessions(self):
        """Получение всех активных сессий (с пустым end_time)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, timer_name 
                FROM timer_sessions 
                WHERE end_time IS NULL
            ''')
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