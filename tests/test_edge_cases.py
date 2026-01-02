from config import Config
from db import get_book_detail, insert_book, insert_progress, init_db, mark_book_completed
from text_processing import split_sentences


def test_split_sentences_with_quotes_and_lowercase():
    text = 'He said, "Wait." and left. next sentence starts lowercase.'
    sentences = split_sentences(text)
    assert len(sentences) == 2
    assert '"Wait."' in sentences[0]
    assert sentences[0].endswith(".")
    assert sentences[1].startswith("next")


def test_completed_date_is_set_when_marked_complete(tmp_path):
    original_db = Config.DATABASE_PATH
    try:
        Config.DATABASE_PATH = str(tmp_path / "test.db")
        init_db()
        book_id = insert_book(
            title="Done",
            author="Author",
            filename="done.txt",
            file_path="done.txt",
            file_type="txt",
            total_words=100,
            total_pages=1,
        )
        insert_progress(book_id, pages_per_day=1)

        mark_book_completed(book_id)
        detail = get_book_detail(book_id)
        assert detail["completed_date"] is not None
    finally:
        Config.DATABASE_PATH = original_db
