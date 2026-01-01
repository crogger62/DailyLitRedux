import re

from PyPDF2 import PdfReader

from config import Config

ABBREVIATIONS = {
    "mr.",
    "mrs.",
    "ms.",
    "dr.",
    "prof.",
    "sr.",
    "jr.",
    "st.",
    "vs.",
    "etc.",
}


def _protect_abbreviations(text):
    for abbr in ABBREVIATIONS:
        escaped = re.escape(abbr)
        text = re.sub(
            escaped,
            lambda match: match.group(0).replace(".", "<DOT>"),
            text,
            flags=re.IGNORECASE,
        )
    return text


def _restore_abbreviations(text):
    return text.replace("<DOT>", ".")


def split_sentences(text):
    protected = _protect_abbreviations(text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", protected)
    return [_restore_abbreviations(part.strip()) for part in parts if part.strip()]


def count_words(text):
    return len(re.findall(r"\b\w+\b", text))


def chunk_text(text, words_per_page=None):
    words_per_page = words_per_page or Config.WORDS_PER_PAGE
    sentences = split_sentences(text)
    chunks = []
    current = []
    current_words = 0

    for sentence in sentences:
        sentence_words = count_words(sentence)
        if current and current_words >= words_per_page:
            chunks.append(" ".join(current).strip())
            current = []
            current_words = 0

        if current and current_words + sentence_words > words_per_page:
            chunks.append(" ".join(current).strip())
            current = [sentence]
            current_words = sentence_words
            continue

        current.append(sentence)
        current_words += sentence_words

    if current:
        chunks.append(" ".join(current).strip())

    return chunks


def chunk_text_with_word_ranges(text, words_per_page=None):
    chunks = chunk_text(text, words_per_page)
    results = []
    word_pos = 0
    for chunk in chunks:
        chunk_words = count_words(chunk)
        start = word_pos + 1
        end = word_pos + chunk_words
        results.append((chunk, start, end))
        word_pos = end
    return results


def extract_text(file_path, file_type):
    if file_type == "txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    if file_type == "pdf":
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
        return "\n".join(pages)
    raise ValueError(f"Unsupported file type: {file_type}")
