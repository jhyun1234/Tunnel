"""기계: 권양기(쇠줄 감는 통) + 배전반 줄. Blender 안에서만 돈다.
winch(mats, state)        원점 = 통 가운데 아래 바닥, 통 축 = y, 다루는 사람 자리 = −y, 끊어진 쇠줄은 +x 바닥으로.
switchboard(mats, panels, ceil_h)  원점 = 벽(y = 0) 바닥, 줄 가운데 = x 0, 판은 −y 쪽을 본다.
build(mats)               본보기: 벽에 배전반, 그 앞 왼쪽에 권양기.
"""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, tube, torus, sweep, obj, text_mesh, place


class _Parts:
    """재질별로 그물을 모았다가 한꺼번에 물체로 낸다 (이름 → bmesh)"""
    def __init__(self, prefix): self.prefix, self.d = prefix, {}
    def __call__(self, name, mat):
        if name not in self.d: self.d[name] = (bmesh.new(), mat)
        return self.d[name][0]
    def out(self, mats, smooth=()):
        return [obj((n if n.startswith("NOCOL_") else self.prefix + n), bm, mats[m], smooth=n in smooth) for n, (bm, m) in self.d.items()]


def _bar(bm, p0, p1, w, t):
    """p0 → p1 납작한 막대 (w = 막대가 누운 면 안 너비, t = 두께)"""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    return box(bm, (p0 + p1) / 2, (w, t, d.length), d.to_track_quat("Z", "Y").to_matrix())


def _arc(bm, c, r0, r1, y0, y1, a0, a1, n):
    """y 축을 도는 굽은 띠 (가운데 c = (x, z), 반지름 r0..r1, y0..y1, 각 a0..a1) — 덮개 · 조임 띠 · 톱니 부채"""
    rings = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n; cs, sn = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((c[0] + r * cs, y, c[1] + r * sn)) for r, y in ((r0, y0), (r1, y0), (r1, y1), (r0, y1))])
    for A, B in zip(rings, rings[1:]):
        for k in range(4): bm.faces.new((A[k], A[(k + 1) % 4], B[(k + 1) % 4], B[k]))
    bm.faces.new(rings[0]); bm.faces.new(rings[-1][::-1])


def _bolt(bm, p, r=0.022, h=0.025, up=(0, 0, 1)):
    cyl(bm, p, Vector(p) + Vector(up) * h, r, seg=6)


def _turn(vs, R, pivot):
    pivot = Vector(pivot)
    for v in vs: v.co = R @ (v.co - pivot) + pivot


