"""광차 싣는 곳의 석탄 슈트(홈통). 위 막장에서 캔 석탄이 벽 위쪽 구멍에서 쇠 홈통을 타고 내려와 광차 위에서 쏟아진다.
본 사진: build/refs/cart/k01_ncms_10489_광산시설.jpg (한국광물자원공사 — 슈트 밑에서 탄 싣는 광차 줄). 사진에서 그대로 옮긴 것:
  - 광차 줄 바로 위에 매달린 두꺼운 쇠판 통(입). 통 옆판에 비스듬한 띠쇠 + 리벳 줄. 쇠는 칠 없이 탄가루 묻은 어두운 쇠
  - 입 아래의 둥글게 굽은 쇠판 — 벽 쪽으로 물러나 있고 석탄은 그 앞으로 쏟아진다 → "부채꼴 문": 닫히면 입 밑을 막고, 열리면 홈통 바닥 밑으로 돌아 들어간다
  - 통 위쪽에 비스듬히 걸린 밝은 쇠 공기 실린더
  - 위에서 사람 손 높이로 내려온 고무 호스 + 손 밸브. 일꾼은 광차 옆 걷는 쪽에 서서 그것을 잡는다
  - 쏟아지는 석탄은 입 폭만큼 넓은 검은 줄기 (고운 탄 + 모난 덩이) · 바닥에도 흘린 탄
지어낸 것(사진에 안 보임): 비스듬한 홈통 · 벽 쪽 쇠 다리 틀과 통을 매단 팔 보 · 벽을 뚫는 자리의 판자 덮개 통 + 각목 틀 · 문 팔과 지레의 생김새
  · 통 앞판(아래 반은 막고 그 위로 석탄이 수북이 보인다) · 손 밸브를 단 쇠 관 기둥 · 다리 사이 바닥에 흘린 탄 더미.
10-03 2차 (그림만 본 사람의 지적): 석탄 덩이를 회색(iron) → 검정으로 · 다리 틀도 녹슨 쇠(rust)로 — 맵에서 사진 재질이 깔리는 쇠는 rust 뿐이고
  iron · bare 는 무늬 없는 단색이라 넓은 면에 쓰면 칠 안 한 모형처럼 보인다 (iron 은 띠쇠 · 팔 · 받침 · 관 같은 작은 것에만)
  · 통 앞이 뚫린 액자 → 앞판 · 천장까지 올라가던 가는 쇠막대 → 다리 틀에서 뻗은 팔 보(천장 높이를 몰라도 뜨지 않는다)
  · 줄 하나에 매달린 밸브 → 바닥에 선 쇠 관 기둥에 붙인 밸브 + 지레 · 통나무 끝 밝은 원판 → 판자 덮개 통(아치가 어디를 지나도 이음새가 판자 위에 생긴다)
  · 쏟아질 때 통 속 더미가 문 모양대로 남던 것 → 뺌 · 바위 한 덩이 같던 줄기 → 홈통 바닥을 타고 넘어 떨어지는 골진 줄기 + 잔 덩이.
build(): 원점 = 레일 가운데 바닥, 슈트 입 바로 아래. x = 레일 방향. 벽 = side*+y 쪽 (입 높이에서 wall_d), 걷는 쪽 = side*-y.
  걷는 쪽은 레일 가운데에서 0.78 m 바깥 · 2.3 m 아래에 아무것도 없다 (밸브 기둥과 지레는 0.75 m 안). 그물은 side = 1 로 짓고 끝에서 y 를 뒤집는다.
"""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, sweep, obj

