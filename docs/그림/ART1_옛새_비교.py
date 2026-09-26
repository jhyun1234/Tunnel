# ART-1 차례 2 — 게임 캡처 옛 모습 | 새 모습 (검사 -only art 가 찍은 build/Tunnel/check/27_art_<자리>_old/new.png)
#   python docs/그림/ART1_옛새_비교.py   → docs/그림/ART1_옛새_비교.png
import os
from PIL import Image
import sheet as S

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(HERE, "..", "..", "build", "Tunnel", "check")
ROWS = [("plaza_n", "광장 첫 자리 (북쪽 — 바위 틈 있는 벽)"), ("plaza_e", "광장 동쪽"), ("plaza_s", "광장 남쪽 (갱목 굴)"),
        ("plaza_w", "광장 서쪽"), ("main", "큰길 가운데")]
TW, TH, GAP = 640, 360, 16
W = 40 + 2 * TW + GAP; HEAD = 92; RH = TH + 40
img, d = S.new(W, HEAD + len(ROWS) * RH + 10)
S.text(20, 14, "ART-1 차례 2 — 게임 화면: 옛 모습 | 새 모습 (헤드램프 켬, 같은 자리)", 22, b=True)
S.text(20, 50, "새 = 바위 Rock031 · 석탄 띠 Rock035 · 바닥 진흙 brown_mud_03, 무늬 되풀이 없음, 젖은 곳, 전등 튀는 빛, 먼지, 필름 입자. 물건(갱목 · 레일 등)은 아직 옛 것 — 차례 3.", 14, col=S.C["sub"])
y = HEAD
for key, label in ROWS:
    S.text(20, y, label, 16, b=True)
    for j, v in enumerate(("old", "new")):
        im = Image.open(os.path.join(CAP, "27_art_%s_%s.png" % (key, v))).convert("RGB").resize((TW * S.SS, TH * S.SS), Image.LANCZOS)
        x = 20 + j * (TW + GAP)
        img.paste(im, (x * S.SS, (y + 26) * S.SS))
        S.text(x + 8, y + 32, "옛" if v == "old" else "새", 18, col=S.C["rew"], b=True)
    y += RH
img.resize((img.width // S.SS, img.height // S.SS), Image.LANCZOS).save(os.path.join(HERE, "ART1_옛새_비교.png"))
print("saved")
