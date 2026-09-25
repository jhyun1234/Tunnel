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

# ======================= MAP2 v3 — 케이지를 한가운데로: 큰 고리가 전부 정거장을 지난다 (사용자 09-24 "계속 돌아다니면 결국 원점, 미로처럼 보여도 출구는 하나")
# 실제 도면 이름 "좌운반갱"(= 케이지 왼쪽 운반갱)처럼 케이지 양쪽으로 운반갱을 낸다. 바람은 케이지 굴로 들어와 안쪽으로 분다(바람을 거슬러 가면 케이지).
def interp(xs, ys): return lambda x: float(np.interp(x, xs, ys))
yH3 = lambda x: interp([-86,-80,-68,-56,-44,-32,-20,-8,8,20,32,44,56,68,80,86], [0.5,0.5,1,1.5,2,1.5,0.5,0,0,0.5,1,1.5,2,1.5,1,1])(x)
yP3 = lambda x: yH3(x) - 12.0                                      # 사람길 = 운반갱 남쪽 12 m (가운데는 케이지 방 밑을 지난다)
SX3 = [-80 + 12 * i for i in range(14)] + [80]; SY3 = [27 if i % 2 == 0 else 30 for i in range(14)] + [29]
yS3 = interp(SX3, SY3)
def lit3(x): return "L" if abs(x) < 24 else "D" if abs(x) < 52 else "K"
T3 = []                                                                    # 정거장 = 케이지 앞 광장(방). 굴 8개가 여기로 모인다
for xs in ([-10,-20,-32,-44,-56,-68,-80,-86], [10,20,32,44,56,68,80,86]):
    for a, b in zip(xs, xs[1:]): T3.append(("haul_%d" % a, [(a,yH3(a),0,4.0),(b,yH3(b),0,4.0)], 3.4, True, True, lit3(a), "tunnel"))
RUNGS3 = [-80,-68,-56,-44,-32,-20,20,32,44,56,68,80]
for side in (-1, 1):
    xs = [x for x in RUNGS3 if x * side > 0]; xs = sorted(xs, key=abs)
    T3.append(("path_in%d" % side, [(side * 10,-6,0,3.0),(xs[0],yP3(xs[0]),0,3.0)], 3.2, True, True, "L", "tunnel"))   # 사람길도 광장으로
    for a, b in zip(xs, xs[1:]): T3.append(("path_%d" % a, [(a,yP3(a),0,3.0),(b,yP3(b),0,3.0)], 3.2, True, True, lit3(a), "tunnel"))
for x in RUNGS3: T3.append(("rung_%d" % x, [(x,yH3(x),0,3.0),(x,yP3(x),0,3.0)], 3.2, True, True, lit3(x), "tunnel"))
XC3 = [(-80,-86,-80,None), (-40,-48,-44,None), (-7,-14,-20,(-7,4)), (0,4,2,(0,4)), (7,14,20,(7,4)), (40,48,44,None), (80,86,80,None)]   # (운반갱 x, 꺾는 x, 연층 x, 광장에서 시작)
for i, (x0, xb, xs, st) in enumerate(XC3):
    a = st if st else (x0, yH3(x0))
    T3.append(("xc%d" % i, [(a[0],a[1],0,3.3),(xb,14,0.7,3.3),(xs,yS3(xs),SEAM,3.3)], 3.2, True, True, "D" if abs(x0) < 52 else "K", "tunnel"))
