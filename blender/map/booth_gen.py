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
GW, GH = 27, 21                 # 칸 수 (가로 · 세로) — 31 × 21 은 빈 바위가 넓게 남아 고리·바큇살·기둥 방만 보였다
CI, CJ = GW // 2, 10            # 케이지 광장 아래 가운데 칸 (광장 = CI-1..CI+1 × CJ..CJ+1)
PI, PJ = CI, CJ + 0.5           # → 세계 (0, 0)
JIT = 1.0                       # m, 굴 칸 가운데를 흔드는 폭 (격자처럼 안 보이게)
AIS = 3.0                       # m, 기둥 방 통로 폭 (booth_table zone_grid 와 같음) — 기둥 = 7 − 3 = 4 m 네모
TURN_P, LOOP_P, BRAID = 0.35, 0.8, 1.0
SPOKES = (6, 8)                 # 광장에서 고리까지 곧은 굴 수 (남쪽 불 켜진 길 말고). 길 잃은 사람이 돌아오는 시간 ≈ 굴 전체 길이 ÷ 광장 입구 수 — MAP2 는 굴 1,300 m 에 입구 5~6, MAP3 는 약 2,300 m (4~5 로는 425 m 안 평균 31 %)
ZONES = (4, 7)                  # 구역 수 (기둥 방 · 비탈) — 짧은 고리는 거의 다 기둥이다(둘레 21~24 m, 굴끼리 만든 고리는 대개 60 m 넘음). 3~6 이면 34~55, 기준 60
ZONE_SIZES = [(3, 3), (4, 3), (3, 4), (4, 4), (5, 4), (4, 5), (5, 5)]   # 섞는다 — 4~6 칸만 쓰면 크고 똑같은 방이 됐다
NICHE_GAP = 11.0                # m, 자동 대피소 간격 (MAP2 12.5 — 칸 격자에서는 옆 굴이 가까워 못 놓는 자리가 많아 줄인다)
MAP2_AREA = 3144.0              # map2_plan.py 로 잰 MAP2 v4 바닥 (m²)
N4 = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def xy(c): return ((c[0] - PI) * CELL, (c[1] - PJ) * CELL)
def nb(c, d): return (c[0] + N4[d][0], c[1] + N4[d][1])


