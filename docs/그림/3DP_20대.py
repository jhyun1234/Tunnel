# 3D-P 차례 2 손질 — 얼굴을 20 대로 다시 입힌 것 비교, 판정 ④ 한 장 (09-29). 그림은 build/player/ (커밋 안 함).
# 먼저: player_meshy_fix.py -- player1 player1_retex1 · -- player1 player1_retex2 (둘 다 가 + 나 = Blender 손질 + 그림 다시 + 장갑 색 되살림)
#   python docs/그림/3DP_20대.py            → build/player/P4_판정4.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "player")
OUT = os.path.join(ROOT, "P4_판정4.png")
W = 2400
S.new(W, 3600)
def photo(x, y, w, h, name, cap, sz=16): S.photo(x, y, w, h, os.path.join(ROOT, name), cap, sz)

NOTES = [l for l in os.environ.get("P4_NOTES", "").split("|") if l]
text(24, 16, "3D-P 차례 2 손질 — 얼굴을 20 대로 다시 입힘 · 판정 ④ (09-29)", 36, b=True)
text(24, 64, "둘 다 가 + 나(Blender 손질 모양 + Meshy 그림 다시 + 장갑 · 손목 색 되살림) · 같은 조명 · 같은 카메라 · 그림 다시 = 10 크레딧씩", 19, C["sub"])
cols = [("1 차 그림 (40~50 대로 보임)", "player1_fix_retex1"), ("20 대로 다시 (이번)", "player1_fix_retex2")]
cw, gap = (W - 48 - 20) / 2, 20
y = 110
for i, (t, _) in enumerate(cols):
    text(24 + i * (cw + gap), y, t, 28, C["rew"] if i == 1 else C["text"], b=True)
y += 52
for key, h, lab in (("소품_얼굴", 900, "얼굴(안전모)"), ("얼굴", 900, "얼굴(안전모 없음)")):
    for i, (_, tag) in enumerate(cols):
        photo(24 + i * (cw + gap), y, cw, h, f"P2_{tag}_{key}.png", lab, 17)
    y += h + 50
w4 = (W - 48 - 3 * 20) / 4
for i, (tag, key, lab) in enumerate(((cols[0][1], "소품_앞", "1 차 · 앞"), (cols[1][1], "소품_앞", "이번 · 앞"),
                                     (cols[0][1], "손", "1 차 · 손"), (cols[1][1], "손", "이번 · 손"))):
    photo(24 + i * (w4 + 20), y, w4, 640 if "앞" in key else 640, f"P2_{tag}_{key}.png", lab, 16)
y += 640 + 50
if NOTES:
    bh = 60 + 34 * len(NOTES)
    S.d.rounded_rectangle([24 * S.SS, y * S.SS, (W - 24) * S.SS, (y + bh) * S.SS], radius=10 * S.SS, fill=(55, 51, 48))
    yy = y + 16; text(44, yy, "판정 ④", 24, C["rew"], b=True); yy += 42
    for ln in NOTES:
        for piece in wrap("· " + ln, 20, W - 100):
            text(48, yy, piece, 20); yy += 30
    y += bh + 20
S.img = S.img.crop((0, 0, W * S.SS, y * S.SS)).resize((W, y), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
