import os
import sqlite3

from config import Config


def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                total_words INTEGER,
                total_pages INTEGER,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reading_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                current_page INTEGER DEFAULT 0,
                current_word_position INTEGER DEFAULT 0,
                pages_per_day INTEGER DEFAULT 1,
                last_sent_date DATE,
                completed_date DATE,
                FOREIGN KEY (book_id) REFERENCES books(id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        defaults = {
            "default_pages_per_day": str(Config.DEFAULT_PAGES_PER_DAY),
            "send_time": Config.SEND_TIME.strftime("%H:%M"),
            "email_address": Config.EMAIL_ADDRESS,
            "timezone": "local",
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?);",
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
