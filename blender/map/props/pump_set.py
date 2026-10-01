"""배수 펌프장 (갱 맨 아래 물 퍼 올리는 자리). 조사 R1_pump_fan props[0] 공통 구조를 따른다:
  받침 콘크리트 하나 위에 굵은 통 둘이 한 줄 — 냉각 날개 달린 전동기 + 고리를 겹쳐 긴 볼트로 조인 다단 펌프(D형),
  펌프에서 곧게 위로 솟는 굵은 플랜지 관 + 역지 밸브 + 손잡이 바퀴 밸브 → 벽을 타고 천장 속으로,
  옆으로 나온 빨아들이는 관이 물웅덩이로 내려가고, 벽에는 기동기 함과 전동기로 가는 굵은 전선.
build(): 원점 = 펌프 받침 가운데 바닥. 긴 쪽 = X (전동기 +X, 펌프 −X). 벽 = y = +wall_d. 보는 쪽 = −y.
sump_cover(): 원점 = 웅덩이 입 가운데 바닥 높이. 판자는 y 쪽으로 걸친다.
"""
import math
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, tube, torus, sweep, obj, text_mesh, place

AZ = 0.82          # 축 높이 (받침 0.45 + 바닥 틀 0.12 + 축 0.25)
SX = 1.9           # 빨아들이는 관이 아래로 꺾이는 자리 x = −SX
SY = -0.50         #   그 자리의 y
STANDBY_X = 3.0    # 빈 예비 받침 가운데 x
PAINT = ("steel_paint", "steel_blue", "steel_red", "steel_yellow", "red")


class _Parts:
    """재질 이름마다 그물 하나. 버려진 상태면 칠 재질을 모두 녹으로 바꾼다"""
    def __init__(s, mats, rusty): s.mats, s.rusty, s.bm = mats, rusty, {}
    def __getitem__(s, k):
        if s.rusty and k in PAINT: k = "rust"
        if k not in s.bm: s.bm[k] = bmesh.new()
        return s.bm[k]
    def finish(s, prefix):
        out = []
        for k, bm in s.bm.items():
            o = obj("%s_%s" % (prefix, k), bm, s.mats[k], smooth=True)
            try: o.data.set_sharp_from_angle(angle=math.radians(40))   # 둥근 옆면만 부드럽게, 뚜껑 · 상자 모서리는 날카롭게
            except Exception: pass
            out.append(o)
        return out


def _fillet(pts, rb=0.13, n=3):
    """꺾이는 점을 둥근 굽은 관(엘보)으로 바꾼 가운데 선"""
    pts = [Vector(p) for p in pts]; out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        u, v = (a - b).normalized(), (c - b).normalized(); ang = u.angle(v)
        cen = b + (u + v).normalized() * (rb / math.sin(ang / 2)); t = rb / math.tan(ang / 2)
        w0, w1 = b + u * t - cen, b + v * t - cen
        out += [cen + w0.slerp(w1, i / n).normalized() * rb for i in range(n + 1)]
    return out + [pts[-1]]


def _joint(P, key, c, axis, rp, bolts=6):
    """플랜지 이음: 원판 두 장 + 둘레 볼트 (관 반지름 rp)"""
    c, a = Vector(c), Vector(axis).normalized(); R = a.to_track_quat("Z", "Y").to_matrix()
    cyl(P[key], c - a * 0.030, c - a * 0.004, rp + 0.055, 12); cyl(P[key], c + a * 0.004, c + a * 0.030, rp + 0.055, 12)
    for i in range(bolts):
        t = 2 * math.pi * (i + 0.5) / bolts
        box(P["iron"], c + R @ Vector(((rp + 0.032) * math.cos(t), (rp + 0.032) * math.sin(t), 0)), (0.024, 0.024, 0.09), R)


