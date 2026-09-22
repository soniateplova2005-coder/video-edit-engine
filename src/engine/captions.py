"""Speech-to-text and burned-in animated captions (Reels-style, word-by-word)."""
import whisper

from . import utils

_model_cache: dict[str, whisper.Whisper] = {}


def _get_model(name: str = "small"):
    if name not in _model_cache:
        _model_cache[name] = whisper.load_model(name)
    return _model_cache[name]


def transcribe_words(audio_path: str, model_size: str = "small", language: str | None = None) -> list[dict]:
    """Returns a flat list of {word, start, end} across the whole file."""
    model = _get_model(model_size)
    result = model.transcribe(audio_path, word_timestamps=True, language=language)
    words = []
    for segment in result["segments"]:
        for w in segment.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": w["start"],
                "end": w["end"],
            })
    return words


def _fmt_ass_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(words: list[dict], out_path: str, video_w: int, video_h: int,
              font_size: int | None = None, group_size: int = 4,
              highlight_color: str = "&H00D7FF&", base_color: str = "&HFFFFFF&"):
    """Groups words into short on-screen chunks and highlights the active word,
    mimicking the word-pop caption style common in Reels/TikTok."""
    font_size = font_size or int(video_h * 0.055)
    margin_v = int(video_h * 0.18)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat ExtraBold,{font_size},{base_color},{base_color},&H00000000&,&H80000000&,-1,0,0,0,100,100,0,0,1,3,0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = []
    for i in range(0, len(words), group_size):
        chunk = words[i:i + group_size]
        if not chunk:
            continue
        chunk_start = chunk[0]["start"]
        chunk_end = chunk[-1]["end"]
        for active_idx, active in enumerate(chunk):
            seg_start = active["start"]
            seg_end = active["end"]
            parts = []
            for j, w in enumerate(chunk):
                color = highlight_color if j == active_idx else base_color
                parts.append(f"{{\\c{color}}}{w['word']}")
            text = " ".join(parts)
            lines.append(
                f"Dialogue: 0,{_fmt_ass_time(seg_start)},{_fmt_ass_time(seg_end)},Default,,0,0,0,,{text}"
            )
        # hold the last word's highlight until the chunk visually ends
        if chunk_end > chunk[-1]["end"]:
            lines.append(
                f"Dialogue: 0,{_fmt_ass_time(chunk[-1]['end'])},{_fmt_ass_time(chunk_end)},Default,,0,0,0,,"
                + " ".join(f"{{\\c{base_color}}}{w['word']}" for w in chunk)
            )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")


def burn_captions(video_in: str, ass_path: str, video_out: str):
    utils.run_ffmpeg([
        "-i", video_in,
        "-vf", f"ass={ass_path}",
        "-c:a", "copy",
        video_out,
    ])
