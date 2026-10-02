"""옛 창고 칸 줄 (마구간을 고쳐 쓴 지하 자재 창고): 판자 칸막이 + 칸마다 든 물건 여섯 가지. Blender 안에서만 돈다.
레퍼런스 사진은 없다 (계획서 글 "옛 마구간을 창고로 쓴다" 뿐). 그래서 이 맵의 다른 방에서 이미 본 물건의 "여분" 을 칸마다 한 가지씩 둔다 —
선로(레일 · 침목) / 배수관(플랜지 관 · 밸브) / 권양기 쇠줄(얼레 · 타래 · 도르래 바퀴) / 바람 관(천 두루마리 · 쇠 테 · 선풍기 통) / 연장(삽 · 곡괭이 · 작업대) / 기계 기름(드럼통 · 말통).
  partition(mats, depth, height, seed)  판자 칸막이 한 장. 원점 = 뒷벽(+y) 쪽 끝 바닥, −y 로 depth 만큼 나온다. 두께 = x.
                                        기둥 · 띠장이 보이는 쪽 = −x, 판자 쪽 = +x. seed 짝수 = 밧줄 타래, 홀수 = 안전등이 가운데 기둥 걸이 못에 걸린다 (x −0.23 까지).
                                        부러진 판자의 떨어진 토막이 +x 쪽 발치에 기대 서 있다 (x 0.24 까지).
  fill(mats, kind, width, depth, seed)  칸 하나에 든 물건. 원점 = 칸 가운데 뒷벽 바닥 (벽 = y 0). x ±(width/2 − 0.25), y −depth .. −0.05, 높이 1.9 아래.
                                        kind = "rails" / "pipes" / "rope" / "duct" / "tools" / "drums"
                                        자리는 칸 가장자리 기준으로 잡는다 — 기본 크기(3.4 x 2.4)에 맞췄고, 너비 3.0 · 깊이 2.2 보다 작으면 물건끼리 겹친다.
벽에 기댄 것도 y = −0.05 에서 멈춘다 (벽에 닿지 않아도 전부 바닥에 선다). 조각 이름 끝이 _R = 둥근 것 (매끈 셰이딩).
머리 위로 지나는 것은 없다 (전부 바닥에 선 장애물). 글자 판은 "drums" 의 "화기엄금" 하나.
10-03 두 번째 손질 (그림만 본 사람이 못 알아본 것): 관 · 바람 관 끝을 진짜 구멍으로 / 레일 더미 끝 단면이 통로를 보게 / 침목은 타르 색 / 쇠줄은 가는 가닥 골 /
연장 머리 · 레일 · 관은 검은 쇠 / 벽에 "꼿꼿이 선" 것들은 눕히거나 눈에 보이게 기대거나 뺐다."""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, torus, sweep, text_mesh
from machines import _Parts
from timber_store import _wedge, _obj, _Logs

D2R = math.radians
X, Z = Vector((1, 0, 0)), Vector((0, 0, 1))
RX = lambda d: Matrix.Rotation(D2R(d), 4, "X")
RY = lambda d: Matrix.Rotation(D2R(d), 4, "Y")
RZ = lambda d: Matrix.Rotation(D2R(d), 4, "Z")


# ───────────────────────── 공용 ─────────────────────────
def _ax(c, d):
    """원점 c, z 축이 d 를 보는 자리표"""
    return Matrix.Translation(Vector(c)) @ Vector(d).to_track_quat("Z", "Y").to_matrix().to_4x4()


def _T(x, y, z=0.0, yaw=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(D2R(yaw), 4, "Z")


def _rest(x, R, hw, lean, yaw):
    """벽에 기대 세운 바퀴 꼴의 자리표 (z = 바퀴 축): lean 만큼 뒤로 눕고 yaw 만큼 돌아선 채 맨 아래가 바닥, 맨 뒤가 y = −0.05. R = 바깥 반지름, hw = 반 두께"""
    q = Matrix.Rotation(D2R(yaw), 3, "Z") @ Matrix.Rotation(D2R(90 - lean), 3, "X")
    pts = [q @ Vector((R * math.cos(math.pi * i / 16), R * math.sin(math.pi * i / 16), s * hw)) for i in range(32) for s in (-1, 1)]
    return Matrix.Translation((x, -0.05 - max(p.y for p in pts), -min(p.z for p in pts))) @ q.to_4x4()


def _upf(d):
    """자루 방향 d 를 z 로, 너비를 x (세계 x 쪽) 로 잡은 3x3 — 세워 둔 연장용 (−y 가 보는 사람 쪽)"""
    z = Vector(d).normalized(); x = (X - z * X.dot(z)).normalized()
    return Matrix((x, z.cross(x), z)).transposed()


def _lathe(bm, M, prof, seg=12, caps=True, sharp=0.6):
    """M 의 z 축 둘레로 돌린 덩어리. prof = [(반지름, 축 자리)]. sharp(라디안) 넘게 꺾인 테는 모서리를 세운다 — 매끈 셰이딩에서도 뚜껑이 평평하게 보인다.
    caps=False 이고 처음 점 = 끝 점이면 단면이 닫힌 도넛 (고리를 이어 붙인다 — 닫힌 덩어리라 면 방향이 틀릴 일이 없다)"""
    loop = not caps and len(prof) > 2 and tuple(prof[0]) == tuple(prof[-1]); pr = prof[:-1] if loop else prof
    rings = [[bm.verts.new(M @ Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), a))) for i in range(seg)] for r, a in pr]
    for A, B in list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if loop else []):
        for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]))
    pts = [Vector(p) for p in pr]; off = 0
    if caps: bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1]); pts = [Vector((0, pr[0][1]))] + pts + [Vector((0, pr[-1][1]))]; off = 1
    elif loop: pts = [pts[-1]] + pts + [pts[0]]; off = 1
    for k in range(1, len(pts) - 1):
        a, b = pts[k] - pts[k - 1], pts[k + 1] - pts[k]
        if a.length > 1e-6 and b.length > 1e-6 and a.angle(b) > sharp:
            R = rings[k - off]
            for i in range(seg): bm.edges.get((R[i], R[(i + 1) % seg])).smooth = False


def _rod(bm, p0, p1, r, seg=10, r1=None):
    """p0 → p1 둥근 막대 (끝면이 평평하게 선다)"""
    p0, p1 = Vector(p0), Vector(p1); _lathe(bm, _ax(p0, p1 - p0), [(r, 0), (r if r1 is None else r1, (p1 - p0).length)], seg)


def _ext(bm, prof, p0, p1, up=Z):
    """단면 prof = [(옆, 위)] 를 p0 → p1 로 민 막대 (레일)"""
    p0, p1 = Vector(p0), Vector(p1); t = (p1 - p0).normalized(); s = t.cross(Vector(up)).normalized(); u = s.cross(t); n = len(prof)
    A = [bm.verts.new(p0 + s * a + u * b) for a, b in prof]; B = [bm.verts.new(p1 + s * a + u * b) for a, b in prof]
    for i in range(n): bm.faces.new((A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]))
    bm.faces.new(A[::-1]); bm.faces.new(B)


class _Flat:
    """홑면 딱지 모음 (관 속 어둠 · 볼트 구멍 · 널 이음 금 · 말린 천의 소용돌이 금). 면마다 바깥 방향을 적어 두었다가 뒤집힌 것을 바로잡는다"""
    def __init__(s): s.bm = bmesh.new(); s.out = []
    def disc(s, c, n, r, seg=10):
        c, n = Vector(c), Vector(n).normalized(); q = n.to_track_quat("Z", "Y").to_matrix()
        s.bm.faces.new([s.bm.verts.new(c + q @ Vector((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), 0))) for i in range(seg)]); s.out.append(n)
    def quad(s, pts, n):
        s.bm.faces.new([s.bm.verts.new(Vector(p)) for p in pts]); s.out.append(Vector(n).normalized())


def _crate(bm, M, w=0.6, d=0.4, h=0.3):
    """뚜껑 없는 판자 궤짝: 밑 굄대 2 + 바닥 널 + 옆 널 2 줄 (사이가 벌어져 있다) + 모서리 각목"""
    R = M.to_3x3(); at = lambda *p: M @ Vector(p); hb = (h - 0.06) / 2
    for x in (-w / 3, w / 3): box(bm, at(x, 0, 0.015), (0.05, d, 0.03), R)
    box(bm, at(0, 0, 0.04), (w, d, 0.02), R)
    for z in (0.05 + hb / 2, 0.06 + hb * 1.5):
        for s in (-1, 1): box(bm, at(0, s * (d / 2 - 0.01), z), (w, 0.02, hb - 0.01), R); box(bm, at(s * (w / 2 - 0.01), 0, z), (0.02, d - 0.04, hb - 0.01), R)
    for sx in (-1, 1):
        for sy in (-1, 1): box(bm, at(sx * (w / 2 - 0.04), sy * (d / 2 - 0.04), 0.05 + (h - 0.05) / 2), (0.04, 0.04, h - 0.05), R)


