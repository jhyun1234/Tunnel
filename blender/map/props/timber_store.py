"""갱목 창고 (갱목 적치장): 껍질 벗긴 둥근 갱목 더미 · 우물 정(井)자 쌓기 · 판자 더미 · 쐐기 상자 · 톱질 자리 · 장대 묶음.
레퍼런스 공통점 (Zeche Zollern Holzplatz 03 · 05, Blaenavon Big Pit, R3 조사):
  - 덩어리는 전부 "둥근" 통나무, 한 더미 안에 굵기가 섞여 있다 (같은 굵기 격자 금지). 끝면이 통로를 본다 — 밝은 동그라미 벽.
  - 끝면은 반듯한 원이 아니다: 테두리가 울퉁불퉁하고, 가운데 심이 어둡고, 심에서 바깥으로 갈라진 금이 있다 (Zollern 05). 끝이 한 면에 맞지 않고 들쭉날쭉하다.
  - 묵은 통나무는 잿빛, 새 것은 누런빛 — 한 더미에 섞여 있다.
  - 더미는 바닥에 닿지 않게 받침목 위, 옆은 세운 말뚝이 막는다. 통나무는 말뚝 밖으로 양 끝이 삐져나온다.
  - 정자 쌓기는 층마다 90도 돌려 쌓고 끝이 들쭉날쭉하다.
조각 함수마다 원점 = 조각 가운데 아래 바닥. 긴 쪽 = x (pole_bundle 만 벽 기준)."""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, torus, sweep, obj, place

def _obj(name, bm, mat, outs, smooth=False):
    """obj() 뒤에 면 방향을 다시 본다 — 뚜껑 없는 통 · 홑면은 자동 맞춤이 뒤집을 수 있다 (게임에서 뒤집힌 면은 안 보인다)"""
    o = obj(name, bm, mat, smooth=smooth)
    assert len(o.data.polygons) == len(outs), name
    for p, n in zip(o.data.polygons, outs):
        if p.normal.dot(n) < 0: p.flip()
    return o

class _Logs:
    """통나무 모음: 옆면(누런 것 · 잿빛 묵은 것) / 끝면 / 끝면의 어두운 심과 갈라진 금을 따로 모은다 — 끝면만 밝아서 머리등에 동그라미가 뜬다"""
    def __init__(s):
        s.bm = {k: bmesh.new() for k in ("side", "old", "end", "heart")}; s.out = {k: [] for k in s.bm}
    def add(s, p0, p1, r0, r1, seg=10, rnd=None, old=False, bend=0.0):
        p0, p1 = Vector(p0), Vector(p1); ax = (p1 - p0).normalized(); q = ax.to_track_quat("Z", "Y").to_matrix()
        ph = rnd.uniform(0, 6.28) if rnd else 0.0; ang = lambda i: ph + 2 * math.pi * i / seg
        jit = [1 + rnd.uniform(-0.07, 0.07) for _ in range(seg)] if rnd else [1.0] * seg   # 울퉁불퉁한 테두리 (반듯한 다각형이 안 보이게)
        dirs = [q @ Vector((math.cos(ang(i)), math.sin(ang(i)), 0)) for i in range(seg)]
        rings = [(p0, r0), (p1, r1)]
        if bend:   # 휜 통나무: 가운데 고리를 위쪽으로 민다
            off = Vector((rnd.uniform(-0.5, 0.5) * bend, rnd.uniform(-0.5, 0.5) * bend, bend)); off -= ax * off.dot(ax)
            rings.insert(1, ((p0 + p1) / 2 + off, (r0 + r1) / 2))
        k = "old" if old else "side"; bm = s.bm[k]
        R = [[bm.verts.new(p + d * (r * j)) for d, j in zip(dirs, jit)] for p, r in rings]
        for A, B in zip(R, R[1:]):
            for i in range(seg):
                bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i])); s.out[k].append(q @ Vector((math.cos(ang(i + 0.5)), math.sin(ang(i + 0.5)), 0)))
        e, h = s.bm["end"], s.bm["heart"]
        for p, r, n in ((p0, r0, -ax), (p1, r1, ax)):
            e.faces.new([e.verts.new(p + d * (r * j)) for d, j in zip(dirs, jit)]); s.out["end"].append(n)
            if rnd is None: continue
            u, v = dirs[0], n.cross(dirs[0]); c = p + n * 0.003 + u * (r * rnd.uniform(0, 0.15)); a0 = rnd.uniform(0, 6.28)
            P = lambda a, rr: h.verts.new(c + (u * math.cos(a) + v * math.sin(a)) * rr)
            h.faces.new([P(a0 + 2 * math.pi * i / 5, r * rnd.uniform(0.3, 0.48)) for i in range(5)]); s.out["heart"].append(n)   # 어두운 심
            for _ in range(rnd.choice((1, 2, 2, 3))):   # 심에서 바깥으로 갈라진 금
                a = rnd.uniform(0, 6.28); w = rnd.uniform(0.08, 0.16)
                h.faces.new([P(a, r * 0.2), P(a - w, r * 0.75), P(a + w, r * 0.75)]); s.out["heart"].append(n)
    def objs(s, mats, side, end):
        o = []
        for k, nm, m, sm in (("side", side, "timber", True), ("old", side + "_OLD", "timber_old", True), ("end", end, "timber_end", False), ("heart", "NOCOL_" + end + "_HEART", "timber_old", False)):
            if len(s.bm[k].faces): o.append(_obj(nm, s.bm[k], mats[m], s.out[k], smooth=sm))
            else: s.bm[k].free()
        return o

