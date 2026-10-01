"""국부 선풍기 + 바람 관 (풍관). 레퍼런스 공통점: 썰매 받침 위 굵은 쇠 통 · 나팔 입 + 둥근 철망 · 속에 날개,
옆구리 방폭 접속함, 쇠 굽은 관으로 천장 높이까지 올라가 노란 주름 천 관이 쇠줄(메신저 와이어)에 고리로 매달려 간다. 끝 한 토막은 찢겨 빈 소매처럼 늘어진다.
  fan(mats)  : 원점 = 선풍기 가운데 아래 바닥. 축 = X, 바람은 +X 로. 천 관은 FAN_OUTLET 에서 시작.
  duct(mats, pts) : pts = [(x, y, z, 천장 z)] 관 가운데 선 (부르는 쪽 좌표 그대로).
  build(mats) : 본보기 = 선풍기 + 4 m 관 + 찢긴 끝 (천장 3.2 m)."""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, tube, torus, sweep, obj

AX = 0.65                         # 통을 빚는 축 높이 (키우기 전)
KY = 1.2                          # 통 굵기 배율: 지름 0.66 → 0.79 (0.6 m 관을 미는 기계가 관보다 가늘어 보이지 않게)
AXN = AX + 0.33 * (KY - 1)        # 키운 뒤 실제 축 높이 0.716 (통 밑은 안장 높이 그대로)
DRUM_M = Matrix.Translation((0, 0, AXN)) @ Matrix.Diagonal((1.1, KY, KY, 1)) @ Matrix.Translation((0, 0, -AX))
DUCT_R = 0.30
FAN_OUTLET = (1.95, 0.0, 2.65)    # 천 관이 시작하는 구멍 가운데 (밑면 2.35 m — 머리 위)
FAN_OUTLET_R = DUCT_R
X = Vector((1, 0, 0)); Z = Vector((0, 0, 1))


def _lathe(bm, prof, z0, seg=16):
    """X 축 둘레로 돌린 닫힌 덩어리. prof = [(x, r)], 처음과 끝은 r = 0 (축 위 한 점)"""
    rings = []
    for x, r in prof:
        rings.append([bm.verts.new((x, 0, z0))] if r == 0 else [bm.verts.new((x, r * math.cos(2 * math.pi * i / seg), z0 + r * math.sin(2 * math.pi * i / seg))) for i in range(seg)])
    for A, B in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            if len(A) == 1: bm.faces.new((A[0], B[j], B[i]))
            elif len(B) == 1: bm.faces.new((A[i], A[j], B[0]))
            else: bm.faces.new((A[i], A[j], B[j], B[i]))


def _bolts(bm, x, R, n, z0, r=0.016, h=0.03):
    """플랜지 둘레 볼트 머리 (육각)"""
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        cyl(bm, (x - h / 2, R * math.cos(a), z0 + R * math.sin(a)), (x + h / 2, R * math.cos(a), z0 + R * math.sin(a)), r, seg=6)


