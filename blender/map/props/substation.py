"""갱내 배전실 (변압기 + 서 있는 배전함 줄). Blender 안에서만 돈다.
10-03 판정 "실제 배전실이 이렇게 생겼나, 배전실 같지 않다" (빈 바위 방에 벽 계기판 하나) 를 고친다.
레퍼런스 메모(갱내 변전소 사진 3장 + 변압기 사진)의 공통 구조:
  바닥에 선 쇠 함이 낮은 받침 위에 벽을 따라 한 줄 — 함마다 문 · 손잡이 · 둥근 계기 · 창 또는 숨구멍 · 이름표,
  함 위에서 굵은 전선이 천장 가까이 올라가 벽의 갈고리를 타고 달린다,
  줄 끝에 기름 변압기 하나 — 네모 통 + 세로 식힘 날개 + 뚜껑 위 사기 애자(긴 것 3 · 짧은 것 4) + 받침대 위 작은 기름 통 + 들어 올리는 귀 + 썰매 틀,
  앞에 허리 높이 울타리와 "고압위험" 판, 불 끄는 모래 통, 함 앞 바닥에 고무 깔판.
법(조사 09 의 2-6): 변압기 밑에는 새는 기름을 빨아들일 모래, 고압 장치엔 "고압위험" + 울타리 + "출입금지", 방 출입구는 둘 이상 (울타리 양 끝을 틔워 둔다).
2차 손질(사진만 본 사람의 지적): 전선은 부드럽게 휘고 처지며 양 끝이 쇠 상자로 들어간다 · 변압기를 사람 가슴 위까지 키웠다 ·
  기름 통을 옆으로 뉘어 원판으로 안 보이게 · 열린 함 속은 밝은 돌판 + 검은 손잡이 칼 스위치 · 녹은 들쭉날쭉한 조각 · 울타리는 검은 쇠 관 ·
  나무 발판(깔판 · 침목으로 읽힘) 대신 고무 깔판 · 벽 전등 · "출입금지" 판.
build(mats, cubicles, wall_d, ceil_h, state, seed)
  원점 = 바닥, 줄 뒤쪽 가운데. 벽 = y = +wall_d (함 뒷면은 y = −0.12), 보는 쪽 = −y. 줄은 x 방향: −x 끝이 변압기, +x 쪽으로 함.
  줄 길이 = 1.75 + 0.85 × 함 수 (4칸이면 5.15 m). 전선 줄은 양 끝으로 1 m 씩 더 나간다 (−x 끝은 천장 상자로, +x 끝은 벽 상자로). 울타리는 y = −1.7.
  state="old": 녹 · 손때, 문 하나가 열려 속의 칼 스위치(내려 놓고 꼬리표를 달았다)가 보임, 계기 유리 하나는 빠지고 하나는 금 감, 변압기 기름이 샌 자국.
"""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, sweep, obj, text_mesh

CW = 0.85      # 함 한 칸 너비
TZ = 1.75      # 변압기 자리 너비 (줄의 −x 끝)
PL = 0.12      # 함 밑 콘크리트 받침 높이
YB = -0.12     # 함 뒷면 y (바위벽이 울퉁불퉁해 벽에서 띄운다)
YG = -1.70     # 울타리 y
TY = -0.52     # 변압기 통 가운데 y
ZL = 1.50      # 변압기 뚜껑 윗면 높이 (사람 가슴 위 — 1차의 1.19 는 "작고 가볍다" 였다)
RUN = ((-0.05, 0.028), (-0.108, 0.020), (-0.156, 0.024))   # 벽 전선 줄: (벽에서 떨어진 거리, 굵기 반지름)
HV = (0.06, 0.24, 0.42)            # 긴 애자 x (통 가운데에서)
LV = (-0.12, 0.04, 0.20, 0.36)     # 짧은 애자 x
PORC = "concrete"                     # 사기 애자 재질 (맵에서 너무 하얗게 튀면 "concrete" 로 — 잿빛 사기)


class _Parts:
    """재질 이름마다 그물 하나 (부딪힘 없는 것은 soft 로 따로 모은다)"""
    def __init__(s, mats): s.mats, s.bm = mats, {}
    def __getitem__(s, k):
        if k not in s.bm: s.bm[k] = bmesh.new()
        return s.bm[k]
    def soft(s, k): return s["NOCOL:" + k]
    def finish(s):
        out = []
        for k, bm in s.bm.items():
            nocol, _, m = k.rpartition(":")
            o = obj(("NOCOL_SUB_" if nocol else "SUB_") + m, bm, s.mats[m], smooth=True)
            try: o.data.set_sharp_from_angle(angle=math.radians(40))   # 둥근 옆면만 부드럽게, 상자 모서리 · 뚜껑은 날카롭게
            except Exception: pass
            out.append(o)
        return out


def _turn(vs, R, pivot):
    pivot = Vector(pivot)
    for v in vs: v.co = R @ (v.co - pivot) + pivot


