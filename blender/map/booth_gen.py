"""MAP3 — 시드로 뽑는 한 층 맵 (제안서 docs/제안서_MAP3_맵2배_조립기.md, 승인 09-25 55차).
옛 Godot 조립기(Tunnel/new-game/scripts/MineAssembler.gd)의 문법을 옮겨 7 m 칸 격자에 굴을 짜고, booth_table.build() 와 같은 형식의 표를 낸다.
고정(사용자 09-25): 가운데 케이지 광장 · 불 켜진 방 셋 · 바깥 고리 · 가짜 출구. 나머지(굴 · 기둥 방 · 비탈 구역 · 고리 · 막다른 굴)는 시드.
  python blender/map/booth_gen.py [시드 수=300] [후보 수=4]   → build/map3/candidates.png · seeds.txt (Blender · Unity 안 건드림)
거르기 = map2_plan.py 와 같은 재기(괴물 반지름 0.6 m 를 뺀 바닥): 바닥이 MAP2(3,144 m²)의 2배 ±10 % · 짧은 고리 ≥ 60 · 막다른 굴 ≤ 8 m ·
  갈림·숨을 곳 없는 가장 긴 굴 ≤ 15 m · 길 잃고 425 m 안에 정거장 ≥ 40 % (300 m × √2 — 넓이 2배면 거리는 √2 배) · 기둥 방이 위·아래 절반에 모두.
build() 는 numpy 만 쓴다(Blender 안에서도 돈다)."""
import math, random, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import booth_table as bt

CELL = 8.0                      # m, 칸 (옛 조립기 7 m — 굴 사이 바위가 3.8 m 라 대피소(깊이 1.6~2.4 + 바위 1.6)가 못 들어가 8 m)
GW, GH = 31, 23                 # 칸 수 (가로 · 세로) — 로브(큰 고리 ~ 바깥 고리 사이에 막장 구역 + 둘레 비움 + 도는 가는 길)가 들어갈 자리. 27 × 21 은 로브가 거의 안 들어갔다
CI, CJ = GW // 2, GH // 2 - 1   # 케이지 광장 아래 가운데 칸 (광장 = CI-1..CI+1 × CJ..CJ+1)
PI, PJ = CI, CJ + 0.5           # → 세계 (0, 0)
JIT = 1.0                       # m, 굴 칸 가운데를 흔드는 폭 (격자처럼 안 보이게)
AIS = 3.0                       # m, 기둥 방 통로 폭 (booth_table zone_grid 와 같음) — 기둥 = 7 − 3 = 4 m 네모
TURN_P, LOOP_P, BRAID = 0.35, 0.8, 1.0
SPOKES = (5, 7)                 # 광장에서 고리까지 곧은 굴 수 (남쪽 불 켜진 길 말고). 길 잃은 사람이 돌아오는 시간 ≈ 굴 전체 길이 ÷ 광장 입구 수 — MAP2 는 굴 1,300 m 에 입구 5~6, MAP3 는 약 2,300 m (4~5 로는 425 m 안 평균 31 %)
ZONES = (4, 7)                  # 구역 수 (기둥 방 · 비탈) — 짧은 고리는 거의 다 기둥이다(둘레 21~24 m, 굴끼리 만든 고리는 대개 60 m 넘음). 3~6 이면 34~55, 기준 60
ZONE_SIZES = [(3, 3), (4, 3), (3, 4), (4, 4), (5, 4), (4, 5), (5, 5)]   # 섞는다 — 4~6 칸만 쓰면 크고 똑같은 방이 됐다
LOBE_SIZES = [(4, 3), (3, 4), (4, 4), (5, 4), (4, 5), (5, 5)]   # 막장 구역 — 로브마다 하나라 기둥(= 짧은 고리)이 모자라지 않게 크게
NICHE_GAP = 11.0                # m, 자동 대피소 간격 (MAP2 12.5 — 칸 격자에서는 옆 굴이 가까워 못 놓는 자리가 많아 줄인다)
MAP2_AREA = 3144.0              # map2_plan.py 로 잰 MAP2 v4 바닥 (m²)
N4 = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def xy(c): return ((c[0] - PI) * CELL, (c[1] - PJ) * CELL)
def nb(c, d): return (c[0] + N4[d][0], c[1] + N4[d][1])


