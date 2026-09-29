# 3D-P — 목 옆 얼룩 손질 전 · 후 (방독면 나, 판정 ⑦ 한 장, 09-29). 그림은 build/player/ (커밋 안 함).
# "전" = P6_안전모_후_옆_머리.png(안전모를 옮긴 뒤, 얼룩 손질 전). 먼저 player_meshy_fix.py -- player1 player1_retex2 → player_mask.py -- full
#   python docs/그림/3DP_목.py            → build/player/P7_판정7.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "player")
OUT = os.path.join(ROOT, "P7_판정7.png")
W = 2400
S.new(W, 2400)
def crop(src, dst):
    Image.open(os.path.join(ROOT, src)).crop((330, 60, 750, 480)).resize((900, 900), Image.LANCZOS).save(os.path.join(ROOT, dst))
crop("P2_player1_fix_retex2_mask_full_소품_옆.png", "P7_목_후_옆_머리.png")
crop("P2_player1_fix_retex2_mask_full_소품_뒤.png", "P7_목_후_뒤_머리.png")
def photo(x, y, w, h, name, cap, sz=17): S.photo(x, y, w, h, os.path.join(ROOT, name), cap, sz)

text(24, 16, "3D-P — 목 옆 얼룩 손질 · 방독면 나 · 판정 ⑦ (09-29)", 36, b=True)
text(24, 64, "사용자 09-29: \"통과. 목 옆 얼룩 고쳐라\" — 모양은 그대로, 그림(텍스처)만 Blender 로 다시 칠함(0 크레딧) · 같은 카메라 · 같은 조명", 19, C["sub"])
w4 = (W - 48 - 3 * 20) / 4
y = 110
for i, (n, c) in enumerate((("P6_안전모_후_옆_머리.png", "전 — 옆(목에 빨강 · 흰 조각)"), ("P7_목_후_옆_머리.png", "후 — 옆"),
                            ("P2_player1_fix_retex2_mask_full_얼굴_가까이.png", "후 — 비스듬히 가까이"), ("P7_목_후_뒤_머리.png", "후 — 뒤"))):
    photo(24 + i * (w4 + 20), y, w4, w4, n, c)
y += w4 + 60
lines = ["원인: Meshy 가 목깃 · 목수건 자리에 칠한 빨강 · 흰색. 목깃 덩어리는 목 속으로 넣었지만 그 둘레 · 뒤통수 아래(안전모 밑)에 그 색이 남았다",
         "고친 것: 면(삼각형) 가운데 자리로 구역을 나눠 그림 칸을 다시 칠함 — 목(귀 높이까지) = 목 살색(때 묻은 어두운 살색) · 뒤통수 아래 = 머리카락 색 · 목수건 아래 옷깃 = 빨강 · 흰 칸만 옷 색. "
         "방독면 속 얼굴(입술 · 눈)과 귀는 그대로. 밝고 어두운 결(때)은 남기고 색만 바꿈",
         "알게 된 것: ① 그림 조각 가장자리에 빨간 줄 — 멀리서 쓰는 흐린 그림(밉맵)이 옆 칸 색을 섞어 옴 → 조각 밖 빈칸으로 12 칸 넓혀 칠함 ② 얼룩은 목 가운데에서 11~13 cm(뒤통수 아래)까지 퍼져 있었다 — 처음엔 목만 칠해서 안 없어졌다",
         "검사: fix_neck_stain(빨강 · 흰 얼룩 22.6 → 0.0 %) · fix_hair_patch(밝은 조각 23.3 → 0.0 %) — 사보타주 norepaint 는 둘 다 FAIL",
         "남은 것: 목 모양이 구겨진 자리가 어두운 주름처럼 보임(Meshy 목깃을 목 속에 넣은 자리) · 귀 뒤 옆머리에 살색이 조금",
         "판정 ⑦: 목이 괜찮은가. 통과면 차례 3 = Mixamo 뼈대(손가락 포함) — Chrome 로그인 필요"]
bh = 60 + 30 * sum(len(wrap("· " + l, 20, W - 100)) for l in lines)
S.d.rounded_rectangle([24 * S.SS, y * S.SS, (W - 24) * S.SS, (y + bh) * S.SS], radius=10 * S.SS, fill=(55, 51, 48))
yy = y + 18
for ln in lines:
    for piece in wrap("· " + ln, 20, W - 100):
        text(48, yy, piece, 20); yy += 30
y = int(y + bh + 24)
S.img = S.img.crop((0, 0, W * S.SS, y * S.SS)).resize((W, y), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
