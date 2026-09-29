# 3D-P 차례 2 손질 — Blender 손질 · Meshy 그림 다시 · 둘 다 비교, 판정 ③ 한 장 (09-29). 그림은 build/player/ (커밋 안 함).
# 먼저: player_meshy_views.py -- player1 gear · -- player1_retex1 [gear] · player_meshy_fix.py -- player1 · -- player1 player1_retex1
#   python docs/그림/3DP_손질.py            → build/player/P3_판정3.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "player")
OUT = os.path.join(ROOT, "P3_판정3.png")
W, H = 2400, 4200
S.new(W, H)
HL, OK = (255, 154, 60), (126, 208, 126)
def photo(x, y, w, h, name, cap, sz=16): S.photo(x, y, w, h, os.path.join(ROOT, name), cap, sz)

text(24, 16, "3D-P 차례 2 손질 — Blender 와 Meshy 로 각각 고친 것 · 판정 ③ (09-29)", 36, b=True)
text(24, 64, "모두 같은 조명 · 같은 카메라 · 안전모 · 탄띠 · 배터리 · 수통은 코드 소품 그대로. Meshy 그림 다시 = 10 크레딧 1 번(남은 2,669) · Blender 손질 = 0 크레딧", 19, C["sub"])
cols = [("원래 (Meshy 한 번)", "player1", "player1"),
        ("가. Blender 손질", "player1_fix", "player1_fix"),
        ("나. Meshy 그림 다시", "player1_retex1", "player1_retex1"),
        ("가 + 나 (+ 장갑 색 되살림)", "player1_fix_retex1", "player1_fix_retex1")]
cw, gap = (W - 48 - 3 * 20) / 4, 20
y = 110
for i, (t, _, _) in enumerate(cols):
    text(24 + i * (cw + gap), y, t, 26, C["rew"] if i == 3 else C["text"], b=True)
y += 48
rows = [("소품_얼굴", 560, "얼굴"), ("소품_앞", 820, "앞"), ("소품_뒤", 820, "뒤"), ("손", 460, "손")]
for key, h, lab in rows:
    for i, (t, gtag, ptag) in enumerate(cols):
        tag = (gtag if key.startswith("소품") else ptag)
        photo(24 + i * (cw + gap), y, cw, h, f"P2_{tag}_{key}.png", lab, 15)
    y += h + 44

bx, bw, bh = 24, W - 48, 300
S.d.rounded_rectangle([bx * S.SS, y * S.SS, (bx + bw) * S.SS, (y + bh) * S.SS], radius=10 * S.SS, fill=(55, 51, 48))
boxes = [("가. Blender 손질 (0 크레딧)", OK, ["뒷머리를 안전모 안쪽으로 — 튀어나온 정도 1.76 → 1.00(안쪽 면)",
                                            "목 깁스(목깃 덩어리 518 점)를 목 속에 넣고 코드 목수건으로 덮음",
                                            "소매 굵기 반지름 5.3 → 4.7 cm(왼 5.0 → 4.5) · 점 순서 그대로",
                                            "남은 것: 뒤통수에 머리 · 살 얼룩 · 목수건이 둥근 고리 모양"]),
         ("나. Meshy 그림 다시 (10 크레딧)", OK, ["얼굴이 사람 같아짐(살결 · 주름 · 탄가루) · 옷이 낡고 때 묻음 · 장화에 흙",
                                                "목깃이 회색 수건처럼 보임(모양은 그대로)",
                                                "틀린 것: 장갑이 검게, 흰 면 손목도 어둡게 바뀜(09-27 근로장갑과 다름)",
                                                "틀린 것: 얼굴이 40~50 대로 보임 — 기획서는 20 대 신입 후산부"]),
         ("가 + 나 · 판정 ③ 물을 것", C["rew"], ["둘은 점 · 그림 좌표가 같아 합쳤다. 장갑 · 손목 색은 원래 그림에서 되살리고 새 그림의 때를 얹음(Blender, 0 크레딧)",
                                             "1. 어느 판으로 차례 3(Mixamo 뼈대)에 갈까 — 추천: 가 + 나",
                                             "2. 얼굴 나이: 이대로 / Meshy 그림 다시 한 번 더(10 크레딧, '20 대 초반' 을 세게)",
                                             "3. 뒤통수 얼룩 · 둥근 목수건은 뼈대 뒤 3 인칭에서 다시 볼까"])]
cw3 = (bw - 60) / 3
for i, (title, col, lines) in enumerate(boxes):
    x0 = bx + 20 + i * (cw3 + 10); yy = y + 16
    text(x0, yy, title, 23, col, b=True); yy += 42
    for ln in lines:
        for piece in wrap("· " + ln, 18, cw3 - 24):
            text(x0, yy, piece, 18); yy += 26
        yy += 8
y_end = y + bh + 30
S.img = S.img.crop((0, 0, W * S.SS, y_end * S.SS)).resize((W, y_end), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
