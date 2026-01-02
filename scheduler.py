import os
import time as time_module
from datetime import date, datetime
from email.message import EmailMessage
import smtplib

from config import Config
from db import get_active_books, get_settings, insert_history, set_book_status, update_progress
from text_processing import chunk_text_with_word_ranges, extract_text


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "logs", "email_log.txt")
DEBUG = os.getenv("DAILYLIT_DEBUG", "0").strip() == "1"


def log_message(message):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def build_email(book, day, total_pages, content, start_page, end_page, percent):
    subject = f"[DailyLit] {book['title']} - Day {day} of ~{total_pages}"
    plain = (
        f"Book: {book['title']}\n"
        f"Author: {book['author'] or 'Unknown'}\n"
        f"Progress: Page {end_page} of {total_pages} ({percent}%)\n\n"
        f"{content}\n\n"
        f"Tomorrow: Page {end_page + 1 if end_page < total_pages else end_page}\n"
    )
    html = f"""
    <html>
      <body>
        <p><strong>Book:</strong> {book['title']}<br/>
        <strong>Author:</strong> {book['author'] or 'Unknown'}<br/>
        <strong>Progress:</strong> Page {end_page} of {total_pages} ({percent}%)</p>
        <hr/>
        <p>{content.replace('\n', '<br/>')}</p>
        <hr/>
        <p>Tomorrow: Page {end_page + 1 if end_page < total_pages else end_page}</p>
      </body>
    </html>
    """.strip()
    return subject, plain, html


def send_email(subject, plain, html, recipient):
    if not Config.EMAIL_PASSWORD:
        raise RuntimeError("Missing GMAIL_APP_PASSWORD.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = Config.EMAIL_ADDRESS
    msg["To"] = recipient
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    if DEBUG:
        log_message(f"SMTP connect {Config.SMTP_SERVER}:{Config.SMTP_PORT} as {Config.EMAIL_ADDRESS}")
    with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as smtp:
        smtp.starttls()
        if DEBUG:
            log_message("SMTP STARTTLS ok")
        smtp.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
        if DEBUG:
            log_message(f"SMTP login ok, sending to {recipient}")
        smtp.send_message(msg)


def process_book(book, force=False):
    settings = get_settings()
    recipient = settings.get("email_address") or Config.EMAIL_ADDRESS
    today = date.today().isoformat()
    file_path = book["file_path"]
    if not os.path.isabs(file_path):
        file_path = os.path.join(BASE_DIR, file_path)
    if DEBUG:
        log_message(
            f"Book {book['id']} status={book['status']} current_page={book['current_page']} "
            f"pages_per_day={book['pages_per_day']} last_sent={book['last_sent_date']} recipient={recipient} "
            f"cwd={os.getcwd()}"
        )
    if book["status"] != "active":
        return False, "Book is not active."
    if book["last_sent_date"] == today and not force:
        if DEBUG:
            log_message(f"Book {book['id']} skipped (already sent today).")
        return False, "Already sent today."

    try:
        if not os.path.exists(file_path):
            log_message(f"Book {book['id']} missing file: {file_path}")
            return False, "Book file not found."
        if DEBUG:
            log_message(f"Book {book['id']} loading {file_path}")
        text = extract_text(file_path, book["file_type"])
        chunks = chunk_text_with_word_ranges(text, Config.WORDS_PER_PAGE)
    except Exception as exc:
        log_message(f"Book {book['id']} failed to load: {exc}")
        if DEBUG:
            return False, f"Failed to read book content: {exc}"
        return False, "Failed to read book content."

    if not chunks:
        log_message(f"Book {book['id']} has no content.")
        return False, "No content to send."

    start_page = book["current_page"] + 1
    if start_page > book["total_pages"]:
        set_book_status(book["id"], "completed")
        update_progress(book["id"], book["current_page"], book["current_word_position"], today, today)
        log_message(f"Book {book['id']} marked completed (already finished).")
        return True, "Book already completed."

    end_page = min(book["current_page"] + book["pages_per_day"], book["total_pages"])
    selection = chunks[book["current_page"] : end_page]
    if not selection:
        log_message(f"Book {book['id']} has no chunk selection.")
        return False, "Unable to select next chunk."

    content = "\n\n".join(chunk for chunk, _, _ in selection)
    word_start = selection[0][1]
    word_end = selection[-1][2]
    percent = round((end_page / book["total_pages"]) * 100)
    if DEBUG:
        log_message(
            f"Book {book['id']} sending pages {start_page}-{end_page} "
            f"words {word_start}-{word_end} ({percent}%)"
        )
    subject, plain, html = build_email(
        book,
        day=end_page,
        total_pages=book["total_pages"],
        content=content,
        start_page=start_page,
        end_page=end_page,
        percent=percent,
    )

    success = False
    last_error = None
    for _ in range(3):
        try:
            send_email(subject, plain, html, recipient)
            success = True
            break
        except Exception as exc:
            last_error = exc
            if DEBUG:
                log_message(f"Book {book['id']} send attempt failed: {exc}")
            time_module.sleep(300)

    if not success:
        log_message(f"Book {book['id']} email failed: {last_error}")
        return False, "Email send failed."

    completed_date = today if end_page >= book["total_pages"] else None
    update_progress(book["id"], end_page, word_end, today, completed_date)
    insert_history(book["id"], today, start_page, end_page, word_start, word_end)
    if completed_date:
        set_book_status(book["id"], "completed")
    log_message(f"Book {book['id']} sent pages {start_page}-{end_page}.")
    return True, f"Sent pages {start_page}-{end_page}."


def process_books():
    books = get_active_books()
    if DEBUG:
        log_message(f"Processing {len(books)} active book(s).")
    for book in books:
        process_book(book)


if __name__ == "__main__":
    if DEBUG:
        log_message("Scheduler run started.")
    process_books()
    if DEBUG:
        log_message("Scheduler run finished.")