def _plinth(P, x, tide):
    """콘크리트 받침 2.2 x 0.8 x 0.45 (물에 잠겨도 전동기가 살게 높인 자리)"""
    bm = P["concrete"]
    for c, s_ in (((x, 0, 0.225), (2.2, 0.8, 0.45)), ((x, 0, 0.04), (2.32, 0.92, 0.08))):   # 몸 + 아래 턱, 모서리는 닳아 둥글다
        vs = box(bm, c, s_); bmesh.ops.bevel(bm, geom=list({e for v in vs for e in v.link_edges}), offset=0.03, segments=1, affect="EDGES")
    for i, (dx, w, h) in enumerate(((-0.80, 0.07, 0.30), (-0.62, 0.03, 0.22), (-0.12, 0.10, 0.36), (0.02, 0.04, 0.17), (0.71, 0.05, 0.26))):   # 앞면에 흘러내린 녹물 · 기름 줄 (패킹에서 새는 물)
        box(P["ochre" if i != 4 else "tar"], (x + dx, -0.401, 0.42 - h / 2), (w, 0.006, h))
    if tide: box(P["ochre"], (x, 0, 0.175), (2.34, 0.94, 0.35))                  # 갱내수 누런 띠 (0.35 m 까지)


def _motor(P):
    """전동기: 세로 날개 두른 통 + 뒤 바람개비 덮개 + 위 단자함 + 발 + 들고리"""
    m = P["steel_paint"]
    cyl(m, (0.22, 0, AZ), (0.92, 0, AZ), 0.20, 14)
    cyl(m, (0.14, 0, AZ), (0.22, 0, AZ), 0.11, 14, r1=0.20)                      # 축 쪽 끝 뚜껑
    cyl(m, (0.92, 0, AZ), (1.05, 0, AZ), 0.215, 14)                              # 바람개비 덮개
    cyl(P["iron"], (1.05, 0, AZ), (1.058, 0, AZ), 0.15, 12)                      # 덮개 숨구멍 판
    for i in range(16):                                                          # 냉각 날개
        R = Matrix.Rotation(2 * math.pi * (i + 0.5) / 16, 3, "X")
        box(m, Vector((0.57, 0, AZ)) + R @ Vector((0, 0, 0.21)), (0.64, 0.022, 0.05), R)
    for x in (0.32, 0.82): box(m, (x, 0, 0.615), (0.10, 0.46, 0.09))             # 발
    for x in (0.32, 0.82):
        for y in (-0.20, 0.20): box(P["iron"], (x, y, 0.672), (0.04, 0.04, 0.025))  # 발 볼트
    box(m, (0.50, 0.0, AZ + 0.265), (0.22, 0.20, 0.13))                          # 단자함
    box(P["iron"], (0.50, 0.0, AZ + 0.335), (0.24, 0.22, 0.012))                 #   뚜껑
    cyl(P["iron"], (0.50, 0.10, AZ + 0.26), (0.50, 0.15, AZ + 0.26), 0.03, 8)    #   전선 들어가는 목
    torus(P["iron"], (0.80, 0, AZ + 0.255), (0, 1, 0), 0.035, 0.012, 10, 5)      # 들고리
    box(P["white"], (0.62, -0.224, AZ + 0.03), (0.16, 0.012, 0.09), Matrix.Rotation(math.radians(8), 3, "X"))  # 명판
    cyl(P["bare"], (-0.02, 0, AZ), (0.14, 0, AZ), 0.03, 8)                       # 축
    cyl(P["steel_yellow"], (-0.03, 0, AZ), (0.15, 0, AZ), 0.13, 12)              # 축 이음 덮개 (둥근 지붕 + 치마)
    box(P["steel_yellow"], (0.06, 0, 0.695), (0.18, 0.26, 0.25))


