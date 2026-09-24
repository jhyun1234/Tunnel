"""MAP2 평면도 초안 v2 + 잰 값 (MAP1 · MAP2 v1 · MAP2 v2 를 같은 방법으로).
  python blender/map/map2_plan.py docs/그림/MAP2_평면도_초안.png
표 형식은 make_booth.py 와 같다: 굴 = (이름, [(x, y, 바닥, 폭)], 천장, 갱목?, 걷는 길?, 빛, 종류). 종류: tunnel · crawl(개구멍, 플레이어만) · niche(좁은 대피소).
재는 것 — 괴물(반지름 0.6 m)이 걷는 바닥으로:
  넓이 · 짧은 고리(한 바퀴 60 m 이하 = 괴물 추격 6.5 m/s 로 9 초 안에 도는 바위 기둥) · 숨을 곳(개구멍 · 좁은 대피소 · 작은 틈) ·
  갈림·숨을 곳 사이 가장 긴 굴(여기서 괴물을 만나면 도망갈 데가 없다)."""
import math, sys
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont

K = 10                     # 칸 / m
VERBOSE = False
R_AGENT = 0.6              # 괴물 반지름 (Tuning.STALKER_R)
LOOP_MAX = 60.0            # 짧은 고리 한 바퀴 (m)

# ======================= MAP1 (지금 맵, make_booth.py)
S1 = 1.0
MAP1 = dict(T=[(n, p, 0, True, True, "K", "tunnel") for n, p in [
    ("station", [(0,0,0,5.0),(8,0,0,5.0)]), ("haulage", [(8,0,0,3.3),(72.5,0,0,3.3)]),
    ("siding", [(9,0,0,3.0),(12,-3.2,0,3.0),(22,-3.2,0,3.0),(25,0,0,3.0)]), ("pump_pass", [(60,0,0,2.4),(60,-3.2,0,2.4)]),
    ("xcut1", [(16,0,0,3.0),(17.21,1.56,0,3.0),(23,9,S1,3.0)]), ("xcut2", [(50,0,0,3.0),(51.09,1.56,0,3.0),(57,10,S1,3.0)]),
    ("xcut3", [(30,0,0,3.0),(35,-6,0,3.0)]), ("door_pass", [(33,-3.6,0,2.4),(28.4,-7.6,0,2.4)]),
    ("noburi", [(35,-6,0,2.4),(41,-7,2.8,2.4),(48,-8.5,6.2,2.4)]), ("seamW1", [(23,9,S1,2.4),(18,10.2,S1,2.4),(13,9.6,S1,2.3)]),
    ("seamW2", [(13,9.6,S1,2.3),(8,11,S1,2.2),(3,11.5,S1,2.1)]), ("stub1", [(18,10.2,S1,2.2),(18.3,14.4,S1,2.2)]),
    ("stub2", [(9,10.8,S1,2.1),(9.6,14.8,S1,2.1)]), ("seamE1", [(23,9,S1,2.4),(28,9.6,S1,2.4),(32.5,9.5,S1,2.4)]),
    ("seamE2", [(47,10,S1,2.4),(52,10.8,S1,2.4),(57,10,S1,2.4),(62,11,S1,2.4),(66,10.6,S1,2.4)])]]
    + [("refuge", [(40,0,0,1.6),(40,-2.6,0,1.6)], 2.2, False, False, "K", "niche")],
    R=[("cage",-3,0,-1.5,1.5,0,3.5,"L"),("pump",57,64,-8,-3,0,3.5,"K")] + [("room_c",cx,cx+2.1,5.0,16.1,S1,2.9,"K") for cx in (32.0,36.5,41.0,45.5)]
      + [("room_r",32.0,47.6,cy,cy+2.1,S1,2.9,"K") for cy in (5.0,9.5,14.0)],
    small_gaps=[(13.0,8.7),(63.3,-7.3)])

