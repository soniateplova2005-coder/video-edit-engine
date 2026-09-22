"""Beat detection (for cutting on-rhythm) and scene-change detection."""
import librosa
from scenedetect import ContentDetector, SceneManager, open_video


def detect_beats(audio_path: str) -> list[float]:
    """Returns beat timestamps in seconds."""
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    return librosa.frames_to_time(beat_frames, sr=sr).tolist()


def detect_scenes(video_path: str, threshold: float = 27.0) -> list[tuple[float, float]]:
    """Returns [(start_seconds, end_seconds), ...] for each detected shot."""
    video = open_video(video_path)
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video)
    scenes = manager.get_scene_list()
    return [(s.get_seconds(), e.get_seconds()) for s, e in scenes]


def snap_to_nearest_beat(timestamp: float, beats: list[float]) -> float:
    if not beats:
        return timestamp
    return min(beats, key=lambda b: abs(b - timestamp))


def snap_cuts_to_beats(cut_points: list[float], beats: list[float]) -> list[float]:
    return [snap_to_nearest_beat(c, beats) for c in cut_points]