def _pump(P):
    """다단 펌프(D형): 양 끝 주물 사이에 단 고리 5개 + 긴 조임 볼트 8개 + 양 끝 베어링 통 + 위로 넘어가는 균형 관"""
    m = P["steel_blue"]
    cyl(m, (-0.16, 0, AZ), (-0.775, 0, AZ), 0.145, 14)                           # 속 몸
    cyl(m, (-0.16, 0, AZ), (-0.28, 0, AZ), 0.205, 14)                            # 내보내는 쪽 끝 주물
    cyl(m, (-0.655, 0, AZ), (-0.775, 0, AZ), 0.205, 14)                          # 빨아들이는 쪽 끝 주물
    for i in range(5): cyl(m, (-0.288 - i * 0.075, 0, AZ), (-0.348 - i * 0.075, 0, AZ), 0.168, 14)   # 단 고리
    for x in (-0.22, -0.715): box(m, (x, 0, 0.64), (0.11, 0.40, 0.14))           # 주물 발
    for x in (-0.22, -0.715):
        for y in (-0.17, 0.17): box(P["iron"], (x, y, 0.722), (0.04, 0.04, 0.025))
    for i in range(8):                                                           # 조임 볼트 + 양 끝 너트
        t = 2 * math.pi * (i + 0.5) / 8; y, z = 0.186 * math.cos(t), AZ + 0.186 * math.sin(t)
        cyl(P["bare"], (-0.135, y, z), (-0.80, y, z), 0.012, 6)
        for x in (-0.145, -0.79): box(P["iron"], (x, y, z), (0.03, 0.036, 0.036), Matrix.Rotation(t, 3, "X"))
    cyl(m, (-0.02, 0, AZ), (-0.16, 0, AZ), 0.08, 10); box(m, (-0.09, 0, 0.66), (0.10, 0.12, 0.18))     # 베어링 통 (축 쪽)
    cyl(m, (-0.775, 0, AZ), (-0.93, 0, AZ), 0.08, 10); box(m, (-0.86, 0, 0.66), (0.10, 0.12, 0.18))    # 베어링 통 (바깥쪽)
    cyl(P["red"], (-0.93, 0, AZ), (-0.955, 0, AZ), 0.085, 10)                    # 축 끝 뚜껑 (사진마다 빨강)
    for x in (-0.09, -0.86): cyl(P["bare"], (x, 0, AZ + 0.075), (x, 0, AZ + 0.13), 0.018, 6)           # 기름 컵
    sweep(P["iron"], _fillet([(-0.19, 0.10, AZ + 0.17), (-0.19, 0.10, AZ + 0.30), (-0.74, 0.10, AZ + 0.30), (-0.74, 0.10, AZ + 0.17)], 0.06, 2), 0.016, 6)  # 균형 관
    cyl(P["iron"], (-0.715, -0.06, AZ + 0.19), (-0.715, -0.06, AZ + 0.36), 0.012, 6)                   # 압력계 대
    cyl(P["iron"], (-0.715, -0.04, AZ + 0.41), (-0.715, -0.08, AZ + 0.41), 0.06, 12)                   # 압력계
    cyl(P["glass"], (-0.715, -0.08, AZ + 0.41), (-0.715, -0.084, AZ + 0.41), 0.05, 12)


def _baseplate(P):
    """한 틀(ㄷ 형강)에 둘을 올리고 받침에 앵커 볼트로 문다"""
    for y in (-0.235, 0.235): box(P["iron"], (-0.01, y, 0.51), (1.92, 0.08, 0.12))
    for x in (-0.93, -0.45, 0.06, 0.57, 0.91): box(P["iron"], (x, 0, 0.51), (0.08, 0.47, 0.11))
    for x in (-0.86, 0.84):
        for y in (-0.32, 0.32):
            box(P["iron"], (x, y, 0.46), (0.12, 0.12, 0.02))                     # 귀
            cyl(P["rust"], (x, y, 0.45), (x, y, 0.53), 0.016, 6); box(P["rust"], (x, y, 0.485), (0.045, 0.045, 0.03))