def _mouth(F, M, a, s, r, fr, bore, seg, holes=6):
    """뚫린 관 끝의 어둠: 구멍 속 깊은 곳에 검은 바닥 + 플랜지 볼트 구멍. a = 끝 자리, s = 관 속 쪽 (+1 / −1)"""
    n = M.to_3x3() @ Vector((0, 0, -s)); ri = r - 0.008
    F.disc(M @ Vector((0, 0, a + s * (bore - 0.004))), n, ri * 1.04, seg)
    for i in range(holes):
        q = 2 * math.pi * (i + 0.5) / holes; rr = (r + fr) / 2 + 0.004
        F.disc(M @ Vector((rr * math.cos(q), rr * math.sin(q), a - s * 0.002)), n, 0.011, 4)


def _flange(bm, F, M, a, s, r, fr=0.10, t=0.02, seg=12, open_=True, bore=0.05):
    """관 끝 플랜지 (닫힌 덩어리). a = 축 위 끝 자리, s = 관 속 쪽 방향 (+1 / −1). open_ = 구멍이 bore 깊이로 파여 속이 보이고 볼트 구멍이 있다"""
    if not open_: _lathe(bm, M, [(fr, a), (fr, a + s * t)], seg); return
    ri = r - 0.008
    _lathe(bm, M, [(ri, a + s * bore), (ri, a), (fr, a), (fr, a + s * t), (r - 0.002, a + s * t), (r - 0.002, a + s * (bore + 0.004))], seg); _mouth(F, M, a, s, r, fr, bore, seg)


def _wheel(bm, M, R, r=0.012, bars=2):
    """손잡이 바퀴: 테 + 납작한 살 + 가운데 통. 축 = M 의 z"""
    q = M.to_3x3(); torus(bm, M.translation, q @ Z, R, r, seg=12, sub=4)
    _lathe(bm, M @ Matrix.Translation((0, 0, -0.02)), [(R * 0.2, 0), (R * 0.2, 0.04)], 10)
    for i in range(bars): box(bm, M.translation, (2 * R, 0.022, 0.012), q @ Matrix.Rotation(math.pi * i / bars, 3, "Z"))


def _loop(bm, M, R, r, seg=12):
    """줄 한 고리 (세모 단면 도넛). 축 = M 의 z"""
    _lathe(bm, M, [(R + r, 0), (R - 0.5 * r, 0.87 * r), (R - 0.5 * r, -0.87 * r), (R + r, 0)], seg, caps=False, sharp=9)


def _out(P, mats):
    """모은 조각을 물체로 낸다. 그 전에 면 노멀을 새로 센다 — box() · cyl() 은 만든 뒤 점을 돌려 옮기므로 옛 노멀이 남고,
    obj() 의 방향 자동 맞춤이 그 옛 노멀을 믿어 돌려 놓은 상자 · 원기둥을 뒤집는다 (게임에서 뒤집힌 면은 안 보인다)"""
    for bm, _ in P.d.values(): bm.normal_update()
    return P.out(mats, smooth={k for k in P.d if k.endswith("_R")})


