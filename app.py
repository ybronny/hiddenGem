from datetime import datetime
from functools import wraps
import os
import random
import sqlite3

from flask import Flask, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "hidden-gem-dev-key")
DATABASE = os.path.join(os.path.dirname(__file__), "hidden_gem.db")

RESTAURANTS = [
    ("Luma", "Modern American", "Brooklyn", "4.8", "$$$", "1.2 mi", "rooftop, date night", "#f1d4bd", "A candlelit neighborhood favorite with market-driven plates and a skyline view."),
    ("Saffron Table", "Indian", "Queens", "4.9", "$$", "2.4 mi", "spicy, groups", "#f4b183", "Regional Indian cooking with bright pickles, handmade breads, and generous sharing plates."),
    ("Mizu House", "Japanese", "Manhattan", "4.7", "$$$$", "3.1 mi", "omakase, quiet", "#b8d8d8", "An intimate sushi counter focused on pristine seafood and a calm, considered rhythm."),
    ("Basil & Brick", "Italian", "Brooklyn", "4.6", "$$", "1.8 mi", "pasta, cozy", "#d9c5a1", "Hand-rolled pasta, natural wine, and the kind of room that makes dinner linger."),
    ("Juniper", "Vegetarian", "Manhattan", "4.8", "$$$", "2.0 mi", "vegetarian, brunch", "#b8c9a8", "Produce-led plates with bold textures, low-intervention wine, and a sunny bar."),
    ("Cinder", "Korean", "Queens", "4.5", "$$", "4.2 mi", "late night, grill", "#d49a8f", "Smoky tabletop grilling and punchy banchan in a lively, late-night dining room."),
]


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cuisine TEXT NOT NULL,
            neighborhood TEXT NOT NULL,
            rating REAL NOT NULL,
            price TEXT NOT NULL,
            distance TEXT NOT NULL,
            tags TEXT NOT NULL,
            color TEXT NOT NULL,
            description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            verification_code TEXT NOT NULL,
            is_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, restaurant_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        );
        """
    )
    if connection.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO restaurants (name, cuisine, neighborhood, rating, price, distance, tags, color, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            RESTAURANTS,
        )
    connection.commit()
    connection.close()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    connection = get_db()
    user = connection.execute("SELECT id, name, email, is_verified FROM users WHERE id = ?", (user_id,)).fetchone()
    connection.close()
    return user


def login_required(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        if not current_user():
            return jsonify({"error": "Please log in to continue."}), 401
        return handler(*args, **kwargs)
    return wrapped


def restaurant_json(row, favorite_ids=()):
    item = dict(row)
    item["tags"] = [tag.strip() for tag in item["tags"].split(",")]
    item["is_favorite"] = item["id"] in favorite_ids
    return item


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/restaurants")
def restaurants():
    query = request.args.get("q", "").strip()
    cuisine = request.args.get("cuisine", "All cuisines")
    sort = request.args.get("sort", "recommended")
    connection = get_db()
    sql = "SELECT * FROM restaurants WHERE (name LIKE ? OR cuisine LIKE ? OR neighborhood LIKE ? OR tags LIKE ?)"
    term = f"%{query}%"
    params = [term, term, term, term]
    if cuisine != "All cuisines":
        sql += " AND cuisine = ?"
        params.append(cuisine)
    sql += " ORDER BY " + ("rating DESC" if sort == "rating" else "name ASC" if sort == "name" else "id ASC")
    rows = connection.execute(sql, params).fetchall()
    user = current_user()
    favorite_ids = set()
    if user:
        favorite_ids = {row[0] for row in connection.execute("SELECT restaurant_id FROM favorites WHERE user_id = ?", (user["id"],)).fetchall()}
    connection.close()
    return jsonify({"restaurants": [restaurant_json(row, favorite_ids) for row in rows], "count": len(rows)})


@app.get("/api/session")
def session_info():
    user = current_user()
    return jsonify({"user": dict(user) if user else None})


@app.post("/api/register")
def register():
    payload = request.get_json() or {}
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    if not name or not email or len(password) < 8:
        return jsonify({"error": "Add your name, a valid email, and a password of at least 8 characters."}), 400
    code = f"{random.randint(100000, 999999)}"
    connection = get_db()
    try:
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash, verification_code, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, generate_password_hash(password), code, datetime.utcnow().isoformat()),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.close()
        return jsonify({"error": "An account with that email already exists."}), 409
    connection.close()
    session["pending_user_id"] = cursor.lastrowid
    return jsonify({"message": "Account created. Enter your verification code.", "demo_code": code})


@app.post("/api/verify")
def verify():
    payload = request.get_json() or {}
    code = payload.get("code", "").strip()
    user_id = session.get("pending_user_id")
    connection = get_db()
    user = connection.execute("SELECT id, verification_code FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user or user["verification_code"] != code:
        connection.close()
        return jsonify({"error": "That verification code is not correct."}), 400
    connection.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))
    connection.commit()
    connection.close()
    session.pop("pending_user_id", None)
    session["user_id"] = user_id
    return jsonify({"message": "Email verified. Welcome to Hidden Gem."})


@app.post("/api/login")
def login():
    payload = request.get_json() or {}
    connection = get_db()
    user = connection.execute("SELECT * FROM users WHERE email = ?", (payload.get("email", "").strip().lower(),)).fetchone()
    connection.close()
    if not user or not check_password_hash(user["password_hash"], payload.get("password", "")):
        return jsonify({"error": "Email or password is incorrect."}), 401
    if not user["is_verified"]:
        session["pending_user_id"] = user["id"]
        return jsonify({"error": "Please verify your email before logging in.", "needs_verification": True}), 403
    session["user_id"] = user["id"]
    return jsonify({"message": f"Welcome back, {user['name']}!"})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out."})


@app.post("/api/favorites/<int:restaurant_id>")
@login_required
def favorite(restaurant_id):
    user = current_user()
    connection = get_db()
    existing = connection.execute("SELECT 1 FROM favorites WHERE user_id = ? AND restaurant_id = ?", (user["id"], restaurant_id)).fetchone()
    if existing:
        connection.execute("DELETE FROM favorites WHERE user_id = ? AND restaurant_id = ?", (user["id"], restaurant_id))
        saved = False
    else:
        connection.execute("INSERT OR IGNORE INTO favorites (user_id, restaurant_id) VALUES (?, ?)", (user["id"], restaurant_id))
        saved = True
    connection.commit()
    connection.close()
    return jsonify({"saved": saved})


init_db()

if __name__ == "__main__":
    app.run(debug=True)
