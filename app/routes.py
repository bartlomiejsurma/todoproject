"""
A simple Flask To-Do application.
Data is stored in a SQLite database (camper.db) - see db.py.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import date
from werkzeug.utils import secure_filename
import os
from . import db

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "gallery")
app.config["ATTACHMENTS_FOLDER"] = os.path.join(app.root_path, "static", "attachments")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["ATTACHMENTS_FOLDER"], exist_ok=True)

# SECRET_KEY is required so Flask can securely sign sessions.
# In production we will set it as a Railway environment variable.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-for-local-testing")

# Admin panel password - locally defaults to "changeme123", but in production
# this should be set via the APP_PASSWORD environment variable.
APP_PASSWORD = os.environ.get("APP_PASSWORD", "changeme123")

# Create the database tables if they do not already exist at startup.
db.init_db()


def login_required(view_func):
    """Decorator that blocks access to a page unless the user is logged in."""
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
        error = "Wrong password, please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
def home():
    tasks = db.get_all_tasks()
    deadlines = db.get_all_deadlines()
    trips = db.get_all_trips()
    return render_template(
        "home.html",
        active_page="home",
        overview_counts={
            "ideas": len(tasks),
            "deadlines": len(deadlines),
            "trips": len(trips),
        },
    )


@app.route("/podroze", methods=["GET", "POST"])
@login_required
def trips():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add_trip":
            title = request.form.get("title", "").strip()
            destination = request.form.get("destination", "").strip()
            start_date = request.form.get("start_date", "")
            end_date = request.form.get("end_date", "")
            note = request.form.get("note", "").strip()
            kilometers = request.form.get("kilometers", "0").replace(",", ".")
            try:
                kilometers_value = float(kilometers)
            except ValueError:
                kilometers_value = 0.0
            if title and destination and start_date and end_date:
                db.add_trip(title, destination, start_date, end_date, note, kilometers_value)
        elif action == "edit_trip":
            trip_id = request.form.get("trip_id")
            title = request.form.get("title", "").strip()
            destination = request.form.get("destination", "").strip()
            start_date = request.form.get("start_date", "")
            end_date = request.form.get("end_date", "")
            note = request.form.get("note", "").strip()
            kilometers = request.form.get("kilometers", "0").replace(",", ".")
            try:
                kilometers_value = float(kilometers)
            except ValueError:
                kilometers_value = 0.0
            if trip_id:
                db.update_trip(trip_id, title=title or None, destination=destination or None, start_date=start_date or None, end_date=end_date or None, note=note, kilometers=kilometers_value)
        elif action == "delete_trip":
            trip_id = request.form.get("trip_id")
            if trip_id:
                db.delete_trip(trip_id)
        elif action == "upload_image":
            trip_id = request.form.get("trip_id")
            image_file = request.files.get("trip_image")
            if trip_id and image_file and image_file.filename:
                image_name = save_attachment(image_file)
                if image_name:
                    db.update_trip(trip_id, image=image_name)
        elif action == "add_place":
            trip_id = request.form.get("trip_id")
            name = request.form.get("place_name", "").strip()
            visited = request.form.get("visited") == "on"
            note = request.form.get("place_note", "").strip()
            if trip_id and name:
                db.add_trip_place(trip_id, name, 1 if visited else 0, note)
        elif action == "add_expense":
            trip_id = request.form.get("trip_id")
            title = request.form.get("expense_title", "").strip()
            amount = request.form.get("expense_amount", "0").replace(",", ".")
            expense_date = request.form.get("expense_date", "")
            category = request.form.get("expense_category", "").strip()
            note = request.form.get("expense_note", "").strip()
            try:
                amount_value = float(amount)
            except ValueError:
                amount_value = 0.0
            if trip_id and title and amount_value > 0 and expense_date:
                db.add_trip_expense(trip_id, title, amount_value, expense_date, category, note)
        elif action == "edit_expense":
            expense_id = request.form.get("expense_id")
            title = request.form.get("expense_title", "").strip()
            amount = request.form.get("expense_amount", "0").replace(",", ".")
            expense_date = request.form.get("expense_date", "")
            category = request.form.get("expense_category", "").strip()
            note = request.form.get("expense_note", "").strip()
            try:
                amount_value = float(amount)
            except ValueError:
                amount_value = None
            if expense_id and title and amount_value is not None and expense_date:
                db.update_trip_expense(expense_id, title=title, amount=amount_value, expense_date=expense_date, category=category, note=note)
        elif action == "delete_expense":
            expense_id = request.form.get("expense_id")
            if expense_id:
                db.delete_trip_expense(expense_id)
        elif action == "toggle_place":
            place_id = request.form.get("place_id")
            if place_id:
                db.toggle_trip_place(place_id)
        return redirect(url_for("trips"))

    trips = db.get_all_trips()
    trip_expense_totals = {}
    for trip in trips:
        trip_expenses = db.get_trip_expenses(trip["id"])
        trip_expense_totals[trip["id"]] = sum(expense["amount"] for expense in trip_expenses)

    selected_trip_id = request.args.get("trip_id")
    selected_trip = None
    selected_places = []
    selected_expenses = []
    if selected_trip_id:
        selected_trip = db.get_trip(selected_trip_id)
        if selected_trip:
            selected_places = db.get_trip_places(selected_trip_id)
            selected_expenses = db.get_trip_expenses(selected_trip_id)
    if not selected_trip and trips:
        selected_trip = trips[0]
        selected_trip_id = str(selected_trip["id"])
        selected_places = db.get_trip_places(selected_trip["id"])
        selected_expenses = db.get_trip_expenses(selected_trip["id"])

    return render_template(
        "podroze.html",
        active_page="podroze",
        trips=trips,
        trip_expense_totals=trip_expense_totals,
        selected_trip=selected_trip,
        selected_trip_id=selected_trip_id,
        selected_places=selected_places,
        selected_expenses=selected_expenses,
        today=date.today().isoformat(),
    )


def save_attachment(file):
    if not file or file.filename == "":
        return ""
    if not allowed_file(file.filename):
        return ""
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["ATTACHMENTS_FOLDER"], filename)
    if os.path.exists(save_path):
        name, ext = os.path.splitext(filename)
        index = 1
        while os.path.exists(save_path):
            filename = f"{name}_{index}{ext}"
            save_path = os.path.join(app.config["ATTACHMENTS_FOLDER"], filename)
            index += 1
    file.save(save_path)
    return filename


def remove_attachment(filename):
    if not filename:
        return
    path = os.path.join(app.config["ATTACHMENTS_FOLDER"], filename)
    if os.path.isfile(path):
        os.remove(path)


@app.route("/todo")
@login_required
def index():
    selected_category = request.args.get("category")
    if selected_category not in db.TASK_CATEGORIES:
        selected_category = None
    tasks = db.get_all_tasks(category=selected_category)
    return render_template(
        "index.html",
        tasks=tasks,
        active_page="todo",
        categories=db.TASK_CATEGORIES,
        category_labels=db.TASK_CATEGORY_LABELS,
        selected_category=selected_category,
    )


@app.route("/add", methods=["POST"])
@login_required
def add_task():
    task_text = request.form.get("task", "").strip()
    category = request.form.get("category", "others")
    description = request.form.get("description", "").strip()
    image_file = request.files.get("image")
    image_name = save_attachment(image_file)
    if task_text:
        db.add_task(task_text, category, description, image_name)
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


@app.route("/tasks/transfer/<int:task_id>")
@login_required
def transfer_task_to_issue(task_id):
    task = next((t for t in db.get_all_tasks() if t["id"] == task_id), None)
    if task:
        db.add_issue(task["text"], task["description"], task["category"], task["image"])
        db.delete_task(task_id)
    return redirect(url_for("index"))


@app.route("/todo/card/<int:task_id>", methods=["GET", "POST"])
@login_required
def task_card(task_id):
    task = db.get_task(task_id)
    if not task:
        return redirect(url_for("index"))

    if request.method == "POST":
        task_text = request.form.get("task", "").strip()
        category = request.form.get("category", "others")
        description = request.form.get("description", "").strip()
        image_file = request.files.get("image")
        image_name = task["image"]
        if image_file and image_file.filename:
            saved_name = save_attachment(image_file)
            if saved_name:
                image_name = saved_name
        db.update_task(task_id, task_text, description, category, image_name)
        return redirect(url_for("task_card", task_id=task_id))

    return render_template(
        "task_card.html",
        task=task,
        active_page="todo",
        categories=db.TASK_CATEGORIES,
        category_labels=db.TASK_CATEGORY_LABELS,
    )


@app.route("/todo/card/<int:task_id>/delete_attachment")
@login_required
def delete_task_attachment(task_id):
    task = db.get_task(task_id)
    if task and task["image"]:
        remove_attachment(task["image"])
        db.update_task(task_id, task["text"], task["description"], task["category"], "")
    return redirect(url_for("task_card", task_id=task_id))


@app.route("/issues")
@login_required
def issues():
    category = request.args.get("category")
    if category not in db.ISSUE_CATEGORIES:
        category = None
    all_issues = db.get_all_issues(category=category)
    columns = {
        "todo": [i for i in all_issues if i["status"] == "todo"],
        "doing": [i for i in all_issues if i["status"] == "doing"],
        "done": [i for i in all_issues if i["status"] == "done"],
    }
    return render_template(
        "issues.html",
        columns=columns,
        active_page="issues",
        selected_category=category,
        categories=db.ISSUE_CATEGORIES,
        category_labels=db.ISSUE_CATEGORY_LABELS,
    )


@app.route("/issues/add", methods=["POST"])
@login_required
def add_issue():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "others")
    image_file = request.files.get("image")
    image_name = save_attachment(image_file)
    if title:
        db.add_issue(title, description, category, image_name)
    return redirect(url_for("issues", category=category if category in db.ISSUE_CATEGORIES else None))


@app.route("/issues/card/<int:issue_id>", methods=["GET", "POST"])
@login_required
def issue_card(issue_id):
    issue = db.get_issue(issue_id)
    if not issue:
        return redirect(url_for("issues"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "others")
        status = request.form.get("status", issue["status"])
        image_file = request.files.get("image")
        image_name = issue["image"]
        if image_file and image_file.filename:
            saved_name = save_attachment(image_file)
            if saved_name:
                image_name = saved_name
        db.update_issue(issue_id, title, description, category, image_name)
        if status in db.ISSUE_STATUSES:
            conn = db.get_connection()
            conn.execute("UPDATE issues SET status = ? WHERE id = ?", (status, issue_id))
            conn.commit()
            conn.close()
        return redirect(url_for("issue_card", issue_id=issue_id))

    return render_template(
        "issue_card.html",
        issue=issue,
        active_page="issues",
        categories=db.ISSUE_CATEGORIES,
        category_labels=db.ISSUE_CATEGORY_LABELS,
        status_labels={"todo": "Do zrobienia", "doing": "W trakcie", "done": "Zrobione"},
    )


@app.route("/issues/card/<int:issue_id>/delete_attachment")
@login_required
def delete_issue_attachment(issue_id):
    issue = db.get_issue(issue_id)
    if issue and issue["image"]:
        remove_attachment(issue["image"])
        db.update_issue(issue_id, issue["title"], issue["description"], issue["category"], "")
    return redirect(url_for("issue_card", issue_id=issue_id))


@app.route("/issues/advance/<int:issue_id>")
@login_required
def advance_issue(issue_id):
    db.advance_issue(issue_id)
    return redirect(url_for("issues"))


@app.route("/issues/revert/<int:issue_id>")
@login_required
def revert_issue(issue_id):
    db.revert_issue(issue_id)
    return redirect(url_for("issues"))


@app.route("/issues/send_back/<int:issue_id>")
@login_required
def send_issue_back_to_tasks(issue_id):
    issue = db.get_issue(issue_id)
    if issue and issue["status"] == "todo":
        db.add_task(issue["title"], issue["category"], issue["description"], issue["image"])
        db.delete_issue(issue_id)
    return redirect(url_for("issues"))


@app.route("/issues/delete/<int:issue_id>")
@login_required
def delete_issue(issue_id):
    db.delete_issue(issue_id)
    return redirect(url_for("issues"))


@app.route("/finanse")
@login_required
def finanse():
    selected_category = request.args.get("category")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    min_amount = request.args.get("min_amount")
    max_amount = request.args.get("max_amount")
    try:
        min_amount_val = float(min_amount) if min_amount else None
    except ValueError:
        min_amount_val = None
    try:
        max_amount_val = float(max_amount) if max_amount else None
    except ValueError:
        max_amount_val = None

    expenses = db.get_all_expenses(
        category=selected_category,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount_val,
        max_amount=max_amount_val,
    )
    incomes = db.get_all_incomes(
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount_val,
        max_amount=max_amount_val,
    )
    expense_total = db.get_expense_total(expenses)
    income_total = db.get_income_total(incomes)
    budget = income_total
    remaining = budget - expense_total
    usage = (expense_total / budget * 100) if budget else 0
    category_totals = db.get_expense_summary(expenses)
    month_totals = db.get_monthly_summary(expenses)
    monthly_category_summary = db.get_monthly_category_summary(expenses)
    monthly_income_summary = db.get_monthly_income_summary(incomes)
    monthly_income_vs_expense_summary = db.get_monthly_income_vs_expense_summary(incomes, expenses)
    max_month_total = max(month_totals.values()) if month_totals else 0
    max_income_total = max(monthly_income_summary.values()) if monthly_income_summary else 0
    max_comparison_total = max(
        [values["income"] for values in monthly_income_vs_expense_summary.values()] + [values["expense"] for values in monthly_income_vs_expense_summary.values()],
        default=0,
    )
    report = db.get_expense_reports(expenses)
    top_categories = db.get_top_categories(expenses)
    today = date.today().isoformat()
    category_colors = {
        "maintenance": "#3b82f6",
        "parts_tools": "#8b5cf6",
        "materials": "#10b981",
        "other": "#f59e0b",
    }

    return render_template(
        "finanse.html",
        active_page="finanse",
        expenses=expenses,
        incomes=incomes,
        categories=db.EXPENSE_CATEGORIES,
        category_labels=db.EXPENSE_CATEGORY_LABELS,
        selected_category=selected_category,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        budget=budget,
        expense_total=expense_total,
        income_total=income_total,
        remaining=remaining,
        usage=usage,
        category_totals=category_totals,
        month_totals=month_totals,
        monthly_category_summary=monthly_category_summary,
        monthly_income_summary=monthly_income_summary,
        monthly_income_vs_expense_summary=monthly_income_vs_expense_summary,
        max_month_total=max_month_total,
        max_income_total=max_income_total,
        max_comparison_total=max_comparison_total,
        report=report,
        top_categories=top_categories,
        today=today,
        category_colors=category_colors,
    )


@app.route("/finanse/budget", methods=["POST"])
@login_required
def update_budget():
    return redirect(url_for("finanse"))


@app.route("/finanse/add", methods=["POST"])
@login_required
def add_expense():
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "0").replace(",", ".")
    category = request.form.get("category", "other")
    expense_date = request.form.get("expense_date")
    note = request.form.get("note", "").strip()
    try:
        amount_value = float(amount)
    except ValueError:
        amount_value = 0.0
    if title and amount_value > 0 and expense_date:
        db.add_expense(title, amount_value, category, expense_date, note)
    return redirect(url_for("finanse"))


@app.route("/finanse/income", methods=["POST"])
@login_required
def add_income():
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "0").replace(",", ".")
    income_date = request.form.get("income_date")
    note = request.form.get("note", "").strip()
    try:
        amount_value = float(amount)
    except ValueError:
        amount_value = 0.0
    if title and amount_value > 0 and income_date:
        db.add_income(title, amount_value, income_date, note)
    return redirect(url_for("finanse"))


@app.route("/expenses/card/<int:expense_id>", methods=["GET", "POST"])
@login_required
def expense_card(expense_id):
    expense = db.get_expense(expense_id)
    if not expense:
        return redirect(url_for("finanse"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount = request.form.get("amount", "0").replace(",", ".")
        category = request.form.get("category", "other")
        expense_date = request.form.get("expense_date")
        note = request.form.get("note", "").strip()
        try:
            amount_value = float(amount)
        except ValueError:
            amount_value = 0.0
        if title and amount_value > 0 and expense_date:
            db.update_expense(expense_id, title, amount_value, category, expense_date, note)
        return redirect(url_for("expense_card", expense_id=expense_id))
    return render_template(
        "expense_card.html",
        active_page="finanse",
        expense=expense,
        categories=db.EXPENSE_CATEGORIES,
        category_labels=db.EXPENSE_CATEGORY_LABELS,
    )


@app.route("/expenses/delete/<int:expense_id>")
@login_required
def delete_expense(expense_id):
    db.delete_expense(expense_id)
    return redirect(url_for("finanse"))


@app.route("/incomes/card/<int:income_id>", methods=["GET", "POST"])
@login_required
def income_card(income_id):
    income = db.get_income(income_id)
    if not income:
        return redirect(url_for("finanse"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount = request.form.get("amount", "0").replace(",", ".")
        income_date = request.form.get("income_date")
        note = request.form.get("note", "").strip()
        try:
            amount_value = float(amount)
        except ValueError:
            amount_value = 0.0
        if title and amount_value > 0 and income_date:
            db.update_income(income_id, title, amount_value, income_date, note)
        return redirect(url_for("income_card", income_id=income_id))
    return render_template(
        "income_card.html",
        active_page="finanse",
        income=income,
    )


@app.route("/incomes/delete/<int:income_id>")
@login_required
def delete_income(income_id):
    db.delete_income(income_id)
    return redirect(url_for("finanse"))


@app.route("/deadlines")
@login_required
def deadlines():
    raw_deadlines = db.get_all_deadlines()
    today = date.today()
    deadlines = []
    for item in raw_deadlines:
        try:
            due_date = date.fromisoformat(item["due_date"])
            days_until = (due_date - today).days
        except ValueError:
            days_until = None

        urgency = "green"
        urgency_label = "Over a month"
        if days_until is None:
            urgency = "gray"
            urgency_label = "Brak daty"
        elif days_until < 0:
            urgency = "red"
            urgency_label = "Deadline passed"
        elif days_until <= 7:
            urgency = "red"
            urgency_label = "Less than a week"
        elif days_until <= 30:
            urgency = "yellow"
            urgency_label = "Less than a month"

        row = dict(item)
        row["urgency"] = urgency
        row["urgency_label"] = urgency_label
        deadlines.append(row)
    return render_template("deadlines.html", deadlines=deadlines, active_page="deadlines")


@app.route("/deadlines/add", methods=["POST"])
@login_required
def add_deadline():
    title = request.form.get("title", "").strip()
    due_date = request.form.get("due_date", "").strip()
    note = request.form.get("note", "").strip()
    if title and due_date:
        db.add_deadline(title, due_date, note)
    return redirect(url_for("deadlines"))


@app.route("/deadlines/edit/<int:deadline_id>", methods=["GET", "POST"])
@login_required
def edit_deadline(deadline_id):
    deadline = db.get_deadline(deadline_id)
    if not deadline:
        return redirect(url_for("deadlines"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        due_date = request.form.get("due_date", "").strip()
        note = request.form.get("note", "").strip()
        if title and due_date:
            db.update_deadline(deadline_id, title, due_date, note)
            return redirect(url_for("deadlines"))

    return render_template("deadline_edit.html", deadline=deadline, active_page="deadlines")


@app.route("/deadlines/delete/<int:deadline_id>")
@login_required
def delete_deadline(deadline_id):
    db.delete_deadline(deadline_id)
    return redirect(url_for("deadlines"))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/gallery")
@login_required
def gallery():
    sort_mode = request.args.get("sort", "newest")
    files = []
    for f in os.listdir(app.config["UPLOAD_FOLDER"]):
        path = os.path.join(app.config["UPLOAD_FOLDER"], f)
        if os.path.isfile(path) and allowed_file(f):
            files.append((f, os.path.getmtime(path)))

    reverse = sort_mode != "oldest"
    files.sort(key=lambda item: item[1], reverse=reverse)
    files = [filename for filename, _ in files]
    return render_template("gallery.html", files=files, active_page="gallery", sort_mode=sort_mode)


@app.route("/gallery/upload", methods=["POST"])
@login_required
def upload_gallery():
    file = request.files.get("photo")
    if not file or file.filename == "":
        flash("Nie wybrano pliku.", "error")
        return redirect(url_for("gallery"))
    if not allowed_file(file.filename):
        flash("Unsupported file type. Use PNG, JPG, JPEG, or GIF.", "error")
        return redirect(url_for("gallery"))
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(save_path):
        name, ext = os.path.splitext(filename)
        index = 1
        while os.path.exists(save_path):
            filename = f"{name}_{index}{ext}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            index += 1
    file.save(save_path)
    flash("Photo added to the gallery.", "success")
    return redirect(url_for("gallery"))


@app.route("/gallery/delete/<path:filename>")
@login_required
def delete_gallery(filename):
    filename = os.path.basename(filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.isfile(file_path) and allowed_file(filename):
        os.remove(file_path)
        flash("Photo removed.", "success")
    else:
        flash("No photo found to remove.", "error")
    return redirect(url_for("gallery"))


if __name__ == "__main__":
    # debug=True is useful for learning and shows errors in the browser
    app.run(debug=True, port=5000)