def _valves(P):
    """내보내는 관 아래 토막: 펌프 위 목 → 역지 밸브(옆 뚜껑) → 손잡이 바퀴 밸브(바퀴가 −y 로 본다). 꼭대기 z = 1.68"""
    m = P["steel_red"]; dx = -0.22
    cyl(m, (dx, 0, AZ + 0.19), (dx, 0, 1.10), 0.075, 12); _joint(P, "steel_red", (dx, 0, 1.10), (0, 0, 1), 0.075)
    cyl(m, (dx, 0, 1.10), (dx, 0, 1.38), 0.105, 12)                              # 역지 밸브 몸
    cyl(m, (dx, -0.08, 1.27), (dx, -0.16, 1.27), 0.075, 10); cyl(m, (dx, -0.16, 1.27), (dx, -0.18, 1.27), 0.095, 10)   # 옆 뚜껑
    for i in range(4): t = math.pi / 4 + i * math.pi / 2; box(P["iron"], (dx + 0.07 * math.cos(t), -0.185, 1.27 + 0.07 * math.sin(t)), (0.026, 0.02, 0.026))
    _joint(P, "steel_red", (dx, 0, 1.38), (0, 0, 1), 0.075)
    cyl(m, (dx, 0, 1.38), (dx, 0, 1.68), 0.095, 12)                              # 게이트 밸브 몸
    box(m, (dx, -0.13, 1.53), (0.17, 0.18, 0.20))                                #   목
    box(m, (dx, -0.225, 1.53), (0.25, 0.03, 0.27))                               #   뚜껑 플랜지
    for sx in (-1, 1):
        for sz in (-1, 1): box(P["iron"], (dx + sx * 0.10, -0.245, 1.53 + sz * 0.11), (0.028, 0.02, 0.028))
    cyl(m, (dx, -0.24, 1.53), (dx, -0.31, 1.53), 0.06, 10, r1=0.035)
    for sx in (-1, 1): box(m, (dx + sx * 0.05, -0.36, 1.53), (0.024, 0.16, 0.034))   # 멍에
    box(m, (dx, -0.44, 1.53), (0.13, 0.026, 0.05))
    cyl(P["bare"], (dx, -0.30, 1.53), (dx, -0.50, 1.53), 0.014, 6)               # 나사 축
    w = P["red"]; torus(w, (dx, -0.475, 1.53), (0, 1, 0), 0.155, 0.017, 24, 8)   # 손잡이 바퀴 (지름 0.34, 살 5개)
    cyl(w, (dx, -0.455, 1.53), (dx, -0.495, 1.53), 0.032, 8)
    for i in range(5):
        R = Matrix.Rotation(2 * math.pi * i / 5 + 0.3, 3, "Y"); box(w, Vector((dx, -0.475, 1.53)) + R @ Vector((0.08, 0, 0)), (0.15, 0.02, 0.024), R)
    _joint(P, "steel_red", (dx, 0, 1.68), (0, 0, 1), 0.075)
    return dx


def _bracket(P, x, y, z, wall_d):
    """벽 받침쇠: 벽에 박은 ㄱ 쇠 + 관을 감은 U 볼트"""
    box(P["iron"], (x, (y + wall_d) / 2, z - 0.03), (0.30, wall_d - y + 0.02, 0.05))
    box(P["iron"], (x, wall_d - 0.012, z - 0.09), (0.30, 0.024, 0.17))
    torus(P["iron"], (x, y, z + 0.012), (0, 0, 1), 0.088, 0.013, 12, 5)
    for sx in (-0.12, 0.12): box(P["bare"], (x + sx, wall_d - 0.03, z - 0.13), (0.035, 0.02, 0.035))


def _discharge(P, dx, wall_d, ceil_h, broken):
    """밸브 위 → 머리 위(관 아래 2.3 m 넘게)에서 벽으로 → 벽을 타고 천장 속으로. broken: 가운데 토막이 빠져 바닥에 누워 있다"""
    m = P["steel_red"]; r = 0.075; hz = min(2.45, ceil_h - 0.45); wy = wall_d - 0.13
    path = _fillet([(dx, 0, 1.68), (dx, 0, hz), (dx, wy, hz), (dx, wy, ceil_h + 0.25)], 0.14, 3)
    if not broken:
        sweep(m, path, r, 10)
        _joint(P, "steel_red", (dx, 0, 2.12), (0, 0, 1), r); _joint(P, "steel_red", (dx, wy * 0.5, hz), (0, 1, 0), r)
    else:
        tube(m, (dx, wy - 0.42, hz), (dx, wy - 0.14, hz), r, r - 0.012, 10)      # 벽 쪽에 남은 토막 (끝이 트여 있다)
        _joint(P, "steel_red", (dx, wy - 0.40, hz), (0, 1, 0), r)
        sweep(m, _fillet([(dx, wy - 0.15, hz), (dx, wy, hz), (dx, wy, ceil_h + 0.25)], 0.14, 3), r, 10)
        tube(m, (dx, 0, 1.68), (dx, 0, 1.80), r, r - 0.012, 10)                  # 밸브 위에 남은 짧은 목 (트인 입)
        a, b = Vector((-0.55, -0.92, 0.135)), Vector((0.95, -0.74, 0.135))       # 바닥에 누운 한 토막 (플랜지로 바닥에 닿는다)
        tube(P["ochre"], a, b, r, r - 0.012, 12); d = (b - a).normalized()
        _joint(P, "ochre", a + d * 0.03, d, r); _joint(P, "ochre", b - d * 0.03, d, r)
    _joint(P, "steel_red", (dx, wy, hz + 0.32), (0, 0, 1), r)
    _bracket(P, dx, wy, hz + 0.62, wall_d)
    if ceil_h - hz > 1.0: _bracket(P, dx, wy, ceil_h - 0.14, wall_d)


