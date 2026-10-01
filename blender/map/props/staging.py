"""큰 빈터의 나무 발판 + 두 번 꺾어 내려오는 열린 계단 (10-02 판정 "큰 굴 구조물 품질이 너무 낮다").
참고 공통 구조(R3 props[1] + Wieliczka 계단 사진): 기둥 위에 도리, 도리 위에 장선, 장선 위에 낱장 판자 · 기둥 사이 X 가새 ·
계단은 옆판 둘 + 낱장 디딤판(챌판 없음) + 기둥 · 윗난간 · 중간난간 · 기둥마다 받침목. 떠 있는 것 없음 — 모든 짐이 바닥까지 내려간다.
자리표: 원점 = 발판 가운데 아래 바닥. 옛 굴 · 바위 벽은 −x 쪽(발판 끝 x = −deck_x/2), 계단은 −x 벽에 붙어 −y 로 내려간다.
build() 발판+계단 · crib() 우물 정(井)자 통나무 쌓기 · spare_timbers() 바닥에 누운 여분 통나무 더미."""
import math, random
import bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, sweep, obj

def board(bm, p0, p1, w, h):
    """p0 → p1 판자. w = 옆(수평) 두께, h = 세운 폭"""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    return box(bm, (p0 + p1) / 2, (d.length, w, h), d.to_track_quat("X", "Z").to_matrix())

def prism(bm, yz, x0, x1, M=None):
    """yz 평면 다각형을 x0 → x1 로 밀어낸 덩어리 (계단 옆판 · 비탈 · 쐐기)"""
    M = M or Matrix.Identity(4)
    a = [bm.verts.new(M @ Vector((x0, y, z))) for y, z in yz]; b = [bm.verts.new(M @ Vector((x1, y, z))) for y, z in yz]; n = len(yz)
    bm.faces.new(a); bm.faces.new(b[::-1])
    for i in range(n): bm.faces.new((a[i], b[i], b[(i + 1) % n], a[(i + 1) % n]))

def log(bm, p0, p1, r, rng, ends=None, seg=10, taper=0.08):
    """껍질 벗긴 통나무: 살짝 휘고 위로 갈수록 가늘다. ends = 끝면(나이테) 을 따로 담을 그물"""
    p0, p1 = Vector(p0), Vector(p1); d = (p1 - p0).normalized(); j = r * 0.12
    pts = [p0.lerp(p1, t) + (Vector((rng.uniform(-j, j), rng.uniform(-j, j), rng.uniform(-j, j))) if 0 < t < 1 else Vector()) for t in (0, 0.33, 0.66, 1)]
    sweep(bm, pts, r, seg, True, lambda i: r * (1 - taper * i / 3))
    if ends is not None:
        cyl(ends, p0 + d * 0.002, p0 - d * 0.005, r * 0.95, seg); cyl(ends, p1 - d * 0.002, p1 + d * 0.005, r * (1 - taper) * 0.95, seg)