def _smooth(pts, subs=2):
    """꺾인 점들을 부드러운 곡선으로 (점마다 지나간다). subs = 구간을 나누는 수 (하나 또는 구간별 목록)"""
    p = [Vector(q) for q in pts]; out = [p[0]]
    for i in range(len(p) - 1):
        a, b, c, d = p[max(i - 1, 0)], p[i], p[i + 1], p[min(i + 2, len(p) - 1)]; n = subs if isinstance(subs, int) else subs[i]
        for s in range(1, n + 1):
            t = s / n; out.append(0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t ** 3))
    return out


def _ragged(bm, x0, x1, y, z0, hs, th=0.003):
    """들쭉날쭉한 얇은 조각 (녹 · 때 · 기름 자국). 밑변 z0 에서 hs 만큼 솟은(음수면 흘러내린) 윤곽, 앞을 보는 면 y 에 붙는다"""
    n = len(hs); vs = []
    for i, h in enumerate(hs):
        x = x0 + (x1 - x0) * i / (n - 1); h = h if abs(h) > 0.004 else math.copysign(0.004, hs[1])
        vs.append([bm.verts.new((x, yy, zz)) for yy in (y - th, y) for zz in (z0, z0 + h)])   # 앞아래 · 앞위 · 뒤아래 · 뒤위
    for a, b in zip(vs, vs[1:]):
        for i, j in ((0, 1), (3, 2), (1, 3), (2, 0)): bm.faces.new((a[i], b[i], b[j], a[j]))
    for e in (vs[0], vs[-1]): bm.faces.new((e[0], e[1], e[3], e[2]))
    return [v for q in vs for v in q]


def _drips(bm, rnd, x, y, z, L, n=3):
    """흘러내린 녹물 줄: 가늘고 길이가 다른 세로 줄 n 개가 나란히 (z 에서 아래로, 가장 긴 것이 L)"""
    vs = []
    for i in range(n):
        w = rnd.uniform(0.010, 0.020); l = L * (1.0 if i == 0 else rnd.uniform(0.3, 0.8)); vs += box(bm, (x + w / 2, y - 0.0015, z - l / 2), (w, 0.003, l)); x += w + rnd.uniform(0.003, 0.012)
    return vs


def _text(name, body, loc, size, mat):
    """판 글자. 거의 곧게 이어진 테두리 점을 녹여 삼각형을 줄인다 (글자 셋이 1,500 개쯤 먹던 것)"""
    o = text_mesh(name, body, loc, size, mat, extrude=0.0)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(14), verts=bm.verts, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free(); return o


def _meter(P, rnd, mx, yd, mz, mr, fault=None, trim="iron"):
    """둥근 계기: 두꺼운 쇠 테 + 밝은 눈금판 + 눈금 줄 셋 + 바늘 + 바늘 축. fault = "gone"(유리 빠져 속이 검다) / "crack"(금 간 유리). 만든 점들을 돌려준다 (문과 같이 돌리려고)"""
    vs = cyl(P[trim], (mx, yd, mz), (mx, yd - 0.06, mz), mr, seg=12)
    if fault == "gone": return vs + cyl(P["black"], (mx, yd - 0.06, mz), (mx, yd - 0.063, mz), mr - 0.02, seg=12)
    vs += cyl(P["glass"], (mx, yd - 0.06, mz), (mx, yd - 0.066, mz), mr - 0.02, seg=12)
    bl = P["black"]; ra = mr - 0.04; pz = mz - mr * 0.38
    for a in (-0.85, 0.0, 0.85): vs += box(bl, (mx + ra * math.sin(a), yd - 0.068, pz + ra * 1.1 * math.cos(a)), (mr * 0.42, 0.004, 0.009), Matrix.Rotation(a, 3, "Y"))
    a = rnd.uniform(-0.8, 0.8); nl = mr * 0.95
    vs += box(bl, (mx + nl / 2 * math.sin(a), yd - 0.069, pz + nl / 2 * math.cos(a)), (0.008, 0.004, nl), Matrix.Rotation(a, 3, "Y"))
    vs += box(P["bare"], (mx, yd - 0.071, pz), (0.022, 0.006, 0.022))
    if fault == "crack":
        vs += box(bl, (mx + 0.005, yd - 0.0685, mz + 0.012), (mr * 1.45, 0.003, 0.003), Matrix.Rotation(0.7, 3, "Y"))
        vs += box(bl, (mx + 0.03, yd - 0.0685, mz + 0.035), (mr * 0.6, 0.003, 0.003), Matrix.Rotation(-0.6, 3, "Y"))
    return vs