A = math.radians(40)                    # 홈통 기울기 (석탄이 저절로 미끄러지는 각)
SA, CA = math.sin(A), math.cos(A)
CY, CZ, GR = 0.25, 2.34, 0.50           # 문 굴대 자리 (y, z) · 문 반지름
TY, TZ = CY, CZ - GR                    # 홈통 바닥이 끝나는 자리 = 굴대 바로 아래, 문이 도는 원의 맨 밑 (1.84 m — 문 판 겉은 1.82 m)
GA = math.radians(-64)                  # 닫힌 문 판이 바닥 끝에서 걷는 쪽 위로 감싸는 각 → 입 앞 턱 = y −0.20, z 2.12
HW, WH = 0.40, 0.47                     # 홈통 속 반 폭 · 옆판 높이
RT = Matrix.Rotation(A, 3, "X")         # 홈통 기울기만큼 누인 틀
LEG_X = 0.72                            # 다리 자리 (레일 방향 ±)
OPEN = math.radians(62)                 # 열린 문이 돈 각 (벽 쪽으로 — 80도까지는 홈통 바닥에 안 걸린다)
S_FRONT, TOP = 0.72, 3.15               # 앞 다리 보가 홈통을 받치는 자리 (열린 문 끝 s 0.51 보다 뒤) · 앞 다리 꼭대기 보 높이
FRONT = 2.50                            # 통 앞판 꼭대기 — 그 위로 석탄이 수북이 보인다
YP = -0.62                              # 밸브 기둥 자리 (걷는 쪽, 광차 옆구리 0.405 와 걷는 길 사이)


def _pt(s, x=0.0, w=0.0):
    """홈통 자리표 → 소품 자리표. s = 바닥 끝에서 벽 쪽으로 올라간 거리, x = 옆, w = 바닥 판에서 뜬 높이"""
    return Vector((x, TY + s * CA - w * SA, TZ + s * SA + w * CA))


def _yz(th, r):
    """문 굴대를 도는 원 위의 점 (th = 맨 아래에서 벽 쪽으로 잰 각)"""
    return (CY + r * math.sin(th), CZ - r * math.cos(th))


class _Parts:
    """(물체 이름, 재질)마다 그물 하나. P("rust") · P("rubber", "NOCOL_CHUTE_HOSE")"""
    def __init__(s): s.bm = {}
    def __call__(s, mat, name="CHUTE"):
        if (name, mat) not in s.bm: s.bm[(name, mat)] = bmesh.new()
        return s.bm[(name, mat)]
    def finish(s, mats, side):
        out = []
        for (name, mat), bm in s.bm.items():
            assert all(v.co.y > -0.78 or v.co.z > 2.3 for v in bm.verts), "걷는 쪽 2.3 m 아래를 막는다: %s" % name
            if side < 0:
                for v in bm.verts: v.co.y = -v.co.y
            coal = "COAL" in name or "POUR" in name                              # 석탄은 모난 면 그대로
            o = obj("%s_%s" % (name, mat), bm, mats[mat], smooth=not coal)
            if not coal:
                try: o.data.set_sharp_from_angle(angle=math.radians(40))         # 둥근 면만 부드럽게
                except Exception: pass
            out.append(o)
        return out


def _bar(bm, p0, p1, w, t, x):
    """x 자리의 세로 면 안에 누운 납작 쇠: (y, z) p0 → p1, 너비 w, 두께 t(x 쪽)"""
    dy, dz = p1[0] - p0[0], p1[1] - p0[1]
    box(bm, (x, (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), (t, math.hypot(dy, dz), w), Matrix.Rotation(math.atan2(dz, dy), 3, "X"))


def _prism(bm, yz, x0, x1):
    """(y, z) 볼록 다각형을 x0~x1 로 민 판"""
    a = [bm.verts.new((x0, y, z)) for y, z in yz]; b = [bm.verts.new((x1, y, z)) for y, z in yz]; n = len(a)
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for i in range(n): bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))


def _arc(bm, r0, r1, x0, x1, a0, a1, n=8):
    """굴대를 도는 굽은 판 (반지름 r0~r1, x0~x1, 각 a0~a1)"""
    ring = [[bm.verts.new((x, *_yz(a0 + (a1 - a0) * i / n, r))) for r in (r0, r1) for x in (x0, x1)] for i in range(n + 1)]
    for P0, P1 in zip(ring, ring[1:]):
        for i, j in ((0, 1), (1, 3), (3, 2), (2, 0)): bm.faces.new((P0[i], P0[j], P1[j], P1[i]))
    for e in (ring[0], ring[-1]): bm.faces.new((e[0], e[1], e[3], e[2]))