def build(seed, crevices=True):
    rng = random.Random(seed)
    kind, opn, zone_of = {}, {}, {}     # 칸 → 종류 · 뚫린 면 · 구역 번호
    CORR = ("ring", "lit", "tun")
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

    # ---- 구역 (시드): 기둥 방 · 비탈(채탄장 15° · 노보리 25°). 칸 모두 통로, 기둥은 네 통로 사이 바위 4 × 4 m
    zones = []
    want = rng.randint(*ZONES)
    for _ in range(400):
        if len(zones) >= want: break
        typ = rng.choices(["pillar", "slope15", "slope25"], [0.6, 0.2, 0.2])[0]
        if typ != "pillar" and any(z["type"] == typ for z in zones): typ = "pillar"   # 비탈은 종류마다 하나까지
        w, h = rng.choice(ZONE_SIZES)
        i0, j0 = rng.randint(2, GW - 2 - w), rng.randint(2, GH - 2 - h)
        rect = [(i, j) for i in range(i0, i0 + w) for j in range(j0, j0 + h)]
        margin = [(i, j) for i in range(i0 - 1, i0 + w + 1) for j in range(j0 - 1, j0 + h + 1)]
        if any(c in kind for c in rect) or any(kind.get(c) not in (None, "ring") for c in margin): continue
        k = len(zones); cy = (j0 + (h - 1) / 2 - PJ) * CELL
        climb = None if typ == "pillar" else ((0, 1) if cy > 0 else (0, -1))                              # 가운데에서 먼 쪽으로 올라간다
        rise = {"pillar": 0.0, "slope15": (CELL - bt.LANDING) * math.tan(math.radians(15)), "slope25": (CELL - bt.LANDING) * math.tan(math.radians(25))}[typ]
        z = {}
        for c in rect:
            kind[c] = "zone"; zone_of[c] = k
            step = 0 if climb is None else ((c[1] - j0) if climb[1] > 0 else (j0 + h - 1 - c[1]))
            z[c] = step * rise
        for c in rect:
            for d in ("E", "N"):
                if nb(c, d) in z: carve(c, d)
        zones.append(dict(type=typ, i0=i0, j0=j0, w=w, h=h, climb=climb, z=z, cells=rect))
    if not any(z["type"] == "pillar" for z in zones): return None

    # 채굴적(괴물 사는 곳): 케이지에서 가장 먼 기둥 방의 바깥쪽 칸 한 줄
    goaf = None
    for zn in sorted([z for z in zones if z["type"] == "pillar"], key=lambda z: -math.hypot(*xy((z["i0"] + z["w"] / 2, z["j0"] + z["h"] / 2)))):
        cy = zn["j0"] + zn["h"] / 2 - PJ
        side = "N" if cy > 0 else "S"
        row = [(i, zn["j0"] + zn["h"] if side == "N" else zn["j0"] - 1) for i in range(zn["i0"], zn["i0"] + zn["w"])]
        if all(free(c) for c in row):
            for c in row: kind[c] = "goaf"
            goaf = (zn, side, row); break

    def connect(start_cells, targets, avoid_first=()):
        """start 에서 비어 있는 칸만 지나 targets(굴)까지 판다 — 칸마다 무게 1~3 을 뽑은 가장 짧은 길이라 조금씩 굽는다 (곧은 너비 우선은 자로 그은 굴이었다)"""
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
                for a, b in zip(path, path[1:]):
                    d = next(d for d in N4 if nb(a, d) == b)
                    if b not in kind: kind[b] = "tun"
                    carve(a, d)
                return True
            for d in N4:
                n_ = nb(c, d)
                if not inside(n_) or not (n_ in targets or (free(n_) and n_ not in avoid_first)): continue
                nc = cc + rng.uniform(1.0, 3.0)
                if nc < cost.get(n_, 1e9):
                    cost[n_] = nc; prev[n_] = c; heapq.heappush(q, (nc, rng.random(), n_))
        return False

    # 구역 문: 가장자리 통로 칸에서 밖으로 2~3 곳 (비탈은 낮은 쪽, 바닥 1.9 m 이하 — 밖은 바닥 0)
    for k, zn in enumerate(zones):
        edge = [(c, d) for c in zn["cells"] for d in N4 if nb(c, d) not in zn["z"] and zn["z"][c] <= 1.9 and kind.get(nb(c, d)) in (None, "ring", "tun")]
        rng.shuffle(edge); doors = []
        for c, d in edge:
            if len(doors) >= rng.randint(2, 3): break
            if any(abs(c[0] - e[0]) + abs(c[1] - e[1]) < 2 for e, _ in doors): continue
            o = nb(c, d)
            if not inside(o): continue
            if o not in kind: kind[o] = "tun"
            carve(c, d); doors.append((c, d))
            corr = {x for x, v in kind.items() if v in ("ring", "tun") and zone_of.get(x) is None} - {o}
            if kind[o] == "tun" and len(opn.get(o, ())) < 2: connect([o], corr)
        zn["doors"] = doors
    # 광장 출구 = 바큇살: 남쪽(불 켜진 길) 말고 SPOKES 곳, 각각 바깥 고리까지 곧게 (MAP2 "모든 길이 정거장으로" — 길 잃은 사람이 살에 닿으면 반은 안쪽으로 간다)
    exits = [((i, J + 1), "N") for i in (I - 1, I, I + 1)] + [((I - 1, j), "W") for j in (J, J + 1)] + [((I + 1, j), "E") for j in (J, J + 1)] + [((I - 1, J), "S"), ((I + 1, J), "S")]
    rng.shuffle(exits); n_ex = 0; n_want = rng.randint(*SPOKES); spoke = set()   # 바큇살 칸에는 옆길을 안 붙인다 (고속도로)
    for c, d in exits:
        if n_ex >= n_want: break
        o = nb(c, d)
        if kind.get(o) is not None or any(abs(x[0] - o[0]) + abs(x[1] - o[1]) < 2 for x in spoke if x in kind): continue   # 바큇살끼리 붙지 않게
        kind[o] = "tun"; carve(c, d); n_ex += 1
        before = set(kind); connect([o], ring_set); spoke.update({o} | (set(kind) - before))
    # 충전실 · 컴프레서실 뒷문 → 고리 (MAP2 처럼, 확률)
    for name, d in (("charge", "W"), ("comp", "E"), ("pump", "S")):
        if rng.random() < 0.7:
            cells = rooms[name][0]; c = max(cells, key=lambda c: c[0] * N4[d][0] + c[1] * N4[d][1] + rng.random() * 0.1)
            o = nb(c, d)
            if free(o):
                kind[o] = "tun"; carve(c, d); connect([o], {x for x, v in kind.items() if v in ("ring", "tun")} - {o})

    # ---- 굴 뻗기 (옛 조립기 횡갱): 있는 굴에서 아무 쪽으로 3~10 칸, 꺾기 TURN_P, 다른 굴에 닿으면 LOOP_P 로 고리
    def area_est():
        a = sum(CELL * 2.2 for c, v in kind.items() if v in CORR)
        a += sum(len(z["cells"]) * CELL * (AIS - 1.2) * 2 for z in zones)
        return a + sum((bw - 1.2) * (bh - 1.2) for _, bw, bh, _ in rooms.values())
    target = 2 * MAP2_AREA * rng.uniform(1.0, 1.15)                          # 어림값이 조금 작게 나온다 (0.95~1.1 이면 잰 바닥 1.8~1.9 배)
    for _ in range(3000):
        if area_est() >= target: break
        cands = [c for c, v in kind.items() if v in ("ring", "tun") and c not in spoke and any(free(nb(c, d)) for d in N4)]
        if not cands: break
        cur = rng.choice(cands); h = rng.choice([d for d in N4 if free(nb(cur, d))])
        for _ in range(rng.randint(3, 10)):
            dirs = [h] + ([rng.choice(["L", "R"])] if rng.random() < TURN_P else [])
            if len(dirs) > 1:
                h = {"N": {"L": "W", "R": "E"}, "S": {"L": "E", "R": "W"}, "E": {"L": "N", "R": "S"}, "W": {"L": "S", "R": "N"}}[h][dirs[1]]
            n_ = nb(cur, h)
            if free(n_):
                kind[n_] = "tun"; carve(cur, h); cur = n_
            elif kind.get(n_) in ("ring", "tun") and n_ not in spoke and h not in opn.get(cur, ()) and rng.random() < LOOP_P:
                carve(cur, h); break
            else:
                break

    # ---- 막다른 굴 줄이기: 옆 굴에 잇거나(BRAID) 1 칸만 남기고 자른다
    def deg(c): return len(opn.get(c, ()))
    changed = True
    while changed:
        changed = False
        for c in [c for c, v in kind.items() if v == "tun" and deg(c) == 1]:
            if deg(c) != 1: continue
            joins = [d for d in N4 if d not in opn[c] and nb(c, d) not in spoke and (kind.get(nb(c, d)) in CORR or (kind.get(nb(c, d)) == "zone" and zones[zone_of[nb(c, d)]]["z"][nb(c, d)] <= 1.9))]
            if joins and rng.random() < BRAID:
                carve(c, rng.choice(joins)); changed = True
            else:
                (d0,) = opn[c]; o = nb(c, d0)
                if kind.get(o) == "tun" and deg(o) == 2:
                    uncarve(c); changed = True
    # 광장에서 닿지 않는 굴은 뺀다
    seen, stack = set(rooms["plaza"][0]), list(rooms["plaza"][0])
    while stack:
        c = stack.pop()
        for d in opn.get(c, ()):
            n_ = nb(c, d)
            if n_ not in seen: seen.add(n_); stack.append(n_)
        if kind.get(c) == "room":
            for c2 in rooms[zone_of[c]][0]:
                if c2 not in seen: seen.add(c2); stack.append(c2)
        if kind.get(c) == "zone":
            for c2 in zones[zone_of[c]]["cells"]:
                if c2 not in seen: seen.add(c2); stack.append(c2)
    for c in [c for c, v in kind.items() if v in CORR and c not in seen]: uncarve(c)
    if any(z["cells"][0] not in seen for z in zones) or any(rooms[r][0][0] not in seen for r in rooms): return None

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
    def node(c): return deg(c) != 2 or any(kind.get(nb(c, d)) not in CORR for d in opn[c])
    done = set(); chains = []
    for c in corr:
        if not node(c): continue
        for d in opn[c]:
            n_ = nb(c, d)
            if kind.get(n_) not in CORR or (c, d) in done: continue
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
    # 문: 굴 칸 → 방·구역 칸 (구역 쪽 바닥으로 비탈)
    for c in corr:
        for d in opn[c]:
            o = nb(c, d)
            if kind.get(o) in ("room", "zone"):
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
    hb = rooms["plaza"]; home = next(r for r in R if r[0] == "plaza")
    return dict(T=T, R=R, PILLARS=PIL, Z=Z, zones=zones, gap_big=[P(c) for c in gaps], crevices=crev, through={c[0] for c in crev if c[1] == "through"},
                home_rect=(home[1], home[2], home[3], home[4]), home_rooms=("plaza",), small_gaps=[], goaf=goaf is not None,
                fake_end=T[[t[0] for t in T].index("fake_exit")][1][-1], spawn_player=(px, py, 0.05), seed=seed, cells=len(corr))


