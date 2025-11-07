#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Combine a sequence of PNG frames into an MP4 using ffmpeg.

Default assumptions (match your tree):
  - Run this script from postProcess/
  - Input frames are in ./frames_png/
  - Filenames look like: frame-00000.png, frame-00001.png, ...
  - Output MP4 will be ./dropfilm.mp4

If your names/folder differ, use CLI options (see -h).
"""

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

def infer_padding_and_prefix(files):
    """
    From a list of filenames like 'frame-00042.png',
    infer prefix='frame-' and pad=5.
    """
    # find the first file matching number pattern
    r = re.compile(r"^(.*?)(\d+)\.png$", re.IGNORECASE)
    for f in sorted(files):
        m = r.match(f.name)
        if m:
            prefix = m.group(1)
            pad = len(m.group(2))
            return prefix, pad
    raise RuntimeError("Cannot infer prefix/padding from filenames. "
                       "Please specify --prefix/--pad manually.")

def main():
    p = argparse.ArgumentParser(
        description="Make an MP4 from PNG frames with ffmpeg.")
    p.add_argument("--indir", default="frames_png",
                   help="Input directory containing PNGs (default: frames_png)")
    p.add_argument("--out", default="dropfilm.mp4",
                   help="Output MP4 path (default: dropfilm.mp4)")
    p.add_argument("--prefix", default=None,
                   help="Filename prefix (e.g., 'frame-'). If omitted, auto-detect.")
    p.add_argument("--pad", type=int, default=None,
                   help="Zero padding width (e.g., 5 for 00042). If omitted, auto-detect.")
    p.add_argument("--fps", type=int, default=30,
                   help="Input framerate (default: 30)")
    p.add_argument("--crf", type=int, default=18,
                   help="x264 quality: lower=better/bigger (default: 18)")
    p.add_argument("--preset", default="medium",
                   choices=["ultrafast","superfast","veryfast","faster","fast",
                            "medium","slow","slower","veryslow"],
                   help="x264 speed/size tradeoff (default: medium)")
    args = p.parse_args()

    indir = Path(args.indir)
    out_path = Path(args.out)

    if not indir.is_dir():
        raise SystemExit(f"[ERROR] Input folder not found: {indir}")

    # collect png files
    pngs = sorted([f for f in indir.iterdir() if f.suffix.lower()==".png"])
    if not pngs:
        raise SystemExit(f"[ERROR] No PNG files found in: {indir}")

    # check ffmpeg
    if shutil.which("ffmpeg") is None:
        raise SystemExit("[ERROR] ffmpeg not found. Install it: sudo apt-get update && sudo apt-get install -y ffmpeg")

    # infer prefix / padding if not provided
    if args.prefix is None or args.pad is None:
        prefix, pad = infer_padding_and_prefix(pngs)
    else:
        prefix, pad = args.prefix, args.pad

    # ensure numbers are contiguous from some start (ffmpeg is ok as long as the sequence is continuous)
    # We just warn if gaps are detected; ffmpeg will stop at first missing number.
    num_re = re.compile(rf"^{re.escape(prefix)}(\d+)\.png$", re.IGNORECASE)
    nums = []
    for f in pngs:
        m = num_re.match(f.name)
        if m:
            nums.append(int(m.group(1)))
    nums.sort()
    if len(nums) >= 2:
        gaps = [b for a,b in zip(nums, nums[1:]) if b != a+1]
        if gaps:
            print("[WARN] Detected gaps in numbering; ffmpeg will stop at first missing frame.")

    pattern = f"{prefix}%0{pad}d.png"
    input_pattern = str(indir / pattern)

    # build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",                       # overwrite
        "-framerate", str(args.fps),
        "-i", input_pattern,        # pattern input
        "-c:v", "libx264",
        "-preset", args.preset,
        "-crf", str(args.crf),
        "-pix_fmt", "yuv420p",      # widest player compatibility
        str(out_path)
    ]

    print("[INFO] Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"[ERROR] ffmpeg failed with code {e.returncode}")

    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"[OK] Video written to {out_path.resolve()}")
    else:
        raise SystemExit("[ERROR] Output MP4 not created or empty.")

if __name__ == "__main__":
    main()