T3.append(("seam", [(x, y, SEAM, 3.0) for x, y in zip(SX3, SY3)], 3.0, True, True, "K", "tunnel"))
T3.append(("eastdrift", [(80,29,SEAM,2.6),(88,33,SEAM,2.6),(94,37,SEAM,2.6)], 2.9, True, True, "K", "tunnel"))
zW3 = lambda y: SEAM + (y - 31) * math.tan(math.radians(15))
T3.append(("incline", [(-67,yS3(-67),SEAM,2.8),(-67,31,SEAM,2.8),(-67,58,zW3(58),2.8)], 2.9, True, True, "K", "tunnel"))
for y in (36, 45, 54): T3.append(("branch_%d" % y, [(-78,y,zW3(y),2.4),(-56,y,zW3(y),2.4)], 2.9, True, True, "K", "tunnel"))
for x in (-78, -56): T3.append(("back_%d" % x, [(x,36,zW3(36),2.4),(x,54,zW3(54),2.4)], 2.9, True, True, "K", "tunnel"))
RX0_3, RY0_3 = -19.5, 33.0; RX1_3, RY1_3 = RX0_3 + NC * PITCH + AIS, RY0_3 + NR * PITCH + AIS
for x in (RX0_3 + 1.5, RX0_3 + 4 * PITCH + 1.5): T3.append(("pr_%d" % x, [(x,yS3(x),SEAM,3.0),(x,RY0_3 + 1,SEAM,3.0)], 3.0, True, True, "K", "tunnel"))
zN3 = lambda y: SEAM + (y - 31.5) * math.tan(math.radians(25))
for x in (50, 62, 74): T3.append(("noburi_%d" % x, [(x,yS3(x),SEAM,2.6),(x,31.5,SEAM,2.6),(x,47,zN3(47),2.6)], 2.9, True, True, "K", "tunnel"))
T3.append(("mid_39", [(50,39,zN3(39),2.6),(74,39,zN3(39),2.6)], 2.9, True, True, "K", "tunnel"))
T3.append(("upper", [(42,48,zN3(47),2.6),(82,48,zN3(47),2.6)], 2.9, True, True, "K", "tunnel"))
T3 += [("charge_pass",[(-27,yP3(-27),0,2.8),(-27,-18,0,2.8)],3.2,False,True,"L","tunnel"), ("pump_pass",[(0,-8,0,2.8),(0,-20,0,2.8)],3.2,False,True,"L","tunnel"),
       ("comp_pass",[(27,yP3(27),0,2.8),(27,-18,0,2.8)],3.2,False,True,"D","tunnel")]
FAKE = [(-86,yH3(-86),0,3.0),(-92,0.5,0,3.0),(-112,-2,20 * math.tan(math.radians(25)),3.0)]   # 가짜 출구: 올라가는 사갱 + "갱구" 표지판, 끝은 무너짐
T3.append(("fake_exit", FAKE, 3.2, True, True, "K", "tunnel"))
CRAWL3 = [("c_%d" % x, [(x, yH3(x)), (x, yP3(x))]) for x in (-74, -50, -26, 26, 50, 74)] + \
         [("c_charge", [(-23,-18),(-23,yP3(-23))]), ("c_pump", [(6,-20),(13,-7)]), ("c_comp", [(31,-18),(31,yP3(31))]),
          ("c_room", [(0.5,yS3(0.5)),(0.5,RY0_3 + 1)]), ("c_west", [(-59,yS3(-59)),(-59,36)])]
for n, pts in CRAWL3: T3.append((n, [(x, y, 0, 0.9) for x, y in pts], 1.3, False, False, "K", "crawl"))
NICH3 = [niche(x, yH3(x), 0, 1, 4.0) for x in (-62, -26, 26, 62)] + [niche(x, yP3(x), 0, -1, 3.0) for x in (-38, 38, -74, 74)] \
      + [niche(x, yS3(x), 0, -1, 3.0) for x in (-62, -52, -35, -26, -9, 10, 26, 35, 58)] + [niche(86, 32, 0.45, -0.9, 2.6)]
for x0, xb, xs, st in XC3:
    for ((ax, ay), (bx, by)), f in zip([(st if st else (x0, yH3(x0)), (xb, 14)), ((xb, 14), (xs, yS3(xs)))], (2 / 3, 1 / 3)):
        mx, my = ax + (bx - ax) * f, ay + (by - ay) * f; L = math.hypot(bx - ax, by - ay); nx, ny = (by - ay) / L, -(bx - ax) / L
        NICH3.append(niche(mx, my, nx, ny, 3.3))
for f in (0.35, 0.7):                                                     # 가짜 출구 비탈에도
    (ax, ay), (bx, by) = FAKE[1][:2], FAKE[2][:2]; mx, my = ax + (bx - ax) * f, ay + (by - ay) * f; L = math.hypot(bx - ax, by - ay)
    NICH3.append(niche(mx, my, (by - ay) / L, -(bx - ax) / L, 3.0))
