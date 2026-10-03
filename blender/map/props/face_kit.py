"""막장 소품 모음 (10-03 71차 "막장(z2 · N2)에 착암기 · 발파 구멍 · 압축공기 관과 호스 · 분필"). 맵에 놓는 일은 scene_mock.py 가 한다.
레퍼런스 공통점 — 공기다리 착암기(잭레그) 사진 여러 장: 가로로 누운 쇠 원통 몸통 0.6~0.7 m(지름 약 0.11) · 뒤에 T 자 손잡이와 공기 밸브 손잡이 · 앞에 물림쇠,
  몸통 앞으로 1.2~2 m 육각 정(지름 2.5 cm, 끝에 날)이 막장 구멍에 꽂힌다 · 몸통 앞쪽 밑에서 뒤아래로 비스듬히(바닥과 40~60°) 늘어나는 공기다리(굵은 바깥 관 7 cm + 가는 속 관 + 뾰족한 발)
  · 몸통 뒤에서 굵은 검은 공기 호스(4 cm)와 가는 물 호스(2 cm)가 나와 바닥을 따라 관의 밸브로 간다 · 몸통 높이 1.0~1.4 m · 칠이 벗겨진 쇠색.
  — 한국 탄광 막장(지역N문화 coalmine/story/3683 사진 둘 · 수기 "에어 틀고 물 뿌려" + 조사/01:26 · 11:23 · 12:26 · 12:63 · 12:68): 바닥에 검은 고무 호스가 막장까지 늘어지고
  벽을 따라 관 두 줄(압축공기 · 물) · 굴진 막장 면에 지름 3~5 cm 발파 구멍 20~25 (가운데 몰린 구멍 + 둘레 + 바닥 줄) · 분필 X · 숫자.
함수마다 원점 · 방향은 그 함수 머리 글에. 재질은 PM["이름"] 으로만 (_util.MAT_KEYS 의 steel_paint · iron · bare · rust · rubber · concrete · chalk). 이름이 NOCOL_ 로 시작하면 부딪힘 없음.
미리보기 + 스스로 검사:  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/map/props/face_kit.py -- <나갈 폴더>
  → <폴더>/face_kit_set.png (막장에 함께 놓은 모습, 머리등만) · face_kit_jackleg.png (서 있는 착암기, 밝게) · face_kit_close.png (눕힌 착암기 · 구멍 · 분필, 밝게) + 로그 FACEKIT (소품마다 삼각형 수)"""
import math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); HERE in sys.path or sys.path.insert(0, HERE)
import bpy, bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, torus, sweep, obj, text_mesh
from pump_set import _Parts, _fillet

BODY_H = 1.2                      # 착암기 몸통 축 = 정 높이 (바닥 위)
ROD_IN = 0.25                     # 정이 바위 속으로 들어간 길이 (막장 면이 울퉁불퉁해도 꽂혀 보이게)
PIN = Vector((0.2, 0, -0.10))     # 공기다리 핀 (착암기 자리표: 코 = 원점, 축 = +x 뒤로)
Z = Vector((0, 0, 1))