def _door(P, rnd, cx, zb, zt, yf, kind, old, open_deg, fault, body, trim):
    """함 문짝과 문에 붙은 것 전부 (이름표 · 계기 · 표시등 · 손잡이 · 경첩 · 숨구멍 · 녹 · 손때). open_deg 만큼 오른쪽 경첩을 축으로 열린다"""
    DW = CW - 0.12; TH = 0.03; yd = yf - TH; vs = []; z0, z1 = zb + 0.06, zt - 0.06      # yd = 문 앞면
    pa, k, bl, wh = P[body], P[trim], P["black"], P["white"]
    vs += box(pa, (cx, yf - TH / 2, (z0 + z1) / 2), (DW, TH, z1 - z0))
    # 이름표 (흰 판 + 글줄)
    vs += box(wh, (cx, yd - 0.003, zt - 0.15), (0.22, 0.006, 0.055)); vs += box(bl, (cx - 0.02, yd - 0.007, zt - 0.15), (0.14, 0.003, 0.012))
    # 계기: 0형 = 둥근 계기 둘, 1형 = 둥근 계기 하나 + 속 들여다보는 작은 창
    mz = zt - 0.37
    if kind == 0:
        vs += _meter(P, rnd, cx - 0.17, yd, mz, 0.095, fault if fault == "crack" else None, trim)
        vs += _meter(P, rnd, cx + 0.17, yd, mz, 0.095, fault if fault == "gone" else None, trim)
        lx, sx0 = cx, cx - 0.17
    else:
        vs += _meter(P, rnd, cx - 0.16, yd, mz, 0.105, fault, trim)
        vs += box(k, (cx + 0.17, yd - 0.007, mz), (0.26, 0.014, 0.20)); vs += box(bl, (cx + 0.17, yd - 0.009, mz), (0.20, 0.014, 0.14))
        vs += box(k, (cx + 0.17, yd - 0.018, mz), (0.012, 0.006, 0.14))
        lx, sx0 = cx - 0.16, cx - 0.16
    # 표시등 (빨간 알 하나)
    vs += cyl(P["red"], (lx, yd, mz - 0.19), (lx, yd - 0.032, mz - 0.19), 0.022, seg=10, r1=0.013)
    # 문 손잡이 (왼쪽, 굵은 지렛대) + 큰 경첩 둘 (오른쪽)
    hx, hz = cx - DW / 2 + 0.08, zb + 0.95; zh1 = zt - 0.30
    vs += cyl(k, (hx, yd, hz), (hx, yd - 0.04, hz), 0.036, seg=10); vs += box(k, (hx, yd - 0.049, hz - 0.07), (0.034, 0.018, 0.20))
    for z in (zb + 0.32, zh1): vs += box(k, (cx + DW / 2 - 0.005, yd - 0.004, z), (0.04, 0.034, 0.15))
    # 숨구멍 (비스듬한 살 넷, 뒤는 검다)
    lz = zb + 0.20
    vs += box(bl, (cx, yd - 0.003, lz + 0.085), (0.46, 0.006, 0.25))
    for j in range(4): vs += box(pa, (cx, yd - 0.02, lz + 0.058 * j), (0.46, 0.006, 0.052), Matrix.Rotation(math.radians(-35), 3, "X"))
    for sx in (-1, 1): vs += box(pa, (cx + sx * 0.236, yd - 0.016, lz + 0.085), (0.014, 0.032, 0.27))
    # 0형: 문 밖으로 나온 차단기 손잡이 (둥근 축 + 긴 쇠 팔 + 검은 손잡이 알)
    if kind == 0:
        ox, oz = cx + 0.15, zb + 0.74; a = rnd.choice((0.55, -0.8, 2.2))
        vs += cyl(k, (ox, yd, oz), (ox, yd - 0.05, oz), 0.055, seg=12)
        ex, ez = ox + 0.24 * math.sin(a), oz + 0.24 * math.cos(a)
        vs += box(k, ((ox + ex) / 2, yd - 0.06, (oz + ez) / 2), (0.035, 0.02, 0.27), Matrix.Rotation(a, 3, "Y"))
        vs += cyl(bl, (ex, yd - 0.06, ez), (ex, yd - 0.15, ez), 0.022, seg=10)
        vs += box(wh, (ox, yd - 0.003, oz + 0.30), (0.09, 0.006, 0.035))
    if old:   # 녹: 문 아랫단에서 들쭉날쭉 올라온 띠 · 경첩과 계기 밑 · 윗단에서 흘러내린 가는 줄. 손 닿는 자리는 칠이 닳아 쇠가 드러났다
        ru = P["rust"]
        vs += _ragged(ru, cx - DW / 2 + 0.004, cx + DW / 2 - 0.004, yd, z0 + 0.002, [rnd.uniform(0.01, 0.05) + (rnd.uniform(0.04, 0.12) if rnd.random() < 0.35 else 0.0) for _ in range(12)])
        vs += _drips(ru, rnd, cx + DW / 2 - 0.05, yd, zh1 - 0.075, rnd.uniform(0.20, 0.50), 2)
        vs += _drips(ru, rnd, sx0 - 0.02 + rnd.uniform(-0.03, 0.03), yd, mz - 0.09, rnd.uniform(0.12, 0.30), 2)
        vs += _drips(ru, rnd, cx + rnd.uniform(-0.28, 0.22), yd, z1, rnd.uniform(0.10, 0.34), 3)
        if body != "iron": vs += box(P["bare"], (hx + 0.005, yd - 0.001, hz - 0.05), (0.10, 0.002, 0.26)); vs += box(P["bare"], (cx - DW / 2 + 0.006, yd - 0.001, hz + 0.05), (0.012, 0.002, 0.55))
    if open_deg: _turn(vs, Matrix.Rotation(math.radians(open_deg), 3, "Z"), (cx + DW / 2, yf, 0))


