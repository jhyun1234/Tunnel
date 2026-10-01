"""질감 후보 비교 묶음 그림: blender/map/tex_compare.py 가 찍은 build/tex_test/compare/<분류>/ → docs/그림/MAP4_질감자료_<분류>.jpg
  python tools/tex_compare_sheet.py rock floor wood metal misc
칸마다 이름 · 출처 · 색 그림 밝기 평균(0~1 — 0.3 넘으면 머리등에 하얗게 탄다)을 적는다."""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TITLE = {"rock": "굴 벽 · 천장 (바위 · 석탄)", "floor": "바닥", "wood": "갱목 · 판자", "metal": "쇠 (기계 · 드럼통 · 관 · 철판)", "misc": "천 · 자루 · 벽 판"}
f1 = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 26); f2 = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 20)
def src(s):
    s = (s or "").lower()
    return "Poly Haven (CC0)" if "polyhaven" in s else "ambientCG (CC0)" if "ambientcg" in s else s if s in ("지금 게임",) else "Fab (이미 가짐)" if "fab" in s else s[:24]
for cat in sys.argv[1:]:
    d = os.path.join(ROOT, "build", "tex_test", "compare", cat); idx = json.load(open(os.path.join(d, "index.json"), encoding="utf-8"))
    W, H, cols = 800, 450, 3; rows = (len(idx) + cols - 1) // cols; sh = Image.new("RGB", (W * cols, 70 + rows * (H + 64)), (14, 14, 16)); dr = ImageDraw.Draw(sh)
    dr.text((16, 16), "MAP4 질감 자료 비교 — %s  (같은 굴 · 같은 빛, 후보만 바꿈. 첫 칸 = 지금 게임. 질감이 보이게 게임보다 밝게 찍음)" % TITLE.get(cat, cat), font=f1, fill=(240, 240, 240))
    for i, it in enumerate(idx):
        x, y = (i % cols) * W, 70 + (i // cols) * (H + 64); sh.paste(Image.open(os.path.join(d, it["file"])).convert("RGB").resize((W, H)), (x, y))
        b = float(np.asarray(Image.open(it["color"]).convert("L").resize((256, 256)), dtype=np.float32).mean() / 255) if it.get("color") else -1
        dr.text((x + 10, y + H + 4), "%d. %s" % (i + 1, it["name"]), font=f1, fill=(255, 210, 120))
        dr.text((x + 10, y + H + 36), "%s · 한 장 %.1f m%s" % (src(it["source"]), it["tile_m"], (" · 밝기 %.2f%s" % (b, " (밝다)" if b > 0.3 else "")) if b >= 0 else ""), font=f2, fill=(200, 200, 200))
    out = os.path.join(ROOT, "docs", "그림", "MAP4_질감자료_%s.jpg" % cat); sh.save(out, quality=88); print(out.encode("unicode_escape").decode(), sh.size, len(idx))