# ───────────────────────── 착암기 ─────────────────────────
def _machine(P, Q, d, L, Lo):
    """몸통 + 손잡이 + 공기다리 (착암기 자리표: 물림쇠 코 = 원점, 축 = +x (뒤 = 손잡이 쪽), z 위). P = 부딪힘 있는 재질 모음, Q = 없는 것.
    다리는 PIN 에서 d 쪽으로 L (바깥 관 Lo). 돌려주는 것: 공기 꼭지 끝 · 물 꼭지 끝"""
    m, i = P["steel_paint"], P["iron"]
    cyl(m, (-0.035, 0, 0), (0, 0, 0), 0.028, 12, r1=0.046); cyl(m, (0, 0, 0), (0.13, 0, 0), 0.05, 12)          # 코 + 앞머리 (물림쇠 통)
    cyl(m, (0.155, 0, 0), (0.50, 0, 0), 0.058, 12); cyl(m, (0.525, 0, 0), (0.62, 0, 0), 0.056, 12, r1=0.05)    # 실린더 (지름 0.116) + 뒷머리
    for x0, x1 in ((0.13, 0.155), (0.50, 0.525)): cyl(i, (x0, 0, 0), (x1, 0, 0), 0.066, 12)                     # 이음 테
    for y in (-0.07, 0.07):                                                                                     # 앞뒤를 조이는 긴 볼트 둘 + 너트 (옆에서 본 착암기의 표시)
        cyl(i, (0.01, y, 0), (0.64, y, 0), 0.009, 6)
        for x in (0.0, 0.625): cyl(i, (x, y, 0), (x + 0.025, y, 0), 0.015, 6)
    box(i, (0.33, 0, 0.066), (0.15, 0.07, 0.022)); cyl(i, (0.18, 0, 0), (0.22, 0, 0), 0.064, 12)               # 배기 덮개 · 다리 띠
    for y in (-0.032, 0.032): box(i, (0.2, y, -0.075), (0.07, 0.012, 0.075))                                   # 다리 걸이 (두 쪽 판)
    q = Q["iron"]
    cyl(q, (0.62, 0, 0), (0.73, 0, 0), 0.02, 8); cyl(q, (0.74, -0.17, 0), (0.74, 0.17, 0), 0.016, 8)           # T 자 손잡이
    for s in (-1, 1): cyl(Q["rubber"], (0.74, s * 0.08, 0), (0.74, s * 0.18, 0), 0.022, 8)                      # 고무 손잡이
    cyl(q, (0.56, -0.05, 0.03), (0.63, -0.075, 0.13), 0.008, 6); box(q, (0.633, -0.076, 0.14), (0.03, 0.02, 0.03))   # 공기 밸브 손잡이 (뒷머리 위 — 당기면 공기가 들어간다)
    a0, a1 = Vector((0.58, 0.035, -0.03)), Vector((0.65, 0.07, -0.09)); u = (a1 - a0).normalized()
    cyl(q, a0, a1, 0.018, 8); cyl(q, a1 - u * 0.03, a1 + u * 0.005, 0.026, 8)                                 # 공기 꼭지 + 물림 이음
    w0, w1 = Vector((0.55, 0.05, -0.015)), Vector((0.60, 0.095, -0.05)); cyl(Q["bare"], w0, w1, 0.009, 6)       # 물 꼭지
    cyl(Q["bare"], PIN - Vector((0, 0.045, 0)), PIN + Vector((0, 0.045, 0)), 0.011, 6)                          # 다리 핀
    cyl(P["iron"], PIN - Vector((0, 0.025, 0)), PIN + Vector((0, 0.025, 0)), 0.03, 8)                           # 다리 머리 (핀이 지나는 통)
    cyl(m, PIN + d * 0.03, PIN + d * Lo, 0.035, 10); cyl(P["iron"], PIN + d * (Lo - 0.01), PIN + d * (Lo + 0.035), 0.041, 10)   # 바깥 관 (지름 7 cm) + 끝 조임 테
    cyl(P["bare"], PIN + d * (Lo + 0.035), PIN + d * (L - 0.1), 0.021, 8)                                       # 속 관 (늘어나는 쪽 — 닳아 번쩍인다)
    cyl(P["iron"], PIN + d * (L - 0.11), PIN + d * (L - 0.06), 0.03, 8); cyl(P["iron"], PIN + d * (L - 0.06), PIN + d * L, 0.03, 8, r1=0.004)   # 발 목 + 뾰족한 발
    return a1, w1


def _rod(Q, x0, x1):
    """육각 정 (x0 = 날 끝 → x1 = 꼬리, 축 = x, y = z = 0): 날(버튼 비트) + 꼬리 테"""
    cyl(Q["bare"], (x0 + 0.03, 0, 0), (x1, 0, 0), 0.0125, 6); cyl(Q["iron"], (x0, 0, 0), (x0 + 0.04, 0, 0), 0.019, 8)
    cyl(Q["iron"], (x1 - 0.13, 0, 0), (x1 - 0.11, 0, 0), 0.018, 6)


def jackleg(PM, rod_len=1.6, leg_deg=50, seed=0):
    """착암기를 막장에 세워 둔 꼴 (구멍을 뚫다 멈춤). 원점 = 정이 막장 면에 꽂힌 점, +x = 막장에서 사람 쪽 (정이 뻗는 반대), z 위. 바닥 = z −BODY_H (−1.2).
    정은 x 0 에서 −ROD_IN (0.25 m) 더 바위 속으로 들어가 있다 (날도 그 속). 몸통 축 = 정 높이 = 바닥 위 1.2 m, 코는 x = rod_len − 0.33.
    공기다리는 바닥과 leg_deg 도로 뒤아래(+x)로 뻗고 (seed 로 −y 쪽으로 3~8 도 비낀다) 발끝이 바닥을 2 cm 뚫는다. 호스 둘은 몸통 뒤에서 +y 쪽으로 늘어져 바닥에 눕는다.
    부딪힘: 몸통 · 다리 = 있음 (JACKLEG_*), 정 · 손잡이 · 호스 = 없음.
    돌려주는 것: (부품 목록, {"hose_out": 공기 호스 끝 (바닥 위 점), "water_out": 물 호스 끝}) — 지역 좌표. 그 점에서 hose() 로 관 밸브 꼭지까지 이어 간다 (공기 dia 0.04 · 물 0.02)"""
    rnd = random.Random("face_kit.jackleg:%d" % seed); P, Q = _Parts(PM, False), _Parts(PM, False)
    xc = rod_len - ROD_IN - 0.08; a = math.radians(leg_deg); psi = math.radians(rnd.uniform(-8, -3))   # 코 자리 (정 꼬리 8 cm 가 물림쇠 속)
    d = Vector((math.cos(a) * math.cos(psi), math.cos(a) * math.sin(psi), -math.sin(a))); L = (BODY_H + PIN.z + 0.02) / math.sin(a)
    air, wat = _machine(P, Q, d, L, min(1.0, 0.62 * L)); _rod(Q, -xc - ROD_IN, 0.08)
    out = P.finish("JACKLEG") + Q.finish("NOCOL_JACKLEG"); f = -BODY_H
    ap = [air - Z * 0.014, air + Vector((0.05, 0.07, -0.16)), Vector((0.76, 0.2, -0.62)), Vector((0.84, 0.29, f)), Vector((1.0, 0.34, f)), Vector((1.2, 0.4, f))]   # 공기 호스 (첫 점은 hose 가 올리는 0.7 r 만큼 내려 꼭지에 맞춘다)
    wp = [wat - Z * 0.007, wat + Vector((0.05, 0.07, -0.15)), Vector((0.71, 0.27, -0.6)), Vector((0.79, 0.37, f)), Vector((0.97, 0.43, f)), Vector((1.15, 0.48, f))]
    out += hose(PM, ap, 0.04, seed, "JACKLEG_AIRHOSE") + hose(PM, wp, 0.02, seed + 1, "JACKLEG_WATERHOSE")
    D = Matrix.Translation((xc, 0, 0))
    for o in out: o.data.transform(D)
    return out, {"hose_out": D @ ap[-1], "water_out": D @ wp[-1]}


