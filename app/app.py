"""
Prosta aplikacja To-Do w Flasku.
Dane trzymane są w bazie SQLite (plik camper.db) - patrz db.py.
"""

from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import os
import db

app = Flask(__name__)

# SECRET_KEY jest potrzebny, żeby Flask mógł bezpiecznie podpisywać sesje
# (czyli "pamiętać", że jesteś zalogowany). W produkcji ustawimy to jako
# zmienną środowiskową na Railway - tutaj lokalnie ma wartość domyślną.
app.secret_key = os.environ.get("SECRET_KEY", "dev-klucz-tylko-do-testow-lokalnych")

# Hasło do panelu - lokalnie domyślnie "zmienhaslo123", ale docelowo
# ustawimy je jako zmienną środowiskową APP_PASSWORD na Railway.
APP_PASSWORD = os.environ.get("APP_PASSWORD", "zmienhaslo123")

# Tworzymy tabele w bazie danych (jeśli jeszcze nie istnieją) od razu
# przy starcie aplikacji.
db.init_db()


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


@app.route("/")
@login_required
def index():
    tasks = db.get_all_tasks()
    return render_template("index.html", tasks=tasks, active_page="todo")


@app.route("/add", methods=["POST"])
@login_required
def add_task():
    task_text = request.form.get("task", "").strip()
    if task_text:
        db.add_task(task_text)
    return redirect(url_for("index"))


@app.route("/toggle/<int:task_id>")
@login_required
def toggle_task(task_id):
    db.toggle_task(task_id)
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>")
@login_required
def delete_task(task_id):
    db.delete_task(task_id)
    return redirect(url_for("index"))


@app.route("/issues")
@login_required
def issues():
    all_issues = db.get_all_issues()
    columns = {
        "todo": [i for i in all_issues if i["status"] == "todo"],
        "doing": [i for i in all_issues if i["status"] == "doing"],
        "done": [i for i in all_issues if i["status"] == "done"],
    }
    return render_template("issues.html", columns=columns, active_page="issues")


@app.route("/issues/add", methods=["POST"])
@login_required
def add_issue():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if title:
        db.add_issue(title, description)
    return redirect(url_for("issues"))


@app.route("/issues/advance/<int:issue_id>")
@login_required
def advance_issue(issue_id):
    db.advance_issue(issue_id)
    return redirect(url_for("issues"))


@app.route("/issues/delete/<int:issue_id>")
@login_required
def delete_issue(issue_id):
    db.delete_issue(issue_id)
    return redirect(url_for("issues"))


if __name__ == "__main__":
    # debug=True przydaje się przy nauce - pokazuje błędy w przeglądarce
    app.run(debug=True, port=5000)
