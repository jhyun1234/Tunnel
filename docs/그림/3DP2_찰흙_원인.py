"""3D-P2 제안서 그림: 지금 세운 몸 가까이(게임 캡처) + 한국 광부 사진에서 본 겉면 → build/player/P14_찰흙_원인.png
  python docs/그림/3DP2_찰흙_원인.py   (먼저 `bash tools/quick.sh player` 로 캡처 51_player_body_front 를 만든다)"""
import glob, os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHK = os.path.join(ROOT, "build", "Tunnel", "check")
REF = os.path.join(ROOT, "build", "refs", "player", "kr")
OUT = os.path.join(ROOT, "build", "player", "P14_찰흙_원인.png")
F = ImageFont.truetype(os.path.join(ROOT, "Assets", "Fonts", "Pretendard-Regular.otf"), 24)
FB = ImageFont.truetype(os.path.join(ROOT, "Assets", "Fonts", "Pretendard-Regular.otf"), 32)
sheet = Image.new("RGB", (2400, 1340), (24, 24, 26))
d = ImageDraw.Draw(sheet)
d.text((20, 14), "3D-P2 — 왜 찰흙처럼 보이나: 지금 몸(왼쪽) · 사진 속 광부 겉면(오른쪽)", font=FB, fill=(240, 240, 240))
now = Image.open(os.path.join(CHK, "51_player_body_front.png")).crop((820, 540, 1100, 1080)).resize((560, 1080))
sheet.paste(now, (20, 70))
notes = ["지금(게임 캡처, 머리등)", "① 몸 전체 윤기 한 값 — 천 · 장화 · 장갑이 같은 은은한 윤",
         "   (Meshy 거칠기 그림도 부위마다 0.58~0.67 로 거의 같다)", "② 소품은 한 색 — 결 · 때 · 닳음 없음",
         "③ 가림(오목한 곳 그늘) · 천 결 · 탄가루 없음", "④ 옷이 근육에 붙고 주름 없음 — 이번엔 안 고침(나 안)"]
for i, t in enumerate(notes):
    d.text((600, 80 + i * 36), t, font=F, fill=(230, 230, 230))
refs = [("k19", "1981 — 안전모가 때로 거뭇 · 긁힘"), ("k26", "1992 — 무광 면 · 주름 · 탄가루 얼룩"), ("k25", "1992 — 헐렁한 옷 · 소매 주름"),
        ("k10", "고무 장화 — 약한 윤 · 밑창에 먼지"), ("k12", "탄띠 — 검은 면 띠 · 쇠 구멍"), ("k09", "면 작업복 — 무광 · 솔기 · 단추")]
for i, (k, t) in enumerate(refs):
    f = glob.glob(os.path.join(REF, k + "_*"))[0]
    im = Image.open(f).convert("RGB"); im.thumbnail((560, 400))
    x, y = 600 + (i % 3) * 600, 330 + (i // 3) * 500
    sheet.paste(im, (x, y))
    d.text((x, y + im.size[1] + 6), f"{k} {t} (사진에서 잼)", font=F, fill=(220, 220, 220))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
sheet.save(OUT)
print(OUT)
