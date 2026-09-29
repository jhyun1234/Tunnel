# 3D-P — 얼굴을 가리는 마스크 두 가지 비교, 판정 ⑤ 한 장 (09-29). 그림은 build/player/ (커밋 안 함).
# 먼저: blender -b -P blender/rig/player_mask.py -- half   ·   -- full
#   python docs/그림/3DP_마스크.py            → build/player/P5_판정5.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "player")
OUT = os.path.join(ROOT, "P5_판정5.png")
W = 2400
S.new(W, 3600)
HL, OK = (255, 154, 60), (126, 208, 126)
def photo(x, y, w, h, name, cap, sz=16): S.photo(x, y, w, h, os.path.join(ROOT, name), cap, sz)

text(24, 16, "3D-P — 얼굴을 가리는 마스크 두 가지 · 판정 ⑤ (09-29)", 36, b=True)
text(24, 64, "사용자 09-29: 협동에서 플레이어마다 얼굴이 달라지니 마스크를 씌운 모습으로 · 둘 다 코드로 20 대 얼굴 판의 얼굴 겉면에 맞춰 만듦(0 크레딧)", 19, C["sub"])
cols = [("가. 반쪽 방진마스크 (기록 있음)", "half", OK), ("나. 얼굴 전체 방독면 (※ 기록 없음)", "full", HL)]
cw, gap = (W - 48 - 20) / 2, 20
y = 110
for i, (t, _, col) in enumerate(cols):
    text(24 + i * (cw + gap), y, t, 28, col, b=True)
y += 52
w4 = (cw - 20) / 2
for i, (_, k, _) in enumerate(cols):
    x0 = 24 + i * (cw + gap)
    photo(x0, y, w4, w4, f"P2_player1_fix_retex2_mask_{k}_소품_얼굴.png", "얼굴 앞", 16)
    photo(x0 + w4 + 20, y, w4, w4, f"P2_player1_fix_retex2_mask_{k}_얼굴_가까이.png", "가까이(협동에서 옆 사람을 볼 때)", 16)
y += w4 + 60
for i, (_, k, _) in enumerate(cols):
    x0 = 24 + i * (cw + gap)
    photo(x0, y, w4, 820, f"P2_player1_fix_retex2_mask_{k}_소품_앞.png", "앞", 16)
    photo(x0 + w4 + 20, y, w4, 820, f"P2_player1_fix_retex2_mask_{k}_소품_옆.png", "옆", 16)
y += 820 + 60

bh = 360
S.d.rounded_rectangle([24 * S.SS, y * S.SS, (W - 24) * S.SS, (y + bh) * S.SS], radius=10 * S.SS, fill=(55, 51, 48))
boxes = [("가. 반쪽 방진마스크", OK, ["근거: 문경석탄박물관 유물(조사 13 k16) — 회청색 고무 컵 · 둥근 필터 하나 · 쇠고리 넷 · 머리끈 둘 · 15 × 10 × 9.5 cm",
                                    "1980 년대 후반부터 제대로 씀(조사 13 [E]) · 1992 장성 사진에도 씀(k25)",
                                    "만든 것: 컵 13.6 × 10.7 × 11.4 cm(필터 포함) · 얼굴에서 3 mm 이상 떠 있음 · 코끝 · 입을 가림",
                                    "눈 · 눈썹은 보인다 — 안전모 챙과 함께 얼굴 차이가 거의 안 드러남"]),
         ("나. 얼굴 전체 방독면", HL, ["※ 1980 년대 한국 광부가 일할 때 쓴 기록 없음 — 흔한 민간 방독면 모양으로 지어냄",
                                    "검은 고무 전면 · 쇠테 눈 렌즈 둘 · 입 앞 정화통 · 머리끈 세 쌍(K-1 방독면 '각 끈(3쌍)')",
                                    "만든 것: 16.9 × 15.6 × 17.9 cm · 윗 끝이 안전모 챙 아래 · 눈 · 코 · 입 모두 가림",
                                    "얼굴이 완전히 가려진다 · 무서운 분위기는 더 난다"]),
         ("판정 ⑤ 물을 것", C["rew"], ["1. 어느 쪽으로 갈까 — 가(기록과 맞음) / 나(얼굴 완전히 가림)",
                                     "2. (생각거리) 평소엔 가, 가스가 찬 곳(기획서 REP-4 가스)에서만 나로 바꿔 쓰기",
                                     "알려 둘 것: 목 옆(귀 아래)에 그림 얼룩 — Meshy 목깃을 숨긴 자리. 마스크 판정 뒤 Blender 로 그림만 손봄(0 크레딧)",
                                     "통과면 차례 3 = Mixamo 뼈대(손가락 포함) — Chrome 로그인 필요"])]
cw3 = (W - 48 - 60) / 3
for i, (title, col, lines) in enumerate(boxes):
    x0 = 44 + i * (cw3 + 10); yy = y + 16
    text(x0, yy, title, 23, col, b=True); yy += 42
    for ln in lines:
        for piece in wrap("· " + ln, 18, cw3 - 24):
            text(x0, yy, piece, 18); yy += 26
        yy += 6
y = int(y + bh + 24)
S.img = S.img.crop((0, 0, W * S.SS, y * S.SS)).resize((W, y), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
