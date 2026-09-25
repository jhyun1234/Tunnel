"""부스 맵 MAP2 v4 표 — 사용자 손그림(09-24)을 옮긴 것. 제안서 docs/제안서_MAP2_맵_5배.md (09-24 승인).
make_booth.py(Blender)와 map2_plan.py(평면도·잰 값)가 둘 다 이 파일을 읽는다 — 표는 여기 한 곳에만.
좌표: 평면도 (x, y) = Blender (X, Y), 높이 z. 단위 m. 손그림 픽셀 (px, py) → m_(): 케이지 = 그림 (910, 660), F m/픽셀.
굴 = (이름, [(x, y, 바닥 z, 폭)], 천장 높이, 갱목?, 걷는 길?, 빛 L·D·K, 종류 tunnel·crawl·niche)
방 = (이름, x0, x1, y0, y1, 바닥, 천장, 빛)   — room_c/room_r 는 기둥 사이 통로(겹친 상자들), goaf = 채굴적
numpy 만 쓴다(Blender 안에서도 돈다)."""
import math
import numpy as np

SEAM = 1.5                  # 위 구역 바닥
MAINZ = 0.5                 # 큰길 바닥 (광장 0 → 조금 오른다)
F = 0.07                    # m / 손그림 픽셀
CX, CY = 910, 660           # 케이지 자리 (손그림 픽셀)
NICHE_W, NICHE_H, NICHE_D = 1.0, 2.2, 2.4       # 좁은 대피소: 사람(지름 0.8)은 서서, 괴물(1.2)은 못 들어감 — 복셀이 ±0.1 m 흔들어도 1.2 밑
CRAWL_W, CRAWL_H = 0.9, 1.3                     # 개구멍: 숙여서 기어 지나감 (서면 1.7 m 라 못 선다)
LANDING = 2.6               # 비탈 중간 갈림의 평평한 받침 길이
# R2b 바위 틈 (제안서 docs/제안서_R2b_바위틈_비집기.md, 승인 09-24) — 차례 3(자리·모양 보이기)까지는 build(crevices=True) 로만 켠다
CREV_W, CREV_H, CREV_ZIG = 0.46, 2.3, 0.15     # 틈 폭(파내는 폭 — 벽 잡음이 0~0.06 m 씩 넓혀 0.46~0.58 · 사람이 몸을 옆으로 돌려 지남, 괴물 1.2 m 는 못 들어감) · 높이 · 가운데 선 지그재그
CREV_SLIT, CREV_ROOM, CREV_HIDE = 1.6, 1.6, 2.6  # 막힌 틈: 좁은 틈 길이 · 안쪽 방 폭 · 숨는 자리(입구 벽에서) — 괴물 팔 1.6 m 가 안 닿는다


def m_(px, py): return ((px - CX) * F, (CY - py) * F)
def seg_len(pts): return sum(math.dist(a[:2], b[:2]) for a, b in zip(pts, pts[1:]))
def point_at(pts, s):
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a[:2], b[:2])
        if s <= L + 1e-9:
            t = s / max(L, 1e-9); return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        s -= L
    return tuple(pts[-1][:2])
def proj(pts, q):
    """(거리, 굴 따라 자리 s, 그 자리 바닥 z)"""
    best = (1e9, 0.0, 0.0); s0 = 0.0; q = np.asarray(q[:2], float)
    for a, b in zip(pts, pts[1:]):
        A, B = np.array(a[:2], float), np.array(b[:2], float); d = B - A; L = float(np.linalg.norm(d))
        t = max(0.0, min(1.0, float(np.dot(q - A, d) / max(L * L, 1e-9)))); dist = float(np.linalg.norm(q - (A + d * t)))
        if dist < best[0]: best = (dist, s0 + t * L, a[2] + (b[2] - a[2]) * t)
        s0 += L
    return best
def room_of(R, q):
    for r in R:
        if r[1] - 0.5 <= q[0] <= r[2] + 0.5 and r[3] - 0.5 <= q[1] <= r[4] + 0.5:
            return "pillar_room" if r[0] in ("room_c", "room_r", "goaf") else r[0]
    return None
def room_floor(R, q):
    for r in R:
        if r[1] - 0.5 <= q[0] <= r[2] + 0.5 and r[3] - 0.5 <= q[1] <= r[4] + 0.5: return r[5]
    return None
def near_room(q, margin, R=None):
    return any(r[1] - margin <= q[0] <= r[2] + margin and r[3] - margin <= q[1] <= r[4] + margin for r in (R if R is not None else _R))
_R = []
def floor_z(T, R, q):
    """(x, y) 의 바닥 높이 — 방 안이면 방 바닥, 아니면 가장 가까운 걷는 굴"""
    z = room_floor(R, q)
    if z is not None: return z
    return min((proj(t[1], q) for t in T if t[4]), key=lambda p: p[0])[2]


