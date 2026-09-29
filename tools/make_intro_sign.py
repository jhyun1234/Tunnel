"""UI-2d 인트로 간판 그림 → Assets/UI/intro_sign.png (제안서 docs/제안서_UI2d_인트로_간판.md).

흰 함석 판(누런 흰색 · 얼룩 · 테두리 선 · 모서리 녹 · 못 구멍 넷) 위에 배민 을지로체로
"귀령광업소"(검정)와 "막장"(빨강). 빛은 굽지 않는다 — 인트로 씬의 머리 램프가 비춘다.
색은 1980년대 탄광 표지 사진(build/refs/intro/korea/01·07)에서 잰 값에서 출발한 제안값.
사용: python tools/make_intro_sign.py  (다시 돌리면 같은 그림 — 난수 씨앗 고정)
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "Assets/Fonts/BMEULJIROTTF.ttf"
OUT = ROOT / "Assets/UI/intro_sign.png"

W, H = 2000, 800                  # 판 1.2 × 0.48 m 와 같은 5:2
PLATE = (222, 216, 198)           # 사진 흰 판 (209~222) 에 누런 기
RED = (150, 42, 33)               # 사진 01 바랜 빨강 (135, 66, 57) 보다 조금 진하게
BLACK = (38, 34, 30)
RUST = np.array([96, 52, 26], np.float32)
MINE = "귀령광업소"
TITLE = "막장"                     # Tuning.INTRO_TITLE 과 같게


def spaced(d, xy, s, font, fill, spacing):
    """가운데 정렬, 글자 사이를 spacing 만큼 벌려 찍는다."""
    widths = [d.textlength(c, font=font) for c in s]
    x = xy[0] - (sum(widths) + spacing * (len(s) - 1)) / 2
    for c, w in zip(s, widths):
        d.text((x, xy[1]), c, font=font, fill=fill, anchor="lm")
        x += w + spacing


def main():
    rng = np.random.default_rng(7)
    im = Image.new("RGB", (W, H), PLATE)
    d = ImageDraw.Draw(im)
    d.rectangle([30, 30, W - 31, H - 31], outline=BLACK, width=9)          # 테두리 선
    spaced(d, (W / 2, 140), MINE, ImageFont.truetype(str(FONT), 88), BLACK, 6)
    spaced(d, (W / 2, 470), TITLE, ImageFont.truetype(str(FONT), 470), RED, 44)

    a = np.asarray(im).astype(np.float32)
    # 얼룩: 굵은 잡음을 흐려서 곱한다 (0.78~1.06)
    stain = Image.fromarray((rng.random((H // 16, W // 16)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(22))
    a *= (0.78 + 0.28 * np.asarray(stain, np.float32) / 255)[..., None]
    # 페인트가 벗겨진 잔 점: 글씨·판 모두 군데군데 바탕이 드러난다
    chips = np.asarray(Image.fromarray((rng.random((H // 4, W // 4)) > 0.985).astype(np.uint8) * 255).resize((W, H), Image.NEAREST).filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
    a = a * (1 - chips[..., None] * 0.35) + np.array([150, 140, 120], np.float32) * chips[..., None] * 0.35
    # 모서리·가장자리 녹
    yy, xx = np.mgrid[0:H, 0:W]
    edge = np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy]).astype(np.float32)
    rust = np.clip(1 - edge / 58, 0, 1) * (rng.random((H, W)) > 0.55)
    rust = np.asarray(Image.fromarray((rust * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
    a = a * (1 - rust[..., None] * 0.7) + RUST * rust[..., None] * 0.7

    out = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(out)
    for bx, by in ((76, 76), (W - 76, 76), (76, H - 76), (W - 76, H - 76)):  # 못 구멍
        d.ellipse([bx - 15, by - 15, bx + 15, by + 15], fill=(60, 50, 40))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    print(f"{OUT.relative_to(ROOT)} {W}x{H}")


if __name__ == "__main__":
    main()