def _inside(P, cx, zb, zt, yf, old):
    """열린 함 속: 잿빛 돌판 + 3극 칼 스위치(당겨 내려 전기를 끊어 놓았다 — 검은 가로대와 손잡이, 꼬리표) + 사기 퓨즈 셋 + 잘린 전선"""
    W = CW - 0.02; yp = yf + 0.34; h = zt - zb; LB = 0.26
    box(P["concrete"], (cx, yp + 0.01, (zb + zt) / 2), (W - 0.04, 0.02, h - 0.04))
    cu, po, bl = P["bare"], P["white"], P["black"]; hz = zb + 0.86; vs = []; piv = Vector((cx, yp - 0.05, hz)); R = Matrix.Rotation(math.radians(48), 3, "X")
    for sx in (-1, 0, 1):
        x = cx + sx * 0.19
        box(po, (x, yp - 0.012, hz + 0.13), (0.09, 0.024, 0.40))                                    # 사기 받침
        box(cu, (x, yp - 0.045, hz), (0.05, 0.045, 0.05))                                           # 아래 경첩
        for e in (-1, 1): box(cu, (x + e * 0.017, yp - 0.045, hz + LB), (0.01, 0.045, 0.06))       # 위 물림쇠
        vs += box(cu, (x, yp - 0.05, hz + LB / 2 + 0.01), (0.024, 0.008, LB + 0.02))                # 칼날
        box(cu, (x, yp - 0.028, (hz + LB + 0.03 + zt - 0.02) / 2), (0.03, 0.008, zt - 0.02 - hz - LB - 0.03))   # 위로 가는 구리 띠
        box(po, (x, yp - 0.04, zb + 0.46), (0.075, 0.07, 0.16)); box(cu, (x, yp - 0.035, zb + 0.46), (0.03, 0.03, 0.23))   # 사기 퓨즈
        sweep(P.soft("rubber"), [(x, yp - 0.035, zb + 0.35), (x + 0.06 * (sx + 0.5), yp - 0.10, zb + 0.03)], 0.016, seg=10)
    vs += box(bl, (cx, yp - 0.06, hz + LB), (0.46, 0.035, 0.04))                                    # 칼날 셋을 묶는 검은 가로대
    vs += cyl(bl, (cx, yp - 0.07, hz + LB), (cx, yp - 0.19, hz + LB), 0.02, seg=10)                 # 검은 손잡이
    _turn(vs, R, piv)
    if old:   # 손잡이에 건 꼬리표 (끊어 놓았으니 올리지 말라는 표)
        g = R @ (Vector((cx, yp - 0.13, hz + LB)) - piv) + piv
        box(po, (cx + 0.03, g.y, g.z - 0.075), (0.07, 0.004, 0.11)); box(P["red"], (cx + 0.03, g.y - 0.003, g.z - 0.045), (0.07, 0.004, 0.03))


def _cubicle(P, rnd, cx, h, d, kind, old, open_deg, fault, body):
    """배전함 한 칸: 검은 밑 틀 + 칠한 몸통 + 윗면 들어 올리는 귀 + 문. 윗면 높이를 돌려준다"""
    W = CW - 0.02; zb = PL + 0.08; zt = zb + h; yf = YB - d; yc = (YB + yf) / 2; zc = (zb + zt) / 2
    pa = P[body]; trim = "bare" if body == "iron" else "iron"
    box(P["iron"], (cx, yc, PL + 0.04), (W, d - 0.04, 0.08))
    for sx in (-1, 1): box(P[trim], (cx + sx * 0.30, yc, zt + 0.035), (0.06, 0.014, 0.07))
    if open_deg:   # 속이 보이는 함: 판 다섯 장 + 문틀
        t = 0.02
        for sx in (-1, 1): box(pa, (cx + sx * (W - t) / 2, yc, zc), (t, d, h)); box(pa, (cx + sx * (W / 2 - 0.025), yf + t / 2, zc), (0.05, t, h))
        box(pa, (cx, YB - t / 2, zc), (W, t, h))
        for z in (zb + t / 2, zt - t / 2): box(pa, (cx, yc, z), (W, d, t))
        for z in (zb + 0.035, zt - 0.035): box(pa, (cx, yf + t / 2, z), (W, t, 0.07))
        _inside(P, cx, zb, zt, yf, old)
    else:
        box(pa, (cx, yc, zc), (W, d, h))
    _door(P, rnd, cx, zb, zt, yf, kind, old, open_deg, fault, body, trim)
    return zt


def _bushing(P, x, y, h, rs, n):
    """사기 애자: 얇은 우산 턱이 n 겹 + 꼭대기 쇠 단자 (밑과 꼭대기는 뚜껑 · 단자가 막는다)"""
    pts = [(0.0, rs * 0.7)]; step = (h - 0.05) / n
    for i in range(n): pts += [(0.035 + step * i, rs), (0.035 + step * (i + 0.8), rs * 0.5)]
    pts += [(h, rs * 0.45)]
    sweep(P[PORC], [(x, y, ZL + z) for z, _ in pts], rs, seg=10, caps=False, r_fn=lambda i: pts[i][1])
    box(P["bare"], (x, y, ZL + h + 0.014), (rs, rs, 0.032))


