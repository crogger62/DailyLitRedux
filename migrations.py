import sqlite3

from config import Config


CURRENT_SCHEMA_VERSION = 1


def get_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_schema_version(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY
        );
        """
    )
    row = conn.execute("SELECT MAX(version) AS version FROM schema_migrations;").fetchone()
    return row["version"] if row and row["version"] is not None else 0


def apply_migration(conn, version, sql):
    conn.executescript(sql)
    conn.execute("INSERT INTO schema_migrations (version) VALUES (?);", (version,))


def migrate():
    conn = get_connection()
    try:
        version = get_schema_version(conn)
        if version < 1:
            apply_migration(
                conn,
                1,
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
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);
                CREATE INDEX IF NOT EXISTS idx_progress_book_id ON reading_progress(book_id);
                CREATE INDEX IF NOT EXISTS idx_history_book_date ON reading_history(book_id, sent_date);
                """,
            )

        if version < CURRENT_SCHEMA_VERSION:
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