def build(mats, deck_h=3.0, deck_x=4.4, deck_y=3.0, stair_w=1.1):
    rng = random.Random(7); out = []; hx, hy = deck_x / 2, deck_y / 2
    PL, JO, CAP, D = 0.05, 0.15, 0.22, 0.33
    z_c = deck_h - PL - JO; z_p = z_c - CAP                     # 도리 윗면 · 기둥 머리 (도리 밑 = 바닥에서 2.58 → 밑을 서서 지난다)
    sx0, sx1 = -hx, -hx + stair_w                               # 계단 폭 (벽 쪽 ~ 열린 쪽)
    px = [-hx + 0.13, sx1 + 0.15, (sx1 + 0.15 + hx - 0.25) / 2, hx - 0.25]; py = [-hy + 0.2, hy - 0.2]   # 벽 쪽 기둥 줄은 벽에 바짝 (디딤판 사이로 기둥이 솟아 보이지 않게)
    land_z = deck_h / 2; n = max(2, round(land_z / 0.19)); r = land_z / n; g = 0.26; s = r / g      # 디딤 높이 0.19 · 너비 0.26 (약 36도)
    L_LAND = 1.3; ya = -hy; yL0 = ya - (n - 1) * g; yL1 = yL0 - L_LAND; yend = yL1 - n * g           # 전체 길이 5.2 m

    timber, ends, foot, iron, bolt = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    def post(x, y, top, rad):
        """받침목(침목 토막) 위에 선 둥근 기둥 — 받침목은 크기 · 방향이 제각각"""
        box(foot, (x, y, 0.05), (rng.uniform(0.30, 0.40), rng.uniform(0.50, 0.66), 0.10), Matrix.Rotation(rng.uniform(-0.4, 0.4), 3, "Z")); log(timber, (x, y, 0.10), (x, y, top), rad, rng)
    # --- 발판: 기둥 4 × 2 → 도리(y 방향) → 장선(x 방향) → 판자(y 방향, 틈) ---
    for x in px:
        for y in py:
            post(x, y, z_p + 0.02, 0.115)
            for sgn in (-1, 1): box(iron, (x + sgn * 0.112, y, z_p + 0.02), (0.02, 0.05, 0.36))          # 기둥과 도리를 잇는 꺾쇠
        log(timber, (x, -hy - 0.06, z_p + CAP / 2), (x, hy + 0.06, z_p + CAP / 2), CAP / 2, rng, ends, taper=0.05)
    bm = bmesh.new()
    for i in range(7):
        y = -hy + 0.05 + i * (deck_y - 0.10) / 6; box(bm, (0, y, z_c + JO / 2), (deck_x, 0.08, JO))
    out.append(obj("STG_JOIST", bm, mats["timber_old"]))
    bm = bmesh.new(); npl = round(deck_x / 0.232); pw = deck_x / npl
    for i in range(npl):                                                                               # 낱장 판자 — 끝이 들쭉날쭉, 틈 1.2 cm, 한 장은 끝이 부러져 장선이 드러난다
        x = -hx + (i + 0.5) * pw; y0 = -hy - (0 if x < sx1 + 0.1 else rng.uniform(0, 0.05)); y1 = hy + rng.uniform(0, 0.05) - (0.42 if i == npl - 6 else 0)
        box(bm, (x, (y0 + y1) / 2, deck_h - PL / 2 - rng.uniform(0, 0.004)), (pw - 0.012, y1 - y0, PL))
    out.append(obj("STG_DECK", bm, mats["plank"]))

    # --- X 가새 (바깥 면에 판자 둘이 엇갈려 덧대임, 가운데 볼트) — 칸마다 높이가 다르고 한 장은 부러져 반만 남았다 ---
    brace = bmesh.new()
    def xbrace(a, b, nrm, broken=False):
        a, b, nrm = Vector((*a, 0)), Vector((*b, 0)), Vector((*nrm, 0)); mz = []
        for k, (p, q) in enumerate(((a, b), (b, a))):
            zl, zh = 0.35 + rng.uniform(-0.12, 0.15), z_p - 0.2 - rng.uniform(0, 0.25)
            o = nrm * (0.14 + 0.06 * k); p0, p1 = p + o + Vector((0, 0, zl)), q + o + Vector((0, 0, zh)); mz.append((zl + zh) / 2)
            board(brace, p0, p0.lerp(p1, 0.57) if broken and k else p1, 0.06, 0.18)
            for e, z in ((p, zl), (q, zh)): cyl(bolt, e + Vector((0, 0, z)) + nrm * 0.05, e + Vector((0, 0, z)) + o + nrm * 0.05, 0.022, 6)
        m = (a + b) / 2 + Vector((0, 0, sum(mz) / 2)); cyl(bolt, m + nrm * 0.10, m + nrm * 0.26, 0.022, 6)
    xbrace((px[3], py[0]), (px[3], py[1]), (1, 0))               # 굴 반대쪽 끝 면
    xbrace((px[2], py[0]), (px[3], py[0]), (0, -1))              # −y 면 바깥 칸 (가운데 칸은 비워 밑으로 드나든다)
    xbrace((px[1], py[1]), (px[2], py[1]), (0, 1), True); xbrace((px[2], py[1]), (px[3], py[1]), (0, 1))
    out.append(obj("STG_BRACE", brace, mats["timber_old"]))

    # --- 계단 두 줄 + 참 ---
    stair, tread, rail, lag = bmesh.new(), [bmesh.new(), bmesh.new()], bmesh.new(), bmesh.new()
    xr, xp = sx1 - 0.025, sx1 + 0.045                            # 난간 판 · 난간 기둥의 x (열린 쪽만 — 반대쪽은 바위 벽)
    def rpost(y, z0, z1):
        box(stair, (xp, y, (z0 + z1) / 2), (0.09, 0.09, z1 - z0)); box(bolt, (xp + 0.05, y, z0 + 0.12), (0.02, 0.05, 0.05))
    def rails(pa, pb, over=0.08):
        """윗난간 · 중간난간: 아래 끝이 기둥을 지나 조금 더 나가고(겹쳐 못질), 기둥 자리마다 볼트 머리"""
        for H in (1.0, 0.5):
            a, b = Vector((xr, pa[0], pa[1] + H)), Vector((xr, pb[0], pb[1] + H)); d = (b - a).normalized()
            board(rail, a, b + d * over, 0.05, 0.11)
            for e in (a + d * 0.04, b): box(bolt, e + Vector((-0.03, 0, 0)), (0.02, 0.04, 0.04))
    def flight(k, y0, z0, zcut, yp_top, yp_bot, zp_bot):
        nos = lambda y: z0 - (y0 - y) * s                        # 디딤판 코를 잇는 선
        zt = lambda y: nos(y) - 0.02
        y3 = y0 - (z0 - 0.02 - D - zcut) / s; y4 = y0 - (z0 - 0.02 - zcut - 0.10) / s
        for xs in (sx0, sx1 - 0.07):                             # 옆판 둘: 위는 수직으로 잘려 테두리에 붙고 아래는 수평으로 앉는다
            prism(stair, [(y0 + 0.03, zt(y0 + 0.03)), (y0 + 0.03, zt(y0 + 0.03) - D), (y3, zcut), (y4, zcut), (y4, zt(y4))], xs, xs + 0.07)
        for i in range(1, n):                                    # 낱장 디딤판(앞 모서리가 닳아 깎임, 장마다 두께 · 기울기가 다름) + 받침 쪽목. 챌판 없음
            top = z0 - i * r; yc = y0 - i * g + 0.12; t = rng.uniform(0.045, 0.06); xa, xb = sx0 + 0.065, sx1 - 0.065; xm = (xa + xb) / 2 - 0.1
            halves = ((xa, xm - 0.01, 0.05, -0.012), (xm + 0.01, xb, -0.09, -0.03)) if (k, i) == (1, 4) else ((xa, xb, rng.uniform(-0.035, 0.035), 0),)    # 한 장은 쪼개져 반쪽이 내려앉았다
            for x0_, x1_, tilt, dz in halves:
                M = Matrix.Translation((0, yc + rng.uniform(-0.012, 0.012), top - t / 2 + dz)) @ Matrix.Rotation(tilt, 4, "X")
                prism(tread[k], [(0.135, -t / 2), (0.135, t / 2), (-0.10, t / 2), (-0.135, t / 2 - 0.022), (-0.135, -t / 2)], x0_, x1_, M)
            for xc in (sx0 + 0.09, sx1 - 0.09): box(stair, (xc, yc, top - 0.085), (0.04, 0.22, 0.05))
        for f in (0.3, 0.72):                                    # 옆판 둘을 조이는 긴 볼트 + 바깥 면 네모 와셔
            y = y0 + (y4 - y0) * f; z = zt(y) - 0.21
            cyl(bolt, (sx0 + 0.01, y, z), (sx1 + 0.045, y, z), 0.013, 6); box(iron, (sx1 + 0.04, y, z), (0.012, 0.09, 0.09))
        box(iron, (sx1 + 0.005, y0 - 0.12, zt(y0 - 0.12) - 0.08), (0.012, 0.34, 0.05), Matrix.Rotation(math.atan(s), 3, "X"))   # 옆판 머리를 붙드는 띠쇠
        cb = bmesh.new(); prism(cb, [(y0, z0), (y0 - n * g, z0 - n * r), (y0 - n * g + 0.12, z0 - n * r), (y0, z0 - 0.08)], sx0, sx1)   # 걷는 비탈 (안 보임)
        o = obj("COLONLY_STAIR_%d" % (k + 1), cb, mats["plank"]); o.hide_render = True; out.append(o)
        ym = (yp_top + yp_bot) / 2; rpost(ym, zt(ym) - D, nos(ym) + 1.04); rpost(yp_bot, zp_bot, nos(yp_bot) + 1.04)
        rails((yp_top, nos(yp_top)), (yp_bot, nos(yp_bot)))
        return nos
    yP1, yP2, yP3 = yL0 - 0.12, yL1 + 0.06, yend + 0.30
    n1 = flight(0, ya, deck_h, land_z - PL - JO, ya - 0.05, yP1, land_z - 0.25)
    n2 = flight(1, yL1, land_z, 0.06, yP2, yP3, 0.06)
    rpost(yP2, land_z - 0.25, n2(yP2) + 1.04)
    rails((yP1, n1(yP1)), (yP2, n2(yP2)), 0.0)                                                         # 참 난간
    box(stair, ((sx0 + sx1) / 2 + 0.06, yL1 - (land_z - 0.35 - 0.06) / s - 0.17, 0.03), (stair_w + 0.16, 0.5, 0.06))   # 계단 발 밑 깔판
    # 참: 기둥 넷 → 도리 둘(x 방향) → 장선 셋(양 끝은 테두리) → 판자
    for y in (yL0 - 0.15, yL1 + 0.15):
        for x in px[:2]: post(x, y, land_z - 0.36, 0.10)
        log(timber, (sx0 + 0.02, y, land_z - 0.29), (px[1] + 0.13, y, land_z - 0.29), 0.09, rng, ends, taper=0.05)
    for x in (sx0 + 0.04, (sx0 + sx1) / 2, sx1 - 0.04): box(stair, (x, (yL0 + yL1) / 2, land_z - PL - JO / 2), (0.08, L_LAND, JO))
    out.append(obj("STG_STAIR", stair, mats["timber_old"]))
    bm = bmesh.new()
    for i in range(6): box(bm, ((sx0 + sx1) / 2, yL0 - (i + 0.5) * L_LAND / 6, land_z - PL / 2 - rng.uniform(0, 0.004)), (stair_w, L_LAND / 6 - 0.012, PL))
    out.append(obj("STG_LANDING", bm, mats["plank"]))
    for k in (0, 1): out.append(obj("NOCOL_TREAD_F%d" % (k + 1), tread[k], mats["plank"]))

    # --- 계단 · 참 밑 막기: 타르 칠한 세로 널을 옆판 바깥 면에 못질 (틈 2 cm, 한 장 빠진 자리도 틈 0.21 — 머리 닿는 밑으로 못 들어간다). 어두운 널 앞에서 밝은 디딤판이 읽힌다 ---
    def under(y):
        if y < yL1: return max(n2(y) - 0.02 - D, 0.0)
        if y <= yL0: return land_z - PL - 0.11
        if y < ya: return max(n1(y) - 0.02 - D, land_z - PL - JO)
        return z_c
    yB = -hy + 0.106; y = yB - 0.07; i = 0                        # yB = 발판 −y 끝 장선 안쪽 면의 널 줄
    while y > yend + 0.3:
        top = under(y) + 0.10 + (rng.uniform(0, 0.03) if y < ya else 0)
        if top > 0.28 and i not in (6, 15): box(lag, (sx1 + 0.02, y, top / 2), (0.03, 0.17, top))
        y -= 0.19; i += 1
    x = sx0 + 0.10
    while x < sx1 - 0.02:                                         # 발판 밑에서 위 계단 밑으로 드는 면 (도리 자리는 도리 밑까지만)
        top = z_p + 0.03 if abs(x - px[0]) < 0.14 else z_c + 0.10 - rng.uniform(0, 0.03); box(lag, (x, yB, top / 2), (0.17, 0.03, top)); x += 0.19
    for z in (0.75, 1.85): box(lag, ((sx0 + sx1) / 2 + 0.02, yB + 0.035, z), (stair_w, 0.04, 0.10))   # 띠장
    box(lag, (sx1 + 0.055, (yB + yL1 - 0.5) / 2, 0.55), (0.04, yB - yL1 + 0.5, 0.10)); box(lag, (sx1 + 0.055, (yB + yL0) / 2 - 0.1, 1.25), (0.04, yB - yL0 + 0.2, 0.10))
    out.append(obj("STG_LAGGING", lag, mats["tar"]))

    # --- 발판 난간: 굴 쪽(−x)과 계단 나가는 자리만 비우고 세 면. 기둥은 테두리 바깥에 볼트로, 윗난간 · 중간난간 · 발막이 판 ---
    def dpost(x, y, nx, ny):
        box(stair2, (x, y, (z_c - 0.12 + deck_h + 1.07) / 2), (0.10, 0.10, deck_h + 1.07 - z_c + 0.12)); box(bolt, (x + nx * 0.055, y + ny * 0.055, z_c + 0.06), (0.05, 0.05, 0.05))
    stair2 = bmesh.new()
    for y in (-hy + 0.05, 0, hy - 0.05): dpost(hx + 0.05, y, 1, 0)
    for x in (xp, (sx1 + hx) / 2): dpost(x, -hy - 0.05, 0, -1)
    for x in (-hx + 0.3, -hx / 3, hx / 3): dpost(x, hy + 0.05, 0, 1)
    out.append(obj("STG_RAILPOST", stair2, mats["timber_old"]))
    for H, w, h in ((1.0, 0.05, 0.12), (0.52, 0.05, 0.11), (0.075, 0.03, 0.15)):
        z = deck_h + H
        board(rail, (hx - w / 2, -hy, z), (hx - w / 2, hy, z), w, h)
        board(rail, (sx1, -hy + w / 2, z), (hx, -hy + w / 2, z), w, h)
        if H != 0.52: board(rail, (-hx + 0.25, hy - w / 2, z), (hx, hy - w / 2, z), w, h)
    board(rail, (-hx / 3 - 0.05, hy - 0.025, deck_h + 0.52), (hx, hy - 0.025, deck_h + 0.52), 0.05, 0.11)          # +y 중간난간: 벽 쪽 한 칸은 빠져
    board(rail, (-hx + 0.3, hy - 0.03, deck_h + 0.50), (-hx / 3 - 0.2, hy - 0.10, deck_h + 0.07), 0.05, 0.11)      # 한 끝이 떨어져 바닥에 걸친 채
    for ya_, yb_ in ((-hy + 0.12, -0.06), (hy - 0.12, 0.06)): board(rail, (hx - 0.0625, ya_, deck_h + 0.16), (hx - 0.0625, yb_, deck_h + 0.94), 0.025, 0.10)   # 칸마다 빗판
    out.append(obj("STG_RAIL", rail, mats["plank"]))
    out.append(obj("STG_TIMBER", timber, mats["timber"], smooth=True))
    out.append(obj("STG_FOOT", foot, mats["timber_old"])); out.append(obj("STG_IRON", iron, mats["rust"])); out.append(obj("STG_BOLT", bolt, mats["iron"])); out.append(obj("STG_ENDS", ends, mats["timber_end"]))
    return out

