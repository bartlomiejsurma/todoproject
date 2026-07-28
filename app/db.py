"""
Moduł obsługi bazy danych SQLite.

Baza danych to plik `camper.db`, który powstaje automatycznie przy pierwszym
uruchomieniu aplikacji. Trzyma się w nim wszystkie dane - na razie tylko
zadania (tasks), ale w przyszłości dojdą kolejne tabele (usterki, wydatki,
terminy).
"""

import sqlite3
import os

DB_FILE = os.environ.get("DB_FILE", "camper.db")


def get_connection():
    """Otwiera połączenie z bazą danych."""
    conn = sqlite3.connect(DB_FILE)
    # Dzięki temu wyniki zapytań zachowują się jak słowniki (dostęp po nazwie
    # kolumny, np. row["text"]), a nie tylko po numerze indeksu.
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Tworzy tabele w bazie danych, jeśli jeszcze nie istnieją.
    Bezpieczne do wywołania wielokrotnie - nic nie nadpisuje istniejących danych."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# --- Funkcje do obsługi zadań (tasks) ---

def get_all_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def add_task(text):
    conn = get_connection()
    conn.execute("INSERT INTO tasks (text, done) VALUES (?, 0)", (text,))
    conn.commit()
    conn.close()


def toggle_task(task_id):
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET done = NOT done WHERE id = ?", (task_id,)
    )
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
