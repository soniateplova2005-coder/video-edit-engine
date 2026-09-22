"""Ties the technical steps together: reframe -> captions -> color grade.

Cutting/trimming and picking the best takes is editorial judgment, not a
mechanical step, so it's not automated here. `beatsync.py` exposes the raw
beat/scene detection to inform those decisions per video instead.
"""
import os
import shutil
import tempfile

from . import captions, colorgrade, reframe, utils


def process(input_path: str, output_path: str, *, vertical: bool = True,
            burn_captions: bool = True, grade: bool = True,
            whisper_model: str = "small") -> str:
    with tempfile.TemporaryDirectory() as work:
        current = input_path

        if vertical:
            step_out = os.path.join(work, "01_reframed.mp4")
            reframe.reframe_to_vertical(current, step_out)
            current = step_out

        if burn_captions:
            audio_path = os.path.join(work, "audio.wav")
            utils.run_ffmpeg(["-i", current, "-vn", "-ac", "1", "-ar", "16000", audio_path])
            words = captions.transcribe_words(audio_path, model_size=whisper_model)

            info = utils.probe(current)
            vstream = utils.video_stream(info)
            ass_path = os.path.join(work, "captions.ass")
            captions.build_ass(words, ass_path, int(vstream["width"]), int(vstream["height"]))

            step_out = os.path.join(work, "02_captioned.mp4")
            captions.burn_captions(current, ass_path, step_out)
            current = step_out

        if grade:
            step_out = os.path.join(work, "03_graded.mp4")
            colorgrade.apply_color_grade(current, step_out)
            current = step_out

        shutil.copy(current, output_path)

    return output_path
