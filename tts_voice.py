#!/usr/bin/env python3
"""音声合成。

本命: Edge-TTS（質問=ja-JP-NanamiNeural の若い声、
      回答=ja-JP-KeitaNeural の落ち着いた男性声、少しゆっくり）
予備: Edge-TTS が失敗したら gTTS で生成し、FFmpeg の rubberband で
      1本目と同じ調整（質問は速度1.15倍、回答はピッチ0.85倍＋速度1.25倍
      ＋フォルマント保持＝落ち着いた男性声に寄せる）を行う。
"""
import asyncio
import subprocess

# 読み替え辞書（2026-11-18 追加）:
# 音声合成が漢字の読みを外した語を、音声に渡す直前にひらがなへ差し替える。
# 画面のカードは漢字のまま（cards.py は元の文を使う）。読み違いが
# 見つかったらここに1行足す。
READING_FIXES = {
    "低電力": "ていでんりょく",
}


def _fix_reading(text):
    for word, reading in READING_FIXES.items():
        text = text.replace(word, reading)
    return text


async def _edge_tts(text, voice, out, rate=None):
    import edge_tts
    kwargs = {"text": text, "voice": voice}
    if rate:
        kwargs["rate"] = rate
    await edge_tts.Communicate(**kwargs).save(out)


def _edge(question, answer, q_path, a_path):
    asyncio.run(_edge_tts(question, "ja-JP-NanamiNeural", q_path))
    asyncio.run(_edge_tts(answer, "ja-JP-KeitaNeural", a_path, rate="-5%"))


def _ffmpeg(args):
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + args, check=True)


def _gtts_fallback(question, answer, q_path, a_path):
    from gtts import gTTS
    q_raw, a_raw = q_path + ".raw.mp3", a_path + ".raw.mp3"
    gTTS(question, lang="ja").save(q_raw)
    gTTS(answer, lang="ja").save(a_raw)
    _ffmpeg(["-i", q_raw, "-af", "rubberband=tempo=1.15", q_path])
    _ffmpeg(["-i", a_raw, "-af",
             "rubberband=pitch=0.85:tempo=1.25:formant=preserved", a_path])


def synthesize(question, answer, q_path, a_path):
    """(question mp3, answer mp3) を作る。使用した方式名を返す。"""
    question = _fix_reading(question)
    answer = _fix_reading(answer)
    try:
        _edge(question, answer, q_path, a_path)
        return "edge-tts"
    except Exception as e:  # ネットワーク不通など。予備方式へ。
        print(f"[tts] edge-tts failed ({e}); falling back to gTTS")
        _gtts_fallback(question, answer, q_path, a_path)
        return "gtts+rubberband"