def _beam(bm, p0, p1, a, b):
    """p0 → p1 각재 (단면 a x b)"""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    return box(bm, (p0 + p1) / 2, (a, b, d.length), d.to_track_quat("Z", "Y").to_matrix())

def _wedge(bm, M, L=0.3, w=0.12, h=0.07):
    """쐐기: 한쪽 두께 h 에서 0 으로 빠지는 세모 기둥 (끝은 1 cm 남긴다 — 종잇장처럼 안 보이게)"""
    v = [bm.verts.new(M @ Vector(c)) for c in ((0, -w / 2, 0), (0, w / 2, 0), (0, w / 2, h), (0, -w / 2, h), (L, -w / 2, 0), (L, w / 2, 0), (L, w / 2, 0.01), (L, -w / 2, 0.01))]
    for f in ((0, 1, 2, 3), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2), (4, 7, 6, 5)): bm.faces.new([v[i] for i in f])

def log_rack(mats, length=2.4, layers=5, width=1.6, seed=0):
    """말뚝 사이 갱목 더미 (Zollern 03): 받침목 2 + 굵은 말뚝 4 + 버팀대 4 + 말뚝 머리를 잇는 띠장 2 + 굵기 섞인 통나무. 통나무 축 = x, 끝면이 ±x 를 본다"""
    rnd = random.Random(seed); out = []; bx = length / 2 - 0.45; rs = 0.07; base = 0.12
    # 통나무 자리: 한 개씩 떨어뜨려 아래 통나무 골에 앉힌다 (y-z 단면에서 원 쌓기)
    placed = []
    def drop(y, r):
        z = base + r
        for (yc, zc, rc) in placed:
            dy = abs(y - yc)
            if dy < r + rc: z = max(z, zc + math.sqrt((r + rc) ** 2 - dy * dy))
        return z
    for L in range(layers):
        y = -width / 2 + (rnd.uniform(0.04, 0.09) if L % 2 else 0.0)
        while True:
            r = rnd.choice((0.06, 0.07, 0.075, 0.085, 0.09, 0.10, 0.11))
            if y + 2 * r > width / 2: break
            yy = y + r; z = drop(yy, r)
            for _ in range(40):   # 골로 굴러 내려간다
                c = [(drop(t, r), t) for t in (yy - 0.008, yy + 0.008) if -width / 2 + r <= t <= width / 2 - r]
                if not c or min(c)[0] >= z - 1e-5: break
                z, yy = min(c)
            placed.append((yy, z, r)); y += 2 * r + rnd.uniform(0.0, 0.012)
    top = max(z + r for (_, z, r) in placed); lg = _Logs()
    for (yy, z, r) in placed:
        ln = length * rnd.uniform(0.88, 1.0); m = length / 2 + 0.05 - ln / 2; off = rnd.uniform(-m, m)   # 길이 · 끝 자리가 제각각 (끝은 ±(length/2 + 0.05) 를 넘지 않는다)
        t = rnd.uniform(0.84, 1.0); ra, rb = (r, r * t) if rnd.random() < 0.5 else (r * t, r)   # 밑동 · 끝 굵기 차
        up = z + r > top - 0.13   # 맨 위에 얹힌 것만 휜다 (아래 것은 눌려서 안 보인다)
        lg.add((off - ln / 2, yy, z), (off + ln / 2, yy + rnd.uniform(-0.012, 0.012), z + (rnd.uniform(0, 0.03) if up else 0)), ra, rb, 12, rnd, old=rnd.random() < 0.3, bend=rnd.uniform(0.012, 0.03) if up else 0.0)
    out += lg.objs(mats, "TS_RACK_LOGS", "TS_RACK_ENDS")
    # 받침목 (바닥에서 띄운다) · 말뚝 (바닥에 박고 받침목에 물린다) · 버팀대 (말뚝 허리 → 받침목 끝) · 띠장 (말뚝 머리끼리 못 박아 벌어지지 않게)
    bm = bmesh.new()
    for sx in (-1, 1):
        box(bm, (sx * bx, 0, base / 2), (0.14, width + 0.74, base), Matrix.Rotation(math.radians(rnd.uniform(-1.5, 1.5)), 3, "Z"))
        zt = top + 0.09
        for sy in (-1, 1):
            h = top + rnd.uniform(0.2, 0.42); y0 = sy * (width / 2 + rs + 0.005)
            cyl(bm, (sx * bx, y0, 0), (sx * bx + rnd.uniform(-0.02, 0.02), y0 + sy * rnd.uniform(0.02, 0.05), h), rs, 8, r1=rs * 0.8)
            _beam(bm, (sx * bx, y0 + sy * 0.04, min(0.85, top * 0.6)), (sx * bx, sy * (width / 2 + 0.33), base - 0.02), 0.08, 0.09)
        box(bm, (sx * (bx + rs + 0.012), rnd.uniform(-0.03, 0.03), zt), (0.035, width + 0.42, 0.10), Matrix.Rotation(math.radians(rnd.uniform(-2.5, 2.5)), 3, "X"))
    out.append(obj("TS_RACK_FRAME", bm, mats["timber_old"])); return out

