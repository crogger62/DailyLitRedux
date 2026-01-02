import os
import sqlite3
from datetime import date

from config import Config
from migrations import migrate


def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    migrate()
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
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed'))
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
                pages_per_day INTEGER DEFAULT 1 CHECK (pages_per_day >= 1),
                last_sent_date DATE,
                completed_date DATE,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reading_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                sent_date DATE NOT NULL,
                start_page INTEGER NOT NULL,
                end_page INTEGER NOT NULL,
                word_start INTEGER NOT NULL,
                word_end INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
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

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_progress_book_id ON reading_progress(book_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_book_date ON reading_history(book_id, sent_date);"
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


def insert_book(
    title,
    author,
    filename,
    file_path,
    file_type,
    total_words,
    total_pages,
):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO books (
                title,
                author,
                filename,
                file_path,
                file_type,
                total_words,
                total_pages
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                title,
                author,
                filename,
                file_path,
                file_type,
                total_words,
                total_pages,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def insert_progress(book_id, pages_per_day):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO reading_progress (book_id, pages_per_day)
            VALUES (?, ?);
            """,
            (book_id, pages_per_day),
        )
        conn.commit()
    finally:
        conn.close()


def get_books_with_progress():
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT
                books.id,
                books.title,
                books.author,
                books.total_pages,
                books.status,
                reading_progress.current_page,
                reading_progress.pages_per_day
            FROM books
            JOIN reading_progress ON reading_progress.book_id = books.id
            ORDER BY books.upload_date DESC;
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_book_detail(book_id):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT
                books.id,
                books.title,
                books.author,
                books.file_path,
                books.file_type,
                books.total_words,
                books.total_pages,
                books.status,
                books.upload_date,
                reading_progress.current_page,
                reading_progress.current_word_position,
                reading_progress.pages_per_day,
                reading_progress.last_sent_date,
                reading_progress.completed_date
            FROM books
            JOIN reading_progress ON reading_progress.book_id = books.id
            WHERE books.id = ?;
            """,
            (book_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def get_reading_history(book_id, limit=30):
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT sent_date, start_page, end_page, word_start, word_end
            FROM reading_history
            WHERE book_id = ?
            ORDER BY sent_date DESC, id DESC
            LIMIT ?;
            """,
            (book_id, limit),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def set_book_status(book_id, status):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE books SET status = ? WHERE id = ?;",
            (status, book_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_pages_per_day(book_id, pages_per_day):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE reading_progress
            SET pages_per_day = ?
            WHERE book_id = ?;
            """,
            (pages_per_day, book_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_book(book_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM books WHERE id = ?;", (book_id,))
        conn.commit()
    finally:
        conn.close()


def get_active_books():
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT
                books.id,
                books.title,
                books.author,
                books.file_path,
                books.file_type,
                books.total_pages,
                books.status,
                reading_progress.current_page,
                reading_progress.current_word_position,
                reading_progress.pages_per_day,
                reading_progress.last_sent_date
            FROM books
            JOIN reading_progress ON reading_progress.book_id = books.id
            WHERE books.status = 'active'
            ORDER BY books.id;
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


def reset_progress(book_id):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE reading_progress
            SET current_page = 0,
                current_word_position = 0,
                last_sent_date = NULL,
                completed_date = NULL
            WHERE book_id = ?;
            """,
            (book_id,),
        )
        conn.execute(
            "DELETE FROM reading_history WHERE book_id = ?;",
            (book_id,),
        )
        conn.execute(
            "UPDATE books SET status = 'active' WHERE id = ?;",
            (book_id,),
        )
        conn.commit()
    finally:
        conn.close()


def mark_book_completed(book_id, completed_date=None):
    completed_date = completed_date or date.today().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE books SET status = 'completed' WHERE id = ?;",
            (book_id,),
        )
        conn.execute(
            "UPDATE reading_progress SET completed_date = ? WHERE book_id = ?;",
            (completed_date, book_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_progress(book_id, current_page, current_word_position, last_sent_date, completed_date=None):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE reading_progress
            SET current_page = ?,
                current_word_position = ?,
                last_sent_date = ?,
                completed_date = ?
            WHERE book_id = ?;
            """,
            (
                current_page,
                current_word_position,
                last_sent_date,
                completed_date,
                book_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_history(book_id, sent_date, start_page, end_page, word_start, word_end):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO reading_history (
                book_id,
                sent_date,
                start_page,
                end_page,
                word_start,
                word_end
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (book_id, sent_date, start_page, end_page, word_start, word_end),
        )
        conn.commit()
    finally:
        conn.close()


def get_settings():
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT key, value FROM settings;")
        rows = cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}
    finally:
        conn.close()


def set_setting(key, value):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