# ======================= MAP2 v1 (첫 초안 09-24 — 사용자: "1자가 너무 길다, 마주치면 무조건 잡힌다")
SEAM = 1.5
MAP2_V1 = dict(T=[
    ("station",[(0,0,0,6.0),(16,0,0,6.0)],4.5,False,True,"L","tunnel"), ("haulage",[(16,0,0,4.0),(40,1,0,4.0),(70,3.5,0,4.0),(100,5,0,4.0),(130,3.5,0,4.0),(160,0.5,0,4.0),(186,-3,0,4.0)],3.4,True,True,"D","tunnel"),
    ("siding",[(20,0,0,3.2),(24,-4.2,0,3.2),(40,-4.2,0,3.2),(44,1.3,0,3.2)],3.2,True,True,"L","tunnel"), ("charge_a",[(5,0,0,2.6),(5,-7,0,2.6)],3.0,False,True,"L","tunnel"),
    ("charge_b",[(12,0,0,2.6),(12,-7,0,2.6)],3.0,False,True,"L","tunnel"), ("refuge1",[(62,2.8,0,1.6),(62,-0.8,0,1.6)],2.7,False,False,"D","niche"),
    ("refuge2",[(102,4.9,0,1.6),(102,1.3,0,1.6)],2.7,False,False,"K","niche"), ("refuge3",[(146,1.9,0,1.6),(146,-1.7,0,1.6)],2.7,False,False,"K","niche"),
    ("comp_pass",[(92,4.6,0,2.8),(92,-4,0,2.8)],3.2,False,True,"D","tunnel"), ("air1",[(54,2.2,0,3.0),(52,-26,0,3.0)],3.2,True,True,"K","tunnel"),
    ("airway",[(50,-26,0,3.0),(80,-27,0,3.0),(110,-26,0,3.0),(140,-24,0,3.0),(170,-22,0,3.0)],3.2,True,True,"K","tunnel"),
    ("air3",[(166,-0.2,0,3.0),(168,-22.3,0,3.0)],3.2,True,True,"K","tunnel"), ("door_stub",[(118,4.3,0,2.8),(118,-8,0,2.8)],3.2,True,True,"K","tunnel"),
    ("pump_pass",[(84,-26.9,0,2.8),(84,-32,0,2.8)],3.2,False,True,"K","tunnel"),
    ("xc1",[(24,0.33,0,3.3),(35,23,SEAM,3.3)],3.2,True,True,"D","tunnel"), ("xc2",[(52,2.0,0,3.3),(65,26,SEAM,3.3)],3.2,True,True,"D","tunnel"),
    ("xc3",[(82,4.1,0,3.3),(95,27,SEAM,3.3)],3.2,True,True,"D","tunnel"), ("xc4",[(112,4.4,0,3.3),(125,25,SEAM,3.3)],3.2,True,True,"K","tunnel"),
    ("xc5",[(142,2.3,0,3.3),(155,22,SEAM,3.3)],3.2,True,True,"K","tunnel"), ("xc6",[(168,-0.6,0,3.3),(180,19,SEAM,3.3)],3.2,True,True,"K","tunnel"),
    ("seamW",[(8,20,SEAM,2.4),(-2,19,SEAM,2.4)],2.9,True,True,"K","tunnel"),
    ("seam",[(8,20,SEAM,3.0),(35,23,SEAM,3.0),(65,26,SEAM,3.0),(95,27,SEAM,3.0),(125,25,SEAM,3.0),(155,22,SEAM,3.0),(180,19,SEAM,3.0)],3.0,True,True,"K","tunnel"),
    ("incline",[(20,21.5,SEAM,2.8),(20.6,28.5,3.4,2.8),(21.3,37.4,5.8,2.8),(22,46,8.1,2.8)],2.9,True,True,"K","tunnel"),
    ("br1W",[(20.6,28.5,3.4,2.4),(10,28.2,3.4,2.4)],2.9,True,True,"K","tunnel"), ("br1E",[(20.6,28.5,3.4,2.4),(32,29,3.4,2.4)],2.9,True,True,"K","tunnel"),
    ("br2W",[(21.3,37.4,5.8,2.4),(10,37,5.8,2.4)],2.9,True,True,"K","tunnel"), ("br2E",[(21.3,37.4,5.8,2.4),(33,38,5.8,2.4)],2.9,True,True,"K","tunnel"),
    ("pr_a",[(70,26.2,SEAM,3.0),(70.5,32,SEAM,3.0)],3.0,True,True,"K","tunnel"), ("pr_b",[(90,26.8,SEAM,3.0),(90.5,32,SEAM,3.0)],3.0,True,True,"K","tunnel"),
    ("noburi1",[(120,25.3,SEAM,2.6),(120.3,28,SEAM,2.6),(121,45,9.4,2.6)],2.9,True,True,"K","tunnel"),
    ("noburi2",[(140,23.5,SEAM,2.6),(140,26.2,SEAM,2.6),(139,45,10.3,2.6)],2.9,True,True,"K","tunnel"),
    ("upper",[(112,46,9.4,2.6),(121,45,9.4,2.6),(139,45,10.3,2.6),(146,44,10.3,2.6)],2.9,True,True,"K","tunnel"),
    ("eastdrift",[(180,19,SEAM,2.6),(192,16,SEAM,2.6),(198,17,SEAM,2.6)],2.9,True,True,"K","tunnel")],
    R=[("cage",-4,0,-2,2,0,3.5,"L"),("charge",3,14,-13,-7,0,3.6,"L"),("comp",86,98,-12,-4,0,3.6,"D"),("pump",77,93,-44,-32,0,3.8,"K"),("goaf",62,97,49.8,55,SEAM,3.4,"K")]
      + [("room_c",cx,cx+3,31,50,SEAM,3.0,"K") for cx in (62,70,78,86,94)] + [("room_r",62,97,cy,cy+3,SEAM,3.0,"K") for cy in (31,39,47)],
    small_gaps=[(10,29.5),(97,44),(135,-25.5),(5,-13),(119.2,31)])