def jackleg_lying(PM, seed=0):
    """바닥에 눕혀 둔 착암기: 공기다리는 줄여(속 관을 밀어 넣어) 몸통 밑으로 접었고, 정은 빼서 옆(+y 0.3 m)에 뉘었다. 몸이 옆으로 32~38 도 기울어 T 손잡이 끝과 접은 다리로 바닥을 짚는다.
    원점 = 바닥 (물림쇠 코 밑), 몸통 축 = +x (코 → 손잡이, 다리 발은 x 1.3 까지), z 위. 길이 약 1.6 m (정). 전부 부딪힘 없음 (밟고 지나가도 걸리지 않게). 돌려주는 것: 부품 목록"""
    rnd = random.Random("face_kit.jackleg_lying:%d" % seed); P = _Parts(PM, False)
    _machine(P, P, Vector((1, 0, 0)), 1.12, 0.95); out = P.finish("NOCOL_JACKLEG_LYING")
    M = Matrix.Rotation(math.radians(rnd.uniform(32, 38)), 4, "X")
    for o in out: o.data.transform(M)
    lo = min(v.co.z for o in out for v in o.data.vertices)
    for o in out: o.data.transform(Matrix.Translation((0, 0, -lo - 0.005)))
    R = _Parts(PM, False); _rod(R, 0.0, 1.6); rod = R.finish("NOCOL_JACKLEG_ROD")                              # 날 · 꼬리 테에 얹혀 6 mm 뜬 육각 정
    M = Matrix.Translation((rnd.uniform(-0.45, -0.25), 0.3, 0.016)) @ Matrix.Rotation(math.radians(rnd.uniform(-6, 6)), 4, "Z")
    for o in rod: o.data.transform(M)
    return out + rod