def _transformer(P, rnd, X0, wall_d, zrun, zg, ymain, zmain, old):
    """기름 변압기: 모래 깐 기름 받이 턱 안에 썰매 틀 · 네모 통 · 식힘 날개 · 애자 3+4 · 뉘어 놓은 기름 통 · 귀. 고압 전선은 벽의 갈림 상자에서 세 가닥으로 내려온다"""
    TX = X0 + 0.84; pa, k, cb = P["steel_paint"], P["iron"], P.soft("rubber"); HW, HD = 0.50, 0.31; yf = TY - HD; XC = X0 + TZ
    # 기름 받이: 콘크리트 턱 + 모래 (법: 기름 쓰는 전기기계 밑엔 모래)
    kx0, kx1, ky0, ky1 = X0 + 0.06, X0 + 1.62, -1.12, -0.08; c = P["concrete"]
    for y in (ky0 + 0.04, ky1 - 0.04): box(c, ((kx0 + kx1) / 2, y, 0.07), (kx1 - kx0, 0.08, 0.14))
    for x in (kx0 + 0.04, kx1 - 0.04): box(c, (x, (ky0 + ky1) / 2, 0.07), (0.08, ky1 - ky0 - 0.16, 0.14))
    box(P["cloth"], ((kx0 + kx1) / 2, (ky0 + ky1) / 2, 0.04), (kx1 - kx0 - 0.1, ky1 - ky0 - 0.1, 0.08))
    # 썰매 틀 (끌어서 들여놓는다)
    for sy in (-1, 1): box(k, (TX, TY + sy * 0.20, 0.10), (1.30, 0.10, 0.20))
    for sx in (-1, 1): box(k, (TX + sx * 0.60, TY, 0.165), (0.05, 0.50, 0.07))
    # 통 + 뚜껑 테 + 뚜껑 볼트 + 들어 올리는 귀
    box(pa, (TX, TY, (0.20 + ZL - 0.035) / 2), (2 * HW, 2 * HD, ZL - 0.235)); box(pa, (TX, TY, ZL - 0.0175), (2 * HW + 0.07, 2 * HD + 0.07, 0.035))
    for j in range(7): box(k, (TX - 0.45 + 0.15 * j, yf - 0.012, ZL + 0.006), (0.03, 0.03, 0.012))
    for sx in (-1, 1):
        for sy in (-1, 1): box(k, (TX + sx * (HW - 0.02), TY + sy * (HD - 0.07), ZL + 0.045), (0.02, 0.09, 0.09))
    # 세로 식힘 날개: 앞은 두 묶음(가운데는 이름판 자리), 양옆은 한 묶음씩
    for sx in (-1, 1):
        for j in range(5): box(pa, (TX + sx * (0.16 + 0.07 * j), yf - 0.06, 0.85), (0.012, 0.12, 1.06))
        for j in range(7): box(pa, (TX + sx * (HW + 0.06), TY - 0.24 + 0.08 * j, 0.85), (0.12, 0.012, 1.06))
    # 앞면 가운데: 기름 온도계 · 이름판 · 기름 빼는 꼭지
    cyl(k, (TX, yf, 1.27), (TX, yf - 0.04, 1.27), 0.06, seg=12); cyl(P["glass"], (TX, yf - 0.04, 1.27), (TX, yf - 0.046, 1.27), 0.046, seg=12)
    box(P["black"], (TX + 0.012, yf - 0.048, 1.28), (0.008, 0.004, 0.055), Matrix.Rotation(0.6, 3, "Y"))
    box(P["white"], (TX, yf - 0.003, 1.04), (0.17, 0.006, 0.12))
    for dz, wl in ((0.03, 0.13), (-0.02, 0.08)): box(P["black"], (TX, yf - 0.007, 1.04 + dz), (wl, 0.003, 0.012))
    cyl(k, (TX, yf, 0.36), (TX, yf - 0.11, 0.36), 0.03, seg=10); cyl(P["rust"], (TX, yf - 0.11, 0.36), (TX, yf - 0.122, 0.36), 0.065, seg=10)
    # 기름 통: 뚜껑 위 −x 쪽에 다리 둘로 올려 옆으로 뉘었다 (앞에서 누운 통으로 보인다) + 눈금 유리 + 붓는 마개 + 통으로 내려오는 관
    cxn, cyn, czn = TX - 0.29, TY + 0.15, ZL + 0.50
    cyl(pa, (cxn - 0.22, cyn, czn), (cxn + 0.22, cyn, czn), 0.14, seg=12, caps=False)
    for sx in (-1, 1):
        cyl(pa, (cxn + sx * 0.22, cyn, czn), (cxn + sx * 0.25, cyn, czn), 0.14, seg=12, r1=0.10)
        box(k, (cxn + sx * 0.15, cyn, ZL + 0.19), (0.04, 0.07, 0.38)); box(k, (cxn + sx * 0.15, cyn, ZL + 0.008), (0.10, 0.16, 0.016))
    cyl(k, (cxn - 0.10, cyn, czn + 0.13), (cxn - 0.10, cyn, czn + 0.18), 0.032, seg=10)
    box(k, (cxn + 0.08, cyn - 0.138, czn), (0.035, 0.014, 0.15)); box(P["glass"], (cxn + 0.08, cyn - 0.142, czn), (0.016, 0.014, 0.11))
    sweep(pa, [(cxn, cyn - 0.05, czn - 0.11), (cxn, TY - 0.02, ZL + 0.20), (cxn, TY - 0.02, ZL)], 0.02, seg=10, caps=False)
    box(k, (cxn, TY - 0.02, ZL + 0.10), (0.07, 0.07, 0.07))
    # 긴 애자 셋 (고압, 뒤쪽). 벽 전선 줄에서 굵은 전선 하나가 벽의 갈림 상자로 내려오고, 상자에서 가는 세 가닥이 애자 꼭대기로 간다
    ht = ZL + 0.49; bx = TX + HV[1]; zbx = min(ht + (zrun - ht) * 0.5, zrun - 0.40)
    box(k, (bx, wall_d - 0.08, zbx), (0.20, 0.20, 0.24))
    sweep(cb, _smooth([(bx - 0.42, ymain, zmain), (bx - 0.14, ymain, zmain - 0.02), (bx, wall_d - 0.08, zmain - 0.20), (bx, wall_d - 0.08, zbx + 0.10)], [1, 2, 1]), 0.026, seg=10, caps=False)
    for i, dx in enumerate(HV):
        x = TX + dx; _bushing(P, x, TY + 0.16, 0.46, 0.06, 4); sx = bx + (i - 1) * 0.06
        sweep(cb, _smooth([(sx, wall_d - 0.09, zbx - 0.10), (sx, wall_d - 0.11, zbx - 0.22), (x, TY + 0.22, ht + 0.12), (x, TY + 0.16, ht)], [1, 2, 1]), 0.013, seg=10, caps=False)
    # 짧은 애자 넷 (저압, 앞쪽) → 전선이 서로 넘어가며 휘어 첫 함 옆구리 전선 상자로 들어간다
    box(k, (XC - 0.025, -0.50, zg), (0.07, 0.38, 0.17)); xe = XC - 0.05; zs = ZL + 0.27
    for j, dx in enumerate(LV):
        x = TX + dx; ye = -0.365 - 0.09 * j; _bushing(P, x, TY - 0.17, 0.24, 0.045, 2); up = 0.04 * (3 - j)
        pts = [(x, TY - 0.17, zs), (x + 0.06, TY - 0.15, zs + 0.10 + up), ((x + xe) / 2 + 0.12, (TY - 0.17 + ye) / 2, max(zg, zs) + 0.04 + up - rnd.uniform(0.0, 0.03)), (xe, ye, zg)]
        sweep(cb, _smooth(pts, [1, 2, 2]), 0.017, seg=10, caps=False)
    if old:
        ru = P["rust"]
        box(ru, (TX, TY, 0.26), (2 * HW + 0.006, 2 * HD + 0.006, 0.12))                             # 통 밑동 녹 띠
        for sx, j, hh in ((-1, 1, 0.30), (-1, 3, 0.46), (1, 0, 0.20), (1, 4, 0.38), (1, 2, 0.14)): box(ru, (TX + sx * (0.16 + 0.07 * j), yf - 0.061, 0.32 + hh / 2), (0.016, 0.124, hh))
        box(ru, (TX + 0.20, TY - 0.02, ZL + 0.0015), (0.34, 0.20, 0.003))
        _drips(ru, rnd, TX - 0.13, yf, ZL - 0.036, 0.20, 3); _drips(ru, rnd, TX + 0.07, yf, ZL - 0.036, 0.12, 2)   # 뚜껑 테 밑으로 흐른 녹물
        _ragged(P["black"], TX - 0.04, TX + 0.05, yf, 0.34, [-0.004, -0.10, -0.14, -0.004])               # 꼭지에서 샌 기름
        box(P.soft("black"), (TX + 0.04, yf - 0.24, 0.081), (0.40, 0.28, 0.004), Matrix.Rotation(0.2, 3, "Z"))   # 모래에 밴 기름 자국


