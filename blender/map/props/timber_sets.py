"""목동발 · 틀동발 (통나무 버팀틀): 틀 한 벌 · 외기둥 · 세우는 중인 자리 · 쇠동발 머리 받침 토막.
레퍼런스 공통점 (조사 11 — R02 채탄 막장 · R03 캡과 쐐기 근접 · R05 캡 위 짧은 널 · R08 쇠동발 머리 토막 · R14 보훔 통나무 틀 · R15 썩은 틀 · R17 기둥과 머리판 · R18b 묵은 틀):
  - 기둥도 캡도 "둥근 통나무" (굵기 18~22 cm). 캡은 두 기둥 머리 위에 얹히고, 캡 끝이 기둥 바깥으로 한 뼘 나온다 — 끝면의 밝은 동그라미가 보인다 (R14).
  - 통나무는 매끈한 관이 아니다: 굵기가 들쭉날쭉하고 살짝 휘었고, 옹이 자국 · 세로로 길게 갈라진 금 · 덜 벗긴 껍질과 탄가루 얼룩이 있다 (R02 · R14 · R17). 발 쪽은 젖어 검다 (R14).
  - 기둥은 위가 안으로 기운다 (R02 · R14). 굵은 쪽이 위다.
  - 기둥 머리와 캡 사이에 막 쪼갠 밝은 쐐기를 마주 박는다 — 사진에서 가장 밝은 곳이고, 두꺼운 끝이 이음 밖으로 삐져나온다 (R03).
  - 천장 널(나래기) · 가는 통나무는 캡 "위"에 굴 방향으로 걸쳐 옆 틀 캡까지 간다. 폭 · 두께가 제각각이고 끝이 들쭉날쭉하다 (R05 · R14). 캡 아래로 내려오지 않는다.
  - 묵은 틀은 잿빛이고, 금이 넓게 벌어지고, 캡이 눌려 가운데가 처지고, 널이 부러져 늘어진다 (R15 · R18b).
  - 외기둥은 머리에 켠 판자(머리판)를 가로로 얹고 그 위를 쳐서 천장에 조인다 (R17).
  - 쇠동발 머리 위에는 켜서 만든 밝은 나무 토막이 가로로 얹힌다. 윗모서리가 죽어 있다 (R08).
좌표: 굴은 x 로 뻗고 틀은 y 로 걸친다. 조각마다 원점 = 조각 가운데 아래 바닥 (head_block 만 토막 밑면 가운데).
frame 의 천장 자리: 캡 밑 = height, 그 위에 캡(20 cm)과 널이 얹혀 맨 위 = height + FRAME_TOP. 천장이 정해져 있으면 roof=천장 높이 를 준다 — 틀 전체가 그 밑에 맞춰 내려온다."""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, sweep, obj, place
from timber_store import _Logs, _wedge, _obj, wedge_box

CAP_R = 0.10        # 캡 반지름
FRAME_TOP = 0.27    # frame 맨 위(널 윗면) = height + 이 값 → 천장을 여기에 맞춘다 (또는 frame(roof=천장) 으로 틀을 천장에 맞춘다)
SINK = 0.05         # 기둥 발을 바닥 밑으로 이만큼 내린다 (발 구덩이에 세운다 — 바닥이 울퉁불퉁해도 발이 뜨지 않는다)