def fan(mats, outlet_z=FAN_OUTLET[2], cable_to=(1.9, -0.75, 0.02)):
    """국부 선풍기. outlet_z = 천 관 높이 (기본 FAN_OUTLET), cable_to = 케이블이 끝나는 곳 (벽 개폐기 자리를 주면 거기까지)"""
    out = []; c = 0.006
    # 썰매 받침: ㄷ 형강 두 줄 + 끝이 들린 썰매 코 + 가로대 + 안장 판 두 장 (통이 얹힌다)
    bm = bmesh.new()
    for y in (-0.27, 0.27):
        box(bm, (0, y * KY, 0.05), (1.5, 0.10, 0.10))
        for sx in (-1, 1): box(bm, (sx * 0.82, y * KY, 0.093), (0.24, 0.10, 0.035), Matrix.Rotation(-sx * math.radians(28), 3, "Y"))
    for x in (-0.55, 0.55): box(bm, (x, 0, 0.07), (0.08, 0.5 * KY, 0.06))
    for x in (-0.33, 0.33):
        box(bm, (x, 0, 0.26), (0.03, 0.64 * KY, 0.32)); box(bm, (x, 0, 0.11), (0.14, 0.64 * KY, 0.02))
        for y in (-0.3, 0.3): box(bm, (x, y * KY, 0.42), (0.10, 0.04, 0.16))                    # 통 옆을 잡는 귀
    out.append(obj("FAN_SKID", bm, mats["rust"]))
    # 통: 나팔 입(0.66 → 0.85) 속이 파인 한 덩어리. 모서리마다 좁은 띠를 넣어 매끈 셰이딩에서도 각이 선다
    bm = bmesh.new()
    _lathe(bm, [(-0.50, 0), (-0.50, 0.30 - c), (-0.50 - c, 0.30), (-0.55, 0.305), (-0.73, 0.40), (-0.735, 0.4125), (-0.73, 0.425), (-0.56, 0.335), (-0.55, 0.33),
                (0.55 - c, 0.33), (0.55, 0.33 - c), (0.55, 0)], AX)
    for x in (-0.55, 0.55): tube(bm, (x - 0.0125, 0, AX), (x + 0.0125, 0, AX), 0.375, 0.32)   # 양 끝 플랜지
    tube(bm, (-0.01, 0, AX), (0.01, 0, AX), 0.345, 0.32)                                      # 가운데 용접 띠
    out.append(obj("FAN_DRUM", bm, mats["steel_paint"], smooth=True))
    # 속: 어두운 뒤판 + 허브 + 날개 7장 (철망 뒤로 보인다)
    bm = bmesh.new(); cyl(bm, (-0.512, 0, AX), (-0.498, 0, AX), 0.296, seg=16); out.append(obj("FAN_BACK", bm, mats["black"]))
    bm = bmesh.new(); cyl(bm, (-0.50, 0, AX), (-0.64, 0, AX), 0.11, seg=10); cyl(bm, (-0.64, 0, AX), (-0.70, 0, AX), 0.11, seg=10, r1=0.04)
    for i in range(7):
        a = 2 * math.pi * i / 7 + 0.2
        box(bm, (-0.585, 0.195 * math.cos(a), AX + 0.195 * math.sin(a)), (0.012, 0.19, 0.12), Matrix.Rotation(a, 3, "X") @ Matrix.Rotation(math.radians(38), 3, "Y"))
    for x in (-0.33, 0.33): cyl(bm, (x - 0.025, 0, AX), (x + 0.025, 0, AX), 0.338, seg=16)    # 안장에 통을 묶는 띠 쇠
    box(bm, (-0.2, -0.332, AX + 0.02), (0.16, 0.012, 0.09))                                   # 이름판
    out.append(obj("FAN_BLADES", bm, mats["bare"]))
    # 철망: 나팔 입을 덮는 둥근 격자 (7 cm 간격 — 머리등에서 살아남는 굵기) + 테
    bm = bmesh.new(); R = 0.405
    torus(bm, (-0.74, 0, AX), X, R, 0.016, seg=16, sub=5)
    for k in range(-5, 6):
        o = k * 0.07; L = 2 * math.sqrt(R * R - o * o)
        box(bm, (-0.74, o, AX), (0.012, 0.012, L)); box(bm, (-0.752, 0, AX + o), (0.012, L, 0.012))
    out.append(obj("FAN_SCREEN", bm, mats["rust"]))
    # 검은 쇠: 볼트 · 들고리 · 방폭 접속함 (둥근 볼트 뚜껑) · 케이블 목
    bm = bmesh.new()
    _bolts(bm, -0.55, 0.355, 12, AX); _bolts(bm, 0.55, 0.355, 12, AX)
    for x in (-0.33, 0.33): torus(bm, (x + 0.08, 0, AX + 0.345), (0, 1, 0), 0.05, 0.016, seg=10, sub=5)
    box(bm, (0.16, -0.40, AX + 0.07), (0.26, 0.16, 0.22)); cyl(bm, (0.16, -0.48, AX + 0.07), (0.16, -0.515, AX + 0.07), 0.092, seg=10)
    for i in range(6):
        a = math.pi * i / 3; cyl(bm, (0.16 + 0.07 * math.cos(a), -0.51, AX + 0.07 + 0.07 * math.sin(a)), (0.16 + 0.07 * math.cos(a), -0.53, AX + 0.07 + 0.07 * math.sin(a)), 0.012, seg=6)
    cyl(bm, (0.16, -0.40, AX - 0.04), (0.16, -0.40, AX - 0.11), 0.032, seg=8)
    out.append(obj("FAN_IRON", bm, mats["iron"]))
    for o in out[1:]: o.data.transform(DRUM_M)                                                # 통 · 속 · 철망 · 접속함을 한꺼번에 키운다 (썰매는 그대로)
    bm = bmesh.new(); e = Vector(cable_to)
    sweep(bm, [DRUM_M @ Vector((0.16, -0.40, AX - 0.08)), (0.18, -0.50, 0.32), (0.22, -0.56, 0.07), (0.34, -0.62, 0.02), (0.5 * (0.34 + e.x), 0.5 * (-0.62 + e.y) - 0.06, 0.02), e], 0.02, seg=6)
    out.append(obj("NOCOL_FAN_CABLE", bm, mats["rubber"], smooth=True))
    # 쇠 굽은 관: 줄임관 → 마디진 굽은 관 → 곧은 올림관 → 굽은 관 → 속 빈 끝 (여기에 천 관을 끼운다). 올림관은 띠 + 두 다리로 바닥에 선다
    zt = outlet_z; Rb = 0.5; ox = FAN_OUTLET[0]; A = AXN; xr = 1.22
    bm = bmesh.new(); cyl(bm, (0.60, 0, A), (0.72, 0, A), 0.33 * KY, seg=14, r1=DUCT_R)
    path = [(0.66, 0, A)] + [(0.72 + Rb * math.sin(t), 0, A + Rb * (1 - math.cos(t))) for t in (math.radians(a) for a in (0, 22.5, 45, 67.5, 90))]
    path += [(xr + Rb * (1 - math.cos(t)), 0, zt - Rb + Rb * math.sin(t)) for t in (math.radians(a) for a in (0, 22.5, 45, 67.5, 90))] + [(ox - 0.2, 0, zt)]
    sweep(bm, path, DUCT_R - 0.004, seg=14)
    tube(bm, (ox - 0.22, 0, zt), (ox, 0, zt), DUCT_R, DUCT_R - 0.02, seg=14)
    for y in (-1, 1):
        cyl(bm, (xr, y * 0.30, 1.55), (xr, y * 0.62, 0.0), 0.028, seg=6); box(bm, (xr, y * 0.62, 0.01), (0.16, 0.16, 0.02))
    out.append(obj("FAN_ELBOW", bm, mats["rust"], smooth=True))
    bm = bmesh.new()
    tube(bm, (0.71, 0, A), (0.77, 0, A), DUCT_R + 0.014, DUCT_R - 0.01, seg=14)
    for z in (A + Rb + 0.02, 1.55, zt - Rb - 0.02): tube(bm, (xr, 0, z - 0.03), (xr, 0, z + 0.03), DUCT_R + 0.014, DUCT_R - 0.01, seg=14)   # 마디 띠 (검은 쇠 — 밝은 띠는 머리등에서 튄다)
    tube(bm, (ox - 0.07, 0, zt), (ox - 0.01, 0, zt), DUCT_R + 0.014, DUCT_R - 0.01, seg=14)
    out.append(obj("FAN_BANDS", bm, mats["iron"], smooth=True))
    return out


