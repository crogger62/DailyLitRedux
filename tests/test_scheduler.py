from scheduler import build_email


def test_build_email_subject_and_body():
    book = {"title": "Test Book", "author": "Author"}
    subject, plain, html = build_email(
        book=book,
        day=3,
        total_pages=10,
        content="Hello world.",
        start_page=3,
        end_page=3,
        percent=30,
    )
    assert "[DailyLit]" in subject
    assert "Test Book" in subject
    assert "Page 3 of 10 (30%)" in plain
    assert "Hello world." in plain
    assert "Hello world." in html
