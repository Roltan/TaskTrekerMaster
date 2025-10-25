import sqlite3
from typing import List, Dict, Any, Optional

class Model:
    def __init__(self, db_path: str = "timers.db", table_name: str = None):
        self.db_path = db_path
        self.table_name = table_name
        self._initTable()
    
    def _connect(self):
        """Создание соединения с базой данных"""
        return sqlite3.connect(self.db_path)
    
    def tableSchema(self):
        return []
    
    def _initTable(self):
        # НЕ используйте параметризацию для имен таблиц и столбцов
        schema = ",\n                    ".join(self.tableSchema())
        create_query = f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {schema}
            )
        '''
        
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(create_query)
            conn.commit()
    
    def create(self, data: Dict[str, Any]) -> bool:
        """Создание новой записи"""
        if not self.table_name:
            raise ValueError("Table name not specified")
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = list(data.values())
        
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f'INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})',
                    values
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return False
    
    def read(self, conditions: Dict[str, Any] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Чтение записей с условиями"""
        if not self.table_name:
            raise ValueError("Table name not specified")
        
        query = f'SELECT * FROM {self.table_name}'
        params = []
        
        if conditions:
            where_parts = []
            for key, value in conditions.items():
                if value is None:
                    where_parts.append(f'{key} IS NULL')
                else:
                    where_parts.append(f'{key} = ?')
                    params.append(value)
            
            where_clause = ' AND '.join(where_parts)
            query += f' WHERE {where_clause}'
        
        if limit:
            query += f' LIMIT {limit}'
        
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def read_one(self, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Чтение одной записи"""
        results = self.read(conditions, limit=1)
        return results[0] if results else None
    
    def update(self, updates: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """Обновление записей"""
        if not self.table_name:
            raise ValueError("Table name not specified")
        
        set_clause = ', '.join([f'{key} = ?' for key in updates.keys()])
        where_clause = ' AND '.join([f'{key} = ?' for key in conditions.keys()])
        
        params = list(updates.values()) + list(conditions.values())
        
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'UPDATE {self.table_name} SET {set_clause} WHERE {where_clause}',
                params
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete(self, conditions: Dict[str, Any]) -> bool:
        """Удаление записей"""
        if not self.table_name:
            raise ValueError("Table name not specified")
        
        where_clause = ' AND '.join([f'{key} = ?' for key in conditions.keys()])
        params = list(conditions.values())
        
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'DELETE FROM {self.table_name} WHERE {where_clause}',
                params
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def execute_custom_query(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Выполнение кастомного SQL запроса"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            else:
                conn.commit()
                return []