def _lump(bm, c, r, rnd):
    """모난 석탄 덩이 하나 (20면체를 찌그러뜨린 것 — 공이 아니다)"""
    g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    R = Matrix.Rotation(rnd.uniform(0, 6.28), 3, "X") @ Matrix.Rotation(rnd.uniform(0, 6.28), 3, "Z")
    sx, sy, sz = rnd.uniform(0.7, 1.25), rnd.uniform(0.6, 1.0), rnd.uniform(0.5, 0.9)
    for v in g["verts"]:
        k = rnd.uniform(0.72, 1.12); v.co = R @ Vector((v.co.x * sx * k, v.co.y * sy * k, v.co.z * sz * k)) * r + Vector(c)


def _lining_y(z, wall_d):
    """강철 아치 속면 어림 (scene_mock HAUL_PROFILE 보다 0.25 m 안쪽): 높이 z 에서 벽까지의 거리"""
    if z <= 2.0: return wall_d
    (z0, d0), (z1, d1) = ((2.0, 0.0), (3.0, 0.7)) if z < 3.0 else ((3.0, 0.7), (3.5, 1.3))
    return wall_d - (d0 + (d1 - d0) * (z - z0) / (z1 - z0))


def _cross(w, wall_d):
    """홈통(높이 w 인 줄)이 아치 속면을 뚫는 s"""
    lo, hi = 0.0, 4.0
    for _ in range(30):
        mid = (lo + hi) / 2; p = _pt(mid, 0, w)
        if p.y < _lining_y(p.z, wall_d): lo = mid
        else: hi = mid
    return lo


def _trough(P, s_end):
    """비스듬한 쇠 홈통: 바닥 판 + 옆판 둘 + 위 테두리 + 세운 보강 쇠 + (사진) 비스듬한 띠쇠와 리벳 줄"""
    m = P("rust"); L = s_end
    box(m, _pt(L / 2, 0, -0.01), (2 * HW + 0.04, L, 0.02), RT)
    box(P("iron"), _pt(1.05, 0, -0.045), (2 * HW + 0.04, 0.012, 0.05), RT)       # 바닥 밑 보강 쇠
    for sx in (-1, 1):
        box(m, _pt(L / 2, sx * (HW + 0.01), WH / 2), (0.02, L, WH), RT)
        k = P("iron"); box(k, _pt(L / 2, sx * (HW + 0.035), WH - 0.006), (0.07, L, 0.012), RT)
        for s_ in (0.80, 1.60): box(k, _pt(s_, sx * (HW + 0.026), WH / 2), (0.012, 0.05, WH), RT)
        a, b = _pt(0.88, 0, 0.05), _pt(1.52, 0, WH - 0.05)
        _bar(k, (a.y, a.z), (b.y, b.z), 0.06, 0.012, sx * (HW + 0.026))
        for i in range(5):
            p = a.lerp(b, (i + 0.5) / 5); box(P("bare"), (sx * (HW + 0.036), p.y, p.z), (0.012, 0.024, 0.024), RT)


def _head(P):
    """입 통: 두꺼운 옆판 둘(아래 가장자리는 문이 도는 원을 따라 둥글다) + 앞판(걷는 쪽). 앞판은 통의 아래 반만 막는다 —
    그 위로 속에 찬 석탄이 수북이 보인다. 위는 트였다 (석탄이 홈통을 타고 들어오는 쪽)"""
    cheek = [_yz(GA * i / 6, GR - 0.015) for i in range(7)]
    a, b = _pt(0.75, 0, 0), _pt(0.75, 0, 0.50); fy, fz = cheek[-1]; cheek += [(fy, FRONT + 0.12), (b.y, b.z), (a.y, a.z)]
    for sx in (-1, 1): _prism(P("rust"), cheek, sx * (HW + 0.02), sx * (HW + 0.05))
    box(P("rust"), (0, fy - 0.01, (fz + FRONT) / 2), (2 * HW + 0.04, 0.02, FRONT - fz))   # 앞판
    r = P("iron")
    box(r, (0, fy - 0.025, FRONT - 0.025), (2 * HW + 0.10, 0.03, 0.05)); box(r, (0, fy - 0.025, fz + 0.03), (2 * HW + 0.10, 0.03, 0.06))   # 앞판 위 테 · 아래 턱
    for x in (-HW - 0.015, -0.14, 0.14, HW + 0.015): box(r, (x, fy - 0.022, (fz + FRONT) / 2), (0.05, 0.024, FRONT - fz))   # 세운 보강 쇠