def _suction(P, tide):
    """빨아들이는 관: 끝 주물 옆 플랜지(−y) → 굽은 관 → −X 로 → x = −SX 에서 아래로 꺾여 웅덩이 속으로. 가운데는 쇠 다리로 받친다"""
    m = P["steel_red"]; r = 0.07; x0 = -0.715
    cyl(m, (x0, -0.15, AZ), (x0, -0.30, AZ), r, 10); _joint(P, "steel_red", (x0, -0.30, AZ), (0, 1, 0), r)
    sweep(m, _fillet([(x0, -0.30, AZ), (x0, SY, AZ), (-SX, SY, AZ), (-SX, SY, -0.35)], 0.13, 3), r, 10)
    _joint(P, "steel_red", (-1.02, SY, AZ), (1, 0, 0), r); _joint(P, "steel_red", (-SX, SY, 0.50), (0, 0, 1), r)
    px = -1.265                                                                  # 관 받침: 콘크리트 기둥(받침과 웅덩이 턱 사이) + 쇠 안장 + U 볼트
    vs = box(P["concrete"], (px, SY, 0.33), (0.18, 0.32, 0.66)); bmesh.ops.bevel(P["concrete"], geom=list({e for v in vs for e in v.link_edges}), offset=0.025, segments=1, affect="EDGES")
    box(P["iron"], (px, SY, 0.675), (0.20, 0.30, 0.03))
    for sy in (-0.085, 0.085): box(P["iron"], (px, SY + sy, 0.72), (0.06, 0.03, 0.08))
    torus(P["iron"], (px, SY, AZ), (1, 0, 0), r + 0.014, 0.014, 12, 5)
    box(P["ochre"], (px - 0.02, SY - 0.161, 0.40), (0.05, 0.006, 0.50))          # 기둥에 흐른 녹물
    if tide:
        cyl(P["ochre"], (-SX, SY, 0.0), (-SX, SY, 0.35), r + 0.008, 10)
        box(P["ochre"], (-1.265, SY, 0.175), (0.20, 0.34, 0.35))


