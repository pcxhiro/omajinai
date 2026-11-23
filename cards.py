#!/usr/bin/env python3
"""『15秒のおまじない』カード画像生成（ひとことポストと同一デザイン）。

1080x1920、背景は温かいクリーム色 #FAF6EE の紙質感、上部にタイトル枠。
- card1: カード1＝場面（黒文字、上半分）のみ
- card2: カード1 + カード2＝おまじない（濃い赤 #C0392B、下半分）
         + 1行あけて添え書き（同色・同サイズ）+ 右下に「応援中」ハンコ
"""
import glob
import random
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
CREAM = (250, 246, 238)       # #FAF6EE
BLACK = (30, 30, 30)
RED = (192, 57, 43)           # #C0392B
FRAME = (120, 100, 80)
TITLE_COLOR = (90, 70, 50)

MARGIN = 90
TEXT_W = W - MARGIN * 2


def _find_font(kind, bold=False):
    """kind: 'sans' | 'serif'。GitHub Actions (fonts-noto-cjk) と
    ローカル環境の両方で見つかるよう glob で探す。"""
    name = {"sans": "NotoSansCJK", "serif": "NotoSerifCJK"}[kind]
    weight = "Bold" if bold else "Regular"
    pats = [
        f"/usr/share/fonts/opentype/noto/{name}-{weight}.ttc",
        f"/usr/share/fonts/**/noto/{name}-{weight}.ttc",
        f"/usr/share/fonts/**/{name}-{weight}.ttc",
        f"/usr/share/fonts/**/{name}*.ttc",
    ]
    for pat in pats:
        hits = sorted(glob.glob(pat, recursive=True))
        if hits:
            return hits[0]
    raise FileNotFoundError(f"Japanese font not found: {name}-{weight}")


def _font(kind, size, bold=False):
    return ImageFont.truetype(_find_font(kind, bold), size)


def _wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=fnt) <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def _draw_block(draw, text, fnt, x, y, color, lh):
    for line in _wrap(draw, text, fnt, TEXT_W):
        draw.text((x, y), line, font=fnt, fill=color)
        y += lh
    return y


def _base_canvas():
    random.seed(42)
    img = Image.new("RGB", (W, H), CREAM)
    px = img.load()
    for _ in range(26000):  # 紙の質感（ごく薄いノイズ）
        x, y = random.randrange(W), random.randrange(H)
        d = random.randint(-7, 7)
        r, g, b = px[x, y]
        px[x, y] = (max(0, min(255, r + d)),
                    max(0, min(255, g + d)),
                    max(0, min(255, b + d)))
    d = ImageDraw.Draw(img)
    tw = 920
    d.rounded_rectangle([(W - tw) // 2, 70, (W + tw) // 2, 190],
                        radius=18, outline=FRAME, width=4)
    t = "15秒のおまじない"
    tf = _font("serif", 58, bold=True)
    twd = d.textlength(t, font=tf)
    d.text(((W - twd) / 2, 98), t, font=tf, fill=TITLE_COLOR)
    return img, d


def _stamp(d):
    sx, sy, ss = W - 320, H - 330, 210
    d.rectangle([sx, sy, sx + ss, sy + ss], outline=RED, width=10)
    sf = _font("serif", 62, bold=True)
    for i, ln in enumerate(["応援", "中"]):
        wd = d.textlength(ln, font=sf)
        d.text((sx + (ss - wd) / 2, sy + 28 + i * 78), ln, font=sf, fill=RED)


def make_cards(card1_text, card2_text, note_text, card1_path, card2_path):
    """card1_text=場面、card2_text=おまじない、note_text=添え書き。

    カード2は おまじない（『…』で始まる本文）を表示し、1行あけて
    添え書きを同じ色・同じ大きさで続ける（2026-11-22 の試作で確定した形）。
    添え書きは画面表示のみで、読み上げには含めない。
    """
    qf = _font("sans", 64, bold=True)
    af = _font("sans", 60, bold=True)

    img, d = _base_canvas()
    _draw_block(d, card1_text, qf, MARGIN, 330, BLACK, 100)
    img.save(card1_path)

    img, d = _base_canvas()
    _draw_block(d, card1_text, qf, MARGIN, 330, BLACK, 100)
    end_y = _draw_block(d, card2_text, af, MARGIN, 1010, RED, 96)
    _draw_block(d, note_text, af, MARGIN, end_y + 96, RED, 96)
    _stamp(d)
    img.save(card2_path)