def _gate(P, g):
    """부채꼴 문: 굽은 판이 입 밑을 막고, 양 옆 팔이 굴대를 돈다. 팔 위로 뻗은 지레 끝을 실린더가 밀면 판이 벽 쪽(홈통 바닥 밑)으로 돌아 열린다.
    g = 돈 각. 돌려주는 값 = 지레 끝 (y, z)"""
    a0, a1 = GA + g, math.radians(3) + g
    _arc(P("rust"), GR, GR + 0.02, -(HW + 0.07), HW + 0.07, a0, a1)
    lug = _yz(math.radians(150) + g, 0.28)
    for sx in (-1, 1):
        x = sx * (HW + 0.08); m = P("iron")
        _arc(m, GR - 0.06, GR + 0.02, x - 0.01, x + 0.01, a0, a1)                # 팔 테
        for th in (a0 + 0.08, a1 - 0.08): _bar(m, (CY, CZ), _yz(th, GR - 0.03), 0.07, 0.02, x)   # 팔 살
        _bar(m, (CY, CZ), lug, 0.07, 0.02, x)                                    # 지레
        cyl(P("iron"), (sx * (HW + 0.05), CY, CZ), (sx * (HW + 0.11), CY, CZ), 0.065, 12)   # 굴대 통
        cyl(P("bare"), (sx * HW, CY, CZ), (sx * (HW + 0.13), CY, CZ), 0.028, 10)    # 굴대 핀
    return lug


def _cylinder(P, sx, lug, q):
    """공기 실린더 (사진: 통 위에 비스듬히 걸린 밝은 쇠 통). q = 다리에 문 끝 (y, z) → 지레 끝. 돌려주는 값 = 호스 꽂는 자리"""
    x = sx * (HW + 0.16); q3, l3 = Vector((x, q[0], q[1])), Vector((x, lug[0], lug[1])); d = (l3 - q3).normalized()
    cyl(P("bare"), q3, q3 + d * 0.34, 0.045, 12)
    for t in (-0.02, 0.32): cyl(P("iron"), q3 + d * t, q3 + d * (t + 0.04), 0.055, 12)   # 양 끝 뚜껑
    cyl(P("bare"), q3 + d * 0.36, l3, 0.016, 10)                                 # 밀대
    box(P("iron"), l3 - d * 0.03, (0.05, 0.08, 0.05), Matrix.Rotation(math.atan2(d.z, d.y), 3, "X"))   # 밀대 끝 고리
    cyl(P("bare"), (sx * (HW + 0.06), lug[0], lug[1]), (sx * (HW + 0.20), lug[0], lug[1]), 0.014, 10)
    box(P("iron"), (sx * (HW + 0.235), q[0], q[1]), (0.09, 0.10, 0.12))          # 다리에 무는 받침
    p = q3 + d * 0.10 + Vector((0, 0, 0.04)); cyl(P("iron"), p, p + Vector((0, 0, 0.07)), 0.014, 10)
    return p + Vector((0, 0, 0.07))


def _hleg(P, x, y, z1):
    """H 꼴 쇠 다리 + 바닥 판"""
    bm = P("rust")
    for dy in (-0.044, 0.044): box(bm, (x, y + dy, z1 / 2), (0.10, 0.012, z1))
    box(bm, (x, y, z1 / 2), (0.01, 0.088, z1)); box(P("rust"), (x, y, 0.008), (0.22, 0.22, 0.016))


