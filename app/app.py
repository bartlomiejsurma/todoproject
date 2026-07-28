"""
Prosta aplikacja To-Do w Flasku.
Dane zapisywane są w pliku tasks.json (nie potrzeba bazy danych).
"""

from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import json
import os

app = Flask(__name__)

# SECRET_KEY jest potrzebny, żeby Flask mógł bezpiecznie podpisywać sesje
# (czyli "pamiętać", że jesteś zalogowany). W produkcji ustawimy to jako
# zmienną środowiskową na Railway - tutaj lokalnie ma wartość domyślną.
app.secret_key = os.environ.get("SECRET_KEY", "dev-klucz-tylko-do-testow-lokalnych")

# Hasło do panelu - lokalnie domyślnie "zmienhaslo123", ale docelowo
# ustawimy je jako zmienną środowiskową APP_PASSWORD na Railway.
APP_PASSWORD = os.environ.get("APP_PASSWORD", "zmienhaslo123")

DATA_FILE = "tasks.json"


def login_required(view_func):
    """Dekorator: blokuje dostęp do strony, jeśli użytkownik nie jest zalogowany."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        entered_password = request.form.get("password", "")
        if entered_password == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Złe hasło, spróbuj ponownie."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


def load_tasks():
    """Wczytuje listę zadań z pliku. Jeśli plik nie istnieje, zwraca pustą listę."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tasks(tasks):
    """Zapisuje listę zadań do pliku."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


@app.route("/")
@login_required
def index():
    tasks = load_tasks()
    return render_template("index.html", tasks=tasks)


@app.route("/add", methods=["POST"])
@login_required
def add_task():
    task_text = request.form.get("task", "").strip()
    if task_text:
        tasks = load_tasks()
        tasks.append({"text": task_text, "done": False})
        save_tasks(tasks)
    return redirect(url_for("index"))


@app.route("/toggle/<int:task_id>")
@login_required
def toggle_task(task_id):
    tasks = load_tasks()
    if 0 <= task_id < len(tasks):
        tasks[task_id]["done"] = not tasks[task_id]["done"]
        save_tasks(tasks)
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>")
@login_required
def delete_task(task_id):
    tasks = load_tasks()
    if 0 <= task_id < len(tasks):
        tasks.pop(task_id)
        save_tasks(tasks)
    return redirect(url_for("index"))


if __name__ == "__main__":
    # debug=True przydaje się przy nauce - pokazuje błędy w przeglądarce
    app.run(debug=True, port=5000)
