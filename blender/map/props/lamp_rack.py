"""안전등 충전대 (램프실) + 안전등 내주는 대.
레퍼런스 공통점 (build/refs/intro/korea/09_lamp_charging_rack.jpg · build/refs/player/kr/k17 1981 안전등실 · k04 · k05 안전등):
  - 아연 빛 ㄱ 쇠 틀, 다리 넷이 바닥까지 내려온다. 뒤판이 없어 벽이 비쳐 보인다. 가운데 뒤에 세로 띠쇠 하나.
  - 층마다 흰 칠 긴 통(레일)이 가로지르고 위에 검은 띠. 레일 앞면에 칸마다 검은 테 두른 동그란 작은 계기(밝은 눈금판)가 한 줄,
    그 아래 누런 때 낀 띠를 따라 번호가 붙어 있다.
  - 레일 밑에 칸마다 검은 충전 걸쇠가 내려와 있고, 안전등 머리가 거기 물려 유리가 앞 아래를 본다. 빈 걸쇠에는 쇠 집게만 보인다.
  - 그 아래 검은 선반(칸막이 토막이 줄지어 있다)에 배터리 통이 좁은 면을 앞으로 하고 한 줄로 서 있다 (통이 폭보다 키가 크다).
    뚜껑 끝에서 나온 가는 검은 전선이 통 옆으로 늘어졌다가 머리로 올라간다 — 고리 모양이 제각각이다.
  - 빈 칸에는 계기 · 걸쇠 · 빈 선반만 남는다 (= 그 사람은 갱 안에 있다). 맨 아래 선반 밑에 쇠막대가 한 줄 더 있다. 종이 꼬리표 하나가 걸쇠에 달려 있다.
  - 배터리(k04 · k05): 납작한 통(폭 12.5 · 두께 5 · 높이 15 cm, 모서리가 둥글다) + 통보다 넓은 쇠 뚜껑 + 넓은 면에 허리띠 고리 둘 + 뚜껑 끝의 굵은 고무 목.
    머리: 색 테 + 속이 오목한 반사경 + 가운데 전구 + 뒤로 가늘어지는 검은 몸. 1981 사진(k17)의 통은 모두 검다 → 통은 검정만 쓴다.
  - 1981 사진(k17): 충전대 위에 둥근 계기 둘 달린 회색 함. (함에서 틀 기둥을 따라 내려가는 쇠 관 · 벽으로 들어가는 관은 지어낸 것)
build(): 원점 = 충전대 뒤 가운데 바닥. 벽 = +y (틀 뒤가 y = 0 에 닿는다). 보는 쪽 = −y.
counter(): 원점 = 가운데 바닥. 긴 쪽 = x. 판자로 막은 앞 = −y (받는 사람 쪽), 트인 뒤 = +y (내주는 사람 쪽).
부딪힘은 틀 · 레일 · 선반 · 함 · 쇠 관 · 대의 뼈대만 — 안전등 · 전선 · 계기 · 번호는 NOCOL_.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
from _util import box, cyl, tube, sweep, obj

DEP = 0.34       # 틀 깊이 (앞면 y = −DEP)
SHELF0 = 0.53    # 맨 아래 선반 윗면 높이
PITCH = 0.465    # 층 사이 (선반 → 선반)
GAP = 0.29       # 선반 윗면 → 레일 밑 (사진: 통 18 cm + 머리가 걸리는 11 cm)
RAIL_H = 0.13    # 레일 높이
CASES = ("black", "black", "iron")            # 배터리 통: 검은 고무 통만 (파랑 · 초록 금지, 붉은 통은 머리등 빛에 살색으로 떠서 뺐다)
BEZELS = ("black", "black", "bare")           # 머리 테: 검정 · 맨 쇠 (사진의 붉은 · 노란 테는 머리등 빛에 과녁처럼 떠서 뺐다)


class _Parts:
    """재질 이름마다 그물 하나 (둥근 옆면만 부드럽게, 상자 모서리는 날카롭게)"""
    def __init__(s, mats): s.mats, s.bm = mats, {}
    def __getitem__(s, k):
        if k not in s.bm: s.bm[k] = bmesh.new()
        return s.bm[k]
    def finish(s, prefix):
        out = []
        for k, bm in s.bm.items():
            o = obj("%s_%s" % (prefix, k), bm, s.mats[k], smooth=True)
            try: o.data.set_sharp_from_angle(angle=math.radians(40))
            except Exception: pass
            out.append(o)
        return out


def _prism(bm, c, s, ch, R=None):
    """세로 모서리 넷을 ch 만큼 죽인 상자 (여덟모 기둥) — 배터리 통. c = 가운데"""
    R = R or Matrix.Identity(3); c = Vector(c); hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    ring = ((hx - ch, -hy), (hx, -hy + ch), (hx, hy - ch), (hx - ch, hy), (-hx + ch, hy), (-hx, hy - ch), (-hx, -hy + ch), (-hx + ch, -hy))
    a = [bm.verts.new(c + R @ Vector((x, y, -hz))) for x, y in ring]; b = [bm.verts.new(c + R @ Vector((x, y, hz))) for x, y in ring]
    for i in range(8): bm.faces.new((a[i], a[(i + 1) % 8], b[(i + 1) % 8], b[i]))
    bm.faces.new(a[::-1]); bm.faces.new(b)


def _lathe(bm, c, a, prof, seg=10):
    """축 a 둘레로 돌린 닫힌 덩어리 (오목한 반사경). prof = [(반지름, 축 따라 거리)] — 첫 점과 끝 점은 축 위"""
    q = a.to_track_quat("Z", "Y").to_matrix(); c = Vector(c)
    rings = [[bm.verts.new(c + q @ Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), z))) for k in range(seg)] for r, z in prof[1:-1]]
    v0 = bm.verts.new(c + a * prof[0][1]); v1 = bm.verts.new(c + a * prof[-1][1])
    for k in range(seg):
        n = (k + 1) % seg; bm.faces.new((v0, rings[0][k], rings[0][n])); bm.faces.new((v1, rings[-1][n], rings[-1][k]))
        for A, B in zip(rings, rings[1:]): bm.faces.new((A[k], A[n], B[n], B[k]))


def _battery(D, c, case, R=None):
    """배터리 통. c = 밑면 가운데, 넓은 면(허리띠 고리) = −y, 고무 목이 나가는 끝 = +x. 돌려준 값 = 전선의 첫 두 점 (굵은 고무 목 — _cable 이 굵게 만든다)"""
    R = R or Matrix.Identity(3); c = Vector(c); P = lambda x, y, z: c + R @ Vector((x, y, z))
    _prism(D[case], P(0, 0, 0.075), (0.125, 0.05, 0.15), 0.012, R)
    box(D["bare"], P(0, 0, 0.165), (0.137, 0.06, 0.03), R)                      # 통보다 넓은 쇠 뚜껑
    for sx in (-1, 1): box(D[case], P(sx * 0.036, -0.029, 0.098), (0.022, 0.012, 0.07), R)   # 허리띠 고리
    return [P(0.06, 0, 0.166), P(0.092, 0, 0.166)]


def _cable(cb, pts):
    """안전등 전선 (지름 1 cm, 여섯 모 — 가늘어서 모가 안 보인다). 첫 두 점 사이는 굵은 고무 목, 그 뒤로 가늘어진다"""
    sweep(cb, pts, 0.005, 6, r_fn=lambda i: 0.011 if i < 2 else 0.005)


def _head(D, c, ax, bezel):
    """안전등 머리. c = 테 앞 가운데, ax = 빛이 나가는 쪽. 돌려준 값 = 전선이 들어가는 뒤 끝.
    테는 속이 빈 고리이고 그 안에 오목한 쇠 반사경과 전구가 들어 있다 (납작한 흰 원판은 과녁처럼 보였다)"""
    c, a = Vector(c), Vector(ax).normalized()
    cyl(D["black"], c - a * 0.070, c - a * 0.022, 0.022, 10, r1=0.036)          # 몸 (뒤로 갈수록 가늘다)
    tube(D[bezel], c - a * 0.026, c, 0.044, 0.0352, 10)                         # 테
    _lathe(D["bare"], c, a, ((0, -0.022), (0.035, -0.004), (0.035, -0.025), (0, -0.025)))   # 반사경 (가운데가 2 cm 들어간다)
    cyl(D["black"], c - a * 0.023, c - a * 0.015, 0.014, 6)                     # 전구 소켓 (밝은 반사경 가운데의 검은 점 — k05)
    cyl(D["glass"], c - a * 0.016, c - a * 0.005, 0.008, 6, r1=0.005)           # 전구
    return c - a * 0.066


def _angle(bm, x, y, sx, sy, z0, z1, w=0.06, t=0.006):
    """ㄱ 쇠 기둥: 모서리 (x, y) 에서 날개가 sx · sy 쪽으로 뻗는다"""
    h = z1 - z0; zc = (z0 + z1) / 2
    box(bm, (x + sx * w / 2, y + sy * t / 2, zc), (w, t, h)); box(bm, (x + sx * t / 2, y + sy * w / 2, zc), (t, w, h))


def _numbers(mats, items):
    """번호 글자를 그물 하나로 모은다 (납작한 홑면 — 앞(−y)만 보이면 된다).
    _util.text_mesh 와 같은 방법이지만 곡선을 성기게(resolution 2) 굽는다 — 기본값 12 로는 번호 30 개에 삼각형 7,800 이 든다"""
    bm = bmesh.new(); font = bpy.data.fonts.load("C:/Windows/Fonts/malgunbd.ttf", check_existing=True)
    for body, loc, size in items:
        cu = bpy.data.curves.new("LAMPRACK_NUM_TMP", "FONT"); cu.body = body; cu.size = size; cu.align_x = "CENTER"; cu.resolution_u = 2; cu.font = font
        t = bpy.data.objects.new("LAMPRACK_NUM_TMP", cu); t.location = loc; t.rotation_euler = (math.radians(90), 0, 0); bpy.context.scene.collection.objects.link(t); bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(t.evaluated_get(bpy.context.evaluated_depsgraph_get())); me.transform(t.matrix_world); bm.from_mesh(me)
        bpy.data.meshes.remove(me); bpy.data.objects.remove(t, do_unlink=True); bpy.data.curves.remove(cu)
    o = obj("NOCOL_LAMPRACK_NUMBERS", bm, mats["black"])
    for p in o.data.polygons:
        if p.normal.y > 0: p.flip()                                              # 자동 맞춤이 뒤집은 글자를 되돌린다
    return o


def build(mats, width=2.4, tiers=3, slots=10, filled=0.7, seed=0, tags=1, charger=True):
    """충전대 하나. filled = 안전등이 꽂힌 칸의 몫, tags = 빈 칸 걸쇠에 달린 종이 꼬리표 수, charger = 위의 계기 함"""
    rnd = random.Random(seed); F = _Parts(mats); D = _Parts(mats); cb = bmesh.new(); nums = []
    hw = width / 2; yf = -DEP; H = SHELF0 + (tiers - 1) * PITCH + GAP + RAIL_H + 0.015; span = width - 0.12
    # 틀: ㄱ 쇠 다리 넷 + 뒤 가운데 띠쇠 + 꼭대기 옆 가로대
    fr = F["bare"]
    for x, y, sx, sy in ((-hw, yf, 1, 1), (hw, yf, -1, 1), (-hw, 0, 1, -1), (hw, 0, -1, -1)): _angle(fr, x, y, sx, sy, 0, H)
    box(fr, (0, -0.003, H / 2), (0.06, 0.006, H))
    for sx in (-1, 1): box(fr, (sx * (hw - 0.02), -DEP / 2, H - 0.015), (0.03, DEP - 0.012, 0.03))
    box(F["iron"], (0, yf + 0.015, SHELF0 - 0.10), (span, 0.03, 0.03))           # 맨 아래 선반 밑 쇠막대
    ps = (span - 0.08) / slots; x0 = -ps * slots / 2; yb = yf + 0.13; left = tags
    lit = set(rnd.sample(range(tiers * slots), round(filled * tiers * slots)))   # 꽂힌 칸 (수를 딱 맞춘다 — 씨앗이 바뀌어도 삼각형 수가 같다)
    for t in range(tiers):
        zs = SHELF0 + (tiers - 1 - t) * PITCH; zr = zs + GAP; low = t == tiers - 1; hung = False
        box(F["white"], (0, yf + 0.06, zr + RAIL_H / 2), (span, 0.12, RAIL_H))   # 레일
        box(F["iron"], (0, yf + 0.065, zr + RAIL_H + 0.0075), (span, 0.13, 0.015))   #   위 검은 띠
        box(D["rust"], (0, yf - 0.0005, zr + 0.008), (span, 0.001, 0.012))       #   번호 밑 누런 때 띠
        box(F["iron"], (-hw + 0.03, yf - 0.014, zr + 0.065), (0.06, 0.03, 0.075))   #   왼쪽 끝 이음 함 (쇠 관이 여기로 들어온다)
        box(F["iron"], (0, -DEP / 2, zs - 0.015), (width - 0.014, DEP - 0.014, 0.03))   # 선반
        box(F["iron"], (0, yf + 0.006, zs - 0.005), (span, 0.012, 0.05))         #   앞 턱
        for k in range(slots + 1): box(D["iron"], (x0 + ps * k, yb, zs + 0.015), (0.018, 0.10, 0.03))   #   칸막이 토막
        for i in range(slots):
            x = x0 + ps * (i + 0.5); zc = zr + 0.093; full = t * slots + i in lit
            cyl(D["black"], (x, yf + 0.002, zc), (x, yf - 0.008, zc), 0.032, 12)            # 칸 계기: 검은 테
            cyl(D["glass"], (x, yf - 0.006, zc), (x, yf - 0.0095, zc), 0.022, 10)           #   밝은 눈금판
            box(D["iron"], (x, yf - 0.0100, zc), (0.004, 0.002, 0.030), Matrix.Rotation(rnd.uniform(0.2, 0.8) if full else -0.85, 3, "Y"))   #   바늘 (충전 중이면 오른쪽, 빈 칸은 왼쪽 끝)
            nums.append((str(t * slots + i + 1), (x, yf - 0.0015, zr + 0.019), 0.052))
            box(D["iron"], (x - 0.04, yf + 0.035, zr - 0.035), (0.04, 0.05, 0.07))          # 충전 걸쇠 (레일 밑으로 내려온 검은 몸)
            if not full:                                                                    # 빈 칸: 쇠 집게만 보인다
                box(D["bare"], (x - 0.04, yf + 0.006, zr - 0.058), (0.03, 0.012, 0.03)); hung = False
                if left > 0 and rnd.random() < 0.5:
                    left -= 1; R = Matrix.Rotation(rnd.uniform(-0.25, 0.25), 3, "Y")          # 종이 꼬리표: 집게에 건 끈 + 표
                    box(D["iron"], (x - 0.04, yf - 0.002, zr - 0.0875), (0.005, 0.004, 0.075))
                    box(D["plank"], Vector((x - 0.04, yf - 0.002, zr - 0.12)) + R @ Vector((0, 0, -0.045)), (0.045, 0.004, 0.09), R)
                continue
            bx = x + 0.04 + rnd.uniform(-0.008, 0.008); j = rnd.uniform(-0.008, 0.008); style = rnd.random(); bz = rnd.choice(BEZELS)
            s = -1 if low else 1 if hung else rnd.choice((-1, 1)); hung = False              # 전선 고리가 늘어지는 쪽
            g = _battery(D, (bx, yb + rnd.uniform(-0.006, 0.006), zs), rnd.choice(CASES), Matrix.Rotation(-math.pi / 2 + rnd.uniform(-0.1, 0.1), 3, "Z"))   # 좁은 면이 앞, 고무 목이 앞으로
            n1 = g[1]
            if style < 0.15 and not low and i < slots - 1:   # 걸쇠에 안 걸고 둔 것: 머리가 선반 앞 턱 너머로 전선에 매달려 아래 레일 앞에 늘어져 있다
                hung = True; hc = Vector((x + ps / 2 + j, yf - 0.05, zs - 0.105)); hb = _head(D, hc, (rnd.uniform(-0.2, 0.2), -0.3, -1), bz)
                pts = g + [n1 + Vector((0.012, -0.02, -0.008)), (bx + 0.045, yf, zs + 0.11), (hc.x - 0.01, yf - 0.018, zs + 0.035), (hc.x - 0.003, yf - 0.03, zs - 0.01), hb]
            elif style < 0.15:             # 맨 아래 층 · 오른쪽 끝 칸에서는 매달 데가 없다 → 머리를 통 옆 선반에 눕혀 놓았다
                hc = Vector((bx - 0.078, yf + 0.05, zs + 0.046)); hb = _head(D, hc, (-0.3, -1, 0.1), bz)
                pts = g + [n1 + Vector((-0.012, -0.012, -0.012)), (bx - 0.05, yf + 0.045, zs + 0.13), (hb.x + 0.01, hb.y + 0.02, hb.z + 0.05), hb]
            else:                          # 걸쇠에 물린 것: 유리가 앞 아래를 본다
                hc = Vector((x - 0.04 + j, yf - 0.03, zr - 0.105)); hb = _head(D, hc, (rnd.uniform(-0.15, 0.15), -1, rnd.uniform(-0.8, -0.35)), bz)
                e = hb + Vector((s * 0.03, 0.004, -0.018))
                if style < 0.62:   # 전선이 통 옆에서 선반 앞으로 늘어졌다가 올라온다 (사진의 처진 고리 — 폭 · 깊이가 제각각)
                    w = rnd.uniform(0.045, 0.08); zb = zs + rnd.uniform(-0.05, 0.04)
                    pts = g + [n1 + Vector((s * 0.012, -0.02, -0.012)), (bx + s * w * 0.7, yf - 0.014, zs + 0.09), (bx + s * w, yf - 0.02, zb + 0.03), (bx + s * (w + 0.022), yf - 0.022, zb),
                               (bx + s * (w + 0.044), yf - 0.02, zb + 0.03), (bx + s * (w + 0.04), yf - 0.008, zs + 0.13), e, hb]
                else:              # 전선이 통 옆 선반 위에 한 번 누웠다가 올라간다
                    pts = g + [n1 + Vector((s * 0.012, -0.012, -0.02)), (bx + s * 0.045, yf + 0.035, zs + 0.07), (bx + s * 0.06, yf + 0.04, zs + 0.008), (bx + s * 0.10, yf + 0.06, zs + 0.006),
                               (bx + s * 0.125, yf + 0.04, zs + 0.008), (bx + s * 0.11, yf + 0.016, zs + 0.05), (bx + s * 0.08, yf, zs + 0.13), e, hb]
            _cable(cb, pts)
    cyl(F["iron"], (-hw + 0.03, yf - 0.012, SHELF0 + GAP + 0.03), (-hw + 0.03, yf - 0.012, H + (0.01 if charger else -0.02)), 0.012, 10)   # 층마다 전기를 나르는 쇠 관 (왼쪽 앞 기둥을 타고 내려온다)
    if charger:   # 계기 함 (1981 사진): 꼭대기 왼쪽 끝에 얹혀 있다. 쇠 관이 밑에서 들어오고, 위로 나간 관은 벽으로 들어간다
        cx, bh, yc = -hw + 0.27, 0.30, yf + 0.125; cz = H + bh / 2; yd = yf - 0.042
        box(F["bare"], (cx, yc, cz), (0.52, 0.31, bh)); box(F["bare"], (cx, yf - 0.036, cz), (0.46, 0.012, bh - 0.06))   # 함 + 문
        for z in (cz - 0.08, cz + 0.08): cyl(D["iron"], (cx - 0.23, yd, z - 0.03), (cx - 0.23, yd, z + 0.03), 0.008, 10)   # 경첩
        for dx in (-0.09, 0.09):
            p = Vector((cx + dx, yd, cz + 0.035))
            tube(D["iron"], p, p + Vector((0, -0.018, 0)), 0.058, 0.048, 12)                 # 계기 테 (눈금판이 테 안으로 들어가 있다)
            cyl(D["white"], p, p + Vector((0, -0.006, 0)), 0.048, 12)                        #   눈금판
            box(D["black"], p + Vector((0.012, -0.007, 0.005)), (0.05, 0.002, 0.005), Matrix.Rotation(math.radians(-35 * (1 if dx > 0 else 2)), 3, "Y"))   #   바늘
        box(D["iron"], (cx + 0.19, yd - 0.006, cz - 0.07), (0.035, 0.012, 0.07))             # 문 손잡이
        sweep(F["iron"], [(cx + 0.15, -0.10, cz + bh / 2 - 0.01), (cx + 0.15, -0.10, cz + bh / 2 + 0.05), (cx + 0.15, -0.07, cz + bh / 2 + 0.08), (cx + 0.15, 0.0, cz + bh / 2 + 0.08)], 0.014, 10)   # 벽으로 들어가는 관
    cable = obj("NOCOL_LAMPRACK_CABLES", cb, mats["rubber"], smooth=True)
    return F.finish("LAMPRACK") + D.finish("NOCOL_LAMPRACK") + [cable, _numbers(mats, nums)]


def counter(mats, width=1.6, seed=0):
    """안전등 내주는 대: 네 귀 기둥 + 기둥 사이를 막은 세로 판자(위아래 가로 띠에 못) + 두꺼운 판자 상판.
    위에 펼친 장부 · 안전등 셋(둘은 통을 세우고 머리를 앞에 눕혔다 — k04 · k05 사진의 놓임새, 하나는 통째 누웠다) · 예비 전구 상자"""
    rnd = random.Random(seed + 3); F = _Parts(mats); D = _Parts(mats); cb = bmesh.new()
    hw = width / 2; dep = 0.6; z0 = 0.90; lx, ly = hw - 0.045, dep / 2 - 0.045; span = width - 0.18
    for sx in (-1, 1):
        for sy in (-1, 1): box(F["timber"], (sx * lx, sy * ly, 0.4275), (0.09, 0.09, 0.855))       # 네 귀 기둥 (앞에서 양 끝 기둥이 보인다)
        box(F["timber"], (sx * lx, 0, 0.80), (0.05, dep - 0.18, 0.10))                             # 옆 가로대 (위)
        box(F["timber"], (sx * lx, 0, 0.265), (0.05, dep - 0.18, 0.05))                            #   (아래 — 선반을 받친다)
        for k in range(3): box(F["tar"], (sx * (lx + 0.02), -0.21 + 0.14 * (k + 0.5), 0.4275), (0.02, 0.137, 0.855))   # 옆을 막은 판자
    box(F["timber"], (0, ly, 0.80), (span, 0.05, 0.10))                                            # 뒤 가로대
    box(F["plank"], (0, 0.03, 0.3025), (width - 0.14, 0.42, 0.025))                                # 아래 선반
    n = max(2, round(span / 0.14)); bw = span / n
    for i in range(n): box(F["tar"], (-span / 2 + bw * (i + 0.5), -ly - 0.015, 0.4275), (bw - 0.006, 0.02, 0.855))   # 앞을 막은 세로 판자 (기둥 면보다 2 cm 들어가 있다, 바닥까지)
    box(D["black"], (0, -ly - 0.004, 0.4275), (span, 0.002, 0.855))                                #   판자 뒤 검은 덧판 (틈으로 속 선반이 비쳐 줄무늬가 생겼다 → 틈은 검은 줄로만 보인다)
    for z, h in ((0.07, 0.14), (0.79, 0.10)):   # 걸레받이 · 윗띠 (기둥 면과 나란하다) + 판자마다 못 머리
        box(F["plank"], (0, -ly - 0.035, z), (span, 0.02, h))
        for i in range(n): box(D["iron"], (-span / 2 + bw * (i + 0.5) + rnd.uniform(-0.03, 0.03), -ly - 0.046, z + rnd.uniform(-0.02, 0.02)), (0.012, 0.004, 0.012))
    for k in range(4):   # 상판 판자 넉 장 (두께 4.5 cm, 끝이 들쭉날쭉, 앞으로 3 cm 나온다)
        box(F["plank"], (rnd.uniform(-0.008, 0.008), -0.33 + 0.1575 * (k + 0.5), z0 - 0.0225), (width + 0.04 - rnd.uniform(0, 0.02), 0.155, 0.045))
    # 장부: 펼쳐 놓은 두 쪽 + 적은 줄 + 연필
    R = Matrix.Rotation(math.radians(7), 3, "Z"); c = Vector((-0.6 * hw, -0.08, z0)); P = lambda x, y, z: c + R @ Vector((x, y, z))
    box(D["black"], P(0, 0, 0.004), (0.42, 0.29, 0.008), R)
    for sx in (-1, 1): box(D["white"], P(sx * 0.102, 0, 0.016), (0.196, 0.27, 0.016), R)
    for k in range(8):
        if k < 6: box(D["iron"], P(-0.102, 0.10 - 0.034 * k, 0.0245), (0.15, 0.005, 0.001), R)
        else: box(D["iron"], P(0.085, 0.10 - 0.034 * (k - 6), 0.0245), (0.11, 0.005, 0.001), R)
    cyl(D["iron"], P(0.03, -0.09, 0.029), P(0.17, -0.04, 0.029), 0.004, 6)
    # 안전등 셋
    Rx = Matrix.Rotation(math.radians(-90), 3, "X")
    for fx, y, deg, lying in ((-0.06, 0.03, 8, False), (0.40, 0.07, -14, False), (0.88, -0.14, 12, True)):
        Rz = Matrix.Rotation(math.radians(deg + rnd.uniform(-4, 4)), 3, "Z"); T = lambda x, y_, z=0.006: Vector((fx * hw, y, z0 + z)) + Rz @ Vector((x, y_, 0))
        if lying:   # 통이 등을 대고 눕고, 전선이 한 바퀴 돌아 옆에 누운 머리로 간다
            g = _battery(D, (fx * hw, y, z0 + 0.03), rnd.choice(CASES), Rz @ Rx)
            hb = _head(D, T(-0.15, 0.12, 0.046), Rz @ Vector((-0.29, -0.96, 0.3)), rnd.choice(BEZELS))
            pts = g + [T(0.125, 0.185, 0.015), T(0.10, 0.24), T(0.0, 0.285), T(-0.10, 0.25), T(-0.135, 0.20, 0.02), hb]
        else:       # 통은 넓은 면(허리띠 고리)을 앞으로 하고 서 있고, 머리는 그 앞 왼쪽에 누워 유리가 받는 사람을 본다
            g = _battery(D, (fx * hw, y, z0), rnd.choice(CASES), Rz)
            hb = _head(D, T(-0.125, -0.115, 0.046), Rz @ Vector((-0.25, -1, 0.25)), rnd.choice(BEZELS))
            pts = g + [T(0.105, -0.03, 0.155), T(0.075, -0.06, 0.10), T(0.025, -0.075, 0.035), T(-0.03, -0.08, 0.008), T(-0.075, -0.06, 0.014), hb]   # 전선은 뚜껑 끝에서 앞으로 돌아 통 앞면을 비스듬히 가로질러 머리로 간다 (통 옆으로 둥글게 벌리면 손잡이 달린 컵으로 보였다)
        _cable(cb, pts)
    # 예비 전구 상자: 나무 상자에 유리 전구 넷 + 갈아 끼울 머리 테 둘
    b = Vector((-0.3 * hw, 0.19, z0)); t = D["plank"]
    box(t, b + Vector((0, 0, 0.004)), (0.20, 0.14, 0.008))
    for sy in (-1, 1): box(t, b + Vector((0, sy * 0.066, 0.03)), (0.20, 0.008, 0.06))
    for sx in (-1, 1): box(t, b + Vector((sx * 0.096, 0, 0.03)), (0.008, 0.124, 0.06))
    for k in range(4):
        p = b + Vector((-0.07 + 0.03 * k, -0.02 + rnd.uniform(-0.012, 0.012), 0.02)); d = Vector((rnd.uniform(-0.3, 0.3), 1, 0)).normalized()
        cyl(D["glass"], p, p + d * 0.026, 0.012, 10); cyl(D["bare"], p - d * 0.016, p, 0.008, 10)
    for k, key in enumerate(("bare", "black")):
        p = b + Vector((0.048 - 0.006 * k, 0.008 * k, 0.008 + 0.022 * k)); tube(D[key], p, p + Vector((0, 0, 0.022)), 0.044, 0.0352, 12)
    cable = obj("NOCOL_LAMPCOUNTER_CABLES", cb, mats["rubber"], smooth=True)
    return F.finish("LAMPCOUNTER") + D.finish("NOCOL_LAMPCOUNTER") + [cable]
