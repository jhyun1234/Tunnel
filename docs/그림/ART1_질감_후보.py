# ART-1 차례 1 — 질감 후보 한 장. 먼저 blender/art/texture_candidates.py 로 build/art/cand/ 를 찍는다.
#   python docs/그림/ART1_질감_후보.py   → docs/그림/ART1_질감_후보.png
import os
from PIL import Image
import sheet as S

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(HERE, "..", "..", "build", "art", "cand")
SRC = {"now": "지금 게임", "dark_rock": "Poly Haven", "brown_mud_03": "Poly Haven", "rocks_ground_02": "Poly Haven",
       "stony_dirt_path": "Poly Haven", "brown_mud_02": "Poly Haven"}          # 나머지 RockNNN = ambientCG (둘 다 CC0)
ROWS = [("벽 (바위)", "wall", "near_wall", ["now", "Rock031", "Rock022", "Rock030", "Rock050"]),
        ("석탄 (까만 띠로 섞일 것)", "coal", "near_wall", ["Rock035", "Rock037", "Rock033", "dark_rock"]),
        ("바닥", "floor", "near_floor", ["now", "brown_mud_03", "rocks_ground_02", "stony_dirt_path", "brown_mud_02"])]
TW, TH, GAP = 400, 225, 20
W = 40 + 5 * (TW + GAP); HEAD = 96; RH = 44 + 2 * TH + 12 + 36
img, d = S.new(W, HEAD + len(ROWS) * RH + 20)
S.text(20, 16, "ART-1 질감 후보 — 진짜 부스 맵 광장에 입혀 같은 빛으로 찍음 (위 = 첫 자리에서 넓게 · 아래 = 가까이)", 24, b=True)
S.text(20, 54, "모두 CC0(공짜 · 팔아도 됨 · 공개 저장소 가능). Blender 빛이라 게임과 밝기·색이 다르다 — 게임에서는 무늬 되풀이를 없애고, 바위 · 석탄 띠 · 바닥 진흙을 섞고, 젖은 곳을 번들거리게 한다.", 15, col=S.C["sub"])
y = HEAD
for title, kind, near, ids in ROWS:
    S.text(20, y + 6, title, 22, b=True)
    for i, cid in enumerate(ids):
        x = 20 + i * (TW + GAP)
        for j, view in enumerate(("wide", near)):
            im = Image.open(os.path.join(CAND, "%s_%s_%s.png" % (kind, cid, view))).convert("RGB").resize((TW * S.SS, TH * S.SS))
            img.paste(im, (x * S.SS, (y + 44 + j * (TH + 6)) * S.SS))
        S.text(x, y + 44 + 2 * TH + 16, "%d. %s  (%s)" % (i + 1, "지금" if cid == "now" else cid, SRC.get(cid, "ambientCG")), 17,
               col=S.C["rew"] if cid == "now" else S.C["text"], b=True)
    y += RH
img.resize((img.width // S.SS, img.height // S.SS), Image.LANCZOS).save(os.path.join(HERE, "ART1_질감_후보.png"))
print("saved", os.path.join(HERE, "ART1_질감_후보.png"))
