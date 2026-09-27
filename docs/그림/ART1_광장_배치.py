# ART-1 차례 3 — 광장 물건 배치 평면 (위에서 본 그림, 북쪽이 위). 좌표 = booth_table.py 의 m (광장 x −7.7..7.7 · y −5.46..4.34, 케이지 (0, 0))
#   python docs/그림/ART1_광장_배치.py   → docs/그림/ART1_광장_배치.png
import os, math
import sheet as S

HERE = os.path.dirname(os.path.abspath(__file__))
PX = 62                                          # px / m
X0, X1, Y0, Y1 = -7.7, 7.7, -5.46, 4.34
MX, MY = 150, 150                                # 여백
W = int((X1 - X0) * PX) + 2 * MX + 520; H = int((Y1 - Y0) * PX) + 2 * MY + 120
img, d = S.new(W, H)
def P(x, y): return ((MX + (x - X0) * PX) * S.SS, (MY + 60 + (Y1 - y) * PX) * S.SS)
def rect(x0, y0, x1, y1, fill=None, outline=None, w=2):
    (a, b), (c, e) = P(x0, y1), P(x1, y0); d.rectangle([a, b, c, e], fill=fill, outline=outline, width=w * S.SS)
def line(pts, col, w=3): d.line([P(*p) for p in pts], fill=col, width=w * S.SS)
def dot(x, y, r, col): (a, b) = P(x, y); d.ellipse([a - r * S.SS, b - r * S.SS, a + r * S.SS, b + r * S.SS], fill=col)
def lab(x, y, t, sz=13, col=S.C["text"], b=False, anchor="mm"):
    a, bb = P(x, y); S.text(a / S.SS, bb / S.SS, t, sz, col=col, b=b, anchor=anchor)

S.text(20, 14, "ART-1 차례 3 — 광장 물건 배치 (위에서 본 그림, 북쪽 = 위, 1 칸 = 1 m)", 22, b=True)
S.text(20, 46, "광장 15.4 × 9.8 m · 천장 4.5 m. 케이지 = 손그림 자리(가운데). 출구 다섯 앞 1.2 m 는 비움(회색 띠). 물건 번호 = 후보 한 장(ART1_물건_후보.png).", 14, col=S.C["sub"])
# 바닥 · 격자
rect(X0, Y0, X1, Y1, fill=(62, 57, 53), outline=(150, 145, 135), w=3)
for gx in range(-7, 8): line([(gx, Y0), (gx, Y1)], (74, 69, 64), 1)
for gy in range(-5, 5): line([(X0, gy), (X1, gy)], (74, 69, 64), 1)
# 출구 (굴 폭 3.3) + 비우는 띠
EX = [("서북 굴 → 큰길", "W", 1.4), ("동북 굴 → 큰길", "E", 0.7), ("서쪽 굴 (어두움)", "W", -2.1), ("동쪽 굴 (어두움)", "E", -4.1), ("남쪽 굴 → 펌프실·충전실", "S", 0.0)]
for name, side, c in EX:
    if side in "WE":
        x = X0 if side == "W" else X1; s = -1 if side == "W" else 1
        rect(min(x, x + s * 1.3), c - 1.65, max(x, x + s * 1.3), c + 1.65, fill=(40, 36, 34))
        rect(min(x, x - s * 1.2), c - 1.65, max(x, x - s * 1.2), c + 1.65, fill=(88, 84, 78))
        lab(x + s * 0.2, c + (1.95 if c > 0 else -1.95), name, 12, col=S.C["exit"], anchor="rm" if side == "W" else "lm")
        line([(x, c - 1.65), (x, c + 1.65)], S.C["door"], 4)                                  # B4 강철 아치
    else:
        rect(c - 1.65, Y0 - 1.3, c + 1.65, Y0, fill=(40, 36, 34)); rect(c - 1.65, Y0, c + 1.65, Y0 + 1.2, fill=(88, 84, 78))
        line([(c - 1.65, Y0), (c + 1.65, Y0)], S.C["door"], 4); lab(c, Y0 - 1.0, name, 12, col=S.C["exit"])
dot(0, Y1, 7, S.C["crawl"]); lab(0, Y1 + 0.55, "뚫린 바위 틈 → 큰길", 12, col=S.C["crawl"])
# 레일 (동서로 케이지를 지남) + 서쪽 갈림 → 서쪽 굴
RC = (150, 150, 160)
for off in (-0.3, 0.3):
    line([(-7.7, 1.4 + off), (-5.5, 0.3 + off), (-3.0, off), (3.0, off), (5.5, 0.3 + off), (7.7, 0.7 + off)], RC, 2)
    line([(-3.0, off), (-4.6, -0.6 + off), (-6.4, -1.7 + off), (-7.7, -2.1 + off)], RC, 2)