def route_events(T, R, routes, others):
    """굴마다 [(자리 s, 갈림?)] — 끝이 다른 굴·방에 닿는가, 다른 굴 끝·숨을 곳 입구가 닿는 자리, 엇갈리는 자리"""
    out = {}
    for n, pts, *_ in routes:
        L = seg_len(pts); ev = []
        for end, s in ((pts[0], 0.0), (pts[-1], L)):
            hit = room_of(R, end) is not None or any(o[0] != n and proj(o[1], end)[0] < o[1][0][3] / 2 + 0.6 for o in others)
            ev.append((s, hit))
        for o in others:
            if o[0] == n: continue
            for end in (o[1][0], o[1][-1]):
                dist, s, _ = proj(pts, end)
                if dist < pts[0][3] / 2 + 0.8 and 0.3 < s < L - 0.3: ev.append((s, True))
            s0 = 0.0
            for a, b in zip(pts, pts[1:]):
                A, B = np.array(a[:2]), np.array(b[:2]); dA = B - A
                for c, e in zip(o[1], o[1][1:]):
                    C, E = np.array(c[:2]), np.array(e[:2]); dC = E - C; den = dA[0] * dC[1] - dA[1] * dC[0]
                    if abs(den) < 1e-9: continue
                    t = ((C[0] - A[0]) * dC[1] - (C[1] - A[1]) * dC[0]) / den; u = ((C[0] - A[0]) * dA[1] - (C[1] - A[1]) * dA[0]) / den
                    sx = s0 + t * float(np.linalg.norm(dA))
                    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9 and 0.3 < sx < L - 0.3: ev.append((sx, True))   # 꺾는 점에서 엇갈려도 센다
                s0 += float(np.linalg.norm(dA))
        out[n] = sorted(ev)
    return out


def niche_pts(x, y, z, nx, ny, w, depth=None):
    """굴 벽에서 옆으로 파 들어간 좁은 대피소 — 굴 안 0.6 m 에서 시작(겹쳐야 이어진다)"""
    a, b = w / 2 - 0.6, w / 2 + (depth or NICHE_D)
    return [(x + nx * a, y + ny * a, z, NICHE_W), (x + nx * b, y + ny * b, z, NICHE_W)]