for i, pts in enumerate(NICH3): T3.append(("niche_%d" % i, pts, 2.2, False, False, "K", "niche"))
R3 = [("plaza",-10,10,-8,4,0,4.5,"L"), ("charge",-32,-22,-26,-18,0,3.6,"L"), ("pump",-7,7,-30,-20,0,3.8,"L"), ("comp",22,32,-26,-18,0,3.6,"D"),
      ("goaf",RX0_3,RX1_3,RY1_3 - 0.2,RY1_3 + 7,SEAM,3.4,"K")]
R3 += [("room_c",RX0_3 + i * PITCH,RX0_3 + i * PITCH + AIS,RY0_3,RY1_3,SEAM,3.0,"K") for i in range(NC + 1)]
R3 += [("room_r",RX0_3,RX1_3,RY0_3 + j * PITCH,RY0_3 + j * PITCH + AIS,SEAM,3.0,"K") for j in range(NR + 1)]
MAP2_V3 = dict(T=T3, R=R3, small_gaps=[(RX0_3 - 0.2, 36), (RX1_3 + 0.2, 45)], home_rooms=("plaza",), home_rect=(-10, 10, -8, 4),
               pillars=[(RX0_3 + AIS + i * PITCH + 3, RY0_3 + AIS + j * PITCH + 3) for i in range(NC) for j in range(NR)])
MAP2_V2.update(home_rooms=("cage",), home_rect=(-4, 14, -3, 3))              # v2: 케이지 + 정거장
V3_MARK = dict(
    pockets=[(-67,58.5),(-78,49),(-56,40),(-72,55.3),(-62,43.7),(-80,25.4),(-10,42),(3,48),(9,54),(15,39),(0,60),(RX1_3,50),(-50,28.4),(-20,31.5),(20,25.5),
             (46,25.5),(60,31.5),(42,48),(56,49.3),(68,46.7),(82,48),(94,37.5),(88,34.5),(-38,3.6),(38,3.6),(-60,-11),(60,-11),(-27,-22),(27,-22),(-66,8)],
    gap_big=[(-67,59.5),(0,RY1_3 + 7),(RX0_3,50),(82.5,48),(95,38.5),(0,-30),(-113,-2),(86.5,1)],
    blocks=[(1,(-50,yH3(-50))),(1,(-50,yP3(-50))),(1,(-47,yS3(-47))),(2,(50,yH3(50))),(2,(50,yP3(50))),(2,(47,yS3(47))),(3,(RX0_3 + 1.5,31.8)),(3,(RX1_3 - 1.5,31.8)),(3,(0.5,31.8))],
    lit=[(-6,0),(6,0),(-14,yH3(-14)),(14,yH3(14)),(0,-25),(-27,-22),(-14,yP3(-14)),(14,yP3(14))],
    dead=[(-26,yH3(-26)),(-38,yH3(-38)),(-50,yH3(-50)),(26,yH3(26)),(38,yH3(38)),(50,yH3(50)),(-38,yP3(-38)),(38,yP3(38)),(4,8),(27,-22)],
    spawn=(0,-5), monster=(10,RY1_3 + 3.5))

# ======================= 재기
def seg_len(pts): return sum(math.dist(a[:2], b[:2]) for a, b in zip(pts, pts[1:]))
def bbox(m):
    xs = [p[0] for t in m["T"] for p in t[1]] + [r[1] for r in m["R"]] + [r[2] for r in m["R"]]
    ys = [p[1] for t in m["T"] for p in t[1]] + [r[3] for r in m["R"]] + [r[4] for r in m["R"]]
    return min(xs) - 6, max(xs) + 6, min(ys) - 6, max(ys) + 6
def raster(m, shrink, kinds=("tunnel",), walk_only=True):
    x0, x1, y0, y1 = bbox(m)
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

def proj(pts, q):
    best = (1e9, 0.0); s0 = 0.0
    for a, b in zip(pts, pts[1:]):
        A, B = np.array(a[:2]), np.array(b[:2]); d = B - A; L = np.linalg.norm(d)
        t = max(0.0, min(1.0, float(np.dot(q - A, d) / max(L * L, 1e-9)))); dist = np.linalg.norm(q - (A + d * t))
        if dist < best[0]: best = (dist, s0 + t * L)
        s0 += L
    return best
