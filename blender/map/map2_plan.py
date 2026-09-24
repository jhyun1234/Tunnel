# MAP2 plan view draft (make_booth.py table format) + walkable-area comparison with MAP1 (same raster method, agent radius 0.6).
import math, sys
from PIL import Image, ImageDraw, ImageFont
OUT = sys.argv[1]

# ---------------- MAP1 (make_booth.py now, widths/heights after +0.5 m)
S1 = 1.0
MAP1_T = [("station", [(0,0,0,5.0),(8,0,0,5.0)]), ("haulage", [(8,0,0,3.3),(72.5,0,0,3.3)]),
    ("siding", [(9,0,0,3.0),(12,-3.2,0,3.0),(22,-3.2,0,3.0),(25,0,0,3.0)]), ("pump_pass", [(60,0,0,2.4),(60,-3.2,0,2.4)]),
    ("xcut1", [(16,0,0,3.0),(17.21,1.56,0,3.0),(23,9,S1,3.0)]), ("xcut2", [(50,0,0,3.0),(51.09,1.56,0,3.0),(57,10,S1,3.0)]),
    ("xcut3", [(30,0,0,3.0),(35,-6,0,3.0)]), ("door_pass", [(33,-3.6,0,2.4),(28.4,-7.6,0,2.4)]),
    ("noburi", [(35,-6,0,2.4),(41,-7,2.8,2.4),(48,-8.5,6.2,2.4)]), ("seamW1", [(23,9,S1,2.4),(18,10.2,S1,2.4),(13,9.6,S1,2.3)]),
    ("seamW2", [(13,9.6,S1,2.3),(8,11,S1,2.2),(3,11.5,S1,2.1)]), ("stub1", [(18,10.2,S1,2.2),(18.3,14.4,S1,2.2)]),
    ("stub2", [(9,10.8,S1,2.1),(9.6,14.8,S1,2.1)]), ("seamE1", [(23,9,S1,2.4),(28,9.6,S1,2.4),(32.5,9.5,S1,2.4)]),
    ("seamE2", [(47,10,S1,2.4),(52,10.8,S1,2.4),(57,10,S1,2.4),(62,11,S1,2.4),(66,10.6,S1,2.4)])]
MAP1_R = [(-3,0,-1.5,1.5),(57,64,-8,-3)] + [(cx,cx+2.1,5.0,16.1) for cx in (32.0,36.5,41.0,45.5)] + [(32.0,47.6,cy,cy+2.1) for cy in (5.0,9.5,14.0)]

