# ART-1 차례 3 — 광장 물건 후보 한 장. 먼저 blender/art/props_candidates.py 로 build/art/props_render/ 를 찍는다.
#   python docs/그림/ART1_물건_후보.py   → docs/그림/ART1_물건_후보.png
import os, json
from PIL import Image
import sheet as S

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "..", "..", "build", "art", "props_render")
info = json.load(open(os.path.join(R, "props.json"), encoding="utf-8"))
NOTE = {"B7": "갱내 사진은 없음(갱구 2)", "B8": "글자는 지어냄", "B3": "문은 반쯤 열림",
        "P1": "부품 모음 — 이어 붙여 씀", "P2": "부품 모음", "P3": "형광등 (화순 2022 사진에 1)", "P4": "여러 모양 모음 — 하나 고름",
        "P6": "요즘 것 (하얗고 깨끗)", "P7": "영어 'DANGER' — 지워야", "P8": "부품 모음", "P14": "글자 찍힘 — 지워야",
        "P15": "영어 경고 그림 — 지워야", "P16": "요즘 것 (파랑)", "P18": "영어 'CEMENT' — 지워야"}
COLS, TW, TH, GAP = 5, 380, 238, 14
def rows(keys): return (len(keys) + COLS - 1) // COLS
B = [k for k in info if k.startswith("B")]; P = [k for k in info if k.startswith("P")]
LH = 64; W = 40 + COLS * (TW + GAP)
H = 110 + 44 + rows(B) * (TH + LH) + 44 + rows(P) * (TH + LH) + 20
img, d = S.new(W, H)
S.text(20, 14, "ART-1 차례 3 — 광장 물건 후보 (진짜 부스 광장 · 새 바위 질감 · 같은 빛)", 24, b=True)
S.text(20, 52, "B = Blender 로 만드는 것(첫 모양 — 치수는 사진·조사, 질감 CC0) · P = Poly Haven CC0 모델(사진으로 스캔한 진짜 물건). '사진 N' = 실제 갱도 사진 13장 중 보인 수, '추정' = 사진에서 확인 못 함.", 14, col=S.C["sub"])
S.text(20, 76, "빼고 싶은 것 · 고치고 싶은 것을 번호로 알려 주세요. 빛은 Blender(게임과 다름). 면 수 = 삼각형, 광장 물건 한도 25만.", 14, col=S.C["sub"])
y = 110
for title, keys in (("Blender 로 만드는 것", B), ("Poly Haven CC0 모델", P)):
    S.text(20, y, title, 20, b=True); y += 44
    for i, k in enumerate(keys):
        x = 20 + (i % COLS) * (TW + GAP); yy = y + (i // COLS) * (TH + LH)
        im = Image.open(os.path.join(R, k + ".png")).convert("RGB").resize((TW * S.SS, TH * S.SS), Image.LANCZOS)
        img.paste(im, (x * S.SS, yy * S.SS))
        v = info[k]; sz = " × ".join("%.1f" % a for a in v["size"])
        S.text(x, yy + TH + 6, "%s  %s" % (k, v["name"]), 16, b=True, col=S.C["rew"] if v["photo"] != "추정" else S.C["text"])
        S.text(x, yy + TH + 28, "%s · %s면 · %s m" % (v["photo"], format(v["tris"], ","), sz), 13, col=S.C["sub"])
        if k in NOTE: S.text(x, yy + TH + 45, NOTE[k], 13, col=S.C["exit"])
    y += rows(keys) * (TH + LH)
img.resize((img.width // S.SS, img.height // S.SS), Image.LANCZOS).save(os.path.join(HERE, "ART1_물건_후보.png"))
print("saved")
