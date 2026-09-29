"""크기 · 눈높이 한 장: 부스 광장 · 내 앞 같은 거리에 세운 몸 · 괴물(멈춰 선 자세) — 옆 그림(나란히) + 내 눈 화면(한 몸씩 같은 자리), 내 눈 줄 → build/player/P16_크기_눈높이.png
  python docs/그림/크기_눈높이.py   (먼저 `bash tools/quick.sh sizes` — 실행 파일이 잰 build/Tunnel/check/sizes.json · 60_sizes_*.png)
  숫자는 전부 실행 파일이 잰 값. 세운 몸의 눈만 어림(머리 꼭대기 − 12 cm) — 몸 그물에 눈 표시가 없다"""
import json, os
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHK = os.path.join(ROOT, "build", "Tunnel", "check")
OUT = os.path.join(ROOT, "build", "player", "P16_크기_눈높이.png")
FONT = os.path.join(ROOT, "Assets", "Fonts", "Pretendard-Regular.otf")
F, FS, FB = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 19), ImageFont.truetype(FONT, 30)
S = json.load(open(os.path.join(CHK, "sizes.json"), encoding="utf-8"))
EYE_GAP = 0.12                                           # 사람 머리 꼭대기 ↔ 눈 (어림)
body_eye = S["bodyOnlyTop"] - EYE_GAP

W0, H0 = 1920, 1080                                      # 캡처 크기
PW, PH = 1200, 675                                       # ① 칸
QW, QH = 950, 534                                        # ② ③ 칸 (아랫줄에 나란히)
sheet = Image.new("RGB", (2 * QW + 50, 100 + PH + 40 + QH + 50), (24, 24, 26))
d = ImageDraw.Draw(sheet)
d.text((20, 12), "크기 · 눈높이 — 부스 광장, 내 앞 같은 거리(%.1f m)에 세운 몸 · 괴물(게임에서 멈춰 선 자세)" % S["dist"], font=FB, fill=(240, 240, 240))
d.text((20, 58), "숫자는 모두 실행 파일에서 잰 바닥에서의 높이. 노란 줄 = 1인칭 화면의 내 눈. 세운 몸의 눈만 어림(머리 꼭대기 − 12 cm)", font=F, fill=(200, 200, 200))

# ① 옆 그림 — 같은 자리에서 원근 없이 찍어 높이를 자로 읽는다
x0, y0 = 20, 100
im = Image.open(os.path.join(CHK, "60_sizes_ortho.png")).convert("RGB").resize((PW, PH))
sheet.paste(im, (x0, y0))
k = PW / W0
half, mid = S["orthoHalf"], S["orthoMid"]
def row(h): return y0 + (H0 / 2 - (h - mid) / half * H0 / 2) * k
def col(dx): return x0 + (W0 / 2 + dx / (half * W0 / H0) * W0 / 2) * k
def dashed(xa, xb, y, fill, w=2, dash=14):
    x = xa
    while x < xb:
        d.line([(x, y), (min(x + dash, xb), y)], fill=fill, width=w)
        x += dash * 2
def tick(cx, half_w, h, text, fill, left=False):
    y = row(h)
    d.line([(cx - half_w, y), (cx + half_w, y)], fill=fill, width=3)
    tw = d.textlength(text, font=FS)
    tx = cx - half_w - tw - 8 if left else cx + half_w + 8
    d.rectangle([tx - 3, y - 13, tx + tw + 3, y + 12], fill=(0, 0, 0))
    d.text((tx, y - 12), text, font=FS, fill=fill)

YEL, CYAN, RED, GRAY = (255, 214, 60), (110, 210, 255), (255, 110, 90), (170, 170, 170)
for m in range(0, 4):                                    # 자 — 1 m 마다
    y = row(m)
    d.line([(x0, y), (x0 + 18, y)], fill=GRAY, width=2)
    d.text((x0 + 22, y - 12), f"{m} m", font=FS, fill=GRAY)
dashed(x0, x0 + PW, row(S["eye"]), YEL, 2)
d.text((x0 + PW - 250, row(S["eye"]) - 30), f"내 눈 {S['eye']:.2f} m (1인칭 화면)", font=F, fill=YEL)   # 왼쪽은 안전제일 표지판과 겹친다
dashed(x0, x0 + 260, row(S["crouchEye"]), (200, 170, 60), 2)
d.text((x0 + 70, row(S["crouchEye"]) - 30), f"숙인 눈 {S['crouchEye']:.2f} m", font=FS, fill=(200, 170, 60))