def duct(mats, pts, torn_end=True, seed=0, floor_z=0.0, torn_side=-1):
    """주름 천 관 + 쇠줄 + 고리 + 천장 걸이. 점마다 천장까지 걸이가 올라간다. torn_end: 마지막 토막(pts[-2] → pts[-1])은 고리에서 떨어져 바닥까지 늘어진다 (쇠줄은 끝까지 간다). torn_side: 바닥에 누운 끝의 입이 도는 쪽 (−1 = 가는 방향의 오른쪽, +1 = 왼쪽, 0 = 곧게)"""
    rnd = random.Random(seed); out = []; R = DUCT_R
    P = [Vector(p[:3]) for p in pts]; ceil = [p[3] for p in pts]
    W = [p + Z * (R + 0.08) for p in P]                                    # 쇠줄: 관 위 8 cm, 걸이 사이 곧게
    main = P[:-1] if torn_end else P
    seg_len = [(b - a).length for a, b in zip(main, main[1:])]; total = sum(seg_len); sag = [0.04 + 0.05 * rnd.random() for _ in seg_len]

    def at(s, wire=False):
        """관 길이 s 자리의 가운데 점 (걸이 사이 처짐 포함) 또는 쇠줄 점"""
        for i, L in enumerate(seg_len):
            if s <= L or i == len(seg_len) - 1:
                u = min(max(s / L, 0), 1); p = main[i].lerp(main[i + 1], u)
                return p + Z * (R + 0.08) if wire else p - Z * sag[i] * math.sin(math.pi * u)
            s -= L

    low = min(p.z for p in main) - R - 0.07 - floor_z if len(main) > 1 else 9
    pre = "NOCOL_" if low >= 2.3 else ""                                   # 밑면이 2.3 m 위면 부딪힘 없음
    if len(main) > 1:
        n = max(2, int(round(total / 0.10))); n += n % 2
        bm = bmesh.new(); sweep(bm, [at(total * i / n) for i in range(n + 1)], R, seg=12, r_fn=lambda i: R - 0.012 * rnd.random() if i % 2 == 0 else R - 0.035 - 0.012 * rnd.random())   # 20 cm 마다 살(나선 철사) 주름, 고르지 않게
        out.append(obj(pre + "DUCT_TUBE", bm, mats["cloth_yellow"], smooth=True))
        # 이음 테: 시작 · 5 m 마다 · 끝. 조임 볼트 귀가 아래에 붙는다
        bm = bmesh.new(); k = max(1, int(round(total / 5.0)))
        for j in range(k + 1):
            s = total * j / k; a, b = at(max(s - 0.06, 0)), at(min(s + 0.06, total)); cyl(bm, a, b, R + 0.02, seg=12)
            box(bm, (a + b) / 2 - Z * (R + 0.035), (0.05, 0.05, 0.05))
        out.append(obj(pre + "DUCT_COLLAR", bm, mats["iron"], smooth=True))                # 검은 조임 띠 (녹 색은 머리등에서 살색으로 뜬다)
    # 쇠줄 · 걸이 (천장 볼트 판까지) · 고리 (75 cm 마다 쇠줄 → 관 등)
    bm = bmesh.new(); sweep(bm, W, 0.01, seg=5)
    for w, cz in zip(W, ceil):
        if cz > w.z:                                                       # 걸이: 천장 볼트 판 + 볼트 머리 + 굵은 고리 쇠 → 쇠줄
            cyl(bm, w - Z * 0.01, (w.x, w.y, cz), 0.015, seg=6); box(bm, (w.x, w.y, cz - 0.012), (0.16, 0.16, 0.024)); cyl(bm, (w.x, w.y, cz - 0.05), (w.x, w.y, cz - 0.02), 0.035, seg=6)
            torus(bm, w, (0, 1, 0) if abs((W[1] - W[0]).normalized().y) < 0.7 else (1, 0, 0), 0.035, 0.012, seg=8, sub=4)
    if len(main) > 1:
        m = max(1, int(total / 0.75))
        for j in range(m):
            s = total * (j + 0.5) / m; cyl(bm, at(s, True) + Z * 0.01, at(s) + Z * (R - 0.02), 0.012, seg=5)
    if torn_end and len(P) > 1:
        L = (P[-1] - P[-2]).length
        for j in range(max(1, int(L / 0.75))):                              # 관이 떨어져 나간 빈 고리
            w = W[-2].lerp(W[-1], (j + 0.6) / max(1, int(L / 0.75))); cyl(bm, w + Z * 0.01, w - Z * (0.10 + 0.08 * rnd.random()), 0.012, seg=5)
    out.append(obj("NOCOL_DUCT_WIRE", bm, mats["iron"]))
    if torn_end and len(P) > 1: out += _torn(mats, P[-2], P[-1] - P[-2], floor_z, rnd, torn_side)
    return out