class _Wood(_Logs):
    """_Logs(갱목 창고와 같은 통나무)에 "손 본 통나무"를 더한다: 고리 여럿(굵기 들쭉날쭉 · 휨) + 옹이 + 세로 금 + 껍질 · 탄가루 얼룩 + 젖은 발.
    옆면은 side/old, 끝면은 end, 잿빛 표시(끝면의 심 · 얼룩 · 젖은 발)는 heart, 검은 표시(세로 금 · 옹이 눈)는 crack 모음에 담긴다 (묵은 통나무는 금도 heart 에 — 어차피 같은 검은 재질).
    share 를 주면 끝면 · 표시를 그 모음에 같이 담는다 (물체 수를 줄인다)"""
    def __init__(s, share=None):
        super().__init__(); s.shared = (); s.bm["crack"] = bmesh.new(); s.out["crack"] = []
        if share is not None:
            s.shared = ("end", "heart", "crack")
            for k in s.shared: s.bm[k].free(); s.bm[k] = share.bm[k]; s.out[k] = share.out[k]

    def trunk(s, p0, p1, r0, r1, seg=8, rnd=None, old=False, rings=5, bow=(0, 0, 0), wob=0.01, z0=None, z1=None, hearts=(True, True),
              knots=2, cracks=1, stains=2, foot=0.0, flare=1.0, cw=0.008, face=None):
        """p0 → p1 통나무. bow = 가운데가 비켜나는 양(휨), wob = 고리마다 흔들림, z0 · z1 = 발 · 머리를 그 높이로 평평하게 자른다,
        hearts = 끝면에 심 · 금을 그릴지(가려지는 끝은 안 그린다), foot = 발에서 이만큼 젖어 검다(m), flare = 머리가 눌려 퍼진 비율, cw = 금 반폭,
        face(n) = 옹이가 그쪽을 봐도 되는가. 돌려주는 것: (고리들, 이번에 생긴 점 전부)"""
        n0 = {k: len(b.verts) for k, b in s.bm.items()}
        p0, p1, bow = Vector(p0), Vector(p1), Vector(bow); ax = (p1 - p0).normalized(); q = ax.to_track_quat("Z", "Y").to_matrix()
        ph = rnd.uniform(0, 6.28); ang = lambda i: ph + 2 * math.pi * i / seg
        dirs = [q @ Vector((math.cos(ang(i)), math.sin(ang(i)), 0)) for i in range(seg)]; mid = [q @ Vector((math.cos(ang(i + 0.5)), math.sin(ang(i + 0.5)), 0)) for i in range(seg)]
        jit = [1 + rnd.uniform(-0.07, 0.07) for _ in range(seg)]   # 울퉁불퉁한 단면 (_Logs 와 같다)
        key = "old" if old else "side"; bm, h, e = s.bm[key], s.bm["heart"], s.bm["end"]; R = []
        for i in range(rings):
            t = i / (rings - 1); lat = Vector((0, 0, 0)); r = r0 + (r1 - r0) * t
            if 0 < i < rings - 1:   # 가운데 고리: 자리 · 굵기가 제각각 → 매끈한 관으로 안 보인다
                t += rnd.uniform(-0.2, 0.2) / (rings - 1); lat = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * wob; lat -= ax * lat.dot(ax)
                r = (r0 + (r1 - r0) * t) * (1 + rnd.uniform(-0.05, 0.05))
            elif i: r *= flare
            c = p0.lerp(p1, t) + bow * math.sin(math.pi * t) + lat
            R.append([bm.verts.new(c + d * (r * j * (1 + rnd.uniform(-0.02, 0.02)))) for d, j in zip(dirs, jit)])
        for ring, z in ((R[0], z0), (R[-1], z1)):
            if z is not None:
                for v in ring: v.co.z = z
        for A, B in zip(R, R[1:]):
            for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i])); s.out[key].append(mid[i])
        for ring, n, show in ((R[0], -ax, hearts[0]), (R[-1], ax, hearts[1])):   # 끝면 + 어두운 심과 갈라진 금 (_Logs 와 같은 그림)
            e.faces.new([e.verts.new(v.co) for v in ring]); s.out["end"].append(n)
            if not show: continue
            p = sum((v.co for v in ring), Vector()) / seg; r = sum((v.co - p).length for v in ring) / seg
            u, w = dirs[0], n.cross(dirs[0]); c = p + n * 0.003 + u * (r * rnd.uniform(0, 0.15)); a0 = rnd.uniform(0, 6.28)
            P = lambda a, rr: h.verts.new(c + (u * math.cos(a) + w * math.sin(a)) * rr)
            h.faces.new([P(a0 + 2 * math.pi * i / 5, r * rnd.uniform(0.3, 0.48)) for i in range(5)]); s.out["heart"].append(n)
            for _ in range(rnd.choice((1, 2, 2, 3))):
                a = rnd.uniform(0, 6.28); wd = rnd.uniform(0.08, 0.16)
                h.faces.new([P(a, r * 0.2), P(a - wd, r * 0.75), P(a + wd, r * 0.75)]); s.out["heart"].append(n)
        def on(i, k, a, b, lift=0.005):
            """겉면 위의 점: 고리 i → i+1 사이 a, 옆 모서리 k → k+1 사이 b. 겉에서 lift 만큼 띄운다 (겉과 겹쳐 깜빡이지 않게)"""
            A, B = R[i], R[i + 1]; k0, k1 = k % seg, (k + 1) % seg
            return A[k0].co.lerp(A[k1].co, b).lerp(B[k0].co.lerp(B[k1].co, b), a) + dirs[k0].lerp(dirs[k1], b).normalized() * lift
        fw = min(0.3, cw / (2 * (r0 + r1) / 2 * math.sin(math.pi / seg)))   # 금 반폭을 옆면 한 칸 폭의 비율로
        ck = "heart" if old else "crack"; g = s.bm[ck]
        for _ in range(cracks):   # 세로로 길게 갈라진 금 (말라 터진 자리 — 사진에서 통나무를 통나무로 보이게 하는 검은 줄): 고리 하나를 사이에 둔 길쭉한 마름모
            i = rnd.randrange(rings - 2); k = rnd.randrange(seg); b = rnd.uniform(0.3, 0.7)
            a, L, Rr, c = (g.verts.new(x) for x in (on(i, k, rnd.uniform(0.1, 0.55), b), on(i, k, 1.0, b - fw), on(i, k, 1.0, b + fw), on(i + 1, k, rnd.uniform(0.45, 0.9), b)))
            g.faces.new((a, L, Rr)); g.faces.new((L, c, Rr)); s.out[ck] += [mid[k % seg]] * 2
        for _ in range(stains):   # 덜 벗긴 껍질 · 탄가루 얼룩: 결을 따라 길쭉하고 양옆이 뾰족하게 빠지는 조각 (네모난 딱지로 안 보이게). 옆면 반 칸씩 n 칸
            i = rnd.randrange(rings - 1); k = rnd.randrange(seg); n = rnd.choice((2, 3, 3, 4)); ac = rnd.uniform(0.3, 0.7); hl = rnd.uniform(0.2, 0.3); col = []
            for j in range(n + 1):
                f = hl * (0.15 + 0.85 * math.sin(math.pi * (j + rnd.uniform(-0.25, 0.25)) / n) if 0 < j < n else 0.1); c = ac + rnd.uniform(-0.06, 0.06)
                col.append([h.verts.new(on(i, k + j // 2, min(max(a, 0.0), 1.0), 0.5 * (j % 2))) for a in (c - f, c + f)])
            for j in range(n): h.faces.new((col[j][0], col[j + 1][0], col[j + 1][1], col[j][1])); s.out["heart"].append(mid[(k + j // 2) % seg])
        if foot:   # 젖어 검은 발: 발에서 올라오는 띠, 윗 끝이 들쭉날쭉
            L = (R[1][0].co - R[0][0].co).length; col = [[h.verts.new(on(0, j, a, 0.0)) for a in (0.0, min(0.95, foot * rnd.uniform(0.55, 1.2) / L))] for j in range(seg)]
            for j in range(seg): h.faces.new((col[j][0], col[(j + 1) % seg][0], col[(j + 1) % seg][1], col[j][1])); s.out["heart"].append(mid[j])
        for _ in range(knots):   # 옹이: 가지를 바투 친 자리 — 납작하고 길쭉한 혹 + 어두운 눈 (못처럼 튀어나오지 않게 1 cm 안팎)
            for _try in range(8):
                k = rnd.randrange(seg)
                if face is None or face(mid[k]): break
            else: continue
            n = mid[k]; w = n.cross(ax); P0 = on(rnd.randrange(rings - 1), k, rnd.uniform(0.15, 0.85), 0.5, 0.0); rb = rnd.uniform(0.03, 0.044); hh = rnd.uniform(0.006, 0.013)
            ring = lambda o, rr: [bm.verts.new(P0 + n * o + (ax * (1.4 * math.cos(math.pi * j / 3)) + w * math.sin(math.pi * j / 3)) * rr) for j in range(6)]
            A, B = ring(-0.02, rb), ring(hh, rb * 0.55)
            for j in range(6):
                bm.faces.new((A[j], A[(j + 1) % 6], B[(j + 1) % 6], B[j])); am = math.pi * (j + 0.5) / 3; s.out[key].append(ax * math.cos(am) + w * math.sin(am) + n * 0.4)
            g.faces.new([g.verts.new(v.co + n * 0.002) for v in B]); s.out[ck].append(n)
        return R, [v for k, b in s.bm.items() for v in list(b.verts)[n0[k]:]]

    def outs(s, mats, side, ends=None, marks=None, cracks=None, end_mat="timber_end", mark_mat="timber_old"):
        """모은 것을 물체로 낸다: 옆면(새 것 · 묵은 것) / 끝면 / 잿빛 표시 / 검은 표시. 빈 모음은 버리고, 남의 모음(share)은 주인이 낸다"""
        o = []; both = len(s.bm["side"].faces) and len(s.bm["old"].faces)
        for k, nm, m, sm in (("side", side, "timber", True), ("old", side + ("_OLD" if both else ""), "timber_old", True), ("end", ends, end_mat, False), ("heart", marks, mark_mat, True), ("crack", cracks, "tar", True)):
            if k in s.shared: continue
            if len(s.bm[k].faces): o.append(_obj(nm, s.bm[k], mats[m], s.out[k], smooth=sm))
            else: s.bm[k].free()
        return o

def _M(o, x, z):
    """쐐기 자리: o = 두꺼운 끝 가운데, x = 박는 방향, z = 쐐기의 평평한 면 반대쪽"""
    x, z = Vector(x), Vector(z); y = z.cross(x)
    return Matrix(((x.x, y.x, z.x, o[0]), (x.y, y.y, z.y, o[1]), (x.z, y.z, z.z, o[2]), (0, 0, 0, 1)))

def _pair(bm, top, d, L=0.34, w=0.10, h=0.045, shift=0.04, off=0.012, H=None):
    """맞쐐기 한 쌍 (R03 — 이음에 마주 박은 쐐기 둘이 포개져 있다): top = 묶음 윗면 가운데, d = 박은 방향.
    아래 쐐기는 두꺼운 끝이 −d 쪽으로, 위 쐐기는 +d 쪽으로 삐져나온다 (옆에서 보면 뾰족한 끝과 두꺼운 끝이 엇갈려 보인다). H = 묶음 높이를 정해 줄 때. 묶음 밑면 높이를 돌려준다"""
    top, d = Vector(top), Vector(d).normalized(); sd = Vector((0, 0, 1)).cross(d); k = 2 * shift / L
    if H is not None: h = (H + 0.002 - 0.01 * (1 + k)) / (1 - k)
    H = h * (1 - k) + 0.01 * (1 + k) - 0.002   # 엇갈린 만큼 묶음이 얇아진다, 두 쐐기는 2 mm 겹친다
    _wedge(bm, _M(top - Vector((0, 0, H)) - d * (L / 2 + shift) + sd * off, d, (0, 0, 1)), L, w, h)
    _wedge(bm, _M(top + d * (L / 2 + shift) - sd * off, -d, (0, 0, -1)), L, w, h)
    return top.z - H

def _round(o):
    """옆면만 둥글게, 뚜껑(다각형)은 평평하게"""
    for p in o.data.polygons: p.use_smooth = len(p.vertices) == 4
    return o

def frame(mats, width=2.6, height=2.3, lean=0.12, lagging=4, old=False, seed=0, roof=None, bay=None):
    """틀 한 벌 (R14 · R02 · R03): 둥근 기둥 둘(발 바깥 = ±width/2, 머리가 lean 만큼 안으로) + 기둥 머리 위에 얹힌 둥근 캡(끝이 기둥 밖으로 나온다)
    + 이음마다 기둥 머리와 캡 사이에 마주 박은 쐐기 둘 + 캡 위에 굴 방향으로 걸친 천장 널 · 가는 통나무 lagging 개. 캡 밑 가운데 = height, 맨 위 = height + FRAME_TOP.
    roof = 천장 높이를 주면 height 대신 틀을 천장 밑에 맞춘다 (캡 밑 = roof − FRAME_TOP. 캡이 2.3 m 아래로 내려오면 캡은 부딪힘 없는 물체가 된다).
    bay = 옆 틀(+x 쪽)까지 거리를 주면 널이 이 캡에서 그 캡까지 걸친다 (안 주면 0.9 m 널이 캡 가운데에 얹힌다 — 0.9 m 마다 세우면 끝이 만난다).
    old = 묵은 틀: 잿빛, 금이 넓고 검다, 캡이 눌려 가운데가 5 cm 처졌다, 기둥 머리가 눌려 퍼졌다, 널 하나는 빠지고 하나는 부러져 늘어졌다, 쐐기도 잿빛"""
    rnd = random.Random(seed); rc = CAP_R; r0, r1 = 0.092, 0.102   # 기둥: 굵은 쪽이 위
    if roof is not None: height = roof - FRAME_TOP
    top = height + FRAME_TOP; legs = []
    for s in (-1, 1):
        fy = s * (width / 2 - r0 * 1.1); legs.append((s, fy, fy - s * (lean + (rnd.uniform(-0.03, 0.01) if old else rnd.uniform(-0.01, 0.01)))))
    hl = min(width / 2, max(abs(l[2]) for l in legs) + r1 + 0.14)   # 캡 끝이 기둥 바깥으로 한 뼘 (벽 속으로는 안 들어간다)
    wp = _Wood(); wc = _Wood(share=wp)   # wp = 기둥(부딪힘 있음), wc = 캡과 가는 통나무 널
    R, cap = wc.trunk((0, -hl, 0), (0, hl, 0), rc, rc * 0.94, 8, rnd, old, rings=5, bow=(0, 0, -0.05 if old else 0.008), wob=0.005,
                      knots=2, cracks=4 if old else 2, stains=4 if old else 3, cw=0.018 if old else 0.009, face=lambda n: n.z > -0.2)
    dz = height + (-0.015 if old else 0.004) - min(v.co.z for ring in R for v in ring)   # 캡 밑 가장 낮은 곳을 height 에 맞춘다 (묵은 틀은 처진 가운데가 1.5 cm 더 낮다)
    for v in cap: v.co.z += dz
    low = min(v.co.z for v in cap); assert low >= height - 0.02, "timber_sets.frame: 캡 밑이 height 보다 낮다"
    prof = [(sum(v.co.y for v in ring) / len(ring), min(v.co.z for v in ring), max(v.co.z for v in ring)) for ring in R]
    def cap_z(y, j):
        """그 자리(y)의 캡 밑(j=1) · 캡 윗등(j=2) 높이"""
        for a, b in zip(prof, prof[1:]):
            if y <= b[0] or b is prof[-1]: return a[j] + (b[j] - a[j]) * min(max((y - a[0]) / (b[0] - a[0]), 0.0), 1.0)
    bmw = bmesh.new(); clear = 0.0; zq = min(1.8, 0.78 * height)   # 사람 어깨 높이에서 기둥 사이 폭을 잰다 (낮은 막장 틀은 같은 비율 높이에서)
    for s, fy, ty in legs:
        cy = s * min(abs(ty), width / 2 - 0.25)   # 맞쐐기: 캡 축을 따라 박는다 → 굴을 걸어오면 기둥 머리와 캡 사이에 뾰족한 옆모습이 보인다 (두꺼운 끝이 통로 쪽으로 한 뼘 나온다)
        zh = _pair(bmw, (rnd.uniform(-0.01, 0.01), cy, cap_z(cy, 1) + 0.004), (0, s, 0), 0.36, 0.10, 0.06, 0.06) + 0.003
        Rp, _ = wp.trunk((rnd.uniform(-0.015, 0.015), fy, -SINK), (0, ty, zh), r0, r1, 8, rnd, old, rings=5, bow=(rnd.uniform(-0.02, 0.02), rnd.uniform(-0.01, 0.01), 0), wob=0.008,
                         z0=-SINK, z1=zh, hearts=(False, False), knots=2, cracks=4 if old else 3, stains=4 if old else 2, foot=0.5 if old else 0.32, flare=1.15 if old else 1.0, cw=0.018 if old else 0.009,
                         face=lambda n, s=s: n.y * s > -0.3)   # 옹이는 통로 쪽으로 안 나온다
        clear += min(s * (a.co.y + (b.co.y - a.co.y) * (zq - a.co.z) / (b.co.z - a.co.z)) for A, B in zip(Rp, Rp[1:]) for a, b in zip(A, B) if (a.co.z - zq) * (b.co.z - zq) <= 0 and a.co.z != b.co.z)
        if not lagging: _pair(bmw, (0, cy, top), (s, 0, 0), 0.30, 0.10, shift=0.03, H=top - cap_z(cy, 2) + 0.012)   # 널이 없으면 캡과 천장 사이를 쐐기로 조인다
    assert clear >= width - 0.7, "timber_sets.frame: 기둥 사이가 좁다 (%.2f m) — lean 을 줄인다" % clear
    ya = hl - 0.13; bm = bmesh.new()   # 천장 널: 캡 길이에 고르게, 널 토막(R05)과 가는 통나무(R14)가 번갈아. 윗면이 천장(top)에 닿는다
    drop = rnd.randrange(lagging) if old and lagging >= 3 else -1; skip = (drop + 1 + rnd.randrange(lagging - 1)) % lagging if old and lagging >= 4 else -1
    for i in range(lagging):
        y = -ya + 2 * ya * (i + 0.5) / lagging + rnd.uniform(-0.05, 0.05); zb = cap_z(y, 2) - 0.012; t = max(top - rnd.uniform(0, 0.008) - zb, 0.03)
        xa, xb = (-rnd.uniform(0.1, 0.2), bay + rnd.uniform(0.02, 0.12)) if bay else (lambda d: (d - 0.45, d + 0.45))(rnd.uniform(-0.08, 0.08))
        wd = rnd.uniform(0.15, 0.24); yaw = math.radians(rnd.uniform(-2, 2)); dy = rnd.uniform(-0.03, 0.03); sg = rnd.choice((-1, 1))
        if i == skip: continue   # 빠진 널
        if i == drop:   # 부러져 늘어진 널 (R15 · R18b): 한 끝은 캡 위에 걸려 있고 다른 끝이 24 도쯤 처졌다 (끝이 캡 밑보다 조금 위에서 멈춘다)
            a = math.radians(24); tb = min(t, 0.04); c = Vector((0, y, zb + tb / 2)) + Vector((sg * math.cos(a), 0, -math.sin(a))) * 0.2
            box(bm, c, (0.5, wd, tb), Matrix.Rotation(sg * a, 3, "Y"))
        elif i % 2: r = min(t / 2.14, 0.045); wc.add((xa, y, zb + 1.07 * r), (xb, y + dy, zb + 1.07 * r), r, r * 0.88, 8, rnd, old=old)
        else: box(bm, ((xa + xb) / 2, y, zb + t / 2), (xb - xa, wd, t), Matrix.Rotation(yaw, 3, "Z"))
    out = wp.outs(mats, "TSET_FRAME_POSTS", "NOCOL_TSET_FRAME_ENDS", "NOCOL_TSET_FRAME_MARKS", "NOCOL_TSET_FRAME_CRACKS", "timber_old" if old else "timber_end", "tar" if old else "timber_old")
    out += wc.outs(mats, ("NOCOL_" if low < 2.28 else "") + "TSET_FRAME_CAP")
    out.append(obj("NOCOL_TSET_FRAME_LAGGING", bm, mats["timber_old" if old else "plank"])) if len(bm.faces) else bm.free()
    out.append(obj("NOCOL_TSET_FRAME_WEDGES", bmw, mats["timber_old" if old else "timber_end"])); return out

def post(mats, height=2.3, seed=0, sink=SINK):
    """외기둥 (R17): 굵은 둥근 기둥(20~22 cm) + 머리판(켠 판자 0.6 x 0.2 x 0.055, y 로 걸친다) + 머리판과 천장 사이에 마주 박은 쐐기 한 쌍. 쐐기 윗면 = height (천장에 닿는다).
    sink = 발을 바닥 밑으로 내리는 깊이 (바닥 위에 그냥 놓으려면 0)"""
    rnd = random.Random(seed + 21); w = _Wood(); tx, ty = rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02); bm = bmesh.new()
    zt = _pair(bm, (tx, ty, height), (0, rnd.choice((-1, 1)), 0), 0.30, 0.09, 0.045, 0.035) + 0.002; zp = zt - 0.055 + 0.003   # 머리판 윗면 · 기둥 머리
    w.trunk((0, 0, -sink), (tx, ty, zp), 0.10, 0.112, 12, rnd, rings=5, bow=(rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), 0), wob=0.01,
            z0=-sink, z1=zp, hearts=(False, False), knots=3, cracks=2, stains=3, foot=0.35)
    out = w.outs(mats, "TSET_POST", "NOCOL_TSET_POST_ENDS", "NOCOL_TSET_POST_MARKS", "NOCOL_TSET_POST_CRACKS"); wed = obj("NOCOL_TSET_POST_WEDGES", bm, mats["timber_end"])
    bm = bmesh.new(); box(bm, (tx, ty, zt - 0.0275), (0.20, 0.60, 0.055), Matrix.Rotation(math.radians(rnd.uniform(-4, 4)), 3, "Z"))
    return out + [obj("NOCOL_TSET_POST_HEAD", bm, mats["plank"]), wed]

def head_block(mats, seed=0):
    """쇠동발 머리와 천장 사이 나무 받침 토막 (R08): 켠 토막 0.55 x 0.16 x 0.12, 윗모서리가 죽어 있다. 긴 쪽 = x.
    그 위에 밝은 쐐기 하나가 평평한 면을 아래로 하고 가로(y)로 박혀 있다 — 쐐기 두꺼운 끝 윗면 = 0.165 (천장이 닿을 곳). 원점 = 토막 밑면 가운데"""
    rnd = random.Random(seed + 31); bm = bmesh.new(); prof = ((-0.08, 0), (0.08, 0), (0.08, 0.085), (0.05, 0.12), (-0.05, 0.12), (-0.08, 0.085))
    A = [bm.verts.new((-0.275, y, z)) for y, z in prof]; B = [bm.verts.new((0.275, y, z)) for y, z in prof]
    for i in range(6): bm.faces.new((A[i], A[(i + 1) % 6], B[(i + 1) % 6], B[i]))
    bm.faces.new(A[::-1]); bm.faces.new(B)
    blk = obj("NOCOL_TSET_HEADBLOCK", bm, mats["plank"]); bm = bmesh.new(); d = rnd.choice((-1, 1))
    _wedge(bm, _M((rnd.uniform(-0.15, 0.15), -d * 0.16, 0.118), (0, d, 0), (0, 0, 1)), 0.30, 0.10, 0.047)
    return [blk, obj("NOCOL_TSET_HEADBLOCK_WEDGE", bm, mats["timber_end"])]

def raising_kit(mats, height=2.3, seed=0, standing=True):
    """틀을 세우는 중인 자리 (2.6 x 1.6 m): 머리판까지 얹어 세운 기둥 하나(쐐기 윗면 = height) · 바닥에 누운 둘째 기둥 · 받침 토막 둘 위에 걸쳐 둔 캡 통나무
    · 쐐기 상자 · 상자에 기대 세운 큰 메(R17 의 망치) · 캡에 기대 세운 활톱. 긴 쪽 = x. 보는 쪽 = +y (연장이 그쪽에 있고 통나무는 뒤에 있다)"""
    # standing=False: 천장이 높은 방(기둥 길이 2~3 m 로는 천장에 안 닿는 곳)에 놓을 때 — 기둥을 세우지 않고 머리판과 함께 눕혀 둔다 (천장에 못 닿는 선 기둥은 "아무것도 안 받치는 기둥"으로 보인다, 사용자 10-03)
    rnd = random.Random(seed + 41); rc = CAP_R; out = place(post(mats, height, seed, sink=0.0), Matrix.Translation((-1.08, 0.45, 0))) if standing else []
    w = _Wood(); cy = -0.3
    if not standing:
        R, new = w.trunk((-1.25, 0.62, 0.3), (0.05, 0.5, 0.3), 0.10, 0.112, 12, rnd, rings=5, bow=(0, 0.012, 0), wob=0.006, knots=3, cracks=2, stains=3, face=lambda n: n.z > -0.3)   # 세울 기둥 (누워 있다)
        dz = -min(v.co.z for v in new)
        for v in new: v.co.z += dz
        bm = bmesh.new(); box(bm, (-1.02, 0.18, 0.0275), (0.60, 0.20, 0.055), Matrix.Rotation(math.radians(8), 3, "Z")); out.append(obj("NOCOL_TSET_KIT_HEADBOARD", bm, mats["plank"]))   # 머리판 (바닥에)
    for x in (-0.75, 0.7): w.add((x, cy - 0.27, 0.065), (x + rnd.uniform(-0.05, 0.05), cy + 0.25, 0.065), 0.06, 0.056, 10, rnd, old=True)   # 받침 토막
    R, new = w.trunk((-1.2, cy, 0.3), (1.2, cy, 0.3), rc, rc * 0.94, 12, rnd, rings=4, bow=(0, 0.01, 0), wob=0.005, knots=2, cracks=2, stains=3, face=lambda n: n.z > -0.3)   # 캡
    dz = 0.118 - min(v.co.z for v in new); cz = sum(v.co.z for ring in R for v in ring) / sum(len(ring) for ring in R) + dz
    for v in new: v.co.z += dz
    R, new = w.trunk((-1.0, -0.62, 0.3), (1.2, -0.56, 0.3), 0.10, 0.09, 12, rnd, rings=5, bow=(0, 0.015, 0), wob=0.006, knots=3, cracks=2, stains=3, face=lambda n: n.z > -0.3 and n.y > -0.3)   # 누운 기둥
    dz = -min(v.co.z for v in new)
    for v in new: v.co.z += dz
    out += w.outs(mats, "TSET_KIT_LOGS", "NOCOL_TSET_KIT_ENDS", "NOCOL_TSET_KIT_MARKS", "NOCOL_TSET_KIT_CRACKS")
    # 쐐기 상자는 갱목 창고 것 그대로 (기대 세운 머리나무 끝이 바닥 밑으로 5 mm 내려가 있어 그만큼 올린다)
    out += place(wedge_box(mats, seed), Matrix.Translation((0.5, 0.27, 0.005)) @ Matrix.Rotation(math.pi, 4, "Z"))
    def lean_dir(p, c_y, c_z, Rr):
        """바닥의 점 p 에서 둥근 것(가운데 c_y · c_z, 반지름 Rr)의 윗등을 스치는 방향 — 자루 · 톱이 거기에 걸쳐 기댄다"""
        d = Vector((0, c_y - p.y, c_z - p.z)); a = math.atan2(d.z, d.y) - math.asin(min(Rr / d.length, 1.0)); return Vector((0, math.cos(a), math.sin(a)))
    p = Vector((0.27, 0.64, 0.045)); u = lean_dir(p, 0.47, 0.303, 0.022); bm = bmesh.new()   # 큰 메: 쇠 머리는 바닥에, 밝은 나무 자루는 상자 윗모서리에 기댔다
    cyl(bm, p - Vector((0.09, 0, 0)), p + Vector((0.09, 0, 0)), 0.045, 10); out.append(_round(obj("NOCOL_TSET_KIT_SLEDGE_HEAD", bm, mats["iron"])))
    bm = bmesh.new(); cyl(bm, p, p + u * 0.85, 0.02, 10, r1=0.017); out.append(_round(obj("NOCOL_TSET_KIT_SLEDGE_HANDLE", bm, mats["timber_end"])))
    # 활톱 (timber_store 톱질 자리와 같은 것): 톱날이 바닥에 길게(x) 닿고 활이 캡 통나무 옆구리에 기대 섰다 → +y 에서 보면 반달 모양이 정면으로 보인다
    L = 0.76; p = Vector((-0.62, cy + 0.125, 0.016)); u = lean_dir(p, cy, cz, rc * 1.07 + 0.014); X = Vector((1, 0, 0)); n = u.cross(X)
    bm = bmesh.new(); box(bm, p + X * (L / 2) + u * 0.018, (L, 0.005, 0.036), Matrix((X, n, u)).transposed()); out.append(obj("NOCOL_TSET_KIT_SAW_BLADE", bm, mats["bare"]))
    bm = bmesh.new(); sweep(bm, [p] + [p + X * (L / 2 * (1 - math.cos(math.pi * k / 8))) + u * (0.05 + 0.17 * math.sin(math.pi * k / 8)) for k in range(9)] + [p + X * L], 0.014, 10)
    out.append(obj("NOCOL_TSET_KIT_SAW_BOW", bm, mats["bare"], smooth=True)); return out

def raising_kit_front(mats, **k):
    """미리보기용: raising_kit 의 보는 쪽(+y)이 미리보기 카메라(−y 쪽에 선다)를 보게 반 바퀴 돌린 것. 맵에서는 raising_kit 을 쓴다"""
    return place(raising_kit(mats, **k), Matrix.Rotation(math.pi, 4, "Z"))

def build(mats):
    """본보기 배치: 막장 가는 길 — 0.9 m 마다 세운 틀 넷 (셋은 새 것이고 널이 옆 틀 캡까지 걸친다, 맨 안쪽은 묵은 것). 굴이 +y 로 뻗는다 (미리보기 카메라가 굴을 따라 본다)"""
    out = []
    for i in range(4): out += place(frame(mats, lagging=6, old=i == 3, seed=i, bay=0.9 if i < 3 else None), Matrix.Translation((0, 0.9 * i, 0)) @ Matrix.Rotation(math.pi / 2, 4, "Z"))
    return out