def _frame(P, s_back):
    """벽 쪽 쇠 다리 틀: 앞 다리 둘(높다 — 실린더와 팔 보를 문다) + 뒤 다리 둘, 홈통 밑 가로 보 둘, 가새(검은 쇠).
    홈통이 벽에 붙은 판이 아니라 틀에 얹힌 것으로 보이게 한다. 돌려주는 값 = 앞 보 자리"""
    m, r = P("rust"), P("iron"); f, b = _pt(S_FRONT, 0, -0.07), _pt(s_back, 0, -0.07)
    for sx in (-1, 1):
        x = sx * LEG_X; _hleg(P, x, f.y, TOP + 0.05); _hleg(P, x, b.y, b.z)
        _bar(r, (f.y, 1.2), (b.y, 1.2), 0.06, 0.06, x)
        _bar(r, (f.y, 0.22), (b.y, min(2.35, b.z - 0.2)), 0.06, 0.02, x + sx * 0.06)
    for p in (f, b): box(m, p, (2 * LEG_X + 0.10, 0.10, 0.10), RT)               # 홈통 밑 보
    box(m, (0, f.y, TOP), (2 * LEG_X + 0.10, 0.10, 0.10)); box(r, (0, f.y, 1.2), (2 * LEG_X, 0.06, 0.06))
    for sg in (-1, 1):                                                           # 뒤 다리 사이 X 가새 (ㄱ자 쇠 굵기) + 가운데 이음 판
        box(r, (0, b.y + 0.062, 1.30), (math.hypot(2 * LEG_X, 2.1), 0.03, 0.07), Matrix.Rotation(sg * math.atan2(2.1, 2 * LEG_X), 3, "Y"))
    box(m, (0, b.y + 0.066, 1.30), (0.20, 0.03, 0.20))
    return f


def _gallows(P, f):
    """입 통을 매단 팔 보: 앞 다리 꼭대기 보에서 레일 위로 뻗은 쇠 보 둘 + 통 옆판을 무는 납작 걸이 쇠 넷.
    (1차는 천장까지 가는 쇠막대였다 — 어두운 천장에 닿는지 안 보여 떠 보였고, 천장 높이가 다르면 정말 뜬다)"""
    for sx in (-1, 1):
        box(P("rust"), (sx * (HW + 0.035), (f.y - 0.16) / 2, TOP), (0.07, f.y + 0.16, 0.11))
        for y in (-0.10, 0.30):
            box(P("iron"), (sx * (HW + 0.056), y, (TOP + FRONT) / 2), (0.016, 0.06, TOP - FRONT))
            box(P("bare"), (sx * (HW + 0.068), y, FRONT + 0.07), (0.012, 0.026, 0.026))   # 볼트 머리


def _collar(P, s0, s1, rnd):
    """벽을 뚫는 자리: 홈통을 둘러싼 타르 판자 덮개 통(s0 ~ s1) + 굴 쪽 끝의 각목 틀. 아치 그물은 못 자르므로, 통이 굴 안쪽에서
    벽 속 깊이까지 이어져 아치가 어디를 지나든 이음새가 판자 위에 생긴다 (판 한 장을 아치 면에 맞추는 것보다 자리 어긋남에 강하다)"""
    L, mid = s1 - s0, (s0 + s1) / 2; t = P("tar")
    for sx in (-1, 1):
        for i in range(3):
            e = 0.03 * rnd.random(); box(t, _pt(mid + e / 2, sx * 0.615, -0.06 + 0.295 * i), (0.03, L - e, 0.28), RT)
    for w in (-0.215, 0.685):
        for i in range(5):
            e = 0.03 * rnd.random(); box(t, _pt(mid + e / 2, -0.504 + 0.252 * i, w), (0.245, L - e, 0.03), RT)
    lg = P("timber"); s = s0 + 0.02
    for w in (-0.275, 0.745): box(lg, _pt(s, 0, w), (1.56, 0.13, 0.13), RT)       # 문지방 · 머리 각목
    for sx in (-1, 1): box(lg, _pt(s + 0.01, sx * 0.695, 0.235), (0.13, 0.13, 1.03), RT)   # 선 각목


