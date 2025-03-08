import os
import sqlite3
import subprocess
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = "users.db"
TEST_SCRIPT = os.path.abspath("test.py")  # Get full path of test.py

# ✅ Initialize Database
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ✅ Route: Home/Login Page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session["user"] = username
            flash("Login successful!", "success")

            # ✅ Start `test.py` with a new terminal (for Windows)
            try:
                subprocess.Popen(["python", TEST_SCRIPT], creationflags=subprocess.CREATE_NEW_CONSOLE)

                time.sleep(2)  # Wait for `test.py` to start
            except Exception as e:
                flash(f"Error starting 3D printer interface: {str(e)}", "danger")
                return redirect(url_for("login"))

            return redirect(url_for("printer_interface"))  # Redirect to the printer page
        else:
            flash("Invalid username or password!", "danger")

    return render_template("login.html")

# ✅ Route: 3D Printer Interface (After Login)
@app.route("/printer")
def printer_interface():
    if "user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    return "Loading 3D Printer Queue (test.py)... If this does not load, restart Flask."

# ✅ Route: Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