def cross_pile(mats, log_len=1.1, layers=8, seed=0):
    """우물 정자 쌓기 (Zollern Holzplatz · Sälzer-Amalie): 층마다 90도 돌린다. 끝이 들쭉날쭉. 맨 아래 층 축 = x. 맨 위에 비뚤게 던져 얹은 한 개"""
    rnd = random.Random(seed + 11); lg = _Logs(); z = 0.0
    for L in range(layers):
        d = rnd.choice((0.13, 0.15, 0.16)); n = 5 if L < layers - 1 else 3; span = log_len - 0.24
        for i in range(n):
            r = d / 2 - rnd.uniform(0, 0.006); c = -span / 2 + span * i / (n - 1) + rnd.uniform(-0.03, 0.03); ln = log_len * rnd.uniform(0.9, 1.0); off = rnd.uniform(-0.06, 0.06); t = rnd.uniform(0.86, 1.0)
            a, b = (-ln / 2 + off, c - rnd.uniform(-0.02, 0.02), z + r), (ln / 2 + off, c, z + r)
            if L % 2: a, b = (a[1], a[0], a[2]), (b[1], b[0], b[2])
            lg.add(a, b, r, r * t, 10, rnd, old=rnd.random() < 0.3)
        z += d - 0.004
    c, s = math.cos(math.radians(24)) * (log_len / 2 - 0.05), math.sin(math.radians(24)) * (log_len / 2 - 0.05)
    lg.add((-c, -s, z + 0.068), (c, s, z + 0.068), 0.07, 0.062, 10, rnd, old=True)
    return lg.objs(mats, "TS_CROSS_LOGS", "TS_CROSS_ENDS")

