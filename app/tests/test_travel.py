import sqlite3

import db


def test_init_db_adds_missing_trip_columns(tmp_path):
    db.DB_FILE = str(tmp_path / "travel_schema_test.db")
    conn = sqlite3.connect(db.DB_FILE)
    conn.execute(
        """
        CREATE TABLE trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            destination TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            note TEXT DEFAULT ''
        )
        """
    )
    conn.commit()
    conn.close()

    db.init_db()

    trip_id = db.add_trip("Weekend in Gdańsk", "Gdańsk", "2024-07-10", "2024-07-12", "Relax")
    trip = db.get_trip(trip_id)

    assert trip["title"] == "Weekend in Gdańsk"
    assert trip["kilometers"] == 0.0
    assert trip["image"] == ""


def test_add_trip_with_places_and_expenses(tmp_path):
    db.DB_FILE = str(tmp_path / "travel_test.db")
    db.init_db()

    trip_id = db.add_trip(
        "Weekend in Gdańsk",
        "Gdańsk",
        "2024-07-10",
        "2024-07-12",
        "Relax",
    )
    place_id = db.add_trip_place(trip_id, "Długi Targ", 1, "Visited")
    expense_id = db.add_trip_expense(trip_id, "Lunch", 45.5, "2024-07-10", "Local")

    trips = db.get_all_trips()
    assert len(trips) == 1
    assert trips[0]["title"] == "Weekend in Gdańsk"

    places = db.get_trip_places(trip_id)
    assert len(places) == 1
    assert places[0]["name"] == "Długi Targ"
    assert places[0]["visited"] == 1

    expenses = db.get_trip_expenses(trip_id)
    assert len(expenses) == 1
    assert expenses[0]["title"] == "Lunch"
    assert expenses[0]["amount"] == 45.5
    assert expense_id is not None
    assert place_id is not None


def test_update_trip_expense_and_delete_trip(tmp_path):
    db.DB_FILE = str(tmp_path / "travel_update_test.db")
    db.init_db()

    trip_id = db.add_trip("Summer trip", "Kraków", "2024-08-01", "2024-08-03", "Old note")
    expense_id = db.add_trip_expense(trip_id, "Dinner", 20.0, "2024-08-02", "Food")

    db.update_trip(trip_id, note="Updated note", kilometers=250.0)
    db.update_trip_expense(expense_id, "Dinner", 30.0, "2024-08-02", "Food", "Updated")
    db.delete_trip(trip_id)

    assert db.get_trip(trip_id) is None
    assert db.get_trip_expenses(trip_id) == []