# ======================= MAP2 v2 — 어디서든 15 m 안에 갈림이나 숨을 곳, 짧은 고리·숨을 곳 v1 의 2배 넘게
def yH(x):                                   # 주운반갱 가운데 선 (탄층 따라 조금 굽음)
    xs = [14,26,38,50,62,74,86,98,110,122,134,146,152]; ys = [0,0.5,1.5,2,2,1.5,1,0.5,0.5,1,1,0.5,0.5]
    return float(np.interp(x, xs, ys))
RUNGS = [26,38,50,62,74,86,98,110,122,134,146]             # 운반갱 ↔ 나란한 사람길 연락갱 12 m 마다
yP = lambda x: yH(x) - 10.0                               # 나란한 사람길(인도) = 운반갱 남쪽 10 m
SX = [0,12,24,36,48,60,72,84,96,108,120,132,144]; SY = [27,30,27,30,27,30,27,30,27,30,27,30,27]   # 연층: 12 m 마다 28° 꺾임
yS = lambda x: float(np.interp(x, SX, SY))
def lit(x): return "L" if x < 38 else "D" if x < 98 else "K"
T2 = [("station",[(0,0,0,6.0),(14,0,0,6.0)],4.5,False,True,"L","tunnel"),
      ("charge_a",[(5,0,0,2.6),(5,-7,0,2.6)],3.0,False,True,"L","tunnel"), ("charge_b",[(11,0,0,2.6),(11,-7,0,2.6)],3.0,False,True,"L","tunnel")]
HX = [14,26,38,50,62,74,86,98,110,122,134,146,152]
for a, b in zip(HX, HX[1:]): T2.append(("haul_%d" % a, [(a,yH(a),0,4.0),(b,yH(b),0,4.0)], 3.4, True, True, lit(a), "tunnel"))
PX = [20] + RUNGS + [152]
for a, b in zip(PX, PX[1:]): T2.append(("path_%d" % a, [(a,yP(a),0,3.0),(b,yP(b),0,3.0)], 3.2, True, True, lit(a), "tunnel"))
for x in RUNGS: T2.append(("rung_%d" % x, [(x,yH(x),0,3.0),(x,yP(x),0,3.0)], 3.2, True, True, lit(x), "tunnel"))
T2 += [("pump_pass",[(62,yP(62),0,2.8),(62,-16,0,2.8)],3.2,False,True,"D","tunnel"),
       ("comp_pass",[(102,yP(102),0,2.8),(102,-15,0,2.8)],3.2,False,True,"K","tunnel")]
for i, (x0, xb, xs) in enumerate([(30,38,36),(66,74,72),(102,110,108),(138,146,144)], 1):   # 크로스컷: 가운데서 꺾인다 (곧게 25 m 를 안 본다)
    T2.append(("xc%d" % i, [(x0,yH(x0),0,3.3),(xb,13,0.7,3.3),(xs,yS(xs),SEAM,3.3)], 3.2, True, True, "D" if i <= 2 else "K", "tunnel"))
T2 += [("seam",[(-6,26,SEAM,2.6)] + [(x,y,SEAM,3.0) for x, y in zip(SX, SY)],3.0,True,True,"K","tunnel"),
       ("eastdrift",[(144,27,SEAM,2.6),(152,29,SEAM,2.6),(158,33,SEAM,2.6)],2.9,True,True,"K","tunnel")]