# ───────────────────────── 관 · 호스 ─────────────────────────
def air_pipe(PM, pts, dia=0.1, valves=(), wall_side=None):
    """압축공기 쇠 관 (바랜 잿빛 칠 steel_paint). 물 관도 같은 것을 가늘게 (dia 0.05). pts = 세계 좌표 관 가운데 선 (점 사이 0.6 m 넘게), 꺾이는 점은 굽은 관으로 둥글린다 (반지름 2.5 x 지름).
    6 m 마다 이음 테 (조임 볼트 귀 둘) · 양 끝 막음 테 · 1.5 m 마다 벽 받침쇠: 관을 감은 띠 + wall_side (관 → 벽 쪽 세계 벡터) 로 0.32 m 뻗은 납작쇠 — 관을 벽에서 0.15~0.3 m 띄우면 끝이 벽 속에 묻힌다. None 이면 받침 없음.
    valves = pts 번호들: 그 자리(꺾인 점이면 관 위 가장 가까운 곳)에 아래로 갈래 관 → 손 바퀴 밸브 (바퀴는 벽 반대쪽을 본다) → 아래를 보는 호스 꼭지.
    부딪힘 없음 (벽에 붙은 가는 관 — 몸이 걸리지 않게). 돌려주는 것: (부품 목록, 밸브 꼭지 끝 세계 좌표 목록 — valves 차례, 여기를 hose() 의 첫 점으로)"""
    r = dia / 2; P = _Parts(PM, False); iron = P["iron"]; V = [Vector(p) for p in pts]
    keep = [V[0]] + [b for a, b, c in zip(V, V[1:], V[2:]) if (b - a).normalized().dot((c - b).normalized()) < 0.9998] + [V[-1]]   # 곧은 줄 위의 점은 뺀다 (굽힐 데가 없다)
    line = _fillet(keep, max(2.5 * dia, 0.2), 3) if len(keep) > 2 else keep
    sweep(P["steel_paint"], line, r, seg=10)
    segs = list(zip(line, line[1:])); total = sum((b - a).length for a, b in segs)

    def at(s):
        """관 길이 s 자리의 (점, 방향)"""
        for k, (a, b) in enumerate(segs):
            L = (b - a).length
            if s <= L or k == len(segs) - 1: return a.lerp(b, min(max(s / L, 0.0), 1.0)), (b - a).normalized()
            s -= L

    def near(q):
        """관 위에서 q 에 가장 가까운 자리의 길이 s"""
        best, acc, bs = 9e9, 0.0, 0.0
        for a, b in segs:
            e = b - a; L = e.length; t = min(max((q - a).dot(e) / (L * L), 0.0), 1.0); dd = (a + e * t - q).length
            if dd < best: best, bs = dd, acc + t * L
            acc += L
        return bs

    def perp(v, t):
        """v 를 t 에 수직으로 (안 되면 None)"""
        v = v - t * v.dot(t); return v.normalized() if v.length > 1e-3 else None

    joints = [6.0 * k for k in range(1, int(total / 6.0) + 1) if 6.0 * k < total - 0.3]
    for s in [0.0, total] + joints:                                                            # 막음 테 · 이음 테
        p, t = at(s); cyl(iron, p - t * (0.025 if s in (0.0, total) else 0.05), p + t * (0.025 if s in (0.0, total) else 0.05), r + 0.012, 10)
        if s in joints:
            u = perp(Z, t) or perp(Vector((1, 0, 0)), t)
            for g in (-1, 1): box(iron, p + u * g * (r + 0.022), (0.035, 0.035, 0.035))
    vs = [near(V[i]) for i in valves]
    if wall_side is not None:
        w = Vector(wall_side).normalized(); s = 0.75
        while s < total - 0.2:
            p, t = at(s); u = perp(w, t)
            if u and all(abs(s - v) > 0.3 for v in vs) and all(abs(s - j) > 0.15 for j in joints):
                cyl(iron, p - t * 0.02, p + t * 0.02, r + 0.006, 10)                          # 관을 감은 띠
                box(iron, p + u * (r + 0.16), (0.32, 0.045, 0.008), Matrix((u, t, u.cross(t))).transposed())   # 벽으로 뻗은 납작쇠 (끝은 벽 속)
            s += 1.5
    taps = []
    for s in vs:
        p, t = at(s); b = perp(-Z, t) or perp(Vector((1, 0, 0)), t)                             # 갈래 = 아래로
        a = perp(-Vector(wall_side), t) if wall_side is not None else None
        a = (perp(a, b) if a else None) or t.cross(b).normalized()                             # 바퀴가 보는 쪽 = 벽 반대
        c = p + b * (r + 0.1); e = c + b * 0.14; hub = c + a * 0.13; e2 = b.cross(a)
        cyl(P["steel_paint"], p, p + b * (r + 0.05), 0.026, 8)                                  # 갈래 관
        cyl(iron, c - b * 0.05, c + b * 0.05, 0.04, 10); cyl(iron, c, c + a * 0.09, 0.022, 8)   # 밸브 몸 + 목
        cyl(P["bare"], c + a * 0.09, hub + a * 0.006, 0.006, 6); torus(P["rust"], hub, a, 0.06, 0.008, 12, 4)   # 밸브 대 + 손 바퀴
        for k in range(3): g = math.tau * k / 3; cyl(P["rust"], hub, hub + (b * math.cos(g) + e2 * math.sin(g)) * 0.06, 0.005, 4)   # 바퀴 살
        cyl(P["bare"], c + b * 0.05, e, 0.015, 8); cyl(P["bare"], e - b * 0.03, e - b * 0.015, 0.02, 8)   # 호스 꼭지 + 걸림 턱
        taps.append(e)
    return P.finish("NOCOL_AIRPIPE"), taps


