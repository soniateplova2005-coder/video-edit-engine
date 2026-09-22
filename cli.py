#!/usr/bin/env python3
import argparse
import sys

sys.path.insert(0, "src")
from engine import pipeline  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Auto-edit a video: reframe to 9:16, burn captions, color grade.")
    p.add_argument("input", help="Path to the source video")
    p.add_argument("output", help="Path to write the edited video")
    p.add_argument("--no-vertical", action="store_true", help="Skip 9:16 auto-reframe")
    p.add_argument("--no-captions", action="store_true", help="Skip auto-captions")
    p.add_argument("--no-grade", action="store_true", help="Skip color grading")
    p.add_argument("--whisper-model", default="small", help="tiny/base/small/medium/large")
    args = p.parse_args()

    pipeline.process(
        args.input, args.output,
        vertical=not args.no_vertical,
        burn_captions=not args.no_captions,
        grade=not args.no_grade,
        whisper_model=args.whisper_model,
    )
    print(f"Done -> {args.output}")


if __name__ == "__main__":
    main()
