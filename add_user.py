import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = "users.db"

def add_user(username, password):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    hashed_password = generate_password_hash(password)
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        print(f"User '{username}' added successfully!")
    except sqlite3.IntegrityError:
        print(f"Username '{username}' already exists!")

    conn.close()

# Add a new user
add_user("stuti", "stuti123")  # Change username & password as needed
