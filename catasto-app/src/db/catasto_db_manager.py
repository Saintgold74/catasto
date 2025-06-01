# File: /catasto-app/catasto-app/src/db/catasto_db_manager.py

import sqlite3
from typing import Any, Dict, List, Optional

class CatastoDBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self.connection = sqlite3.connect(self.db_path)

    def close(self) -> None:
        if self.connection:
            self.connection.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> None:
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            self.connection.commit()

    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def create_user(self, username: str, password_hash: str, full_name: str, email: str, role: str) -> bool:
        query = """
        INSERT INTO users (username, password_hash, full_name, email, role)
        VALUES (?, ?, ?, ?, ?)
        """
        try:
            self.execute_query(query, (username, password_hash, full_name, email, role))
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user_credentials(self, username: str) -> Optional[Dict[str, Any]]:
        query = "SELECT id, password_hash FROM users WHERE username = ?"
        return self.fetch_one(query, (username,))

    def register_access(self, user_id: int, action: str, indirizzo_ip: str, esito: bool, application_name: str) -> Optional[str]:
        query = """
        INSERT INTO access_logs (user_id, action, indirizzo_ip, esito, application_name)
        VALUES (?, ?, ?, ?, ?)
        """
        self.execute_query(query, (user_id, action, indirizzo_ip, esito, application_name))
        return self.connection.lastrowid

    def get_comuni(self, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM comuni"
        if filter_text:
            query += " WHERE nome LIKE ?"
            return self.fetch_all(query, (f'%{filter_text}%',))
        return self.fetch_all(query)