bx, mx = col(S["bodyX"]), col(S["monX"])
# 세운 몸은 높이가 5 cm 씩이라 글이 겹친다 — 글은 위로 떼어 쌓고 선으로 잇는다
for i, (hh, text) in enumerate(((S["bodyTop"], f"안전모 꼭대기 {S['bodyTop']:.2f}"), (S["bodyOnlyTop"], f"머리 꼭대기 {S['bodyOnlyTop']:.2f}"), (body_eye, f"눈(어림) {body_eye:.2f}"))):
    y, ly = row(hh), row(S["bodyTop"]) - 110 + i * 30
    d.line([(bx - 30, y), (bx + 30, y)], fill=CYAN, width=3)
    tw = d.textlength(text, font=FS)
    lx = bx + 60
    d.line([(bx + 30, y), (lx - 4, ly)], fill=CYAN, width=1)
    d.rectangle([lx - 3, ly - 13, lx + tw + 3, ly + 12], fill=(0, 0, 0))
    d.text((lx, ly - 12), text, font=FS, fill=CYAN)
tick(mx, 70, S["monTop"], f"머리 꼭대기 {S['monTop']:.2f}", RED)
if S["monEyePx"] > 0:
    tick(mx, 70, S["monEye"], f"눈(빛나는 곳) {S['monEye']:.2f}", RED)
tick(mx, 70, S["monCapsuleBooth"], f"부딪히는 몸통 끝 {S['monCapsuleBooth']:.2f} (부스)", (200, 90, 80))
if S["ceilMon"] == S["ceilMon"] and S["ceilMon"] < mid + half:   # NaN 이 아니고 그림 안
    dashed(mx - 160, mx + 160, row(S["ceilMon"]), GRAY, 2, 8)
    d.text((mx + 170, row(S["ceilMon"]) - 12), f"천장 {S['ceilMon']:.2f}", font=FS, fill=GRAY)
d.text((x0 + 8, y0 + PH + 6), "① 옆 그림 — 같은 자리에서 원근 없이(멀어도 작아지지 않게) 찍은 것. 팔 · 곡괭이는 뺌", font=FS, fill=(220, 220, 220))

# ② ③ 내 눈으로 본 게임 화면 — 고개 수평이면 화면 가운데 줄이 곧 내 눈높이. 한 몸씩 같은 자리(Shift+7 · 9 키와 같은 거리)
qy = y0 + PH + 40
for i, (key, label) in enumerate((("body", "② 세운 몸"), ("monster", "③ 괴물"))):
    fp = Image.open(os.path.join(CHK, f"60_sizes_fp_{key}.png")).convert("RGB").resize((QW, QH))
    px = x0 + i * (QW + 10)
    sheet.paste(fp, (px, qy))
    dashed(px, px + QW, qy + QH / 2, YEL, 2, 10)
    d.text((px + 6, qy + QH + 6), f"{label} — 내 눈으로 본 게임 화면(고개 수평). 노란 줄 = 내 눈높이. 같은 자리 · 같은 거리({S['dist']:.1f} m)", font=FS, fill=(220, 220, 220))

# 표 — 쉬운 말로
qx, ty = x0 + PW + 24, y0 + 6
pose = {"up_stand": "멈춰 섬", "up_walk": "걷기", "up_jog": "빠른 걸음", "up_run": "뛰어옴", "up_grope": "더듬기", "idle_crouch": "9 키로 세울 때(웅크림)"}
left = [
    (f"나(1인칭): 눈 {S['eye']:.2f} m · 숙이면 {S['crouchEye']:.2f} m", YEL),
    (f"  = 카메라 {S['eye'] - S['rootGap']:.2f} + 몸이 바닥에서 뜬 {S['rootGap'] * 100:.0f} cm", YEL),
    (f"  (부딪히는 몸통 {S['capsule']:.2f} m 의 바닥 여유)", YEL),
    (f"세운 몸(남이 보는 내 몸): 안전모까지 {S['bodyTop']:.2f} m", CYAN),
    (f"  머리 {S['bodyOnlyTop']:.2f} · 눈 어림 {body_eye:.2f} m", CYAN),
    (f"  → 내 눈이 남의 눈보다 {(S['eye'] - body_eye) * 100:.0f} cm 높다", CYAN),
    (f"괴물(×{S['monScale']:.1f}, 멈춰 섬): 머리 {S['monTop']:.2f} · 눈 {S['monEye']:.2f} m", RED),
    (f"  발이 바닥에서 {S['monSole'] * 100:.0f} cm 떠 있다", RED),
    (f"  부딪히는 몸통 {S['monCapsuleBooth']:.1f}(부스) / {S['monCapsule']:.1f}(복도) m", RED),
    (f"  나를 보는 눈(코드) {S['monEyeRay']:.1f} m", RED),
]
right = [("괴물 자세별 머리 꼭대기(가장 낮게~높게)", RED)]
for p in S["poses"]:
    right.append((f"  {pose.get(p['clip'], p['clip'])} {p['top'][0]:.2f}~{p['top'][1]:.2f} m", RED))
right.append((f"천장: 내 자리 {S['ceilMe']:.2f} · 괴물 자리 {S['ceilMon']:.2f} m", GRAY))
for i, (t, c) in enumerate(left + [("", GRAY)] + right):
    d.text((qx, ty + i * 27), t, font=FS, fill=c)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
sheet.save(OUT)
print(OUT)
