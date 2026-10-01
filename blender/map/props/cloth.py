"""천 소품: 광차에 덮어씌운 거적(tarp) + 석탄 자루 더미(sacks).
옛 거적은 굳은 판 세 장이라 회색 상자로 읽혔다 → 이어진 천 한 장: 위는 덩이 위에 얹혀 울퉁불퉁, 테에서 꺾여 네 옆으로 늘어지고,
모서리는 고깔처럼 벌어지며 끝자락 높이가 들쭉날쭉, 한 모서리는 걷어 올려져 광차 옆이 보인다. 줄이 지나는 자리는 천이 조여진다. 천 시뮬레이션은 쓰지 않는다(식으로 만든다 — 늘 같은 모양)."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
from _util import box, cyl, sweep, torus, obj

CLEAR = 0.03    # 짐 상자와 천 사이 틈
HEM_MIN = 0.39  # 끝자락이 이보다 낮게 내려오지 않는다 (바퀴 · 레일 위)

def _drape_fn(L, W, H, drop, seed):
    """천 자리표 (a, b) → 공간 점. lift = 천 겉에서 바깥으로 띄우는 양 (줄)"""
    r = random.Random(seed); p = [r.uniform(0, 6.28) for _ in range(6)]
    hx, hy = L / 2 + CLEAR, W / 2 + CLEAR
    k = min(1.0, (H + 0.028 - HEM_MIN) / (1.25 * drop))   # 짐이 낮으면 늘어짐을 줄인다 (바닥 · 바퀴에 안 닿게)
    fx, fy = [(1, -1), (-1, -1), (1, 1), (-1, 1)][seed % 4]   # 걷어 올린 모서리
    ropes = (-0.2 * L, 0.2 * L + 0.04)
    def f(a, b, lift=0.0):
        sa, sb = (1 if a >= 0 else -1), (1 if b >= 0 else -1)
        ex, ey = max(abs(a) - hx, 0.0), max(abs(b) - hy, 0.0); ac, bc = max(-hx, min(hx, a)), max(-hy, min(hy, b))
        # 위: 가운데가 살짝 꺼지고 석탄 덩이 자리만 볼록 (짐 윗면보다 늘 2 cm 넘게 위)
        rim = max(abs(ac) / hx, abs(bc) / hy) ** 4
        zt = H + 0.028 + 0.03 * rim + 0.045 * (0.5 + 0.5 * math.sin(6.1 * ac + p[0]) * math.sin(7.3 * bc + p[1])) ** 2
        if ex == 0 and ey == 0: return Vector((ac, bc, zt + lift))
        d = max(ex, ey) + 0.25 * min(ex, ey); th = math.atan2(ey, ex); t = d / drop
        w = 0.5 + 0.5 * math.sin(12.5 * ac + 11.1 * bc + p[2]); w2 = 0.5 + 0.5 * math.sin(4.3 * ac - 5.9 * bc + p[3])
        cin = 1 - 0.9 * max(math.exp(-((ac - x0) / 0.09) ** 2) for x0 in ropes)   # 줄이 지나는 자리는 천이 짐에 붙게 조여진다
        g = math.exp(-((ac - fx * hx) / 0.36) ** 2 - ((bc - fy * hy) / 0.3) ** 2)   # 걷어 올린 모서리에 가까운 정도
        # 세로 주름: 끝자락으로 갈수록 깊어지고, 모서리에서는 고깔처럼 벌어진다. 걷어 올린 자리는 천이 뭉쳐 불룩하다
        out = d * (0.03 + cin * (0.32 * w * w + 0.08 * w2) + 0.17 * (1 - 0.7 * g) * math.sin(2 * th)) + 0.08 * g * math.sin(math.pi * min(t, 1.0)) ** 2 + lift
        hn = 0.5 + 0.5 * math.sin(2.3 * ac - 1.9 * bc + 1.7 * th + p[4])
        zd = d * k * (1 - 0.2 * hn * t) * (1 - 0.62 * g)   # 끝자락 높이 들쭉날쭉 (0.15 쯤) + 한 모서리는 걷혀 광차 옆이 드러난다
        return Vector((ac + sa * math.cos(th) * out, bc + sb * math.sin(th) * out, zt - zd))
    return f, hx, hy, ropes

def tarp(mats, L=1.8, W=0.85, H=1.3, seed=0, drop=0.75):
    """L x W x H 짐(광차) 위에 덮인 거적. 원점 = 짐 가운데 아래 바닥, 긴 쪽 = X"""
    f, hx, hy, ropes = _drape_fn(L, W, H, drop, seed)
    sk = [0.09, 0.3, 0.55, 0.8, 1.0]                           # 늘어진 부분의 줄 (테 바로 아래를 촘촘히 — 둥글게 꺾인다)
    def line(h, n): return [-h - drop * s for s in reversed(sk)] + [-h + 2 * h * i / n for i in range(n + 1)] + [h + drop * s for s in sk]
    A, B = line(hx, 18), line(hy, 10)
    bm = bmesh.new(); V = [[bm.verts.new(f(a, b)) for b in B] for a in A]   # 이어진 천 한 장 (자르거나 접지 않는다 — 접은 판은 굳은 종이로 읽혔다)
    for i in range(len(A) - 1):
        for j in range(len(B) - 1): bm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1]))
    o = obj("TARP", bm, mats["cloth"], smooth=True, per_m=0.6)
    m = o.modifiers.new("t", "SOLIDIFY"); m.thickness = 0.01; m.offset = 0.0   # 두께 1 cm — 걷힌 모서리 아래에서 안쪽 면이 보인다
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); o.modifiers.clear(); old = o.data; o.data = me; bpy.data.meshes.remove(old)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    # 동여맨 줄 2가닥: 천을 누르며 위를 넘어 양 옆 끝자락까지, 끝자락 고리에 매듭 짓고 남은 끝은 아래로 늘어진다 (허공에서 끊기지 않는다)
    bm = bmesh.new()
    for n, x0 in enumerate(ropes):
        bs = [-hy - drop * 0.9 + (2 * hy + 2 * drop * 0.9) * i / 16 for i in range(17)]
        pts = [f(x0 + 0.012 * math.sin(4 * b + n), b, 0.014) for b in bs]
        for q, s in ((pts[0], -1), (pts[-1], 1)):
            sweep(bm, [q + Vector((0, 0, 0.03)), q + Vector((0, s * 0.012, -0.035))], 0.028, seg=6)   # 매듭
            sweep(bm, [q, q + Vector((0.02, s * 0.02, -0.08)), q + Vector((0.035, s * 0.012, max(0.36 - q.z, -0.2)))], 0.012, seg=5)   # 늘어진 끝
        sweep(bm, pts, 0.012, seg=5)
    rope = obj("NOCOL_TARP_ROPE", bm, mats["rubber"], smooth=True)
    return [o, rope]

# 자루 한 개의 단면 (길이 비율, 반 너비, 반 높이): 꿰맨 밑 → 불룩한 몸 → 묶은 목 → 벌어진 주둥이 귀
_SACK = [(0.0, .19, .012), (0.04, .21, .06), (0.12, .222, .095), (0.28, .228, .11), (0.5, .23, .112), (0.68, .225, .108),
         (0.8, .20, .095), (0.87, .13, .07), (0.915, .05, .042), (0.94, .036, .034), (0.965, .07, .04), (1.0, .14, .02)]

def _sack(bm, M, sag, droop, r, seg=12, Ls=0.75, tie=None):
    """베개 꼴 자루. sag = 가운데가 꺼지는 양, droop = 양 끝이 처지는 양"""
    ph = r.uniform(0, 6.28); fat = r.uniform(0.9, 1.08); rings = []
    for t, w, h in _SACK:
        u = 2 * t - 1; ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg; ca, sa = math.cos(a), math.sin(a)
            y = w * math.copysign(abs(ca) ** 0.77, ca); z = h * fat * math.copysign(abs(sa) ** 0.77, sa)
            if z < 0: z *= 0.6                                   # 밑은 눌려 판판하다
            z *= 1 + 0.10 * math.sin(3 * a + 7 * t + ph)         # 속에 든 덩이 때문에 고르지 않은 겉
            ring.append(bm.verts.new(M @ Vector((u * Ls / 2, y, z - sag * (1 - u * u) - droop * u * u))))
        rings.append(ring)
    for A, B in zip(rings, rings[1:]):
        for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    if tie is not None: torus(tie, M @ Vector((0.88 * Ls / 2, 0, -droop * 0.77)), M.to_3x3() @ Vector((1, 0, 0)), 0.04, 0.013, seg=8, sub=4)   # 목을 묶은 검은 끈

def sacks(mats, n=5, seed=0):
    """석탄 자루 더미: 바닥에 둘 나란히, 그 위에 가로로 하나, 옆에 하나 기대고, 맨 위에 하나. 원점 = 더미 가운데 아래 바닥"""
    r = random.Random(seed); D = math.radians
    lay = [((0.0, -0.235, 0.066), 5, 0, 0, 0), ((0.03, 0.235, 0.066), 174, 0, 0, 0),          # (자리, 돌림, 기울임, 꺼짐, 처짐)
           ((-0.03, 0.0, 0.225), 96, 0, 0.03, 0), ((0.64, 0.03, 0.17), 183, -20, 0, 0), ((-0.06, 0.02, 0.375), 22, 0, 0, 0.06)]
    for i in range(5, n):                                       # 여섯째부터는 둘레 바닥에 눕힌다
        a = 2.1 * i; lay.append(((-0.8 * math.cos(a) - 0.1, 0.85 * math.sin(a), 0.066), math.degrees(a) + 80, 0, 0, 0))
    bm = bmesh.new(); tb = bmesh.new()
    for (loc, yaw, pitch, sag, droop) in lay[:n]:
        M = Matrix.Translation(loc) @ Matrix.Rotation(D(yaw + r.uniform(-6, 6)), 4, "Z") @ Matrix.Rotation(D(pitch), 4, "Y") @ Matrix.Rotation(D(r.uniform(-4, 4)), 4, "X")
        _sack(bm, M, sag, droop, r, tie=tb)
    return [obj("SACKS", bm, mats["cloth"], smooth=True, per_m=1.2), obj("NOCOL_SACK_TIE", tb, mats["rubber"], smooth=True)]

def build(mats):
    """본보기: 광차 대신 세운 녹슨 쇠 통(테 · 갈빗대 · 대차 · 바퀴 — 본보기에만 쓴다)에 거적 + 옆에 자루 더미"""
    L, W, H = 1.8, 0.85, 1.3
    bm = bmesh.new(); box(bm, (0, 0, (H + 0.42) / 2), (L - 0.05, W - 0.05, H - 0.42)); box(bm, (0, 0, H - 0.03), (L, W, 0.06))   # 통 + 윗테
    for x in (-0.875, -0.45, 0, 0.45, 0.875): box(bm, (x, 0, (H + 0.42) / 2), (0.05, W, H - 0.42))                              # 세로 갈빗대
    box(bm, (0, 0, 0.37), (L * 0.85, W * 0.72, 0.1))                                                                             # 대차
    for x in (-0.5, 0.5):
        for y in (-0.3, 0.3): cyl(bm, (x, y - 0.04, 0.16), (x, y + 0.04, 0.16), 0.16, seg=12)                                   # 바퀴
    out = [obj("DEMO_BOX", bm, mats["rust"])]
    out += tarp(mats, L, W, H)
    s = sacks(mats)
    for o in s: o.matrix_world = Matrix.Translation((2.1, -0.1, 0)) @ o.matrix_world
    return out + s