def crib(mats, height=2.8, log_len=1.3):
    """우물 정자 쌓기: 한 켜에 통나무 둘, 켜마다 직각으로 엇갈림, 가운데는 비고, 맨 위는 머리판 + 쐐기로 천장에 조인다 (Grube Fortuna Holzkasten)"""
    rng = random.Random(11); r, pitch = 0.09, 0.165; off = log_len / 2 - 0.16
    n = int((height - 0.10 - 2 * r) / pitch) + 1; top = 2 * r + (n - 1) * pitch
    logs, ends, wed = bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(n):
        z = r + k * pitch
        for sgn in (-1, 1):
            a = sgn * (off + rng.uniform(-0.03, 0.03)); e0 = -log_len / 2 + rng.uniform(-0.05, 0.05); e1 = log_len / 2 + rng.uniform(-0.05, 0.05)
            if k % 2 == 0: log(logs, (e0, a, z), (e1, a, z), r, rng, ends)
            else: log(logs, (a, e0, z), (a, e1, z), r, rng, ends)
    M = Matrix.Rotation(math.pi / 2, 4, "Z") if n % 2 == 0 else Matrix.Identity(4)                    # 맨 위 켜의 방향에 맞춰 돌린다
    for sgn in (-1, 1):
        b = bmesh.ops.create_cube(wed, size=1.0)                                                       # 머리판: 맨 위 통나무 둘에 걸친다
        for v in b["verts"]: v.co = M @ Vector((v.co.x * 0.22 + sgn * 0.3, v.co.y * (log_len - 0.1), v.co.z * 0.04 + top + 0.02))
        for y in (-off, off):                                                                          # 쐐기: 굵은 끝이 천장에 닿는다
            prism(wed, [(y - 0.2 * sgn, top + 0.04), (y + 0.2 * sgn, top + 0.04), (y + 0.2 * sgn, height), (y - 0.2 * sgn, top + 0.065)], sgn * 0.3 - 0.07, sgn * 0.3 + 0.07, M)
    return [obj("CRIB_LOGS", logs, mats["timber"], smooth=True), obj("CRIB_ENDS", ends, mats["timber_end"]), obj("CRIB_WEDGE", wed, mats["plank"])]