def _starter(P, mats, wall_d, hang_open):
    """기동기 함 (0.6 x 0.8 x 0.25, 벽에 띠쇠로) + 옆 손잡이 + 전류계 + 전동기로 가는 굵은 전선. 위에 흰 이름판"""
    bx, y1, zc = 1.5, wall_d - 0.03, 1.40; y0 = y1 - 0.25; yc = (y0 + y1) / 2; m = P["steel_paint"]
    for z in (zc - 0.30, zc + 0.30):                                             # 벽 띠쇠 + 볼트
        box(P["iron"], (bx, wall_d - 0.015, z), (0.80, 0.03, 0.06))
        for sx in (-0.36, 0.36): box(P["bare"], (bx + sx, wall_d - 0.035, z), (0.035, 0.02, 0.035))
    box(m, (bx, y1 - 0.01, zc), (0.60, 0.02, 0.80))                              # 함: 뒤 · 위 · 아래 · 양 옆 판
    for z in (zc - 0.39, zc + 0.39): box(m, (bx, yc, z), (0.60, 0.25, 0.02))
    for sx in (-0.29, 0.29): box(m, (bx + sx, yc, zc), (0.02, 0.25, 0.80))
    box(P["black"], (bx, y1 - 0.04, zc), (0.54, 0.02, 0.74))                     # 속 판
    for i in range(3): box(P["bare"], (bx - 0.15 + i * 0.15, y1 - 0.08, zc + 0.12), (0.09, 0.08, 0.16))   # 접촉기 덩이
    box(P["iron"], (bx, y1 - 0.08, zc - 0.18), (0.36, 0.08, 0.14))
    cyl(P["iron"], (bx + 0.30, yc, zc + 0.10), (bx + 0.345, yc, zc + 0.10), 0.05, 10)                     # 옆 돌림 손잡이
    box(P["black"], (bx + 0.36, yc, zc + 0.17), (0.03, 0.04, 0.24), Matrix.Rotation(math.radians(25 if hang_open else -20), 3, "X"))
    hinge = Vector((bx - 0.30, y0 - 0.012, zc))                                  # 문 (경첩 = 왼쪽)
    R = Matrix.Rotation(math.radians(-118), 3, "Z") @ Matrix.Rotation(math.radians(7), 3, "Y") if hang_open else Matrix.Identity(3)
    box(m, hinge + R @ Vector((0.30, 0, 0)), (0.62, 0.024, 0.82), R)
    box(P["iron"], hinge + R @ Vector((0.55, -0.025, 0)), (0.03, 0.03, 0.14), R)                          #   걸쇠
    cyl(P["iron"], hinge + R @ Vector((0.30, -0.012, 0.20)), hinge + R @ Vector((0.30, -0.03, 0.20)), 0.065, 12)   #   전류계
    cyl(P["glass"], hinge + R @ Vector((0.30, -0.03, 0.20)), hinge + R @ Vector((0.30, -0.034, 0.20)), 0.052, 12)
    for z in (-0.28, 0.28): cyl(P["iron"], hinge + Vector((0, -0.005, z - 0.05)), hinge + Vector((0, -0.005, z + 0.05)), 0.014, 6)   #   경첩
    tl = math.radians(-4.5); RS = Matrix.Rotation(tl, 3, "Y"); sc_ = Vector((bx, wall_d - 0.008, 2.02))   # 이름판 (벽) — 한쪽 못이 빠져 기울었다
    box(P["white"], sc_, (0.62, 0.016, 0.18), RS)
    box(P["iron"], sc_ + RS @ Vector((-0.28, -0.012, 0.05)), (0.025, 0.012, 0.025), RS)
    box(P["rust"], (bx + 0.29, wall_d - 0.012, 2.065), (0.025, 0.024, 0.025))    #   빠진 못은 벽에 남았다
    box(P["ochre"], sc_ + RS @ Vector((-0.28, -0.0095, -0.03)), (0.03, 0.004, 0.11), RS)   #   못에서 흐른 녹물
    txt = text_mesh("NOCOL_PUMP_SIGN_TEXT", "배수펌프 1호", sc_ + RS @ Vector((0, -0.0105, -0.045)), 0.10, mats["red"], rot=(math.radians(90), tl, 0))
    # 전선 (갑옷 케이블, 지름 4 cm): 함 아래 → 벽 고정쇠 → 바닥에 늘어져 → 받침을 타고 전동기 단자함으로
    cyl(P["iron"], (bx - 0.12, yc, zc - 0.40), (bx - 0.12, yc, zc - 0.45), 0.032, 8)
    pts = [(bx - 0.12, yc, 0.97), (bx - 0.12, yc + 0.02, 0.80), (bx - 0.13, wall_d - 0.035, 0.62), (bx - 0.18, wall_d - 0.035, 0.34), (bx - 0.28, wall_d - 0.08, 0.10),
           (bx - 0.42, wall_d - 0.26, 0.022), (bx - 0.62, 0.72, 0.022), (bx - 0.80, 0.52, 0.03), (0.60, 0.425, 0.20), (0.54, 0.42, 0.46), (0.51, 0.34, 0.60), (0.50, 0.24, 0.84), (0.50, 0.18, AZ + 0.25), (0.50, 0.14, AZ + 0.26)]
    cb = bmesh.new(); sweep(cb, pts, 0.02, 6); cable = obj("NOCOL_PUMP_CABLE", cb, mats["rubber"], smooth=True)
    box(P["iron"], (bx - 0.15, wall_d - 0.02, 0.50), (0.10, 0.04, 0.035))        # 전선 벽 고정쇠
    return [txt, cable]