zW = lambda y: SEAM + (y - 31) * math.tan(math.radians(15))                   # 채탄장 15° 오르막
T2 += [("incline",[(14,yS(14),SEAM,2.8),(14,31,SEAM,2.8),(14,58,zW(58),2.8)],2.9,True,True,"K","tunnel")]
for y in (36, 45, 54): T2.append(("branch_%d" % y, [(3,y,zW(y),2.4),(25,y,zW(y),2.4)], 2.9, True, True, "K", "tunnel"))
for x in (3, 25): T2.append(("backW_%d" % x, [(x,36,zW(36),2.4),(x,54,zW(54),2.4)], 2.9, True, True, "K", "tunnel"))
RX0, RY0, AIS, PITCH, NC, NR = 44.0, 33.0, 3.0, 9.0, 4, 3                      # 기둥 사이: 기둥 6 × 6 m, 4 × 3 = 12개
RX1, RY1 = RX0 + NC * PITCH + AIS, RY0 + NR * PITCH + AIS
for x in (RX0 + 1.5, RX0 + 3 * PITCH + 1.5, RX0 + 4 * PITCH + 1.5):          # 연층 → 기둥 사이 통로 셋
    T2.append(("pr_%d" % x, [(x,yS(x),SEAM,3.0),(x,RY0 + 1,SEAM,3.0)], 3.0, True, True, "K", "tunnel"))
zN = lambda y: SEAM + (y - 31.5) * math.tan(math.radians(25))                 # 노보리 25°
for x in (102, 114, 126): T2.append(("noburi_%d" % x, [(x,yS(x),SEAM,2.6),(x,31.5,SEAM,2.6),(x,47,zN(47),2.6)], 2.9, True, True, "K", "tunnel"))
T2.append(("upper",[(94,48,zN(47),2.6),(134,48,zN(47),2.6)],2.9,True,True,"K","tunnel"))
T2.append(("mid_39",[(102,39,zN(39),2.6),(126,39,zN(39),2.6)],2.9,True,True,"K","tunnel"))   # 노보리 셋의 가운데를 잇는 굴 (같은 기울기라 같은 높이) — 오르막 18 m 를 반으로
# 개구멍 (0.9 × 1.3 m — 숙여서 기어 지나감, 괴물 못 지나감): 두 굴을 바위 속으로 잇는다
CRAWL = [("c_pillar44",[(44,yH(44)),(44,yP(44))]), ("c_pillar80",[(80,yH(80)),(80,yP(80))]), ("c_pillar116",[(116,yH(116)),(116,yP(116))]),
         ("c_charge",[(13,-10),(20,yP(20))]), ("c_pump",[(68,-16),(68,yP(68))]), ("c_comp",[(106,-15),(106,yP(106))]),
         ("c_room",[(RX0 + 2 * PITCH + 1.5,yS(RX0 + 2 * PITCH + 1.5)),(RX0 + 2 * PITCH + 1.5,RY0 + 1)]), ("c_west",[(22,yS(22)),(22,36)])]
for n, pts in CRAWL: T2.append((n, [(x, y, 0, 0.9) for x, y in pts], 1.3, False, False, "K", "crawl"))
# 좁은 대피소 (폭 1.1 × 높이 2.2 × 깊이 2.4 m — 사람은 서서 들어가고 괴물(1.2 m)은 못 들어감)
def niche(x, y, dx, dy, w): return [(x + dx * w / 2, y + dy * w / 2, 0, 1.1), (x + dx * (w / 2 + 2.4), y + dy * (w / 2 + 2.4), 0, 1.1)]
NICHES = [niche(x, yH(x), 0, 1, 4.0) for x in (56, 92, 128)] + [niche(x, yP(x), 0, -1, 3.0) for x in (44, 116)] \
       + [niche(x, yS(x), 0, -1, 3.0) for x in (54, 90, 135)] + [niche(150, 29.3, 0.45, -0.9, 2.6)] + [niche(4, yS(4), 0, 1, 3.0)]
for x0, xb, xs in [(30,38,36),(66,74,72),(102,110,108),(138,146,144)]:        # 크로스컷 두 다리 가운데마다
    for ((ax, ay), (bx, by)), f in zip([((x0, yH(x0)), (xb, 13)), ((xb, 13), (xs, yS(xs)))], (2 / 3, 1 / 3)):   # 꺾임 가까이 — 조각이 12 m 를 안 넘게
        mx, my = ax + (bx - ax) * f, ay + (by - ay) * f; L = math.hypot(bx - ax, by - ay); nx, ny = (by - ay) / L, -(bx - ax) / L
        NICHES.append(niche(mx, my, nx, ny, 3.3))
for i, pts in enumerate(NICHES): T2.append(("niche_%d" % i, pts, 2.2, False, False, "K", "niche"))
R2 = [("cage",-4,0,-2,2,0,3.5,"L"), ("charge",3,13,-13,-7,0,3.6,"L"), ("pump",56,70,-24,-16,0,3.8,"D"), ("comp",96,108,-22,-15,0,3.6,"K"),
      ("goaf",RX0,RX1,RY1 - 0.2,RY1 + 7,SEAM,3.4,"K")]