def build(crevices=False):
    T, R, PIL = [], [], []
    def pl(name, pxs, w, h, z, lz, kind="tunnel", walk=True, timber=True):
        zs = z if isinstance(z, list) else [z] * len(pxs)
        return (name, [(*m_(px, py), zz, w) for (px, py), zz in zip(pxs, zs)], h, timber, walk, lz, kind)
    def box(name, px0, px1, py0, py1, fz, h, lz):
        (x0, y1), (x1, y0) = m_(px0, py0), m_(px1, py1); return (name, x0, x1, y0, y1, fz, h, lz)

    # ---- 가운데: 정거장 광장(케이지 앞) · 큰길 · 광장에서 나가는 굴 다섯 · 아래 불 켜진 길과 방 셋
    R += [box("plaza", 800, 1020, 598, 738, 0, 4.5, "L"), box("charge", 300, 520, 1070, 1190, 0, 3.6, "L"),
          box("pump", 790, 1030, 1090, 1225, 0, 3.8, "L"), box("comp", 1240, 1480, 1105, 1215, 0, 3.6, "L")]
    T.append(pl("main", [(55,522),(205,520),(400,520),(585,528),(925,528),(1115,535),(1465,540),(1540,535),(1665,522),(1855,515)], 4.0, 3.4, MAINZ, "D"))
    T += [pl("link_nw", [(800,640),(700,620),(640,580),(585,528)], 3.3, 3.2, [0,0.15,0.35,MAINZ], "L"),
          pl("link_ne", [(1020,650),(1100,620),(1115,580),(1115,535)], 3.3, 3.2, [0,0.15,0.35,MAINZ], "L"),
          pl("link_e", [(990,712),(1100,740),(1250,735),(1400,700),(1460,620),(1465,540)], 3.3, 3.2, [0,0,0,0,0.25,MAINZ], "D"),
          pl("link_w", [(810,690),(670,690),(520,710),(430,740),(345,775)], 3.3, 3.2, [0,0,0.1,0.2,0.3], "D"),
          pl("south", [(910,738),(925,920)], 3.3, 3.2, 0, "L"),
          pl("south_pump", [(925,920),(915,1090)], 3.0, 3.2, 0, "L"),
          pl("south_w", [(925,920),(790,930),(500,930),(365,957)], 3.0, 3.2, 0, "L"),
          pl("south_e", [(925,920),(1120,915),(1250,945),(1340,1050),(1352,1105)], 3.0, 3.2, 0, "L"),
          pl("to_charge", [(365,957),(390,1070)], 3.0, 3.2, 0, "L"),
          pl("bottom_w", [(20,945),(205,952),(365,960)], 3.0, 3.2, 0, "K"),
          pl("bottom_e", [(1245,952),(1630,948),(1940,945)], 3.0, 3.2, 0, "K")]

    # ---- 넓은 구역: 기둥 사이(상자 통로) · 채탄장·노보리(비탈 굴 격자, 갈림마다 평평한 받침)
    def zone_grid(px0, px1, py0, py1, nc, nr, fz, lz, a=3.0):
        (x0, y1), (x1, y0) = m_(px0, py0), m_(px1, py1)
        px = (x1 - x0 - a) / nc; py = (y1 - y0 - a) / nr
        R.extend([("room_c", x0 + i * px, x0 + i * px + a, y0, y1, fz, 3.0, lz) for i in range(nc + 1)])
        R.extend([("room_r", x0, x1, y0 + j * py, y0 + j * py + a, fz, 3.0, lz) for j in range(nr + 1)])
        PIL.extend([(x0 + a + i * px, x0 + (i + 1) * px, y0 + a + j * py, y0 + (j + 1) * py) for i in range(nc) for j in range(nr)])
        return dict(x0=x0, x1=x1, y0=y0, y1=y1, cx=[x0 + i * px + a / 2 for i in range(nc + 1)], cy=[y0 + j * py + a / 2 for j in range(nr + 1)], z=fz)
    def zone_slope(tag, px0, px1, py0, py1, slope_deg, colf, rowf, wc, wr, lz):
        (x0, y1), (x1, y0) = m_(px0, py0), m_(px1, py1)
        xs = [x0 + (x1 - x0) * f for f in colf]; ys = [y0 + (y1 - y0) * f for f in rowf]
        tn = math.tan(math.radians(slope_deg)); zs = [SEAM]
        for a, b in zip(ys, ys[1:]): zs.append(zs[-1] + max(0.0, b - a - LANDING) * tn)
        for i, x in enumerate(xs):
            pts = []
            for k, (y, z) in enumerate(zip(ys, zs)):
                if k > 0: pts.append((x, y - LANDING / 2, z, wc))
                pts.append((x, y, z, wc))
                if k < len(ys) - 1: pts.append((x, y + LANDING / 2, z, wc))
            T.append(("%s_col%d" % (tag, i), pts, 2.9, True, True, lz, "tunnel"))
        for j, (y, z) in enumerate(zip(ys, zs)):
            T.append(("%s_row%d" % (tag, j), [(xs[0], y, z, wr), (xs[-1], y, z, wr)], 2.9, True, True, lz, "tunnel"))
        return dict(x0=x0, x1=x1, y0=y0, y1=y1, xs=xs, ys=ys, zs=zs)
    Z1 = zone_slope("W_z1", 240, 500, 105, 385, 15, (0.06, 0.5, 0.94), (0.05, 0.37, 0.63, 0.95), 2.6, 2.4, "K")   # ① 채탄장
    Z2 = zone_grid(770, 1090, 110, 390, 3, 2, SEAM, "K")                                                          # ② 기둥 사이 (기둥 6)
    R.append(("goaf", Z2["x0"], Z2["x1"], Z2["y1"] - 0.2, Z2["y1"] + 5.5, SEAM, 3.4, "K"))                         # 채굴적 — 그것이 사는 곳
    Z3 = zone_slope("E_z3", 1375, 1650, 160, 390, 25, (0.06, 0.5, 0.94), (0.06, 0.5, 0.94), 2.6, 2.6, "K")          # ③ 노보리
    Z4 = zone_grid(100, 345, 705, 832, 2, 1, 0.3, "K")                                                            # 아래 작은 기둥 방
    Z5 = zone_grid(1545, 1752, 700, 822, 2, 1, 0.3, "K")

    def at(px, py, z, w): return (*m_(px, py), z, w)
    T += [("v_z1", [at(400,520,MAINZ,3.0), (m_(400,0)[0], Z1["ys"][0], SEAM, 3.0)], 3.2, True, True, "K", "tunnel"),
          ("v_z2", [at(925,528,MAINZ,3.0), (m_(925,0)[0], Z2["y0"] + 1.5, SEAM, 3.0)], 3.2, True, True, "K", "tunnel"),
          ("v_z3", [at(1540,535,MAINZ,3.0), (m_(1540,0)[0], Z3["ys"][0], SEAM, 3.0)], 3.2, True, True, "K", "tunnel"),
          ("v_z4a", [at(205,520,MAINZ,3.0), (m_(205,0)[0], Z4["y1"] - 1.5, 0.3, 3.0)], 3.2, True, True, "K", "tunnel"),
          ("v_z4b", [(m_(205,0)[0], Z4["y0"] + 1.5, 0.3, 3.0), at(205,952,0,3.0)], 3.2, True, True, "K", "tunnel"),
          ("v_z5a", [at(1665,522,MAINZ,3.0), (m_(1665,0)[0], Z5["y1"] - 1.5, 0.3, 3.0)], 3.2, True, True, "K", "tunnel"),
          ("v_z5b", [(m_(1615,0)[0], Z5["y0"] + 1.5, 0.3, 3.0), at(1630,948,0,3.0)], 3.2, True, True, "K", "tunnel"),
          # ①–② 두 줄(손그림) = 채탄장 가운데 두 줄 곁굴 높이에서 기둥 사이로 내려간다
          ("link12a", [(Z1["xs"][2], Z1["ys"][2], Z1["zs"][2], 2.8), (Z2["x0"] + 1.5, Z1["ys"][2], SEAM, 2.8)], 3.0, True, True, "K", "tunnel"),
          ("link12b", [(Z1["xs"][2], Z1["ys"][1], Z1["zs"][1], 2.8), (Z2["x0"] + 1.5, Z1["ys"][1], SEAM, 2.8)], 3.0, True, True, "K", "tunnel"),
          ("link23", [(Z2["x1"] - 1.5, Z3["ys"][1], SEAM, 2.8), (Z3["xs"][0], Z3["ys"][1], Z3["zs"][1], 2.8)], 3.0, True, True, "K", "tunnel")]
    # 맨 위 활 굴 = 위 편: 채탄장 꼭대기 → 가운데 평평 → 노보리 가운데 줄로 내려온다
    za, zb = Z1["zs"][-1], Z3["zs"][1]; zt = za + 0.4
    arc_px = [(300,55),(600,18),(1000,10),(1400,30),(1700,90),(1765,160),(1760,210),(1700,260)]
    arc_z = [za + 0.2, zt, zt, zt, zt, zt - 0.4 * (zt - zb), zt - 0.7 * (zt - zb), zb]
    T.append(("T_arc", [(Z1["xs"][0], Z1["ys"][-1], za, 3.0)] + [at(px, py, z, 3.0) for (px, py), z in zip(arc_px, arc_z)] + [(Z3["xs"][2], Z3["ys"][1], zb, 3.0)],
              3.0, True, True, "K", "tunnel"))
    c1 = (Z1["xs"][0], Z1["ys"][0], SEAM, 2.6); c3 = (Z3["xs"][2], Z3["ys"][0], SEAM, 2.6)
    T += [("W_spur", [c1] + [at(px, py, SEAM, 2.6) for px, py in [(150,380),(40,390),(22,383)]], 2.9, True, True, "K", "tunnel"),
          ("E_spur", [c3] + [at(px, py, SEAM, 2.6) for px, py in [(1750,352),(1900,282),(1925,270)]], 2.9, True, True, "K", "tunnel"),
          ("W_edge", [(c1[0], c1[1], SEAM, 3.0)] + [at(px, py, z, 3.0) for (px, py), z in zip([(200,410),(120,460),(55,522),(60,600),(20,750),(5,900),(20,945),(80,1010),(200,1100),(300,1150)],
                                                                                   [1.2,0.8,MAINZ,0.4,0.2,0.1,0,0,0,0])], 3.2, True, True, "K", "tunnel"),
          ("E_edge", [(c3[0], c3[1], SEAM, 3.0)] + [at(px, py, z, 3.0) for (px, py), z in zip([(1700,420),(1855,515),(1900,590),(1945,700),(1945,900),(1940,945),(1850,1000),(1700,1080),(1490,1165)],
                                                                                   [1.2,MAINZ,0.4,0.2,0.1,0,0,0,0])], 3.2, True, True, "K", "tunnel")]
    # 가짜 출구 — 활 굴 꼭대기에서 더 올라가는 사갱("갱구" 표지판은 소품 단계), 끝은 무너짐
    fx0 = m_(1000, 10); fx1 = m_(1010, -60); fx2 = m_(1030, -250)
    T.append(("fake_exit", [(*fx0, zt, 3.0), (*fx1, zt, 3.0), (*fx2, zt + math.dist(fx1, fx2) * math.tan(math.radians(25)), 3.0)], 3.2, True, True, "K", "tunnel"))

    # ---- 곁길(지선): 긴 굴이 바위 하나를 두고 두 갈래로 갈라졌다 합친다 — 짧은 고리
    def siding(name, parent, pxa, pxb, off_m, lz):
        par = next(t for t in T if t[0] == parent)
        (ax, ay), (bx, by) = m_(*pxa), m_(*pxb); za_, zb_ = proj(par[1], (ax, ay))[2], proj(par[1], (bx, by))[2]
        L = math.hypot(bx - ax, by - ay); nx, ny = -(by - ay) / L, (bx - ax) / L
        p = lambda f, o: (ax + (bx - ax) * f + nx * o, ay + (by - ay) * f + ny * o, za_ + (zb_ - za_) * f, 3.0)
        T.append((name, [p(0, 0), p(0.25, off_m), p(0.75, off_m), p(1, 0)], 3.0, True, True, lz, "tunnel"))
    siding("sd_main_w", "main", (585,528), (800,528), 7.0, "D"); siding("sd_main_e", "main", (1150,536), (1400,540), 7.0, "D")
    siding("sd_arc_w", "T_arc", (620,17), (900,11), 7.0, "K"); siding("sd_arc_e", "T_arc", (1100,15), (1380,29), 7.0, "K")
    siding("sd_edge_w", "W_edge", (60,600), (20,750), -7.0, "K"); siding("sd_edge_e", "E_edge", (1945,700), (1945,880), 7.0, "K")
    siding("sd_bottom_e", "bottom_e", (1300,952), (1580,948), -7.0, "K"); siding("sd_link_e", "link_e", (1250,735), (1400,700), -7.0, "D")

    # ---- 개구멍 (사람만 기어서) — 양 끝 바닥 높이는 이어지는 굴·방에서
    walkT = [t for t in T if t[4]]
    def crawl(name, a, b, via=()):                                          # via = 꺾는 점 (바닥 높이는 길이 따라 잇는다)
        za_, zb_ = floor_z(walkT, R, a), floor_z(walkT, R, b); xy = [a, *via, b]
        ss = np.cumsum([0.0] + [math.dist(p, q) for p, q in zip(xy, xy[1:])])
        T.append((name, [(*p, za_ + (zb_ - za_) * s_ / ss[-1], CRAWL_W) for p, s_ in zip(xy, ss)], CRAWL_H, False, False, "K", "crawl"))
    crawl("c_plaza", m_(910,598), m_(910,530))
    xm = (Z1["xs"][2] + Z2["x0"]) / 2; crawl("c_link12", (xm, Z1["ys"][2]), (xm, Z1["ys"][1]))
    crawl("c_z4", (Z4["x0"] + 0.5, m_(0,770)[1]), m_(22,770))
    lk = next(t for t in T if t[0] == "link_e")[1]; a5 = (Z5["x0"] + 0.5, m_(0,720)[1]); w5 = (Z5["x0"] - 1.5, a5[1])
    crawl("c_z5", a5, point_at(lk, proj(lk, w5)[1]), via=[w5])            # 방 벽에서 곧게 1.5 m → link_e 가운데 선의 가장 가까운 점. 손그림 자리 (1470,705)는 link_e 벽 밖 2.5 m 바위 속이라
                                                                            # 막다른 구멍이었다 (R2b 차례 4 검사가 찾음 09-25, check_hole_ends). 곧게 link_e 로 가면 방 벽을 37° 로 비스듬히 빠져 입구가 방 쪽으로 열린 쐐기가 됐다
    crawl("c_charge", m_(510,1070), m_(510,930)); crawl("c_comp", m_(1460,1105), m_(1460,955))   # 충전실 뒷문은 들어오는 굴(왼쪽 위)과 먼 오른쪽 위 — 왼쪽(330)에 두었더니 괴물이 14 m 만 돌면 반대편이었다(구멍 7.6 m, MAP2 검사 09-25)
    crawl("c_z2", (Z2["x1"] - 1.0, Z2["y0"]), m_(1115,538)); crawl("c_z1", (Z1["xs"][0], Z1["ys"][0]), m_(240,515))

    # ---- R2b 바위 틈: 뚫린 틈 = 짧은 개구멍 넷(4.8~6.0 m)을 바위 틈으로 · 막힌 틈 10 = 굴·방 벽에서 좁은 틈 1.6 m → 안쪽 방 1.6 m
    crev = []                                                               # (이름, through/closed, 입구 벽 점, 끝 점(뚫린: 반대편 끝 · 막힌: 숨는 자리), 안쪽 방향)
    if crevices:
        for n in ("c_plaza", "c_link12", "c_z5", "c_z4"):                   # 긴 개구멍(① · ② → 큰길 10 m 등)은 그대로 — 뚫린 틈은 4.2 m 안팎(제안서)
            i = [t[0] for t in T].index(n); nm, pts, *_ = T[i]; L = seg_len(pts)
            def zp(f, sg):                                                  # 굴 따라 f 자리에서 옆으로 sg × CREV_ZIG
                q = np.array(point_at(pts, L * f)); dd = np.array(point_at(pts, min(L * f + 0.05, L))) - np.array(point_at(pts, max(L * f - 0.05, 0)))
                return np.array((*(q + np.array((-dd[1], dd[0])) / np.linalg.norm(dd) * CREV_ZIG * sg), proj(pts, q)[2]))
            ss = np.cumsum([0.0] + [math.dist(a[:2], b[:2]) for a, b in zip(pts, pts[1:])])
            zig = [k[1] for k in sorted([(s_, np.array(p[:3])) for s_, p in zip(ss, pts)] + [(L * f, zp(f, sg)) for f, sg in ((0.35, 1), (0.65, -1))], key=lambda k: k[0])]   # 가운데 선이 지그재그 — 곧은 홈처럼 안 보이게 (꺾는 점은 그대로)
            T[i] = (nm, [(*p, CREV_W) for p in zig], CREV_H, False, False, "K", "crevice")
            d = np.array(pts[-1][:2]) - np.array(pts[0][:2]); crev.append((nm, "through", pts[0][:3], pts[-1][:3], tuple(d / np.linalg.norm(d))))
        def closed(name, px, py, parent=None, d=None):
            q = np.array(m_(px, py))
            if parent:                                                      # 굴 벽: px 쪽 벽 (px = 옛 대피소 입구)
                par = next(t for t in T if t[0] == parent)[1]; dist, s, z = proj(par, q); c = np.array(point_at(par, s))
                n = (q - c) / np.linalg.norm(q - c); wall = c + n * par[0][3] / 2
            else:                                                           # 방 벽: px = 벽 위 점, d = 안쪽 방향
                n = np.array(d, float); wall = q; z = room_floor(R, tuple(q))
            p = lambda k: (*(wall + n * k), z)
            l_ = np.array((-n[1], n[0])); pz = lambda k, sd: (*(wall + n * k + l_ * sd), z)
            T.append((name, [(*p(-0.6), CREV_W), (*pz(0.7, CREV_ZIG), CREV_W), (*p(CREV_SLIT), CREV_W)], CREV_H, False, False, "K", "crevice"))
            T.append((name + "_room", [(*p(CREV_SLIT - 0.1), CREV_ROOM), (*p(CREV_SLIT + CREV_ROOM + 0.2), CREV_ROOM)], CREV_H + 0.2, False, False, "K", "crevice_room"))
            crev.append((name, "closed", p(0), p(CREV_HIDE), tuple(n)))
        closed("cr_z2w", 770, 160, d=(-1, 0)); closed("cr_z2e", 1090, 330, d=(1, 0)); closed("cr_pump", 1030, 1160, d=(1, 0))   # ② 기둥 사이 양쪽 벽 · 펌프실 (옛 작은 틈 자리)
        for nm, px_, py_, par in (("cr_main_a", 1020, 511, "main"), ("cr_main_b", 1275, 557, "main"), ("cr_link_w", 653, 707, "link_w"), ("cr_link_e", 1119, 754, "link_e"),
                                  ("cr_arc", 1239, 35, "T_arc"), ("cr_edge_w", 142, 1072, "W_edge"), ("cr_edge_e", 1823, 1029, "E_edge")):
            closed(nm, px_, py_, par)                                       # 큰길 갈림 가까이 둘 · 광장 옆 굴 둘 · 활 굴 · 바깥 고리 둘 (옛 대피소 자리) — 막힌 틈 10

    # ---- 좁은 대피소 자동: 걷는 굴마다 갈림·숨을 곳 사이가 12.5 m 를 넘지 않게 (다른 굴·방과 부딪히면 앞뒤로 옮김)
    global _R; _R = R
    def auto_niches(maxgap=12.5):
        walkT = [t for t in T if t[4]]; others = [t for t in T if t[6] != "tunnel" or t[4]]
        ev = route_events(T, R, walkT, others); added = []
        for n, pts, *_ in walkT:
            e = ev[n]
            for (s0, j0), (s1, j1) in zip(e, e[1:]):
                L = s1 - s0; k = math.ceil(L / maxgap) - 1 if (j0 and j1) else (math.ceil(L / maxgap) if L > 9 else 0)
                for i in range(1, k + 1):
                    s_want = s0 + L * i / (k + 1) if (j0 and j1) else s0 + L * i / (k + 0.5)
                    done = False
                    for ds, depth in [(d_, NICHE_D) for d_ in (0, 1.5, -1.5, 3, -3, 4.5, -4.5, 6, -6)] + [(d_, 1.6) for d_ in (0, 1.5, -1.5, 3, -3, 4.5, -4.5, 6, -6)]:   # 자리가 좁으면 얕은 대피소(1.6 m)
                        s = min(max(s_want + ds, s0 + 1.0), s1 - 1.0)
                        (x, y) = point_at(pts, s); (x2, y2) = point_at(pts, min(s + 0.5, seg_len(pts))); (x1, y1) = point_at(pts, max(s - 0.5, 0))
                        dx, dy = x2 - x1, y2 - y1; L2 = math.hypot(dx, dy) or 1; w = pts[0][3]; z = proj(pts, (x, y))[2]
                        for side in ((1, -1) if len(added) % 2 == 0 else (-1, 1)):
                            nx, ny = -dy / L2 * side, dx / L2 * side
                            tips = [(x + nx * (w / 2 + r) + tx * sd, y + ny * (w / 2 + r) + ty * sd) for r in (0.8, 1.6, 2.4, 3.2) if r <= depth + 0.8 for sd in (-0.5, 0, 0.5)
                                    for tx, ty in ((dx / L2, dy / L2),)]                          # 대피소 폭까지 — 옆 굴·방과 바위 1.6 m 이상
                            narrow_ = [t for t in T if t[6] != "tunnel"] + added              # 다른 개구멍·대피소와도 떨어지게 (겹치면 넓어져 괴물이 들어간다)
                            if all(not near_room(tp, 1.6) for tp in tips) and all(proj(o[1], tp)[0] > o[1][0][3] / 2 + 1.6 for o in walkT if o[0] != n for tp in tips)                                     and all(proj(o[1], tp)[0] > o[1][0][3] / 2 + 1.2 for o in narrow_ for tp in tips):
                                added.append(("niche_%d" % len(added), niche_pts(x, y, z, nx, ny, w, depth), NICHE_H, False, False, "K", "niche")); done = True; break
                        if done: break
        T.extend(added)
    auto_niches()

    # ---- 자리들
    def snap(px, py):                                                        # 손그림 점 → 가장 가까운 걷는 바닥
        q = m_(px, py); walkT = [t for t in T if t[4]]
        if room_of(R, q): return (*q, room_floor(R, q))
        t = min(walkT, key=lambda t: proj(t[1], q)[0]); d, s, z = proj(t[1], q); return (*point_at(t[1], s), z)
    gap_big = [snap(*p) for p in [(430,150),(945,112),(1420,355),(20,380),(1925,270),(345,780),(20,950),(1940,945)]]
    gap_small = [(*m_(768,250), SEAM), (*m_(1092,330), SEAM), (*m_(1025,1160), 0.0)]
    pockets = []                                                             # (자리, 벽 쪽 방향) — 광맥 30
    for Z, zs_ in ((Z1, 8), (Z3, 8)):
        for j, (y, z) in enumerate(zip(Z["ys"], Z["zs"])):
            for i in range(len(Z["xs"]) - 1):
                if len([p for p in pockets if p[2] is Z]) >= zs_: break
                pockets.append(((( Z["xs"][i] + Z["xs"][i + 1]) / 2, y, z), (0.0, 1.0 if j < len(Z["ys"]) - 1 else -1.0), Z))
    for (x0, x1, y0, y1) in PIL[:6]:                                          # 기둥 사이: 기둥 여섯의 남쪽·북쪽 면
        pockets.append((((x0 + x1) / 2, y0 - 1.5, SEAM), (0.0, 1.0), Z2)); pockets.append((((x0 + x1) / 2, y1 + 1.5, SEAM), (0.0, -1.0), Z2))
    pockets = pockets[:28]
    for Z in (Z4, Z5): x0, x1, y0, y1 = PIL[-1 if Z is Z5 else 6]; pockets.append((((x0 + x1) / 2, y1 + 1.5, 0.3), (0.0, -1.0), Z))
    ws = next(t for t in T if t[0] == "W_spur")[1]; es = next(t for t in T if t[0] == "E_spur")[1]
    pockets += [((ws[-1][0] + 1.0, ws[-1][1], SEAM), (-1.0, 0.0), None), ((es[-1][0] - 0.8, es[-1][1] - 0.4, SEAM), (0.9, 0.45), None)]
    pockets = [(p, d) for p, d, _ in pockets][:30]
    lit = [(m_(850,640), 0, 4.5), (m_(970,640), 0, 4.5), (m_(700,620), 0.15, 3.2), (m_(1100,620), 0.15, 3.2), (m_(918,830), 0, 3.2),
           (m_(650,930), 0, 3.2), (m_(1150,918), 0, 3.2), (m_(410,1130), 0, 3.6), (m_(910,1150), 0, 3.8), (m_(1360,1160), 0, 3.6)]
    dead = [(m_(px, py), MAINZ, 3.4) for px, py in [(300,520),(700,528),(1300,538),(1750,518)]] + [(m_(1250,735), 0, 3.2), (m_(520,710), 0.1, 3.2),
           (m_(150,952), 0, 3.2), (m_(1500,950), 0, 3.2)]
    def blk(g, px, py, parent):                                             # (묶음, x, y, 바닥, 굴 방향 °, 굴 폭, 천장)
        t = next(t for t in T if t[0] == parent); par = t[1]; q = m_(px, py); d, s, z = proj(par, q)
        (x1, y1) = point_at(par, max(s - 1, 0)); (x2, y2) = point_at(par, min(s + 1, seg_len(par)))
        return (g, *point_at(par, s), z, math.degrees(math.atan2(y2 - y1, x2 - x1)), par[0][3], t[2])
    def blk_mid(g, parent):                                                  # 개구멍 한가운데 (사람만 지나가는 길도 막는다)
        par = next(t for t in T if t[0] == parent)[1]; q = point_at(par, seg_len(par) / 2); return blk(g, q[0] / F + CX, CY - q[1] / F, parent)
    # 묶음 = 가운데와 닫을 구역 사이를 잇는 곳 전부 (09-25 Unity 전 점검: 넷씩이면 ①–② 윗줄 · 바깥 고리 끝 → 충전실·컴프레서실 · 개구멍 둘이 열려 둘 다 켜도 거의 다 열렸다)
    # 가운데 쪽 갈림에서 3 m 쯤 — 멀리 두면 가운데 쪽에 막다른 굴이 남는다(첫 자리: 최대 17.5 m, 도망치다 갇힌다 · 길 잃고 걷기 부스판 67 %, MAP2 검사 09-25)
    blocks = [blk(1, 400, 450, "v_z1"), blk(1, 745, 0, "link12b"), blk(1, 745, 0, "link12a"), blk(1, 160, 521, "main"), blk(1, 160, 948, "bottom_w"),
              blk(1, 255, 1128, "W_edge"), blk_mid(1, "c_z1"), blk_mid(1, "c_z4"),
              blk(2, 1540, 460, "v_z3"), blk(2, 1135, 0, "link23"), blk(2, 1710, 520, "main"), blk(2, 1675, 948, "bottom_e"), blk(2, 1535, 1147, "E_edge")]
    spawn_p = (*m_(910, 705), 0.05); look_p = (*m_(910, 560), 1.6)
    gy = Z2["y1"] - 1.5; spawn_s = (Z2["cx"][1], gy, SEAM + 0.05); look_s = (Z2["cx"][-1], gy, SEAM + 1.0)
    fake_end = T[[t[0] for t in T].index("fake_exit")][1][-1]
    return dict(T=T, R=R, PILLARS=PIL, Z=dict(Z1=Z1, Z2=Z2, Z3=Z3, Z4=Z4, Z5=Z5), gap_big=gap_big, gap_small=gap_small, pockets=pockets,
                lit=lit, dead=dead, blocks=blocks, crevices=crev, spawn_player=spawn_p, look_player=look_p, spawn_stalker=spawn_s, look_stalker=look_s,
                cart=(*m_(840, 650), 0.0), lunchbox=(es[-1][0] - 1.5, es[-1][1] - 0.7, SEAM), fake_end=fake_end,
                home_rect=(m_(800, 0)[0], m_(1020, 0)[0], m_(0, 738)[1], m_(0, 598)[1]))