def spare_timbers(mats, seed=0):
    """바닥에 누운 여분 기둥감 (넷 깔고 골에 둘 얹음) + 판자 몇 장 + 쐐기 — 구조물 발치에 늘 있는 것"""
    rng = random.Random(seed); logs, ends, pl = bmesh.new(), bmesh.new(), bmesh.new(); r = 0.10
    def lying(y, z, yaw):
        L = rng.uniform(2.1, 2.7); x = rng.uniform(-0.2, 0.2); d = Vector((math.cos(yaw), math.sin(yaw), 0)) * L / 2
        log(logs, Vector((x, y, z)) - d, Vector((x, y, z)) + d, r, rng, ends, taper=0.10)
    for i in range(4): lying((i - 1.5) * 0.23, r, rng.uniform(-0.03, 0.03))
    for y in (-0.23, 0.23): lying(y, r + 0.166, rng.uniform(-0.06, 0.06))
    for k in range(3):                                                                                 # 겹쳐 놓은 판자
        a = rng.uniform(-0.12, 0.12); c = Vector((rng.uniform(-0.2, 0.2), 0.78 + rng.uniform(-0.04, 0.04), 0.025 + 0.05 * k)); d = Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.8, 1.1)
        board(pl, c - d, c + d, 0.20, 0.05)
    board(pl, (-0.5, 1.45, 0.03), (-0.55, 0.22, 0.40), 0.20, 0.05)                                     # 한 장은 통나무 더미에 기대 있다
    for k in range(3):
        M = Matrix.Translation((0.9 + 0.2 * k, 1.1 + 0.15 * k, 0)) @ Matrix.Rotation(rng.uniform(0, 3), 4, "Z"); prism(pl, [(-0.15, 0), (0.15, 0), (0.15, 0.09), (-0.15, 0.015)], -0.06, 0.06, M)
    return [obj("SPARE_LOGS", logs, mats["timber"], smooth=True), obj("SPARE_ENDS", ends, mats["timber_end"]), obj("SPARE_PLANK", pl, mats["plank"])]
