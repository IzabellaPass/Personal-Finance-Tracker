"""Create an empty finance database without overwriting existing data."""

import sqlite3
from pathlib import Path


database_path = Path(__file__).with_name("finance.db")

with sqlite3.connect(database_path) as connection:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute("INSERT OR IGNORE INTO diaries(name) VALUES ('Il mio diario')")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            description TEXT DEFAULT '',
            transaction_time TEXT DEFAULT '',
            diary_id INTEGER REFERENCES diaries(id)
        )
        """
    )

print(f"Database ready: {database_path}")
