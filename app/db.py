"""
Moduł obsługi bazy danych SQLite.

Baza danych to plik `camper.db`, który powstaje automatycznie przy pierwszym
uruchomieniu aplikacji. Trzyma się w nim wszystkie dane - na razie tylko
zadania (tasks), ale w przyszłości dojdą kolejne tabele (usterki, wydatki,
terminy).
"""

import sqlite3
import os
from datetime import date

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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo',
            category TEXT NOT NULL DEFAULT 'others',
            image TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL DEFAULT 'other',
            expense_date TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            amount REAL NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            due_date TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    ensure_task_category_column(conn)
    ensure_task_description_column(conn)
    ensure_task_image_column(conn)
    ensure_issue_category_column(conn)
    ensure_issue_image_column(conn)
    conn.close()


def ensure_task_category_column(conn):
    """Dodaje kolumnę category do tabeli tasks, jeśli jej brak."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "category" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN category TEXT NOT NULL DEFAULT 'others'"
        )
        conn.commit()


def ensure_task_description_column(conn):
    """Dodaje kolumnę description do tabeli tasks, jeśli jej brak."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "description" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT ''"
        )
        conn.commit()


def ensure_task_image_column(conn):
    """Dodaje kolumnę image do tabeli tasks, jeśli jej brak."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "image" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN image TEXT NOT NULL DEFAULT ''"
        )
        conn.commit()


def ensure_issue_image_column(conn):
    """Dodaje kolumnę image do tabeli issues, jeśli jej brak."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(issues)").fetchall()]
    if "image" not in columns:
        conn.execute(
            "ALTER TABLE issues ADD COLUMN image TEXT NOT NULL DEFAULT ''"
        )
        conn.commit()