R2 += [("room_c",RX0 + i * PITCH,RX0 + i * PITCH + AIS,RY0,RY1,SEAM,3.0,"K") for i in range(NC + 1)]
R2 += [("room_r",RX0,RX1,RY0 + j * PITCH,RY0 + j * PITCH + AIS,SEAM,3.0,"K") for j in range(NR + 1)]
PILLARS = [(RX0 + AIS + i * PITCH + 3, RY0 + AIS + j * PITCH + 3) for i in range(NC) for j in range(NR)]
MAP2_V2 = dict(T=T2, R=R2, small_gaps=[(RX0 - 0.2, 36), (-6.5, 27.5)])
POCKETS = [(14,58.5),(3,49),(25,40),(8,55.3),(20,43.7),(-6,26),(50,42),(62,48),(68,54),(74,39),(59,60),(RX1,50),(30,28.4),(60,31.5),(96,25.5),
           (120,25.5),(140,29.7),(94,48),(108,49.3),(120,46.7),(133,48),(158,33.5),(150,30.5),(70,3.8),(110,-1.5),(56,-11.3),(130,-11),(70,-20),(96,-18),(35,6.5)]
GAP_BIG = [(14,59.5),(RX0 + 19.5,RY1 + 7),(RX0,50),(134.5,48),(159,34.5),(63,-24),(153,-9.5),(152.5,0.5)]
BLOCKS = [(92,yH(92)),(92,yP(92)),(87,yS(87)),(70,7),(14,33),(RX0 + 4 * PITCH + 1.5,31.8)]
LIT_LAMPS = [(-2,0),(4,0),(10,0),(8,-10),(20,yH(20)),(30,yH(30)),(26,yP(26)),(36,yH(36))]
DEAD_LAMPS = [(44,yH(44)),(56,yH(56)),(68,yH(68)),(80,yH(80)),(92,yH(92)),(44,yP(44)),(68,yP(68)),(92,yP(92)),(34,7),(70,7)]

# ======================= 재기
def seg_len(pts): return sum(math.dist(a[:2], b[:2]) for a, b in zip(pts, pts[1:]))
def raster(m, shrink, kinds=("tunnel",), walk_only=True, box=(-12, 205, -50, 75)):
    x0, x1, y0, y1 = box
    im = Image.new("L", (int((x1 - x0) * K), int((y1 - y0) * K)), 0); d = ImageDraw.Draw(im)
    P = lambda x, y: ((x - x0) * K, (y1 - y) * K)
    for n, pts, h, tb, walk, lz, kind in m["T"]:
        if kind not in kinds or (walk_only and not walk): continue
        for a, b in zip(pts, pts[1:]):
            w = (a[3] + b[3]) / 2 - 2 * shrink
            if w > 0: d.line([P(*a[:2]), P(*b[:2])], fill=255, width=max(1, int(round(w * K))))
        for p in pts:
            r = (p[3] - 2 * shrink) / 2 * K; X, Y = P(*p[:2])
            if r > 0: d.ellipse([X - r, Y - r, X + r, Y + r], fill=255)
    for n, rx0, rx1, ry0, ry1, fz, h, lz in m["R"]:
        if n == "goaf": ry1 = min(ry1, ry0 + 5)                               # 채굴적은 앞쪽만 걸음
        d.rectangle([P(rx0 + shrink, ry1 - shrink), P(rx1 - shrink, ry0 + shrink)], fill=255)
    return np.array(im) > 0

