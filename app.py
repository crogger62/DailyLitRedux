import math
import os
from email.message import EmailMessage
import smtplib

from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from config import Config
from db import (
    delete_book,
    get_book_detail,
    get_books_with_progress,
    get_reading_history,
    get_settings,
    init_db,
    insert_book,
    insert_progress,
    set_setting,
    set_book_status,
    update_pages_per_day,
)
from text_processing import count_words, extract_text
from scheduler import process_book


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db()

    @app.route("/")
    def index():
        books = get_books_with_progress()
        return render_template("index.html", books=books)

    @app.route("/upload")
    def upload():
        return render_template("upload.html")

    @app.route("/upload", methods=["POST"])
    def upload_post():
        upload_file = request.files.get("book_file")
        if not upload_file or not upload_file.filename:
            return render_template("upload.html", message="Please choose a file.")

        filename = secure_filename(upload_file.filename)
        file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if file_ext not in app.config["ALLOWED_EXTENSIONS"]:
            return render_template("upload.html", message="Unsupported file type.")

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        base_name = os.path.splitext(filename)[0]
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        counter = 1
        while os.path.exists(file_path):
            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                f"{base_name}-{counter}.{file_ext}",
            )
            counter += 1
        upload_file.save(file_path)

        try:
            text = extract_text(file_path, file_ext)
        except ValueError as exc:
            return render_template("upload.html", message=str(exc))

        total_words = count_words(text)
        total_pages = max(1, math.ceil(total_words / app.config["WORDS_PER_PAGE"]))

        title = request.form.get("title") or os.path.splitext(filename)[0]
        author = request.form.get("author") or None
        pages_per_day = request.form.get("pages_per_day")
        if not pages_per_day:
            settings_data = get_settings()
            pages_per_day = settings_data.get(
                "default_pages_per_day",
                app.config["DEFAULT_PAGES_PER_DAY"],
            )
        try:
            pages_per_day = max(1, int(pages_per_day))
        except ValueError:
            pages_per_day = app.config["DEFAULT_PAGES_PER_DAY"]

        book_id = insert_book(
            title=title,
            author=author,
            filename=os.path.basename(file_path),
            file_path=file_path,
            file_type=file_ext,
            total_words=total_words,
            total_pages=total_pages,
        )
        insert_progress(book_id, pages_per_day)

        return render_template(
            "upload.html",
            message="Upload complete.",
            details={
                "title": title,
                "author": author or "Unknown",
                "total_words": total_words,
                "total_pages": total_pages,
            },
        )

    @app.route("/settings")
    def settings():
        settings_data = get_settings()
        return render_template("settings.html", settings=settings_data)

    @app.route("/settings/default", methods=["POST"])
    def settings_default():
        value = request.form.get("default_pages_per_day", "").strip()
        try:
            value_int = max(1, int(value))
        except ValueError:
            flash("Default pages per day must be a positive number.", "error")
            return redirect(url_for("settings"))

        set_setting("default_pages_per_day", str(value_int))
        flash("Default pages per day updated.", "success")
        return redirect(url_for("settings"))

    @app.route("/settings/test", methods=["POST"])
    def settings_test_email():
        if not app.config["EMAIL_PASSWORD"]:
            flash("Missing GMAIL_APP_PASSWORD.", "error")
            return redirect(url_for("settings"))

        msg = EmailMessage()
        msg["Subject"] = "[DailyLit] Test Email"
        msg["From"] = app.config["EMAIL_ADDRESS"]
        msg["To"] = app.config["EMAIL_ADDRESS"]
        msg.set_content("This is a test email from DailyLit Redux.")

        try:
            with smtplib.SMTP(app.config["SMTP_SERVER"], app.config["SMTP_PORT"]) as smtp:
                smtp.starttls()
                smtp.login(app.config["EMAIL_ADDRESS"], app.config["EMAIL_PASSWORD"])
                smtp.send_message(msg)
            flash("Test email sent.", "success")
        except Exception as exc:
            flash(f"Test email failed: {exc}", "error")

        return redirect(url_for("settings"))

    @app.route("/book/<int:book_id>")
    def book_detail(book_id):
        book = get_book_detail(book_id)
        history = get_reading_history(book_id)
        return render_template(
            "book_detail.html",
            book=book,
            history=history,
        )

    @app.route("/book/<int:book_id>/status", methods=["POST"])
    def book_status(book_id):
        status = request.form.get("status", "").strip().lower()
        if status not in {"active", "paused", "completed"}:
            flash("Invalid status.", "error")
            return redirect(url_for("book_detail", book_id=book_id))
        set_book_status(book_id, status)
        flash("Status updated.", "success")
        return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/book/<int:book_id>/pages", methods=["POST"])
    def book_pages(book_id):
        pages = request.form.get("pages_per_day", "").strip()
        try:
            pages = max(1, int(pages))
        except ValueError:
            pages = None

        if not pages:
            flash("Pages per day must be a positive number.", "error")
            return redirect(url_for("book_detail", book_id=book_id))

        update_pages_per_day(book_id, pages)
        flash("Pages per day updated.", "success")
        return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/book/<int:book_id>/delete", methods=["POST"])
    def book_delete(book_id):
        book = get_book_detail(book_id)
        delete_book(book_id)
        if book and book["file_path"] and os.path.exists(book["file_path"]):
            try:
                os.remove(book["file_path"])
            except OSError:
                pass
        flash("Book deleted.", "success")
        return redirect(url_for("index"))

    @app.route("/book/<int:book_id>/send", methods=["POST"])
    def book_send_now(book_id):
        book = get_book_detail(book_id)
        if not book:
            flash("Book not found.", "error")
            return redirect(url_for("index"))

        ok, message = process_book(book)
        flash(message, "success" if ok else "error")
        return redirect(url_for("book_detail", book_id=book_id))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