def _standby(P, mats, tide, wall_d, ceil_h):
    """빈 예비 받침: 펌프와 전동기를 떼어 간 자리 — 녹슨 빈 바닥 틀(ㄷ 형강)이 앵커 볼트에 그대로 물려 있고,
    벽에는 막음 플랜지로 막은 내보내는 관 토막, 받침 위에는 잘린 전선 끝"""
    x = STANDBY_X; _plinth(P, x, tide); r = 0.075
    for y in (-0.235, 0.235): box(P["rust"], (x - 0.01, y, 0.51), (1.92, 0.08, 0.12))          # 빈 바닥 틀
    for sx in (-0.93, -0.45, 0.06, 0.57, 0.91): box(P["rust"], (x + sx, 0, 0.50), (0.08, 0.47, 0.09))
    for sx in (0.32, 0.82, -0.22, -0.715):                                                     # 기계 발 볼트만 남았다
        for sy in (-0.235, 0.235): cyl(P["bare"], (x + sx, sy, 0.57), (x + sx, sy, 0.62), 0.014, 6)
    for sx in (-0.86, 0.84):
        for sy in (-0.32, 0.32):
            box(P["rust"], (x + sx, sy, 0.46), (0.12, 0.12, 0.02)); cyl(P["rust"], (x + sx, sy, 0.45), (x + sx, sy, 0.55), 0.018, 6); box(P["rust"], (x + sx, sy, 0.49), (0.05, 0.05, 0.035))
    wy = wall_d - 0.13; sx_ = x - 0.22; zb = 1.78                                              # 벽 관 토막: 천장 속 → 1.78 m 에서 막음 플랜지
    cyl(P["steel_red"], (sx_, wy, zb), (sx_, wy, ceil_h + 0.25), r, 10)
    cyl(P["steel_red"], (sx_, wy, zb), (sx_, wy, zb + 0.026), r + 0.055, 12); cyl(P["rust"], (sx_, wy, zb - 0.03), (sx_, wy, zb - 0.004), r + 0.055, 12)
    for i in range(6):
        t = math.pi * (i + 0.5) / 3; box(P["iron"], (sx_ + (r + 0.032) * math.cos(t), wy + (r + 0.032) * math.sin(t), zb), (0.024, 0.024, 0.09))
    _bracket(P, sx_, wy, zb + 0.45, wall_d)
    if ceil_h - zb > 1.5: _bracket(P, sx_, wy, ceil_h - 0.14, wall_d)
    y1 = wall_d - 0.035                                                                        # 잘린 전선: 벽 고정쇠 → 바닥 → 받침 위에서 끝
    pts = [(x + 0.62, y1, 1.30), (x + 0.61, y1, 0.80), (x + 0.58, y1, 0.30), (x + 0.55, y1 - 0.06, 0.06), (x + 0.52, y1 - 0.25, 0.022), (x + 0.50, 0.62, 0.022),
           (x + 0.49, 0.49, 0.06), (x + 0.49, 0.425, 0.30), (x + 0.48, 0.42, 0.46), (x + 0.46, 0.33, 0.60), (x + 0.42, 0.20, 0.595), (x + 0.33, 0.06, 0.595), (x + 0.22, 0.02, 0.60)]
    cb = bmesh.new(); sweep(cb, pts, 0.02, 6)
    for z in (1.28, 0.62): box(P["iron"], (x + 0.61, wall_d - 0.02, z), (0.10, 0.04, 0.035))
    for k in range(3): cyl(P["bare"], pts[-1], Vector(pts[-1]) + Vector((-0.07, 0.025 * (k - 1), 0.012 * k)), 0.006, 5)   # 드러난 심선 세 가닥
    return [obj("NOCOL_PUMP_CABLE_CUT", cb, mats["rubber"], smooth=True)]


