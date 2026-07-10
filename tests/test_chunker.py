import pytest
from study_mcp.core import chunker


def test_short_text_stays_one_chunk() -> None:
    text = 'A short paragraph that is long enough to survive the filter.'
    chunks, discarded = chunker.chunk_text(text)
    assert chunks == [text]
    assert discarded == 0


def test_splits_by_heading() -> None:
    text = (
        '# Heading One\n\n'
        'This paragraph belongs to the first heading and is long enough.\n\n'
        '# Heading Two\n\n'
        'This paragraph belongs to the second heading and is long enough.'
    )
    chunks, discarded = chunker.chunk_text(text)
    assert discarded == 0
    assert any(c.startswith('# Heading One') for c in chunks)
    assert any(c.startswith('# Heading Two') for c in chunks)


def test_giant_paragraph_splits_into_multiple_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(chunker.settings, 'CHUNK_SIZE', 120)
    monkeypatch.setattr(chunker.settings, 'CHUNK_OVERLAP', 30)

    paragraph = (
        'This is sentence one, it is fairly short. '
        'This is sentence two, also fairly short here. '
        'This is sentence three, a bit longer than the others maybe. '
        'This is sentence four, wrapping up the paragraph nicely now. '
        'This is sentence five for good measure and more length.'
    )
    chunks, discarded = chunker.chunk_text(paragraph)
    assert len(chunks) > 1
    assert discarded == 0


def test_never_cuts_mid_word(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunker.settings, 'CHUNK_SIZE', 60)
    monkeypatch.setattr(chunker.settings, 'CHUNK_OVERLAP', 15)

    paragraph = (
        'Supercalifragilisticexpialidocious words never get split. '
        'Neither do ordinary words in the middle of a sentence here. '
        'One more sentence to make sure splitting actually happens now.'
    )
    original_words = set(paragraph.replace('.', '').split())
    chunks, _ = chunker.chunk_text(paragraph)

    chunk_words: set[str] = set()
    for chunk in chunks:
        chunk_words.update(chunk.replace('.', '').split())

    assert chunk_words.issubset(original_words)


def test_consecutive_chunks_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunker.settings, 'CHUNK_SIZE', 120)
    monkeypatch.setattr(chunker.settings, 'CHUNK_OVERLAP', 40)

    paragraph = (
        'This is sentence one, it is fairly short. '
        'This is sentence two, also fairly short here. '
        'This is sentence three, a bit longer than the others maybe. '
        'This is sentence four, wrapping up the paragraph nicely now.'
    )
    chunks, _ = chunker.chunk_text(paragraph)
    assert len(chunks) >= 2
    # the second sentence should appear at the tail of chunk 0 and the
    # head of chunk 1 - proof the overlap carried a whole sentence over
    assert 'sentence two' in chunks[0]
    assert 'sentence two' in chunks[1]


def test_short_chunks_are_discarded_and_counted() -> None:
    text = (
        '# H\n\nHi\n\n# H2\n\nThis one is definitely long enough to survive.'
    )
    chunks, discarded = chunker.chunk_text(text)
    assert discarded == 1
    assert len(chunks) == 1
    assert chunks[0].startswith('# H2')