def build(seed, crevices=True):
    rng = random.Random(seed)
    kind, opn, zone_of = {}, {}, {}     # 칸 → 종류 · 뚫린 면 · 구역 번호
    CORR = ("ring", "lit", "tun", "inner", "sc")                        # 바깥 고리 · 불 켜진 길 · 굴 · 큰 고리 · 지름길
    def inside(c): return 0 <= c[0] < GW and 0 <= c[1] < GH
    def free(c): return inside(c) and c not in kind
    def carve(a, d):
        b = nb(a, d); opn.setdefault(a, set()).add(d); opn.setdefault(b, set()).add(OPP[d])
    def uncarve(a):
        for d in list(opn.get(a, ())):
            opn[nb(a, d)].discard(OPP[d])
        opn.pop(a, None); kind.pop(a, None)
    def walkable(c): return kind.get(c) in CORR + ("room", "zone")

    # ---- 고정 1: 가운데 케이지 광장 + 아래로 불 켜진 길과 방 셋 (MAP2 와 같은 짜임)
    rooms = {}                          # 이름 → (칸들, 상자 폭, 상자 높이, 천장)
    def room(name, i0, i1, j0, j1, bw, bh, h):
        cells = [(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]
        for c in cells: kind[c] = "room"; zone_of[c] = name
        rooms[name] = (cells, bw, bh, h)
    I, J = CI, CJ
    room("plaza", I - 1, I + 1, J, J + 1, 15.4, 9.8, 4.5)
    room("charge", I - 5, I - 4, J - 3, J - 2, 13.0, 8.4, 3.6); room("comp", I + 4, I + 5, J - 3, J - 2, 13.0, 7.7, 3.6); room("pump", I - 1, I + 1, J - 6, J - 5, 16.8, 9.5, 3.8)
    lit = [(I, J - 1), (I, J - 2), (I - 1, J - 2), (I - 2, J - 2), (I - 3, J - 2), (I + 1, J - 2), (I + 2, J - 2), (I + 3, J - 2), (I, J - 3), (I, J - 4)]
    for c in lit: kind[c] = "lit"
    for a, d in (((I, J), "S"), ((I, J - 1), "S"), ((I, J - 2), "W"), ((I - 1, J - 2), "W"), ((I - 2, J - 2), "W"), ((I - 3, J - 2), "W"), ((I, J - 2), "E"),
                 ((I + 1, J - 2), "E"), ((I + 2, J - 2), "E"), ((I + 3, J - 2), "E"), ((I, J - 2), "S"), ((I, J - 3), "S"), ((I, J - 4), "S")):
        carve(a, d)

    # ---- 고정 2: 바깥 고리 — 모서리·가운데 여덟 점을 안쪽으로 0~2 칸 흔들고 ㄱ자로 잇는다 (옛 조립기 순환선)
    def jit(): return rng.randint(0, 2)
    wp = [(1 + jit(), 1 + jit()), (GW // 2, 1 + jit()), (GW - 2 - jit(), 1 + jit()), (GW - 2 - jit(), GH // 2), (GW - 2 - jit(), GH - 2 - jit()),
          (GW // 2, GH - 2 - jit()), (1 + jit(), GH - 2 - jit()), (1 + jit(), GH // 2)]
    ring = []
    for a, b in zip(wp, wp[1:] + wp[:1]):
        cur = a; hfirst = rng.random() < 0.5
        while cur != b:
            dx, dy = b[0] - cur[0], b[1] - cur[1]
            d = ("E" if dx > 0 else "W") if (dx and (hfirst or not dy)) else ("N" if dy > 0 else "S")
            if not ring or ring[-1] != cur: ring.append(cur)
            kind.setdefault(cur, "ring"); carve(cur, d); cur = nb(cur, d)
        kind.setdefault(cur, "ring")
    ring_set = set(ring)

    # ---- 고정 3: 가짜 출구 — 고리 위쪽(가운데 3분의 1)에서 맵 밖(북쪽)으로 올라가는 사갱, 끝은 무너짐
    top = [c for c in ring_set if GW / 3 <= c[0] <= 2 * GW / 3 and all(not inside((c[0], j)) or (c[0], j) not in kind for j in range(c[1] + 1, GH))]
    fake_root = max(top, key=lambda c: (c[1], -abs(c[0] - PI))) if top else max(ring_set, key=lambda c: c[1])

    # ---- 큰 고리 (옛 광차 순환선 — 제안서 문법 2, 차례 2 첫 판에서 빠졌던 것): 충전실 위 → 광장 북쪽 → 컴프레서실 위. 불 켜진 길과 합쳐 광장을 한 바퀴 두른다
    a_, b_ = rng.randint(0, 1), rng.randint(0, 1); top = J + 3 + rng.randint(0, 1)
    iw = [(I - 5, J - 1), (I - 5 - a_, J + 1), (I - 5 - a_, top), (I, top + rng.randint(0, 1)), (I + 5 + b_, top), (I + 5 + b_, J + 1), (I + 5, J - 1)]
    for p, q in zip(iw, iw[1:]):
        cur = p; hfirst = rng.random() < 0.5
        while cur != q:
            dx, dy = q[0] - cur[0], q[1] - cur[1]
            d = ("E" if dx > 0 else "W") if (dx and (hfirst or not dy)) else ("N" if dy > 0 else "S")
            kind.setdefault(cur, "inner"); carve(cur, d); cur = nb(cur, d)
        kind.setdefault(cur, "inner")
    carve((I - 5, J - 1), "S"); carve((I + 5, J - 1), "S")                 # 충전실 · 컴프레서실로
    inner_set = {c for c, v in kind.items() if v == "inner"}
    spoke = set()                                                         # 옆길을 안 붙이는 칸 (광장 잇기 · 바큇살 · 지름길)
    def connect(start_cells, targets, allow=None, straight=False):
        """start 에서 비어 있는 칸만 지나 targets 까지 가는 칸 목록 — 칸마다 무게 1~3 을 뽑은 가장 짧은 길(조금씩 굽음), straight 면 무게 1 (곧게)"""
        import heapq
        q = [(0.0, rng.random(), c) for c in start_cells]; prev = {c: None for c in start_cells}; cost = {c: 0.0 for c in start_cells}
        heapq.heapify(q)
        while q:
            cc, _, c = heapq.heappop(q)
            if cc > cost.get(c, 1e9): continue
            if c in targets and c not in start_cells:
                path = [c]
                while prev[path[-1]] is not None: path.append(prev[path[-1]])
                path.reverse()
                return path
            for d in N4:
                n_ = nb(c, d)
                if not inside(n_) or not (n_ in targets or (free(n_) and (allow is None or allow(n_)))): continue
                nc = cc + (1.0 if straight else rng.uniform(1.0, 3.0))
                if nc < cost.get(n_, 1e9):
                    cost[n_] = nc; prev[n_] = c; heapq.heappush(q, (nc, rng.random(), n_))
        return None
    region = {}                                                           # 칸 → 로브 번호 (없으면 "hub" = 광장·큰 고리·바큇살·바깥 고리). 곁가지는 같은 곳끼리만 잇는다
    def reg(c): return region.get(c, "hub")
    def dig(path, k="tun", rg=None):
        for a, b in zip(path, path[1:]):
            d = next(d for d in N4 if nb(a, d) == b)
            if b not in kind:
                kind[b] = k
                if rg is not None: region[b] = rg
            carve(a, d)
    # 광장 → 큰 고리 3~4 곳 (짧고 곁가지 없음)
    links = [((I - 1, J + 1), "N"), ((I + 1, J + 1), "N"), ((I - 1, rng.choice((J, J + 1))), "W"), ((I + 1, rng.choice((J, J + 1))), "E")]
    rng.shuffle(links)
    for c, d in links:                                                     # 넷 다 (광장 입구가 돌아오기를 가장 크게 좌우한다 — MAP3 첫 판 교훈)
        o = nb(c, d)
        if not free(o): continue
        kind[o] = "tun"; carve(c, d); spoke.add(o)
        p = connect([o], inner_set)
        if p: dig(p); spoke.update(p[:-1])
    # ---- 바큇살 6~8: 큰 고리 · 아래 방에서 바깥 고리까지, 각도를 고르게 (길 잃은 사람이 살에 닿으면 반은 가운데로)
    def ang(c): x, y = xy(c); return math.atan2(y, x)
    def adiff(a, b): return abs((a - b + math.pi) % (2 * math.pi) - math.pi)
    hub = inner_set | {c for c in kind if kind[c] == "room" and zone_of[c] in ("charge", "comp", "pump")}
    K = rng.randint(*SPOKES); base = rng.uniform(0, 2 * math.pi / K); spoke_ang = []; spoke_start = []
    for k in range(K):
        th = base + 2 * math.pi * k / K + rng.uniform(-0.12, 0.12)
        cands = [(h, d) for h in hub for d in N4 if free(nb(h, d)) and (N4[d][0] * math.cos(th) + N4[d][1] * math.sin(th)) > 0.3]
        if not cands: continue
        h, d = min(cands, key=lambda hd: adiff(ang(nb(*hd)), th) + 0.02 * math.hypot(*xy(hd[0])) / CELL)
        o = nb(h, d)
        if any(abs(o[0] - s[0]) + abs(o[1] - s[1]) < 3 for s in spoke_start): continue   # 바큇살끼리만 떨어뜨린다 (광장 잇기 굴과 붙어도 된다)
        kind[o] = "tun"; carve(h, d); spoke_start.append(o)
        p = connect([o], ring_set, allow=lambda c: adiff(ang(c), th) < 0.45) or connect([o], ring_set)
        if p: dig(p); spoke.update({o} | set(p[:-1])); spoke_ang.append(ang(o))
    if len(spoke_ang) < 5: return None
    spoke_ang.sort()
    def sector(c):
        a = ang(c)
        for k in range(len(spoke_ang)):
            lo_, hi_ = spoke_ang[k], spoke_ang[(k + 1) % len(spoke_ang)]
            if (a - lo_) % (2 * math.pi) < (hi_ - lo_) % (2 * math.pi): return k
        return 0

    # ---- 로브 = 고리로 짜기(Unexplored 식): 부채꼴마다 막장 구역 하나 — 큰 고리에서 길고 꼬인 "가는 길" → 막장 구역(광맥 · 기둥) →
    #      바깥 고리로 빠지는 "다른 길" + 큰 고리로 곧장 오는 "지름길"(한쪽 문: 판자벽은 막장 쪽에서만 걷어찬다 · 비탈은 꼭대기에서 사다리를 내린다)
    zones, lobes, door_edges, ladder_edges = [], [], set(), set()
    sc_side = {}                                                          # 지름길 한쪽 문 → (막장 쪽 칸, 집 쪽 칸)
    hubset = inner_set | {c for c, v in kind.items() if v in ("lit", "room")}
    # (가) 막장 구역을 먼저 다 놓는다 — 부채꼴 가운데쯤 (바깥 고리 바로 옆이면 바큇살·고리로 돌아 들어가는 길이 가는 길만큼 짧았다)
    for k in range(len(spoke_ang)):
        sec = lambda c, k=k: sector(c) == k
        best = None
        for _ in range(300):
            w, h = rng.choice(LOBE_SIZES); i0, j0 = rng.randint(2, GW - 2 - w), rng.randint(2, GH - 2 - h)
            rect = [(i, j) for i in range(i0, i0 + w) for j in range(j0, j0 + h)]
            margin = [(i, j) for i in range(i0 - 1, i0 + w + 1) for j in range(j0 - 1, j0 + h + 1)]
            if not all(free(c) for c in rect) or not sec((i0 + w // 2, j0 + h // 2)) or any(kind.get(c) not in (None, "ring") for c in margin): continue   # 가운데 칸만 이 부채꼴에 · 둘레 한 칸은 비움
            mx, my = np.mean([xy(c) for c in rect], axis=0); th_ = math.atan2(my, mx)
            r_edge = 1 / math.hypot(math.cos(th_) / ((GW / 2 - 1.5) * CELL), math.sin(th_) / ((GH / 2 - 1.5) * CELL))
            sc_ = -abs(math.hypot(mx, my) - 0.6 * r_edge) + rng.uniform(0, 6)
            if best is None or sc_ > best[0]: best = (sc_, i0, j0, w, h, rect)
        if best is None: lobes.append(None); continue
        _, i0, j0, w, h, rect = best
        typ = rng.choices(["pillar", "slope15", "slope25"], [0.6, 0.2, 0.2])[0]
        if typ != "pillar" and any(z["type"] == typ for z in zones): typ = "pillar"   # 비탈은 종류마다 하나까지
        zk = len(zones); cx, cy = xy((i0 + (w - 1) / 2, j0 + (h - 1) / 2))
        inward = (0, -1 if cy > 0 else 1) if abs(cy) >= abs(cx) else (-1 if cx > 0 else 1, 0)       # 가운데 쪽 (비탈은 이쪽으로 올라간다 — 꼭대기가 집 쪽)
        rise = {"pillar": 0.0, "slope15": (CELL - bt.LANDING) * math.tan(math.radians(15)), "slope25": (CELL - bt.LANDING) * math.tan(math.radians(25))}[typ]
        zz = {}; span = (w - 1) * abs(inward[0]) + (h - 1) * abs(inward[1])
        for c in rect:
            kind[c] = "zone"; zone_of[c] = zk; region[c] = k
            t_ = (c[0] - i0) * inward[0] + (c[1] - j0) * inward[1]
            zz[c] = 0.0 if typ == "pillar" else (t_ if min(inward) >= 0 else span + t_) * rise
        for c in rect:
            for d in ("E", "N"):
                if nb(c, d) in zz: carve(c, d)
        zones.append(dict(type=typ, i0=i0, j0=j0, w=w, h=h, climb=None if typ == "pillar" else inward, z=zz, cells=rect, lobe=k))
        lat = (-inward[1], inward[0])
        lobes.append(dict(k=k, zone=zk, rect=rect, zz=zz, typ=typ, inward=inward, lat=lat, side=rng.choice((1, -1)), c=(cx, cy),
                          goal=max(rect, key=lambda c: math.hypot(*xy(c)) - 50 * zz[c]), long=None, out=None, short=None, kind=None))   # 막장 = 가운데에서 가장 먼 칸 (비탈은 낮은 쪽 끝)
    def on_side(lo, c, need=0.4):                                         # 구역 가운데 선에서 lo["side"] 쪽으로 need 칸 넘게
        return np.dot(np.subtract(xy(c), lo["c"]), lo["lat"]) * lo["side"] > need * CELL
    # (나) 가는 길: 부채꼴 안, 구역 가운데 선의 한쪽(side)으로만 — 큰 고리 입구에서 구역 옆면까지 목표 쪽으로 기울어 헤매며 걷는다 (곧은 길의 1.8 배 넘게, 다른 굴에 안 붙는 한 줄)
    for lo in [l_ for l_ in lobes if l_]:
        k, rect, zz, inward, lat, sg = lo["k"], lo["rect"], lo["zz"], lo["inward"], lo["lat"], lo["side"]
        ok_cell = lambda c, lo=lo: free(c) and sector(c) == lo["k"] and on_side(lo, c)
        far_doors = [(c, d) for c in rect for d in N4 if ok_cell(nb(c, d)) and zz[c] <= 1.9 and (N4[d][0] * inward[0] + N4[d][1] * inward[1]) <= 0]
        entries = [(hc, d) for hc in hubset for d in N4 if ok_cell(nb(hc, d)) and nb(hc, d) not in spoke]
        if not (far_doors and entries): continue
        zc_, zd = rng.choice(far_doors); tgt = nb(zc_, zd)
        hc, hd = min(entries, key=lambda e: math.dist(xy(nb(*e)), xy(tgt)) + rng.uniform(0, 12))
        s0 = nb(hc, hd); straight_ = abs(s0[0] - tgt[0]) + abs(s0[1] - tgt[1]); path = None
        for _try in range(40):
            pth = [s0]; seen_ = {s0}; head = hd
            while pth[-1] != tgt and len(pth) < 4 * straight_ + 12:
                cur = pth[-1]; opts = []
                for d in N4:
                    n_ = nb(cur, d)
                    if n_ in seen_ or not (n_ == tgt or ok_cell(n_)): continue
                    if n_ != tgt and any(nb(n_, s) in kind and nb(n_, s) != cur and nb(n_, s) != tgt and nb(n_, s) not in rect for s in N4): continue
                    if n_ != tgt and any(nb(n_, s) in seen_ and nb(n_, s) != cur for s in N4): continue
                    gain = (abs(cur[0] - tgt[0]) + abs(cur[1] - tgt[1])) - (abs(n_[0] - tgt[0]) + abs(n_[1] - tgt[1]))
                    opts.append((n_, d, math.exp(0.6 * gain) * (1.6 if d == head else 1.0)))
                if not opts: break
                n_, head, _w = rng.choices(opts, [o[2] for o in opts])[0]; pth.append(n_); seen_.add(n_)
            if pth[-1] == tgt and len(pth) - 1 >= 1.8 * straight_: path = pth; break
        if path is None: path = connect([s0], {tgt}, allow=ok_cell)
        if path and path[-1] == tgt:
            kind[s0] = "tun"; region[s0] = k; carve(hc, hd); dig(path, "tun", k); carve(tgt, OPP[zd]); lo["long"] = len(path); lo["long_cells"] = [hc] + path + [zc_]
    # (다) 지름길: 구역의 가운데 쪽 면(가는 길 반대쪽 또는 가운데) → 큰 고리 · 방 · 바큇살 (곧게). 판자벽 = 집 쪽에 붙는 마지막 한 칸 · 비탈 = 꼭대기 칸에서 사다리
    for lo in [l_ for l_ in lobes if l_]:
        k, rect, zz, inward, typ = lo["k"], lo["rect"], lo["zz"], lo["inward"], lo["typ"]
        ins = [(c, d) for c in rect for d in N4 if free(nb(c, d)) and N4[d] == tuple(inward) and not on_side(lo, c, 0.6)]
        if typ != "pillar": ins = [cd for cd in ins if zz[cd[0]] == max(zz.values())]
        best_sc = None
        for c, d in ins:
            o = nb(c, d); p = connect([o], hubset | spoke, straight=True)
            if p and (best_sc is None or len(p) < len(best_sc[2])): best_sc = (c, d, p)
        if best_sc:
            c, d, p = best_sc; o = p[0]
            kind[o] = "sc"; region[o] = k; carve(c, d); dig(p, "sc", k); spoke.update(p[:-1]); lo["sc_cells"] = [c] + p
            if typ == "pillar":
                e_ = (p[-2] if len(p) > 1 else o, p[-1]); door_edges.add(frozenset(e_)); sc_side[frozenset(e_)] = e_; lo["kind"] = "plank"
            else:
                ladder_edges.add(frozenset((c, o))); sc_side[frozenset((c, o))] = (c, o); lo["kind"] = "ladder"
            lo["short"] = len(p)
    # (라) 다른 길: 구역 바깥 면 → 바큇살에서 먼 바깥 고리 자리 (한 바퀴 = 큰 고리 → 가는 길 → 막장 → 바깥 고리 → 바큇살 → 큰 고리)
    far_ring = {r_ for r_ in ring_set if all(abs(r_[0] - s_[0]) + abs(r_[1] - s_[1]) >= 3 for s_ in spoke if s_ in ring_set or any(nb(s_, dd) in ring_set for dd in N4))}
    for lo in [l_ for l_ in lobes if l_]:
        k, rect, zz, inward = lo["k"], lo["rect"], lo["zz"], lo["inward"]
        outs = [(c, d) for c in rect for d in N4 if free(nb(c, d)) and zz[c] <= 1.9 and (N4[d][0] * inward[0] + N4[d][1] * inward[1]) < 0]
        rng.shuffle(outs)
        for c, d in outs[:1]:
            o = nb(c, d); p = connect([o], far_ring) or connect([o], ring_set)
            if p: kind[o] = "tun"; region[o] = k; carve(c, d); dig(p, "tun", k); lo["out"] = len(p)
    if sum(1 for lo in lobes if lo and lo["short"]) < 4 or not any(z["type"] == "pillar" for z in zones): return None

    # 채굴적(괴물 사는 곳): 케이지에서 가장 먼 기둥 방의 바깥쪽 칸 한 줄
    goaf = None
    for zn in sorted([z for z in zones if z["type"] == "pillar"], key=lambda z: -math.hypot(*xy((z["i0"] + z["w"] / 2, z["j0"] + z["h"] / 2)))):
        cy = zn["j0"] + zn["h"] / 2 - PJ
        side = "N" if cy > 0 else "S"
        row = [(i, zn["j0"] + zn["h"] if side == "N" else zn["j0"] - 1) for i in range(zn["i0"], zn["i0"] + zn["w"])]
        if all(free(c) for c in row):
            for c in row: kind[c] = "goaf"
            goaf = (zn, side, row); break

    # ---- 굴 뻗기 (옛 조립기 횡갱) — 부채꼴 안에서만, 바큇살·지름길에는 안 붙는다
    def area_est():
        a = sum(CELL * 2.2 for c, v in kind.items() if v in CORR)
        a += sum(len(z["cells"]) * CELL * (AIS - 1.2) * 2 for z in zones)
        return a + sum((bw - 1.2) * (bh - 1.2) for _, bw, bh, _ in rooms.values())
    target = 2 * MAP2_AREA * rng.uniform(1.0, 1.15)
    for _ in range(3000):
        if area_est() >= target: break
        cands = [c for c, v in kind.items() if v in ("ring", "tun", "inner") and c not in spoke and any(free(nb(c, d)) for d in N4)]
        if not cands: break
        cur = rng.choice(cands); sk = sector(cur); h = rng.choice([d for d in N4 if free(nb(cur, d))])
        for _ in range(rng.randint(3, 10)):
            if rng.random() < TURN_P:
                h = {"N": {"L": "W", "R": "E"}, "S": {"L": "E", "R": "W"}, "E": {"L": "N", "R": "S"}, "W": {"L": "S", "R": "N"}}[h][rng.choice("LR")]
            n_ = nb(cur, h)
            if free(n_) and sector(n_) == sk:
                kind[n_] = "tun"; region[n_] = reg(cur); carve(cur, h); cur = n_
            elif kind.get(n_) in ("ring", "tun", "inner") and n_ not in spoke and reg(n_) == reg(cur) and h not in opn.get(cur, ()) and rng.random() < LOOP_P:
                carve(cur, h); break
            else:
                break

    # ---- 막다른 굴 줄이기: 옆 굴에 잇거나(BRAID) 1 칸만 남기고 자른다 (바큇살·지름길에는 안 잇는다 — 판자벽을 돌아가는 길이 생긴다)
    def deg(c): return len(opn.get(c, ()))
    changed = True
    while changed:
        changed = False
        for c in [c for c, v in kind.items() if v == "tun" and deg(c) == 1 and c not in spoke]:
            if deg(c) != 1: continue
            joins = [d for d in N4 if d not in opn[c] and nb(c, d) not in spoke and reg(nb(c, d)) == reg(c) and (kind.get(nb(c, d)) in ("ring", "tun", "inner", "lit") or (kind.get(nb(c, d)) == "zone" and zones[zone_of[nb(c, d)]]["z"][nb(c, d)] <= 1.9))]
            if joins and rng.random() < BRAID:
                carve(c, rng.choice(joins)); changed = True
            else:
                (d0,) = opn[c]; o = nb(c, d0)
                if kind.get(o) == "tun" and deg(o) == 2 and o not in spoke:
                    uncarve(c); changed = True
    # 광장에서 닿지 않는 굴은 뺀다 (문 연 채로)
    def reach(closed):
        seen, stack = set(rooms["plaza"][0]), list(rooms["plaza"][0])
        while stack:
            c = stack.pop()
            for d in opn.get(c, ()):
                n_ = nb(c, d)
                if closed and (frozenset((c, n_)) in door_edges or frozenset((c, n_)) in ladder_edges): continue
                if n_ not in seen: seen.add(n_); stack.append(n_)
            grp = rooms[zone_of[c]][0] if kind.get(c) == "room" else zones[zone_of[c]]["cells"] if kind.get(c) == "zone" else ()
            for c2 in grp:
                if c2 not in seen: seen.add(c2); stack.append(c2)
        return seen
    seen = reach(False)
    for c in [c for c, v in kind.items() if v in CORR and c not in seen]: uncarve(c)
    shut = reach(True)                                                    # 문 닫힌 채(처음 들어온 사람)로도 구역·방 전부 닿아야 한다
    if any(z["cells"][0] not in shut for z in zones) or any(rooms[r][0][0] not in shut for r in rooms): return None

    # ================= 표로 바꾸기 (booth_table.build() 형식)
    J = {c: (rng.uniform(-JIT, JIT), rng.uniform(-JIT, JIT)) for c in kind}
    def P(c, z=0.0):
        x, y = xy(c)
        return (x + J[c][0], y + J[c][1], z) if kind.get(c) in CORR else (x, y, z)
    def zc(c): return zones[zone_of[c]]["z"][c] if kind.get(c) == "zone" else 0.0
    T, R, PIL = [], [], []
    near_plaza = lambda c: min(abs(c[0] - rc[0]) + abs(c[1] - rc[1]) for rc in rooms["plaza"][0]) <= 2
    def light(cells): return "L" if all(kind.get(c) == "lit" for c in cells) else "D" if any(near_plaza(c) for c in cells) else "K"
    # 굴 사슬: 갈림(면 ≠ 2)·종류가 바뀌는 칸에서 끊는다
    corr = [c for c, v in kind.items() if v in CORR]
    shortcut_e = door_edges | ladder_edges
    def node(c): return deg(c) != 2 or any(kind.get(nb(c, d)) not in CORR or frozenset((c, nb(c, d))) in shortcut_e for d in opn[c])
    done = set(); chains = []
    for c in corr:
        if not node(c): continue
        for d in opn[c]:
            n_ = nb(c, d)
            if kind.get(n_) not in CORR or (c, d) in done or frozenset((c, n_)) in shortcut_e: continue
            ch = [c]; prev = c; cur = n_
            done.add((c, d))
            while True:
                ch.append(cur)
                if node(cur): break
                d2 = next(d_ for d_ in opn[cur] if nb(cur, d_) != prev)
                prev, cur = cur, nb(cur, d2)
            done.add((cur, next(d_ for d_ in N4 if nb(cur, d_) == prev)))
            chains.append(ch)
    loops_left = [c for c in corr if not node(c) and not any(c in ch for ch in chains)]
    while loops_left:                                                     # 갈림 없는 고리 (있으면)
        c = loops_left[0]; ch = [c]; prev = None; cur = c
        while True:
            d2 = next(d_ for d_ in opn[cur] if nb(cur, d_) != prev); prev, cur = cur, nb(cur, d2)
            ch.append(cur)
            if cur == c: break
        chains.append(ch); loops_left = [x for x in loops_left if x not in ch]
    for k, ch in enumerate(chains):
        ringy = all(kind[c] == "ring" for c in ch)
        w = 3.6 if ringy else 3.0 if all(kind[c] == "lit" for c in ch) else rng.choice([2.8, 3.0, 3.2, 3.4])
        pts = [(*P(c)[:2], 0.0, w) for c in ch]
        for e_, e2 in ((0, 1), (-1, -2)):                                    # 막다른 끝은 칸 가운데보다 1.5 m 당긴다 (흔들기까지 9 m 넘던 것 — 기준 8 m)
            if deg(ch[e_]) == 1:
                a_, b_ = np.array(pts[e2][:2]), np.array(pts[e_][:2]); L_ = np.linalg.norm(b_ - a_)
                pts[e_] = (*(b_ - (b_ - a_) / L_ * min(1.5, L_ * 0.3)), 0.0, w)
        T.append(("t%d" % k if not ringy else "ring_%d" % k, pts, 3.4 if ringy else 3.2, True, True, light(ch), "tunnel"))
    # 문: 굴 칸 → 방·구역 칸 (구역 쪽 바닥으로 비탈) · 지름길 판자벽(scdoor_) · 사다리(ladder_) — 문 닫힌 재기에서는 이것들을 뺀다
    shortcuts = []
    for c in corr:
        for d in opn[c]:
            o = nb(c, d)
            if frozenset((c, o)) in door_edges and kind.get(o) in CORR and c < o:
                T.append(("scdoor_%d" % len(shortcuts), [(*P(c)[:2], 0.0, 3.0), (*P(o)[:2], 0.0, 3.0)], 3.2, True, True, light([c, o]), "tunnel"))
                a_, b_ = sc_side[frozenset((c, o))]; shortcuts.append(("scdoor_%d" % (len(shortcuts)), "plank", P(a_), P(b_)))
            elif frozenset((c, o)) in door_edges and kind.get(o) in ("room",):
                T.append(("scdoor_%d" % len(shortcuts), [(*P(c)[:2], 0.0, 3.0), (*P(o)[:2], 0.0, 3.0)], 3.2, True, True, light([c]), "tunnel"))
                a_, b_ = sc_side[frozenset((c, o))]; shortcuts.append(("scdoor_%d" % (len(shortcuts)), "plank", P(a_), P(b_)))
            elif frozenset((c, o)) in ladder_edges:
                T.append(("ladder_%d" % len(shortcuts), [(*P(c)[:2], 0.0, 2.6), (*P(o)[:2], zc(o), 2.6)], 3.2, True, True, "K", "tunnel"))
                shortcuts.append(("ladder_%d" % (len(shortcuts)), "ladder", P(o, zc(o)), P(c)))   # (막장 쪽 = 비탈 꼭대기, 집 쪽 = 사다리 밑)
            elif kind.get(o) in ("room", "zone"):
                w = 3.3 if kind[o] == "room" else 2.8
                T.append(("door_%d_%d_%s" % (c[0], c[1], d), [(*P(c)[:2], 0.0, w), (*P(o)[:2], zc(o), w)], 3.2, True, True, light([c]), "tunnel"))
    # 방
    for name, (cells, bw, bh, h) in rooms.items():
        cx = sum(xy(c)[0] for c in cells) / len(cells); cy = sum(xy(c)[1] for c in cells) / len(cells)
        R.append((name, cx - bw / 2, cx + bw / 2, cy - bh / 2, cy + bh / 2, 0.0, h, "L"))
    # 구역: 기둥 방 = 통로 상자(booth_table zone_grid 처럼) · 비탈 = 굴(오르는 세로 줄 + 받침 높이의 가로 줄, zone_slope 처럼)
    Z = {}
    for k, zn in enumerate(zones):
        xs = sorted({xy(c)[0] for c in zn["cells"]}); ys = sorted({xy(c)[1] for c in zn["cells"]})
        Z["Z%d" % k] = dict(type=zn["type"], x0=xs[0] - AIS / 2, x1=xs[-1] + AIS / 2, y0=ys[0] - AIS / 2, y1=ys[-1] + AIS / 2, xs=xs, ys=ys)
        if zn["type"] == "pillar":
            R.extend([("room_c", x - AIS / 2, x + AIS / 2, ys[0] - AIS / 2, ys[-1] + AIS / 2, 0.0, 3.0, "K") for x in xs])
            R.extend([("room_r", xs[0] - AIS / 2, xs[-1] + AIS / 2, y - AIS / 2, y + AIS / 2, 0.0, 3.0, "K") for y in ys])
        else:
            zz = lambda y: zn["z"][(round(xs[0] / CELL + PI), round(y / CELL + PJ))]
            order = ys if zn["climb"][1] > 0 else ys[::-1]
            for i, x in enumerate(xs):
                pts = []
                for q, y in enumerate(order):
                    u = zn["climb"][1]
                    if q > 0: pts.append((x, y - u * bt.LANDING / 2, zz(y), 2.6))
                    pts.append((x, y, zz(y), 2.6))
                    if q < len(order) - 1: pts.append((x, y + u * bt.LANDING / 2, zz(y), 2.6))
                T.append(("Z%d_col%d" % (k, i), pts, 2.9, True, True, "K", "tunnel"))
            for q, y in enumerate(ys):
                T.append(("Z%d_row%d" % (k, q), [(xs[0], y, zz(y), 2.6), (xs[-1], y, zz(y), 2.6)], 2.9, True, True, "K", "tunnel"))
        for a in xs[:-1]:
            for b in ys[:-1]:
                PIL.append((a + AIS / 2, a + CELL - AIS / 2, b + AIS / 2, b + CELL - AIS / 2))
    if goaf:
        zn, side, row = goaf; k = zones.index(zn); zx = Z["Z%d" % k]
        g = (zx["y1"] - 0.2, zx["y1"] + 5.5) if side == "N" else (zx["y0"] - 5.5, zx["y0"] + 0.2)
        R.append(("goaf", zx["x0"], zx["x1"], g[0], g[1], 0.0, 3.4, "K"))
    # 가짜 출구
    fx, fy, _ = P(fake_root)
    T.append(("fake_exit", [(fx, fy, 0.0, 3.0), (fx, fy + 5.0, 0.0, 3.0), (fx, fy + 21.0, 16.0 * math.tan(math.radians(25)), 3.0)], 3.2, True, True, "K", "tunnel"))

    # ---- 사람만 지나가는 길: 굴 두 칸 사이에 바위 한 칸, 굴로 돌면 먼(≥ 5 칸) 곳 → 뚫린 바위 틈 · 개구멍
    from collections import deque
    def graph_dist(a, b, cap=40):
        q = deque([(a, 0)]); seen_ = {a}
        while q:
            c, dd = q.popleft()
            if c == b: return dd
            if dd >= cap: continue
            for d in opn.get(c, ()):
                n_ = nb(c, d)
                if n_ not in seen_: seen_.add(n_); q.append((n_, dd + 1))
        return 99
    pairs = []                                                            # 반대편은 굴 · 방 · 구역 통로(바닥 1.9 m 이하) 다 된다 (굴끼리만이면 맵마다 1 곳뿐이었다)
    def ok_end(e): return kind.get(e) in CORR + ("room",) or (kind.get(e) == "zone" and zones[zone_of[e]]["z"][e] <= 1.9)
    for c in corr:
        for d in N4:
            m_, e = nb(c, d), nb(nb(c, d), d)
            if free(m_) and ok_end(e) and all(free(nb(m_, s)) or ok_end(nb(m_, s)) for s in N4):
                gd = graph_dist(c, e)
                if gd >= 4: pairs.append((gd + rng.random(), c, e))
    pairs.sort(reverse=True); picked = []
    for gd, a, b in pairs:
        if len(picked) >= 9: break
        if all(min(abs(a[0] - p[1][0]) + abs(a[1] - p[1][1]), abs(b[0] - p[2][0]) + abs(b[1] - p[2][1])) >= 4 for p in picked): picked.append((gd, a, b))
    crev = []
    for n, (gd, a, b) in enumerate(picked):
        name = ("c_%d" % n)
        T.append((name, [(*P(a)[:2], 0.0, bt.CRAWL_W), (*P(b)[:2], zc(b), bt.CRAWL_W)], bt.CRAWL_H, False, False, "K", "crawl"))
        if crevices and n < 5: crev.append(bt.through_crevice(T, name))        # 먼 것 다섯 = 뚫린 바위 틈, 나머지 = 개구멍
    # 막힌 바위 틈: 긴 굴 벽, 뒤로 한 칸이 바위인 곳 (12 곳, 서로 3 칸 넘게)
    if crevices:
        spots = []
        for ch_i, ch in enumerate(chains):
            for c in ch[1:-1]:
                for d in N4:
                    if d in opn[c] or not free(nb(c, d)) or not free(nb(nb(c, d), d)) and inside(nb(nb(c, d), d)): continue
                    if any(kind.get(nb(nb(c, d), s)) not in (None,) for s in N4 if s != OPP[d]): continue
                    spots.append((rng.random(), c, d, T[ch_i][1][0][3]))
        spots.sort(); used = []
        for _, c, d, w in spots:
            if len(used) >= 12: break
            if any(abs(c[0] - u[0]) + abs(c[1] - u[1]) < 4 for u in used): continue
            n_ = np.array(N4[d], float); wall = np.array(P(c)[:2]) + n_ * w / 2
            crev.append(bt.closed_crevice(T, "cr_%d" % len(used), wall, n_, 0.0)); used.append(c)
    bt.add_niches(T, R, maxgap=NICHE_GAP)

    # ---- 큰 틈(괴물) 8: 막다른 끝 먼저, 모자라면 케이지에서 먼 고리 칸
    dead = [c for c in corr if deg(c) == 1]
    far_ring = sorted(ring_set, key=lambda c: -math.hypot(*xy(c)))
    gap_cells = (dead + [c for c in far_ring if all(abs(c[0] - g[0]) + abs(c[1] - g[1]) >= 5 for g in dead)])
    gaps = []
    for c in gap_cells:
        if len(gaps) >= 8: break
        if all(abs(c[0] - g[0]) + abs(c[1] - g[1]) >= 5 for g in gaps): gaps.append(c)
    px, py = xy((PI, PJ))
    home = next(r for r in R if r[0] == "plaza")
    # 막장까지: 처음(문 닫힘) 광장 → 막장 · 지름길을 연 뒤 막장 → 광장 (칸 걸음 × 8 m)
    from collections import deque
    def steps(closed):
        dist = {c: 0 for c in rooms["plaza"][0]}; q = deque(rooms["plaza"][0])
        while q:
            c = q.popleft()
            nxt = [nb(c, d) for d in opn.get(c, ()) if not (closed and frozenset((c, nb(c, d))) in shortcut_e)]
            nxt += rooms[zone_of[c]][0] if kind.get(c) == "room" else zones[zone_of[c]]["cells"] if kind.get(c) == "zone" else []
            for n_ in nxt:
                if n_ not in dist: dist[n_] = dist[c] + (0 if kind.get(n_) == kind.get(c) == "room" and zone_of.get(n_) == zone_of.get(c) else 1); q.append(n_)
        return dist
    d_shut, d_open = steps(True), steps(False)
    lobe_d = [(d_shut[lo["goal"]] * CELL, d_open[lo["goal"]] * CELL, lo["kind"]) for lo in lobes if lo and lo["short"] and lo["goal"] in d_shut]
    n_long = sum(1 for lo in lobes if lo and lo["short"] and lo.get("long_cells"))
    return dict(T=T, R=R, PILLARS=PIL, Z=Z, zones=zones, gap_big=[P(c) for c in gaps], crevices=crev, through={c[0] for c in crev if c[1] == "through"},
                long_paths=[[P(c)[:2] for c in lo["long_cells"]] for lo in lobes if lo and lo.get("long_cells")],
                sc_paths=[[P(c)[:2] for c in lo["sc_cells"]] for lo in lobes if lo and lo.get("sc_cells")],
                n_long=n_long, shortcuts=shortcuts, goals=[(P(lo["goal"], zc(lo["goal"])), lo["kind"]) for lo in lobes if lo], lobe_d=lobe_d, n_spokes=len(spoke_ang),
                home_rect=(home[1], home[2], home[3], home[4]), home_rooms=("plaza",), small_gaps=[], goaf=goaf is not None,
                fake_end=T[[t[0] for t in T].index("fake_exit")][1][-1], spawn_player=(px, py, 0.05), seed=seed, cells=len(corr))


def closed_map(m):
    """지름길 문(판자벽 · 사다리)이 닫힌 맵 — 처음 들어온 사람"""
    return dict(m, T=[t for t in m["T"] if not t[0].startswith(("scdoor_", "ladder_"))])


def score(m):
    """거르는 값 (map2_plan.py 와 같은 재기). 길 잃고 걷기는 지름길 문을 닫은 채(처음 들어온 사람)와 연 채 둘 다"""
    import map2_plan as mp
    r = mp.measure(m, limit=425.0)                                        # 모양 값(넓이 · 고리 · 막다른 · 가장 긴)은 문 연 맵 — 닫힌 판자벽 앞 굴은 걷어차 여는 자리라 막다른 굴로 안 친다
    r["within_open"] = r["within"]; r["within"] = mp.wander(closed_map(m), limit=425.0)["within"]   # 길 잃고 걷기: 문 닫힘(처음 들어온 사람)
    d = m["lobe_d"]; r["first"] = float(np.mean([a for a, b, k in d])); r["back"] = float(np.mean([b for a, b, k in d])); r["n_short"] = len(d)
    up = any(z["type"] == "pillar" and z["ys"][0] > 0 for z in m["Z"].values()); down = any(z["type"] == "pillar" and z["ys"][-1] < 0 for z in m["Z"].values())
    r["pillar_up_down"] = up and down
    r["ok"] = (0.9 * 2 * MAP2_AREA <= r["area"] <= 1.1 * 2 * MAP2_AREA and r["dead"] <= 8.0 and r["longest"] <= 15.0 and r["pillar_up_down"] and m["goaf"]
               and r["n_short"] >= 4 and r["first"] >= 1.8 * r["back"] and m["n_long"] >= max(3, r["n_short"] - 1))   # 지름길 있는 로브는 (하나 빼고) 가는 길도 있어야 — 없으면 고리가 반쪽      # 로브 판(09-26): 짧은 고리 · 길 잃고 걷기는 거르지 않고 값으로 보인다 (가는 길을 길게 한 값)
    return r


def one(s):
    m = build(s)
    return (s, m, score(m) if m is not None else None)


def draw(ms, rs, out):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1500, 1060; cols = 2; rows = (len(ms) + 1) // 2
    img = Image.new("RGB", (W * cols, H * rows), "#2c2926"); d = ImageDraw.Draw(img)
    Fn = lambda sz, b=False: ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if b else "C:/Windows/Fonts/malgun.ttf", int(sz))
    COL = {"L": "#efd68e", "D": "#d6cdb6", "K": "#aaa290"}
    for n, (m, r) in enumerate(zip(ms, rs)):
        xs_ = [p[0] for t in m["T"] for p in t[1]]; ys_ = [p[1] for t in m["T"] for p in t[1]]
        S = min((W - 60) / (max(xs_) - min(xs_)), (H - 150) / (max(ys_) - min(ys_)))
        OX = (n % cols) * W + W / 2 - S * (max(xs_) + min(xs_)) / 2; OY = (n // cols) * H + 110 + S * max(ys_)
        P = lambda x, y: (OX + S * x, OY - S * y)
        def poly(pts, w, col):
            q = [P(*p[:2]) for p in pts]; d.line(q, fill=col, width=max(1, int(w * S)), joint="curve")
            for X, Y in q: rr = w * S / 2; d.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=col)
        def rect(x0, x1, y0, y1, col): d.rectangle([P(x0, y1), P(x1, y0)], fill=col)
        def dot(x, y, col, rr=5): X, Y = P(x, y); d.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=col, outline="#1d1b19")
        for t in m["T"]:
            if t[6] == "tunnel": poly(t[1], t[1][0][3], COL[t[5]])
        for rr_ in m["R"]:
            if rr_[0] == "goaf": rect(rr_[1], rr_[2], rr_[3], rr_[4], "#4a4540")
            else: rect(rr_[1], rr_[2], rr_[3], rr_[4], "#7fd67f" if rr_[0] == "plaza" else COL[rr_[7]])
        for x0, x1, y0, y1 in m["PILLARS"]: rect(x0, x1, y0, y1, "#3a3632")
        for t in m["T"]:
            if t[6] == "niche": poly(t[1], 1.1, "#3d8fe0")
            if t[6] == "crawl": poly(t[1], 0.9, "#9ff0ff")
            if t[6] == "crevice": poly(t[1], 0.9, "#19d9c8" if t[0] in m["through"] else "#f04fbf")
            if t[6] == "crevice_room": poly(t[1], 1.4, "#f04fbf")
        for g in m["gap_big"]: dot(g[0], g[1], "#d33c2c", 7)
        for pth in m.get("long_paths", []):                                 # 가는 길(주황 점선) · 지름길(하늘색) — 로브가 보이게
            q = [P(*p_) for p_ in pth]
            for a_, b_ in zip(q, q[1:]):
                L_ = math.dist(a_, b_); n_ = max(1, int(L_ / 14))
                for i in range(0, n_, 2): d.line([a_[0] + (b_[0] - a_[0]) * i / n_, a_[1] + (b_[1] - a_[1]) * i / n_, a_[0] + (b_[0] - a_[0]) * (i + 1) / n_, a_[1] + (b_[1] - a_[1]) * (i + 1) / n_], fill="#ffb05c", width=5)
        for pth in m.get("sc_paths", []): d.line([P(*p_) for p_ in pth], fill="#9fd0ff", width=5)
        for name, kd, lob, hom in m.get("shortcuts", []):                 # 한쪽 문: 흰 화살표 = 열리는 쪽(막장 → 집) · 판자벽 = 주황 막대 · 사다리 = 노란 사다리
            (ax, ay), (bx, by) = P(lob[0], lob[1]), P(hom[0], hom[1])
            mx, my = (ax + bx) / 2, (ay + by) / 2; L = math.hypot(bx - ax, by - ay) or 1; ux, uy = (bx - ax) / L, (by - ay) / L
            if kd == "plank":
                d.line([mx - uy * 15, my + ux * 15, mx + uy * 15, my - ux * 15], fill="#ff8c1a", width=10)
            else:
                for sg in (-1, 1): d.line([ax - uy * 7 * sg, ay + ux * 7 * sg, bx - uy * 7 * sg, by + ux * 7 * sg], fill="#ffe066", width=3)
                for t in (0.2, 0.4, 0.6, 0.8):
                    qx, qy = ax + (bx - ax) * t, ay + (by - ay) * t; d.line([qx - uy * 7, qy + ux * 7, qx + uy * 7, qy - ux * 7], fill="#ffe066", width=3)
            hx, hy = mx + ux * 14, my + uy * 14
            d.polygon([(hx + ux * 12, hy + uy * 12), (hx - uy * 8, hy + ux * 8), (hx + uy * 8, hy - ux * 8)], fill="#ffffff")
        for g, kd in m.get("goals", []):
            X, Y = P(g[0], g[1])
            d.polygon([(X + 14 * math.cos(math.pi / 2 + i * math.pi / 5) * (1 if i % 2 == 0 else 0.45), Y - 14 * math.sin(math.pi / 2 + i * math.pi / 5) * (1 if i % 2 == 0 else 0.45)) for i in range(10)], fill="#ffd23f", outline="#1d1b19")
        fe = m["fake_end"]; rect(fe[0] - 1.6, fe[0] + 1.6, fe[1] - 0.2, fe[1] + 1.4, "#ff9c7a")
        for zk, z in m["Z"].items():
            lab = {"pillar": "기둥 방", "slope15": "채탄장 15°", "slope25": "노보리 25°"}[z["type"]]
            X, Y = P((z["x0"] + z["x1"]) / 2, z["y1"] + 3); d.text((X, Y), lab, font=Fn(15, True), fill="#f4f1ea", anchor="mm")
        X, Y = P(0, 0); d.text((X, Y), "케이지", font=Fn(14, True), fill="#1d1b19", anchor="mm")
        x0 = (n % cols) * W + 24; y0 = (n // cols) * H + 14
        d.text((x0, y0), "후보 %s — 시드 %d" % ("ABCD"[n], m["seed"]), font=Fn(24, True), fill="#f4f1ea")
        lines = ["막장까지 처음(문 닫힘) %.0f m → 지름길 열면 %.0f m (%.1f 배 짧음) · 로브 %d (가는 길 %d)" % (r["first"], r["back"], r["first"] / r["back"], r["n_short"], m["n_long"]),
                 "바닥 %.0f m² (MAP2 의 %.1f 배) · 짧은 고리 %d · 숨을 곳 %d · 기둥 방 %d · 비탈 %d" % (r["area"], r["area"] / MAP2_AREA, r["small"], r["hides"],
                 sum(z["type"] == "pillar" for z in m["Z"].values()), sum(z["type"] != "pillar" for z in m["Z"].values())),
                 "길 잃고 425 m 안에 정거장 %.0f %% (지름길 다 열면 %.0f %%) · 막다른 굴 %.0f m · 갈림 없는 가장 긴 굴 %.0f m" % (r["within"], r["within_open"], r["dead"], r["longest"])]
        for i, s in enumerate(lines): d.text((x0, y0 + 36 + i * 22), s, font=Fn(15), fill=("#ffb05c", "#efd68e", "#7fd67f")[min(i, 2)])
        sx, sy = P(-100, -70); d.line([sx, sy, sx + 30 * S, sy], fill="#f4f1ea", width=3); d.text((sx + 15 * S, sy + 14), "30 m", font=Fn(13), fill="#f4f1ea", anchor="mm")
    lx, ly = 24, H * rows - 30
    for i, (c, s) in enumerate([("#7fd67f", "케이지 광장"), ("#efd68e", "불 켜진 방·길"), ("#aaa290", "어두운 굴"), ("#3a3632", "기둥(바위)"), ("#4a4540", "채굴적(괴물 집)"),
                                ("#3d8fe0", "대피소"), ("#9ff0ff", "개구멍"), ("#19d9c8", "뚫린 바위 틈"), ("#f04fbf", "막힌 바위 틈"), ("#d33c2c", "큰 틈(괴물)"), ("#ff9c7a", "가짜 출구 끝"), ("#ffd23f", "막장(광맥)"), ("#ffb05c", "가는 길"), ("#9fd0ff", "지름길"), ("#ff8c1a", "판자벽"), ("#ffe066", "사다리")]):
        X = lx + i * 185; d.rectangle([X, ly - 8, X + 16, ly + 8], fill=c); d.text((X + 22, ly), s, font=Fn(14), fill="#f4f1ea", anchor="lm")
    img.save(out); print("saved", out)



def draw_schema(out):
    """구조도 (로브 판, 09-26): 기법이 맵 어디에 들어갔는지 — 뼈대만, 크기는 어림"""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 2600, 1500
    img = Image.new("RGB", (W, H), "#2c2926"); d = ImageDraw.Draw(img)
    Fn = lambda sz, b=False: ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if b else "C:/Windows/Fonts/malgun.ttf", int(sz))
    CX, CY = 760, 800
    def pol(r, a): return (CX + r[0] * math.cos(a), CY - r[1] * math.sin(a))
    def ell(rx, ry, col, w): d.ellipse([CX - rx, CY - ry, CX + rx, CY + ry], outline=col, width=w)
    def txt(x, y, s, sz=20, col="#f4f1ea", b=True, anchor="mm"): d.text((x, y), s, font=Fn(sz, b), fill=col, anchor=anchor)
    def arrow(x0, y0, x1, y1, col, w=4):
        d.line([x0, y0, x1, y1], fill=col, width=w); L = math.hypot(x1 - x0, y1 - y0) or 1; ux, uy = (x1 - x0) / L, (y1 - y0) / L
        d.polygon([(x1 + ux * 14, y1 + uy * 14), (x1 - uy * 9, y1 + ux * 9), (x1 + uy * 9, y1 - ux * 9)], fill=col)
    def star(X, Y, r=16): d.polygon([(X + r * math.cos(math.pi / 2 + i * math.pi / 5) * (1 if i % 2 == 0 else 0.45), Y - r * math.sin(math.pi / 2 + i * math.pi / 5) * (1 if i % 2 == 0 else 0.45)) for i in range(10)], fill="#ffd23f", outline="#1d1b19")
    RO, RI = (640, 560), (230, 190)
    ell(*RO, "#aaa290", 26); ell(*RI, "#d6cdb6", 22)                          # 바깥 고리 · 큰 고리
    for a in (90, 25, -35, -90, -145, 155): d.line([pol(RI, math.radians(a)), pol(RO, math.radians(a))], fill="#c9c1ad", width=18)
    for a in (60, 120, 180, 0): d.line([pol((70, 45), math.radians(a)), pol(RI, math.radians(a))], fill="#d6cdb6", width=16)   # 광장 → 큰 고리 넷
    d.rectangle([CX - 80, CY - 45, CX + 80, CY + 45], fill="#7fd67f"); txt(CX, CY, "케이지 광장", 22, "#1d1b19")
    for dx in (-150, 0, 150): d.rectangle([CX + dx - 45, CY + 110, CX + dx + 45, CY + 150], fill="#efd68e")
    d.line([CX, CY + 45, CX, CY + 110], fill="#efd68e", width=12); d.line([CX - 150, CY + 105, CX + 150, CY + 105], fill="#efd68e", width=12)
    txt(CX - 250, CY + 130, "불 켜진 방 셋", 17, "#efd68e", True, "rm")
    for a_deg, kd in ((57, "plank"), (-5, "plank"), (-62, "ladder"), (125, "plank")):   # 로브 넷을 자세히
        a = math.radians(a_deg); zx, zy = pol((430, 375), a); g = 58
        d.rectangle([zx - g, zy - g, zx + g, zy + g], fill="#aaa290")
        for i in (-1, 1):
            for j in (-1, 1): d.rectangle([zx + i * 28 - 13, zy + j * 28 - 13, zx + i * 28 + 13, zy + j * 28 + 13], fill="#3a3632")
        star(zx + (g - 8) * math.cos(a), zy - (g - 8) * math.sin(a))
        pts = []                                                          # 가는 길: 큰 고리에서 옆으로 비껴 나가 구불구불 → 구역 옆면
        for t in np.linspace(0, 1, 40):
            ang_ = a + 0.32 * (1 - t) + 0.2 * t; rr = (RI[0] + 20 + 310 * t, RI[1] + 18 + 272 * t)
            pts.append(pol(rr, ang_ + 0.08 * math.sin(t * 18)))
        d.line(pts, fill="#e8b36a", width=8, joint="curve")
        d.line([(zx + g * math.cos(a + 0.5), zy - g * math.sin(a + 0.5)), pol(RO, a + 0.12)], fill="#c9c1ad", width=10)   # 다른 길 → 바깥 고리
        x0, y0 = zx - g * math.cos(a), zy + g * math.sin(a); x1, y1 = pol(RI, a)                      # 지름길: 구역 안쪽 면 → 큰 고리 (곧게) + 한쪽 문
        d.line([x0, y0, x1, y1], fill="#9fd0ff", width=10)
        L = math.hypot(x0 - x1, y0 - y1); ux, uy = (x1 - x0) / L, (y1 - y0) / L
        if kd == "plank":
            mx, my = x1 + (x0 - x1) * 0.15, y1 + (y0 - y1) * 0.15; d.line([mx - uy * 22, my + ux * 22, mx + uy * 22, my - ux * 22], fill="#ff8c1a", width=12)
        else:
            for sg in (-1, 1): d.line([x0 + (x1 - x0) * 0.2 - uy * 9 * sg, y0 + (y1 - y0) * 0.2 + ux * 9 * sg, x0 + (x1 - x0) * 0.5 - uy * 9 * sg, y0 + (y1 - y0) * 0.5 + ux * 9 * sg], fill="#ffe066", width=4)
            for t in (0.25, 0.32, 0.39, 0.46):
                qx, qy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t; d.line([qx - uy * 9, qy + ux * 9, qx + uy * 9, qy - ux * 9], fill="#ffe066", width=4)
        arrow(x0 + (x1 - x0) * 0.55, y0 + (y1 - y0) * 0.55, x0 + (x1 - x0) * 0.75, y0 + (y1 - y0) * 0.75, "#ffffff", 3)
    zx, zy = pol((430, 375), math.radians(125)); d.rectangle([zx - 58, zy - 88, zx + 58, zy - 62], fill="#4a4540"); txt(zx, zy - 102, "채굴적(괴물 집)", 16, "#d9a0e8")
    for a_deg in (70, 10, -20, -110, -170, 140, 200, 105):
        X, Y = pol(RO, math.radians(a_deg)); d.ellipse([X - 11, Y - 11, X + 11, Y + 11], fill="#d33c2c", outline="#1d1b19")
    fx, fy = pol(RO, math.radians(97)); d.line([fx, fy, fx, fy - 120], fill="#aaa290", width=16); d.rectangle([fx - 26, fy - 138, fx + 26, fy - 116], fill="#ff9c7a"); txt(fx + 34, fy - 128, "가짜 출구", 17, "#ff9c7a", True, "lm")
    txt(*pol((RO[0] + 70, RO[1] + 70), math.radians(-40)), "바깥 고리", 20, "#c9c1ad")
    txt(*pol((RI[0] - 70, RI[1] - 45), math.radians(150)), "큰 고리", 19, "#d6cdb6")
    bx_, by_ = pol((330, 290), math.radians(-90)); txt(bx_ + 22, by_, "바큇살", 18, "#c9c1ad", True, "lm")

    X0, Y0 = 1480, 60
    txt(X0, Y0, "MAP3 구조 — 바퀴 + 고리로 짜기 + 한쪽 문 지름길", 34, anchor="lm")
    txt(X0, Y0 + 48, "케이지로 내려와 막장에서 캐고, 사이렌이 울리면 케이지로 돌아온다", 20, "#c9c1ad", False, "lm")
    rows = [("바퀴 모양 (hub and spoke)", "있음 → 보강", "광장 → 큰 고리 → 바큇살 5~7 → 바깥 고리. 어디서 걷든 바큇살을 만나면 가운데로 온다."),
            ("꼬인 미로 (braid)", "있음", "막다른 굴은 옆 굴에 잇거나 한 칸만 남긴다(8 m 이하). 곁가지는 같은 로브 안에서만 잇는다."),
            ("큰 고리", "새로", "제안서 문법 2 에 있었는데 첫 판에 빠졌다. 불 켜진 길과 함께 광장 둘레를 한 바퀴 두른다."),
            ("고리로 짜기 (cyclic, Unexplored)", "새로", "바큇살 사이 칸마다 로브 하나: 큰 고리 → 가는 길(곧은 거리의 1.8 배 넘게 구불구불) → 막장 구역(기둥 · 광맥) → 다른 길(바깥 고리로)."),
            ("지름길 한쪽 문 (다크 소울)", "새로", "막장 구역에서 큰 고리로 곧장 온다. 판자벽은 막장 쪽에서만 걷어찬다(걷어차면 소리 — 소리를 내야 돈, 소리 내면 죽음). 비탈 구역은 꼭대기에서 사다리를 내린다."),
            ("아래 빈 바위", "채움", "아래쪽 부채꼴에도 로브가 들어가 불 켜진 방 둘레까지 채운다."),
            ("그대로 (고정)", "", "케이지 광장 가운데 · 불 켜진 방 셋 · 바깥 고리 · 가짜 출구. 괴물 집은 광장에서 가장 먼 기둥 방 바깥.")]
    y = Y0 + 110
    for name, st, desc in rows:
        txt(X0, y, name, 22, "#f4f1ea", True, "lm"); txt(X0 + 1000, y, st, 20, "#7fd67f" if st in ("새로", "채움") else "#efd68e", True, "rm")
        yy = y + 34; line = ""
        for w_ in desc.split(" "):
            if line and d.textlength(line + " " + w_, font=Fn(18, False)) > 1000: txt(X0, yy, line, 18, "#c9c1ad", False, "lm"); yy += 26; line = ""
            line = (line + " " + w_).strip()
        txt(X0, yy, line, 18, "#c9c1ad", False, "lm"); y = yy + 48
    y += 20
    for i, (kind_, col, s_) in enumerate([("line", "#e8b36a", "가는 길 — 큰 고리에서 비껴 나가 구불구불 막장 구역 옆면까지"), ("line", "#9fd0ff", "지름길 — 막장 구역 안쪽 면에서 큰 고리로 곧게"),
                                          ("line", "#c9c1ad", "다른 길 — 막장 구역 바깥 면에서 바깥 고리로"), ("bar", "#ff8c1a", "판자벽 (막장 쪽에서만 걷어차 연다)"),
                                          ("ladder", "#ffe066", "사다리 (비탈 꼭대기에서 내린다)"), ("star", "#ffd23f", "막장 (광맥)"), ("dot", "#d33c2c", "큰 틈 (괴물이 나오는 곳)"),
                                          ("arrow", "#ffffff", "문이 열리는 쪽 (막장 → 집). 집 쪽에서는 판자벽만 보인다")]):
        yy = y + i * 40; x_ = X0 + 30
        if kind_ == "line": d.line([x_ - 28, yy, x_ + 28, yy], fill=col, width=9)
        elif kind_ == "bar": d.line([x_, yy - 16, x_, yy + 16], fill=col, width=12)
        elif kind_ == "ladder":
            d.line([x_ - 20, yy - 7, x_ + 20, yy - 7], fill=col, width=4); d.line([x_ - 20, yy + 7, x_ + 20, yy + 7], fill=col, width=4)
            for t_ in (-12, -4, 4, 12): d.line([x_ + t_, yy - 7, x_ + t_, yy + 7], fill=col, width=4)
        elif kind_ == "star": star(x_, yy, 15)
        elif kind_ == "dot": d.ellipse([x_ - 11, yy - 11, x_ + 11, yy + 11], fill=col, outline="#1d1b19")
        else: arrow(x_ - 26, yy, x_ + 14, yy, col, 3)
        txt(X0 + 80, yy, s_, 18, "#f4f1ea", False, "lm")
    img.save(out); print("saved", out)

if __name__ == "__main__":
    import time
    if sys.argv[1:2] == ["pick"]:                                          # 고른 시드만 다시 그린다: python booth_gen.py pick 111 79 262 148
        seeds = [int(x) for x in sys.argv[2:]]; ms = [build(s_) for s_ in seeds]
        draw(ms, [score(m_) for m_ in ms], os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "build", "map3", "candidates.png")); sys.exit()
    if sys.argv[1:2] == ["schema"]:
        draw_schema(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "build", "map3", "schema.png")); sys.exit()
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 300; n_pick = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "build", "map3"); os.makedirs(out_dir, exist_ok=True)
    t0 = time.time(); rows = []; good = []
    from multiprocessing import Pool
    with Pool(max(1, os.cpu_count() - 2)) as pool:
        results = pool.map(one, range(1, n_seeds + 1))
    for s, m, r in results:
        if m is None: rows.append("%4d  (구역·방이 광장에서 안 닿음 — 버림)" % s); continue
        rows.append("%4d  바닥 %5.0f (%.2f 배) · 짧은 고리 %3d · 숨을 곳 %3d · 막다른 %4.1f m · 가장 긴 %4.1f m · 425 m 안 %3.0f %% (문 열면 %3.0f %%) · 막장 처음 %3.0f m / 지름길 %3.0f m · 기둥 위아래 %s · %s"
                    % (s, r["area"], r["area"] / MAP2_AREA, r["small"], r["hides"], r["dead"], r["longest"], r["within"], r["within_open"], r["first"], r["back"], r["pillar_up_down"], "OK" if r["ok"] else "-"))
        print(rows[-1], flush=True)
        if r["ok"]: good.append((m, r))
    open(os.path.join(out_dir, "seeds.txt"), "w", encoding="utf-8").write("\n".join(rows))
    print("시드 %d 개 %.0f s · 통과 %d" % (n_seeds, time.time() - t0, len(good)))
    pick = []                                                               # 서로 다른 것: 구역 수·종류가 다른 것부터
    for m, r in sorted(good, key=lambda g: -(g[1]["within"] + 0.2 * g[1]["small"])):
        sig = tuple(sorted(z["type"] for z in m["Z"].values()))
        if all(sig != tuple(sorted(z["type"] for z in p[0]["Z"].values())) for p in pick) or len(good) < n_pick * 2: pick.append((m, r))
        if len(pick) >= n_pick: break
    if pick: draw([p[0] for p in pick], [p[1] for p in pick], os.path.join(out_dir, "candidates.png"))
