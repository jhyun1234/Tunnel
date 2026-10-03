"""벽 소품 묶음: 가스 검정판(기둥에 삐딱하게) · 출입금지 판 · 갱내 전화 · 게시판(+ 번호표 걸이) · 구급함(+ 들것) · 기동기 상자.
벽 소품 약속: 벽면 = y 0, 소품은 −y 로 튀어나온다, x = 벽을 따라, 원점 = 벽 위 바닥 높이(z 0). 글자는 −y 쪽에서 읽힌다.
레퍼런스 공통점(R2_gas_steps 조사): 검정판은 계기가 아니라 '줄 친 양식' — 파란 판 · 흰 테두리 줄 · 왼쪽 인쇄 칸 · 오른쪽 검은 칸에 분필 글씨, 못에 철사로 걸려 삐딱하다."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, sweep, torus, obj, text_mesh, thin, FONT   # FONT = 을지로체 — 분필 글씨도 (사용자 10-03 "모든 것들을", 옛 분필 = Ink Free)
_T = lambda x=0, y=0, z=0: Matrix.Translation((x, y, z))

class _P:
    """재질마다 그물 하나로 모은다 (물체 수를 줄인다). p("iron") → bmesh. smooth = 둥근 것, nocol = 부딪힘 없음"""
    def __init__(s, mats, pre): s.m, s.pre, s.b, s.txt = mats, pre, {}, []
    def __call__(s, key, smooth=False, nocol=False): return s.b.setdefault((key, smooth, nocol), bmesh.new())
    def text(s, body, loc, size, key, tilt=0.0):
        """글자: _util.text_mesh 와 같은 방향(−y 에서 읽힘) · 같은 을지로체 · 곡선을 성기게(resolution 2 + thin)이되 두께 없이 — 한글 한 자가 수백 삼각형이 되는 것을 막는다. 만든 물체를 돌려준다"""
        name = "NOCOL_%s_T%d" % (s.pre, len(s.txt))
        cu = bpy.data.curves.new(name, "FONT"); cu.body = body; cu.size = size; cu.align_x = "CENTER"; cu.resolution_u = 2; cu.font = bpy.data.fonts.load(FONT, check_existing=True)
        t = bpy.data.objects.new(name + "_c", cu); t.location = loc; t.rotation_euler = (math.pi / 2, tilt, 0); bpy.context.scene.collection.objects.link(t); bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(t.evaluated_get(bpy.context.evaluated_depsgraph_get())); me.transform(t.matrix_world); bpy.data.objects.remove(t, do_unlink=True); thin(me)
        me.materials.clear(); me.materials.append(s.m[key]); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); s.txt.append(o); return o
    def done(s, M=None):
        out = [obj("%s%s_%s%s" % ("NOCOL_" if n else "", s.pre, k, "_r" if sm else ""), bm, s.m[k], smooth=sm) for (k, sm, n), bm in s.b.items()] + s.txt
        if M is not None:
            for o in out: o.data.transform(M)
        return out

def _rect(bm, cx, cz, w, h, y, t=0.002, deg=0.0):
    """벽과 나란한 얇은 판 (앞면 = y − t/2). deg = −y 에서 볼 때 시계 반대로 도는 각"""
    box(bm, (cx, y, cz), (w, t, h), rot=Matrix.Rotation(-math.radians(deg), 3, "Y"))

def _stroke(bm, pts, y, w=0.004):
    """분필 · 줄: (x, z) 점들을 잇는 얇은 띠"""
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        box(bm, ((ax + bx) / 2, y, (az + bz) / 2), (math.hypot(bx - ax, bz - az) + w, 0.002, w), rot=Matrix.Rotation(-math.atan2(bz - az, bx - ax), 3, "Y"))

def _wedge(bm, c, s, rz=0.0):
    """쐐기 (한쪽 끝이 얇다 — 얇은 쪽이 +x, rz 로 돌린다)"""
    vs = box(bm, (0, 0, 0), s); R = Matrix.Rotation(rz, 3, "Z")
    for v in vs:
        if v.co.x > 0: v.co.z = -s[2] / 2 + 0.006 * (1 if v.co.z > 0 else 0)
        v.co = R @ v.co + Vector(c)

def _bolts(bm, pts, y0, y1, r=0.011, seg=6):
    for x, z in pts: cyl(bm, (x, y0, z), (x, y1, z), r, seg)

def _elbow(x, y, z, n=3, deep=0.12):
    """벽을 타고 오르던 관 · 케이블이 z 높이에서 벽 속(+y)으로 직각으로 꺾여 들어가는 가운데 선 (벽에 뚫은 구멍으로 선이 넘어간다 — 허공에서 끊기지 않는다).
    벽에서 떨어진 거리(−y)가 굽은 반지름. 바위 벽은 울퉁불퉁하니 벽 속으로 deep 만큼 더 넣는다"""
    R = -y
    return [(x, -R * math.cos(a), z - R + R * math.sin(a)) for a in (math.pi / 2 * i / n for i in range(n + 1))] + [(x, deep, z)]

# ───────────────────────── 1) 가스 검정판 + 통나무 기둥 ─────────────────────────
def gas_board(mats, label_text=True, h=2.3, rows=None, warn=False):
    """원점 = 기둥 발. 기둥(굵기 0.16, 높이 2.3) 앞(−y)에 판(0.42 x 0.32, 가운데 1.45 m)이 4도 삐딱하게 걸린다.
    label_text=False 면 왼쪽 칸 글자를 흰 띠로 바꾼다 (삼각형 아끼기). h = 기둥 높이 = 놓는 자리의 천장 높이 (머리 판이 천장에 닿아야 동발로 읽힌다)
    rows = [(날짜, 시각, 측정값), …] 을 주면 판이 날마다 한 줄씩 적은 기록이 된다 (_gas_log). warn=True = 날마다 오르는 기록(rows 를 안 주면 _GAS_RISE) + 마지막 줄에 빨간 동그라미 · 분필 "출입금지".
    rows · warn 둘 다 없으면 옛 판 그대로 (어제 · 오늘 두 칸)"""
    p = _P(mats, "GASBD")
    # 기둥: 껍질 벗긴 통나무, 위가 조금 가늘고 살짝 기운다. 발 받침 판 + 쐐기, 머리 판 + 쐐기 (동발 고정 방식)
    cyl(p("timber", smooth=True), (0, 0, 0.05), (0.012, 0.004, h - 0.08), 0.085, 10, r1=0.075)
    box(p("timber_old"), (0, 0, 0.025), (0.36, 0.26, 0.05), rot=Matrix.Rotation(math.radians(8), 3, "Z"))
    _wedge(p("timber_end"), (0.15, 0.01, 0.075), (0.17, 0.08, 0.05), math.pi)
    _wedge(p("timber_end"), (-0.03, 0.0, h - 0.06), (0.30, 0.10, 0.04), math.radians(20))
    box(p("timber_old"), (0.01, 0, h - 0.02), (0.34, 0.20, 0.04), rot=Matrix.Rotation(math.radians(-6), 3, "Z"))
    out = p.done()
    # 판: 판 자리표(가운데 = 0, 뒷면 y 0)로 만든 뒤 4도 돌려 기둥 앞에 붙인다
    b = _P(mats, "GASBD_PLATE")
    if rows or warn: _gas_log(b, list(rows or _GAS_RISE), warn, label_text)
    else:
        _rect(b("steel_blue"), 0, 0, 0.42, 0.32, -0.002, 0.004)
        W = b("white")
        for cx, cz, w, h in ((0, 0.143, 0.392, 0.006), (0, -0.143, 0.392, 0.006), (-0.193, 0, 0.006, 0.292), (0.193, 0, 0.006, 0.292)): _rect(W, cx, cz, w, h, -0.005)   # 흰 테두리 줄
        b.text("가스 검정", (0, -0.0065, 0.082), 0.05, "white")
        _rect(W, 0, 0.068, 0.38, 0.004, -0.005)
        top, rh = 0.065, 0.041; rows = [top - rh * (i + 0.5) for i in range(5)]
        _rect(b("black"), 0.085, top - rh * 2.5, 0.21, rh * 5, -0.005)           # 오른쪽 검은 분필 칸
        for i in range(1, 5): _rect(W, 0, top - rh * i, 0.38, 0.003, -0.007)     # 가로 줄 (양식)
        _rect(W, -0.02, top - rh * 2.5, 0.003, rh * 5, -0.007); _rect(W, 0.085, top - rh * 2.5, 0.003, rh * 5, -0.007)   # 세로 줄: 칸 나눔 · 이틀 치 두 칸
        for z, lab in zip(rows, ("가스 CH4", "측정값 %", "날짜", "시각", "검정자")):
            if label_text: b.text(lab, (-0.105, -0.0065, z - 0.009), 0.024, "white")
            else: _rect(W, -0.105, z, 0.11 if len(lab) > 3 else 0.06, 0.009, -0.005)
        # 분필 글씨: 어제 칸 · 오늘 칸 (숫자 · 날짜 · 시각 · 휘갈긴 서명)
        C = b("chalk")
        for cx, vals, tl in ((0.0325, ("0.2", "10.1", "6:40"), 0.10), (0.1375, ("0.3", "10.2", "7:10"), -0.07)):
            _stroke(C, [(cx - 0.02, rows[0] + 0.002), (cx - 0.008, rows[0] - 0.012), (cx + 0.022, rows[0] + 0.014)], -0.008)   # 확인 표시
            for z, v in zip(rows[1:4], vals): b.text(v, (cx, -0.0095, z - 0.011), 0.032, "chalk", tilt=tl)
            s = [(-0.04, -0.008), (-0.028, 0.012), (-0.02, -0.01), (-0.008, 0.01), (0.0, -0.008), (0.012, 0.004), (0.02, -0.006), (0.042, 0.002 + tl * 0.05)]
            _stroke(C, [(cx + x, rows[4] + z) for x, z in s], -0.008, 0.0035)
    M = _T(0, -0.083, 1.45) @ Matrix.Rotation(math.radians(4), 4, "Y")
    out += b.done(M)
    # 굽은 못 + 철사 고리 (판 위 두 구멍 → 못). 판이 돌아서 철사 두 가닥 길이가 다르다
    n = _P(mats, "GASBD_HANG")
    sweep(n("iron"), [(0.012, -0.05, 1.700), (0.012, -0.112, 1.706), (0.012, -0.120, 1.728)], 0.005, 6)
    h1, h2 = (M @ Vector((-0.15, -0.006, 0.145)), M @ Vector((0.15, -0.006, 0.145)))
    sweep(n("bare", nocol=True), [h1, (0.008, -0.108, 1.713), (0.016, -0.108, 1.713), h2], 0.003, 5)
    return out + n.done()

_GAS_RISE = (("10.1", "6:40", "0.4"), ("10.2", "6:50", "0.7"), ("10.3", "7:05", "1.1"), ("10.4", "6:45", "1.6"), ("10.5", "7:10", "2.3"))   # 날마다 오르는 메탄 % (1.5 넘으면 전기를 끊고 2 넘으면 사람을 내보내고 통행을 막는다)
def _gas_log(b, rows, warn, label_text):
    """gas_board(rows=…) 의 판: 머리 줄(날짜 · 시각 · CH4 % · 비고) 아래 검은 분필 칸에 하루 한 줄. 판 위 끝(0.16)은 옛 판과 같고(철사 고리 자리) 줄이 많으면 아래로 늘어난다 (다섯 줄 = 0.42 x 0.35).
    warn = 마지막 줄 측정값에 빨간 동그라미(위험 빨강 한 값 = "red") + 비고 칸에 분필 "출입금지". 분필 글자 기울기는 random.Random("gas_board")"""
    n = len(rows); rh, hd, top = 0.041, 0.03, 0.065; z0 = top - hd; bot = z0 - rh * n; pb = min(-0.16, bot - 0.02); zb = pb + 0.017   # z0 = 머리 줄 아래 · bot = 마지막 줄 아래 · pb = 판 아래 끝
    _rect(b("steel_blue"), 0, (0.16 + pb) / 2, 0.42, 0.16 - pb, -0.002, 0.004)
    W = b("white")
    for cx, cz, w, h in ((0, 0.143, 0.392, 0.006), (0, zb, 0.392, 0.006), (-0.193, (0.143 + zb) / 2, 0.006, 0.149 - zb), (0.193, (0.143 + zb) / 2, 0.006, 0.149 - zb)): _rect(W, cx, cz, w, h, -0.005)   # 흰 테두리 줄
    b.text("가스 검정", (0, -0.0065, 0.082), 0.05, "white"); _rect(W, 0, 0.068, 0.38, 0.004, -0.005)
    xs = (-0.19, -0.105, -0.02, 0.07, 0.19); cs = [(a + c) / 2 for a, c in zip(xs, xs[1:])]   # 칸 경계 · 칸 가운데
    _rect(b("black"), 0, (z0 + bot) / 2, 0.38, z0 - bot, -0.005)                              # 검은 분필 칸
    for i in range(n + 1): _rect(W, 0, z0 - rh * i, 0.38, 0.003, -0.007)                         # 가로 줄
    for x in xs[1:4]: _rect(W, x, (top + bot) / 2, 0.003, top - bot, -0.007)                     # 세로 줄
    for x, lab in zip(cs, ("날짜", "시각", "CH4 %", "비고")):
        if label_text: b.text(lab, (x, -0.0065, z0 + hd / 2 - 0.008), 0.022, "white")
        else: _rect(W, x, z0 + hd / 2, 0.05, 0.008, -0.005)
    rnd = random.Random("gas_board")
    for i, r in enumerate(rows):
        for x, v in zip(cs, r): b.text(v, (x, -0.0095, z0 - rh * (i + 0.5) - 0.011), 0.03, "chalk", tilt=rnd.uniform(-0.08, 0.08))
    if warn:
        z, x = z0 - rh * (n - 0.5), cs[2]
        _stroke(b("red"), [(x + 0.042 * math.cos(a), z + 0.002 + 0.018 * math.sin(a)) for a in (math.radians(110 + 30 * k) for k in range(14))], -0.0105, 0.004)   # 빨간 동그라미: 한 바퀴 넘게 그어 끝이 겹친다
        b.text("출입금지", (cs[3], -0.0095, z - 0.011), 0.03, "chalk", tilt=rnd.uniform(-0.06, 0.06))

# ───────────────────────── 2) 출입금지 판 ─────────────────────────
def no_entry_plate(mats):
    """원점 = 판 뒷면 한가운데 (울타리 가로대에 못으로 박는다). 0.60 x 0.36, 흰 바탕 빨간 글씨"""
    p = _P(mats, "NOENTRY")
    _rect(p("white"), 0, 0, 0.60, 0.36, -0.003, 0.006)
    R = p("red")
    for cx, cz, w, h in ((0, 0.14, 0.52, 0.012), (0, -0.14, 0.52, 0.012), (-0.26, 0, 0.012, 0.292), (0.26, 0, 0.012, 0.292)): _rect(R, cx, cz, w, h, -0.007)
    p.text("출입금지", (0, -0.0085, -0.045), 0.125, "red")
    nails = [(sx * 0.282, sz * 0.162) for sx in (-1, 1) for sz in (-1, 1)]
    _bolts(p("iron"), nails, -0.005, -0.012, 0.009)
    for (x, z), L in zip(nails[1::2], (0.07, 0.045)): _rect(p("rust"), x + 0.002, z - 0.012 - L / 2, 0.007, L, -0.0065, 0.001)   # 못 아래 녹물 자국
    return p.done()

def _fit(o, cz, wmax):
    """글자 물체의 가운데 높이를 cz 에 맞추고, 너비가 wmax 보다 길면 그만큼 줄인다 (x 0 = 가운데)"""
    co = [v.co for v in o.data.vertices]; x0, x1, z0, z1 = min(c.x for c in co), max(c.x for c in co), min(c.z for c in co), max(c.z for c in co); k = min(1.0, wmax / (x1 - x0)); m = (z0 + z1) / 2
    for c in co: c.x *= k; c.z = cz + (c.z - m) * k

def danger_board(mats, lines=("출입금지",)):
    """막아 둔 까닭을 적은 출입금지 판 (no_entry_plate 의 여러 줄 판). 원점 = 판 뒷면 한가운데, 0.60 x (0.36 + 0.075 x (줄 수 − 1)) — 세 줄 = 0.60 x 0.51.
    흰 바탕 · 빨간 테 · 빨간 글씨(위험 빨강 한 값 = "red", no_entry_plate 와 같다). 첫 줄 = 크게(0.125), 다음 줄들 = 작게(0.055). 판 안쪽(0.48)보다 긴 줄은 그 줄만 줄인다.
    레퍼런스: 1964 광산보안법 시행규칙 제156조(쓰지 않는 갱도 = 출입 금지 경표 + 책위) · 제67조(유해 가스가 난 곳 = 경표 + 책위, 허락 없이 걷어 내지 못함).
    보기: ("출입금지", "유해가스 발생", "허가 없이 들어가지 말 것") · ("출입금지", "붕락 위험", "허가 없이 들어가지 말 것")
      — "허가 없이 들어가지 말 것" 은 제67조의 뜻을 판 글로 Claude 가 정한 문구다 (옛 경표의 실제 글이 아니다)"""
    n = len(lines); H = 0.36 + 0.075 * (n - 1); e = H / 2 - 0.04; zt = (H - 0.21) / 2
    p = _P(mats, "DANGER")
    _rect(p("white"), 0, 0, 0.60, H, -0.003, 0.006)
    R = p("red")
    for cx, cz, w, h in ((0, e, 0.52, 0.012), (0, -e, 0.52, 0.012), (-0.26, 0, 0.012, 2 * e + 0.012), (0.26, 0, 0.012, 2 * e + 0.012)): _rect(R, cx, cz, w, h, -0.007)
    for i, s in enumerate(lines): _fit(p.text(s, (0, -0.0085, 0), 0.125 if i == 0 else 0.055, "red"), zt - 0.075 if i == 0 else zt - 0.15 - 0.075 * (i - 0.5), 0.48)
    nails = [(sx * 0.282, sz * (H / 2 - 0.018)) for sx in (-1, 1) for sz in (-1, 1)]
    _bolts(p("iron"), nails, -0.005, -0.012, 0.009)
    for (x, z), L in zip(nails[1::2], (0.07, 0.045)): _rect(p("rust"), x + 0.002, z - 0.012 - L / 2, 0.007, L, -0.0065, 0.001)   # 못 아래 녹물 자국
    return p.done()

def chalk_on_boards(mats, text, w, h, seed=0, pitch=0.4, board=0.28, x0=0.0):
    """판자 울타리 앞면에 분필로 휘갈긴 큰 글씨 (보기 "출입금지" · "가스!" · "붕락") — 흰 분필("chalk"), 부딪힘 없음(NOCOL_), 물체 하나.
    원점 = 글씨 칸 한가운데, 판자 앞면 = y 0 (−y 에서 읽힌다). 글씨를 w x h 칸을 넘지 않는 가장 큰 크기로 맞춘다 (한 줄 — 보통 h 가 크기를 정한다). 글자마다 조금씩 기울고 크기 · 높이가 오르내리며 줄 전체가 살짝 비탈지고, 판자마다 1~2 cm 어긋난다.
    판자 사이 틈에 걸린 획은 잘라 낸다 (허공에 뜬 분필이 안 생기게): 판자 가운데 = x0 + k·pitch, 너비 board. 기본값 = scene_mock 울타리 FENCE(0.4 간격 · 0.28 너비, 가운데 판자가 x 0) · pitch=None = 통판.
    울타리 가로대(z 0.54~0.66 · 1.74~1.86)가 판자 앞에 있어 그 높이의 글씨는 가려진다. 흔들림 = random.Random("chalk_on_boards <seed>")"""
    rnd = random.Random("chalk_on_boards %d" % seed); bm = bmesh.new(); x = 0.0
    for ch in text:
        if ch == " ": x += 0.35 * h; continue
        o = text_mesh("CHALK_TMP", ch, (0, 0, 0), h, mats["chalk"], extrude=0.0); co = [v.co for v in o.data.vertices]
        a, c = min(q.x for q in co), max(q.x for q in co); zc = (min(q.z for q in co) + max(q.z for q in co)) / 2; k = rnd.uniform(0.88, 1.1)
        o.data.transform(_T(x + (c - a) * k / 2, 0, rnd.uniform(-0.07, 0.07) * h) @ Matrix.Rotation(rnd.uniform(-0.12, 0.12), 4, "Y") @ Matrix.Scale(k, 4) @ _T(-(a + c) / 2, 0, -zc))
        bm.from_mesh(o.data); x += (c - a) * k + 0.08 * h; me = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(me)
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(rnd.uniform(-0.05, 0.05), 4, "Y"), verts=bm.verts)          # 줄이 살짝 비탈진다
    lo, hi = [Vector([f(v.co[i] for v in bm.verts) for i in range(3)]) for f in (min, max)]; m = (lo + hi) / 2
    bmesh.ops.transform(bm, matrix=_T(0, -0.002, 0) @ Matrix.Scale(min(w / (hi.x - lo.x), h / (hi.z - lo.z)), 4) @ _T(-m.x, -m.y, -m.z), verts=bm.verts)   # 칸에 꽉 차게 · 판자 앞 2 mm
    if pitch:
        L, Rx = min(v.co.x for v in bm.verts), max(v.co.x for v in bm.verts)
        for k in range(math.floor((L - x0) / pitch) - 1, math.ceil((Rx - x0) / pitch) + 2):
            for ex in (x0 + k * pitch - board / 2, x0 + k * pitch + board / 2):
                if L < ex < Rx: bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(ex, 0, 0), plane_no=(1, 0, 0))
        kof = lambda x_: round((x_ - x0) / pitch)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.calc_center_median().x - x0 - kof(f.calc_center_median().x) * pitch) > board / 2], context="FACES")   # 틈에 걸린 조각
        dz = {}
        for v in bm.verts: v.co.z += dz.setdefault(kof(v.co.x), rnd.uniform(-0.04, 0.04) * h)   # 판자마다 조금 어긋난다 (분필이 판자 턱에서 튄다)
    me = bpy.data.meshes.new("NOCOL_CHALKBD_TEXT"); bm.to_mesh(me); bm.free(); me.materials.append(mats["chalk"])
    for p_ in me.polygons:
        if p_.normal.y > 0: p_.flip()                                                                     # 앞(−y)을 보게
    o = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(o); return [o]

# ───────────────────────── 3) 갱내 전화 ─────────────────────────
def phone(mats):
    """자석식 갱내 전화: 세로 판자 넷으로 짠 나무 뒤판 + 주물 상자(0.25 x 0.32 x 0.14) + 왼쪽 걸쇠의 송수화기 + 오른쪽 손잡이(돌려서 호출) + 위 종 두 개 + 벽 타고 오르는 전선관. 상자 가운데 z 1.45
    전선관은 벽에서 5 cm 띄운 받침 둘에 물려 올라가 z 2.35 에서 크게 굽어 둥근 벽 판의 쇠 목 구멍으로 벽 속에 들어간다 (10-03: 2.45 에서 허공에 끊겨 있었다). 2.4 위로는 아무것도 없다 — 맵에서 위로 덧대는 선이 필요 없다"""
    p = _P(mats, "PHONE"); zc = 1.45
    # 뒤판: 검은 송수화기 · 손잡이가 밝은 판자 위에 놓여야 어두운 굴에서 보인다 (사진: 송수화기는 상자 왼쪽에 세로로 걸린다). 통짜 판은 새 합판 한 장으로 읽혔다 → 세로 판자 넷, 사이 틈 · 위아래 끝이 들쭉날쭉
    for i in range(4): box(p("plank"), (-0.035 + (i - 1.5) * 0.1335, -0.015, zc - 0.03 + (0.0, 0.008, -0.006, 0.004)[i]), (0.1265, 0.03, 0.62))
    I = p("iron"); _bolts(I, [(-0.035 + sx * 0.235, zc - 0.03 + sz * 0.27) for sx in (-1, 1) for sz in (-1, 1)], -0.03, -0.04)
    S = p("steel_paint")
    box(S, (0, -0.10, zc), (0.25, 0.14, 0.32)); box(S, (0, -0.175, zc), (0.21, 0.012, 0.28))             # 상자 + 앞 뚜껑
    _bolts(I, [(sx * 0.088, zc + sz * 0.123) for sx in (-1, 1) for sz in (-1, 1)], -0.181, -0.19, 0.009)
    Ir = p("iron", smooth=True)
    for dz in (-0.09, 0.09): cyl(Ir, (-0.128, -0.168, zc + dz - 0.03), (-0.128, -0.168, zc + dz + 0.03), 0.012, 10)   # 경첩
    _rect(p("white"), 0, zc + 0.03, 0.13, 0.055, -0.182, 0.003); _rect(p("red"), 0, zc + 0.05, 0.13, 0.012, -0.184, 0.002)   # 번호 판 (뚜껑 가운데 있던 둥근 단추는 뺐다 — 무엇인지 읽히지 않았다)
    for x, z, sw, sh in ((-0.03, zc - 0.133, 0.13, 0.010), (0.088, zc + 0.07, 0.008, 0.08), (0.02, zc - 0.03, 0.008, 0.06)): _rect(p("rust"), x, z, sw, sh, -0.1815, 0.002)   # 낡음: 뚜껑 아래 턱 · 볼트 · 번호 판 밑 녹물 (뚜껑 면 안에만 — 밖으로 나가면 허공에 뜬다)
    # 호출 손잡이 (오른쪽): 굵은 축 + 납작한 쇠 팔 + 검은 쥘 곳 — 밝은 뒤판 앞에서 검은 쥘 곳이 보인다 (가는 팔 + 나무 쥘 곳은 눈에 안 띄었다)
    cyl(Ir, (0.125, -0.10, zc + 0.02), (0.172, -0.10, zc + 0.02), 0.015, 10); box(p("bare"), (0.165, -0.10, zc - 0.025), (0.008, 0.022, 0.115))
    cyl(p("rubber", smooth=True), (0.167, -0.10, zc - 0.07), (0.225, -0.10, zc - 0.07), 0.017, 10)
    # 종 두 개 + 가운데 공이 (위)
    Bz = p("bare", smooth=True); zt = zc + 0.16
    for x in (-0.062, 0.062):
        cyl(Ir, (x, -0.10, zt), (x, -0.10, zt + 0.02), 0.01, 6)
        for z0, z1, r0, r1 in ((0.015, 0.035, 0.046, 0.042), (0.035, 0.052, 0.042, 0.024), (0.052, 0.058, 0.024, 0.008)): cyl(Bz, (x, -0.10, zt + z0), (x, -0.10, zt + z1), r0, 10, r1=r1)
    cyl(Ir, (0, -0.10, zt), (0, -0.10, zt + 0.03), 0.005, 5); box(I, (0, -0.10, zt + 0.035), (0.018, 0.018, 0.018))
    # 송수화기: 옆에서 본 ㄷ 꼴이 앞에서 보인다 (손잡이 + 상자 쪽을 보는 컵 둘), 위 컵 목이 닳은 쇠 걸쇠에 얹힌다 (검은 걸쇠는 검은 송수화기에 묻혀 '옆에 그냥 붙은 것'으로 읽혔다)
    H = p("rubber", smooth=True); hy = -0.10
    sweep(H, [(-0.198, hy, zc + 0.118), (-0.214, hy, zc + 0.06), (-0.220, hy, zc + 0.005), (-0.214, hy, zc - 0.05), (-0.198, hy, zc - 0.108)], 0.021, 10)
    for z in (zc + 0.10, zc - 0.09):
        cyl(H, (-0.205, hy, z), (-0.162, hy, z), 0.022, 10); cyl(H, (-0.165, hy, z), (-0.133, hy, z), 0.028, 10, r1=0.042)
    K = p("bare"); box(K, (-0.150, hy, zc + 0.075), (0.05, 0.07, 0.008)); box(K, (-0.178, hy - 0.028, zc + 0.086), (0.006, 0.012, 0.03)); box(K, (-0.178, hy + 0.028, zc + 0.086), (0.006, 0.012, 0.03))
    # 줄: 송수화기 아래 끝 → 처졌다가 → 상자 밑 이음쇠로 올라가 들어간다. 매끈한 고무 줄 (굵기가 번갈아 바뀌던 줄은 쇠사슬로 읽혔다), 처진 곳이 뒤판 안에 남는다
    a, c_, e = Vector((-0.199, hy, zc - 0.104)), Vector((-0.15, hy + 0.01, zc - 0.44)), Vector((-0.05, hy, zc - 0.178)); N = 12
    sweep(p("rubber", smooth=True, nocol=True), [(1 - t) ** 2 * a + 2 * t * (1 - t) * c_ + t * t * e for t in (i / N for i in range(N + 1))], 0.007, 10)
    cyl(Bz, (-0.05, hy, zc - 0.16), (-0.05, hy, zc - 0.19), 0.015, 10)
    # 전선관: 상자 위에서 곧장 올라간다 (벽에서 5 cm) + 받침 둘(벽 판 + 관을 문 쇠) → 2.35 에서 크게 굽어 벽 속으로 + 둥근 벽 판(나사 둘) + 관을 문 쇠 목 — 기동기 케이블의 벽 들어가는 자리와 같은 꼴
    sweep(p("rust", smooth=True), [(0.0, -0.05, zt)] + _elbow(0.0, -0.05, 2.35, 4), 0.012, 10)
    for z in (1.95, 2.20): box(I, (0, -0.004, z), (0.085, 0.008, 0.034)); box(I, (0, -0.036, z), (0.04, 0.06, 0.02))
    cyl(Bz, (0, -0.008, 2.35), (0, 0.03, 2.35), 0.04, 12); cyl(Ir, (0, -0.024, 2.35), (0, -0.008, 2.35), 0.021, 10); _bolts(I, [(-0.03, 2.35), (0.03, 2.35)], -0.008, -0.013, 0.006)
    return p.done()

# ───────────────────────── 4) 게시판 + 번호표 걸이 ─────────────────────────
def _prism(bm, pts, t=0.002):
    """앞면 점들(3D)을 +y 로 t 만큼 두께 준 판 (찢긴 · 말린 종이)"""
    A = [bm.verts.new(Vector(q)) for q in pts]; B = [bm.verts.new(Vector(q) + Vector((0, t, 0))) for q in pts]; n = len(pts)
    bm.faces.new(A); bm.faces.new(B[::-1])
    for i in range(n): bm.faces.new((A[i], B[i], B[(i + 1) % n], A[(i + 1) % n]))

# (x 비율, z 비율, 너비, 높이, 기운 각, 종류, 귀퉁이: curl = 아래 귀가 말려 들림 · torn = 아래 귀가 찢겨 없음, 부호 = 어느 쪽 귀)
_PAPERS = [(-0.74, 0.30, 0.21, 0.30, -3, "lines", "curl", 1), (-0.42, -0.22, 0.30, 0.21, 4, "red", "torn", -1), (-0.12, 0.34, 0.21, 0.30, 2, "lines", "torn", 1), (0.16, -0.20, 0.26, 0.36, -5, "table", "curl", -1),
           (0.50, 0.36, 0.30, 0.21, 1, "lines", "", 1), (0.80, -0.02, 0.21, 0.30, 21, "lines", "curl", 1), (0.44, -0.66, 0.18, 0.13, -14, "blank", "torn", 1)]
def notice_board(mats, w=2.0, h=1.1):
    """나무 틀 + 타르 바탕에 켠 판자 다섯 장(벽과 색이 달라야 '판'으로 읽힌다) + 핀으로 꽂은 종이 7장(귀가 말리고 찢기고, 하나는 빨간 머리 줄, 하나는 귀의 핀 하나에 매달려 기울었다)
    + 종이 없이 남은 핀 · 뜯겨 나간 종이의 윗 띠 + 오른쪽에 번호표 걸이(입갱표: 노란 판 + 못 5 x 4 + 못 위 흰 번호 딱지 + 고리에 매달린 길쭉한 알루미늄 표, 여덟 못은 비었다). 판 가운데 z 1.5, x 0
    (물 자국은 뺐다 — 얇은 판으로 만든 얼룩은 노란 테이프 · 잿빛 고드름으로만 읽혔다. 얼룩은 그물이 아니라 재질 사진이 할 일이다)"""
    p = _P(mats, "NOTICE"); zc = 1.5
    box(p("tar"), (0, -0.02, zc), (w, 0.02, h))
    n = 5; ph_ = h / n
    for i in range(n): box(p("plank"), ((0.004 if i % 2 else -0.003), -0.034, zc - h / 2 + ph_ * (i + 0.5)), (w - 0.004, 0.012, ph_ - 0.008))   # 판자 사이 틈으로 타르가 보인다
    F = p("timber")
    for sz in (-1, 1): box(F, (0, -0.03, zc + sz * (h / 2 + 0.035)), (w + 0.14, 0.06, 0.07))
    for sx in (-1, 1): box(F, (sx * (w / 2 + 0.035), -0.03, zc), (0.07, 0.06, h))
    I = p("iron"); _bolts(I, [(sx * (w / 2 + 0.035), zc + sz * (h / 2 + 0.035)) for sx in (-1, 1) for sz in (-1, 1)], -0.06, -0.068, 0.012)   # 틀 귀 못
    for fx, fz, pw, ph, deg, kind, wear, sg in _PAPERS:
        cx, cz = fx * w / 2, zc + fz * h / 2; R = Matrix.Rotation(-math.radians(deg), 3, "Y")
        def at(lx, lz, y, R=R, cx=cx, cz=cz): q = R @ Vector((lx, 0, lz)); return (cx + q.x, y, cz + q.z)
        def on(bm, lx, lz, sw, sh, y, R=R, at=at): box(bm, at(lx, lz, y), (sw, 0.002, sh), rot=R)
        c = 0.085 if wear == "torn" else 0.055 if wear == "curl" else 0.0; X, Z = pw / 2, ph / 2
        pts = [(-X, Z), (X, Z), (X, -Z + c)] + ([(X - c * 0.45, -Z + c * 0.7)] if wear == "torn" else []) + [(X - c, -Z), (-X, -Z)]
        _prism(p("white"), [at(sg * x, z, -0.043) for x, z in pts])
        if wear == "curl": _prism(p("white"), [at(sg * X, -Z + c, -0.043), at(sg * (X - c), -Z, -0.043), at(sg * (X - 0.012), -Z + 0.016, -0.068)])   # 말려 들린 귀
        if kind != "blank":
            on(p("red" if kind == "red" else "black"), 0, Z - 0.035, pw * 0.7, 0.02, -0.0445)            # 머리 줄
            nl = int((ph - 0.09) / 0.032) - (3 if wear == "torn" else 1 if wear == "curl" else 0)
            for i in range(nl): on(p("black"), -pw * (0.04 if i % 3 else 0.0), Z - 0.075 - i * 0.032, pw * (0.72 if i % 3 else 0.8), 0.005, -0.0445)
            if kind == "table":
                for lx in (-0.05, 0.03): on(p("black"), lx, 0.01, 0.004, ph - 0.19, -0.0445)
        px = -sg * (X - 0.02) if abs(deg) > 15 else 0.0                                                # 많이 기운 종이는 한쪽 귀의 핀 하나에 매달렸다
        q = at(px, Z - 0.012, 0); cyl(I, (q[0], -0.04, q[2]), (q[0], -0.05, q[2]), 0.006, 5)   # 핀
    # 종이가 뜯겨 나간 자리: 핀만 남았거나, 뜯긴 종이의 윗 띠(너비 14 cm, 아래가 들쭉날쭉)가 핀에 남았다 — 손톱만 한 조각은 3 m 에서 흰 점으로만 보였다
    for fx, fz, scrap in ((-0.90, -0.55, True), (-0.25, -0.70, False), (0.58, -0.30, True), (0.30, 0.72, False), (-0.55, 0.62, False)):
        x, z = fx * w / 2, zc + fz * h / 2; cyl(p("rust"), (x, -0.04, z), (x, -0.05, z), 0.006, 5)
        if scrap: _prism(p("white"), [(x + lx, -0.043, z + lz) for lx, lz in ((-0.07, 0.014), (0.07, 0.017), (0.072, -0.022), (0.035, -0.008), (0.005, -0.034), (-0.03, -0.012), (-0.068, -0.030))])
    # 번호표 걸이 (입갱표 — 들어갈 때 제 번호 표를 걸어 두고 나올 때 가져간다, 남은 표 = 아직 갱 안에 있는 사람). 레퍼런스(k20, 1981 입갱표 판) 공통점:
    # 노랗게 칠한 판 · 못마다 바로 위에 작은 흰 번호 딱지(옆 딱지와 거의 닿는다) · 못에 둥근 고리 · 고리에 양 끝이 둥근 길쭉한 알루미늄 표 · 표 너비 = 못 간격의 6할이고 표가 줄 간격을 거의 채운다 · 표는 조금씩 삐뚤고 몇 못은 비었다
    xr = w / 2 + 0.07 + 0.30; zr = zc + 0.12
    box(p("steel_yellow"), (xr, -0.0125, zr), (0.42, 0.025, 0.62)); _rect(p("black"), xr, zr + 0.245, 0.36, 0.085, -0.026)
    p.text("입갱표", (xr, -0.0285, zr + 0.222), 0.06, "white")
    Tg, Rg, ra = p("bare"), p("bare", smooth=True, nocol=True), 0.025
    oval = [(ra * math.cos(t), -0.037 + ra * math.sin(t)) for t in (math.pi * i / 4 for i in range(5))] + [(ra * math.cos(t), -0.062 + ra * math.sin(t)) for t in (math.pi + math.pi * i / 4 for i in range(5))]   # 표: 0.050 x 0.075, 못 기준(0, 0) 아래로 매달린다
    for k in range(20):
        x, z = xr + (k % 5 - 2) * 0.08, zr + 0.165 - (k // 5) * 0.124
        cyl(I, (x, -0.02, z), (x, -0.048, z + 0.006), 0.004, 3); _rect(p("white"), x, z + 0.02, 0.058, 0.018, -0.026)   # 못 + 번호 딱지
        if k in (3, 6, 9, 12, 13, 15, 18, 19): continue                                                  # 빈 못 (표 주인이 나갔다)
        sw = math.radians(((k * 7) % 5 - 2) * 3.5); cs, sn = math.cos(sw), math.sin(sw); ty = -0.034 - (k % 3) * 0.002   # 못을 축으로 조금씩 삐뚤게
        _prism(Tg, [(x + lx * cs - lz * sn, ty, z + lx * sn + lz * cs) for lx, lz in oval])
        torus(Rg, (x + 0.008 * sn, ty - 0.002, z - 0.008 * cs), (0.3 if k % 2 else -0.3, -1, 0), 0.010, 0.002, 8, 3)   # 고리: 위는 못에 얹히고 아래는 표 머리 구멍 자리에 겹친다
    return p.done()

# ───────────────────────── 5) 구급함 + 들것 ─────────────────────────
def first_aid(mats):
    """흰 벽장(0.45 x 0.55 x 0.18, 가운데 z 1.45, x 0) + 빨간 십자 + 걸쇠, 문이 조금 열려 있다 · 녹물 자국. 오른쪽(x 0.68)에 접은 들것이 갈고리 둘에 세로로 걸린다
    (들것 = 장대 둘 + 장대를 감싼 천 + 쇠 발 넷 + 가죽 띠 + 십자 표 — 손잡이 끝이 위아래로 나와야 들것으로 읽힌다)"""
    p = _P(mats, "AID"); zc = 1.45
    Wt = p("white"); box(Wt, (0, -0.09, zc), (0.45, 0.18, 0.55)); _rect(p("black"), 0, zc, 0.40, 0.50, -0.1805, 0.002)   # 문 틈으로 보이는 어두운 속
    box(Wt, (0, -0.10, zc + 0.285), (0.49, 0.21, 0.02))                                                    # 윗 덮개 (조금 내민다)
    Ir = p("iron", smooth=True)
    for dz in (-0.17, 0.17): cyl(Ir, (-0.218, -0.186, zc + dz - 0.03), (-0.218, -0.186, zc + dz + 0.03), 0.01, 8)
    for x, L in ((-0.21, 0.16), (0.12, 0.09), (0.19, 0.22)): _rect(p("rust"), x, zc - 0.275 - L / 2, 0.012, L, -0.001, 0.002)   # 상자 밑 벽에 흐른 녹물
    # 문: 경첩(왼쪽)을 축으로 5도 열렸다 — 걸쇠가 풀린 채 버려졌다
    d = _P(mats, "AID_DOOR"); box(d("white"), (0, -0.186, zc), (0.41, 0.008, 0.51))
    R = d("red"); _rect(R, 0, zc + 0.03, 0.22, 0.07, -0.192, 0.004); _rect(R, 0, zc + 0.03, 0.07, 0.22, -0.192, 0.004)
    for x, z, sw, sh in ((0.09, zc + 0.058, 0.04, 0.014), (-0.028, zc - 0.07, 0.014, 0.02)): _rect(d("white"), x, z, sw, sh, -0.195, 0.002)   # 십자 칠이 벗겨진 자리
    for x, z, sw, sh in ((-0.10, zc - 0.245, 0.20, 0.014), (-0.195, zc - 0.20, 0.014, 0.10), (0.16, zc - 0.247, 0.07, 0.01), (-0.196, zc + 0.10, 0.01, 0.13), (0.10, zc - 0.21, 0.008, 0.07), (0.185, zc - 0.075, 0.01, 0.08)): _rect(d("rust"), x, z, sw, sh, -0.1905, 0.002)   # 문 아래 · 귀의 녹
    box(d("bare"), (0.185, -0.194, zc), (0.03, 0.012, 0.07)); cyl(d("iron", smooth=True), (0.185, -0.20, zc), (0.185, -0.217, zc), 0.011, 8)   # 걸쇠
    out = p.done() + d.done(_T(-0.205, -0.182, 0) @ Matrix.Rotation(math.radians(-5), 4, "Z") @ _T(0.205, 0.182, 0))
    # 들것
    s = _P(mats, "AID_STRETCHER"); I = s("iron"); xs, ys = 0.68, -0.085
    for sx in (-1, 1):
        cyl(s("timber", smooth=True), (xs + sx * 0.085, ys, 0.25), (xs + sx * 0.085, ys, 2.25), 0.022, 8)
        for z in (0.80, 1.72):                                                                             # 쇠 발 (ㄷ 꼴, 앞으로 나온다)
            for dz in (-0.045, 0.045): box(I, (xs + sx * 0.085, ys - 0.06, z + dz), (0.018, 0.09, 0.018))
            box(I, (xs + sx * 0.085, ys - 0.105, z), (0.018, 0.018, 0.108))
    def roll(bm, z0, z1, r, fx=1.55, fy=0.62):
        for v in cyl(bm, (xs, ys, z0), (xs, ys, z1), r, 10): v.co.x = xs + (v.co.x - xs) * fx; v.co.y = ys + (v.co.y - ys) * fy
    roll(s("cloth", smooth=True), 0.62, 1.90, 0.075)
    for z in (0.98, 1.50): roll(s("rubber"), z, z + 0.045, 0.079); box(s("bare"), (xs + 0.03, ys - 0.052, z + 0.022), (0.04, 0.008, 0.055))   # 띠 + 버클
    _rect(s("white"), xs, 1.27, 0.15, 0.15, ys - 0.048, 0.004); _rect(s("red"), xs, 1.27, 0.10, 0.032, ys - 0.052, 0.003); _rect(s("red"), xs, 1.27, 0.032, 0.10, ys - 0.052, 0.003)   # 천에 꿰맨 십자 표
    for zh in (2.0, 0.42):
        box(I, (xs, ys, zh + 0.022), (0.21, 0.03, 0.02))                                                    # 들것 가로대
        box(I, (xs, -0.09, zh + 0.006), (0.03, 0.18, 0.012)); box(I, (xs, -0.174, zh + 0.03), (0.03, 0.012, 0.06))   # 벽 갈고리 (끝이 위로 굽었다)
        box(I, (xs, -0.004, zh - 0.02), (0.06, 0.008, 0.10))                                                # 갈고리 벽 판
    return out + s.done()

# ───────────────────────── 6) 기동기 상자 ─────────────────────────
def switch_box(mats):
    """갱내 기동기(스위치) 상자 0.5 x 0.7 x 0.25, 가운데 z 1.3: 벽의 ㄷ형강 둘에 볼트로 달림 · 볼트 두른 두꺼운 문 · 둥근 전류계 · 오른쪽 옆 손잡이
    · 굵은 케이블 둘이 모두 벽을 타고 올라가 z 2.35 에서 직각으로 꺾여 벽 속으로 들어간다(둥근 벽 판 + 쇠 목): 하나는 위 이음쇠에서 곧장, 하나는 아래 이음쇠에서 늘어졌다가(물 떨굼 고리) 상자 왼쪽 벽으로 올라간다
    — 끝이 허공에 남지 않는다 (10-03: 2.45 에서 끊겨 있었다). 2.42 위로는 아무것도 없다"""
    p = _P(mats, "SWBOX"); zc = 1.3
    I = p("iron"); Ir = p("iron", smooth=True); S = p("steel_paint")
    for sz in (-1, 1):
        box(p("rust"), (0, -0.02, zc + sz * 0.25), (0.64, 0.04, 0.06)); _bolts(I, [(sx * 0.29, zc + sz * 0.25) for sx in (-1, 1)], -0.04, -0.052, 0.013)
    box(S, (0, -0.165, zc), (0.5, 0.25, 0.7)); box(S, (0, -0.297, zc), (0.46, 0.014, 0.66)); box(S, (0, -0.31, zc), (0.38, 0.012, 0.58))
    _bolts(I, [(sx * 0.21, zc + dz) for sx in (-1, 1) for dz in (-0.28, 0, 0.28)] + [(0, zc + 0.31), (0, zc - 0.31)], -0.304, -0.32, 0.012)
    # 전류계: 검은 테 + 밝은 눈금판 + 바늘
    ax, az = -0.07, zc + 0.16
    cyl(Ir, (ax, -0.316, az), (ax, -0.342, az), 0.072, 12); cyl(p("glass"), (ax, -0.342, az), (ax, -0.345, az), 0.058, 12)
    _stroke(p("black"), [(ax, az - 0.03), (ax + 0.03, az + 0.035)], -0.347, 0.005); _stroke(p("black"), [(ax - 0.04, az + 0.012), (ax - 0.025, az + 0.035), (ax, az + 0.044), (ax + 0.025, az + 0.035), (ax + 0.04, az + 0.012)], -0.347, 0.004)
    _rect(p("steel_yellow"), 0.10, zc + 0.17, 0.10, 0.07, -0.3175, 0.003)                                   # 이름표
    _rect(p("white"), 0, zc - 0.14, 0.22, 0.08, -0.3175, 0.003); _rect(p("red"), 0, zc - 0.115, 0.22, 0.018, -0.3195, 0.002)
    cyl(p("red"), (-0.05, -0.316, zc - 0.01), (-0.05, -0.335, zc - 0.01), 0.022, 8); cyl(p("black"), (0.05, -0.316, zc - 0.01), (0.05, -0.335, zc - 0.01), 0.022, 8)   # 누름 단추 둘
    # 낡음: 문 아래 턱의 녹, 볼트 · 전류계 밑으로 흐른 녹물
    Ru = p("rust")
    for x, z, sw, sh in ((-0.08, zc - 0.283, 0.20, 0.012), (-0.183, zc - 0.22, 0.012, 0.13), (0.15, zc - 0.284, 0.07, 0.01), (0.0, zc - 0.215, 0.01, 0.08), (-0.07, zc + 0.04, 0.012, 0.09)): _rect(Ru, x, z, sw, sh, -0.3165, 0.002)
    for x, z, sw, sh in ((-0.21, zc - 0.20, 0.012, 0.22), (0.21, zc - 0.20, 0.012, 0.14), (-0.21, zc + 0.20, 0.012, 0.13), (0.21, zc + 0.19, 0.01, 0.16)): _rect(Ru, x, z, sw, sh, -0.3045, 0.002)
    # 옆 손잡이: 축 통 + 비스듬한 팔 + 빨간 쥘 곳
    cyl(Ir, (0.25, -0.165, zc + 0.10), (0.295, -0.165, zc + 0.10), 0.045, 10)
    a, b = Vector((0.305, -0.165, zc + 0.10)), Vector((0.335, -0.35, zc + 0.36)); d = (b - a).normalized()
    cyl(p("bare", smooth=True), a - d * 0.03, b, 0.016, 8); cyl(p("steel_red", smooth=True), b - d * 0.01, b + d * 0.12, 0.027, 8)
    # 케이블 이음쇠(육각 너트) + 케이블. 남는 구멍은 마개
    Cb = p("rubber", smooth=True, nocol=True); zt, zb = zc + 0.35, zc - 0.35
    for x, z0, z1 in ((0.10, zt, zt + 0.07), (-0.10, zb, zb - 0.07), (0.10, zb, zb - 0.04)):
        cyl(Ir, (x, -0.165, z0), (x, -0.165, z1), 0.04, 10); cyl(I, (x, -0.165, z0 + (z1 - z0) * 0.35), (x, -0.165, z0 + (z1 - z0) * 0.75), 0.052, 6)
    sweep(Cb, [(0.10, -0.165, zt + 0.05), (0.10, -0.165, zt + 0.20), (0.11, -0.10, zt + 0.36), (0.13, -0.04, zt + 0.50)] + _elbow(0.13, -0.035, 2.35), 0.026, 10)
    loop = [(-0.235 + 0.135 * math.cos(t), -0.165 + 0.13 * t / math.pi, 0.70 - 0.135 * math.sin(t)) for t in (math.pi * i / 6 for i in range(7))]   # 물 떨굼 고리: 둥근 U (세 점으로 꺾은 V 는 꺾인 관으로 보였다), 돌면서 벽 쪽으로 붙는다
    sweep(Cb, [(-0.10, -0.165, zb - 0.05)] + loop + [(-0.375, -0.035, 1.4), (-0.366, -0.035, 2.2)] + _elbow(-0.364, -0.035, 2.35), 0.026, 10)
    for x in (0.13, -0.364):                                                                               # 벽 들어가는 자리: 둥근 벽 판 + 케이블을 문 쇠 목
        cyl(p("bare", smooth=True), (x, -0.008, 2.35), (x, 0.03, 2.35), 0.062, 12); cyl(Ir, (x, -0.03, 2.35), (x, -0.008, 2.35), 0.038, 10)
    for x, z in ((0.13, 2.25), (-0.375, 1.0), (-0.365, 2.1)): box(p("rust"), (x, -0.03, z), (0.12, 0.06, 0.03))   # 케이블 고정 띠
    return p.done()

# ───────────────────────── 7) 본보기: 여섯 가지를 7 m 벽에 ─────────────────────────
def build(mats):
    """미리보기 옵션: {"_wall": 0.0, "_ceil": 2.4} — 기둥 머리가 천장(2.4)에 닿는다. 전선관 · 케이블은 z 2.35 에서 벽 속으로 들어간다"""
    out = []
    for fn, M, kw in ((gas_board, _T(-3.0, -0.6, 0), dict(h=2.4)), (no_entry_plate, _T(-2.2, 0, 1.5), {}), (phone, _T(-1.4, 0, 0), {}), (notice_board, _T(0.25, 0, 0), {}), (first_aid, _T(2.3, 0, 0), {}), (switch_box, _T(3.85, 0, 0), {})):
        objs = fn(mats, **kw)
        for o in objs: o.data.transform(M)
        out += objs
    return out