def _guard(P, mats, out, X0, X1, old, rnd):
    """허리 높이 검은 쇠 관 울타리 (양 끝은 터 있다). 판은 위아래 관 두 줄에 띠쇠 넷으로 조였다: 번개 표시 · "고압위험" · "출입금지" """
    ru, k, wh, rd = P["rust"], P["iron"], P["white"], P["red"]; gx0, gx1 = X0 + 0.25, X1 - 0.25
    n = max(2, math.ceil((gx1 - gx0) / 1.6) + 1); xs = [gx0 + (gx1 - gx0) * i / (n - 1) for i in range(n)]
    for x in xs:
        cyl(k, (x, YG, 0), (x, YG, 1.03), 0.028, seg=10); box(k, (x, YG, 0.006), (0.15, 0.15, 0.012))
        if old: cyl(ru, (x, YG, 0.012), (x, YG, rnd.uniform(0.10, 0.32)), 0.031, seg=10, caps=False)   # 기둥 밑동 녹
    for z in (1.0, 0.55): cyl(k, (gx0 - 0.06, YG, z), (gx1 + 0.06, YG, z), 0.022, seg=10)
    m = (n - 1) // 2; mid = lambda i: (xs[i] + xs[min(i + 1, n - 1)]) / 2; plates = [("고압위험", mid(m), 0.74, 0.15)]
    if n >= 3: plates.append((None, mid(0), 0.36, 0.0))
    if n >= 4: plates.append(("출입금지", mid(n - 2), 0.68, 0.135))
    zc, hh, yp = 0.775, 0.40, YG - 0.033
    for i, (body, x, w, size) in enumerate(plates):
        box(wh, (x, YG - 0.030, zc), (w, 0.006, hh))
        for sx in (-1, 1):
            for z in (1.0, 0.55): box(k, (x + sx * (w / 2 - 0.07), YG - 0.007, z), (0.035, 0.066, 0.066))   # 관을 감아 조인 띠쇠
        if old:   # 녹물 · 탄가루 때 (새 판처럼 하얗게 튀지 않게)
            _drips(ru, rnd, x - w / 2 + 0.05, yp, zc + hh / 2 - 0.01, rnd.uniform(0.12, 0.24), 2)
            if rnd.random() < 0.6: _drips(ru, rnd, x + w / 2 - 0.09, yp, zc + hh / 2 - 0.01, rnd.uniform(0.06, 0.14), 2)
            _ragged(P["black"], x - w / 2 + 0.004, x + w / 2 - 0.004, yp, zc - hh / 2 + 0.002, [rnd.uniform(0.005, 0.035) for _ in range(7)])
        if body:
            for s in (-1, 1): box(rd, (x, yp - 0.0015, zc + s * (hh / 2 - 0.035)), (w - 0.06, 0.003, 0.018))   # 빨간 테 줄
            out.append(_text("NOCOL_SUB_TEXT_%d" % i, body, (x, yp - 0.002, zc - 0.37 * size), size, mats["red"])); continue
        for (x0, z0), (x1, z1) in (((0.05, 0.16), (-0.065, -0.008)), ((-0.065, 0.016), (0.065, -0.016)), ((0.065, 0.008), (-0.045, -0.16))):   # 번개 표시 (꺾인 획 셋)
            box(rd, (x + (x0 + x1) / 2, yp - 0.0015, zc + (z0 + z1) / 2), (0.04, 0.003, math.hypot(x1 - x0, z1 - z0)), Matrix.Rotation(math.atan2(x1 - x0, z1 - z0), 3, "Y"))