# ───────────────────────── 권양기 ─────────────────────────
def winch(mats, state="abandoned"):
    P = _Parts("WINCH_"); ZC = 0.95   # 통 축 높이
    YB0, YB1 = -0.74, 0.70            # 축받이 두 자리 (−y 쪽은 멈춤 통, +y 쪽은 큰 톱니바퀴)

    # 콘크리트 받침 + 바닥에 박은 볼트
    b = P("BASE", "concrete"); box(b, (-0.2, -0.02, 0.075), (2.4, 1.96, 0.15))
    # ㄷ자 쇠 틀 (세로 2 + 가로 4) — 받침에 볼트로 물린다
    f = P("FRAME", "steel_paint")
    for y in (YB0, YB1): box(f, (-0.2, y, 0.21), (2.1, 0.12, 0.12))
    for x in (-1.2, -0.55, 0.55, 0.8): box(f, (x, (YB0 + YB1) / 2, 0.20), (0.1, YB1 - YB0, 0.10))
    k = P("IRON", "iron")
    for y in (YB0, YB1):
        for x in (-1.15, -0.2, 0.75):
            box(f, (x, y - 0.09 * (1 if y < 0 else -1), 0.16), (0.14, 0.10, 0.02)); _bolt(k, (x, y - 0.10 * (1 if y < 0 else -1), 0.17))
        # A 자 다리 + 축받이 (통 축을 양쪽에서 받친다)
        for sx in (-1, 1):
            _bar(f, (sx * 0.42, y, 0.27), (sx * 0.08, y, 0.87), 0.09, 0.10)
            box(f, (sx * 0.42, y, 0.28), (0.2, 0.14, 0.02)); _bolt(k, (sx * 0.48, y, 0.29), 0.018)
        box(f, (0, y, 0.60), (0.50, 0.03, 0.07)); box(f, (0, y, 0.865), (0.34, 0.14, 0.03))
        box(k, (0, y, 0.93), (0.24, 0.12, 0.10)); cyl(k, (0, y - 0.07, ZC), (0, y + 0.07, ZC), 0.085, seg=10)
        for sx in (-1, 1): _bolt(k, (sx * 0.095, y, 0.98), 0.016, 0.03)

    # 통: 축 + 큰 귀(테) 둘 + 귀 보강 살
    d = P("DRUM", "rust")
    cyl(d, (0, YB0 - 0.10, ZC), (0, YB1 + 0.10, ZC), 0.045, seg=8)
    cyl(d, (0, -0.43, ZC), (0, 0.43, ZC), 0.43, seg=14, caps=False)
    for sy in (-1, 1):
        cyl(d, (0, sy * 0.43, ZC), (0, sy * 0.47, ZC), 0.60, seg=24)
        cyl(k, (0, sy * 0.47, ZC), (0, sy * 0.52, ZC), 0.14, seg=10)
        tube(P("RIM", "iron"), (0, sy * 0.425, ZC), (0, sy * 0.475, ZC), 0.606, 0.588, seg=24)   # 귀 가장자리 두꺼운 테 (검은 쇠)
        for i in range(8):   # 주물 보강 살 (검은 쇠 — 녹슨 귀 위에서 바퀴살로 읽힌다)
            a = math.pi * 2 * i / 8 + 0.2
            box(k, (0.36 * math.cos(a), sy * 0.485, ZC + 0.36 * math.sin(a)), (0.44, 0.03, 0.04), Matrix.Rotation(-a, 3, "Y"))
    # 감긴 쇠줄: 골이 진 겹 (−y 쪽은 한 겹 더 감겨 높다 — 고르게 안 감긴 옛 줄)
    r = P("ROPEWOUND", "iron"); N = 52   # 줄 한 가닥 = 골 하나 (굵기 3 cm 남짓), 각진 골이 머리등에 줄무늬로 잡힌다
    sweep(r, [(0, -0.43 + 0.86 * i / N, ZC) for i in range(N + 1)], 0.5, seg=14,
          r_fn=lambda i: (0.52 if i < 36 else 0.485) + (0.016 if i % 2 else -0.014))
    torus(r, (0.03, 0.30, ZC - 0.04), (0.10, 1, 0.05), 0.535, 0.02, seg=16, sub=6)   # 풀려 늘어진 한 바퀴

    # 큰 톱니바퀴 (+y 귀 옆) + 작은 톱니 + 톱니 상자 + 덮개
    g = P("GEAR", "iron"); Y0, Y1 = 0.515, 0.585
    tube(g, (0, Y0, ZC), (0, Y1, ZC), 0.485, 0.40, seg=24); cyl(g, (0, Y0 - 0.02, ZC), (0, Y1 + 0.02, ZC), 0.10, seg=10)
    for i in range(6):
        a = math.pi * i / 3 + 0.3; _bar(g, (0.08 * math.cos(a), (Y0 + Y1) / 2, ZC + 0.08 * math.sin(a)), (0.42 * math.cos(a), (Y0 + Y1) / 2, ZC + 0.42 * math.sin(a)), 0.07, 0.035)
    for i in range(40):
        a = math.pi * 2 * i / 40; box(g, (0.50 * math.cos(a), (Y0 + Y1) / 2, ZC + 0.50 * math.sin(a)), (0.045, Y1 - Y0, 0.036), Matrix.Rotation(-a, 3, "Y"))
    cyl(g, (-0.56, Y0, 0.70), (-0.56, Y1, 0.70), 0.10, seg=10)                      # 작은 톱니 (상자 안에서 물린다)
    c = P("CASE", "steel_paint")
    box(c, (-0.75, 0.58, 0.455), (0.56, 0.24, 0.37)); cyl(c, (-0.75, 0.46, 0.64), (-0.75, 0.70, 0.64), 0.28, seg=14)
    box(c, (-0.75, 0.58, 0.64), (0.62, 0.27, 0.03))                                 # 위아래 상자 이음 테
    cyl(c, (-0.75, 0.70, 0.64), (-0.75, 0.73, 0.64), 0.12, seg=10)                  # 점검 뚜껑
    for i in range(6): a = math.pi * i / 3; _bolt(k, (-0.75 + 0.095 * math.cos(a), 0.73, 0.64 + 0.095 * math.sin(a)), 0.012, 0.012, (0, 1, 0))
    for sx in (-1, 1): _bolt(k, (-0.75 + sx * 0.29, 0.58, 0.655), 0.014)
    gd = P("GUARD", "steel_yellow")
    _arc(gd, (0, ZC), 0.545, 0.565, 0.49, 0.62, math.radians(65), math.radians(192), 10)
    _arc(gd, (0, ZC), 0.22, 0.565, 0.605, 0.62, math.radians(65), math.radians(192), 10)
    _bar(gd, (0.23, 0.63, ZC + 0.50), (0.42, 0.70, 0.27), 0.05, 0.02)                # 덮개 버팀 띠 → 틀

    # 전동기 (통 뒤, 축은 y) — 식힘 살 · 양 끝 뚜껑 · 단자 상자 · 발
    m = P("MOTOR", "steel_paint"); MX, MZ = -0.9, 0.56
    box(m, (MX, 0.10, 0.275), (0.75, 0.74, 0.03))                                   # 전동기 받침 판 (가로 틀 위)
    for sy in (-0.12, 0.30): box(m, (MX, sy, 0.31), (0.50, 0.08, 0.05))
    cyl(m, (MX, -0.20, MZ), (MX, 0.40, MZ), 0.23, seg=12)
    for i in range(7): y = -0.14 + 0.07 * i; cyl(m, (MX, y, MZ), (MX, y + 0.02, MZ), 0.255, seg=12)
    cyl(m, (MX, -0.32, MZ), (MX, -0.20, MZ), 0.245, seg=12)                         # 바람개비 덮개
    cyl(m, (MX, 0.40, MZ), (MX, 0.46, MZ), 0.20, seg=12, r1=0.09)
    cyl(k, (MX, 0.44, MZ), (MX, 0.50, MZ), 0.04, seg=8)                             # 전동기 축 → 톱니 상자
    box(m, (MX, 0.10, MZ + 0.27), (0.16, 0.18, 0.10))                               # 단자 상자
    cyl(m, (MX, 0.10, MZ + 0.25), (MX, 0.10, MZ + 0.36), 0.012, seg=6)

    # 띠 멈춤: 멈춤 통(−y 귀 옆) + 조임 띠 + 긴 손 지렛대 + 톱니 부채
    br = P("BRAKEDRUM", "iron"); tube(br, (0, -0.63, ZC), (0, -0.50, ZC), 0.40, 0.335, seg=16)   # 멈춤 통 = 테 + 살 다섯 (민판이 아니라 살 사이로 통 귀가 보인다)
    cyl(br, (0, -0.66, ZC), (0, -0.47, ZC), 0.11, seg=10)
    for i in range(5):
        a = math.pi * 2 * i / 5 + 0.5; _bar(br, (0.09 * math.cos(a), -0.565, ZC + 0.09 * math.sin(a)), (0.35 * math.cos(a), -0.565, ZC + 0.35 * math.sin(a)), 0.075, 0.05)
    lv = P("BRAKE", "iron")
    _arc(P("BAND", "rust"), (0, ZC), 0.402, 0.424, -0.61, -0.52, math.radians(-62), math.radians(242), 20)
    for a in (-62, 242):
        ar = math.radians(a); box(lv, (0.44 * math.cos(ar), -0.565, ZC + 0.44 * math.sin(ar)), (0.07, 0.07, 0.03), Matrix.Rotation(-ar, 3, "Y"))
    _bar(lv, (-0.21, -0.565, ZC - 0.39), (-0.30, -0.70, 0.27), 0.03, 0.03)          # 띠 고정 끝 → 틀
    PV = Vector((0.36, -0.86, 0.33)); TOP = Vector((0.80, -0.86, 1.50)); u = (TOP - PV).normalized()
    cyl(lv, (0.20, -0.565, ZC - 0.385), PV + u * 0.20 + Vector((0, 0.01, 0)), 0.014, seg=6)   # 띠 당김 끝 → 지렛대
    box(lv, (PV.x, -0.86, 0.27), (0.18, 0.13, 0.24)); cyl(lv, (PV.x, -0.94, PV.z), (PV.x, -0.78, PV.z), 0.028, seg=8)
    _bar(P("LEVER", "steel_red"), PV, TOP - u * 0.14, 0.065, 0.035)                  # 붉은 칠 멈춤 지렛대 (어둠에서 윤곽을 맡는다)
    _bar(lv, PV + u * 0.72 + Vector((0.045, 0, -0.017)), TOP - u * 0.20 + Vector((0.045, 0, -0.017)), 0.014, 0.014)   # 걸쇠 당김 막대
    hd = P("GRIP", "rust"); cyl(hd, TOP - u * 0.16, TOP, 0.028, seg=8); _bar(hd, TOP - u * 0.24 + Vector((0.07, 0, -0.026)), TOP - u * 0.06 + Vector((0.09, 0, -0.034)), 0.018, 0.02)
    A0, A1 = math.radians(48), math.radians(100)
    _arc(lv, (PV.x, PV.z), 0.60, 0.66, -0.915, -0.89, A0, A1, 8)
    for a in (A0, A1): _bar(lv, (PV.x, -0.90, PV.z), (PV.x + 0.61 * math.cos(a), -0.90, PV.z + 0.61 * math.sin(a)), 0.04, 0.02)
    for i in range(13):
        a = A0 + (A1 - A0) * (i + 0.5) / 13; box(lv, (PV.x + 0.67 * math.cos(a), -0.9025, PV.z + 0.67 * math.sin(a)), (0.035, 0.025, 0.022), Matrix.Rotation(-a + 0.5, 3, "Y"))

    # 기동기 상자 (다루는 자리 왼쪽 기둥 위) + 돌림 손잡이 + 전동기로 가는 전선
    s = P("STARTER", "iron")   # 주물 기동기: 칠한 몸통 + 검은 문짝 + 비 가림 갓 + 이름표 + 아래 전선 물림
    box(f, (-1.05, YB0, 0.72), (0.06, 0.06, 0.90)); box(f, (-1.05, YB0, 1.21), (0.26, 0.18, 0.42))
    box(s, (-1.05, YB0 - 0.096, 1.20), (0.21, 0.012, 0.33))
    for sz in (-1, 1): box(s, (-1.165, YB0 - 0.10, 1.20 + sz * 0.10), (0.03, 0.02, 0.05))        # 문 경첩
    box(P("RUSTP", "rust"), (-1.05, YB0 - 0.01, 1.43), (0.31, 0.24, 0.025), Matrix.Rotation(0.12, 3, "X"))
    box(P("PLATE", "white"), (-1.05, YB0 - 0.104, 1.33), (0.11, 0.005, 0.035))
    cyl(s, (-1.05, YB0 + 0.03, 0.94), (-1.05, YB0 + 0.03, 1.0), 0.03, seg=8)
    cyl(k, (-1.05, YB0 - 0.16, 1.20), (-1.05, YB0 - 0.10, 1.20), 0.022, seg=8); _bar(k, (-1.05, YB0 - 0.15, 1.20), (-0.95, YB0 - 0.15, 1.29), 0.025, 0.015)
    cyl(P("GRIPWOOD", "timber_old"), (-0.95, YB0 - 0.24, 1.29), (-0.95, YB0 - 0.15, 1.29), 0.02, seg=8)
    cb = P("NOCOL_WINCH_CABLE", "rubber")
    sweep(cb, [(-1.05, YB0 + 0.09, 1.10), (-1.04, -0.52, 1.02), (-1.0, -0.33, 0.93), (-0.95, -0.14, 0.89), (MX, 0.02, MZ + 0.29)], 0.018, seg=6)

    # 녹 번진 자리 (틀 · 덮개) + 받침 위 누런 물때 — 한 색 덩어리로 안 보이게
    ru = P("RUSTP", "rust"); st = P("NOCOL_WINCH_STAIN", "ochre")
    for x, y, L in ((-0.75, YB0, 0.30), (0.30, YB0, 0.22), (-0.45, YB1, 0.36), (0.62, YB1, 0.16)): box(ru, (x, y, 0.21), (L, 0.127, 0.127))
    _bar(ru, (0.36, YB0, 0.37), (0.25, YB0, 0.555), 0.097, 0.107); _bar(ru, (-0.40, YB1, 0.30), (-0.30, YB1, 0.47), 0.097, 0.107)
    _arc(ru, (0, ZC), 0.562, 0.570, 0.50, 0.61, math.radians(92), math.radians(128), 4)
    _arc(ru, (0, ZC), 0.30, 0.50, 0.618, 0.624, math.radians(150), math.radians(185), 4)
    box(ru, (-0.80, 0.455, 0.40), (0.30, 0.008, 0.20)); box(ru, (MX + 0.1, -0.20, 0.292), (0.34, 0.16, 0.006))
    for x, y, sx, sy, a in ((-1.12, -0.80, 0.42, 0.20, 0.3), (0.72, -0.88, 0.30, 0.14, -0.2), (-0.15, 0.84, 0.46, 0.16, 0.1), (0.78, 0.20, 0.34, 0.5, 0.5), (-1.30, 0.25, 0.16, 0.44, -0.1)):
        box(st, (x, y, 0.152), (sx, sy, 0.005), Matrix.Rotation(a, 3, "Z"))

    if state == "abandoned":
        # 끊어진 쇠줄: 통 밑에서 풀려 틀 · 받침 모서리를 넘어 바닥에 누워 굽이친다 (공중에 뜬 데 없음)
        rp = P("NOCOL_WINCH_ROPE", "iron"); y = 0.10
        pts = [(-0.05, y, ZC - 0.505), (0.15, y, 0.425), (0.36, y, 0.345), (0.55, y, 0.275), (0.80, y, 0.275), (1.0, y, 0.172), (1.10, y + 0.01, 0.07), (1.24, y + 0.02, 0.022)]
        fl = [(1.45, 0.10), (1.66, 0.0), (1.80, -0.18), (1.84, -0.40), (1.74, -0.60), (1.56, -0.70), (1.40, -0.64)]   # 받침 앞에서 되감기듯 굽는다 (자리 덜 차지)
        pts += [(x, yy, 0.022) for x, yy in fl]
        sweep(rp, pts, 0.02, seg=8)
        rnd = random.Random(3)
        for i in range(6):   # 풀어진 가닥 끝
            a0 = 2.78; a = a0 - 0.9 + 0.36 * i + rnd.uniform(-0.1, 0.1); am = (a + a0) / 2; L = rnd.uniform(0.12, 0.22); ex, ey = 1.41, -0.645
            sweep(rp, [(ex, ey, 0.012), (ex + L * 0.5 * math.cos(am), ey + L * 0.5 * math.sin(am), 0.010), (ex + L * math.cos(a), ey + L * math.sin(a), 0.008)], 0.007, seg=4)
    return P.out(mats, smooth=("NOCOL_WINCH_ROPE", "NOCOL_WINCH_CABLE"))


