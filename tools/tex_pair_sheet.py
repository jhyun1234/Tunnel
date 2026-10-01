"""TEX-1 바닥 고르기 묶음 그림: blender/map/tex_compare.py CAT=pair 가 찍은 build/tex_test/compare/pair/ → 벽마다 한 장(sheet_w<벽>.jpg, 고르는 용) + docs/그림/MAP4_바닥고르기.jpg
  python tools/tex_pair_sheet.py                      잰 값 표 + 벽마다 한 장
  python tools/tex_pair_sheet.py 3:6,4 4:12,7 ...     고른 짝(벽:바닥,바닥)을 노란 테두리로 → docs/그림/MAP4_바닥고르기.jpg
잰 값 = 벽과 바닥이 만나는 선 위아래 30 픽셀 띠의 차이: 색 차(밝기 뺀 색조 · 진하기) · 밝기 차 · 결 거칠기 비. 작을수록 이어져 보인다 — 마지막은 눈으로 고른다."""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = os.path.join(ROOT, "build", "tex_test", "compare", "pair")
f1 = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 22); f2 = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 17)
WALL = {3: "③ Fab 바위벽", 4: "④ 착암 자국", 5: "⑤ 회색 셰일", 6: "⑥ 갈색 바위", 7: "⑦ 석탄", 8: "⑧ 층진 셰일", 9: "⑨ 짙은 회색", 10: "⑩ 검은 바위", 11: "⑪ 검은 셰일"}
FLOOR = {2: "② 석탄 부스러기", 3: "③ 잔돌 흙", 4: "④ 어두운 진흙", 5: "⑤ 돌 부스러기", 6: "⑥ 돌 박힌 흙", 7: "⑦ 깬돌", 8: "⑧ 진흙", 9: "⑨ 젖은 흙", 10: "⑩ 진흙 자국", 11: "⑪ 다져진 바닥", 12: "⑫ 붉은 자갈"}

def lab(rgb):                                                              # sRGB 0..1 → CIE Lab
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]]) / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

mk = np.asarray(Image.open(os.path.join(D, "mask.png")).convert("RGB"), dtype=np.float32) / 255
wall, floor = (mk[..., 0] > 0.5) & (mk[..., 1] < 0.5), (mk[..., 1] > 0.5) & (mk[..., 0] < 0.5)
B = 30; ws, fs = np.zeros_like(wall), np.zeros_like(floor)
for k in range(1, B + 1):                                                  # 벽 띠 = 바로 아래 30 픽셀 안에 바닥이 있는 벽 · 바닥 띠 = 그 반대
    ws[:-k] |= wall[:-k] & floor[k:]; fs[k:] |= floor[k:] & wall[:-k]
def grain(L, m):                                                           # 띠 안 밝기의 잔 결 (이웃 픽셀과의 차이)
    d = np.abs(np.diff(L, axis=1)); return float(d[m[:, 1:] & m[:, :-1]].mean())
idx = json.load(open(os.path.join(D, "index.json"), encoding="utf-8")); rows = []
for it in idx:
    im = np.asarray(Image.open(os.path.join(D, it["file"])).convert("RGB"), dtype=np.float64) / 255; lb = lab(im)
    a, b = lb[ws].mean(0), lb[fs].mean(0)
    it.update(wl=float(a[0]), fl=float(b[0]), dcol=float(np.hypot(a[1] - b[1], a[2] - b[2])), dl=float(b[0] - a[0]), grain=grain(lb[..., 0], fs) / max(grain(lb[..., 0], ws), 1e-6))
    it["score"] = it["dcol"] + 0.5 * abs(it["dl"]) + 6 * abs(np.log(it["grain"]))
