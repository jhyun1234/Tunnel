"""ORE-1 탄층 조각 도형 (결 덩이 무리 · 캘 덩이 · 틈 · 굴러 나온 덩이). make_ore.py(부스 맵 · 후보 그림)와 scene_mock.py(MAP4 석탄 자리)가 같이 쓴다.
불러도 아무것도 안 한다 (make_ore.py 는 불러오는 순간 장면을 비운다 — 그래서 도형만 여기로 뺐다)."""
import bmesh, math, random
from mathutils import Vector, Matrix
import mine_props as mp

UP = Vector((0, 0, 1))
DIP = math.radians(30)                                         # 띠 기울기 (사용자 09-27)
BAND_HALF, RECESS = 0.6, 0.03                                  # 띠 두께 1.2 m (한국 평균 1.4 · 사진 1.2~1.4) · 후보 그림만: 석탄이 3 cm 들어감(무른 쪽이 먼저 떨어짐 — 우리 판단)
LOOSE = (0.30, 0.18, 0.22)                                     # 캘 덩이: 결 방향 길이 · 깊이 · 폭 (지금 덩이 27 × 18 × 22 와 비슷)

def frame(along):
    """벽 안의 띠 방향 BU · 띠에 수직 BN (along = 벽을 향해 섰을 때 오른쪽, 수평)"""
    return along * math.cos(DIP) + UP * math.sin(DIP), -along * math.sin(DIP) + UP * math.cos(DIP)

def block(bm, c, ax, size, jit, rnd):
    """모난 덩이: 상자 모서리 8 점을 jit 만큼 흔든 볼록 껍질 (삼각형 12). ax = (길이 축, 바깥 축, 폭 축)"""
    pts = [bm.verts.new(c + sum((a * (s_ * sz / 2 + rnd.uniform(-jit, jit)) for a, s_, sz in zip(ax, sg, size)), Vector()))
           for sg in [(a, b, d) for a in (-1, 1) for b in (-1, 1) for d in (-1, 1)]]
    r = bmesh.ops.convex_hull(bm, input=pts)
    bmesh.ops.delete(bm, geom=[g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)], context="VERTS")

def hull(bm, c, ax, size, rnd):
    """모난 덩이(면 많음): 상자 모서리 8 + 면 가운데 6 점을 흔든 볼록 껍질"""
    pts = [Vector((sx, sy, sz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)] + [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    vs = [bm.verts.new(c + sum((a * (q * sz / 2 * (0.85 if p_.length > 1.2 else 1.15) * rnd.uniform(0.85, 1.1)) for a, q, sz in zip(ax, p_, size)), Vector())) for p_ in pts]
    r = bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.delete(bm, geom=[g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)], context="VERTS")

def falloff(t, d):                                             # 덩이 무리 가장자리로 갈수록 벽에 묻힘 (띠 칠과 이어지게)
    return max(0.0, 1 - (t / 0.62) ** 2 - (d / BAND_HALF) ** 2)

def place(bm, lb, gb, kind, P, along, out, surf, rnd):
    """캘 덩이 둘레의 결 덩이 무리(bm) + 캘 덩이(lb) + 틈(gb). surf(c) = c 를 벽 쪽으로 옮긴 벽 겉 점(없으면 None). 캘 덩이 가운데를 돌려준다"""
    BU, BN = frame(along); placed = skipped = 0
    def put(c2, ax, size, prot_max, jit):
        nonlocal placed, skipped
        t, d = (c2 - P).dot(BU), (c2 - P).dot(BN); w = falloff(t, d)
        if w <= 0 or rnd.random() <= 0.08 or (c2 - P).length <= 0.2: return
        prot = w * rnd.uniform(0.005, prot_max); sn = 0.08
        W = surf(c2)
        if W is None: skipped += 1; return
        block(bm, W + out * (prot - sn / 2), ax, size, jit, rnd); placed += 1
    if kind == "grid":                                         # 층(띠와 나란히) 6~12 cm · 벽돌 길이 8~20 cm · 줄마다 엇갈림
        ax = (BU, out, BN); d = -BAND_HALF
        while d < BAND_HALF:
            h = rnd.uniform(0.06, 0.12); t = -0.7 + rnd.uniform(0, 0.1)
            while t < 0.7:
                L = rnd.uniform(0.08, 0.2)
                put(P + BU * (t + L / 2) + BN * (d + h / 2), ax, (L - 0.012, 0.08, h - 0.01), 0.03, 0.008)
                t += L
            d += h
    else:                                                      # 금 방향 = 수평에서 60° (한국 사진 45~60°) — 판은 금을 따라 길쭉, 두께 3~8 cm
        cd = along * math.cos(math.radians(60)) + UP * math.sin(math.radians(60)); cn = -along * math.sin(math.radians(60)) + UP * math.cos(math.radians(60))
        ax = (cd, out, cn); s = -0.8
        while s < 0.8:
            th = rnd.uniform(0.03, 0.08); a = -0.8 + rnd.uniform(0, 0.12)
            while a < 0.8:
                L = rnd.uniform(0.12, 0.3)
                put(P + cn * (s + th / 2) + cd * (a + L / 2), ax, (L - 0.012, 0.08, th - 0.008), 0.035, 0.007)
                a += L + rnd.uniform(0, 0.02)
            s += th
    L_, D_, W_ = LOOSE                                         # 캘 덩이: 둘레(최대 3.5 cm)보다 더 — 앞면이 벽에서 9 cm, 위가 8° 들림(결 틈이 벌어짐)
    tilt = Matrix.Rotation(math.radians(8), 3, BU); axl = tuple(tilt @ a for a in ax)
    cl = surf(P) + out * (0.09 - D_ / 2)
    hull(lb, cl, axl, (L_, D_, W_), rnd)                       # 모서리 14 점 — 면이 여러 방향이라 머리등에 어느 한 면은 번쩍
    gc = cl - out * (D_ / 2 - 0.02)
    block(gb, gc, axl, (L_ * 1.25, 0.03, W_ * 1.3), 0.01, rnd)   # 벌어진 틈 = 덩이 뒤 까만 판(가장자리만 보임)
    return cl, gc, placed, skipped

def mk(name, bm, mat, origin):
    """bm(월드 좌표)을 origin 이 원점인 물체로"""
    bmesh.ops.translate(bm, vec=-origin, verts=bm.verts)
    return mp.obj(name, bm, mat, loc=origin)

def lump_bm(seed=11, size=0.2):
    """굴러 나온 탄 덩이 ~20 cm (Rk25 손에 든 15~20 · 모난 덩이): 깨진 상자 점 14 개의 볼록 껍질 (coal_heap 덩어리와 같은 방식), 원점 = 가운데"""
    rnd = random.Random(seed); bm = bmesh.new()
    pts = [Vector((sx, sy, sz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)] + [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    sq = Vector((1.0, 0.75, 0.6))
    vs = [bm.verts.new(Vector([q * s_ * size * 0.5 * rnd.uniform(0.8, 1.1) for q, s_ in zip(p_ * (0.85 if p_.length > 1.2 else 1.2), sq)])) for p_ in pts]
    r = bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.delete(bm, geom=[g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)], context="VERTS")
    return bm

def tris(objs): return sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)
