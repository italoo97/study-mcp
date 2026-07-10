import re

_TIME_RE = re.compile(r'(?:(\d{2}):)?(\d{2}):(\d{2})[.,](\d{3})')
_TAG_RE = re.compile(r'<[^>]+>')
_INDEX_RE = re.compile(r'^\d+$')

MAX_LINES_PER_PARAGRAPH = 8
MAX_PAUSE_SECONDS = 2.0


def _parse_timestamp(raw: str) -> float:
    match = _TIME_RE.match(raw.strip())
    if not match:
        return 0.0
    hours, minutes, seconds, millis = match.groups()
    hours_i = int(hours) if hours else 0
    return (
        hours_i * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000
    )


def _format_timestamp(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    return f'{minutes:02d}:{secs:02d}'


def _parse_cues(raw: str) -> list[tuple[float, float, str]]:
    """Parse SRT/VTT cue blocks into (start, end, text) tuples."""
    blocks = re.split(r'\n\s*\n', raw.strip())
    cues: list[tuple[float, float, str]] = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or lines[0] == 'WEBVTT':
            continue
        if _INDEX_RE.match(lines[0]):
            lines = lines[1:]
        if not lines or '-->' not in lines[0]:
            continue

        start_raw, end_raw = lines[0].split('-->')
        start = _parse_timestamp(start_raw)
        end = _parse_timestamp(end_raw.split()[0])
        text = ' '.join(_TAG_RE.sub('', line) for line in lines[1:])
        if text.strip():
            cues.append((start, end, text.strip()))

    return cues


def parse_transcript(raw: str) -> str:
    """
    Convert SRT/VTT captions into coherent paragraphs of plain text.

    Groups consecutive cues into a paragraph until a pause longer than
    MAX_PAUSE_SECONDS or MAX_LINES_PER_PARAGRAPH cues is reached.
    """
    cues = _parse_cues(raw)
    if not cues:
        return ''

    paragraphs: list[str] = []
    current_lines: list[str] = []
    paragraph_start = cues[0][0]
    prev_end = cues[0][0]

    for start, end, text in cues:
        pause = start - prev_end
        if current_lines and (
            pause > MAX_PAUSE_SECONDS
            or len(current_lines) >= MAX_LINES_PER_PARAGRAPH
        ):
            paragraphs.append(
                f'[{_format_timestamp(paragraph_start)}] '
                + ' '.join(current_lines)
            )
            current_lines = []
            paragraph_start = start

        current_lines.append(text)
        prev_end = end

    if current_lines:
        paragraphs.append(
            f'[{_format_timestamp(paragraph_start)}] '
            + ' '.join(current_lines)
        )

    return '\n\n'.join(paragraphs)


_LEADING_TIMESTAMP_RE = re.compile(r'^\[(\d{2}):(\d{2})(?::(\d{2}))?\]')


def extract_start_time(chunk: str) -> float | None:
    """Parse a leading '[mm:ss]' or '[hh:mm:ss]' marker into seconds.

    Only chunks that begin exactly at a parsed paragraph boundary carry
    the marker (see parse_transcript) - chunks split further by
    chunk_text's sentence-grouping (when a paragraph exceeds
    CHUNK_SIZE) won't have one, and this returns None for those.
    """
    match = _LEADING_TIMESTAMP_RE.match(chunk)
    if not match:
        return None
    first, second, third = match.groups()
    if third is not None:
        hours, minutes, seconds = int(first), int(second), int(third)
    else:
        hours, minutes, seconds = 0, int(first), int(second)
    return float(hours * 3600 + minutes * 60 + seconds)