def measure(m):
    walk = raster(m, R_AGENT)
    area = walk.sum() / K ** 2
    lab, n = ndimage.label(~walk)                                            # 바위 덩어리들 — 바깥과 이어지지 않은 것 = 둘레를 돌 수 있는 기둥
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    loops = []
    for i in range(1, n + 1):
        if i in border: continue
        isl = lab == i
        ring = ndimage.binary_dilation(isl) & walk
        per = ring.sum() / K * 0.9                                           # 둘레 칸 수 → m (대각선 보정 대략)
        loops.append(per)
    small = sum(1 for p in loops if p <= LOOP_MAX)
    hides = sum(1 for t in m["T"] if t[6] in ("crawl", "niche")) + len(m["small_gaps"])
    # 갈림·숨을 곳 사이 가장 긴 굴: 걷는 굴마다, 다른 굴·방·숨을 곳 입구가 닿는 자리로 자른다
    walkT = [t for t in m["T"] if t[4]]
    others = [t for t in m["T"] if t[6] != "tunnel" or t[4]]
    def proj(pts, q):
        best = (1e9, 0.0); s0 = 0.0
        for a, b in zip(pts, pts[1:]):
            A, B = np.array(a[:2]), np.array(b[:2]); d = B - A; L = np.linalg.norm(d)
            t = max(0.0, min(1.0, float(np.dot(q - A, d) / max(L * L, 1e-9)))); dist = np.linalg.norm(q - (A + d * t))
            if dist < best[0]: best = (dist, s0 + t * L)
            s0 += L
        return best
    def in_room(q): return any(r[1] - 0.5 <= q[0] <= r[2] + 0.5 and r[3] - 0.5 <= q[1] <= r[4] + 0.5 for r in m["R"])
    longest, longest_at, dead_longest = 0.0, "", 0.0
    for n, pts, h, tb, wk, lz, kind in walkT:
        L = seg_len(pts); ev = []
        for end, s in ((pts[0], 0.0), (pts[-1], L)):
            q = np.array(end[:2]); hit = in_room(q)
            for o in others:
                if o[0] != n and proj(o[1], q)[0] < o[1][0][3] / 2 + 0.6: hit = True
            ev.append((s, hit))
        for o in others:
            if o[0] == n: continue
            for end in (o[1][0], o[1][-1]):
                dist, s = proj(pts, np.array(end[:2]))
                if dist < pts[0][3] / 2 + 0.8 and 0.3 < s < L - 0.3: ev.append((s, True))
            s0 = 0.0                                                          # 가운데서 엇갈리는 굴 (채탄장 오르막 × 곁굴)
            for a, b in zip(pts, pts[1:]):
                A, B = np.array(a[:2]), np.array(b[:2]); dA = B - A
                for c, e in zip(o[1], o[1][1:]):
                    C, E = np.array(c[:2]), np.array(e[:2]); dC = E - C; den = dA[0] * dC[1] - dA[1] * dC[0]
                    if abs(den) < 1e-9: continue
                    t = ((C[0] - A[0]) * dC[1] - (C[1] - A[1]) * dC[0]) / den; u = ((C[0] - A[0]) * dA[1] - (C[1] - A[1]) * dA[0]) / den
                    if 0 < t < 1 and 0 < u < 1: ev.append((s0 + t * np.linalg.norm(dA), True))
                s0 += np.linalg.norm(dA)
        ev.sort()
        for (s0, j0), (s1, j1) in zip(ev, ev[1:]):
            piece = s1 - s0
            if piece > 15 and VERBOSE: print("   15 m 넘음: %s %.1f → %.1f (%.0f m)%s" % (n, s0, s1, piece, "" if j0 and j1 else " 막다른"))
            if j0 and j1:
                if piece > longest: longest, longest_at = piece, n
            elif piece > dead_longest: dead_longest = piece
    tl = sum(seg_len(t[1]) for t in m["T"] if t[6] == "tunnel")
    return dict(area=area, small=small, loops=len(loops), hides=hides, longest=longest, at=longest_at, dead=dead_longest, length=tl)

M = {}
for k, v in (("MAP1", MAP1), ("v1", MAP2_V1), ("v2", MAP2_V2)):
    VERBOSE = k == "v2"; M[k] = measure(v)
VERBOSE = False
for k, r in M.items():
    print("%-4s 굴 %4.0f m · 바닥 %5.0f m² (MAP1 의 %.1f 배) · 짧은 고리(≤%d m) %2d / 고리 %2d · 숨을 곳 %2d · 갈림·숨을 곳 사이 가장 긴 굴 %.0f m (%s) · 막다른 굴 가장 긴 것 %.0f m"
          % (k, r["length"], r["area"], r["area"] / M["MAP1"]["area"], LOOP_MAX, r["small"], r["loops"], r["hides"], r["longest"], r["at"], r["dead"]))
BOOTH_CLOSED_X = 90.0                                                          # 스위치 1·2·3 = x 87~92 에서 동쪽을 닫는다
booth = dict(T=[t for t in T2 if all(p[0] <= BOOTH_CLOSED_X for p in t[1])] + [t for t in T2 if t[0] == "seam"], R=[r for r in R2 if r[2] <= BOOTH_CLOSED_X + 1], small_gaps=MAP2_V2["small_gaps"])
booth["T"] = [(n, [p for p in pts if p[0] <= BOOTH_CLOSED_X] if n == "seam" else pts, *rest) for n, pts, *rest in booth["T"]]
MB = measure(booth)
print("부스판(1·2·3 켬) 굴 %.0f m · 바닥 %.0f m² (MAP1 의 %.1f 배) · 짧은 고리 %d · 숨을 곳 %d" % (MB["length"], MB["area"], MB["area"] / M["MAP1"]["area"], MB["small"], MB["hides"]))