def check_hole_ends(B):
    """개구멍·뚫린 바위 틈은 양 끝이, 막힌 바위 틈은 입구 끝이 걷는 굴·방 안에 있는가 (끝이 바위 속이면 막다른 구멍이다)"""
    walk = [t for t in B["T"] if t[4]]; through = {c[0] for c in B.get("crevices", []) if c[1] == "through"}
    def inside(q): return any(r[1] <= q[0] <= r[2] and r[3] <= q[1] <= r[4] for r in B["R"]) or any(proj(t[1], q)[0] < t[1][0][3] / 2 for t in walk)
    return [(n, k, round(min(proj(t[1], e)[0] - t[1][0][3] / 2 for t in walk), 2)) for n, pts, *_, kind in B["T"] if kind in ("crawl", "crevice")
            for k, e in ((0, pts[0]), (1, pts[-1])) if (k == 0 or kind == "crawl" or n in through) and not inside(e[:2])]


def check_junction_floors(B, tol=0.15):
    """굴 끝이 다른 굴·방에 닿는 자리에서 바닥 높이가 맞는가 (턱이 없어야 한다)"""
    T, R = B["T"], B["R"]; bad = []
    for n, pts, *_ in T:
        for end in (pts[0], pts[-1]):
            zr = room_floor(R, end)
            if zr is not None:
                if abs(zr - end[2]) > tol: bad.append((n, "room", round(end[2] - zr, 2)))
                continue
            for o in T:
                if o[0] == n or not o[4]: continue
                d, s, z = proj(o[1], end)
                if d < o[1][0][3] / 2 + 0.3 and abs(z - end[2]) > tol and not (o[6] != "tunnel"): bad.append((n, o[0], round(end[2] - z, 2)))
    return bad


if __name__ == "__main__":
    B = build()
    kinds = {}
    for t in B["T"]: kinds[t[6]] = kinds.get(t[6], 0) + 1
    print("굴 %d (%s) · 방 %d · 기둥 %d · 광맥 %d · 큰 틈 %d · 전등 %d/%d · 막힘 %d" % (len(B["T"]), kinds, len(B["R"]), len(B["PILLARS"]), len(B["pockets"]),
          len(B["gap_big"]), len(B["lit"]), len(B["dead"]), len(B["blocks"])))
    print("갈림 바닥 어긋남:", check_junction_floors(B) or "없음")