def _clutter(P):
    """쓰던 흔적: 받침 모서리의 기름통 + 걸레"""
    cyl(P["bare"], (1.02, -0.27, 0.45), (1.02, -0.27, 0.57), 0.045, 10); cyl(P["bare"], (1.02, -0.27, 0.57), (1.02, -0.27, 0.61), 0.045, 10, r1=0.012)
    cyl(P["bare"], (1.02, -0.27, 0.60), (0.95, -0.33, 0.68), 0.008, 5)                          # 기름통 주둥이
    box(P["cloth"], (-1.02, -0.30, 0.462), (0.20, 0.14, 0.025), Matrix.Rotation(0.5, 3, "Z"))    # 걸레 (받침 모서리에 걸쳐 늘어짐)
    box(P["cloth"], (-1.04, -0.403, 0.39), (0.13, 0.012, 0.13), Matrix.Rotation(0.12, 3, "Y"))


def build(mats, state="working", wall_d=1.2, ceil_h=3.6, standby=True):
    ab = state == "abandoned"; P = _Parts(mats, ab)
    _plinth(P, 0, ab); _baseplate(P); _motor(P); _pump(P)
    dx = _valves(P); _discharge(P, dx, wall_d, ceil_h, ab); _suction(P, ab)
    extra = _starter(P, mats, wall_d, ab); _clutter(P)
    if standby: extra += _standby(P, mats, ab, wall_d, ceil_h)
    return P.finish("PUMP") + extra


def station(mats, state="working", wall_d=1.2, ceil_h=3.6, standby=True, sump_w=2.0, sump_d=1.5):
    """build() + sump_cover() 를 맞는 자리에 함께 (빨아들이는 관이 판자 빠진 틈 7번으로 내려간다).
    웅덩이 가운데 = build 자리표 (-SX - sump_w * (7.5 / 9 - 0.5), SY) — 맵은 이 자리에 웅덩이를 판다"""
    cx = -SX - sump_w * (7.5 / 9 - 0.5)
    return build(mats, state, wall_d, ceil_h, standby) + place(sump_cover(mats, sump_w, sump_d), Matrix.Translation((cx, SY, 0)))


def sump_cover(mats, w=2.0, d=1.5):
    """물웅덩이 입: 콘크리트 턱(높이 0.12) + 타르 판자 9장 자리 중 2장 빠짐(틈 0.25 m) + 한 장은 비스듬히 빠져 있음 + 검은 물(z = −0.15)"""
    P = _Parts(mats, False); k = 0.20; h = 0.12
    for sy in (-1, 1): box(P["concrete"], (0, sy * (d + k) / 2, h / 2), (w + 2 * k, k, h))
    for sx in (-1, 1): box(P["concrete"], (sx * (w + k) / 2, 0, h / 2), (k, d, h))
    n = 9; p = w / n; L = d + 2 * k - 0.06
    for i in range(n):
        if i in (3, 7): continue                                                 # 빠진 자리 (7 = 빨아들이는 관이 내려가는 틈)
        j = ((i * 37) % 7 - 3) / 3.0                                             # 판자마다 조금씩 어긋남
        box(P["tar"], (-w / 2 + p * (i + 0.5) + 0.004 * j, 0.03 * j, h + 0.025), (p - 0.022, L - 0.05 * abs(j), 0.05), Matrix.Rotation(math.radians(1.2 * j), 3, "Z"))
    x3 = -w / 2 + p * 3.5                                                        # 빠진 판자: 한 끝은 턱에 걸리고 한 끝은 물속
    a, b = Vector((x3 + 0.02, d / 2 + 0.06, h + 0.03)), Vector((x3 - 0.03, d / 2 - 1.25, -0.42))
    R = (b - a).to_track_quat("Y", "Z").to_matrix() @ Matrix.Rotation(math.radians(14), 3, "Y")
    box(P["tar"], (a + b) / 2, (p - 0.022, (b - a).length, 0.05), R)
    for sy in (-1, 1):                                                           # 판자 누르는 띠쇠 (양 턱 위)
        box(P["rust"], (-w / 2 + p * 1.5, sy * (d / 2 + k * 0.55), h + 0.056), (p * 3 - 0.04, 0.05, 0.012))
    wb = bmesh.new(); box(wb, (0, 0, -0.16), (w, d, 0.02))
    return P.finish("SUMP") + [obj("NOCOL_SUMP_WATER", wb, mats["water"])]
