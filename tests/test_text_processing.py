from text_processing import count_words, split_sentences, chunk_text


def test_count_words_basic():
    text = "Hello world! This is a test."
    assert count_words(text) == 6


def test_split_sentences_handles_abbreviations():
    text = "Mr. Smith went home. He slept."
    sentences = split_sentences(text)
    assert sentences == ["Mr. Smith went home.", "He slept."]


def test_chunk_text_respects_sentence_boundaries():
    text = "One. Two. Three. Four. Five."
    chunks = chunk_text(text, words_per_page=2)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.endswith((".", "!", "?"))