# ---------------- MAP2 draft. (이름, [(x, y, 바닥, 폭)], 천장, 갱목?, 걷는 길?, 빛)  빛: L 켜짐 · D 꺼진 전등 · K 어둠
SEAM = 1.5
T = [
    ("station",   [(0,0,0,6.0),(16,0,0,6.0)], 4.5, False, True, "L"),
    ("haulageA",  [(16,0,0,4.0),(40,1,0,4.0)], 3.4, True, True, "L"),
    ("haulageB",  [(40,1,0,4.0),(70,3.5,0,4.0),(100,5,0,4.0)], 3.4, True, True, "D"),
    ("haulageC",  [(100,5,0,4.0),(130,3.5,0,4.0),(160,0.5,0,4.0),(186,-3,0,4.0)], 3.4, True, True, "K"),
    ("siding",    [(20,0,0,3.2),(24,-4.2,0,3.2),(40,-4.2,0,3.2),(44,1.3,0,3.2)], 3.2, True, True, "L"),
    ("charge_a",  [(5,0,0,2.6),(5,-7,0,2.6)], 3.0, False, True, "L"),
    ("charge_b",  [(12,0,0,2.6),(12,-7,0,2.6)], 3.0, False, True, "L"),
    ("refuge1",   [(62,2.8,0,1.6),(62,-0.8,0,1.6)], 2.7, False, False, "D"),
    ("refuge2",   [(102,4.9,0,1.6),(102,1.3,0,1.6)], 2.7, False, False, "K"),
    ("refuge3",   [(146,1.9,0,1.6),(146,-1.7,0,1.6)], 2.7, False, False, "K"),
    ("comp_pass", [(92,4.6,0,2.8),(92,-4,0,2.8)], 3.2, False, True, "D"),
    ("air1",      [(54,2.2,0,3.0),(52,-26,0,3.0)], 3.2, True, True, "K"),
    ("airway",    [(50,-26,0,3.0),(80,-27,0,3.0),(110,-26,0,3.0),(140,-24,0,3.0),(170,-22,0,3.0)], 3.2, True, True, "K"),
    ("air3",      [(166,-0.2,0,3.0),(168,-22.3,0,3.0)], 3.2, True, True, "K"),
    ("door_stub", [(118,4.3,0,2.8),(118,-8,0,2.8)], 3.2, True, True, "K"),
    ("pump_pass", [(84,-26.9,0,2.8),(84,-32,0,2.8)], 3.2, False, True, "K"),
    ("xc1",       [(24,0.33,0,3.3),(35,23,SEAM,3.3)], 3.2, True, True, "D"),
    ("xc2",       [(52,2.0,0,3.3),(65,26,SEAM,3.3)], 3.2, True, True, "D"),
    ("xc3",       [(82,4.1,0,3.3),(95,27,SEAM,3.3)], 3.2, True, True, "D"),
    ("xc4",       [(112,4.4,0,3.3),(125,25,SEAM,3.3)], 3.2, True, True, "K"),
    ("xc5",       [(142,2.3,0,3.3),(155,22,SEAM,3.3)], 3.2, True, True, "K"),
    ("xc6",       [(168,-0.6,0,3.3),(180,19,SEAM,3.3)], 3.2, True, True, "K"),
    ("seamW",     [(8,20,SEAM,2.4),(-2,19,SEAM,2.4)], 2.9, True, True, "K"),
    ("seam",      [(8,20,SEAM,3.0),(35,23,SEAM,3.0),(65,26,SEAM,3.0),(95,27,SEAM,3.0),(125,25,SEAM,3.0),(155,22,SEAM,3.0),(180,19,SEAM,3.0)], 3.0, True, True, "K"),
    ("incline",   [(20,21.5,SEAM,2.8),(20.6,28.5,3.4,2.8),(21.3,37.4,5.8,2.8),(22,46,8.1,2.8)], 2.9, True, True, "K"),   # 주탄중승 15°
    ("br1W",      [(20.6,28.5,3.4,2.4),(10,28.2,3.4,2.4)], 2.9, True, True, "K"),
    ("br1E",      [(20.6,28.5,3.4,2.4),(32,29,3.4,2.4)], 2.9, True, True, "K"),
    ("br2W",      [(21.3,37.4,5.8,2.4),(10,37,5.8,2.4)], 2.9, True, True, "K"),
    ("br2E",      [(21.3,37.4,5.8,2.4),(33,38,5.8,2.4)], 2.9, True, True, "K"),
    ("oldnoburi", [(48,24.3,SEAM,1.4),(48.2,27.2,SEAM,1.4)], 2.5, False, False, "K"),
    ("pr_a",      [(70,26.2,SEAM,3.0),(70.5,32,SEAM,3.0)], 3.0, True, True, "K"),
    ("pr_b",      [(90,26.8,SEAM,3.0),(90.5,32,SEAM,3.0)], 3.0, True, True, "K"),
    ("noburi1",   [(120,25.3,SEAM,2.6),(120.3,28,SEAM,2.6),(121,45,9.4,2.6)], 2.9, True, True, "K"),   # 25°
    ("noburi2",   [(140,23.5,SEAM,2.6),(140,26.2,SEAM,2.6),(139,45,10.3,2.6)], 2.9, True, True, "K"),
    ("upper",     [(112,46,9.4,2.6),(121,45,9.4,2.6),(139,45,10.3,2.6),(146,44,10.3,2.6)], 2.9, True, True, "K"),
    ("eastdrift", [(180,19,SEAM,2.6),(192,16,SEAM,2.6),(198,17,SEAM,2.6)], 2.9, True, True, "K"),
]
RX0, RX1, RY0, RY1, AIS, PITCH = 62.0, 97.0, 31.0, 50.0, 3.0, 8.0
R = [("cage", -4, 0, -2, 2, 0, 3.5, "L"), ("charge", 3, 14, -13, -7, 0, 3.6, "L"), ("comp", 86, 98, -12, -4, 0, 3.6, "D"),
     ("pump", 77, 93, -44, -32, 0, 3.8, "K"), ("goaf", RX0, RX1, RY1 - 0.2, 60, SEAM, 3.4, "K")]