def _fire_point(P, mats, out, fx, wall_d):
    """불 끄는 모래: 나무 다리 둘에 흰 판 "방화사" + 그 앞 바닥에 모래 통 둘"""
    fy = wall_d - 0.14; ru = P["rust"]
    for sx in (-1, 1): box(P["timber_old"], (fx + sx * 0.33, fy, 0.675), (0.07, 0.045, 1.35))
    box(P["white"], (fx, fy - 0.035, 1.16), (0.80, 0.025, 0.24))
    out.append(_text("NOCOL_SUB_TEXT_SAND", "방화사", (fx, fy - 0.0505, 1.16 - 0.37 * 0.14), 0.14, mats["red"]))
    for i, bx in enumerate((fx - 0.19, fx + 0.19)):
        by = fy - 0.24 - 0.05 * i
        cyl(ru, (bx, by, 0), (bx, by, 0.27), 0.11, seg=12, r1=0.15)
        cyl(P["red"], (bx, by, 0.15), (bx, by, 0.21), 0.1352, seg=12, r1=0.1441, caps=False)        # 빨간 띠 (불 끄는 통 표시)
        cyl(P["cloth"], (bx, by, 0.25), (bx, by, 0.33), 0.145, seg=12, r1=0.03)                     # 봉긋한 모래
        t = math.radians(25 if i else -20)                                                          # 들 손잡이 (녹슬어 비스듬히 선 채 굳었다)
        sweep(P.soft("iron"), [(bx - 0.15 * math.cos(a), by - 0.15 * math.sin(a) * math.sin(t), 0.262 + 0.15 * math.sin(a) * math.cos(t)) for a in (math.pi * j / 4 for j in range(5))], 0.007, seg=10, caps=False)


