import os
from datetime import time

from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    # Database
    DATABASE_PATH = os.path.join("data", "books.db")

    # File Storage
    UPLOAD_FOLDER = os.path.join("data", "uploads")
    ALLOWED_EXTENSIONS = {"txt", "pdf"}
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

    # Email
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "crog62@gmail.com")
    EMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

    # Chunking
    WORDS_PER_PAGE = 400

    # Scheduling
    SEND_TIME = time(2, 0)  # 2:00 AM

    # Defaults
    DEFAULT_PAGES_PER_DAY = 1
