import db


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