def ensure_issue_category_column(conn):
    """Dodaje kolumnę category, jeśli stara schemat bazy jej nie zawiera."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(issues)").fetchall()]
    if "category" not in columns:
        conn.execute(
            "ALTER TABLE issues ADD COLUMN category TEXT NOT NULL DEFAULT 'others'"
        )
        conn.commit()


# --- Funkcje do obsługi zadań (tasks) ---

def get_all_tasks(category=None):
    conn = get_connection()
    if category and category in TASK_CATEGORIES:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE category = ? ORDER BY id DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_task(task_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return row


def add_task(text, category="others", description="", image=""):
    if category not in TASK_CATEGORIES:
        category = "others"
    conn = get_connection()
    conn.execute(
        "INSERT INTO tasks (text, done, category, description, image) VALUES (?, 0, ?, ?, ?)",
        (text, category, description, image),
    )
    conn.commit()
    conn.close()


def update_task(task_id, text, description="", category="others", image=None):
    if category not in TASK_CATEGORIES:
        category = "others"
    conn = get_connection()
    if image is not None:
        conn.execute(
            "UPDATE tasks SET text = ?, description = ?, category = ?, image = ? WHERE id = ?",
            (text, description, category, image, task_id),
        )
    else:
        conn.execute(
            "UPDATE tasks SET text = ?, description = ?, category = ? WHERE id = ?",
            (text, description, category, task_id),
        )
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


# --- Funkcje do obsługi usterek/pomysłów (issues) ---

# Kolejność statusów - używana do przycisku "przenieś dalej"
ISSUE_STATUSES = ["todo", "doing", "done"]

# Kategorie usterek/pomysłów
ISSUE_CATEGORIES = ["electricity", "mechanical parts", "hydraulics", "interior", "others"]
ISSUE_CATEGORY_LABELS = {
    "electricity": "Elektryka",
    "mechanical parts": "Elementy Mechaniczne",
    "hydraulics": "Hydraulika",
    "interior": "Wnętrze",
    "others": "Inne",
}

TASK_CATEGORIES = ISSUE_CATEGORIES
TASK_CATEGORY_LABELS = ISSUE_CATEGORY_LABELS

# --- Finanse ---
EXPENSE_CATEGORIES = ["maintenance", "parts_tools", "materials", "other"]
EXPENSE_CATEGORY_LABELS = {
    "maintenance": "Naprawy",
    "parts_tools": "Narzędzia",
    "materials": "Materiały",
    "other": "Inne",
    # legacy labels for old expense data
    "fuel": "Paliwo",
    "food": "Jedzenie",
    "lodging": "Noclegi",
    "equipment": "Wyposażenie",
}


def get_all_issues(category=None):
    conn = get_connection()
    if category:
        rows = conn.execute(
            "SELECT * FROM issues WHERE category = ? ORDER BY id DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM issues ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def get_issue(issue_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    conn.close()
    return row


def add_issue(title, description="", category="others", image=""):
    if category not in ISSUE_CATEGORIES:
        category = "others"
    conn = get_connection()
    conn.execute(
        "INSERT INTO issues (title, description, status, category, image) VALUES (?, ?, 'todo', ?, ?)",
        (title, description, category, image),
    )
    conn.commit()
    conn.close()


def update_issue(issue_id, title, description="", category="others", image=None):
    if category not in ISSUE_CATEGORIES:
        category = "others"
    conn = get_connection()
    if image is not None:
        conn.execute(
            "UPDATE issues SET title = ?, description = ?, category = ?, image = ? WHERE id = ?",
            (title, description, category, image, issue_id),
        )
    else:
        conn.execute(
            "UPDATE issues SET title = ?, description = ?, category = ? WHERE id = ?",
            (title, description, category, issue_id),
        )
    conn.commit()
    conn.close()


# --- Finanse ---

def get_all_expenses(category=None, start_date=None, end_date=None, min_amount=None, max_amount=None):
    conn = get_connection()
    query = "SELECT * FROM expenses"
    clauses = []
    params = []
    if category and category in EXPENSE_CATEGORIES:
        clauses.append("category = ?")
        params.append(category)
    if start_date:
        clauses.append("expense_date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("expense_date <= ?")
        params.append(end_date)
    if min_amount is not None:
        clauses.append("amount >= ?")
        params.append(min_amount)
    if max_amount is not None:
        clauses.append("amount <= ?")
        params.append(max_amount)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY expense_date DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_expense(expense_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return row


def add_expense(title, amount, category="other", expense_date=None, note=""):
    if category not in EXPENSE_CATEGORIES:
        category = "other"
    if not expense_date:
        expense_date = date.today().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT INTO expenses (title, amount, category, expense_date, note) VALUES (?, ?, ?, ?, ?)",
        (title, amount, category, expense_date, note),
    )
    conn.commit()
    conn.close()


def update_expense(expense_id, title, amount, category="other", expense_date=None, note=""):
    if category not in EXPENSE_CATEGORIES:
        category = "other"
    if not expense_date:
        expense_date = date.today().isoformat()
    conn = get_connection()
    conn.execute(
        "UPDATE expenses SET title = ?, amount = ?, category = ?, expense_date = ?, note = ? WHERE id = ?",
        (title, amount, category, expense_date, note, expense_id),
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id):
    conn = get_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def get_budget():
    conn = get_connection()
    row = conn.execute("SELECT amount FROM budget WHERE id = 1").fetchone()
    conn.close()
    return row["amount"] if row else 0.0


def set_budget(amount):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO budget (id, amount) VALUES (1, ?)", (amount,))
    conn.commit()
    conn.close()


def get_expense_summary(expenses):
    totals = {category: 0.0 for category in EXPENSE_CATEGORIES}
    for expense in expenses:
        category = expense["category"]
        if category not in totals:
            totals[category] = 0.0
        totals[category] += float(expense["amount"])
    return totals


def get_monthly_summary(expenses):
    monthly = {}
    for expense in expenses:
        month = expense["expense_date"][:7]
        monthly[month] = monthly.get(month, 0.0) + float(expense["amount"])
    return dict(sorted(monthly.items()))


def get_expense_reports(expenses):
    total = sum(float(exp["amount"]) for exp in expenses)
    count = len(expenses)
    average = total / count if count else 0
    max_expense = max((float(exp["amount"]) for exp in expenses), default=0)
    min_expense = min((float(exp["amount"]) for exp in expenses), default=0)
    return {
        "total": total,
        "count": count,
        "average": average,
        "max": max_expense,
        "min": min_expense,
    }


def get_top_categories(expenses, limit=5):
    totals = {}
    for expense in expenses:
        cat = expense["category"]
        totals[cat] = totals.get(cat, 0.0) + float(expense["amount"])
    items = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return items[:limit]


def get_expense_total(expenses):
    return sum(float(exp["amount"]) for exp in expenses)


def get_remaining_budget(expenses, budget):
    return budget - get_expense_total(expenses)


def get_budget_usage(expenses, budget):
    total = get_expense_total(expenses)
    return (total / budget * 100) if budget and total else 0


def advance_issue(issue_id):
    """Przesuwa kartę do następnego statusu (todo -> doing -> done)."""
    conn = get_connection()
    row = conn.execute("SELECT status FROM issues WHERE id = ?", (issue_id,)).fetchone()
    if row:
        current_index = ISSUE_STATUSES.index(row["status"])
        if current_index < len(ISSUE_STATUSES) - 1:
            new_status = ISSUE_STATUSES[current_index + 1]
            conn.execute("UPDATE issues SET status = ? WHERE id = ?", (new_status, issue_id))
            conn.commit()
    conn.close()


def revert_issue(issue_id):
    """Przesuwa kartę do poprzedniego statusu (done -> doing -> todo)."""
    conn = get_connection()
    row = conn.execute("SELECT status FROM issues WHERE id = ?", (issue_id,)).fetchone()
    if row:
        current_index = ISSUE_STATUSES.index(row["status"])
        if current_index > 0:
            new_status = ISSUE_STATUSES[current_index - 1]
            conn.execute("UPDATE issues SET status = ? WHERE id = ?", (new_status, issue_id))
            conn.commit()
    conn.close()


def delete_issue(issue_id):
    conn = get_connection()
    conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()


# --- Funkcje do obsługi terminów (deadlines) ---

def get_all_deadlines():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM deadlines ORDER BY due_date ASC, id DESC").fetchall()
    conn.close()
    return rows


def add_deadline(title, due_date, note=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO deadlines (title, due_date, note) VALUES (?, ?, ?)",
        (title, due_date, note),
    )
    conn.commit()
    conn.close()


def delete_deadline(deadline_id):
    conn = get_connection()
    conn.execute("DELETE FROM deadlines WHERE id = ?", (deadline_id,))
    conn.commit()
    conn.close()


def get_deadline(deadline_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM deadlines WHERE id = ?", (deadline_id,)).fetchone()
    conn.close()
    return row


def update_deadline(deadline_id, title, due_date, note=""):
    conn = get_connection()
    conn.execute(
        "UPDATE deadlines SET title = ?, due_date = ?, note = ? WHERE id = ?",
        (title, due_date, note, deadline_id),
    )
    conn.commit()
    conn.close()