def _controls(P, f, ports, opened):
    """손 밸브 (사진: 위에서 내려온 고무 호스 끝의 밸브를 일꾼이 광차 옆에서 잡고 있다). 사람 없이 줄에만 매달면 떠 보여서,
    앞 다리 꼭대기에서 레일 위를 건너와 바닥까지 내려선 쇠 공기 관을 기둥 삼아 밸브를 붙였다. 호스 둘이 관을 따라 올라가 실린더로 간다.
    지레는 걷는 쪽에서 옆으로 보이게 레일 방향으로 젖혀진다 (닫힘 = 입 반대쪽, 쏟는 중 = 입 쪽)"""
    x, zt = LEG_X, TOP + 0.075; m = P("iron")
    sweep(m, [(x, f.y + 0.04, zt), (x, YP + 0.12, zt), (x, YP + 0.035, zt - 0.035), (x, YP, zt - 0.12), (x, YP, 0.01)], 0.03, 10)
    box(P("rust"), (x, YP, 0.008), (0.18, 0.18, 0.016))                          # 바닥 판
    box(m, (x, YP, 1.22), (0.12, 0.11, 0.18))                                    # 밸브 몸통
    for z in (1.75, 2.55): box(m, (x, YP + 0.025, z), (0.10, 0.12, 0.03))        # 호스 물림쇠
    yf = YP - 0.055; piv = Vector((x, yf - 0.025, 1.24)); tip = piv + Vector((-0.11 if opened else 0.11, 0, 0.21))
    cyl(P("rust"), (x, yf, 1.24), (x, yf - 0.012, 1.24), 0.10, 12)               # 지레 뒤 둥근 판
    cyl(m, (x, yf, 1.24), (x, yf - 0.04, 1.24), 0.024, 10)                       # 지레 굴대
    cyl(P("bare"), piv, tip, 0.011, 10); cyl(P("rubber"), piv.lerp(tip, 0.68), piv.lerp(tip, 1.04), 0.02, 10)   # 지레 + 손잡이
    h = P("rubber", "NOCOL_CHUTE_HOSE")
    for dx in (-0.022, 0.022):
        sweep(h, [(x + dx, YP + 0.045, 1.30), (x + dx, YP + 0.045, zt - 0.22), (x + dx, YP + 0.07, zt - 0.10), (x + dx, YP + 0.16, zt - 0.045), (x + dx, f.y - 0.06, zt - 0.045)], 0.014, 10)
    for p in ports:
        sweep(h, [p, p + Vector((0, 0, 0.10)), (p.x, f.y - 0.085, TOP - 0.04), (p.x, f.y - 0.07, TOP + 0.04), (p.x, f.y - 0.03, TOP + 0.064), (p.x, f.y, TOP + 0.062), (x - 0.04, f.y, TOP + 0.062)], 0.012, 10)


def _coal(P, rnd, s_end, s_vis, opened):
    """석탄 (모두 검정): 홈통 속 탄 켜 + 닫혔을 때 입 통 속 더미(앞판 위로 수북이 보인다) + 다리 사이 바닥에 흘린 탄.
    닫힌 슈트는 문 뒤로 석탄이 밀려 입 쪽이 꽉 찬다. 열리면 더미가 빠져 얇은 켜만 흐른다 (_pour 가 줄기를 잇는다)"""
    bed = P("black", "NOCOL_CHUTE_COAL")
    ns, nx = 8, 4; xs = [-0.39 + 0.78 * j / nx for j in range(nx + 1)]; top, bot = [], []
    back = 0.0 if opened else 0.28
    wbed = lambda s_, x_: 0.12 + 0.06 * (1 - (x_ / HW) ** 2) + back * max(0.0, 1 - (s_ - 0.5))
    for i in range(ns + 1):
        s = 0.50 + (s_end - 0.52) * i / ns
        top.append([bed.verts.new(_pt(s, x_, wbed(s, x_) + rnd.uniform(-0.02, 0.02))) for x_ in xs]); bot.append([bed.verts.new(_pt(s, x_, 0.004)) for x_ in xs])
    for i in range(ns):
        for j in range(nx):
            bed.faces.new((top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j])); bed.faces.new((bot[i][j], bot[i + 1][j], bot[i + 1][j + 1], bot[i][j + 1]))
        for j in (0, nx): bed.faces.new((top[i][j], top[i + 1][j], bot[i + 1][j], bot[i][j]))
    for j in range(nx):
        for i in (0, ns): bed.faces.new((top[i][j], top[i][j + 1], bot[i][j + 1], bot[i][j]))
    if not opened:
        a, b = _pt(0.55), _pt(0.55, 0, 0.50); fy = _yz(GA, GR)[0] + 0.03; zt = FRONT + 0.07   # 입 통 속 더미 (문 판 위에 얹혀 앞판 꼭대기 위까지)
        heap = [_yz(GA * i / 5, GR - 0.004) for i in range(6)] + [(fy, zt), (b.y, b.z), (a.y, a.z)]
        _prism(bed, heap, -0.38, 0.38)
        for i in range(9):                                                       # 앞판 가장자리에 걸친 덩이 줄
            r = rnd.uniform(0.045, 0.075); _lump(bed, (-0.34 + 0.085 * i + rnd.uniform(-0.02, 0.02), fy + rnd.uniform(0.0, 0.05), zt + r * 0.35), r, rnd)
        for _ in range(16):
            r = rnd.uniform(0.04, 0.08); _lump(bed, (rnd.uniform(-0.32, 0.32), rnd.uniform(fy + 0.06, b.y), zt + r * 0.25), r, rnd)
    for _ in range(8):
        s_, x_ = rnd.uniform(0.6, s_vis), rnd.uniform(-0.3, 0.3); r = rnd.uniform(0.04, 0.08); _lump(bed, _pt(s_, x_, wbed(s_, x_) + r * 0.3), r, rnd)
    cx, cy, n, RX, RY = 0.0, 1.06, 12, 0.60, 0.40                                # 바닥에 흘린 탄 더미 (광차 뒤, 다리 사이) — 뿔이 아니라 낮고 넓게
    ring = lambda k, z, j: [bed.verts.new((cx + RX * k * math.cos(2 * math.pi * i / n) * rnd.uniform(0.78, 1.12), cy + RY * k * math.sin(2 * math.pi * i / n) * rnd.uniform(0.78, 1.12), z + rnd.uniform(-j, j))) for i in range(n)]
    rs, tp = [ring(1.0, -0.005, 0.0), ring(0.72, 0.11, 0.025), ring(0.42, 0.20, 0.03), ring(0.16, 0.25, 0.02)], bed.verts.new((cx + 0.05, cy - 0.03, 0.27))
    bed.faces.new(rs[0][::-1])
    for R0, R1 in zip(rs, rs[1:]):
        for i in range(n): bed.faces.new((R0[i], R0[(i + 1) % n], R1[(i + 1) % n], R1[i]))
    for i in range(n): bed.faces.new((rs[-1][i], rs[-1][(i + 1) % n], tp))
    for _ in range(26):
        t = rnd.uniform(0, 2 * math.pi); k = rnd.uniform(0.15, 1.12); r = rnd.uniform(0.04, 0.085)
        _lump(bed, (cx + RX * k * math.cos(t), cy + RY * k * math.sin(t), max(0.0, 0.27 * (1 - k)) + r * 0.3), r, rnd)


