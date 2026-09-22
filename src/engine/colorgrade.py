"""Basic color grading and crossfade transitions."""
from . import utils

# A punchy, slightly warm look that reads well on phone screens — a
# reasonable default until we tune presets against real reference footage.
DEFAULT_EQ = "eq=contrast=1.08:saturation=1.15:brightness=0.01"


def apply_color_grade(video_in: str, video_out: str, eq: str = DEFAULT_EQ):
    utils.run_ffmpeg(["-i", video_in, "-vf", eq, "-c:a", "copy", video_out])


def concat_with_crossfade(clip_paths: list[str], durations: list[float], video_out: str,
                           transition: str = "fade", transition_dur: float = 0.35):
    """Concatenates clips with an xfade transition between each consecutive pair.
    `durations` must be each clip's length in seconds (needed to place the xfade offset)."""
    if len(clip_paths) == 1:
        utils.run_ffmpeg(["-i", clip_paths[0], "-c", "copy", video_out])
        return

    inputs = []
    for p in clip_paths:
        inputs += ["-i", p]

    filter_parts = []
    prev_label = "0:v"
    running_offset = durations[0] - transition_dur
    for i in range(1, len(clip_paths)):
        out_label = f"v{i}"
        filter_parts.append(
            f"[{prev_label}][{i}:v]xfade=transition={transition}:duration={transition_dur}:offset={running_offset:.3f}[{out_label}]"
        )
        prev_label = out_label
        if i < len(clip_paths) - 1:
            running_offset += durations[i] - transition_dur

    filter_complex = ";".join(filter_parts)
    utils.run_ffmpeg([
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{prev_label}]",
        video_out,
    ])