# ───────────────────────── 배전반 ─────────────────────────
def switchboard(mats, panels=3, ceil_h=3.2):
    P = _Parts("SWB_"); rnd = random.Random(7)
    W, Z0, Z1 = 0.8, 0.3, 1.9; YF = -0.33          # 판 너비 · 아래 · 위, 판 앞면 y
    X0 = -W * panels / 2; opened = min(1, panels - 1)   # 덮개가 떨어져 나간 칸
    f = P("FRAME", "steel_paint"); k = P("IRON", "iron")
    # 쇠 틀: 칸 사이마다 다리 + 위아래 가로대 + 벽으로 가는 버팀 (벽에 물린다)
    for i in range(panels + 1):
        x = X0 + W * i
        box(f, (x, -0.275, 0.975), (0.05, 0.05, 1.95)); box(f, (x, -0.275, 0.005), (0.14, 0.14, 0.01)); _bolt(k, (x, -0.33, 0.01), 0.014, 0.02)
        for z in (0.36, 1.925): box(f, (x, -0.125, z), (0.04, 0.25, 0.04))
        box(f, (x, -0.01, 1.925), (0.12, 0.02, 0.12))
    for z in (Z0, Z1): box(f, (0, -0.275, z), (W * panels, 0.05, 0.05))
    # 위 전선 함 + 벽을 타고 천장 속으로 올라가는 전선
    box(f, (0, -0.09, 2.01), (W * panels + 0.1, 0.16, 0.13))
    for x in (X0 - 0.05, X0 + W * panels + 0.05): box(f, (x, -0.09, 2.01), (0.012, 0.19, 0.16))
    cb = P("NOCOL_SWB_CABLE", "rubber")
    for j in range(panels + 1):
        x = X0 + 0.3 + (W * panels - 0.6) * j / max(1, panels) + rnd.uniform(-0.08, 0.08); rr = (0.028, 0.02, 0.024)[j % 3]
        pts = [(x, -0.06, 2.07)] + [(x + rnd.uniform(-0.03, 0.03), -0.035, z) for z in (2.3, 2.65, 2.95)] + [(x, -0.035, ceil_h + 0.04)]
        sweep(cb, pts, rr, seg=6)
        for z in (2.45, 2.85): box(k, (x, -0.03, z), (0.10, 0.06, 0.025))            # 전선 고정 띠
    # 바닥 전선 홈통 (판 밑, 뚜껑 한 장이 빠져 전선이 보인다)
    L = W * panels + 0.3; D0, D1 = -L / 2, L / 2          # 줄 가운데에 맞춘 홈통 (양 끝 0.15 씩 나온다)
    box(f, (0, -0.16, 0.006), (L, 0.26, 0.012))
    for y in (-0.285, -0.035): box(f, (0, y, 0.035), (L, 0.012, 0.07))
    gap = X0 + W * (opened + 0.5)
    box(f, ((D0 + gap - 0.3) / 2, -0.16, 0.074), (gap - 0.3 - D0, 0.27, 0.008))
    box(f, ((gap + 0.3 + D1) / 2, -0.16, 0.074), (D1 - gap - 0.3, 0.27, 0.008))
    for y in (-0.21, -0.14, -0.08): sweep(cb, [(D0 + 0.03, y, 0.035), (gap, y + 0.01, 0.04), (D1 - 0.03, y, 0.035)], 0.02, seg=6)
    # 녹 · 물때: 다리 밑동, 전선 함 모서리, 판을 타고 내린 누런 줄
    ru = P("RUSTP", "rust"); st = P("NOCOL_SWB_STAIN", "ochre")
    for i in range(panels + 1): box(ru, (X0 + W * i, -0.275, 0.09 + 0.05 * (i % 2)), (0.057, 0.057, 0.16 + 0.10 * (i % 2)))
    box(ru, (X0 + 0.25, -0.172, 1.98), (0.5, 0.006, 0.07)); box(ru, (X0 + W * panels - 0.5, -0.172, 2.03), (0.34, 0.006, 0.09))

    sl = P("PANEL", "black"); me = P("METER", "iron"); dl = P("DIAL", "glass"); nd = P("NEEDLE", "black")
    cu = P("BLADE", "bare"); wd = P("HANDLE", "timber"); po = P("PORCELAIN", "white"); rd = P("LAMP", "red")
    for i in range(panels):
        cx = X0 + W * (i + 0.5); zb = 1.33 if i == opened else Z0
        box(sl, (cx, YF + 0.015, (zb + Z1) / 2), (W - 0.012, 0.03, Z1 - zb))
        for sx in (-1, 1):
            for z in (zb + 0.05, Z1 - 0.05): _bolt(k, (cx + sx * 0.34, YF, z), 0.016, 0.012, (0, -1, 0))
        # 둥근 계기 둘 (검은 쇠 테 + 밝은 눈금판 + 바늘)
        for sx in (-1, 1):   # 칸마다 크기 · 높이가 조금씩 다르다 (나중에 갈아 끼운 계기), 끝 칸 하나는 유리가 깨져 속이 검다
            mr = rnd.choice((0.118, 0.118, 0.098, 0.13)); mx, mz = cx + sx * 0.2, 1.62 + rnd.uniform(-0.03, 0.02)
            cyl(me, (mx, YF, mz), (mx, YF - 0.06, mz), mr, seg=12)
            if i == panels - 1 and sx == 1 and panels > 1: cyl(nd, (mx, YF - 0.06, mz), (mx, YF - 0.063, mz), mr - 0.02, seg=12); continue
            cyl(dl, (mx, YF - 0.06, mz), (mx, YF - 0.066, mz), mr - 0.02, seg=12)
            a = rnd.uniform(-1.0, 0.9)
            box(nd, (mx + 0.035 * math.sin(a), YF - 0.069, mz - 0.03 + 0.035 * math.cos(a)), (0.012, 0.005, 0.10), Matrix.Rotation(a, 3, "Y"))
            box(nd, (mx, YF - 0.069, mz - 0.062), (0.09, 0.005, 0.022))
        tl = Matrix.Rotation((0.0, -0.10, 0.03)[i % 3], 3, "Y")                      # 이름표 (하나는 나사가 빠져 기울었다) + 글줄 둘
        box(po, (cx, YF - 0.004, 1.82), (0.24, 0.008, 0.07), tl)
        for dz, wl in ((0.014, 0.18), (-0.014, 0.12)): box(nd, tl @ Vector((0, 0, dz)) + Vector((cx, YF - 0.009, 1.82)), (wl, 0.003, 0.012), tl)
        h = (Z1 - zb) * rnd.uniform(0.25, 0.7); box(st, (cx + rnd.choice((-0.34, 0.34)) + rnd.uniform(-0.02, 0.02), YF - 0.001, Z1 - 0.07 - h / 2), (rnd.uniform(0.02, 0.04), 0.004, h))   # 볼트에서 흘러내린 녹물
        cyl(k, (cx, YF, 1.41), (cx, YF - 0.025, 1.41), 0.04, seg=10); cyl(rd, (cx, YF - 0.025, 1.41), (cx, YF - 0.065, 1.41), 0.03, seg=10, r1=0.016)   # 표시등
        if i == opened: continue
        # 칼 스위치 3극: 아래 경첩 · 위 물림쇠 · 칼날 셋 · 가로 막대 · 나무 손잡이 (칸마다 닫힘 / 열림이 다르다)
        hz, t = 0.92, (0.0, 1.05, 0.0, 0.7)[(i + (1 if i > opened else 0)) % 4]
        box(sl, (cx, YF - 0.008, hz + 0.16), (0.40, 0.016, 0.46))                    # 스위치 밑판
        R = Matrix.Rotation(t, 3, "X"); pv = (cx, YF - 0.04, hz); vs = []
        for sx in (-1, 0, 1):
            x = cx + sx * 0.11
            box(cu, (x, YF - 0.035, hz), (0.04, 0.04, 0.05)); box(cu, (x - 0.016, YF - 0.035, hz + 0.30), (0.01, 0.04, 0.06)); box(cu, (x + 0.016, YF - 0.035, hz + 0.30), (0.01, 0.04, 0.06))
            vs += box(cu, (x, YF - 0.04, hz + 0.16), (0.02, 0.008, 0.34))
        _turn(vs, R, pv)
        _turn(box(sl, (cx, YF - 0.05, hz + 0.25), (0.30, 0.03, 0.035)), R, pv)
        _turn(cyl(wd, (cx, YF - 0.06, hz + 0.25), (cx, YF - 0.20, hz + 0.25), 0.022, seg=8), R, pv)
        # 사기 퓨즈 통 셋 (한 칸은 하나가 빠졌다)
        for sx in (-1, 0, 1):
            x = cx + sx * 0.14
            box(cu, (x, YF - 0.01, 0.62), (0.03, 0.02, 0.20))
            if i == panels - 1 and sx == 1: continue
            box(po, (x, YF - 0.035, 0.62), (0.07, 0.05, 0.13)); box(po, (x, YF - 0.07, 0.62), (0.03, 0.03, 0.05))
    # 덮개 없는 칸: 모선(가로 쇠 띠 셋) · 사기 애자 · 내림 띠 · 잘린 전선 + 바닥에 기대 선 깨진 판
    cx = X0 + W * (opened + 0.5)
    for sx in (-1, 1): box(f, (cx + sx * 0.3, -0.012, 0.95), (0.05, 0.024, 0.95))
    for j, z in enumerate((1.20, 1.05, 0.90)):
        box(cu, (cx, -0.135, z), (W - 0.06, 0.012, 0.05))
        for sx in (-1, 1): cyl(po, (cx + sx * 0.3, -0.024, z), (cx + sx * 0.3, -0.13, z), 0.032, seg=8)
        x = cx - 0.18 + 0.18 * j
        box(cu, (x, -0.148, (z + 0.50) / 2), (0.035, 0.012, z - 0.50))
        sweep(cb, [(x, -0.15, 0.52), (x + 0.02, -0.17, 0.3), (x + 0.03 * (j - 1), -0.16, 0.035)], 0.016, seg=6)
    # 떼어 낸 판: 두꺼운 돌판에 계기 하나 · 이름표 · 모서리 볼트 구멍 쇠가 그대로 붙어 있다 (그냥 검은 네모가 아니게)
    Mr = Matrix.Rotation(-0.33, 3, "X") @ Matrix.Rotation(0.06, 3, "Y"); pc = Vector((cx + 0.22, -0.465, 0.335)); lp = lambda x, y, z: pc + Mr @ Vector((x, y, z))
    box(sl, pc, (0.70, 0.045, 0.62), Mr)
    for sx in (-1, 1):
        for sz in (-1, 1): box(k, lp(sx * 0.31, -0.024, sz * 0.27), (0.035, 0.012, 0.035), Mr)
    cyl(me, lp(-0.14, -0.02, 0.10), lp(-0.14, -0.08, 0.10), 0.118, seg=14); cyl(dl, lp(-0.14, -0.08, 0.10), lp(-0.14, -0.086, 0.10), 0.098, seg=14)
    box(nd, lp(-0.12, -0.089, 0.11), (0.012, 0.005, 0.10), Mr @ Matrix.Rotation(0.6, 3, "Y"))
    box(po, lp(0.16, -0.026, 0.20), (0.24, 0.008, 0.07), Mr); box(ru, lp(0.0, 0.0, 0.312), (0.704, 0.049, 0.03), Mr)
    box(k, lp(0.20, -0.028, -0.12), (0.12, 0.012, 0.05), Mr)                         # 스위치 경첩 쇠가 남은 자리
    out = P.out(mats, smooth=("NOCOL_SWB_CABLE", "METER", "LAMP"))
    # 빨간 "위험" 표찰 (첫 칸 아래)
    c0 = X0 + W * 0.5 if opened != 0 else X0 + W * 1.5
    if panels > 1 or opened != 0:
        bm = bmesh.new(); box(bm, (c0, YF - 0.004, 0.42), (0.36, 0.008, 0.13)); out.append(obj("SWB_SIGN", bm, mats["white"]))
        out.append(text_mesh("NOCOL_SWB_SIGNTEXT", "위험", (c0, YF - 0.009, 0.385), 0.09, mats["red"]))
    return out


def build(mats):
    """본보기: 벽(y = 0)에 배전반 3칸, 그 앞 왼쪽에 권양기 (35도 틀어 놓아 감긴 줄 · 톱니 · 지렛대가 한눈에 보인다)"""
    return switchboard(mats) + place(winch(mats), Matrix.Translation((-2.4, -1.7, 0)) @ Matrix.Rotation(math.radians(-35), 4, "Z"))