for i, cx in enumerate((62, 70, 78, 86, 94)): R.append(("room_c%d" % i, cx, cx + AIS, RY0, RY1, SEAM, 3.0, "K"))
for i, cy in enumerate((31, 39, 47)): R.append(("room_r%d" % i, RX0, RX1, cy, cy + AIS, SEAM, 3.0, "K"))
PILLARS = [(cx + AIS + 2.5, cy + AIS + 2.5) for cx in (62, 70, 78, 86) for cy in (31, 39)]
POCKETS = [(10,28.2),(32,29),(10,37),(33,38),(22,46),(-2,19),(27,22.2),(58,26.8),(106,26.7),(148,23.2),(172,20.6),
           (67.5,39),(75.5,34),(83.5,42),(91.5,47),(96.5,40),(112,46),(130,46.5),(146,44),(121,38),(198,17),(190,17.6),
           (59.9,13.5),(120,14),(150.5,12),(80,-28.5),(140,-25.6),(97.5,-8),(92.5,-40),(183,-1.2)]
GAP_BIG = [(22,47.5),(80,59),(62,41),(147,45.3),(199,15.6),(85,-44),(171,-23.5),(187,-0.8)]
GAP_SMALL = [(10,29.5),(97,44),(135,-25.5),(5,-13),(119.2,31)]
BLOCKS = [(104,4.8),(104,26.4),(53,-10),(84,8),(20.4,24.5),(90.3,29.5)]
LIT_LAMPS = [(-2,0),(4,0),(12,0),(8,-10),(20,0.2),(28,0.5),(36,0.8),(32,-4.2)]
DEAD_LAMPS = [(48,1.6),(56,2.2),(64,3),(72,3.6),(80,4),(88,4.4),(96,4.8),(29,11),(54,6),(92,-8)]

def seg_len(pts): return sum(math.dist(a[:2], b[:2]) for a, b in zip(pts, pts[1:]))

# ---------------- walkable area (raster 10 px/m, agent radius 0.6)
def area(tunnels, rooms, walk_only=None):
    xs = [p[0] for _, pts in tunnels for p in pts] + [r[0] for r in rooms] + [r[1] for r in rooms]
    ys = [p[1] for _, pts in tunnels for p in pts] + [r[2] for r in rooms] + [r[3] for r in rooms]
    k = 10; x0, y0 = min(xs) - 5, min(ys) - 5
    im = Image.new("1", (int((max(xs) - x0 + 5) * k), int((max(ys) - y0 + 5) * k)), 0); d = ImageDraw.Draw(im)
    P = lambda x, y: ((x - x0) * k, (y - y0) * k)
    for _, pts in tunnels:
        for a, b in zip(pts, pts[1:]):
            w = (a[3] + b[3]) / 2 - 1.2
            if w <= 0: continue
            d.line([P(*a[:2]), P(*b[:2])], fill=1, width=int(w * k))
        for p in pts:
            r = (p[3] - 1.2) / 2 * k; X, Y = P(*p[:2])
            if r > 0: d.ellipse([X - r, Y - r, X + r, Y + r], fill=1)
    for r in rooms:
        a, b = P(r[0] + 0.6, r[2] + 0.6), P(r[1] - 0.6, r[3] - 0.6)
        d.rectangle([a, b], fill=1)
    return sum(im.get_flattened_data()) / (k * k)

m1_area = area(MAP1_T, MAP1_R)
walk2 = [(n, p) for n, p, h, tb, w, lz in T if w]
m2_rooms = [r[1:5] for r in R if not r[0].startswith("goaf")] + [(RX0, RX1, RY1 - 0.2, 55)]
m2_area = area(walk2, m2_rooms)
m1_len = sum(seg_len(p) for _, p in MAP1_T); m2_len = sum(seg_len(p) for n, p, *_ in T)
aisles = 3 * (RX1 - RX0) + 5 * (RY1 - RY0)
print("MAP1: tunnels %.0f m, walkable raster %.0f m2 (Unity navmesh 432)" % (m1_len, m1_area))
print("MAP2: tunnels %.0f m + pillar aisles %.0f m, walkable raster %.0f m2 -> x%.1f" % (m2_len, aisles, m2_area, m2_area / m1_area))
booth_open = [n for n, *_ in T if n in ("station","haulageA","haulageB","siding","charge_a","charge_b","refuge1","comp_pass","xc1","xc2","xc3","seamW","incline","br1W","br1E","br2W","br2E","oldnoburi","pr_a","pr_b")]
bo_len = sum(seg_len(p) for n, p, *_ in T if n in booth_open) + sum(seg_len(p) for n, p, *_ in T if n == "seam") * (104 - 8) / 172 + aisles
bo_area = area([(n, p) for n, p, h, tb, w, lz in T if n in booth_open] + [("seamB", [(8,20,SEAM,3.0),(35,23,SEAM,3.0),(65,26,SEAM,3.0),(95,27,SEAM,3.0),(104,26.4,SEAM,3.0)])],
               [r[1:5] for r in R if r[0] in ("cage", "charge", "comp") or r[0].startswith("room_")] + [(RX0, RX1, RY1 - 0.2, 55)])