def hose(PM, pts, dia=0.04, seed=0, name="HOSE"):
    """바닥을 따라 늘어진 고무 호스. pts = 세계 좌표 점, z = 그 자리 바닥 높이 (호스 밑이 닿는 높이 — 바닥이 울퉁불퉁하면 1 m 마다 점을 준다).
    점 사이를 부드럽게 잇고 (캣멀롬) 토막마다 옆으로 살짝 굽이친다 (토막 길이의 5 %, 10 cm 까지). 굵기의 30 % 가 바닥에 묻힌다 (뜨지 않게). 밸브 꼭지 같은 높은 점을 주면 거기서 늘어져 내려온다 (두 점 사이 낮은 쪽 밑으로는 안 내려간다).
    양 끝에 쇠 물림 이음. 부딪힘 없음 (NOCOL_ — 밟혀도 걸리지 않게). 돌려주는 것: 부품 목록"""
    rnd = random.Random("face_kit.hose:%s:%d" % (name, seed)); r = dia / 2; P = [Vector(p) for p in pts]; n = len(P)
    tan = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]) / (2 if 0 < i < n - 1 else 1) for i in range(n)]; line = []
    for i in range(n - 1):
        a, b, ta, tb = P[i], P[i + 1], tan[i], tan[i + 1]; L = (b - a).length; k = max(2, math.ceil(L / 0.12)); h = Vector((b.x - a.x, b.y - a.y, 0))
        side = Z.cross(h).normalized() if h.length > 1e-3 else Vector(); amp = rnd.choice((-1, 1)) * min(0.1, 0.05 * L) * rnd.uniform(0.5, 1.0) * h.length / max(L, 1e-6); ph = rnd.uniform(0, math.tau)
        for j in range(k + (i == n - 2)):
            t = j / k; t2, t3 = t * t, t * t * t
            p = (2 * t3 - 3 * t2 + 1) * a + (t3 - 2 * t2 + t) * ta + (3 * t2 - 2 * t3) * b + (t3 - t2) * tb + side * amp * math.sin(math.pi * t) * (0.7 + 0.3 * math.sin(3 * math.pi * t + ph))
            p.z = max(p.z, min(a.z, b.z)) + r * 0.7; line.append(p)
    bm = bmesh.new(); sweep(bm, line, r, seg=8 if dia >= 0.03 else 6); out = [obj("NOCOL_" + name, bm, PM["rubber"], smooth=True)]
    bm = bmesh.new()
    for p, q in ((line[0], line[1]), (line[-1], line[-2])): u = (q - p).normalized(); cyl(bm, p - u * 0.01, p + u * 0.05, r * 1.35, 8)
    return out + [obj("NOCOL_" + name + "_END", bm, PM["iron"], smooth=True)]


# ───────────────────────── 막장 면: 구멍 · 자리 · 분필 ─────────────────────────
def drill_holes(PM, spots, dia=0.04):
    """발파 구멍. spots = [(세계 위치, 바깥쪽 법선)] — 위치는 실제 막장 면 위의 점 (광선으로 잰 점). 면을 파지 않고 면 앞에 붙인다:
    바위 속 4 cm 에서 올라와 면 위 1.2 cm 로 솟은 깨진 돌 테 (뚫을 때 나온 가루로 조금 밝다 — concrete, 가장자리 들쭉날쭉) + 안으로 꺼지는 깔때기와 바닥 (아주 어두운 잿빛 rubber — 순수 검정 아님).
    구멍 하나 = 닫힌 덩어리 하나 (60 삼각형). 부딪힘 없음 (NOCOL_HOLES). 돌려주는 것: 부품 목록"""
    rnd = random.Random("face_kit.holes:%d" % len(spots)); r = dia / 2; seg = 8; bm = bmesh.new()
    for p, nrm in spots:
        p = Vector(p); q = Vector(nrm).normalized().to_track_quat("Z", "Y").to_matrix(); ph = rnd.uniform(0, math.tau); jit = [rnd.uniform(0.75, 1.35) for _ in range(seg)]
        ring = lambda rr, z, j: [bm.verts.new(p + q @ Vector((rr * (1 + (jit[k] - 1) * j) * math.cos(ph + math.tau * k / seg), rr * (1 + (jit[k] - 1) * j) * math.sin(ph + math.tau * k / seg), z + 0.004 * j * rnd.random()))) for k in range(seg)]
        R = [ring(r * 2.3, -0.04, 1.0), ring(r * 1.9, 0.004, 1.0), ring(r * 1.25, 0.012, 0.3), ring(r * 0.9, 0.003, 0.15)]   # 묻힌 밑 → 테 바깥 → 테 입술 → 구멍 바닥
        for m, (A, B) in enumerate(zip(R, R[1:])):
            for k in range(seg): bm.faces.new((A[k], A[(k + 1) % seg], B[(k + 1) % seg], B[k])).material_index = int(m == 2)
        bm.faces.new(R[0][::-1]); bm.faces.new(R[-1]).material_index = 1
    o = obj("NOCOL_HOLES", bm, PM["concrete"]); o.data.materials.append(PM["rubber"]); return [o]