def score(m):
    """거르는 값 (map2_plan.py 와 같은 재기)"""
    import map2_plan as mp
    r = mp.measure(m, limit=425.0)
    up = any(z["type"] == "pillar" and z["ys"][0] > 0 for z in m["Z"].values()); down = any(z["type"] == "pillar" and z["ys"][-1] < 0 for z in m["Z"].values())
    r["pillar_up_down"] = up and down
    r["ok"] = (0.9 * 2 * MAP2_AREA <= r["area"] <= 1.1 * 2 * MAP2_AREA and r["small"] >= 60 and r["dead"] <= 8.0 and r["longest"] <= 15.0
               and r["within"] >= 40.0 and r["pillar_up_down"] and m["goaf"])
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
        fe = m["fake_end"]; rect(fe[0] - 1.6, fe[0] + 1.6, fe[1] - 0.2, fe[1] + 1.4, "#ff9c7a")
        for zk, z in m["Z"].items():
            lab = {"pillar": "기둥 방", "slope15": "채탄장 15°", "slope25": "노보리 25°"}[z["type"]]
            X, Y = P((z["x0"] + z["x1"]) / 2, z["y1"] + 3); d.text((X, Y), lab, font=Fn(15, True), fill="#f4f1ea", anchor="mm")
        X, Y = P(0, 0); d.text((X, Y), "케이지", font=Fn(14, True), fill="#1d1b19", anchor="mm")
        x0 = (n % cols) * W + 24; y0 = (n // cols) * H + 14
        d.text((x0, y0), "후보 %s — 시드 %d" % ("ABCD"[n], m["seed"]), font=Fn(24, True), fill="#f4f1ea")
        lines = ["바닥 %.0f m² (MAP2 의 %.1f 배) · 짧은 고리 %d · 숨을 곳 %d · 기둥 방 %d · 비탈 %d" % (r["area"], r["area"] / MAP2_AREA, r["small"], r["hides"],
                 sum(z["type"] == "pillar" for z in m["Z"].values()), sum(z["type"] != "pillar" for z in m["Z"].values())),
                 "길 잃고 425 m 안에 정거장 %.0f %% (300 m 안 %.0f %%) · 가운데값 %.0f m · 막다른 굴 %.0f m · 갈림 없는 가장 긴 굴 %.0f m" % (r["within"], r["within300"], r["median"], r["dead"], r["longest"])]
        for i, s in enumerate(lines): d.text((x0, y0 + 36 + i * 22), s, font=Fn(15), fill="#efd68e" if i == 0 else "#7fd67f")
        sx, sy = P(-100, -70); d.line([sx, sy, sx + 30 * S, sy], fill="#f4f1ea", width=3); d.text((sx + 15 * S, sy + 14), "30 m", font=Fn(13), fill="#f4f1ea", anchor="mm")
    lx, ly = 24, H * rows - 30
    for i, (c, s) in enumerate([("#7fd67f", "케이지 광장"), ("#efd68e", "불 켜진 방·길"), ("#aaa290", "어두운 굴"), ("#3a3632", "기둥(바위)"), ("#4a4540", "채굴적(괴물 집)"),
                                ("#3d8fe0", "대피소"), ("#9ff0ff", "개구멍"), ("#19d9c8", "뚫린 바위 틈"), ("#f04fbf", "막힌 바위 틈"), ("#d33c2c", "큰 틈(괴물)"), ("#ff9c7a", "가짜 출구 끝")]):
        X = lx + i * 170; d.rectangle([X, ly - 8, X + 16, ly + 8], fill=c); d.text((X + 22, ly), s, font=Fn(14), fill="#f4f1ea", anchor="lm")
    img.save(out); print("saved", out)


if __name__ == "__main__":
    import time
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 300; n_pick = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "build", "map3"); os.makedirs(out_dir, exist_ok=True)
    t0 = time.time(); rows = []; good = []
    from multiprocessing import Pool
    with Pool(max(1, os.cpu_count() - 2)) as pool:
        results = pool.map(one, range(1, n_seeds + 1))
    for s, m, r in results:
        if m is None: rows.append("%4d  (구역·방이 광장에서 안 닿음 — 버림)" % s); continue
        rows.append("%4d  바닥 %5.0f (%.2f 배) · 짧은 고리 %3d · 숨을 곳 %3d · 막다른 %4.1f m · 가장 긴 %4.1f m · 425 m 안 %3.0f %% · 기둥 위아래 %s · %s"
                    % (s, r["area"], r["area"] / MAP2_AREA, r["small"], r["hides"], r["dead"], r["longest"], r["within"], r["pillar_up_down"], "OK" if r["ok"] else "-"))
        print(rows[-1], flush=True)
        if r["ok"]: good.append((m, r))
    open(os.path.join(out_dir, "seeds.txt"), "w", encoding="utf-8").write("\n".join(rows))
    print("시드 %d 개 %.0f s · 통과 %d" % (n_seeds, time.time() - t0, len(good)))
    pick = []                                                               # 서로 다른 것: 구역 수·종류가 다른 것부터
    for m, r in sorted(good, key=lambda g: -g[1]["within"]):
        sig = tuple(sorted(z["type"] for z in m["Z"].values()))
        if all(sig != tuple(sorted(z["type"] for z in p[0]["Z"].values())) for p in pick) or len(good) < n_pick * 2: pick.append((m, r))
        if len(pick) >= n_pick: break
    if pick: draw([p[0] for p in pick], [p[1] for p in pick], os.path.join(out_dir, "candidates.png"))