def build(mats, cubicles=4, wall_d=0.0, ceil_h=3.2, state="old", seed=0):
    P = _Parts(mats); rnd = random.Random(seed); old = state == "old"; n = max(1, int(cubicles)); out = []
    L = TZ + CW * n; X0, X1 = -L / 2, L / 2; XC = X0 + TZ          # XC = 함 줄이 시작하는 x
    zrun = ceil_h - 0.25; zh = zrun - 0.035; ymain, zmain = wall_d + RUN[0][0], zh + RUN[0][1]; k = P["iron"]; cb = P.soft("rubber")
    var = [(i + seed) % 4 for i in range(n)]; H = (1.70, 1.70, 1.55, 1.78); D = (0.72, 0.72, 0.66, 0.72)
    _transformer(P, rnd, X0, wall_d, zrun, min(PL + 0.08 + H[var[0]] - 0.16, ZL + 0.26), ymain, zmain, old)
    # 함 줄: 낮은 콘크리트 받침 위에 나란히 (키 · 깊이 · 칠이 조금씩 다르다 — 해마다 하나씩 들여놓은 줄. 낮은 것은 검은 칠의 옛 함)
    box(P["concrete"], ((XC + X1) / 2, -0.50, PL / 2), (CW * n + 0.10, 0.88, PL))
    opened = min(1, n - 1) if old else -1
    for i in range(n):
        cx = XC + CW * (i + 0.5); v = var[i]
        fault = None if not old else "gone" if i == n - 1 else "crack" if i == 0 else None
        zt = _cubicle(P, rnd, cx, H[v], D[v], i % 2, old, 62 if i == opened else 0, fault, "iron" if v == 2 and n >= 3 and i != opened else "steel_paint")
        # 윗면 전선 물림 → 전선이 뒤로 휘어 벽에 붙어 오르다(죔쇠 하나) 옆으로 누워 벽 전선 줄에 합쳐진다
        gx = cx + rnd.uniform(-0.12, 0.12); dy = ymain + 0.30
        cyl(k, (gx, -0.30, zt), (gx, -0.30, zt + 0.08), 0.05, seg=10)
        z1 = zt + min(0.30 + 0.6 * dy, (zrun - 0.22 - zt) * 0.7); z2 = max(z1 + 0.06, zrun - 0.22)
        pts = [(gx, -0.30, zt + 0.04), (gx, -0.30 + 0.2 * dy, zt + (z1 - zt) * 0.55), (gx, ymain, z1), (gx, ymain, z2), (gx + 0.12, ymain, zmain - 0.04), (gx + 0.36, ymain, zmain)]
        sweep(cb, _smooth(pts, [1, 2, 1, 2, 1]), 0.022, seg=10, caps=False)
        box(k, (gx, wall_d - 0.045, (z1 + z2) / 2), (0.10, 0.11, 0.035))
    # 벽 전선 줄: 갈고리(벽에 박은 쇠)에 굵은 전선 셋이 얹혀 처지며 줄 끝에서 1 m 씩 더 간다. −x 끝은 천장 상자로 올라가고 +x 끝은 벽 상자로 들어간다
    xa, xb = X0 - 1.0, X1 + 1.0; nh = max(2, round((xb - xa - 0.5) / 1.4)); hooks = [xa + 0.25 + (xb - xa - 0.5) * i / nh for i in range(nh + 1)]
    hk = P.soft("iron")   # 갈고리 · 끝 상자는 부딪힘 없이 (천장이 낮은 방에서는 머리 높이까지 내려온다)
    for hx in hooks: box(hk, (hx, wall_d - 0.085, zh - 0.015), (0.03, 0.27, 0.03)); box(hk, (hx, wall_d - 0.205, zh + 0.03), (0.03, 0.03, 0.09))
    box(hk, (xa, wall_d - 0.105, ceil_h - 0.045), (0.16, 0.25, 0.15)); box(hk, (xb + 0.09, wall_d - 0.105, zh + 0.02), (0.26, 0.25, 0.18))
    for ci, (yo, r) in enumerate(RUN):
        y = wall_d + yo; zc = zh + r; pts = [(xa, y, ceil_h - 0.06), (xa, y, zc + 0.14), (xa + 0.07, y, zc + 0.035), (hooks[0], y, zc)]
        for a, b in zip(hooks, hooks[1:]):   # 바깥 줄은 깊게, 안쪽 둘은 얕게 처진다
            s = rnd.uniform(0.08, 0.14) if ci == 2 else rnd.uniform(0.03, 0.07)
            pts += [(a + (b - a) * t, y, zc - s * 4 * t * (1 - t)) for t in ((0.25, 0.5, 0.75) if ci == 2 else (0.5,))] + [(b, y, zc)]
        sweep(cb, pts + [(xb, y, zc)], r, seg=10, caps=False)
    # 벽 전등 (꺼져 있다): 벽 상자 + 갓 + 유리 알 + 쇠 살 바구니. 함 사이 경계 위, 전선 줄 바로 밑
    lx, ly, lz = XC + CW * (n // 2), wall_d - 0.19, zrun - 0.28
    box(k, (lx, wall_d - 0.06, lz), (0.12, 0.16, 0.12)); cyl(k, (lx, ly, lz + 0.03), (lx, ly, lz - 0.04), 0.062, seg=10)
    cyl(P["glass"], (lx, ly, lz - 0.04), (lx, ly, lz - 0.18), 0.05, seg=10, r1=0.034)
    for a in range(4): box(k, (lx + 0.058 * math.cos(a * math.pi / 2), ly + 0.058 * math.sin(a * math.pi / 2), lz - 0.115), (0.008, 0.008, 0.16))
    box(k, (lx, ly, lz - 0.195), (0.125, 0.008, 0.008)); box(k, (lx, ly, lz - 0.195), (0.008, 0.125, 0.008))
    sweep(cb, [(lx, wall_d - 0.05, lz + 0.05), (lx + 0.03, ymain, zmain)], 0.012, seg=10, caps=False)
    _guard(P, mats, out, X0, X1, old, rnd)
    _fire_point(P, mats, out, X1 + 0.50, wall_d)
    # 함 앞 바닥 고무 깔판 두 장 (감전 막이). old 면 한 장이 비뚤게 밀려 있다
    mw = CW * n
    box(cb, (XC + mw * 0.25 + 0.01, -1.27, 0.006), (mw * 0.5 - 0.03, 0.62, 0.012))
    box(cb, (XC + mw * 0.75, -1.26, 0.006), (mw * 0.5 - 0.04, 0.60, 0.012), Matrix.Rotation(math.radians(3.5 if old else 0.0), 3, "Z"))
    return P.finish() + out