def burn_pattern(w, h, n=24, seed=0):
    """굴진 막장 면의 발파 구멍 자리 (조사/01:26 · 12:68). 면 가운데 원점, u = 오른쪽 (면을 마주 볼 때), v = 위, 바닥 v = −h/2.
    가운데 몰린 구멍 4~6 (면 가운데보다 5 % 아래, 반지름 0.12 m 고리 — 홀수면 한가운데 하나) + 둘레 고리 (옆 · 위, 가장자리에서 0.15 m 안, 둥근 네모) + 바닥 줄 (바닥 위 0.12 m, 약 0.55 m 간격).
    손으로 뚫은 것이라 ±3 cm (가운데는 ±1 cm) 흔들린다. 돌려주는 것: [(u, v)] n 개 (가운데 → 둘레 → 바닥 차례)"""
    rnd = random.Random("face_kit.burn_pattern:%d" % seed); j = lambda s=0.03: rnd.uniform(-s, s)
    k = rnd.randint(4, 6); m = min(max(3, round(w / 0.55)), n - k - 3); cy = -0.05 * h
    out = [(0.0, cy)] if k % 2 else []; c = k - len(out)
    out += [(0.12 * math.cos(math.pi / 4 + math.tau * i / c) + j(0.01), cy + 0.12 * math.sin(math.pi / 4 + math.tau * i / c) + j(0.01)) for i in range(c)]
    A, B = w / 2 - 0.15, h / 2 - 0.15; sq = lambda x: math.copysign(abs(x) ** 0.5, x)                     # 둥근 네모 (초타원 지수 4)
    pp = [(A * sq(math.cos(t)), B * sq(math.sin(t))) for t in (math.radians(-50 + 280 * i / 200) for i in range(201))]; cum = [0.0]
    for a, b in zip(pp, pp[1:]): cum.append(cum[-1] + math.dist(a, b))
    ring = n - k - m
    for i in range(ring):
        s = cum[-1] * i / max(ring - 1, 1); x, y = pp[min(range(len(cum)), key=lambda q: abs(cum[q] - s))]; out.append((x + j(), y + j()))
    out += [(-(w / 2 - 0.2) + (w - 0.4) * i / (m - 1) + j(), -h / 2 + 0.12 + j(0.015)) for i in range(m)]
    return out


def chalk(PM, text, size=0.12, seed=0):
    """분필 글씨 (흰 분필 chalk, 살짝 비뚤게 — 줄이 ±7 도 기울고 글자 줄이 물결친다). 글씨체 = 인트로 을지로체 (_util.FONT, 곡선 resolution 2 + thin) · 두께 없음.
    자리표 = 벽 소품 약속 (wall_props): 면 = y 0, 글자는 y −0.004 에서 −y 쪽으로 읽힌다, x 오른쪽, z 위, 원점 = 글 가운데. 막장 면(법선 n)에 붙이려면 −y 가 n 을 보게 돌린다 (n = +x 면 Rz(+90°)).
    부딪힘 없음 (NOCOL_CHALK). 돌려주는 것: 부품 목록"""
    rnd = random.Random("face_kit.chalk:%s:%d" % (text, seed))
    o = text_mesh("NOCOL_CHALK", text, (0, -0.004, 0), size, PM["chalk"], rot=(math.pi / 2, math.radians(rnd.uniform(-7, 7)), 0), extrude=0.0)
    vs = o.data.vertices; ph, k = rnd.uniform(0, math.tau), rnd.uniform(0.04, 0.08)
    for v in vs: v.co.z += size * k * math.sin(v.co.x / size * 2.2 + ph)
    cx, cz = (min(v.co.x for v in vs) + max(v.co.x for v in vs)) / 2, (min(v.co.z for v in vs) + max(v.co.z for v in vs)) / 2
    for v in vs: v.co.x -= cx; v.co.z -= cz
    return [o]


