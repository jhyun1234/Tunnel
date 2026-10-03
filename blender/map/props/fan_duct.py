"""국부 선풍기 + 바람 관 (풍관). 레퍼런스 공통점: 썰매 받침 위 굵은 쇠 통 · 나팔 입 + 둥근 철망 · 속에 날개,
옆구리 방폭 접속함, 쇠 굽은 관으로 천장 높이까지 올라가 노란 주름 천 관이 쇠줄(메신저 와이어)에 고리로 매달려 간다. 끝 한 토막은 찢겨 빈 소매처럼 늘어진다.
  fan(mats)  : 원점 = 선풍기 가운데 아래 바닥. 축 = X, 바람은 +X 로. 천 관은 FAN_OUTLET 에서 시작.
  duct(mats, pts, end="torn"|"open", dia=0.6) : pts = [(x, y, z, 천장 z)] 관 가운데 선 (부르는 쪽 좌표 그대로). 돌려주는 값 = (물체 목록, 관 가운데 줄).
  build(mats) : 본보기 = 선풍기 + 4 m 관 + 찢긴 끝 (천장 3.2 m)."""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, tube, torus, sweep, obj, text_mesh

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


def fan(mats, outlet_z=FAN_OUTLET[2], cable_to=(1.9, -0.75, 0.02), number=None):
    """국부 선풍기. outlet_z = 천 관 높이 (기본 FAN_OUTLET), cable_to = 케이블이 끝나는 곳 (벽 개폐기 자리를 주면 거기까지), number = 통 옆 흰 페인트 번호 (예: "3", 안 주면 없음)"""
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
    if number is not None:                                                                   # 흰 페인트 번호: 이름판 위 비스듬한 면 (16 각 통의 한 면, 2 mm 띄움) — 양 옆 다 (어느 쪽에서 보아도)
        a = 0.33 * KY * math.cos(math.pi / 16) + 0.002
        for sy in (-1, 1):
            n = Vector((0, sy * math.cos(math.radians(33.75)), math.sin(math.radians(33.75)))); c = Vector((-0.22, 0, AXN)) + n * a
            o = text_mesh("NOCOL_FAN_NUMBER", str(number), c, 0.16, mats["white"], rot=(math.radians(56.25), 0, math.pi if sy > 0 else 0), extrude=0.0)
            co = [v.co for v in o.data.vertices]
            if co: o.data.transform(Matrix.Translation(c - (Vector([min(v[i] for v in co) for i in range(3)]) + Vector([max(v[i] for v in co) for i in range(3)])) / 2))   # 글씨체가 바뀌어도 글자 가운데를 면 가운데에
            out.append(o)
    return out


