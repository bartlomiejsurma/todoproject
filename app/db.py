"""
SQLite database handling module.

The database is stored in the `camper.db` file, which is created automatically
on first application startup. It stores all app data, including tasks, issues,
expenses, deadlines, and trips.
"""

import sqlite3
import os
from datetime import date

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "camper.db")
DB_FILE = os.environ.get("DB_FILE", DEFAULT_DB_FILE)


def get_connection():
    """Open a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    # This makes query results behave like dictionaries (accessible by column name,
    # e.g. row["text"]) rather than by numeric index.
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create database tables if they do not exist.
    Safe to call repeatedly; it does not overwrite existing data."""
    db_dir = os.path.dirname(DB_FILE)
    if db_dir and not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)
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
        CREATE TABLE IF NOT EXISTS incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            income_date TEXT NOT NULL,
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            destination TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            note TEXT DEFAULT '',
            kilometers REAL NOT NULL DEFAULT 0,
            image TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trip_places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            visited INTEGER NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trip_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT NOT NULL,
            category TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(trip_id) REFERENCES trips(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    ensure_task_category_column(conn)
    ensure_task_description_column(conn)
    ensure_task_image_column(conn)
    ensure_issue_category_column(conn)
    ensure_issue_image_column(conn)
    ensure_trip_kilometers_column(conn)
    ensure_trip_image_column(conn)
    conn.close()


def ensure_task_category_column(conn):
    """Add the category column to the tasks table if it is missing."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "category" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN category TEXT NOT NULL DEFAULT 'others'"
        )
        conn.commit()


def ensure_task_description_column(conn):
    """Add the description column to the tasks table if it is missing."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "description" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT ''"
        )
        conn.commit()


def ensure_task_image_column(conn):
    """Add the image column to the tasks table if it is missing."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "image" not in columns:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN image TEXT NOT NULL DEFAULT ''"
        )
        conn.commit()


def ensure_issue_image_column(conn):
    """Add the image column to the issues table if it is missing."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(issues)").fetchall()]
    if "image" not in columns:
        conn.execute(
            "ALTER TABLE issues ADD COLUMN image TEXT NOT NULL DEFAULT ''"
        )
        conn.commit()


def ensure_issue_category_column(conn):
    """Add the category column if the existing database schema does not contain it."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(issues)").fetchall()]
    if "category" not in columns:
        conn.execute(
            "ALTER TABLE issues ADD COLUMN category TEXT NOT NULL DEFAULT 'others'"
        )
        conn.commit()


def ensure_trip_kilometers_column(conn):
    """Add the kilometers column to the trips table if it is missing."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(trips)").fetchall()]
    if "kilometers" not in columns:
        conn.execute("ALTER TABLE trips ADD COLUMN kilometers REAL NOT NULL DEFAULT 0")
        conn.commit()