def _torn(mats, p0, d, floor_z, rnd, side=-1):
    """찢겨 떨어진 토막: 살(나선 철사)이 남아 둥근 채로 굽어 내려와 바닥에 눕고, 끝은 옆으로 돌아 너덜너덜한 입 속이 검게 들여다보인다 (천이라 부딪힘 없음)"""
    R = DUCT_R; d = Vector((d.x, d.y, 0)); d = d.normalized() if d.length > 1e-4 else X.copy(); s0 = Z.cross(d)
    zc = floor_z + R - 0.01; R1 = R2 = min(0.6, max(0.2, (p0.z - zc) / 2)); raw = []
    for i in range(9): t = math.pi / 2 * i / 8; raw.append(p0 + d * R1 * math.sin(t) - Z * R1 * (1 - math.cos(t)))          # 고리에서 떨어져 꺾여 내려온다
    c = Vector((p0.x, p0.y, zc + R2)) + d * (R1 + R2)
    for i in range(9): t = math.pi / 2 * i / 8; raw.append(c - d * R2 * math.cos(t) - Z * R2 * math.sin(t))                  # 바닥에서 다시 눕는다
    e0 = raw[-1]; Ry = 0.8; yaw = math.radians(50)
    for i in range(1, 7):                                                                                                    # 누운 끝이 옆으로 돈다
        a = yaw * i / 6; raw.append(e0 + (d * math.sin(a) + s0 * side * (1 - math.cos(a))) * Ry if side else e0 + d * 0.12 * i)
    path = [raw[0]]; acc = 0.0                                                                                               # 10 cm 간격으로 다시 나눈다 (살 간격이 고르게)
    for a, b in zip(raw, raw[1:]):
        L = (b - a).length
        while acc + L >= 0.10: a = a.lerp(b, (0.10 - acc) / L); L = (b - a).length; path.append(a.copy()); acc = 0.0
        acc += L
    n = len(path); bm = bmesh.new(); u = s0.copy(); fr = []
    for i, p in enumerate(path): p += s0 * (0.07 * math.sin(math.pi * i / (n - 1)) * math.sin(i * 0.5 + 1))            # 힘없이 매달려 좌우로 구불거린다
    for i, p in enumerate(path):
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized(); u = (u - t * u.dot(t)).normalized(); fr.append((p, t, u, t.cross(u)))
    jag = [0.09 * rnd.random() - 0.05 for _ in range(12)]; jag[1] = 0.10; jag[2] = 0.13                      # 찢긴 가장자리 + 삐져나온 천 조각

    def ring(i, r, edge=0.0):
        p, t, u, v = fr[i]
        return [bm.verts.new(p + (u * math.cos(2 * math.pi * j / 12) + v * math.sin(2 * math.pi * j / 12)) * r + t * jag[j] * edge) for j in range(12)]

    rings = [ring(i, R - 0.012 * rnd.random() if i % 2 == 0 else R - 0.035 - 0.012 * rnd.random()) for i in range(n - 1)]
    rings += [ring(n - 1, R - 0.01, 1.0), ring(n - 1, R - 0.03, 0.6), ring(n - 3, R - 0.05), ring(n - 6, R - 0.05)]          # 입에서 안으로 접혀 들어간 속
    for A, B in zip(rings, rings[1:]):
        for j in range(12): bm.faces.new((A[j], A[(j + 1) % 12], B[(j + 1) % 12], B[j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    out = [obj("NOCOL_DUCT_TORN", bm, mats["cloth_yellow"], smooth=True)]
    bm = bmesh.new(); p, t = fr[n - 2][0], fr[n - 2][1]; cyl(bm, p - t * 0.01, p + t * 0.01, R - 0.05, seg=12); out.append(obj("NOCOL_DUCT_TORN_DARK", bm, mats["black"]))   # 속 어둠
    bm = bmesh.new(); cyl(bm, p0 - d * 0.06, p0 + d * 0.06, R + 0.02, seg=12); out.append(obj("NOCOL_DUCT_TORN_COLLAR", bm, mats["iron"], smooth=True))
    return out


def build(mats):
    """본보기: 선풍기 + 4 m 관 + 찢긴 끝 (천장 3.2 m). 미리보기 옵션 '{"_ceil": 3.2}'. 길면 미리보기 눈이 너무 멀어져 짧게 둔다 — 맵에서는 pts 를 길게 준다"""
    x0, y0, z0 = FAN_OUTLET
    return fan(mats) + duct(mats, [(x0 + 2.0 * i, y0, z0, 3.2) for i in range(4)], torn_end=True)


def torn_demo(mats):
    """찢긴 끝만 가까이 보는 본보기 (미리보기: 함수 이름 torn_demo, 옵션 '{"_ceil": 3.2}')"""
    return duct(mats, [(2.0 * i, 0, 2.65, 3.2) for i in range(3)], torn_end=True)