def point_at(pts, s):
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a[:2], b[:2])
        if s <= L + 1e-9: t = s / max(L, 1e-9); return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        s -= L
    return pts[-1][:2]
def room_of(m, q):
    for r in m["R"]:
        if r[1] - 0.5 <= q[0] <= r[2] + 0.5 and r[3] - 0.5 <= q[1] <= r[4] + 0.5: return "pillar_room" if r[0] in ("room_c", "room_r", "goaf") else r[0]
    return None

def route_events(m, routes, others):
    """booth_table.route_events 와 같은 것 (한 곳에만)"""
    return bt.route_events(m["T"], m["R"], routes, others)

def wander(m, runs=3000, cap=3000.0, seed=1, limit=300.0):
    """길 잃은 사람: 맵 아무 데서나 시작해 되돌아서지 않고 갈림마다 아무 쪽이나 골라 계속 걷는다(개구멍도 지나감, 막다른 곳에서만 돌아선다).
    정거장(케이지 앞)에 닿을 때까지 걸은 거리."""
    routes = [t for t in m["T"] if t[4] or t[6] == "crawl" or (t[6] == "crevice" and m.get("through") and t[0] in m["through"])]   # 뚫린 바위 틈도 사람 길
    ev = route_events(m, routes, routes)
    nodes, pos, npos = {}, [], {}
    def node(q):
        r = room_of(m, q)
        if r: k = nodes.setdefault(r, len(nodes)); npos.setdefault(k, (r, q)); return k
        for k, (x, y) in enumerate(pos):
            if math.dist((x, y), q) < 2.5: return nodes[("p", k)]
        pos.append(q); k = nodes.setdefault(("p", len(pos) - 1), len(nodes)); npos[k] = (None, q); return k
    adj = {}
    for n, pts, *_ in routes:
        ids = [node(point_at(pts, s)) for s, _ in ev[n]]
        for (s0, _), (s1, _), a, b in zip(ev[n], ev[n][1:], ids, ids[1:]):
            if a != b and s1 - s0 > 0.05: adj.setdefault(a, []).append((b, s1 - s0)); adj.setdefault(b, []).append((a, s1 - s0))
    hx0, hx1, hy0, hy1 = m["home_rect"]
    home = {k for k, (r, q) in npos.items() if r in m["home_rooms"] or (hx0 <= q[0] <= hx1 and hy0 <= q[1] <= hy1)}
    edges = [(a, b, L) for a, lst in adj.items() for b, L in lst if a not in home and b not in home]
    w = np.array([e[2] for e in edges]); w /= w.sum()
    rng = np.random.default_rng(seed); dists = []
    for _ in range(runs):
        a, b, L = edges[rng.choice(len(edges), p=w)]
        prev, cur, d = a, b, L * rng.random()                              # 굴 한가운데 어딘가에서 시작
        while d < cap and cur not in home:
            opts = [e for e in adj[cur] if e[0] != prev] or adj[cur]
            nxt, L = opts[rng.integers(len(opts))]
            prev, cur, d = cur, nxt, d + L
        dists.append(d)
    dists = np.array(dists)
    return dict(within300=float((dists <= 300).mean() * 100), within=float((dists <= limit).mean() * 100), median=float(np.median(dists)),
                deadends=sum(1 for k, v in adj.items() if len(v) == 1 and k not in home), hubdeg=max(len(adj[k]) for k in home))

def measure(m, limit=300.0):
    walk = raster(m, R_AGENT)
    area = walk.sum() / K ** 2
    lab, n = ndimage.label(~walk)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    loops = [(ndimage.binary_dilation(lab == i) & walk).sum() / K * 0.9 for i in range(1, n + 1) if i not in border]
    hides = sum(1 for t in m["T"] if t[6] in ("crawl", "niche", "crevice")) + len(m["small_gaps"])   # 바위 틈(R2b)도 숨을 곳
    walkT = [t for t in m["T"] if t[4]]; others = [t for t in m["T"] if t[6] != "tunnel" or t[4]]
    ev = route_events(m, walkT, others)
    longest, longest_at, dead_longest, dead_at = 0.0, "", 0.0, ""
    for n_, e in ev.items():
        for (s0, j0), (s1, j1) in zip(e, e[1:]):
            piece = s1 - s0
            if VERBOSE and piece > 15: print("   15 m 넘음: %s %.0f m%s" % (n_, piece, "" if j0 and j1 else " 막다른"))
            if j0 and j1:
                if piece > longest: longest, longest_at = piece, n_
            elif piece > dead_longest: dead_longest, dead_at = piece, n_
    tl = sum(seg_len(t[1]) for t in m["T"] if t[6] == "tunnel")
    r = dict(area=area, small=sum(1 for p in loops if p <= LOOP_MAX), loops=len(loops), hides=hides, longest=longest, at=longest_at,
             dead=dead_longest, dead_at=dead_at, length=tl)
    if "home_rect" in m: r.update(wander(m, limit=limit))
    return r


