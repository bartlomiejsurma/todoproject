import io
import os
import sqlite3

from app import db
from app.routes import app as flask_app


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

    trip_id = db.add_trip("Weekend in Gdansk", "Gdansk", "2024-07-10", "2024-07-12", "Relax")
    trip = db.get_trip(trip_id)

    assert trip["title"] == "Weekend in Gdansk"
    assert trip["kilometers"] == 0.0
    assert trip["image"] == ""


def test_add_trip_with_places_and_expenses(tmp_path):
    db.DB_FILE = str(tmp_path / "travel_test.db")
    db.init_db()

    trip_id = db.add_trip(
        "Weekend in Gdansk",
        "Gdansk",
        "2024-07-10",
        "2024-07-12",
        "Relax",
    )
    place_id = db.add_trip_place(trip_id, "Long Market", 1, "Visited")
    expense_id = db.add_trip_expense(trip_id, "Lunch", 45.5, "2024-07-10", "Local")

    trips = db.get_all_trips()
    assert len(trips) == 1
    assert trips[0]["title"] == "Weekend in Gdansk"

    places = db.get_trip_places(trip_id)
    assert len(places) == 1
    assert places[0]["name"] == "Long Market"
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

    trip_id = db.add_trip("Summer trip", "Krakow", "2024-08-01", "2024-08-03", "Old note")
    expense_id = db.add_trip_expense(trip_id, "Dinner", 20.0, "2024-08-02", "Food")

    db.update_trip(trip_id, note="Updated note", kilometers=250.0)
    db.update_trip_expense(expense_id, "Dinner", 30.0, "2024-08-02", "Food", "Updated")
    db.delete_trip(trip_id)

    assert db.get_trip(trip_id) is None
    assert db.get_trip_expenses(trip_id) == []


def test_trip_details_hidden_until_trip_is_selected(tmp_path):
    db.DB_FILE = str(tmp_path / "travel_route_test.db")
    db.init_db()
    db.add_trip("Weekend in Gdansk", "Gdansk", "2024-07-10", "2024-07-12", "Relax")

    client = flask_app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True

    response = client.get("/podroze")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Trip plan" not in body
    assert "Trip expenses" not in body


def test_trip_photo_upload_adds_image_to_gallery(tmp_path):
    db.DB_FILE = str(tmp_path / "travel_gallery_test.db")
    db.init_db()
    trip_id = db.add_trip("Weekend in Gdansk", "Gdansk", "2024-07-10", "2024-07-12", "Relax")

    flask_app.config["ATTACHMENTS_FOLDER"] = str(tmp_path / "attachments")
    flask_app.config["UPLOAD_FOLDER"] = str(tmp_path / "gallery")
    os.makedirs(flask_app.config["ATTACHMENTS_FOLDER"], exist_ok=True)
    os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)

    client = flask_app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True

    response = client.post(
        "/podroze",
        data={
            "action": "upload_image",
            "trip_id": trip_id,
            "trip_image": (io.BytesIO(b"fake-image-data"), "photo.jpg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    gallery_files = os.listdir(flask_app.config["UPLOAD_FOLDER"])
    assert any(name.endswith(".jpg") for name in gallery_files)

    gallery_response = client.get("/gallery")
    body = gallery_response.get_data(as_text=True)
    assert "Weekend in Gdansk" in body


def test_multiple_trip_photo_uploads_are_kept(tmp_path):
    db.DB_FILE = str(tmp_path / "travel_gallery_multi_test.db")
    db.init_db()
    trip_id = db.add_trip("Weekend in Gdansk", "Gdansk", "2024-07-10", "2024-07-12", "Relax")

    flask_app.config["ATTACHMENTS_FOLDER"] = str(tmp_path / "attachments")
    flask_app.config["UPLOAD_FOLDER"] = str(tmp_path / "gallery")
    os.makedirs(flask_app.config["ATTACHMENTS_FOLDER"], exist_ok=True)
    os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)

    client = flask_app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True

    client.post(
        "/podroze",
        data={
            "action": "upload_image",
            "trip_id": trip_id,
            "trip_image": (io.BytesIO(b"first"), "photo1.jpg"),
        },
        content_type="multipart/form-data",
    )
    client.post(
        "/podroze",
        data={
            "action": "upload_image",
            "trip_id": trip_id,
            "trip_image": (io.BytesIO(b"second"), "photo2.jpg"),
        },
        content_type="multipart/form-data",
    )

    gallery_files = os.listdir(flask_app.config["UPLOAD_FOLDER"])
    assert len(gallery_files) >= 2