def _hang(c, n, stretch=1.0, yaw=0.0):
    """못에 걸려 늘어진 고리의 자리표: 고리 면이 수평 방향 n 을 보고, 제 무게로 세로로 stretch 배 늘어진다"""
    n = Vector(n).normalized(); u = Z.cross(n)
    return Matrix.Translation(Vector(c)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix((u, Z, n)).transposed().to_4x4() @ Matrix.Diagonal((1, stretch, 1, 1))


# ───────────────────────── 칸막이 ─────────────────────────
def partition(mats, depth=3.0, height=2.2, seed=0):
    """판자 칸막이: 각목 기둥(0.12) 둘 · 셋 + 밑 도리 + 띠장 두 줄 + 세로 판자 (너비 0.18 ~ 0.22, 틈 1 ~ 2 cm, 윗끝 들쭉날쭉, 한 장 빠지고 한 장 부러짐) + 가운데 기둥 걸이 못에 걸린 것"""
    rnd = random.Random(seed); P = _Parts("STALL_"); f = P("FRAME", "tar"); pl = P("PLANKS", "timber_old")
    ys = [-0.06, -depth / 2, -depth + 0.06] if depth > 2.4 else [-0.06, -depth + 0.06]
    for y in ys: box(f, (-0.03, y, height / 2), (0.12, 0.12, height))
    box(f, (-0.03, -depth / 2, 0.04), (0.10, depth - 0.02, 0.08))                                # 밑 도리 (기둥 발을 잡는 바닥 각목)
    for z in (0.45, height - 0.45): box(f, (0.0475, -depth / 2, z), (0.035, depth, 0.10))
    n = int(depth / 0.215); miss = rnd.randrange(3, n - 3) if n > 7 else -9; brk = miss + rnd.choice((-2, 2)); y = -0.004; i = 0
    while y > -depth + 0.08:
        w = min(rnd.uniform(0.18, 0.22), y + depth); yc = y - w / 2; top = height - rnd.uniform(0.0, 0.06)
        if i == brk:   # 부러진 판자: 밑동은 뾰족하게 찢긴 채 서 있고, 윗 토막은 윗 띠장 못 하나에 매달려 비뚤게 돌아갔고, 가운데 토막은 발치에 기대 서 있다
            zb = rnd.uniform(0.75, 0.95); zt = rnd.uniform(1.30, 1.40); piv = Vector((0.0775, yc, height - 0.45)); R = Matrix.Rotation(D2R(rnd.choice((-12, 12))), 3, "X")
            for v in box(pl, (0.0775, yc, zb / 2), (0.025, w, zb)):
                if v.co.z > zb / 2 and v.co.y > yc: v.co.z += 0.22
            for v in box(pl, (0.104, yc, (zt + top) / 2), (0.025, w, top - zt)):
                if v.co.z < (zt + top) / 2 and v.co.y < yc: v.co.z -= 0.18
                v.co = R @ (v.co - piv) + piv
            a = D2R(-12); box(pl, Vector((0.215, yc - 0.03, 0.002)) + Vector((math.sin(a), 0, math.cos(a))) * 0.24, (0.025, w, 0.48), Matrix.Rotation(a, 3, "Y"))
        elif i != miss: box(pl, (0.0775, yc, top / 2), (0.025, w, top), Matrix.Rotation(D2R(rnd.uniform(-0.35, 0.35)), 3, "X"))
        y -= w + rnd.uniform(0.01, 0.02); i += 1
    ym = ys[len(ys) // 2]
    box(P("NOCOL_STALL_PEG", "iron"), (-0.155, ym, 1.63), (0.15, 0.03, 0.03), Matrix.Rotation(D2R(12), 3, "Y"))   # 기둥에 박은 굵은 걸이 못 (끝이 들렸다)
    if seed % 2 == 0:   # 사려서 건 밧줄: 못에 걸려 길쭉하게 늘어진 고리 셋
        c = P("NOCOL_STALL_COIL_R", "cloth")
        for k in range(3): _loop(c, _hang((-0.125 - 0.03 * k, ym + rnd.uniform(-0.012, 0.012), 1.44 - 0.006 * k), X, 1.7, rnd.uniform(-0.12, 0.12)), 0.13 - 0.006 * k, 0.016, 10)
    else:               # 안전등 (가스 재는 불꽃 등): 밑통 + 유리와 살 셋 + 쇠 갓 + 못에 건 고리 쇠
        M = _T(-0.17, ym, 1.24); L = P("NOCOL_STALL_LAMP_R", "bare"); k = P("NOCOL_STALL_LAMP_IRON", "iron")
        _lathe(L, M, [(0.055, 0), (0.055, 0.06)], 10); _lathe(L, M, [(0.046, 0.15), (0.04, 0.25), (0.02, 0.29)], 10)
        _lathe(P("NOCOL_STALL_LAMP_GLASS_R", "glass"), M, [(0.036, 0.06), (0.036, 0.15)], 10, caps=False)
        for i in range(3): g = 2.1 * i + 0.5; box(k, M @ Vector((0.047 * math.cos(g), 0.047 * math.sin(g), 0.105)), (0.009, 0.009, 0.10))
        box(k, M @ Vector((0, 0, 0.345)), (0.009, 0.009, 0.12))
    return _out(P, mats)


# ───────────────────────── 레일 칸 ─────────────────────────
# 광산 레일 단면 (옆, 위): 넓은 밑판 → 가는 허리 → 머리
_RAIL = [(-.05, 0), (.05, 0), (.05, .012), (.009, .026), (.009, .066), (.027, .074), (.027, .10), (-.027, .10), (-.027, .074), (-.009, .066), (-.009, .026), (-.05, .012)]


def _fishplate(bm, F, M):
    """이음판: 볼트 구멍 넷 뚫린 납작한 쇠판 (레일 두 토막을 잇는다)"""
    box(bm, M.translation, (0.42, 0.065, 0.018), M.to_3x3())
    for x in (-0.16, -0.06, 0.06, 0.16): F.disc(M @ Vector((x, 0, 0.0105)), M.to_3x3() @ Z, 0.012, 4)


def _rails(P, F, mats, rnd, W, D):
    t = P("TIMBER", "timber_old"); sl = P("SLEEPER", "tar"); k = P("IRON", "iron"); x0 = -W + 0.10
    # 받침목 둘 위 레일 더미 (왼쪽): 끝 단면(工 꼴)이 통로를 본다. 일곱 · 여섯 · 다섯 · 셋, 아래 켜 머리 사이에 밑판이 걸친다. 끝 자리가 제각각, 녹슨 것이 섞였다
    for y in (-0.60, -D + 0.60): box(t, (x0 + 0.345, y, 0.06), (0.88, 0.12, 0.12))
    for L, n in enumerate((7, 6, 5, 3)):
        for i in range(n):
            x = x0 + 0.115 * (i + 0.5 * L); z = 0.12 + 0.10 * L
            _ext(P("RAIL_RUST", "rust") if rnd.random() < 0.3 else P("RAIL", "iron"), _RAIL, (x, -D + 0.10 + rnd.uniform(0, 0.14), z), (x, -0.20 - rnd.uniform(0, 0.10), z))
    # 조립해 둔 선로 한 토막 (가운데 앞 바닥): 타르 먹인 침목 넷에 레일 둘을 개못으로 박았다 — 굴에서 밟고 온 그 선로 (벽에 세우면 사다리로 보여 눕혔다)
    M = _T(0.20, -D + 0.12, 0, 4); R = M.to_3x3(); at = lambda *p: M @ Vector(p)
    for sx in (-0.3, 0.3): _ext(P("RAIL_RUST", "rust"), _RAIL, at(sx, 0, 0.10), at(sx, 1.5, 0.10))
    for s in (0.15, 0.55, 0.95, 1.35):
        box(sl, at(rnd.uniform(-0.02, 0.02), s, 0.05), (0.85, 0.15, 0.10), R)
        for sx in (-1, 1): box(k, at(sx * 0.362, s, 0.118), (0.028, 0.035, 0.036), R)
    wh = P("WHEEL_R", "iron")   # 그 선로 위에 올려 둔 여분 광차 바퀴 축 한 벌 (안쪽 턱이 레일 안쪽에 걸린다)
    for sx in (-1, 1):
        _lathe(wh, M @ Matrix.Translation((sx * 0.26, 0.75, 0.35)) @ RY(sx * 90), [(0.04, -0.02), (0.18, -0.02), (0.18, 0.0), (0.155, 0.012), (0.15, 0.085), (0.115, 0.085), (0.105, 0.05), (0.065, 0.05), (0.065, 0.11), (0.04, 0.11)], 20)
    _rod(P("AXLE_R", "rust"), at(-0.42, 0.75, 0.35), at(0.42, 0.75, 0.35), 0.037, 12)
    # 침목 더미 (오른쪽 뒤): 세 개씩 세 켜 + 뒤쪽에 둘. 앞 턱에 큰 메가 누워 있다
    px = 0.60
    for L in range(4):
        for j in range(3 if L < 3 else 2):
            box(sl, (px + rnd.uniform(-0.05, 0.05), -0.17 - 0.17 * j + rnd.uniform(-0.008, 0.008), 0.055 + 0.11 * L), (1.0, 0.15, 0.11), Matrix.Rotation(D2R(rnd.uniform(-1.2, 1.2)), 3, "Z"))
    _rod(P("HANDLE_R", "timber"), (px - 0.40, -0.48, 0.352), (px + 0.38, -0.53, 0.375), 0.02); box(k, (px + 0.38, -0.53, 0.376), (0.09, 0.24, 0.09), Matrix.Rotation(D2R(-4), 3, "Z"))
    # 이음판 궤짝 (오른쪽 앞): 구멍 넷 뚫린 쇠판이 차곡차곡 + 테에 걸친 것 · 앞에 기대 세운 것
    M = _T(W - 0.42, -D + 0.55, 0, 8); _crate(P("CRATE", "plank"), M); fp = P("FISHPLATE", "rust")
    for i in range(10): _fishplate(fp, F, M @ Matrix.Translation((rnd.uniform(-0.06, 0.06), rnd.uniform(-0.1, 0.1), 0.059 + 0.018 * i)) @ Matrix.Rotation(rnd.uniform(-0.3, 0.3), 4, "Z"))
    _fishplate(fp, F, M @ Matrix.Translation((0.12, -0.05, 0.27)) @ RY(-38) @ RX(90))
    _fishplate(fp, F, M @ Matrix.Translation((0.20, -0.235, 0.16)) @ RZ(-15) @ RX(72) @ RY(90))
    # 개못 통 (작은 나무 통에 쇠 테 둘, 뚜껑 없이 개못이 삐죽삐죽 솟았다)
    Mk = _T(W - 0.35, -1.25); _lathe(P("KEG_R", "plank"), Mk, [(0.12, 0), (0.15, 0.12), (0.155, 0.20), (0.15, 0.28), (0.12, 0.40), (0.105, 0.40), (0.105, 0.30)], 12, sharp=0.9)
    for z in (0.07, 0.33): _lathe(P("IRON_R", "iron"), Mk, [(0.139, z - 0.02), (0.146, z), (0.139, z + 0.02)], 12, caps=False, sharp=9)
    _lathe(P("IRON_R", "iron"), Mk, [(0.10, 0.30), (0.06, 0.345), (0.02, 0.355)], 12, sharp=9)
    for i in range(6):
        g = 1.05 * i + 0.3; c = Mk @ Vector((0.055 * math.cos(g), 0.055 * math.sin(g), 0.385)); box(k, c, (0.016, 0.016, 0.15), Matrix.Rotation(rnd.uniform(-0.4, 0.4), 3, "X") @ Matrix.Rotation(rnd.uniform(-0.4, 0.4), 3, "Y"))
        box(k, c + Z * 0.07, (0.035, 0.022, 0.014), Matrix.Rotation(g, 3, "Z"))


# ───────────────────────── 관 칸 ─────────────────────────
def _pipe(bm, F, p0, p1, r=0.057, fr=0.10, seg=14, ends=(True, True), bore=0.25, t=0.02):
    """양 끝에 플랜지 달린 곧은 관 (닫힌 덩어리 하나). ends = 끝이 뚫려 속이 보이는가 (p0 쪽, p1 쪽). p1 쪽이 None 이면 플랜지 없이 막힌 끝 (벽에 닿아 안 보이는 쪽)"""
    p0, p1 = Vector(p0), Vector(p1); M = _ax(p0, p1 - p0); L = (p1 - p0).length; ri = r - 0.008
    _lathe(bm, M, ([(ri, bore), (ri, 0)] if ends[0] else []) + [(fr, 0), (fr, t), (r, t)] + ([(r, L)] if ends[1] is None else [(r, L - t), (fr, L - t), (fr, L)]) + ([(ri, L), (ri, L - bore)] if ends[1] else []), seg)
    if ends[0]: _mouth(F, M, 0, 1, r, fr, bore, seg)
    if ends[1]: _mouth(F, M, L, -1, r, fr, bore, seg)


def _elbow(bm, F, M, r=0.057, Rb=0.19, seg=12, open0=False):
    """90도 굽은 관: 플랜지(자리표 z = 0)에서 +z 로 올라가 +x 로 꺾인다"""
    h = 0.06; pts = [(0, 0, 0), (0, 0, h)] + [(Rb * (1 - math.cos(D2R(q))), 0, h + Rb * math.sin(D2R(q))) for q in (22.5, 45, 67.5, 90)] + [(Rb + h, 0, h + Rb)]
    sweep(bm, [M @ Vector(p) for p in pts], r, seg, caps=False); _flange(bm, F, M, 0, 1, r, seg=seg, open_=open0)
    _flange(bm, F, M @ Matrix.Translation((Rb + h, 0, h + Rb)) @ RY(90), 0, -1, r, seg=seg)


def _valve(P, F, M):
    """게이트 밸브: 양쪽 플랜지로 바닥에 서 있다. 관 방향 = 자리표 x, 손잡이 바퀴가 위"""
    b = P("PIPE_R", "rust"); k = P("IRON_R", "iron"); Mz = M @ Matrix.Translation((0, 0, 0.10)); Mx = Mz @ RY(90)
    _lathe(b, Mx @ Matrix.Translation((0, 0, -0.15)), [(0.057, 0), (0.075, 0.06), (0.09, 0.15), (0.075, 0.24), (0.057, 0.30)], 12, caps=False, sharp=9)
    _flange(b, F, Mx, -0.15, 1, 0.057); _flange(b, F, Mx, 0.15, -1, 0.057)
    _lathe(b, Mz, [(0.06, 0.07), (0.06, 0.12), (0.095, 0.12), (0.095, 0.145), (0.05, 0.145), (0.035, 0.30), (0.02, 0.30)], 12)   # 뚜껑 몸: 볼트 테 + 목
    _rod(k, Mz @ Vector((0, 0, 0.30)), Mz @ Vector((0, 0, 0.47)), 0.011); _wheel(k, Mz @ Matrix.Translation((0, 0, 0.45)), 0.13)


def _pipes(P, F, mats, rnd, W, D):
    p = P("PIPE_R", "rust"); p2 = P("PIPE_BLACK_R", "iron"); t = P("TIMBER", "timber_old"); k = P("IRON_R", "iron"); cx = -W + 0.60; zs = 0.177; dz = 0.204
    # 받침목 둘 + 말뚝 넷 사이에 쌓은 관: 뚫린 끝(플랜지 구멍)이 통로를 본다. 켜 사이에 굄 각목 (플랜지끼리 안 겹치게 한 뼘 띄웠다). 검은 칠 관이 섞였다
    for y in (-0.6, -D + 0.6):
        box(t, (cx, y, 0.06), (1.12, 0.12, 0.12))
        for sx in (-1, 1): box(t, (cx + sx * 0.50, y + 0.10, 0.45), (0.08, 0.08, 0.9))
        for L in (1, 2): box(t, (cx, y, zs + 0.102 + dz * (L - 1)), (0.92 - 0.2 * (L - 1), 0.06, 0.09))
    for L, (n, c0) in enumerate(((4, 1.5), (3, 1.0), (2, 0.5))):
        for i in range(n):
            x = cx + (i - c0) * 0.215; z = zs + dz * L
            _pipe(p2 if (L + i) % 3 == 1 else p, F, (x, -D + 0.10 + rnd.uniform(0, 0.10), z), (x, -0.10 - rnd.uniform(0, 0.10), z), ends=(True, None))
    # 굽은 관 둘 (하나는 플랜지로 서 있고 하나는 누웠다) · 밸브 · 바닥에 놓인 손잡이 바퀴
    _elbow(p, F, _T(0.42, -D + 0.50, 0, -70)); _elbow(p2, F, _T(W - 0.55, -D + 0.30, 0.10, 20) @ RX(-90), open0=True)
    _valve(P, F, _T(W - 0.55, -1.25, 0, 25)); _wheel(k, _T(0.30, -1.25, 0.014), 0.19, 0.014, 3)
    # 이음쇠 선반 (오른쪽 뒤): 옆 널 둘 + 선반 석 장. 아래 칸에 플랜지 더미, 가운데 칸에 T 이음관 · 플랜지 더미
    for x in (0.17, 0.93): box(t, (x, -0.25, 0.625), (0.03, 0.36, 1.25))
    for z in (0.40, 0.85, 1.235): box(t, (0.55, -0.25, z), (0.79, 0.36, 0.03))
    for x, z, n, bm in ((0.36, 0.415, 2, p2), (0.74, 0.415, 2, p), (0.34, 0.865, 2, p)):
        for i in range(n): _lathe(bm, _T(x + rnd.uniform(-0.012, 0.012), -0.26 + rnd.uniform(-0.012, 0.012), z + 0.023 * i), [(0.10, 0), (0.10, 0.021)], 12)
    _flange(p, F, _T(0.34, -0.26, 0.932), 0, -1, 0.057)
    M = _T(0.71, -0.25, 0.965, 6); _pipe(p2, F, M @ Vector((-0.17, 0, 0)), M @ Vector((0.17, 0, 0)), seg=12, ends=(False, False))   # T 이음관: 눕힌 몸 + 통로 쪽으로 난 가지
    _lathe(p2, M @ RX(90), [(0.057, 0.03), (0.057, 0.13), (0.10, 0.13), (0.10, 0.15)], 12)
    # 가는 관 셋: 발은 바닥, 허리가 선반 윗 모서리에 걸쳐 비스듬히 기댔다
    for i, fx in enumerate((W - 0.20, W - 0.12, W - 0.04)):
        p0 = Vector((fx, -0.34 + 0.09 * i, 0.012)); d = (Vector((0.985, p0.y + 0.03, 1.262)) - p0).normalized()
        _rod(p if i != 1 else p2, p0, p0 + d * 1.83, 0.03)


# ───────────────────────── 쇠줄 칸 ─────────────────────────
def _reel(P, F, M, R=0.55, w=0.5, t=0.045, rope_r=0.41, turns=8, faces=(-1, 1)):
    """나무 얼레 (케이블 드럼): 축 = 자리표 z, 가운데 = 원점. 둥근 옆 판 둘 (널 이음 금 · 축 구멍 · 볼트 머리는 faces 쪽 옆 판에만) + 감긴 쇠줄 (rope_r = 0 이면 빈 얼레 — 가운데 통만)"""
    fl = P("REEL_R", "timber_old"); k = P("BOLT", "iron"); q = M.to_3x3()
    for s in (-1, 1):
        a0 = s * w / 2; n = q @ Vector((0, 0, s)); _lathe(fl, M, [(R, a0), (R, a0 + s * t)], 28)
        if s not in faces: continue
        zf = a0 + s * (t + 0.002); F.disc(M @ Vector((0, 0, zf)), n, R * 0.1, 10)
        for off in (-0.5 * R, -0.17 * R, 0.17 * R, 0.5 * R):
            h = math.sqrt(R * R - off * off) * 0.985; F.quad([M @ Vector((sx * h, off + sy * 0.004, zf)) for sx, sy in ((-1, 1), (1, 1), (1, -1), (-1, -1))], n)
        for i in range(4):
            g = math.pi / 2 * i + 0.4; c = M @ Vector((R * 0.6 * math.cos(g), R * 0.6 * math.sin(g), a0 + s * t)); cyl(k, c, c + n * 0.02, 0.025, 6)
    if not rope_r: _lathe(fl, M, [(R * 0.4, -w / 2), (R * 0.4, w / 2)], 12, caps=False); return
    d = w / turns; prof = [(rope_r - 0.014, -w / 2)]
    for i in range(turns): prof += [(rope_r + 0.012, -w / 2 + (i + 0.5) * d), (rope_r - 0.014, -w / 2 + (i + 1) * d)]
    _lathe(P("ROPE_R", "iron"), M, prof, 16, caps=False, sharp=9)


def _coil(bm, M, R, w, h, r, seg=18):
    """철사로 묶어 둔 쇠줄 타래: 단면이 네모난 도넛, 바깥 옆 · 윗면에 줄 가닥 골이 돈다. 축 = 자리표 z, 밑 = 0, R = 바깥 반지름, w · h = 단면 너비 · 높이, r = 줄 반지름"""
    nh = max(2, round(h / (2 * r))); nw = max(2, round(w / (2 * r))); prof = [(R - w, 0), (R - 0.4 * r, 0)]
    for i in range(nh): prof += [(R, (2 * i + 1) * h / (2 * nh)), (R - 0.4 * r, (2 * i + 2) * h / (2 * nh))]
    for i in range(nw): prof += [(R - (2 * i + 1) * w / (2 * nw), h + 0.4 * r), (R - (2 * i + 2) * w / (2 * nw), h)]
    _lathe(bm, M, prof + [prof[0]], seg, caps=False, sharp=9)


def _rope(P, F, mats, rnd, W, D):
    # 굄 쐐기로 받친 얼레 (왼쪽 뒤): 축을 비스듬히 돌려 옆 판과 감긴 줄이 함께 보인다. 기름 먹은 새 줄이라 검다
    a = Vector((math.cos(D2R(-35)), math.sin(D2R(-35)), 0)); c = Vector((-W + 0.62, -0.74, 0.55)); roll = Vector((-a.y, a.x, 0)); _reel(P, F, _ax(c, a))
    ch = P("CHOCK", "timber"); base = Vector((c.x + a.x * 0.2725, c.y + a.y * 0.2725, 0))
    for s in (-1, 1): _wedge(ch, Matrix.Translation(base + roll * (s * 0.33)) @ (roll * -s).to_track_quat("X", "Z").to_matrix().to_4x4())
    # 바닥의 묵은 쇠줄 타래 둘: 가는 줄 가닥이 여러 바퀴 돈 묶음 + 위에 비뚤게 풀린 고리 + (큰 것은) 묶은 철사 셋
    co = P("ROPE_OLD_R", "rust"); ci = P("ROPE_R", "iron"); tie = P("NOCOL_ROPE_TIE_R", "iron")
    M1 = _T(-0.55, -D + 0.68); _coil(co, M1, 0.44, 0.13, 0.10, 0.016, 18)
    _loop(co, M1 @ Matrix.Translation((0.025, -0.02, 0.121)) @ RX(2) @ RY(-1.5), 0.39, 0.016, 18)
    for g in (0.5, 2.6, 4.7): torus(tie, M1 @ Vector((0.375 * math.cos(g), 0.375 * math.sin(g), 0.058)), (-math.sin(g), math.cos(g), 0), 0.08, 0.007, 10, 3)
    M2 = _T(0.18, -D + 0.34); _coil(co, M2, 0.27, 0.10, 0.08, 0.016, 14); _loop(co, M2 @ Matrix.Translation((0.02, -0.01, 0.10)) @ RX(3), 0.24, 0.016, 14)
    # 도르래 바퀴 (가운데 뒤): 깊은 줄 홈이 파인 테 + 구멍 다섯 뚫린 얇은 판 + 축 통. 벽에 비스듬히 돌려 기대 홈이 통로에서 보인다
    Rs = 0.40; Ms = _rest(0.20, Rs, 0.05, 14, 35); q = Ms.to_3x3()
    _lathe(P("SHEAVE_R", "iron"), Ms, [(0.035, -0.07), (0.085, -0.07), (0.085, -0.012), (Rs - 0.10, -0.012), (Rs - 0.07, -0.05), (Rs, -0.05), (Rs - 0.055, 0), (Rs, 0.05), (Rs - 0.07, 0.05), (Rs - 0.10, 0.012), (0.085, 0.012), (0.085, 0.07), (0.035, 0.07)], 20)
    for s in (-1, 1):
        F.disc(Ms @ Vector((0, 0, s * 0.072)), q @ (Z * s), 0.035, 10)
        for i in range(5): g = 2 * math.pi / 5 * i + 0.3; F.disc(Ms @ Vector((0.19 * math.cos(g), 0.19 * math.sin(g), s * 0.014)), q @ (Z * s), 0.055, 8)
    # 타래 걸이 (오른쪽 뒤): 기둥 둘 + 가로 널 + 굵은 나무 못 둘. 묵은 쇠줄 타래와 삼 밧줄 타래가 못에 걸려 늘어져 있다
    t = P("RACK", "timber_old")
    for x in (0.70, W - 0.07): box(t, (x, -0.10, 0.85), (0.08, 0.08, 1.70))
    box(t, ((0.70 + W - 0.07) / 2, -0.10, 0.03), (W - 0.07 - 0.70, 0.10, 0.06)); box(t, ((0.70 + W - 0.07) / 2, -0.155, 1.55), (W - 0.07 - 0.70 + 0.08, 0.03, 0.14))
    for x, bm, r, w in ((0.86, ci, 0.012, 0.05), (1.22, P("ROPE_HEMP_R", "cloth"), 0.017, 0.07)):   # 타래 = 가닥 골이 도는 묶음 (못에 걸려 세로로 늘어졌다) + 겉에 풀린 고리 하나
        box(t, (x, -0.27, 1.56), (0.04, 0.24, 0.04), Matrix.Rotation(D2R(-10), 3, "X"))
        Mh = _hang((x, -0.20, 1.585 - (0.17 - w) * 1.35), (0, -1, 0), 1.35, rnd.uniform(-0.1, 0.1)); _coil(bm, Mh, 0.17, w, 0.07, r, 14)
        _loop(bm, Mh @ Matrix.Translation((rnd.uniform(-0.01, 0.01), -0.012, 0.085)) @ RX(rnd.uniform(-3, 3)), 0.165, r, 14)
    # 눕혀 둔 빈 얼레 (오른쪽 앞) 위에 굵은 고무 전기 케이블 타래
    Mc = _T(W - 0.65, -D + 0.85, 0.22, 250); _reel(P, F, Mc, 0.42, 0.35, 0.045, 0, faces=(1,)); cb = P("CABLE_R", "rubber")
    for i in range(4): _loop(cb, Mc @ Matrix.Translation((0.03 + rnd.uniform(-0.015, 0.015), rnd.uniform(-0.015, 0.015), 0.242 + 0.04 * (i // 2))) @ RX(rnd.uniform(-2, 2)), 0.27 - 0.05 * (i % 2), 0.024, 14)


# ───────────────────────── 바람 관 칸 ─────────────────────────
def _roll(P, F, M, r, L, ends=(0,), seg=14):
    """납작하게 눌러 돌돌 만 천 바람 관 한 토막, 철사 두 줄로 묶었다. 축 = 자리표 z (0 .. L). ends = 소용돌이 금(말린 켜)을 그릴 끝 (0 · 1)"""
    _lathe(P("ROLL_R", "cloth"), M, [(r - 0.025, 0), (r, 0.03), (r * 1.03, L / 2), (r, L - 0.03), (r - 0.025, L)], seg)
    for a in (0.2 * L, 0.8 * L): _lathe(P("ROLL_TIE_R", "iron"), M, [(r * 1.012 + 0.005, a - 0.011), (r * 1.012 + 0.005, a + 0.011)], seg, caps=False)
    for e in ends:
        z = -0.002 if e == 0 else L + 0.002; n = M.to_3x3() @ Vector((0, 0, -1 if e == 0 else 1)); N = 18
        ring = [(0.03 + (r - 0.07) * i / N, 2 * math.pi * 2.25 * i / N) for i in range(N + 1)]
        for (r0, g0), (r1, g1) in zip(ring, ring[1:]):
            F.quad([M @ Vector((rr * math.cos(g), rr * math.sin(g), z)) for rr, g in ((r0 - 0.005, g0), (r0 + 0.005, g0), (r1 + 0.005, g1), (r1 - 0.005, g1))], n)


def _fan(P, F, M):
    """작은 국부 선풍기 (여분 — 선풍기 방 것과 같은 칠): 나팔 입 달린 통 · 날개 · 썰매 받침 · 등의 접속함과 늘어진 전선 · 들 고리 둘. 축 = 자리표 x, 빨아들이는 입 = −x. 원점 = 통 가운데 아래 바닥"""
    zc, Rc, L = 0.46, 0.34, 0.80; R = M.to_3x3(); at = lambda *p: M @ Vector(p); Mx = M @ Matrix.Translation((-L / 2, 0, zc)) @ RY(90); q = Mx.to_3x3()
    prof = [(Rc + 0.07, 0), (Rc, 0.09), (Rc, L - 0.03), (Rc + 0.04, L - 0.03), (Rc + 0.04, L), (Rc - 0.015, L), (Rc - 0.015, 0.09), (Rc + 0.055, 0)]
    _lathe(P("FAN_R", "steel_paint"), Mx, prof + [prof[0]], 16, caps=False)
    _lathe(P("IRON_R", "iron"), Mx, [(0.04, 0.05), (0.12, 0.10), (0.13, 0.18), (0.13, 0.60)], 12)                # 가운데 통 (모터 자리)
    bl = P("FAN_BLADE", "bare")
    for i in range(6): g = math.pi / 3 * i + 0.3; box(bl, Mx @ Vector((0.225 * math.cos(g), 0.225 * math.sin(g), 0.22)), (0.20, 0.11, 0.008), q @ Matrix.Rotation(g, 3, "Z") @ Matrix.Rotation(D2R(35), 3, "X"))
    for i in range(3): g = 2 * math.pi / 3 * i + 0.5; box(bl, Mx @ Vector((0.225 * math.cos(g), 0.225 * math.sin(g), 0.50)), (0.21, 0.012, 0.05), q @ Matrix.Rotation(g, 3, "Z"))   # 통을 잡는 살
    sk = P("FAN_SKID", "rust")
    for sy in (-1, 1): box(sk, at(0, sy * 0.24, 0.04), (0.95, 0.08, 0.08), R)
    for sx in (-1, 1): box(sk, at(sx * 0.25, 0, 0.16), (0.04, 0.56, 0.16), R)
    k = P("FAN_BOX", "iron"); box(k, at(0.10, 0, zc + Rc + 0.04), (0.20, 0.15, 0.09), R)                            # 등에 붙은 접속함
    for sx in (-1, 1): torus(P("IRON_R", "iron"), at(sx * 0.27, 0, zc + Rc + 0.03), R @ Vector((0, 1, 0)), 0.04, 0.009, 10, 3)
    cb = P("NOCOL_FAN_CABLE_R", "rubber")   # 전선: 접속함에서 통 옆구리를 타고 내려와 바닥을 따라가다 둥글게 사려져 있다
    sweep(cb, [at(*v) for v in ((0.10, 0.07, 0.845), (0.10, 0.19, 0.765), (0.10, 0.315, 0.635), (0.10, 0.36, 0.46), (0.08, 0.37, 0.20), (0.02, 0.41, 0.014), (-0.35, 0.45, 0.014), (-0.70, 0.41, 0.014))], 0.012, 10)
    for i in range(2): _loop(cb, M @ Matrix.Translation((-0.80, 0.33 - 0.02 * i, 0.011 + 0.02 * i)), 0.11, 0.012, 12)


def _duct(P, F, mats, rnd, W, D):
    # 말아 둔 천 바람 관 더미 (왼쪽 뒤): 셋 위에 둘, 제 무게로 납작하게 눌렸다. 끝면(말린 켜의 소용돌이)이 통로를 본다
    r = 0.20; x0 = -W + 0.22
    for i, (x, z) in enumerate(((x0, 0.17), (x0 + 0.42, 0.17), (x0 + 0.84, 0.17), (x0 + 0.21, 0.46), (x0 + 0.63, 0.46))):
        _roll(P, F, Matrix.Translation((x, -1.10 - rnd.uniform(0, 0.06), z)) @ RX(-90) @ Matrix.Diagonal((1, 0.85, 1, 1)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z"), r, 0.92)
    # 반쯤 풀린 두루마리 (왼쪽 앞): 납작한 천 띠가 통로 쪽 바닥에 펴져 있다 — 가장자리에 매다는 쇠 고리 구멍이 줄지어 있다 (통나무가 아니라 말린 천임이 보이게)
    xr, yr = -W + 0.10, -D + 0.78; cl = P("ROLL_FLAP", "cloth")
    _roll(P, F, Matrix.Translation((xr, yr, 0.14)) @ RY(90), 0.14, 0.90, ends=(1,))
    box(cl, (xr + 0.45, yr - 0.38, 0.012), (0.90, 0.76, 0.024)); box(cl, (xr + 0.45, yr - 0.735, 0.03), (0.90, 0.05, 0.036))
    for i in range(6): F.disc((xr + 0.84, yr - 0.10 - 0.11 * i, 0.0245), Z, 0.02, 6)
    # 작은 선풍기 (가운데 뒤): 나팔 입과 날개가 통로를 본다
    _fan(P, F, _T(0.32, -0.60, 0, 84))
    # 살 든 주름 관 한 토막 (오른쪽 뒤): 통로 쪽 입이 뚫려 속이 들여다보인다 — 선풍기 방에서 본 그 관. 검은 조임 띠 셋
    x = W - 0.33; M = _ax((x, -1.45, 0.30), (0, 1, 0)); n = 8; pit = 1.2 / n; prof = [(0.286, 0.5), (0.286, 0), (0.30, 0)]
    for i in range(n): prof += [(0.262, (i + 0.5) * pit), (0.30, (i + 1) * pit)]
    _lathe(P("DUCT_R", "cloth"), M, prof, 14, sharp=1.2); F.disc((x, -1.45 + 0.496, 0.30), (0, -1, 0), 0.29, 14)
    for a in (0.016, 4 * pit, 8 * pit - 0.016): _lathe(P("DUCT_BAND_R", "iron"), M, [(0.306, a - 0.016), (0.306, a + 0.016)], 14, caps=False)
    # 쇠 테 더미 (오른쪽 앞, 주름 관 입 앞): 바람 관을 둥글게 잡는 테 — 주름 관과 같은 굵기. 여섯이 비뚤비뚤 포개 쌓였다
    hp = P("NOCOL_HOOP_R", "iron"); hx, hy = 0.55, -D + 0.52
    for i in range(6): j = 0.03 if i < 5 else 0.08; torus(hp, (hx + rnd.uniform(-j, j), hy + rnd.uniform(-j, j), 0.014 + 0.027 * i), Z, 0.30, 0.014, 18, 3)


# ───────────────────────── 연장 칸 ─────────────────────────
def _shovel(P, f, d, L):
    """각삽: 자루 끝이 바닥, 날이 위. 날 = 납작한 판 + 양 옆 · 어깨 테"""
    q = _upf(d); k = P("TOOL_HEAD", "iron"); c = f + d * (L - 0.15)
    _rod(P("HANDLE_R", "timber"), f, f + d * (L - 0.30), 0.018); _rod(P("TOOL_R", "iron"), f + d * (L - 0.42), f + d * (L - 0.27), 0.021, 10, 0.028)
    for v in box(k, c, (0.23, 0.012, 0.30), q):   # 날 끝 두 귀를 죽인다 (네모 판으로 보이지 않게)
        if (v.co - c).dot(d) > 0: v.co -= (q @ X) * (v.co - c).dot(q @ X) * 0.45
    box(k, c + q @ Vector((0, -0.02, -0.144)), (0.23, 0.04, 0.012), q)
    for sx in (-1, 1): box(k, c + q @ Vector((sx * 0.109, -0.02, -0.07)), (0.012, 0.04, 0.16), q)


def _pick(P, f, d, L, yaw=30):
    """곡괭이: 자루 끝이 바닥, 양 끝이 뾰족하게 휜 쇠 머리가 위"""
    q = _upf(d) @ Matrix.Rotation(D2R(yaw), 3, "Z"); k = P("TOOL_HEAD", "iron"); c = f + d * (L - 0.03)
    _rod(P("HANDLE_R", "timber"), f, f + d * L, 0.018, 10, 0.024); box(k, c, (0.07, 0.05, 0.06), q)
    sweep(k, [c + q @ Vector((s, 0, -0.10 * (s / 0.3) ** 2)) for s in (-0.30, -0.2, -0.1, 0, 0.1, 0.2, 0.30)], 0.02, 4, r_fn=lambda i: 0.008 + 0.014 * (1 - abs(i - 3) / 3))


def _tools(P, F, mats, rnd, W, D):
    # 연장 걸이 (왼쪽 뒤): 기둥 둘 + 허리의 홈 널 (뒤 널 · 앞 띠 · 칸막이 토막 — 자루가 홈에 끼워져 선다) + 윗 널 + 발 받침 틀. 삽 둘 · 지렛대 둘 · 곡괭이 둘 · 큰 메, 윗 널에 활톱
    t = P("RACK", "timber_old"); k = P("TOOL_HEAD", "iron"); x0, x1 = -W + 0.04, -0.06; xm = (x0 + x1) / 2; wr = x1 - x0 + 0.08; l = math.atan2(0.11, 0.72)
    for x in (x0, x1): box(t, (x, -0.14, 0.8), (0.08, 0.08, 1.6)); box(t, (x, -0.27, 0.02), (0.07, 0.31, 0.04)); box(t, (x, -0.24, 0.72), (0.08, 0.06, 0.07))
    box(t, (xm, -0.195, 0.72), (wr, 0.03, 0.12)); box(t, (xm, -0.285, 0.72), (wr, 0.03, 0.07)); box(t, (xm, -0.085, 1.48), (wr, 0.03, 0.12)); box(t, (xm, -0.385, 0.02), (wr, 0.04, 0.04))
    for x in (x0 + 0.29, x0 + 0.49, x0 + 0.71, x0 + 0.89, x0 + 1.06): box(t, (x, -0.24, 0.72), (0.025, 0.06, 0.05))
    def stand(x): dl = l + rnd.uniform(-0.01, 0.01); return Vector((x, -0.34, 0.004)), Vector((rnd.uniform(-0.015, 0.015), math.sin(dl), math.cos(dl))).normalized()
    _shovel(P, *stand(x0 + 0.16), 1.45); _shovel(P, *stand(x0 + 0.42), 1.38)
    for x, L in ((x0 + 0.55, 1.55), (x0 + 0.61, 1.42)): f, d = stand(x); _rod(P("TOOL_R", "iron"), f, f + d * L, 0.013)
    _pick(P, *stand(x0 + 0.81), 0.90); _pick(P, *stand(x0 + 0.97), 0.86)
    f, d = stand(x0 + 1.15); _rod(P("HANDLE_R", "timber"), f, f + d * 0.85, 0.018); box(k, f + d * 0.85, (0.20, 0.075, 0.075), _upf(d))
    sx = x0 + 0.95; zb = 1.21; y = -0.118   # 활톱: 모난 쇠 활 + 넓은 톱날, 윗 널의 못에 걸렸다
    sweep(P("NOCOL_SAW_BOW_R", "iron"), [(sx - 0.30, y, zb), (sx - 0.30, y, zb + 0.10), (sx - 0.20, y, zb + 0.24), (sx + 0.20, y, zb + 0.24), (sx + 0.30, y, zb + 0.10), (sx + 0.30, y, zb)], 0.013, 10)
    box(P("NOCOL_SAW_BLADE", "bare"), (sx, y, zb + 0.02), (0.60, 0.004, 0.05)); box(t, (sx, -0.13, zb + 0.217), (0.02, 0.06, 0.02))
    # 작업대 (오른쪽 뒤): 두꺼운 널 석 장 + 다리 넷 + 아래 선반. 위에 바이스 · 손으로 돌리는 숫돌 · 망치, 선반에 궤짝
    bx, by = W - 0.70, -0.42; b = P("BENCH", "plank")
    for i in range(3): box(b, (bx + rnd.uniform(-0.01, 0.01), by + (i - 1) * 0.2, 0.825), (1.3, 0.195, 0.05))
    for sx_ in (-1, 1):
        for sy in (-1, 1): box(t, (bx + sx_ * 0.57, by + sy * 0.23, 0.40), (0.08, 0.08, 0.80))
        box(t, (bx + sx_ * 0.57, by, 0.18), (0.05, 0.40, 0.06))
    box(t, (bx, by - 0.2825, 0.75), (1.22, 0.025, 0.10)); box(b, (bx, by, 0.2225), (1.14, 0.50, 0.025)); _crate(P("CRATE", "timber_old"), _T(bx + 0.25, by, 0.235, 4), 0.42, 0.3, 0.2)
    M = _T(bx - 0.42, by - 0.20, 0.85); at = lambda *p: M @ Vector(p); v = P("VICE", "iron"); br = P("BARE", "bare")   # 바이스 (검은 주물): 받침 · 뒤 턱 · 앞 턱 · 미끄럼 쇠 · 나사 손잡이, 턱 물림 면은 닳아 반짝인다
    box(v, at(0, 0, 0.02), (0.17, 0.20, 0.04)); box(v, at(0, 0.045, 0.115), (0.14, 0.07, 0.15)); box(v, at(0, -0.075, 0.125), (0.14, 0.05, 0.13)); box(v, at(0, -0.04, 0.08), (0.06, 0.27, 0.05))
    for yy in (0.006, -0.046): box(br, at(0, yy, 0.178), (0.14, 0.008, 0.025))
    _rod(P("IRON_R", "iron"), at(0, -0.175, 0.08), at(0, -0.205, 0.08), 0.022); _rod(P("BARE_R", "bare"), at(0, -0.19, 0.19), at(0, -0.19, -0.05), 0.008)
    M = _T(bx + 0.38, by - 0.17, 0.85); at = lambda *p: M @ Vector(p)                                    # 손 숫돌: 대에 물린 받침 + 톱니 집 + 돌 바퀴 하나 + 돌리는 손잡이 (전기 없이 쓴다)
    box(v, at(0, 0, 0.02), (0.08, 0.11, 0.04)); box(v, at(0, 0, 0.10), (0.05, 0.05, 0.16)); _rod(P("IRON_R", "iron"), at(-0.05, 0, 0.21), at(0.05, 0, 0.21), 0.06, 12)
    _rod(P("BARE_R", "bare"), at(-0.14, 0, 0.21), at(0.13, 0, 0.21), 0.011); _rod(P("STONE_R", "concrete"), at(-0.135, 0, 0.21), at(-0.095, 0, 0.21), 0.11, 14)
    box(br, at(0.122, 0, 0.145), (0.012, 0.028, 0.16)); _rod(P("HANDLE_R", "timber"), at(0.125, 0, 0.08), at(0.215, 0, 0.08), 0.016)
    _rod(P("HANDLE_R", "timber"), (bx - 0.2, by - 0.02, 0.868), (bx + 0.08, by + 0.05, 0.868), 0.014); box(k, (bx + 0.08, by + 0.05, 0.87), (0.04, 0.11, 0.04), Matrix.Rotation(0.245, 3, "Z"))
    # 연장통 (작업대 앞 바닥): 가운데 손잡이 막대 달린 나무 통에 망치 · 정 자루가 삐져나와 있다
    M = _T(bx - 0.05, -D + 0.85, 0, -15); R = M.to_3x3(); at = lambda *p: M @ Vector(p); tb = P("TOTE", "plank"); Mi = M.inverted()
    box(tb, at(0, 0, 0.0125), (0.56, 0.22, 0.025), R)
    for s in (-1, 1):
        box(tb, at(0, s * 0.10, 0.085), (0.56, 0.02, 0.13), R)
        for vt in box(tb, at(s * 0.2675, 0, 0.15), (0.025, 0.22, 0.30), R):   # 끝 널: 위로 갈수록 좁아진다
            lc = Mi @ vt.co
            if lc.z > 0.2: lc.y *= 0.3; vt.co = M @ lc
    _rod(P("HANDLE_R", "timber"), at(-0.28, 0, 0.26), at(0.28, 0, 0.26), 0.016)
    _rod(P("HANDLE_R", "timber"), at(-0.12, -0.04, 0.03), at(-0.02, 0.05, 0.36), 0.013); box(k, at(-0.02, 0.05, 0.36), (0.11, 0.035, 0.035), R)
    for x in (0.08, 0.15): _rod(P("TOOL_R", "iron"), at(x, 0.04, 0.03), at(x + 0.04, -0.03, 0.30), 0.009)
    # 장작 모탕에 깊이 찍어 둔 도끼 (앞 왼쪽) — 동발 따는 연장. 모탕은 껍질 벗긴 통나무 토막 (윗면에 나이테 심 · 갈라진 금)
    sx, sy = -W + 0.65, -D + 0.75; lg = _Logs(); lg.add((sx, sy, 0), (sx, sy, 0.45), 0.22, 0.19, 12, rnd)
    u = Vector((math.cos(D2R(-25)), math.sin(D2R(-25)), 0)); hd = (u * 0.6 - Z * 0.8).normalized(); dh = (u * 0.8 + Z * 0.6).normalized(); hc = Vector((sx - 0.03, sy, 0.45)) - hd * 0.045
    for vt in box(k, hc, (0.20, 0.04, 0.09), Matrix((hd, dh.cross(hd), dh)).transposed()):
        if (vt.co - hc).dot(hd) > 0: vt.co -= dh.cross(hd) * (vt.co - hc).dot(dh.cross(hd)) * 0.8   # 날 쪽이 얇아진다
    _rod(P("HANDLE_R", "timber"), hc - dh * 0.05, hc + dh * 0.52, 0.017)
    return lg.objs(mats, "STORE_STUMP", "STORE_STUMP_END")


# ───────────────────────── 기름 칸 ─────────────────────────
def _drum(bm, k, M, R=0.29, H=0.88, seg=16, g=0.0):
    """200 리터 쇠 드럼통: 구름 테 두 줄 + 위아래 테 + 살짝 들어간 뚜껑 + 뚜껑의 큰 마개 · 작은 마개 (k 에, g = 큰 마개가 놓인 각). 축 = 자리표 z"""
    c = R - 0.008; prof = [(R, 0), (R, 0.03), (c, 0.04)]
    for a in (0.27, 0.56): prof += [(c, a), (R + 0.005, a + 0.02), (c, a + 0.04)]
    _lathe(bm, M, prof + [(c, H - 0.04), (R, H - 0.03), (R, H), (R - 0.016, H), (R - 0.02, H - 0.018)], seg)
    for s, r in ((1, 0.032), (-1, 0.018)): p = Vector((s * 0.19 * math.cos(g), s * 0.19 * math.sin(g), 0)); _rod(k, M @ (p + Z * (H - 0.02)), M @ (p + Z * (H + 0.006)), r)


def _tin(P, M, key):
    """말통 (18 리터 네모 깡통): 몸 + 위아래 이음 테 + 활 손잡이 + 구석의 굵은 마개"""
    b = P("CAN_" + key.upper(), key); h = P("TIN", "bare"); R = M.to_3x3(); at = lambda *p: M @ Vector(p)
    box(b, at(0, 0, 0.175), (0.235, 0.235, 0.33), R)
    for z in (0.006, 0.344): box(b, at(0, 0, z), (0.247, 0.247, 0.012), R)
    box(h, at(-0.03, -0.03, 0.39), (0.11, 0.02, 0.01), R @ Matrix.Rotation(D2R(45), 3, "Z"))
    for s in (-1, 1): box(h, at(-0.03 + s * 0.035, -0.03 + s * 0.035, 0.368), (0.012, 0.02, 0.04), R @ Matrix.Rotation(D2R(45), 3, "Z"))
    _rod(P("TIN_R", "bare"), at(0.07, 0.07, 0.35), at(0.07, 0.07, 0.39), 0.03)


def _drums(P, F, mats, rnd, W, D):
    dp = P("DRUM_PAINT_R", "steel_paint"); dr = P("DRUM_RUST_R", "rust"); db = P("DRUM_BLACK_R", "iron"); k = P("IRON_R", "iron"); tn = P("TIN_R", "bare"); cl = P("RAG", "cloth"); hb = P("TIN", "bare")
    # 세워 둔 드럼통 셋 (회색 칠 · 녹슨 것 · 검은 것): 하나엔 큰 깔때기가 꽂혀 있고, 하나엔 주둥이 긴 기름 주전자가 얹혀 있고, 하나엔 걸레가 걸쳐 있다
    (x1, y1), (x2, y2), (x3, y3) = (-W + 0.33, -0.38), (-W + 0.95, -0.36), (-W + 0.65, -0.93)
    _drum(dp, k, _T(x1, y1), g=2.2); _drum(dr, k, _T(x2, y2), g=0.6); _drum(db, k, _T(x3, y3), g=1.2)
    _lathe(tn, _T(x3 + 0.19 * math.cos(1.2), y3 + 0.19 * math.sin(1.2), 0.80), [(0.015, 0), (0.018, 0.12), (0.14, 0.26), (0.14, 0.275), (0.128, 0.268), (0.014, 0.13)], 12)   # 깔때기 (큰 마개 구멍에 꽂혔다, 속이 파였다)
    M = _T(x2 - 0.06, y2 - 0.07, 0.862, 205); at = lambda *p: M @ Vector(p)                                                                    # 기름 주전자
    _lathe(tn, M, [(0.08, 0), (0.085, 0.015), (0.085, 0.12), (0.035, 0.17), (0.025, 0.19)], 12)
    sweep(tn, [at(0.07, 0, 0.06), at(0.16, 0, 0.14), at(0.30, 0, 0.27)], 0.012, 10, r_fn=lambda i: (0.014, 0.011, 0.007)[i])
    box(hb, at(-0.115, 0, 0.10), (0.012, 0.022, 0.11), M.to_3x3())
    for z in (0.05, 0.15): box(hb, at(-0.098, 0, z), (0.045, 0.022, 0.012), M.to_3x3())
    box(cl, (x1 + 0.05, y1 - 0.19, 0.888), (0.20, 0.22, 0.014), Matrix.Rotation(0.2, 3, "Z")); box(cl, (x1 + 0.03, y1 - 0.298, 0.775), (0.20, 0.014, 0.24), Matrix.Rotation(0.06, 3, "Y"))
    # 눕혀서 받침 틀에 올린 드럼통 (회색 칠): 다리 넷 + 가로 각목 둘 + 굄 쐐기 넷. 앞 뚜껑 아래 마개에 꼭지, 그 밑 바닥에 기름 받는 들통
    cx = W - 0.62; zc = 0.69; yb = -0.50; cr = P("CRADLE", "timber_old"); Md = Matrix.Translation((cx, yb, zc)) @ RX(90)
    _drum(dp, k, Md, g=D2R(-90))
    for y in (yb - 0.20, yb - 0.68):
        box(cr, (cx, y, 0.36), (0.80, 0.08, 0.08))
        for s in (-1, 1):
            box(cr, (cx + s * 0.34, y, 0.16), (0.08, 0.08, 0.32)); _wedge(P("CHOCK", "timber"), Matrix.Translation((cx + s * 0.27, y, 0.40)) @ RZ(180 if s > 0 else 0), 0.22, 0.08, 0.16)
    for s in (-1, 1): box(cr, (cx + s * 0.34, yb - 0.44, 0.14), (0.05, 0.50, 0.07))
    p = Md @ Vector((0, -0.19, 0.88)); Y = Vector((0, 1, 0))
    _rod(tn, p - Y * 0.004, p - Y * 0.12, 0.018); _rod(tn, p - Y * 0.105, p - Y * 0.105 - Z * 0.075, 0.015)
    box(hb, p - Y * 0.07 + Z * 0.035, (0.014, 0.014, 0.04)); box(hb, p - Y * 0.07 + Z * 0.06, (0.10, 0.016, 0.014))
    _lathe(tn, _T(cx, p.y - 0.105), [(0.10, 0), (0.13, 0.22), (0.12, 0.22), (0.092, 0.012)], 12); F.disc((cx, p.y - 0.105, 0.07), Z, 0.097, 12)
    # 말통 셋 (가운데 앞) + 기름걸레 통 (반 자른 드럼통): 테에 걸쳐 늘어진 걸레들 · 안에 구겨 넣은 더미 · 바닥에 떨어진 한 장
    _tin(P, _T(-0.55, -D + 0.80, 0, 6), "steel_paint"); _tin(P, _T(-0.27, -D + 0.72, 0, -14), "rust"); _tin(P, _T(-0.42, -D + 0.45, 0, 31), "bare")
    M = _T(0.30, -D + 0.40, 0, -9); R = M.to_3x3(); at = lambda *p: M @ Vector(p); Rb = 0.29; c = Rb - 0.008
    _lathe(dr, M, [(Rb, 0), (Rb, 0.03), (c, 0.04), (c, 0.25), (Rb + 0.005, 0.27), (c, 0.29), (c, 0.41), (Rb, 0.42), (Rb, 0.44), (c - 0.012, 0.44), (c - 0.012, 0.33)], 16)   # 반 자른 드럼통 (기름걸레 통)
    _lathe(P("RAG_R", "cloth"), M, [(c - 0.014, 0.33), (0.20, 0.40), (0.07, 0.46)], 12, sharp=9)                                                              # 안에 구겨 넣은 걸레 더미
    for g, w, ln in ((-1.75, 0.20, 0.26), (-1.05, 0.15, 0.15), (-2.6, 0.16, 0.19), (0.3, 0.17, 0.22)):   # 테에 걸쳐 밖으로 늘어진 걸레
        q = R @ Matrix.Rotation(g + math.pi / 2, 3, "Z"); o = Vector((math.cos(g), math.sin(g), 0))
        box(cl, at(*(o * (Rb - 0.07) + Z * 0.452)), (w, 0.20, 0.014), q @ Matrix.Rotation(rnd.uniform(-0.12, 0.12), 3, "Z")); box(cl, at(*(o * (Rb + 0.018) + Z * (0.455 - ln / 2))), (w * 0.9, 0.014, ln), q @ Matrix.Rotation(rnd.uniform(-0.1, 0.1), 3, "Y"))
    for i in range(3): g = 2.2 * i + 0.4; box(cl, at(0.10 * math.cos(g), 0.10 * math.sin(g), 0.45 + 0.012 * i), (0.19, 0.15, 0.02), R @ Matrix.Rotation(g, 3, "Z") @ Matrix.Rotation(rnd.uniform(-0.35, 0.35), 3, "X"))
    box(cl, at(-0.45, -0.02, 0.007), (0.26, 0.20, 0.014), R @ Matrix.Rotation(0.5, 3, "Z")); box(cl, at(-0.42, 0.0, 0.02), (0.13, 0.15, 0.014), R @ Matrix.Rotation(-0.3, 3, "Z"))
    # "화기엄금" 판: 발 달린 말뚝 둘에 못 박은 흰 널, 빨간 글씨 (기름 두는 곳에 실제로 붙는 판)
    sg = P("SIGN_POST", "timber_old")
    for x in (-0.12, 0.44): box(sg, (x, -0.085, 0.88), (0.06, 0.06, 1.76)); box(sg, (x, -0.18, 0.03), (0.09, 0.24, 0.06))
    box(P("SIGN", "white"), (0.16, -0.126, 1.62), (0.70, 0.02, 0.24))
    return [text_mesh("NOCOL_STORE_SIGN_TEXT", "화기엄금", (0.16, -0.138, 1.575), 0.13, mats["red"], extrude=0.0)]


_KINDS = {"rails": _rails, "pipes": _pipes, "rope": _rope, "duct": _duct, "tools": _tools, "drums": _drums}


def fill(mats, kind, width=3.4, depth=2.4, seed=0):
    """칸 하나에 든 물건 (kind 는 _KINDS 의 이름). 다 만든 뒤 칸 밖으로 나간 것이 있으면 로그에 알린다 (width · depth 를 줄였을 때)"""
    rnd = random.Random("%s%d" % (kind, seed)); P = _Parts("STORE_"); F = _Flat(); W = width / 2 - 0.25
    out = _KINDS[kind](P, F, mats, rnd, W, depth) or []
    out += _out(P, mats)
    if len(F.bm.faces): out.append(_obj("NOCOL_STORE_DARK", F.bm, mats["black"], F.out))
    co = [o.matrix_world @ v.co for o in out for v in o.data.vertices]; lo = [min(c[i] for c in co) for i in range(3)]; hi = [max(c[i] for c in co) for i in range(3)]
    if lo[0] < -W - 0.005 or hi[0] > W + 0.005 or lo[1] < -depth - 0.005 or hi[1] > -0.045 or lo[2] < -0.03 or hi[2] > 1.9:
        print("STORE_STALLS 칸 밖으로 나감: %s lo %s hi %s (x ±%.2f, y %.2f .. -0.05, z 0 .. 1.9)" % (kind, [round(v, 3) for v in lo], [round(v, 3) for v in hi], W, -depth))
    return out