print("booth (blocks 1-3 on): ~%.0f m, walkable %.0f m2 -> x%.1f of MAP1" % (bo_len, bo_area, bo_area / m1_area))

# ---------------- drawing
SS = 2; S = 6.4 * SS; OX, OY = 70 * SS, 500 * SS
W, H = 1520, 940
img = Image.new("RGB", (W * SS, H * SS), "#2c2926"); d = ImageDraw.Draw(img)
F = lambda sz, b=False: ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if b else "C:/Windows/Fonts/malgun.ttf", int(sz * SS))
P = lambda x, y: (OX + S * x, OY - S * y)
COL = {"L": "#efd68e", "D": "#d6cdb6", "K": "#aaa290"}
def poly(pts, w, col):
    q = [P(*p[:2]) for p in pts]
    d.line(q, fill=col, width=max(1, int(w * S)), joint="curve")
    for X, Y in q:
        r = w * S / 2; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col)
def rect(x0, x1, y0, y1, col, outline=None):
    a, b = P(x0, y1), P(x1, y0); d.rectangle([a, b], fill=col, outline=outline, width=2 * SS if outline else 0)
def txt(x, y, s, sz=11, anchor="mm", b=False, col="#f4f1ea"): d.text(P(x, y), s, font=F(sz, b), fill=col, anchor=anchor)
def dot(x, y, col, r=4.5):
    X, Y = P(x, y); r *= SS; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col, outline="#1d1b19", width=SS)
def cross(x, y, n):
    X, Y = P(x, y); r = 6 * SS
    d.line([X - r, Y - r, X + r, Y + r], fill="#ffffff", width=3 * SS); d.line([X - r, Y + r, X + r, Y - r], fill="#ffffff", width=3 * SS)
    d.text((X + 9 * SS, Y - 9 * SS), str(n), font=F(11, True), fill="#ffffff", anchor="mm")

for n, x0, x1, y0, y1, fz, h, lz in R:
    if n == "goaf":
        rect(x0, x1, y0, y1, "#4a4540", "#c9c1ad")
        for i in range(int(x0), int(x1), 3):
            d.line([P(i, y0), P(min(i + 6, x1), min(y0 + 6, y1))], fill="#8a826f", width=SS)
    elif not n.startswith("room_"): rect(x0, x1, y0, y1, COL[lz])
for n, pts, h, tb, w, lz in T: poly(pts, pts[0][3], COL[lz])
for n, x0, x1, y0, y1, fz, h, lz in R:
    if n.startswith("room_"): rect(x0, x1, y0, y1, COL[lz])
for cx, cy in PILLARS: rect(cx - 2.5, cx + 2.5, cy - 2.5, cy + 2.5, "#3a3632")
rect(186, 187.8, -5, -1, "#6b6457"); rect(146, 147.5, 42.7, 45.3, "#6b6457"); rect(198, 199.5, 15.7, 18.3, "#6b6457")
rect(117, 119, -9.2, -8, "#7a5a3a")                                          # wind door (sealed)
d.line([P(RX0, RY1 + 0.1), P(RX1, RY1 + 0.1)], fill="#f4f1ea", width=2 * SS)   # fence
for x, y in LIT_LAMPS: dot(x, y, "#fff3b0", 3)
for x, y in DEAD_LAMPS: dot(x, y, "#6e675c", 3)
for x, y in POCKETS: dot(x, y, "#e8892b")
for x, y in GAP_BIG: dot(x, y, "#d33c2c", 5.5)
for x, y in GAP_SMALL: dot(x, y, "#3d7fd6", 5.5)
for i, (x, y) in enumerate(BLOCKS, 1): cross(x, y, i)
dot(-2, 0, "#7fd67f", 6); dot(80, 55, "#b05cc4", 6)

