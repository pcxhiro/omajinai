#!/usr/bin/env python3
"""FFmpeg でカード2枚＋音声2本を1本の縦型MP4に合成する（1本目と同一方式）。

タイムライン:
  0秒〜質問音声の終わり      : card1 + 質問音声
  質問の終わり〜最後         : card2 + 回答音声（最後に1秒の無音の余韻）
"""
import subprocess


def _duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        check=True, capture_output=True, text=True)
    return float(out.stdout.strip())


def compose(card1, card2, q_mp3, a_mp3, out_mp4):
    q = _duration(q_mp3)
    a = _duration(a_mp3)
    seg2 = a + 1.0          # 回答区間 + 余韻1秒
    total = q + a + 1.0
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-loop", "1", "-t", f"{q:.3f}", "-i", card1,
        "-loop", "1", "-t", f"{seg2:.3f}", "-i", card2,
        "-i", q_mp3, "-i", a_mp3,
        "-filter_complex",
        "[0:v][1:v]concat=n=2:v=1:a=0,fps=30,format=yuv420p[v];"
        "[2:a][3:a]concat=n=2:v=0:a=1,apad=pad_dur=1[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-t", f"{total:.3f}", out_mp4,
    ]
    subprocess.run(cmd, check=True)
    return total
