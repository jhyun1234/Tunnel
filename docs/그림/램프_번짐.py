"""램프 빛 번짐 한 장: 표지판 셋 1 m · 뒤가 트인 곳의 세운 몸 0.6 m — 고치기 전 ↔ 지금(09-30: 표지판 바탕 × SIGN_BOARD_BRIGHT · 머리등이 표지판 · 남의 몸도 봄 × LAMP_PROBE_DIM)
  → build/player/P18_램프_번짐.png
  python docs/그림/램프_번짐.py   (먼저 `bash tools/quick.sh glare` — build/Tunnel/check/61_glare_* · build/quick_glare.log 의 GLARE 줄)"""
import os, re
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHK = os.path.join(ROOT, "build", "Tunnel", "check")
OUT = os.path.join(ROOT, "build", "player", "P18_램프_번짐.png")
FONT = os.path.join(ROOT, "Assets", "Fonts", "Pretendard-Regular.otf")
F, FS, FB = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 19), ImageFont.truetype(FONT, 30)
log = open(os.path.join(ROOT, "build", "quick_glare.log"), encoding="utf-8", errors="ignore").read()
num = {(m[0], m[1]): (float(m[2]), float(m[3])) for m in re.findall(r"GLARE (\S+) (\S+): burnt ([\d.]+) % · mean ([\d.]+)", log)}
names = sorted({k[0] for k in num})
pick = lambda p: next(x for x in names if x.startswith(p))
SIGN_COLS = (("before", "고치기 전"), ("before_nobloom", "고치기 전 + 빛 번짐 끔"), ("now", "지금 (판 어둡게 + 머리등이 봄)"), ("nobloom", "지금 + 빛 번짐 끔"))
BODY_COLS = (("before", "고치기 전 (머리등이 못 봄)"), ("probe0.5", "머리등이 보는 정도 0.5"), ("probe0.7", "보는 정도 0.7"), ("now", "보는 정도 1.0 (지금)"))
rows = [(pick("sign0"), "벽의 흰 표지판 1 m", SIGN_COLS), (pick("sign1"), "케이지 기둥 노란 표지판 1 m", SIGN_COLS),
        (pick("sign2"), "동쪽 벽 작업현황 1 m", SIGN_COLS), (pick("stoodbody_open"), "뒤가 트인 곳 세운 몸 0.6 m", BODY_COLS)]
W, H = 440, 248
sheet = Image.new("RGB", (40 + 4 * (W + 10), 120 + len(rows) * (H + 62)), (24, 24, 26))
d = ImageDraw.Draw(sheet)
d.text((20, 12), "램프 빛 번짐 — 고치기 전 ↔ 지금 (부스 맵, 실행 파일)", font=FB, fill=(240, 240, 240))
d.text((20, 58), "숫자 = 물체 위 하얗게 탄 몫 · 밝기. 빛 번짐(Bloom)은 거의 상관없다 — 탄 원인은 빛이 너무 센 것", font=F, fill=(200, 200, 200))
for r, (n, lab, cols) in enumerate(rows):
    for c, (tag, ct) in enumerate(cols):
        f = os.path.join(CHK, f"61_glare_{n}_{tag}.png")
        x, y = 20 + c * (W + 10), 100 + r * (H + 62)
        if not os.path.exists(f):
            continue
        sheet.paste(Image.open(f).convert("RGB").crop((480, 270, 1440, 810)).resize((W, H)), (x, y))
        b, m = num[(n, tag)]
        col = (255, 110, 90) if b > 20 else (240, 210, 90) if b > 8 else (140, 220, 140)
        d.text((x + 4, y + H + 4), f"{lab} · {ct}", font=FS, fill=(220, 220, 220))
        d.text((x + 4, y + H + 28), f"하얗게 탄 몫 {b:.0f} % · 밝기 {m:.2f}", font=FS, fill=col)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
sheet.save(OUT)
print(OUT)
