from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -----------------------
# DATABASE SETUP
# -----------------------
def init_db():
    conn = sqlite3.connect(os.path.join(os.getcwd(), "grindleague.db"))
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            team TEXT,
            xp INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            team TEXT,
            message TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------
# HOME / LOGIN
# -----------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form.get("username")
        team = request.form.get("team")

        if not username or not team:
            return redirect("/")

        session["username"] = username
        session["team"] = team

        conn = sqlite3.connect(os.path.join(os.getcwd(), "grindleague.db"))
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()

        if not user:
            c.execute(
                "INSERT INTO users (username, team, xp) VALUES (?, ?, 0)",
                (username, team)
            )
            conn.commit()

        conn.close()
        return redirect("/dashboard")

    return render_template("home.html")


# -----------------------
# DASHBOARD
# -----------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "username" not in session:
        return redirect("/")

    username = session["username"]
    team = session["team"]

    conn = sqlite3.connect(os.path.join(os.getcwd(), "grindleague.db"))
    c = conn.cursor()

    # Handle XP submission with proof
    if request.method == "POST":
        action = request.form.get("action")
        file = request.files.get("proof")

        if action and file and file.filename != "":
            filename = f"{datetime.now().timestamp()}_{file.filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            xp_values = {
                "workout": 15,
                "study": 10,
                "business": 20,
                "money": 25
            }

            xp_gain = xp_values.get(action, 0)

            c.execute("UPDATE users SET xp = xp + ? WHERE username = ?", (xp_gain, username))
            conn.commit()

    # Get user XP
    c.execute("SELECT xp FROM users WHERE username = ?", (username,))
    user_xp = c.fetchone()[0]

    # Level system
    level = user_xp // 100 + 1
    progress_percent = user_xp % 100

    # Team leaderboard
    c.execute("""
        SELECT username, xp
        FROM users
        WHERE team = ?
        ORDER BY xp DESC
        LIMIT 5
    """, (team,))
    team_leaderboard = c.fetchall()

    # Global leaderboard
    c.execute("""
        SELECT username, xp
        FROM users
        ORDER BY xp DESC
        LIMIT 5
    """)
    top_contributors = c.fetchall()

    # Chat preview
    c.execute("""
        SELECT username, message
        FROM messages
        WHERE team = ?
        ORDER BY id DESC
        LIMIT 5
    """, (team,))
    messages = c.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        username=username,
        team=team,
        user_xp=user_xp,
        level=level,
        progress_percent=progress_percent,
        team_leaderboard=team_leaderboard,
        top_contributors=top_contributors,
        messages=messages
    )


# -----------------------
# CHAT PAGE
# -----------------------
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "username" not in session:
        return redirect("/")

    username = session["username"]
    team = session["team"]

    conn = sqlite3.connect(os.path.join(os.getcwd(), "grindleague.db"))
    c = conn.cursor()

    if request.method == "POST":
        message = request.form.get("message")

        if message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute(
                "INSERT INTO messages (username, team, message, timestamp) VALUES (?, ?, ?, ?)",
                (username, team, message, timestamp)
            )
            conn.commit()

    c.execute("""
        SELECT username, message, timestamp
        FROM messages
        WHERE team = ?
        ORDER BY id DESC
        LIMIT 50
    """, (team,))
    messages = c.fetchall()

    conn.close()

    return render_template(
        "chat.html",
        messages=messages,
        username=username
    )


# -----------------------
# LEADERBOARDS PAGE
# -----------------------
@app.route("/leaderboards")
def leaderboards():
    if "username" not in session:
        return redirect("/")

    conn = sqlite3.connect(os.path.join(os.getcwd(), "grindleague.db"))
    c = conn.cursor()

    c.execute("""
        SELECT username, xp
        FROM users
        ORDER BY xp DESC
    """)
    users = c.fetchall()

    conn.close()

    return render_template("leaderboards.html", users=users)


# -----------------------
# LOGOUT
# -----------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