def duct(mats, pts, torn_end=True, seed=0, floor_z=0.0, torn_side=-1, end=None, dia=2 * DUCT_R, name="DUCT"):
    """주름 천 관 + 쇠줄 + 고리 + 천장 걸이. pts = [(x, y, 관 가운데 z, 그 자리 천장 z)] — 점마다 천장까지 걸이가 올라간다.
    end: "torn" = 마지막 토막(pts[-2] → pts[-1])은 고리에서 떨어져 바닥까지 늘어진다 (쇠줄은 끝까지 간다) · "open" = 온전한 끝 (검은 테 + 속이 어두운 열린 입). 안 주면 torn_end 를 따른다 (옛 부름).
    torn_side: 바닥에 누운 끝의 입이 도는 쪽 (−1 = 가는 방향의 오른쪽, +1 = 왼쪽, 0 = 곧게). dia = 관 지름 (좁은 막장 0.45). floor_z = 바닥 z 하나 또는 점마다 목록. name = 물체 이름 머리.
    이웃 토막 사이가 20° 넘게 꺾이면 쇠 굽은 토막(팔꿈치: 굽이 반지름 = 지름, 마디 22.5°)으로 돌아가고, 그 앞뒤 끝에 걸이가 선다.
    돌려주는 값 = (물체 목록, 관 가운데 줄): 줄 = 매달린 관 가운데 점들 (10 cm 간격, 굽은 곳 펼침 · 처짐 포함, pts 와 같은 좌표 · 찢긴 토막은 빼고)"""
    end = end or ("torn" if torn_end else ""); torn = end == "torn"
    rnd = random.Random(seed); out = []; R = dia / 2
    P = [Vector(p[:3]) for p in pts]; ceil = [p[3] for p in pts]; FZ = list(floor_z) if isinstance(floor_z, (list, tuple)) else [floor_z] * len(P)
    main = P[:-1] if torn else P
    # 걸이 자리 st = [(점, 천장 z)] · arcs[k] = 걸이 k → k+1 사이 굽은 토막의 점들 (그 밖은 곧은 천 토막)
    st = [(main[0], ceil[0])]; arcs = {}
    for i in range(1, len(main) - 1):
        a, b, c = main[i - 1], main[i], main[i + 1]; u, v = (b - a).normalized(), (c - b).normalized(); g = u.angle(v)
        if g <= math.radians(20): st.append((b, ceil[i])); continue
        la, lc = (b - a).length, (c - b).length; t = min(dia * math.tan(g / 2), 0.45 * la, 0.45 * lc); rb = t / math.tan(g / 2)
        w = (v - u * u.dot(v)).normalized(); o = b - u * t + w * rb; k = max(2, math.ceil(g / math.radians(22.5) - 1e-6))
        arc = [o + (u * math.sin(g * j / k) - w * math.cos(g * j / k)) * rb for j in range(k + 1)]; arcs[len(st)] = arc
        st += [(arc[0], ceil[i] + (ceil[i - 1] - ceil[i]) * t / la), (arc[-1], ceil[i] + (ceil[i + 1] - ceil[i]) * t / lc)]
    if len(main) > 1: st.append((main[-1], ceil[len(main) - 1]))
    sg = [0.0 if k in arcs else 0.03 + 0.02 * rnd.random() for k in range(len(st) - 1)]   # 걸이 사이 처짐 3~5 cm (굽은 쇠 토막은 안 처진다)

    def span(k):
        """걸이 k → k+1 의 가운데 점들 (끝점 빼고). 천 토막 = 10 cm 간격 짝수 개 (주름이 이어진다) + 처짐"""
        if k in arcs: return arcs[k][:-1]
        a, b = st[k][0], st[k + 1][0]; n = max(2, int(round((b - a).length / 0.10))); n += n % 2
        return [a.lerp(b, j / n) - Z * sg[k] * math.sin(math.pi * j / n) for j in range(n)]

    def along(pl, s):
        """꺾인 선 pl 의 길이 s 자리"""
        for a, b in zip(pl, pl[1:]):
            L = (b - a).length
            if s <= L: return a.lerp(b, s / L) if L > 1e-9 else a.copy()
            s -= L
        return pl[-1].copy()

    line = [q for k in range(len(st) - 1) for q in span(k)] + [st[-1][0].copy()] if len(st) > 1 else []
    low = min(p.z - f for p, f in zip(main, FZ)) - R - 0.07 if len(main) > 1 else 9
    pre = "NOCOL_" if low >= 2.3 else ""                                   # 밑면이 바닥에서 2.3 m 위면 부딪힘 없음
    if len(st) > 1:
        runs = [[]]                                                        # 곧은 천 토막 묶음 (굽은 토막에서 끊긴다)
        for k in range(len(st) - 1):
            if k in arcs: runs.append([])
            else: runs[-1].append(k)
        bm = bmesh.new(); bc = bmesh.new()                                 # bc = 이음 테 (검은 쇠)
        for r in [r for r in runs if r]:
            pl = [q for k in r for q in span(k)] + [st[r[-1] + 1][0]]; mouth = end == "open" and r[-1] == len(st) - 2
            rg = sweep(bm, pl, R, seg=12, caps=not mouth, r_fn=lambda i: R - 0.012 * rnd.random() if i % 2 == 0 else R - 0.035 - 0.012 * rnd.random())   # 20 cm 마다 살(나선 철사) 주름, 고르지 않게
            if mouth: bm.faces.new(rg[0][::-1])                            # 열린 입: 끝 뚜껑 없이
            # 이음 테: 시작 · 5 m 마다 · 끝. 조임 볼트 귀가 아래에 붙는다 (열린 입은 아래 끝 테가 대신)
            L = sum((b - a).length for a, b in zip(pl, pl[1:])); kk = max(1, int(round(L / 5.0)))
            for j in range(kk + 1 - mouth):
                s = L * j / kk; a, b = along(pl, max(s - 0.06, 0)), along(pl, min(s + 0.06, L)); cyl(bc, a, b, R + 0.02, seg=12)
                box(bc, (a + b) / 2 - Z * (R + 0.035), (0.05, 0.05, 0.05))
        out.append(obj(pre + name + "_TUBE", bm, mats["cloth_yellow"], smooth=True))
        if arcs:                                                           # 굽은 쇠 토막: 마디마다 용접 띠, 두 끝은 천 관 테와 이어진 띠
            be = bmesh.new()
            for arc in arcs.values():
                sweep(be, arc, R + 0.012, seg=12, caps=False)
                for j in range(1, len(arc) - 1): t = (arc[j + 1] - arc[j - 1]).normalized(); cyl(bc, arc[j] - t * 0.012, arc[j] + t * 0.012, R + 0.022, seg=12)
                for q, q2 in ((arc[0], arc[1]), (arc[-1], arc[-2])): cyl(bc, q, q + (q2 - q).normalized() * 0.06, R + 0.02, seg=12)
            out.append(obj(pre + name + "_ELBOW", be, mats["rust"], smooth=True))
        if end == "open":                                                  # 열린 입: 끝 테 (속 벽이 보인다) + 10 cm 안쪽 어둠
            q, t = line[-1], (line[-1] - line[-2]).normalized(); tube(bc, q - t * 0.12, q + t * 0.01, R + 0.02, R - 0.03, seg=12)
            bm = bmesh.new(); cyl(bm, q - t * 0.11, q - t * 0.09, R - 0.025, seg=12); out.append(obj("NOCOL_" + name + "_DARK", bm, mats["black"]))
        out.append(obj(pre + name + "_COLLAR", bc, mats["iron"], smooth=True))   # 검은 조임 띠 (녹 색은 머리등에서 살색으로 뜬다)
    # 쇠줄 (굽은 곳은 굽은 토막을 따라) · 걸이 (천장 볼트 판까지) · 고리 (75 cm 마다 쇠줄 → 관 등)
    sw = st + ([(P[-1], ceil[-1])] if torn and len(P) > 1 else []); lift = Z * (R + 0.08)
    W = [q for k, (p, _) in enumerate(sw) for q in [p + lift] + ([a + lift for a in arcs[k][1:-1]] if k in arcs else [])]
    bm = bmesh.new(); sweep(bm, W, 0.01, seg=5)
    for k, (p, cz) in enumerate(sw):
        w = p + lift
        if cz > w.z:                                                       # 걸이: 천장 볼트 판 + 볼트 머리 + 굵은 고리 쇠 → 쇠줄
            cyl(bm, w - Z * 0.01, (w.x, w.y, cz), 0.015, seg=6); box(bm, (w.x, w.y, cz - 0.012), (0.16, 0.16, 0.024)); cyl(bm, (w.x, w.y, cz - 0.05), (w.x, w.y, cz - 0.02), 0.035, seg=6)
            ax = Z.cross(sw[min(k + 1, len(sw) - 1)][0] - sw[max(k - 1, 0)][0]); torus(bm, w, ax.normalized() if ax.length > 1e-6 else X, 0.035, 0.012, seg=8, sub=4)
    for k in range(len(st) - 1):
        if k in arcs: continue
        a, b = st[k][0], st[k + 1][0]; m = max(1, int((b - a).length / 0.75))
        for j in range(m):
            u = (j + 0.5) / m; q = a.lerp(b, u); cyl(bm, q + lift + Z * 0.01, q + Z * (R - 0.02 - sg[k] * math.sin(math.pi * u)), 0.012, seg=5)
    if torn and len(P) > 1:
        L = (P[-1] - P[-2]).length; w0, w1 = P[-2] + lift, P[-1] + lift
        for j in range(max(1, int(L / 0.75))):                              # 관이 떨어져 나간 빈 고리
            w = w0.lerp(w1, (j + 0.6) / max(1, int(L / 0.75))); cyl(bm, w + Z * 0.01, w - Z * (0.10 + 0.08 * rnd.random()), 0.012, seg=5)
    out.append(obj("NOCOL_" + name + "_WIRE", bm, mats["iron"]))
    if torn and len(P) > 1: out += _torn(mats, P[-2], P[-1] - P[-2], FZ[-2], rnd, torn_side, R, name)
    return out, line


