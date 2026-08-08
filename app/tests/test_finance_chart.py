import re
import uuid

from app import db, app


def test_get_monthly_category_summary_groups_expenses_by_month_and_category():
    expenses = [
        {"category": "maintenance", "amount": 50.0, "expense_date": "2024-07-01"},
        {"category": "materials", "amount": 30.0, "expense_date": "2024-07-05"},
        {"category": "maintenance", "amount": 20.0, "expense_date": "2024-08-01"},
    ]

    result = db.get_monthly_category_summary(expenses)

    assert result["2024-07"] == [("maintenance", 50.0), ("materials", 30.0)]
    assert result["2024-08"] == [("maintenance", 20.0)]


def test_get_monthly_income_summary_groups_incomes_by_month():
    incomes = [
        {"amount": 100.0, "income_date": "2024-07-10"},
        {"amount": 50.0, "income_date": "2024-07-15"},
        {"amount": 25.0, "income_date": "2024-08-01"},
    ]

    result = db.get_monthly_income_summary(incomes)

    assert result["2024-07"] == 150.0
    assert result["2024-08"] == 25.0


def test_get_monthly_income_vs_expense_summary_returns_both_series():
    expenses = [{"amount": 40.0, "expense_date": "2024-07-20"}]
    incomes = [{"amount": 100.0, "income_date": "2024-07-10"}]

    result = db.get_monthly_income_vs_expense_summary(incomes, expenses)

    assert result["2024-07"] == {"income": 100.0, "expense": 40.0}


def test_update_and_delete_income_records():
    db.add_income("Test Income", 125.0, "2024-09-05", "Initial note")
    created = next(item for item in db.get_all_incomes() if item["title"] == "Test Income")

    db.update_income(created["id"], "Updated Income", 200.0, "2024-09-06", "Updated note")
    updated = db.get_income(created["id"])

    assert updated["title"] == "Updated Income"
    assert updated["amount"] == 200.0
    assert updated["note"] == "Updated note"

    db.delete_income(created["id"])
    assert db.get_income(created["id"]) is None


def test_finance_page_renders_income_rows_in_template():
    db.add_income("Visible Income", 77.5, "2024-10-01", "Should appear")

    with app.test_client() as client:
        with client.session_transaction() as session:
            session["logged_in"] = True
        response = client.get("/finanse")

    assert response.status_code == 200
    assert b"Visible Income" in response.data


def test_finance_page_includes_scroll_restore_script():
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["logged_in"] = True
        response = client.get("/finanse")

    assert response.status_code == 200
    assert b"finance-scroll-position" in response.data


def test_home_page_overview_counts_are_dynamic():
    db.add_task("Home overview task", "others", "test")
    db.add_deadline("Home overview deadline", "2099-01-01", "test")
    db.add_trip("Home overview trip", "Test destination", "2099-01-01", "2099-01-02", "test")

    with app.test_client() as client:
        response = client.get("/")

    html = response.get_data(as_text=True)
    ideas_match = re.search(r"<span>Ideas</span>\s*<strong>(\d+)</strong>", html)
    deadlines_match = re.search(r"<span>Deadlines</span>\s*<strong>(\d+)</strong>", html)
    trips_match = re.search(r"<span>Trips</span>\s*<strong>(\d+)</strong>", html)

    assert response.status_code == 200
    assert ideas_match is not None
    assert deadlines_match is not None
    assert trips_match is not None
    assert int(ideas_match.group(1)) >= 1
    assert int(deadlines_match.group(1)) >= 1
    assert int(trips_match.group(1)) >= 1


def test_get_all_incomes_filters_by_date_and_amount():
    matched_title = f"Filtered Income {uuid.uuid4().hex[:6]}"
    other_title = f"Other Income {uuid.uuid4().hex[:6]}"
    small_title = f"Small Income {uuid.uuid4().hex[:6]}"

    db.add_income(matched_title, 120.0, "2024-11-10", "keep")
    db.add_income(other_title, 80.0, "2024-11-20", "drop")
    db.add_income(small_title, 40.0, "2024-10-15", "drop")

    result = db.get_all_incomes(start_date="2024-11-01", end_date="2024-11-30", min_amount=100.0)
    filtered_titles = [row["title"] for row in result if row["title"] in {matched_title, other_title, small_title}]

    assert filtered_titles == [matched_title]