lab(-2.4, 0.55, "B1 레일", 12, col=RC); lab(-5.4, -1.35, "B1 갈림", 12, col=RC)
# 케이지 (틀 2.6 × 2.2, 문 = 서쪽·동쪽 — 레일이 지나감)
rect(-1.3, -1.1, 1.3, 1.1, fill=(95, 70, 60), outline=(200, 150, 120), w=3); rect(-0.9, -0.7, 0.9, 0.7, outline=(170, 170, 175), w=2)
lab(0, 0.25, "B3 케이지", 14, b=True); lab(0, -0.3, "B6 사슬 · 위는 검은 굴", 11)
line([(-1.3, -0.7), (-1.3, 0.7)], (230, 230, 235), 5); line([(1.3, -0.7), (1.3, 0.7)], (230, 230, 235), 5)
# 광차 (원래 SLOT_Prop_Cart 자리 근처, 서쪽 레일 위) — Meshy 시험
rect(-5.6, -0.2, -4.1, 0.75, fill=(110, 105, 100), outline=(220, 220, 220)); lab(-4.85, 0.28, "B2 광차", 12, b=True)
# 벽을 따라: 관 · 전선 · 통풍관 · 등 · 판
line([(-7.6, 4.15), (7.6, 4.15)], (120, 160, 200), 5); lab(0.6, 3.75, "P1 관 · 밸브 (북쪽 벽 3.6 m 높이)", 12, col=(140, 180, 220), anchor="lm")
line([(-7.55, -5.3), (-3, -5.3)], (200, 200, 90), 3); line([(3, -5.3), (6.0, -5.3)], (200, 200, 90), 3); lab(3.2, -4.9, "P2 전선 (벽 2.8 m)", 12, col=(210, 210, 110), anchor="lm")
line([(7.45, 2.4), (7.45, 4.2), (4.5, 4.2)], (170, 170, 170), 7); lab(6.0, 3.3, "P8 통풍관 (천장 아래)", 12, col=(190, 190, 190), anchor="mm")
for x, y in ((-4.2, 1.4), (4.2, 1.4)): dot(x, y, 9, S.C["rew"]); lab(x, y - 0.55, "P4 철망 등 (전등 자리)", 11, col=S.C["rew"])
dot(7.55, -1.2, 6, S.C["rew"]); lab(6.9, -1.2, "P3 형광등", 11, col=S.C["rew"], anchor="rm")
for x, y, t, dx, dy, an in ((-3.0, 4.25, "B7 안전제일", 0.2, -0.45, "lm"), (7.6, -1.8, "B9 작업현황", -0.7, 0.0, "rm"), (-1.45, -0.9, "B8 케이지 경고", 0.0, -0.45, "mm")):
    dot(x, y, 6, (240, 240, 240)); lab(x + dx, y + dy, t, 12, anchor=an)
# 공구 모퉁이 (남서쪽 — 서쪽 굴 · 남쪽 굴 비우는 띠 밖)
rect(-7.6, -5.4, -6.0, -4.8, fill=(110, 110, 100)); lab(-6.8, -5.1, "P20", 11)
for i, t in enumerate(("P9", "P10", "P11", "P12")): dot(-5.7 + i * 0.35, -5.25, 5, (200, 180, 140))
lab(-5.2, -4.7, "P9–P12 공구 기대 둠", 11)
rect(-7.6, -4.6, -6.8, -4.2, fill=(140, 100, 70)); lab(-7.2, -4.4, "P13", 11)
dot(-4.0, -4.9, 6, (150, 110, 80)); lab(-3.6, -4.6, "P17", 11)
line([(-2.9, -5.35), (-2.1, -5.35)], (170, 130, 90), 6); lab(-2.5, -4.95, "P19 사다리", 11)
# 첫 자리
dot(0, -3.15, 9, S.C["hub"]); line([(0, -3.15), (0, -2.1)], S.C["hub"], 3); lab(0.3, -3.5, "첫 자리 (북쪽을 봄)", 12, col=S.C["hub"], anchor="lm")
# 오른쪽 설명
tx = MX + (X1 - X0) * PX + 190; ty = MY + 60
for i, t in enumerate(["굴 안(광장 밖):", "B5 나무 동발 — 지금 하얀 네모 갱목을", "   둥근 통나무로 (부스 맵 전체)", "", "사진 근거 없는 것 = 추정:", "P9–P13 · P17 · P20 · B7 갱내", "", "물건 한도: 삼각형 25만,", "부딪힘 = 케이지 · 광차 · 선반 ·", "상자만 (길찾기 바닥 다시 굽기)", "", "레일 · 관 · 전선 · 판 = 부딪힘 없음"]):
    S.text(tx, ty + i * 24, t, 14, col=S.C["sub"] if not t.endswith(":") else S.C["text"], b=t.endswith(":"))
img.resize((img.width // S.SS, img.height // S.SS)).save(os.path.join(HERE, "ART1_광장_배치.png"))
print("saved")
