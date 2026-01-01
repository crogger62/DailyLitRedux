import math
import os
import tempfile

import scheduler
from config import Config
from db import (
    get_book_detail,
    get_reading_history,
    get_active_books,
    init_db,
    insert_book,
    insert_progress,
)
from text_processing import count_words


def test_upload_send_updates_progress():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        uploads_dir = os.path.join(tmp_dir, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        Config.DATABASE_PATH = db_path
        Config.UPLOAD_FOLDER = uploads_dir

        init_db()

        content = "Hello world. This is a test sentence."
        file_path = os.path.join(uploads_dir, "sample.txt")
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(content)

        total_words = count_words(content)
        total_pages = max(1, math.ceil(total_words / Config.WORDS_PER_PAGE))
        book_id = insert_book(
            title="Sample",
            author="Author",
            filename="sample.txt",
            file_path=file_path,
            file_type="txt",
            total_words=total_words,
            total_pages=total_pages,
        )
        insert_progress(book_id, pages_per_day=1)

        books = get_active_books()
        assert len(books) == 1

        original_send_email = scheduler.send_email
        scheduler.send_email = lambda *args, **kwargs: None
        try:
            ok, _ = scheduler.process_book(books[0], force=True)
        finally:
            scheduler.send_email = original_send_email

        assert ok
        detail = get_book_detail(book_id)
        assert detail["current_page"] == 1
        assert detail["last_sent_date"] is not None

        history = get_reading_history(book_id)
        assert len(history) == 1