# ======================= MAP2 v4 — 사용자 손그림(09-24). 표는 booth_table.py 한 곳에 (make_booth.py 도 같은 것을 읽는다)
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import booth_table as bt
B4 = bt.build()
m_ = bt.m_
MAP2_V4 = dict(T=B4["T"], R=B4["R"], small_gaps=[g[:2] for g in B4["gap_small"]], home_rooms=("plaza",), home_rect=B4["home_rect"])
PIL4 = B4["PILLARS"]; Z1 = tuple(B4["Z"]["Z1"][k] for k in ("x0", "x1", "y0", "y1")); Z3 = tuple(B4["Z"]["Z3"][k] for k in ("x0", "x1", "y0", "y1"))
FAKE4 = next(t for t in B4["T"] if t[0] == "fake_exit")[1]
NA = sum(1 for t in B4["T"] if t[6] == "niche")
V4_MARK = dict(gap_big=[g[:2] for g in B4["gap_big"]], blocks=[(b[0], b[1:3]) for b in B4["blocks"]], monster=B4["spawn_stalker"][:2])

# ======================= 결과
if __name__ == "__main__":                 # 불러 쓸 때(booth_gen.py)는 재기 함수만
    M = {}
    for k, v in (("MAP1", MAP1), ("v1", MAP2_V1), ("v2", MAP2_V2), ("v3", MAP2_V3), ("v4", MAP2_V4)):
        VERBOSE = k == "v4"; M[k] = measure(v)
    VERBOSE = False
    for k, r in M.items():
        print("%-4s 굴 %4.0f m · 바닥 %5.0f m² (%.1f 배) · 짧은 고리 %2d · 숨을 곳 %2d · 갈림 없는 가장 긴 굴 %2.0f m (%s) · 막다른 굴 %2.0f m (%s)"
              % (k, r["length"], r["area"], r["area"] / M["MAP1"]["area"], r["small"], r["hides"], r["longest"], r["at"], r["dead"], r["dead_at"])
              + ("" if "median" not in r else " · 길 잃고 300 m 안에 정거장 %.0f %% · 가운데값 %.0f m · 정거장에 모이는 굴 %d" % (r["within300"], r["median"], r["hubdeg"])))
    print("v4 자동 대피소 %d" % NA)
    def drop(m, prefixes, room_boxes=()):
        keep = lambda n: not any(n.startswith(p) for p in prefixes)
        T = [t for t in m["T"] if keep(t[0])]
        R = [r for r in m["R"] if not any(bx0 - 0.5 <= r[1] and r[2] <= bx1 + 0.5 and by0 - 0.5 <= r[3] and r[4] <= by1 + 6 for bx0, bx1, by0, by1 in room_boxes)]
        walk = [t for t in T if t[4]]; mm = dict(R=R)
        def attached(q): return room_of(mm, q) is not None or any(proj(o[1], np.array(q))[0] < o[1][0][3] / 2 + 0.6 for o in walk)
        T = [t for t in T if t[4] or (t[6] == "niche" and attached(t[1][0][:2])) or (t[6] == "crawl" and attached(t[1][0][:2]) and attached(t[1][-1][:2]))]   # 닫힌 굴에 붙은 대피소·개구멍은 뺀다
        return dict(T=T, R=R, small_gaps=m["small_gaps"], home_rooms=m["home_rooms"], home_rect=m["home_rect"])
    BOOTH4 = drop(MAP2_V4, ("W_", "E_", "T_", "fake", "sd_arc", "sd_edge", "link12", "link23", "v_z1", "v_z3", "c_z1", "c_link12"), (Z1, Z3))
    MB = measure(BOOTH4)
    print("부스판(묶음 1·2 켬 = 양쪽 위 구역·바깥 고리 닫힘) 굴 %.0f m · 바닥 %.0f m² (%.1f 배) · 짧은 고리 %d · 숨을 곳 %d · 길 잃고 300 m 안에 정거장 %.0f %%"
          % (MB["length"], MB["area"], MB["area"] / M["MAP1"]["area"], MB["small"], MB["hides"], MB["within300"]))

    # ======================= 그림 (v4)
    if len(sys.argv) > 1:
        m, mk = MAP2_V4, V4_MARK
        OUT = sys.argv[1]; SS = 2; S = 8.5 * SS; OX, OY = 750 * SS, 720 * SS; W, H = 1500, 1300
        img = Image.new("RGB", (W * SS, H * SS), "#2c2926"); d = ImageDraw.Draw(img)
        Fn = lambda sz, b=False: ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if b else "C:/Windows/Fonts/malgun.ttf", int(sz * SS))
        P = lambda x, y: (OX + S * x, OY - S * y)
        COL = {"L": "#efd68e", "D": "#d6cdb6", "K": "#aaa290"}; HIDE = "#3d8fe0"; CRAWL_C = "#9ff0ff"
        def poly(pts, w, col):
            q = [P(*p[:2]) for p in pts]; d.line(q, fill=col, width=max(1, int(w * S)), joint="curve")
            for X, Y in q: r = w * S / 2; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col)
        def rect(x0, x1, y0, y1, col, outline=None): d.rectangle([P(x0, y1), P(x1, y0)], fill=col, outline=outline, width=2 * SS if outline else 0)
        def txt(x, y, s, sz=11, anchor="mm", b=False, col="#f4f1ea"): d.text(P(x, y), s, font=Fn(sz, b), fill=col, anchor=anchor)
        def dot(x, y, col, r=4.5): X, Y = P(x, y); r *= SS; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col, outline="#1d1b19", width=SS)
        def cross(x, y, n):
            X, Y = P(x, y); r = 6 * SS
            d.line([X - r, Y - r, X + r, Y + r], fill="#ffffff", width=3 * SS); d.line([X - r, Y + r, X + r, Y - r], fill="#ffffff", width=3 * SS)
            d.text((X + 9 * SS, Y - 9 * SS), str(n), font=Fn(11, True), fill="#ffffff", anchor="mm")
        for n, x0, x1, y0, y1, fz, h, lz in m["R"]:
            if n == "goaf":
                rect(x0, x1, y0, y1, "#4a4540", "#c9c1ad")
                for i in range(int(x0), int(x1), 3): d.line([P(i, y0), P(min(i + 5, x1), min(y0 + 5, y1))], fill="#8a826f", width=SS)
            elif not n.startswith("room_"): rect(x0, x1, y0, y1, COL[lz])
        for n, pts, h, tb, w, lz, kind in m["T"]:
            if kind == "tunnel": poly(pts, pts[0][3], COL[lz])
        for n, x0, x1, y0, y1, fz, h, lz in m["R"]:
            if n.startswith("room_"): rect(x0, x1, y0, y1, COL[lz])
        for x0, x1, y0, y1 in PIL4: rect(x0, x1, y0, y1, "#3a3632")
        cx0, cy1 = m_(870, 690); cx1, cy0 = m_(950, 735); rect(cx0, cx1, cy0, cy1, "#7fd67f"); txt((cx0 + cx1) / 2, (cy0 + cy1) / 2, "케이지", 9, b=True, col="#1d1b19")
        for n, pts, h, tb, w, lz, kind in m["T"]:
            if kind == "crawl":
                (ax, ay), (bx, by) = pts[0][:2], pts[-1][:2]; L = math.hypot(bx - ax, by - ay); t = 0.0
                while t < L:
                    t1 = min(t + 0.9, L); d.line([P(ax + (bx - ax) * t / L, ay + (by - ay) * t / L), P(ax + (bx - ax) * t1 / L, ay + (by - ay) * t1 / L)], fill=CRAWL_C, width=int(0.9 * S)); t += 1.5
            if kind == "niche": poly(pts, 1.1, HIDE)
        for x, y in m["small_gaps"]: dot(x, y, HIDE, 5)
        fx, fy = FAKE4[-1][:2]; rect(fx - 1.6, fx + 1.6, fy - 0.2, fy + 1.4, "#6b6457")
        for x, y in mk["gap_big"]: dot(x, y, "#d33c2c", 6)
        for g, (x, y) in mk["blocks"]: cross(x, y, g)
        dot(*mk["monster"], "#b05cc4", 6)
        lab = [(m_(370, 60), "① 채탄장 15°"), (m_(930, 75), "② 기둥 사이 · 채굴적"), (m_(1510, 125), "③ 노보리 25°"), (m_(1050, 575), "정거장 광장"),
               (m_(1150, 490), "큰길"), (m_(1000, -35), "맨 위 활 굴 (위 편)"), (m_(410, 1215), "충전실"), (m_(910, 1245), "펌프실"), (m_(1360, 1240), "컴프레서실"),
               (m_(225, 675), "작은 기둥 방"), (m_(1650, 680), "작은 기둥 방")]
        for (x, y), s in lab: txt(x, y, s, 10.5, b=True)
        fx2, fy2 = FAKE4[-1][:2]; txt(fx2 + 2, fy2 + 3.5, "가짜 출구 — 더 올라가는 사갱, 끝 무너짐", 10, "lm", True, "#ff9c7a")
        d.text((20 * SS, 14 * SS), "한 층 평면도 초안 v4 — 사용자 손그림을 옮김 (케이지 가운데 · 바깥 고리 · 위 구역 셋)", font=Fn(17, True), fill="#f4f1ea")
        r3, r4, r0 = M["v3"], M["v4"], M["MAP1"]
        lines = [("길 잃고 아무 데서나 계속 걸으면 300 m 안에 정거장  v3 %.0f %% → v4 %.0f %% · 걸은 거리 가운데값 %.0f → %.0f m" % (r3["within300"], r4["within300"], r3["median"], r4["median"]), "#7fd67f"),
                 ("짧은 고리(한 바퀴 60 m 이하)  v3 %d → v4 %d개   ·   숨을 곳  v3 %d → v4 %d곳 (대피소는 긴 굴에 12.5 m 마다 자동)" % (r3["small"], r4["small"], r3["hides"], r4["hides"]), "#efd68e"),
                 ("갈림·숨을 곳 없이 이어지는 가장 긴 굴 %.0f m · 막다른 굴 %.0f m · 바닥 %.0f m² (지금 맵의 %.1f 배) · 부스판(1·2) %.1f 배" % (r4["longest"], r4["dead"], r4["area"], r4["area"] / r0["area"], MB["area"] / r0["area"]), "#f4f1ea")]
        for i, (s, c) in enumerate(lines): d.text((20 * SS, (42 + i * 19) * SS), s, font=Fn(11.5, i < 2), fill=c)
        lx, ly = 1030, 1150
        items = [("#efd68e", "켜진 전등 구역"), ("#d6cdb6", "꺼진 전등 구역"), ("#aaa290", "어둠"), (HIDE, "좁은 대피소"), (CRAWL_C, "개구멍(기어서)"),
                 ("#d33c2c", "큰 틈(괴물) 8"), ("#7fd67f", "케이지(출구)"), ("#b05cc4", "괴물 시작")]
        for i, (c, s) in enumerate(items):
            X, Y = (lx + (i % 2) * 230) * SS, (ly + (i // 2) * 21) * SS
            d.rectangle([X, Y - 6 * SS, X + 12 * SS, Y + 6 * SS], fill=c); d.text((X + 18 * SS, Y), s, font=Fn(10.5), fill="#f4f1ea", anchor="lm")
        d.text((lx * SS, (ly + 90) * SS), "X 부스 막힘 묶음: 1 서쪽 · 2 동쪽 (둘 다 켜면 가운데만)", font=Fn(10.5), fill="#ffffff", anchor="lm")
        sx0, sy = P(-80, -52); d.line([sx0, sy, sx0 + 30 * S, sy], fill="#f4f1ea", width=2 * SS); d.text((sx0 + 15 * S, sy + 12 * SS), "30 m", font=Fn(10), fill="#f4f1ea", anchor="mm")
        img.resize((W, H), Image.LANCZOS).save(OUT); print("saved", OUT)
