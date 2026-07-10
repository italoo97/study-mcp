from study_mcp.core.transcript import extract_start_time, parse_transcript

SRT_SAMPLE = """1
00:00:01,000 --> 00:00:04,000
Hello there, welcome to the video.

2
00:00:04,500 --> 00:00:08,000
Today we're going to talk about Python.

3
00:00:15,000 --> 00:00:18,000
That was a long pause, new paragraph now.
"""

VTT_SAMPLE = """WEBVTT

00:00:01.000 --> 00:00:04.000
<c.colorFFFFFF>Hello</c> there, welcome.

00:00:04.500 --> 00:00:08.000
Today: Python basics.
"""


def test_parses_srt_into_paragraphs() -> None:
    result = parse_transcript(SRT_SAMPLE)
    paragraphs = result.split('\n\n')
    assert len(paragraphs) == 2
    assert 'Hello there, welcome to the video.' in paragraphs[0]
    assert "Today we're going to talk about Python." in paragraphs[0]
    assert 'That was a long pause' in paragraphs[1]


def test_srt_strips_index_numbers_and_timestamps() -> None:
    result = parse_transcript(SRT_SAMPLE)
    assert '00:00:01,000' not in result
    assert '-->' not in result
    for line in result.splitlines():
        assert line.strip() != '1'
        assert line.strip() != '2'


def test_srt_groups_by_pause_over_two_seconds() -> None:
    result = parse_transcript(SRT_SAMPLE)
    paragraphs = result.split('\n\n')
    # cue 2 ends at 8s, cue 3 starts at 15s -> 7s pause -> new paragraph
    assert len(paragraphs) == 2


def test_parses_vtt_and_strips_webvtt_header_and_tags() -> None:
    result = parse_transcript(VTT_SAMPLE)
    assert 'WEBVTT' not in result
    assert '<c.colorFFFFFF>' not in result
    assert '</c>' not in result
    assert 'Hello there, welcome.' in result
    assert 'Today: Python basics.' in result


def test_paragraphs_prefixed_with_start_time_marker() -> None:
    result = parse_transcript(SRT_SAMPLE)
    assert result.startswith('[00:01]')
    assert '[00:15]' in result


def test_empty_input_returns_empty_string() -> None:
    assert not parse_transcript('')


def test_extract_start_time_mm_ss() -> None:
    assert extract_start_time('[02:15] some text here') == 135.0


def test_extract_start_time_hh_mm_ss() -> None:
    assert extract_start_time('[01:02:15] some text here') == 3735.0


def test_extract_start_time_no_marker_returns_none() -> None:
    assert extract_start_time('just plain text, no marker') is None
