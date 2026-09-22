"""Auto-reframe a horizontal video to 9:16 by tracking the main face.

v1 approach: sample face positions at a fixed rate, smooth them, collapse
into a small number of piecewise-constant crop segments (switches only when
the subject actually moves), then bake that into a single ffmpeg crop
expression driven by time. This avoids visible jitter without needing
per-frame keyframing.
"""
import os

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.core.base_options import BaseOptions

from . import utils

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "blaze_face_short_range.tflite")


def _make_detector():
    options = mp_vision.FaceDetectorOptions(
        base_options=BaseOptions(model_asset_path=os.path.normpath(_MODEL_PATH)),
        running_mode=mp_vision.RunningMode.VIDEO,
        min_detection_confidence=0.5,
    )
    return mp_vision.FaceDetector.create_from_options(options)


def sample_face_centers(video_path: str, sample_fps: float = 2.0) -> list[tuple[float, float]]:
    """Returns [(t_seconds, center_x_normalized_0_to_1), ...]."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_step = max(1, round(fps / sample_fps))

    centers = []
    frame_idx = 0
    detector = _make_detector()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % frame_step == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                t = frame_idx / fps
                result = detector.detect_for_video(mp_image, int(t * 1000))
                if result.detections:
                    best = max(result.detections, key=lambda d: d.categories[0].score if d.categories else 0.0)
                    box = best.bounding_box
                    cx = (box.origin_x + box.width / 2) / frame.shape[1]
                    centers.append((t, cx))
                elif centers:
                    centers.append((t, centers[-1][1]))
                else:
                    centers.append((t, 0.5))
            frame_idx += 1
    finally:
        detector.close()
        cap.release()
    return centers


def smooth_centers(centers: list[tuple[float, float]], alpha: float = 0.15) -> list[tuple[float, float]]:
    if not centers:
        return centers
    smoothed = [centers[0]]
    prev = centers[0][1]
    for t, cx in centers[1:]:
        prev = alpha * cx + (1 - alpha) * prev
        smoothed.append((t, prev))
    return smoothed


def collapse_to_segments(centers: list[tuple[float, float]], move_threshold: float = 0.06) -> list[tuple[float, float]]:
    """Merges consecutive samples into (t_start, center_x) segments,
    starting a new segment only when the center drifts past the threshold."""
    if not centers:
        return [(0.0, 0.5)]
    segments = [(centers[0][0], centers[0][1])]
    for t, cx in centers[1:]:
        _, last_cx = segments[-1]
        if abs(cx - last_cx) > move_threshold:
            segments.append((t, cx))
    return segments


def build_crop_expr(segments: list[tuple[float, float]], src_w: int, crop_w: int) -> str:
    """Builds a nested ffmpeg if() expression for the crop x offset in pixels,
    keeping the tracked center inside the crop window and the window inside frame."""
    def x_for(cx_norm: float) -> int:
        x = int(cx_norm * src_w - crop_w / 2)
        return max(0, min(src_w - crop_w, x))

    expr = str(x_for(segments[-1][1]))
    for t_start, cx in reversed(segments[:-1]):
        expr = f"if(lt(t,{t_start:.3f}),{x_for(cx)},{expr})"
    return expr


def reframe_to_vertical(video_in: str, video_out: str, out_w: int = 1080, out_h: int = 1920,
                         sample_fps: float = 2.0):
    info = utils.probe(video_in)
    vstream = utils.video_stream(info)
    src_w, src_h = int(vstream["width"]), int(vstream["height"])

    crop_w = round(src_h * out_w / out_h)
    crop_w = min(crop_w, src_w)

    centers = sample_face_centers(video_in, sample_fps=sample_fps)
    centers = smooth_centers(centers)
    segments = collapse_to_segments(centers)
    x_expr = build_crop_expr(segments, src_w, crop_w)

    vf = f"crop={crop_w}:{src_h}:{x_expr}:0,scale={out_w}:{out_h}"
    utils.run_ffmpeg(["-i", video_in, "-vf", vf, "-c:a", "copy", video_out])