def board_stack(mats, n=12):
    """흙막이 판자 더미: 0.03 x 0.15 x 2.0 판자를 3 장 나란히 n 층, 굄목 3 개 위. 끝이 들쭉날쭉, 맨 위 층은 덜 차고 한 장이 비뚤다"""
    rnd = random.Random(n); bm = bmesh.new()
    for x in (-0.75, 0.0, 0.75): box(bm, (x, 0, 0.03), (0.07, 0.56, 0.06))
    st = obj("TS_BOARD_STICKERS", bm, mats["timber_old"]); bm = bmesh.new()
    for L in range(n):
        z = 0.06 + 0.03 * L + 0.015
        for k in range(3):
            if L == n - 1 and k == 2: continue
            box(bm, (rnd.uniform(-0.07, 0.07), (k - 1) * 0.16 + rnd.uniform(-0.012, 0.012), z), (2.0, 0.15, 0.03), Matrix.Rotation(math.radians(rnd.uniform(-1.0, 1.0)), 3, "Z"))
    box(bm, (0.1, 0.06, 0.06 + 0.03 * n + 0.015), (2.0, 0.15, 0.03), Matrix.Rotation(math.radians(9), 3, "Z"))   # 비뚤게 얹힌 한 장
    return [st, obj("TS_BOARDS", bm, mats["plank"])]

def wedge_box(mats, seed=0):
    """쐐기 상자: 판자 궤짝 0.6 x 0.4 x 0.3 에 쐐기와 머리나무(동발 위 굄판) 가 수북하다. 바닥에도 두엇 흘려 있다"""
    rnd = random.Random(seed + 5); bm = bmesh.new()
    for x in (-0.2, 0.2): box(bm, (x, 0, 0.015), (0.05, 0.4, 0.03))   # 밑 굄대
    box(bm, (0, 0, 0.04), (0.6, 0.4, 0.02))
    for z in (0.11, 0.24):   # 옆 널 2 줄 — 사이가 벌어져 있다
        for sy in (-1, 1): box(bm, (0, sy * 0.19, z), (0.6, 0.02, 0.115))
        for sx in (-1, 1): box(bm, (sx * 0.29, 0, z), (0.02, 0.36, 0.115))
    for sx in (-1, 1):
        for sy in (-1, 1): box(bm, (sx * 0.26, sy * 0.16, 0.175), (0.04, 0.04, 0.25))
    crate = obj("TS_WEDGE_CRATE", bm, mats["timber_old"]); bm = bmesh.new()
    box(bm, (0, 0, 0.15), (0.54, 0.34, 0.2))   # 속에 찬 쐐기 덩어리
    for i in range(14):   # 수북이 쌓인 쐐기: 두툼한 세모 기둥이 제멋대로 박혀 있다
        a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0, 0.15); x, y = d * math.cos(a) * 1.3, d * math.sin(a) * 0.8
        M = Matrix.Translation((x, y, 0.24 + 0.10 * (1 - d / 0.15) * rnd.uniform(0.4, 1.0))) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(rnd.uniform(-0.7, 0.5), 4, "Y") @ Matrix.Rotation(rnd.uniform(-0.6, 0.6), 4, "X") @ Matrix.Translation((-0.14, 0, 0))
        _wedge(bm, M, rnd.uniform(0.24, 0.34))
    for (x, y, a) in ((0.52, -0.1, 0.5), (0.45, 0.22, 2.4), (-0.5, -0.24, 4.0)):   # 바닥에 흘린 쐐기
        _wedge(bm, Matrix.Translation((x, y, 0)) @ Matrix.Rotation(a, 4, "Z"), 0.32)
    wd = obj("TS_WEDGES", bm, mats["plank"]); bm = bmesh.new()
    box(bm, (0.05, 0.0, 0.36), (0.46, 0.15, 0.07), Matrix.Rotation(0.5, 3, "Z") @ Matrix.Rotation(0.12, 3, "Y"))   # 머리나무: 상자 위에 걸쳐 있다
    box(bm, (-0.41, 0.02, 0.21), (0.45, 0.15, 0.07), Matrix.Rotation(math.radians(-62), 3, "Y"))   # 상자에 기대 세운 것
    box(bm, (0.0, -0.33, 0.035), (0.48, 0.15, 0.07), Matrix.Rotation(0.15, 3, "Z"))
    return [crate, wd, obj("TS_CAP_PIECES", bm, mats["timber"])]

