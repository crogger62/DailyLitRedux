# DailyLit Redux

Personal book delivery system that emails daily chunks of uploaded books.

## Requirements

- Python 3.13+
- Gmail App Password (for SMTP)

## Setup

1. Create a virtual environment (optional) and install dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Set environment variables (PowerShell example):

```powershell
$env:GMAIL_APP_PASSWORD="your_app_password"
$env:GMAIL_ADDRESS="crog62@gmail.com"
$env:SECRET_KEY="change-me"
```
Alternatively, create a `.env` file in the project root.

3. Run the app:

```bash
python app.py
```

The database is initialized automatically on first run.

## Windows Task Scheduler (Daily Email)

1. Open Task Scheduler.
2. Create Basic Task.
3. Name: `DailyLit Send`.
4. Trigger: Daily at `02:00`.
5. Action: Start a program.
   - Program/script: `python`
   - Add arguments: `scheduler.py`
   - Start in: `D:\Projects\DailyLitRedux`
6. Finish and optionally set "Run whether user is logged on or not".

## Tests

```bash
python -m pytest
```

## Notes

- Upload supports `.txt` and `.pdf` (PDF extraction is basic).
- Email sends to the configured Gmail address.