# ───────────────────────── 미리보기 + 스스로 검사 ─────────────────────────
if __name__ == "__main__":
    import json
    import _util, timber_sets
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []; out_dir = argv[0] if argv else HERE; os.makedirs(out_dir, exist_ok=True)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene; T = Matrix.Translation; Rz = lambda deg: Matrix.Rotation(math.radians(deg), 4, "Z")
    LOOK = {"steel_paint": (0.2, 0.2, 0.19), "iron": (0.11, 0.11, 0.115), "bare": (0.3, 0.3, 0.31), "rust": (0.2, 0.12, 0.08), "concrete": (0.3, 0.29, 0.27), "chalk": (0.5, 0.5, 0.47), "rubber": (0.02, 0.02, 0.02),
            "timber": (0.22, 0.18, 0.12), "timber_end": (0.28, 0.24, 0.17), "plank": (0.2, 0.16, 0.11)}   # 맵 값에 가깝게 (맵의 쇠 셋은 같은 철판 사진, 막장 나무는 가루 앉아 어둡다)

    def flat(nm, rgb, rough=0.8, metal=0.0):
        m = bpy.data.materials.new(nm); m.use_nodes = True; b = next(x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal; return m
    PM = {k: flat(k, LOOK.get(k, v), 0.55 if k in ("steel_paint", "iron", "bare") else 0.8, 0.6 if k in ("steel_paint", "iron", "bare") else 0.0) for k, v in _util.MAT_KEYS.items()}
    tris = lambda objs: sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)

    def islands_ok(objs, support):
        """떠 있는 덩어리 찾기 (_preview 와 같은 법): 덩어리마다 support(점) 이거나 다른 덩어리 상자와 2 cm 안이면 닿음"""
        isl = []
        for o in objs:
            b = bmesh.new(); b.from_mesh(o.data); b.transform(o.matrix_world); b.verts.index_update(); seen = set()
            for v in b.verts:
                if v.index in seen: continue
                st, comp = [v], []
                while st:
                    x = st.pop()
                    if x.index in seen: continue
                    seen.add(x.index); comp.append(x.co.copy()); st += [e.other_vert(x) for e in x.link_edges]
                isl.append((o.name, [min(c[i] for c in comp) for i in range(3)], [max(c[i] for c in comp) for i in range(3)], any(support(c) for c in comp)))
        ok = [s for *_, s in isl]; ch = True
        while ch:
            ch = False
            for i, (_, lo, hi, _) in enumerate(isl):
                if not ok[i] and any(ok[j] and all(lo[k] <= isl[j][2][k] + 0.02 and isl[j][1][k] <= hi[k] + 0.02 for k in range(3)) for j in range(len(isl))): ok[i] = ch = True
        return [isl[i][0] for i in range(len(isl)) if not ok[i]]

    # 스스로 검사: 숫자로 답이 나오는 것
    for w_, h_, n_ in ((3.0, 2.4, 24), (2.4, 2.2, 20), (4.0, 3.0, 25)):
        bp = burn_pattern(w_, h_, n_, seed=1); assert len(bp) == n_, "burn_pattern: 수가 다르다"
        assert all(abs(u) <= w_ / 2 - 0.1 and abs(v) <= h_ / 2 - 0.05 for u, v in bp), "burn_pattern: 면 밖"
        assert 4 <= sum(math.hypot(u, v + 0.05 * h_) < 0.2 for u, v in bp) <= 6, "burn_pattern: 가운데 몰린 구멍 4~6 아님"
        assert sum(v < -h_ / 2 + 0.2 for u, v in bp) >= 3, "burn_pattern: 바닥 줄 없음"
        assert min(math.dist(a, b) for i, a in enumerate(bp) for b in bp[i + 1:]) > 0.08, "burn_pattern: 구멍이 겹친다"
    jl, ends = jackleg(PM, seed=1); lz = min((o.matrix_world @ v.co).z for o in jl if not o.name.startswith("NOCOL_") for v in o.data.vertices)   # 몸통 · 다리만 (호스는 따로 바닥에 눕는다)
    assert abs(lz + BODY_H + 0.02) < 0.01, "jackleg: 발끝이 바닥(−1.2)에 안 닿는다 (%.3f)" % lz
    assert abs(ends["hose_out"].z + BODY_H) < 1e-6 and abs(ends["water_out"].z + BODY_H) < 1e-6, "jackleg: 호스 끝이 바닥 위가 아니다"
    fl = islands_ok(jl, lambda c: c.z <= -BODY_H + 0.03 or c.x <= 0.0); assert not fl, "jackleg: 떠 있는 덩어리 %s" % fl[:5]
    ly = jackleg_lying(PM, seed=2); fl = islands_ok(ly, lambda c: c.z <= 0.03); assert not fl, "jackleg_lying: 떠 있는 덩어리 %s" % fl[:5]
    assert abs(min((o.matrix_world @ v.co).z for o in ly for v in o.data.vertices) + 0.005) < 0.006, "jackleg_lying: 바닥에 안 닿는다"
    tri = {"jackleg": tris(jl), "jackleg_lying": tris(ly)}; assert tri["jackleg"] < 6000, "jackleg: 삼각형 %d (6,000 넘음)" % tri["jackleg"]
    for o in jl + ly: bpy.data.objects.remove(o, do_unlink=True)

    # 무대: 굴진 막장 (면 = x 0, 굴은 +x 로, 바닥 z 0, 벽 y ±1.75, 천장 2.6) + 동발 틀 둘
    stage = {}
    def slab(nm, c, s, rgb):
        bm = bmesh.new(); box(bm, c, s); stage[nm] = obj("STAGE_" + nm, bm, flat("st_" + nm, rgb, 0.95)); return stage[nm]
    slab("floor", (4, 0, -0.05), (9, 3.9, 0.1), (0.05, 0.042, 0.034)); slab("face", (-0.15, 0, 1.3), (0.3, 3.5, 2.6), (0.17, 0.15, 0.12))
    slab("wallR", (4, 1.85, 1.3), (9, 0.2, 2.6), (0.12, 0.105, 0.085)); slab("wallL", (4, -1.85, 1.3), (9, 0.2, 2.6), (0.12, 0.105, 0.085)); slab("ceil", (4, 0, 2.7), (9, 3.9, 0.2), (0.1, 0.09, 0.075))
    frames = []
    for x in (2.2, 4.4): frames += _util.place(timber_sets.frame(PM, width=2.8, height=2.3, lagging=4, seed=int(x * 10)), T((x, 0, 0)))
    kit = {}
    face_c = Vector((0, 0, 1.2)); spots = [(face_c + Vector((0, u, v)), (1, 0, 0)) for u, v in burn_pattern(3.0, 2.4, 24, seed=1)]
    Mj = T((0, 0.55, BODY_H)); spots.append((Vector((0, 0.55, BODY_H)), (1, 0, 0)))                    # 착암기가 뚫던 구멍
    kit["holes"] = drill_holes(PM, spots); jl, ends = jackleg(PM, seed=1); kit["jackleg"] = _util.place(jl, Mj)
    kit["lying"] = _util.place(jackleg_lying(PM, seed=2), T((0.9, -1.0, 0)) @ Rz(18))
    kit["air_pipe"], at_ = air_pipe(PM, [(8.4, 1.5, 1.95), (3.4, 1.5, 1.95), (2.9, 1.5, 1.55)], 0.1, valves=(2,), wall_side=(0, 1, 0))
    kit["water_pipe"], wt_ = air_pipe(PM, [(8.4, 1.6, 1.2), (2.6, 1.6, 1.2)], 0.05, valves=(1,), wall_side=(0, 1, 0))
    ho, wo = Mj @ ends["hose_out"], Mj @ ends["water_out"]; a, b = at_[0], wt_[0]
    kit["air_hose"] = hose(PM, [a, a + Vector((0.03, -0.06, -0.6)), Vector((a.x - 0.1, a.y - 0.3, 0)), Vector((2.75, 1.0, 0)), ho], 0.04, 3, "AIRHOSE")
    kit["water_hose"] = hose(PM, [b, Vector((b.x - 0.05, b.y - 0.2, 0)), wo], 0.02, 4, "WATERHOSE")
    kit["chalk"] = _util.place(chalk(PM, "X", 0.22, 1), T((0, -0.75, 1.55)) @ Rz(90)) + _util.place(chalk(PM, "12", 0.14, 2), T((0, 0.95, 1.9)) @ Rz(90))
    one = [drill_holes(PM, [((0, 0, -5), (1, 0, 0))]), chalk(PM, "X", 0.2), chalk(PM, "12", 0.14)]; hole_one, x_one, n_one = (tris(v) for v in one)
    for o in sum(one, []): bpy.data.objects.remove(o, do_unlink=True)
    tri.update({k: tris(v) for k, v in kit.items()}); tri.update(hole_each=hole_one, chalk_X=x_one, chalk_12=n_one, holes_n=len(spots),
                pipe_len_m=round(sum((Vector(p) - Vector(q)).length for p, q in (((8.4, 1.5, 1.95), (3.4, 1.5, 1.95)), ((3.4, 1.5, 1.95), (2.9, 1.5, 1.55)))), 2))
    print("FACEKIT " + json.dumps(tri, ensure_ascii=False))
    print("FACEKIT hose_out %s water_out %s taps %s %s" % (tuple(round(c, 3) for c in ends["hose_out"]), tuple(round(c, 3) for c in ends["water_out"]), tuple(round(c, 3) for c in a), tuple(round(c, 3) for c in b)))

    # 그림 셋 (가로 800)
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try: sc.render.engine = eng; break
        except TypeError: pass
    sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True; bg = next(x for x in sc.world.node_tree.nodes if x.type == "BACKGROUND")
    cam = bpy.data.objects.new("CAM", bpy.data.cameras.new("CAM")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.sensor_fit = "VERTICAL"; cam.data.angle_y = math.radians(57); cam.data.clip_start = 0.05
    lamp = bpy.data.objects.new("HEAD", bpy.data.lights.new("HEAD", "SPOT")); sc.collection.objects.link(lamp); lamp.data.spot_size = math.radians(70); lamp.data.spot_blend = 0.5; lamp.data.color = (1.0, 0.96, 0.88)
    sun = bpy.data.objects.new("SUN", bpy.data.lights.new("SUN", "SUN")); sc.collection.objects.link(sun); sun.rotation_euler = (math.radians(50), 0, math.radians(-60)); sun.data.energy = 3.0
    sc.render.resolution_x, sc.render.resolution_y = 800, 450
    views = [("set", (6.0, -0.8, 1.65), (0.6, 0.45, 1.0), False, 1300), ("jackleg", (1.7, -2.5, 1.25), (1.35, 0.55, 0.7), True, 0), ("close", (2.4, -1.9, 1.5), (0.4, -0.35, 0.65), True, 0)]
    for nm, eye, look, bright, watt in views:
        cam.location = eye; qq = (Vector(look) - Vector(eye)).to_track_quat("-Z", "Y"); cam.rotation_euler = qq.to_euler()
        lamp.location = Vector(eye) + Vector((0, 0, 0.1)); lamp.rotation_euler = qq.to_euler(); lamp.data.energy = watt; lamp.hide_render = bright; sun.hide_render = not bright
        for k in ("wallL", "ceil"): stage[k].hide_render = bright
        for o in frames: o.hide_render = bright
        bg.inputs[0].default_value = (0.25, 0.25, 0.27, 1) if bright else (0.003, 0.003, 0.0035, 1)
        sc.render.filepath = os.path.join(out_dir, "face_kit_%s.png" % nm); bpy.ops.render.render(write_still=True)
    print("FACEKIT done -> %s" % out_dir)
