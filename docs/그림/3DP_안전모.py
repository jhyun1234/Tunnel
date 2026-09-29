# 3D-P — 안전모를 Meshy 머리 가운데로 옮긴 전 · 후 (방독면 나, 판정 ⑥ 한 장, 09-29). 그림은 build/player/ (커밋 안 함).
# "전" 그림 P6_안전모_전_*.png 는 옮기기 전에 P2_player1_fix_retex2_mask_full_* 를 복사해 둔 것.
#   python docs/그림/3DP_안전모.py            → build/player/P6_판정6.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "player")
OUT = os.path.join(ROOT, "P6_판정6.png")
W = 2400
S.new(W, 2600)
def crop_head(src, dst):
    """옆모습(1024 × 1536, 정사영 2.05 m)에서 머리 부분만 잘라 키운다 — 전 · 후 같은 자리."""
    im = Image.open(os.path.join(ROOT, src)); im.crop((330, 60, 750, 480)).resize((900, 900), Image.LANCZOS).save(os.path.join(ROOT, dst))
crop_head("P6_안전모_전_옆.png", "P6_안전모_전_옆_머리.png")
crop_head("P2_player1_fix_retex2_mask_full_소품_옆.png", "P6_안전모_후_옆_머리.png")
def photo(x, y, w, h, name, cap, sz=17): S.photo(x, y, w, h, os.path.join(ROOT, name), cap, sz)

text(24, 16, "3D-P — 안전모를 뒤로(머리 가운데로) · 방독면 나 · 판정 ⑥ (09-29)", 36, b=True)
text(24, 64, "사용자 09-29: \"나로 간다. 옆모습을 보니 안전모가 머리에서 좀 앞으로 튀어나와 있다. 뒤로 좀 빼야\" — 같은 카메라 · 같은 조명", 19, C["sub"])
cw = (W - 48 - 20) / 2
y = 110
for i, t in enumerate(("전 — 챙이 이마 앞 6.9 cm · 뒤통수 뒤 -0.2 cm", "후 — 챙이 이마 앞 3.3 cm · 뒤통수 뒤 3.3 cm")):
    text(24 + i * (cw + 20), y, t, 26, C["text"] if i == 0 else C["rew"], b=True)
y += 48
photo(24, y, cw, cw * 0.72, "P6_안전모_전_옆_머리.png", "옆(머리)")
photo(24 + cw + 20, y, cw, cw * 0.72, "P6_안전모_후_옆_머리.png", "옆(머리)")
y += cw * 0.72 + 56
photo(24, y, cw, cw * 0.72, "P6_안전모_전_가까이.png", "비스듬히 가까이")
photo(24 + cw + 20, y, cw, cw * 0.72, "P2_player1_fix_retex2_mask_full_얼굴_가까이.png", "비스듬히 가까이")
y += cw * 0.72 + 56
lines = ["원인: 안전모 자리를 밑그림 머리에 맞춰 두었는데 Meshy 머리 가운데는 그보다 3.5 cm 뒤(y -4.2 → -0.7 cm)",
         "고친 것: 챙 2~4.5 cm 아래 머리 단면(손질 전)의 앞 끝 · 뒤 끝 가운데로 옮기고 램프 줄을 다시 이음 — 새 검사 fix_helmet_balanced(앞뒤 차이 < 1.5 cm), 사보타주 helmetfwd 는 FAIL",
         "같이 맞춘 것: 뒷머리 · 이마를 새 안전모 안쪽 면에 · 방독면을 새 자리에 다시 만듦(윗 끝이 챙 아래) — 검사 모두 통과",
         "판정 ⑥: 이 정도로 뒤로 간 것이 맞나 · 방독면 나 모습이 괜찮나. 통과면 목 옆 그림 얼룩 손질 → 차례 3 Mixamo 뼈대(Chrome 로그인 필요)"]
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