walls = sorted({it["wall"] for it in idx}); floors = sorted({it["floor"] for it in idx})
for w in walls:
    r = sorted((it for it in idx if it["wall"] == w), key=lambda it: it["score"])
    print("wall %2d: " % w + "  ".join("f%d(%.1f: col %.1f L %+.0f grain %.2f x%.2f)" % (it["floor"], it["score"], it["dcol"], it["dl"], it["grain"], it["floor_mul"]) for it in r))
    cols, W, H = 4, 640, 360; n = len(r); sh = Image.new("RGB", (W * cols, 44 + ((n + cols - 1) // cols) * (H + 30)), (14, 14, 16)); dr = ImageDraw.Draw(sh)
    dr.text((10, 8), "벽 %s × 바닥 후보 (잰 값 차례 — 왼쪽 위가 가장 가깝다)" % WALL.get(w, w), font=f1, fill=(240, 240, 240))
    for i, it in enumerate(r):
        x, y = (i % cols) * W, 44 + (i // cols) * (H + 30); sh.paste(Image.open(os.path.join(D, it["file"])).convert("RGB"), (x, y))
        dr.text((x + 8, y + H + 4), "바닥 %s · 색 차 %.1f · 밝기 %+.0f · 결 %.2f · 곱 %.2f" % (FLOOR.get(it["floor"], it["floor"]), it["dcol"], it["dl"], it["grain"], it["floor_mul"]), font=f2, fill=(255, 210, 120))
    sh.save(os.path.join(D, "sheet_w%02d.jpg" % w), quality=86)
json.dump(idx, open(os.path.join(D, "measured.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
Y = lambda L: ((max(L, 1.0) + 16) / 116) ** 3                             # 찍힌 띠 밝기 → 빛 계산 눈금. 바닥이 벽보다 조금(L 4) 어둡게 되도록 곱을 다시 맞춘다 (바닥은 빛을 더 받는다)
json.dump({"%d_%d" % (it["wall"], it["floor"]): round(min(1.5, it["floor_mul"] * Y(it["wl"] - 4) / Y(it["fl"])), 3) for it in idx}, open(os.path.join(D, "pair_mul.json"), "w"))

pick = dict((int(a), [int(v) for v in b.split(",")]) for a, b in (t.split(":") for t in sys.argv[1:]))
if pick:
    W, H, X0, Y0 = 300, 169, 190, 140; sh = Image.new("RGB", (X0 + W * len(floors), Y0 + (H + 26) * len(walls) + 10), (14, 14, 16)); dr = ImageDraw.Draw(sh)
    dr.text((14, 12), "TEX-1 바닥 고르기 — 벽마다 바닥 후보를 같은 굴 · 같은 빛에 나란히. 노란 테두리 = 고른 바닥 (벽과 가장 이어져 보이는 것)", font=f1, fill=(240, 240, 240))
    dr.text((14, 44), "칸 아래 = 만나는 선 위아래의 색 차 · 결 거칠기 비(1 에 가까울수록 벽과 같은 결). 바닥 밝기는 벽보다 조금 어둡게 곱으로 맞춰 찍었다(밝기는 게임에서 키로 고른다)", font=f2, fill=(200, 200, 200))
    dr.text((14, 70), "바닥 ③ 은 가까이 보면 풀이 보여 뺐다. 물가 방(펌프실 · 옛 펌프장)은 바닥 사진이 벽 아래 물 자국 띠로 올라가서 무늬 없는 ④ 로. 석탄 면(⑦)은 벽과 같은 사진 ②.", font=f2, fill=(200, 200, 200))
    for j, f in enumerate(floors): dr.text((X0 + j * W + 8, Y0 - 30), "바닥 " + FLOOR.get(f, str(f)), font=f2, fill=(255, 210, 120))
    for i, w in enumerate(walls):
        y = Y0 + i * (H + 26); dr.text((10, y + 60), "벽 " + WALL.get(w, str(w)), font=f2, fill=(255, 210, 120))
        for j, f in enumerate(floors):
            it = next((t for t in idx if t["wall"] == w and t["floor"] == f), None)
            if it is None: continue
            x = X0 + j * W; sh.paste(Image.open(os.path.join(D, it["file"])).convert("RGB").resize((W, H)), (x, y))
            dr.text((x + 6, y + H + 2), "색 차 %.1f · 결 %.2f" % (it["dcol"], it["grain"]), font=f2, fill=(255, 225, 90) if f in pick.get(w, ()) else (150, 150, 150))
            if f in pick.get(w, ()): dr.rectangle((x + 1, y + 1, x + W - 2, y + H - 2), outline=(255, 225, 40), width=5)
    out = os.path.join(ROOT, "docs", "그림", "MAP4_바닥고르기.jpg"); sh.save(out, quality=88); print(out.encode("unicode_escape").decode(), sh.size)