def saw_station(mats, seed=0):
    """톱질 자리: X 다리 톱질 모탕(0.9 x 0.85) 위에 반쯤 켠 통나무, 켠 자리에 물린 활톱, 바닥에 토막 · 톱밥 더미 · 나무 부스러기"""
    rnd = random.Random(seed + 7); out = []; bm = bmesh.new(); r = 0.085; zc = 0.70; z0 = 0.019
    for x in (-0.4, 0.4):   # X 다리 두 벌 (겹쳐 못 박은 각재)
        _beam(bm, (x - 0.035, -0.32, z0), (x - 0.035, 0.24, 0.85), 0.07, 0.07); _beam(bm, (x + 0.035, 0.32, z0), (x + 0.035, -0.24, 0.85), 0.07, 0.07)
    for sy in (-1, 1): box(bm, (0, sy * 0.19, 0.25), (0.9, 0.035, 0.09))   # 두 벌을 잇는 가로대
    _beam(bm, (-0.4, -0.2, 0.12), (0.4, -0.12, 0.40), 0.03, 0.08)   # 흔들림 막는 빗대
    out.append(obj("TS_SAWHORSE", bm, mats["timber_old"]))
    lg = _Logs(); cut = 0.66
    lg.add((-0.75, 0, zc), (cut - 0.008, 0, zc), r, r * 0.97, 12, rnd); lg.add((cut + 0.008, 0, zc), (0.95, 0, zc), r * 0.97, r * 0.95, 12, rnd)
    lg.add((cut - 0.02, 0, zc - 0.3 * r), (cut + 0.02, 0, zc - 0.3 * r), 0.68 * r, 0.68 * r, 8)   # 아직 안 켠 아래쪽 살
    # 바닥 토막: 세워진 것(나이테가 위를 본다) · 누운 것 · 서로 기댄 것 — 켜는 대로 떨어져 구른 자리
    lg.add((1.05, -0.25, 0), (1.05, -0.25, 0.13), r, r, 12, rnd); lg.add((0.8, 0.38, 0), (0.8, 0.38, 0.27), 0.075, 0.075, 12, rnd, old=True)
    lg.add((1.2, 0.12, 0.08), (1.42, 0.22, 0.08), 0.08, 0.08, 12, rnd); lg.add((0.55, -0.5, 0.075), (0.68, -0.58, 0.075), 0.075, 0.075, 12, rnd)
    lg.add((0.82, -0.27, 0.036), (0.868, -0.25, 0.136), 0.08, 0.08, 12, rnd)   # 세운 토막에 비스듬히 기댄 것
    lg.add((1.02, 0.16, 0.07), (1.10, 0.02, 0.07), 0.07, 0.07, 12, rnd, old=True)
    out += lg.objs(mats, "TS_SAW_LOGS", "TS_SAW_ENDS")
    bm = bmesh.new(); zb = zc + 0.4 * r   # 활톱: 둥글게 휜 쇠 대롱 활 + 톱날, 켠 틈에 걸려 있다
    sweep(bm, [(cut, -0.36, zb)] + [(cut, -0.36 * math.cos(math.pi * k / 8), zb + 0.07 + 0.2 * math.sin(math.pi * k / 8)) for k in range(9)] + [(cut, 0.36, zb)], 0.014, 6)
    out.append(obj("NOCOL_TS_SAW_BOW", bm, mats["steel_red"], smooth=True))
    bm = bmesh.new(); box(bm, (cut, 0, zb + 0.018), (0.006, 0.74, 0.036)); out.append(obj("NOCOL_TS_SAW_BLADE", bm, mats["bare"]))
    bm = bmesh.new()   # 톱밥 더미 (켠 자리 바로 아래 큰 것 + 통나무 끝 아래 작은 것) — 가장자리가 고르지 않다
    for (cx, cy, R, h) in ((cut, 0.0, 0.45, 0.07), (cut + 0.42, -0.16, 0.24, 0.04)):
        vs = cyl(bm, (cx, cy, 0), (cx, cy, h), R, 12, r1=R * 0.3); j = [rnd.uniform(0.72, 1.15) for _ in range(12)]
        for v in vs:
            if v.co.z < h / 2: k = int(round(math.atan2(v.co.y - cy, v.co.x - cx) / (math.pi / 6))) % 12; v.co.x = cx + (v.co.x - cx) * j[k]; v.co.y = cy + (v.co.y - cy) * j[k] * 0.75
    out.append(obj("NOCOL_TS_SAWDUST", bm, mats["timber_end"]))
    bm = bmesh.new()   # 나무 부스러기 · 껍질 조각: 톱질 자리 둘레에 흩어져 있다
    for i in range(14):
        a = rnd.uniform(0, 6.28); d = rnd.uniform(0.25, 0.8)
        _wedge(bm, Matrix.Translation((cut + d * math.cos(a), d * math.sin(a) * 0.8, 0)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z"), rnd.uniform(0.07, 0.14), rnd.uniform(0.035, 0.06), rnd.uniform(0.02, 0.035))
    out.append(obj("NOCOL_TS_SAW_CHIPS", bm, mats["plank"])); return out

def pole_bundle(mats, lean=18, length=2.0, seed=0):
    """가는 장대 묶음 (천장 흙막이 장대): 7 개를 두 군데 철사로 묶어 벽에 기대 세웠다. 원점 = 벽면(y=0) 아래 바닥, 발은 −y 쪽"""
    rnd = random.Random(seed + 3); a = math.radians(lean); ax = Vector((0, math.sin(a), math.cos(a))); R = 0.085
    foot = Vector((0, -R / math.cos(a) - length * math.sin(a), 0))   # 묶음 축이 바닥과 만나는 점 → 꼭대기 벽 쪽 장대가 y=0 에 닿는다
    u, v = Vector((1, 0, 0)), ax.cross(Vector((1, 0, 0))); lg = _Logs()
    for i in range(7):
        r = rnd.uniform(0.032, 0.044); o = Vector((0, 0, 0)) if i == 0 else (u * math.cos(i * math.pi / 3) + v * math.sin(i * math.pi / 3)) * (R - 0.01)
        p = foot + o; p0 = p + ax * ((r * math.sin(a) - p.z) / ax.z)   # 장대마다 발이 바닥에 닿게
        dl = 0.0 if i == 2 else rnd.uniform(-0.3, -0.02)   # 길이가 제각각 (벽 쪽 한 개만 끝까지 가서 벽에 닿는다)
        lg.add(p0, p + ax * (length + dl), r, r * 0.8, 8, rnd, old=i in (3, 5))
    out = lg.objs(mats, "TS_POLES", "TS_POLE_ENDS")
    bm = bmesh.new()
    for t in (0.45, 1.45):
        torus(bm, foot + ax * t, ax, R + 0.035, 0.012, 12, 5); torus(bm, foot + ax * (t + 0.03), ax, R + 0.033, 0.012, 12, 5)
    out.append(obj("NOCOL_TS_POLE_TIES", bm, mats["iron"], smooth=True)); return out

def loose_log(mats, length=2.2, d=0.18, seed=0):
    """바닥에 누운 통나무 하나 (쓰러진 동발 등 다른 자리 꾸밈용). 축 = x. 살짝 휘었고 가지 친 옹이 둘"""
    rnd = random.Random(seed); lg = _Logs(); r = d / 2; t = rnd.uniform(0.85, 0.95)
    lg.add((-length / 2, 0, r), (length / 2, 0, r * t), r, r * t, 12, rnd, bend=0.025)
    out = lg.objs(mats, "TS_LOOSE_LOG", "TS_LOOSE_LOG_ENDS"); bm = bmesh.new()
    for fx, ang in ((-0.22, 0.9), (0.27, 2.3)):   # 옹이: 가지를 바투 친 자리
        n = Vector((0, math.cos(ang), math.sin(ang))); c = Vector((fx * length, 0, r + 0.012))
        cyl(bm, c + n * r * 0.6, c + n * (r + 0.035), 0.03, 6, r1=0.022)
    out.append(obj("TS_LOOSE_LOG_KNOTS", bm, mats["timber"])); return out

def build(mats):
    """본보기 배치: 창고 구석 6 x 4 m (x −3..3, y −2..2, 뒷벽 y = 2). 통나무 끝면이 통로(−y) 를 본다"""
    T = lambda x, y, deg=0: Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(deg), 4, "Z"); out = []
    out += place(log_rack(mats, 2.4, 7, 1.6, 0), T(-1.9, 0.75, 90))
    out += place(log_rack(mats, 1.8, 5, 1.2, 1), T(0.45, 1.05, 90))
    out += place(cross_pile(mats), T(2.3, 1.35))
    out += place(pole_bundle(mats), T(1.5, 2.0))
    out += place(board_stack(mats), T(2.35, -0.6, 90))
    out += place(wedge_box(mats), T(-1.1, -1.25, 15))
    out += place(saw_station(mats), T(0.45, -1.2, -8))
    out += place(loose_log(mats, 2.0, 0.17, 4), T(-2.1, -1.0, 12))
    return out