# labels
txt(-2, 4.5, "케이지", 10); txt(8, 5.2, "정거장 6 × 4.5 m", 10); txt(8.5, -16, "축전차 충전실 (문 둘)", 9)
txt(32, -8.2, "지선 — 광차 대기", 9); txt(72, -3.6, "주운반갱 4 × 3.4 m, 170 m", 10)
txt(191, -6.5, "무너짐", 9); txt(92, -14.5, "컴프레서실", 9); txt(85, -47.5, "펌프실", 9)
txt(112, -21.2, "바람길(통기갱도) 3 × 3.2 m", 10); txt(118, -11, "바람 문 (막힘)", 8)
for i, (x, y) in enumerate([(27, 12), (57, 14), (87, 15), (116, 15), (146, 12), (172, 9)], 1): txt(x - 3.5, y, "크로스컷 %d" % i, 9, "rm")
txt(148, 27.5, "연층(탄층 따라) 3 × 3 m, 170 m", 9, "lm")
txt(21, 52, "① 채탄장 — 15° 오름 + 9 m 마다 곁굴", 10); txt(22, 49, "막장 A", 10, b=True)
txt(79.5, 62.8, "② 기둥 사이 35 × 19 m (통로 3 m, 기둥 8)", 10); txt(79.5, 57.5, "탄벽채굴적 — 그것이 사는 곳", 9)
txt(130, 52, "③ 노보리 둘 25° → 위 편 (세로 고리)", 10); txt(112, 49, "막장 C", 10, b=True)
txt(198, 21, "막장 B · 도시락", 10, b=True); txt(49.5, 30, "옛 노보리(철판)", 8)
txt(-4, 23, "막다른 연층", 8)

# title + legend + scale + MAP1 inset (same scale)
d.text((20 * SS, 16 * SS), "한 층(편) 평면도 초안 — MAP2 (지금 맵의 약 5배)", font=F(17, True), fill="#f4f1ea")
d.text((20 * SS, 42 * SS), "크로스컷 여섯이 운반갱과 연층을 이어 고리 다섯 · 바람길로 큰 고리 · 노보리 둘로 위아래 고리. 굴 폭은 MAP1보다 넓게(운반갱 3.3 → 4.0 m, 연층 2.4 → 3.0 m, 기둥 사이 통로 2.1 → 3.0 m)",
       font=F(10.5), fill="#c9c1ad")
d.text((20 * SS, 60 * SS), "굴 합 약 %d m + 기둥 사이 통로 %d m · 걸을 수 있는 바닥 약 %d m² (MAP1 %d m² 의 %.1f 배, 같은 방법으로 잰 값)" % (round(m2_len, -1), aisles, round(m2_area, -1), round(m1_area), m2_area / m1_area),
       font=F(10.5, True), fill="#efd68e")
lx, ly = 110, 705
items = [("#efd68e", "켜진 전등 구역"), ("#d6cdb6", "꺼진 전등 구역"), ("#aaa290", "어둠"), ("#e8892b", "광맥 30"), ("#d33c2c", "큰 틈(괴물) 8"),
         ("#3d7fd6", "작은 틈(플레이어) 5"), ("#7fd67f", "시작(케이지)"), ("#b05cc4", "괴물 시작")]
for i, (c, s) in enumerate(items):
    X, Y = (lx + (i % 2) * 150) * SS, (ly + (i // 2) * 20) * SS
    d.rectangle([X, Y - 6 * SS, X + 12 * SS, Y + 6 * SS], fill=c); d.text((X + 18 * SS, Y), s, font=F(10), fill="#f4f1ea", anchor="lm")
X, Y = lx * SS, (ly + 88) * SS
d.text((X, Y), "X 1~6 부스 막힘 스위치 — 제안: 1·2·3 켬 = 동쪽 절반·바람길 닫힘", font=F(10), fill="#ffffff", anchor="lm")
d.text((X, Y + 18 * SS), "   부스에서 열린 곳 약 %d m · 바닥 %d m² (MAP1 의 %.1f 배)" % (round(bo_len, -1), round(bo_area, -1), bo_area / m1_area), font=F(10), fill="#ffffff", anchor="lm")
sx0, sy = P(0, -52)
d.line([sx0, sy, sx0 + 50 * S, sy], fill="#f4f1ea", width=2 * SS); d.text((sx0 + 25 * S, sy + 12 * SS), "50 m", font=F(10), fill="#f4f1ea", anchor="mm")
# MAP1 inset, same scale, placed lower-left
IX, IY = 103, -50
def Pi(x, y): return P(IX + x, IY - 0 + y)
d.text(Pi(-3, 22), "지금 맵(MAP1), 같은 비율", font=F(10, True), fill="#f4f1ea", anchor="lm")
for _, pts in MAP1_T:
    q = [Pi(*p[:2]) for p in pts]; d.line(q, fill="#8fb3c9", width=max(1, int(pts[0][3] * S)), joint="curve")
for x0, x1, y0, y1 in MAP1_R:
    a, b = Pi(x0, y1), Pi(x1, y0); d.rectangle([a, b], fill="#8fb3c9")
img = img.resize((W, H), Image.LANCZOS); img.save(OUT)
print("saved", OUT)
