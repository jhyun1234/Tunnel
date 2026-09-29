"""3D-P2 판정 ⑤ 한 장: 세운 몸 옛(찰흙) ↔ 새 재질 — 1.5 · 3 m, 앞 · 옆 · 뒤 (머리등, 같은 자리 · 멈춘 채) → build/player/P15_판정5.png
  python docs/그림/3DP2_판정5.py   (먼저 `bash tools/quick.sh player` — 캡처 build/Tunnel/check/55_player_look_*)"""
import os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHK = os.path.join(ROOT, "build", "Tunnel", "check")
OUT = os.path.join(ROOT, "build", "player", "P15_판정5.png")
FONT = os.path.join(ROOT, "Assets", "Fonts", "Pretendard-Regular.otf")
F, FB = ImageFont.truetype(FONT, 24), ImageFont.truetype(FONT, 32)
CROP = {"1.5": (610, 180, 1310, 1080), "3.0": (760, 360, 1160, 1000)}   # 몸이 가운데 오는 칸
W, H = 380, 490
sheet = Image.new("RGB", (40 + 6 * (W + 10), 120 + 2 * (H + 50)), (24, 24, 26))
d = ImageDraw.Draw(sheet)
d.text((20, 14), "3D-P2 판정 ⑤ — 세운 몸 재질: 옛(찰흙) ↔ 새 (머리등, 같은 자리 · 멈춘 채 · 탄가루 보통)", font=FB, fill=(240, 240, 240))
d.text((20, 60), "새 = 부위별 윤기 · 오목한 곳 그늘 · 천 결 · 탄가루 · 소품 질감 (소품은 두 칸 모두 새 것 — 옛/새 는 몸만 바꾼다)", font=F, fill=(210, 210, 210))
for r, dist in enumerate(("1.5", "3.0")):
    for c, (dn, label) in enumerate((("front", "앞"), ("side", "옆"), ("back", "뒤"))):
        for k, old in enumerate(("old", "new")):
            im = Image.open(os.path.join(CHK, f"55_player_look_{old}_{dist}m_{dn}.png")).crop(CROP[dist]).resize((W, H))
            x, y = 20 + (c * 2 + k) * (W + 10), 110 + r * (H + 50)
            sheet.paste(im, (x, y))
            d.text((x + 6, y + H + 6), f"{dist} m {label} — {'옛(찰흙)' if old == 'old' else '새'}", font=F, fill=(230, 230, 230) if old == "new" else (170, 170, 170))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
sheet.save(OUT)
print(OUT)