def ensure_trip_image_column(conn):
    """Add the image column to the trips table if it is missing."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(trips)").fetchall()]
    if "image" not in columns:
        conn.execute("ALTER TABLE trips ADD COLUMN image TEXT NOT NULL DEFAULT ''")
        conn.commit()


# --- Task handling functions ---

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


def add_trip(title, destination, start_date, end_date, note="", kilometers=0.0, image=""):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO trips (title, destination, start_date, end_date, note, kilometers, image) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (title, destination, start_date, end_date, note, kilometers, image),
    )
    conn.commit()
    trip_id = cursor.lastrowid
    conn.close()
    return trip_id


def update_trip(trip_id, title=None, destination=None, start_date=None, end_date=None, note=None, kilometers=None, image=None):
    conn = get_connection()
    updates = []
    values = []
    if title is not None:
        updates.append("title = ?")
        values.append(title)
    if destination is not None:
        updates.append("destination = ?")
        values.append(destination)
    if start_date is not None:
        updates.append("start_date = ?")
        values.append(start_date)
    if end_date is not None:
        updates.append("end_date = ?")
        values.append(end_date)
    if note is not None:
        updates.append("note = ?")
        values.append(note)
    if kilometers is not None:
        updates.append("kilometers = ?")
        values.append(kilometers)
    if image is not None:
        updates.append("image = ?")
        values.append(image)
    if updates:
        values.append(trip_id)
        conn.execute(f"UPDATE trips SET {', '.join(updates)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_trip(trip_id):
    conn = get_connection()
    conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()


def get_all_trips():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM trips ORDER BY start_date DESC, id DESC").fetchall()
    conn.close()
    return rows


def get_trip(trip_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
    conn.close()
    return row


def add_trip_place(trip_id, name, visited=0, note=""):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO trip_places (trip_id, name, visited, note) VALUES (?, ?, ?, ?)",
        (trip_id, name, int(visited), note),
    )
    conn.commit()
    place_id = cursor.lastrowid
    conn.close()
    return place_id


def get_trip_places(trip_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM trip_places WHERE trip_id = ? ORDER BY id ASC",
        (trip_id,),
    ).fetchall()
    conn.close()
    return rows


def toggle_trip_place(place_id):
    conn = get_connection()
    conn.execute("UPDATE trip_places SET visited = NOT visited WHERE id = ?", (place_id,))
    conn.commit()
    conn.close()


def add_trip_expense(trip_id, title, amount, expense_date, category="", note=""):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO trip_expenses (trip_id, title, amount, expense_date, category, note) VALUES (?, ?, ?, ?, ?, ?)",
        (trip_id, title, amount, expense_date, category, note),
    )
    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()
    return expense_id


def update_trip_expense(expense_id, title=None, amount=None, expense_date=None, category=None, note=None):
    conn = get_connection()
    updates = []
    values = []
    if title is not None:
        updates.append("title = ?")
        values.append(title)
    if amount is not None:
        updates.append("amount = ?")
        values.append(amount)
    if expense_date is not None:
        updates.append("expense_date = ?")
        values.append(expense_date)
    if category is not None:
        updates.append("category = ?")
        values.append(category)
    if note is not None:
        updates.append("note = ?")
        values.append(note)
    if updates:
        values.append(expense_id)
        conn.execute(f"UPDATE trip_expenses SET {', '.join(updates)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_trip_expense(expense_id):
    conn = get_connection()
    conn.execute("DELETE FROM trip_expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def get_trip_expenses(trip_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM trip_expenses WHERE trip_id = ? ORDER BY expense_date DESC, id DESC",
        (trip_id,),
    ).fetchall()
    conn.close()
    return rows


# --- Issues and ideas handling functions ---

# Status order - used by the "move forward" button
ISSUE_STATUSES = ["todo", "doing", "done"]

# Categories for issues and ideas
ISSUE_CATEGORIES = ["electricity", "mechanical parts", "hydraulics", "interior", "others"]
ISSUE_CATEGORY_LABELS = {
    "electricity": "Electrical",
    "mechanical parts": "Mechanical Parts",
    "hydraulics": "Hydraulics",
    "interior": "Interior",
    "others": "Other",
}

TASK_CATEGORIES = ISSUE_CATEGORIES
TASK_CATEGORY_LABELS = ISSUE_CATEGORY_LABELS

# --- Finanse ---
EXPENSE_CATEGORIES = ["maintenance", "parts_tools", "materials", "other"]
EXPENSE_CATEGORY_LABELS = {
    "maintenance": "Maintenance",
    "parts_tools": "Tools",
    "materials": "Materials",
    "other": "Other",
    # legacy labels for old expense data
    "fuel": "Fuel",
    "food": "Food",
    "lodging": "Lodging",
    "equipment": "Equipment",
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


def add_income(title, amount, income_date=None, note=""):
    if not income_date:
        income_date = date.today().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT INTO incomes (title, amount, income_date, note) VALUES (?, ?, ?, ?)",
        (title, amount, income_date, note),
    )
    conn.commit()
    conn.close()


def get_all_incomes(start_date=None, end_date=None, min_amount=None, max_amount=None):
    conn = get_connection()
    query = "SELECT * FROM incomes"
    clauses = []
    params = []
    if start_date:
        clauses.append("income_date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("income_date <= ?")
        params.append(end_date)
    if min_amount is not None:
        clauses.append("amount >= ?")
        params.append(min_amount)
    if max_amount is not None:
        clauses.append("amount <= ?")
        params.append(max_amount)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY income_date DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_income(income_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM incomes WHERE id = ?", (income_id,)).fetchone()
    conn.close()
    return row


def update_income(income_id, title, amount, income_date=None, note=""):
    if not income_date:
        income_date = date.today().isoformat()
    conn = get_connection()
    conn.execute(
        "UPDATE incomes SET title = ?, amount = ?, income_date = ?, note = ? WHERE id = ?",
        (title, amount, income_date, note, income_id),
    )
    conn.commit()
    conn.close()


def delete_income(income_id):
    conn = get_connection()
    conn.execute("DELETE FROM incomes WHERE id = ?", (income_id,))
    conn.commit()
    conn.close()


def get_income_total(incomes):
    return sum(float(item["amount"]) for item in incomes)


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


def get_monthly_category_summary(expenses):
    monthly = {}
    for expense in expenses:
        month = expense["expense_date"][:7]
        category = expense["category"]
        month_totals = monthly.setdefault(month, {})
        month_totals[category] = month_totals.get(category, 0.0) + float(expense["amount"])

    return {
        month: [
            (category, totals[category])
            for category in sorted(totals, key=lambda item: totals[item], reverse=True)
        ]
        for month, totals in sorted(monthly.items())
    }


def get_monthly_summary(expenses):
    monthly = {}
    for expense in expenses:
        month = expense["expense_date"][:7]
        monthly[month] = monthly.get(month, 0.0) + float(expense["amount"])
    return dict(sorted(monthly.items()))


def get_monthly_income_summary(incomes):
    monthly = {}
    for income in incomes:
        month = income["income_date"][:7]
        monthly[month] = monthly.get(month, 0.0) + float(income["amount"])
    return dict(sorted(monthly.items()))


def get_monthly_income_vs_expense_summary(incomes, expenses):
    monthly = {}
    for income in incomes:
        month = income["income_date"][:7]
        monthly.setdefault(month, {"income": 0.0, "expense": 0.0})
        monthly[month]["income"] += float(income["amount"])

    for expense in expenses:
        month = expense["expense_date"][:7]
        monthly.setdefault(month, {"income": 0.0, "expense": 0.0})
        monthly[month]["expense"] += float(expense["amount"])

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
    """Move the card to the next status (todo -> doing -> done)."""
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
    """Move the card to the previous status (done -> doing -> todo)."""
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


# --- Deadline handling functions ---

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