# ======================= 그림
if len(sys.argv) > 1:
    OUT = sys.argv[1]; SS = 2; S = 7.4 * SS; OX, OY = 80 * SS, 715 * SS; W, H = 1400, 1140
    img = Image.new("RGB", (W * SS, H * SS), "#2c2926"); d = ImageDraw.Draw(img)
    F = lambda sz, b=False: ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if b else "C:/Windows/Fonts/malgun.ttf", int(sz * SS))
    P = lambda x, y: (OX + S * x, OY - S * y)
    COL = {"L": "#efd68e", "D": "#d6cdb6", "K": "#aaa290"}; HIDE = "#3d8fe0"; CRAWL_C = "#9ff0ff"
    def poly(pts, w, col):
        q = [P(*p[:2]) for p in pts]; d.line(q, fill=col, width=max(1, int(w * S)), joint="curve")
        for X, Y in q: r = w * S / 2; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col)
    def rect(x0, x1, y0, y1, col, outline=None): d.rectangle([P(x0, y1), P(x1, y0)], fill=col, outline=outline, width=2 * SS if outline else 0)
    def txt(x, y, s, sz=11, anchor="mm", b=False, col="#f4f1ea"): d.text(P(x, y), s, font=F(sz, b), fill=col, anchor=anchor)
    def dot(x, y, col, r=4.5): X, Y = P(x, y); r *= SS; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col, outline="#1d1b19", width=SS)
    def cross(x, y, n):
        X, Y = P(x, y); r = 6 * SS
        d.line([X - r, Y - r, X + r, Y + r], fill="#ffffff", width=3 * SS); d.line([X - r, Y + r, X + r, Y - r], fill="#ffffff", width=3 * SS)
        d.text((X + 9 * SS, Y - 9 * SS), str(n), font=F(11, True), fill="#ffffff", anchor="mm")
    for n, x0, x1, y0, y1, fz, h, lz in R2:
        if n == "goaf":
            rect(x0, x1, y0, y1, "#4a4540", "#c9c1ad")
            for i in range(int(x0), int(x1), 3): d.line([P(i, y0), P(min(i + 6, x1), min(y0 + 6, y1))], fill="#8a826f", width=SS)
        elif not n.startswith("room_"): rect(x0, x1, y0, y1, COL[lz])
    for n, pts, h, tb, w, lz, kind in T2:
        if kind == "tunnel": poly(pts, pts[0][3], COL[lz])
    for n, x0, x1, y0, y1, fz, h, lz in R2:
        if n.startswith("room_"): rect(x0, x1, y0, y1, COL[lz])
    for cx, cy in PILLARS: rect(cx - 3, cx + 3, cy - 3, cy + 3, "#3a3632")
    for n, pts, h, tb, w, lz, kind in T2:
        if kind == "crawl":
            (ax, ay), (bx, by) = pts[0][:2], pts[-1][:2]; L = math.hypot(bx - ax, by - ay); t = 0.0
            while t < L:                                                      # 점선 = 기어서 지나가는 구멍
                t1 = min(t + 0.9, L); d.line([P(ax + (bx - ax) * t / L, ay + (by - ay) * t / L), P(ax + (bx - ax) * t1 / L, ay + (by - ay) * t1 / L)], fill=CRAWL_C, width=int(0.9 * S)); t += 1.5
        if kind == "niche": poly(pts, 1.1, HIDE)
    for x, y in MAP2_V2["small_gaps"]: dot(x, y, HIDE, 5)
    rect(152, 153.6, -1.5, 2.5, "#6b6457"); rect(134, 135.5, 46.7, 49.3, "#6b6457"); rect(152, 153.4, -11, -8, "#7a5a3a")
    d.line([P(RX0, RY1 + 0.1), P(RX1, RY1 + 0.1)], fill="#f4f1ea", width=2 * SS)
    for x, y in LIT_LAMPS: dot(x, y, "#fff3b0", 3)
    for x, y in DEAD_LAMPS: dot(x, y, "#6e675c", 3)
    for x, y in POCKETS: dot(x, y, "#e8892b", 4)
    for x, y in GAP_BIG: dot(x, y, "#d33c2c", 5.5)
    for i, (x, y) in enumerate(BLOCKS, 1): cross(x, y, i)
    dot(-2, 0, "#7fd67f", 6); dot(RX0 + 30, RY1 + 3.5, "#b05cc4", 6)
    txt(-2, 4.2, "케이지", 10); txt(7, 5, "정거장", 10); txt(8, -16, "충전실(문 둘)", 9)
    txt(118, 6.2, "주운반갱 4 m", 10); txt(129, -13.6, "나란한 사람길 3 m — 12 m 마다 연락갱", 10)
    txt(63, -27, "펌프실", 9); txt(102, -25, "컴프레서실", 9); txt(157, -12.5, "바람 문(막힘)", 8); txt(158, 4.5, "무너짐", 9)
    for i, (x, y) in enumerate([(36, 13), (72, 13), (108, 13), (144, 13)], 1): txt(x + 4.5, y + 1.5, "크로스컷 %d" % i, 9, "lm")
    txt(-8, 23.3, "연층 — 12 m 마다 꺾임", 9, "lm"); txt(14, 64, "① 채탄장 15° — 곁굴을 뒤에서 이어 고리 넷", 10); txt(14, 61, "막장 A", 10, b=True)
    txt(RX0 + 19.5, RY1 + 10.5, "② 기둥 사이 — 기둥 12개, 통로 3 m", 10); txt(RX0 + 19.5, RY1 + 6.5, "채굴적 — 그것이 사는 곳", 9)
    txt(114, 55, "③ 노보리 셋 25° → 위 굴 (위아래 고리 둘)", 10); txt(94, 51, "막장 C", 10, "mm", True); txt(162, 36.5, "막장 B", 10, "lm", True)
    d.text((20 * SS, 14 * SS), "한 층 평면도 초안 v2 — MAP2 (도망칠 길·숨을 곳을 늘린 판)", font=F(17, True), fill="#f4f1ea")
    r1, r2, r0 = M["v1"], M["v2"], M["MAP1"]
    lines = [("짧은 고리(한 바퀴 60 m 이하, 괴물 추격으로 9 초)  v1 %d → v2 %d 개 (%.1f 배)" % (r1["small"], r2["small"], r2["small"] / r1["small"]), "#efd68e"),
             ("숨을 곳(개구멍·좁은 대피소·작은 틈)  v1 %d → v2 %d 곳 (%.1f 배)" % (r1["hides"], r2["hides"], r2["hides"] / r1["hides"]), "#8fd0ff"),
             ("갈림·숨을 곳 없이 이어지는 가장 긴 굴  v1 %.0f m → v2 %.0f m" % (r1["longest"], r2["longest"]), "#f4f1ea"),
             ("걸을 수 있는 바닥 %.0f m² (지금 맵의 %.1f 배) · 부스판(1·2·3 켬) %.0f m² (%.1f 배)" % (r2["area"], r2["area"] / r0["area"], MB["area"], MB["area"] / r0["area"]), "#c9c1ad")]
    for i, (s, c) in enumerate(lines): d.text((20 * SS, (42 + i * 19) * SS), s, font=F(11.5, i < 3), fill=c)
    lx, ly = 640, 930
    items = [("#efd68e", "켜진 전등 구역"), ("#d6cdb6", "꺼진 전등 구역"), ("#aaa290", "어둠"), (HIDE, "좁은 대피소(사람만 들어감)"), (CRAWL_C, "개구멍 — 숙여서 기어 지나감(사람만)"),
             ("#e8892b", "광맥 30"), ("#d33c2c", "큰 틈(괴물) 8"), ("#7fd67f", "시작"), ("#b05cc4", "괴물 시작")]
    for i, (c, s) in enumerate(items):
        X, Y = (lx + (i % 2) * 260) * SS, (ly + (i // 2) * 21) * SS
        d.rectangle([X, Y - 6 * SS, X + 12 * SS, Y + 6 * SS], fill=c); d.text((X + 18 * SS, Y), s, font=F(10.5), fill="#f4f1ea", anchor="lm")
    d.text((lx * SS, (ly + 112) * SS), "X 1~6 부스 막힘 스위치 — 제안: 1·2·3 켬 = 동쪽(크로스컷 3·4, 노보리, 막장 B) 닫힘", font=F(10.5), fill="#ffffff", anchor="lm")
    IX, IY = -5, -45                                                          # 지금 맵(MAP1), 같은 비율
    d.text(P(IX - 3, IY + 19), "지금 맵(MAP1) — 같은 비율", font=F(10.5, True), fill="#8fb3c9", anchor="lm")
    for n, pts, *_ in MAP1["T"]:
        d.line([P(IX + p[0], IY + p[1]) for p in pts], fill="#8fb3c9", width=max(1, int(pts[0][3] * S)), joint="curve")
    for n, rx0, rx1, ry0, ry1, *_ in MAP1["R"]: d.rectangle([P(IX + rx0, IY + ry1), P(IX + rx1, IY + ry0)], fill="#8fb3c9")
    sx0, sy = P(76, -50.5); d.line([sx0, sy, sx0 + 50 * S, sy], fill="#f4f1ea", width=2 * SS); d.text((sx0 + 25 * S, sy + 12 * SS), "50 m", font=F(10), fill="#f4f1ea", anchor="mm")
    img.resize((W, H), Image.LANCZOS).save(OUT); print("saved", OUT)