def _torn(mats, p0, d, floor_z, rnd, side=-1, R=DUCT_R, name="DUCT"):
    """찢겨 떨어진 토막: 살(나선 철사)이 남아 둥근 채로 굽어 내려와 바닥에 눕고, 끝은 옆으로 돌아 너덜너덜한 입 속이 검게 들여다보인다 (천이라 부딪힘 없음)"""
    d = Vector((d.x, d.y, 0)); d = d.normalized() if d.length > 1e-4 else X.copy(); s0 = Z.cross(d)
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
    out = [obj("NOCOL_" + name + "_TORN", bm, mats["cloth_yellow"], smooth=True)]
    bm = bmesh.new(); p, t = fr[n - 2][0], fr[n - 2][1]; cyl(bm, p - t * 0.01, p + t * 0.01, R - 0.05, seg=12); out.append(obj("NOCOL_" + name + "_TORN_DARK", bm, mats["black"]))   # 속 어둠
    bm = bmesh.new(); cyl(bm, p0 - d * 0.06, p0 + d * 0.06, R + 0.02, seg=12); out.append(obj("NOCOL_" + name + "_TORN_COLLAR", bm, mats["iron"], smooth=True))
    return out


def build(mats):
    """본보기: 선풍기 + 4 m 관 + 찢긴 끝 (천장 3.2 m). 미리보기 옵션 '{"_ceil": 3.2}'. 길면 미리보기 눈이 너무 멀어져 짧게 둔다 — 맵에서는 pts 를 길게 준다"""
    x0, y0, z0 = FAN_OUTLET
    return fan(mats) + duct(mats, [(x0 + 2.0 * i, y0, z0, 3.2) for i in range(4)], torn_end=True)[0]


def torn_demo(mats):
    """찢긴 끝만 가까이 보는 본보기 (미리보기: 함수 이름 torn_demo, 옵션 '{"_ceil": 3.2}')"""
    return duct(mats, [(2.0 * i, 0, 2.65, 3.2) for i in range(3)], torn_end=True)[0]


def bend_demo(mats):
    """방에서 굴로 ㄱ자로 꺾어 들어가 막장 앞에서 열린 입으로 끝나는 관 + 번호 단 선풍기 (미리보기: 함수 이름 bend_demo, 옵션 '{"_ceil": 3.2}')"""
    x0, y0, z0 = FAN_OUTLET
    return fan(mats, number="3") + duct(mats, [(x0, y0, z0, 3.2), (x0 + 2.0, y0, z0, 3.2), (x0 + 4.0, y0, z0, 3.2), (x0 + 4.0, y0 - 2.0, z0, 3.2), (x0 + 4.0, y0 - 4.0, z0, 3.2)], end="open")[0]