def _chip(bm, c, r, rnd):
    """잔 석탄 조각 (찌그러뜨린 8면체 — 덩이보다 싸서 많이 뿌릴 수 있다)"""
    R = Matrix.Rotation(rnd.uniform(0, 6.28), 3, "X") @ Matrix.Rotation(rnd.uniform(0, 6.28), 3, "Z")
    v = [bm.verts.new(R @ (Vector(d) * r * rnd.uniform(0.55, 1.25)) + Vector(c)) for d in ((1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    for i in range(4): bm.faces.new((v[i], v[(i + 1) % 4], v[4])); bm.faces.new((v[(i + 1) % 4], v[i], v[5]))


def _pour(P, rnd, z_end):
    """쏟아지는 석탄 줄기 (사진: 입 폭만큼 넓은 검은 줄기): 홈통 바닥을 타고 내려와 바닥 끝을 넘어 포물선으로 광차 속(z_end)까지.
    큰 면이 보이면 바위 한 덩이로 읽히고, 매끈하면 쇠판으로 읽힌다 → 납작한 속 덩어리는 거의 가리고 겉을 잔 조각 220개로 덮는다.
    아래 끝은 들쭉날쭉하고, 조각은 아래로 갈수록 줄기 밖으로 흩어진다"""
    bm = P("black", "NOCOL_CHUTE_POUR"); n, v0 = 14, 1.2
    p0 = _pt(0.0, 0, 0.10); path = [(_pt(s, 0, 0.10), 0.34, 0.10) for s in (0.62, 0.31, 0.0)]   # (가운데, 반 폭, 반 두께)
    t_end = (-v0 * SA + math.sqrt((v0 * SA) ** 2 + 19.6 * (p0.z - z_end))) / 9.8; m = max(5, round((p0.z - z_end) / 0.08))
    for i in range(1, m + 1):
        t = t_end * i / m; drop = v0 * SA * t + 4.9 * t * t; k = min(1.0, drop / 0.47)
        path.append((Vector((0, p0.y - v0 * CA * t, p0.z - drop)), 0.34 - 0.07 * k, 0.10 - 0.04 * k))
    col = [rnd.uniform(0.55, 0.95) for _ in range(n)]                            # 기둥마다 다른 굵기 = 흐르는 방향으로 이어진 골
    nrm = lambda i: (lambda d: Vector((0, -d.z, d.y)))((path[min(i + 1, len(path) - 1)][0] - path[max(i - 1, 0)][0]).normalized())
    def surf(i, a, k):                                                           # 줄기 겉의 점 (i = 고리, a = 둘레 각, k = 부푼 배수)
        c, hw, th = path[i]; ca = math.cos(a)
        return c + Vector((hw * math.copysign(abs(ca) ** 0.6, ca) * k, 0, 0)) + nrm(i) * (th * math.sin(a) * k)
    rings = [[bm.verts.new(surf(i, 2 * math.pi * q / n, col[q]) + Vector((0, rnd.uniform(-0.015, 0.015), 0))) for q in range(n)] for i in range(len(path))]
    for v in rings[-1]: v.co.z += rnd.uniform(0.0, 0.14)                         # 아래 끝은 들쭉날쭉 (z_end 보다 아래로는 안 간다)
    for R0, R1 in zip(rings, rings[1:]):
        for q in range(n): bm.faces.new((R0[q], R0[(q + 1) % n], R1[(q + 1) % n], R1[q]))
    bm.faces.new(rings[0][::-1]); c = bm.verts.new(path[-1][0] + Vector((0, 0, 0.08)))
    for q in range(n): bm.faces.new((rings[-1][q], rings[-1][(q + 1) % n], c))
    for j in range(220):                                                         # 셋에 둘은 걷는 쪽에서 보이는 앞면에, 여섯에 하나는 줄기 밖으로 튄다 (아래일수록 멀리)
        i = 2 + int(rnd.random() * (len(path) - 2.001)); fall = (i - 2) / (len(path) - 3); r = rnd.uniform(0.022, 0.052)
        c, hw, th = path[i]; u = rnd.uniform(-1, 1); sg = -1 if j % 3 else 1; k = 1.0 if j % 6 else 1.0 + 0.8 * fall * rnd.random()
        p = c + Vector((u * hw * k, 0, rnd.uniform(-0.04, 0.04))) + nrm(i) * (sg * th * (1 - abs(u) ** 3) * k * rnd.uniform(0.85, 1.1))
        _chip(bm, (p.x, p.y, max(z_end + r * 0.6, p.z)), r, rnd)


def build(mats, wall_d=2.2, roof_h=3.6, side=1, pouring=False, seed=0, collar_off=0.0, pour_to=1.45):
    """roof_h = 아치 꼭대기 높이. 이제 천장에 닿는 것이 없다 — 틀 꼭대기 3.23 m 가 그 아래 들어가는지만 본다.
    collar_off = 판자 덮개 통을 홈통을 따라 벽 속(+) · 굴 안(−)으로 옮기는 거리 (맵의 아치 속면이 어림과 다를 때 맞춘다)
    pour_to = 쏟아지는 줄기가 끝나는 높이 (광차 속 석탄 윗면. 빈 광차면 낮춘다)"""
    assert roof_h >= TOP + 0.15, "아치 꼭대기가 슈트 틀(3.23 m)보다 낮다"
    rnd = random.Random(seed); P = _Parts()
    sb = _cross(0.0, wall_d) + collar_off; s0, s_end = sb - 0.32, sb + 0.75    # 덮개 통: 어림한 아치 자리보다 0.3 m 굴 안에서 시작해 0.75 m 벽 속까지
    _trough(P, s_end); _head(P); lug = _gate(P, OPEN if pouring else 0.0)
    f = _frame(P, min(1.25, sb - 0.45))
    ports = [_cylinder(P, sx, lug, (f.y, 2.82)) for sx in (-1, 1)]
    _gallows(P, f); _collar(P, s0, s_end, rnd); _controls(P, f, ports, pouring); _coal(P, rnd, s_end, s0, pouring)
    if pouring: _pour(P, random.Random(seed + 1), pour_to)
    return P.finish(mats, side)
