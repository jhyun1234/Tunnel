"""ART-1 차례 3 — Blender 로 만드는 광장 물건 (첫 모양). 제안서 docs/제안서_ART1_현실감_광장_시험.md.
props_candidates.py 가 불러 후보 그림을 찍는다. 치수 = 조사 09(광산시설) · 사진 공통점(제안서 ART-1 표) · 어림(표시).
좌표: Blender Z 위, 단위 m. 물건은 원점(바닥 가운데)에 만들고 부르는 쪽이 옮긴다. 재질은 CC0 질감(상자 투영 — 후보 그림용, 게임에 넣을 때 UV 로)."""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

def pbr(name, color, rough, normal, size_m=1.0, tint=(1, 1, 1), metal=0.0, sat=1.0):
    """CC0 질감 셋(색 · 거칠기 · 노멀 GL)을 물체 좌표 상자 투영으로 — size_m = 질감 한 장 크기(m)"""
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / size_m,) * 3
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def img(path, data):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(path, check_existing=True)
        if data: n.image.colorspace_settings.name = "Non-Color"
        n.projection = "BOX"; n.projection_blend = 0.25
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    c = img(color, False)
    hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = sat   # 주황 녹 → 탄가루 낀 짙은 쇠 (사진: 녹은 흑백 사진이 많아 판단 못 함, 갱내 쇠는 짙다)
    nt.links.new(c.outputs["Color"], hs.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 1.0
    nt.links.new(hs.outputs["Color"], mix.inputs["A"]); mix.inputs["B"].default_value = (*tint, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(img(rough, True).outputs["Color"], b.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(img(normal, True).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = metal
    return m

def flat(name, rgb, rough=0.6, metal=0.0, emit=None):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit: b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = 3.0
    return m


def materials(root):
    """물건 재질 한 벌 (CC0 질감: build/art/cand_tex/ 1K · 석탄은 Assets/Tunnel/Art). 쇠는 채도를 낮춰 탄가루 낀 짙은 쇠로"""
    CT = os.path.join(root, "build", "art", "cand_tex"); ART = os.path.join(root, "Assets", "Tunnel", "Art", "textures")
    def T(i, s): return os.path.join(CT, "%s_%s.jpg" % (i, s))
    return dict(steel=pbr("M_Steel", T("rusty_metal_03", "Color"), T("rusty_metal_03", "Roughness"), T("rusty_metal_03", "NormalGL"), 1.0, tint=(0.55, 0.52, 0.5), metal=0.6, sat=0.3),
             dark_steel=pbr("M_DarkSteel", T("rusty_metal_03", "Color"), T("rusty_metal_03", "Roughness"), T("rusty_metal_03", "NormalGL"), 0.6, tint=(0.32, 0.31, 0.3), metal=0.6, sat=0.2),
             paint=pbr("M_Paint", T("rusty_painted_metal", "Color"), T("rusty_painted_metal", "Roughness"), T("rusty_painted_metal", "NormalGL"), 1.5, tint=(0.7, 0.7, 0.65), sat=0.55),
             wood=pbr("M_Wood", T("weathered_brown_planks", "Color"), T("weathered_brown_planks", "Roughness"), T("weathered_brown_planks", "NormalGL"), 1.5, tint=(0.6, 0.55, 0.5)),
             plank=pbr("M_Plank", T("wood_planks_dirt", "Color"), T("wood_planks_dirt", "Roughness"), T("wood_planks_dirt", "NormalGL"), 1.5, tint=(0.7, 0.65, 0.6)),
             log=pbr("M_Log", T("weathered_brown_planks", "Color"), T("weathered_brown_planks", "Roughness"), T("weathered_brown_planks", "NormalGL"), 1.0, tint=(0.45, 0.38, 0.32)),
             coal=pbr("M_Coal", os.path.join(ART, "art_coal_Rock035_DiffRough.png"), T("Rock035", "Roughness"), os.path.join(ART, "art_coal_Rock035_nor_gl.jpg"), 0.5, tint=(0.4, 0.4, 0.45)))

UV_M = dict(steel=1.0, dark_steel=0.6, paint=1.5, wood=1.5, plank=1.5, log=1.0, coal=0.5, coal_lump=0.3, coal_fresh=0.3,
            timber=None, log_end=None, wedge=None, lagging=None)   # None = 그물이 UV 를 직접 가짐 (통나무 옆 = 둘레·길이 m, 잘린 끝 = 원, 판자 = 길이·폭 m — 결이 길이 방향)   # 질감 한 장 크기 m (materials 와 같은 값)

def game_materials(root):
    """게임용 재질 (glTF 로 나감): props_tex 그림(prop_textures.py 가 채도·색까지 구움) + UV 한 벌. arm = (1, 거칠기, 쇠)"""
    TX = os.path.join(root, "Assets", "Tunnel", "Art", "props_tex"); out = {}
    for k, size in UV_M.items():
        m = bpy.data.materials.new("PM_" + k); m.use_nodes = True
        if size: m["uv_m"] = size
        nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        def img(suf, data):
            n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(os.path.join(TX, k + suf), check_existing=True)
            if data: n.image.colorspace_settings.name = "Non-Color"
            return n
        nt.links.new(img("_Diffuse.jpg", False).outputs["Color"], b.inputs["Base Color"])
        sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(img("_arm.jpg", True).outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"]); nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
        nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(img("_nor_gl.jpg", True).outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        out[k] = m
    return out

def box_uv(me, uv_per_m):
    """상자 투영 UV (그물 좌표): 면마다 가장 큰 법선 축을 빼고 나머지 두 축으로 — 후보 그림의 물체 좌표 상자 투영과 같은 모양"""
    if not me.uv_layers: me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        n = poly.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a, b = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
            uv[li].uv = (a * uv_per_m, b * uv_per_m)

# ---------- 도형 (bmesh 에 더하기)
def box(bm, c, s, rot=Matrix.Identity(3)):
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(Vector(c)) @ rot.to_4x4() @ Matrix.Diagonal((*s, 1)))

def rod(bm, a, b, r, seg=10, r2=None):
    a, b = Vector(a), Vector(b); d = b - a; L = d.length
    q = d.normalized().to_track_quat("Z", "Y")
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=L,
                          matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4())

def ibeam(bm, a, b, h=0.16, w=0.1, t=0.012):
    """I 형 강철: 가운데 판 + 위아래 날개. a→b 방향, 날개는 '위' = 월드 Z 와 방향이 가장 먼 쪽"""
    a, b = Vector(a), Vector(b); d = (b - a).normalized(); L = (b - a).length
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, 1, 0))
    side = d.cross(up).normalized(); up = side.cross(d).normalized()
    R = Matrix((side, up, d)).transposed(); m = (a + b) / 2
    box(bm, m, (t, h, L), R)
    for s in (-1, 1): box(bm, m + up * (s * (h / 2 - t / 2)), (w, t, L), R)

def obj(name, bm, mat, loc=(0, 0, 0), smooth=False, coll=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); o.location = loc
    (coll or bpy.context.scene.collection).objects.link(o); return o

def group(name, objs, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    for o in objs: o.parent = e
    e.location = loc; return e

# ---------- 물건
def rails(M, length=6.0, gauge=0.6, switch=False):
    """레일(협궤 0.6 m) + 나무 침목 0.6 m 마다. switch = 한쪽으로 갈라지는 갈림 레일(곡선 반지름 6 m, 20°)"""
    bm = bmesh.new(); sl = bmesh.new()
    def line(p0, dirv, L, lat):
        for s in (-1, 1):
            a = Vector(p0) + lat * (s * gauge / 2)
            ibeam(bm, a + Vector((0, 0, 0.145)), a + dirv * L + Vector((0, 0, 0.145)), h=0.09, w=0.06, t=0.014)
    X = Vector((1, 0, 0)); Y = Vector((0, 1, 0))
    line((-length / 2, 0, 0), X, length, Y)
    n = int(length / 0.6)
    for i in range(n + 1):
        box(sl, (-length / 2 + i * 0.6, 0, 0.05), (0.16, gauge + 0.5, 0.1))
    if switch:
        R = 6.0; steps = 8; ang = math.radians(20)
        for s in (-1, 1):
            prev = None
            for k in range(steps + 1):
                t = ang * k / steps
                p = Vector((R * math.sin(t), R - R * math.cos(t), 0)) + Vector((-math.sin(t), math.cos(t), 0)) * (s * gauge / 2)
                p = p + Vector((0, 0, 0.145))
                if prev is not None: ibeam(bm, prev, p, h=0.09, w=0.06, t=0.014)
                prev = p
    o1 = obj("Rails", bm, M["steel"]); o2 = obj("Sleepers", sl, M["wood"])
    return group("PROP_Rails", [o1, o2])

def rails_path(M, path, floor_z, name="Rails", gauge=0.6, step=0.6):
    """꺾은 선(path = [(x, y)], 부르는 쪽이 매끈하게) 을 따라 레일 — 침목을 step m 마다 그 자리 바닥(floor_z(x, y))에 조금 묻어 놓고, 레일은 침목 윗면을 잇는다"""
    P = [Vector((x, y, 0)) for x, y in path]
    L = [0.0]
    for a, b in zip(P, P[1:]): L.append(L[-1] + (b - a).length)
    def at(s):
        for i in range(len(P) - 1):
            if s <= L[i + 1] + 1e-9:
                t = (s - L[i]) / max(L[i + 1] - L[i], 1e-9); return P[i].lerp(P[i + 1], t), (P[i + 1] - P[i]).normalized()
        return P[-1], (P[-1] - P[-2]).normalized()
    n = max(2, int(L[-1] / step) + 1); samp = []
    for k in range(n):
        p, d = at(min(k * step, L[-1])); lat = Vector((-d.y, d.x, 0))
        z = sum(floor_z(q.x, q.y) for q in (p, p + lat * 0.45, p - lat * 0.45)) / 3 - 0.03
        samp.append((Vector((p.x, p.y, z)), d, lat))
    bm = bmesh.new(); sl = bmesh.new()
    for p, d, lat in samp:
        box(sl, p + Vector((0, 0, 0.05)), (0.16, gauge + 0.5, 0.1), Matrix.Rotation(math.atan2(d.y, d.x), 3, "Z"))
    for (p0, d0, l0), (p1, d1, l1) in zip(samp, samp[1:]):
        for s_ in (-1, 1):
            ibeam(bm, p0 + l0 * (s_ * gauge / 2) + Vector((0, 0, 0.145)), p1 + l1 * (s_ * gauge / 2) + Vector((0, 0, 0.145)), h=0.09, w=0.06, t=0.014)
    return group("PROP_" + name, [obj(name, bm, M["steel"]), obj(name + "_Sleepers", sl, M["wood"])])

def mine_car(M, coal=True):
    """광차: 바닥 1.3 × 0.75 · 위 1.5 × 0.9 · 높이 0.65 m 사다리꼴 쇠 통, 바퀴 넷(지름 0.3, 궤간 0.6), 앞뒤 연결고리, 석탄 싣기"""
    bm = bmesh.new(); z0 = 0.33
    bl, bw, tl, tw, h, th = 1.3, 0.75, 1.5, 0.9, 0.65, 0.035
    def ring(l, w, z): return [Vector((sx * l / 2, sy * w / 2, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for inset in (0.0, th):                                   # 바깥 · 안 벽 (두께)
        lo, hi = ring(bl - 2 * inset, bw - 2 * inset, z0 + inset), ring(tl - 2 * inset, tw - 2 * inset, z0 + h)
        vs = [bm.verts.new(v) for v in lo + hi]
        for i in range(4):
            f = [vs[i], vs[(i + 1) % 4], vs[4 + (i + 1) % 4], vs[4 + i]]
            bm.faces.new(f if inset == 0 else list(reversed(f)))
        bm.faces.new(list(reversed(vs[:4])) if inset == 0 else vs[:4])
    for sx in (-1, 1):                                        # 테두리 띠 · 바닥 보
        box(bm, (sx * (tl / 2 + 0.005), 0, z0 + h - 0.04), (0.04, tw + 0.04, 0.07))
        box(bm, (0, sx * (tw / 2 + 0.005), z0 + h - 0.04), (tl + 0.04, 0.04, 0.07))
        box(bm, (0, sx * 0.22, z0 - 0.06), (bl + 0.1, 0.08, 0.1))
        box(bm, (sx * (bl / 2 + 0.16), 0, z0 + 0.02), (0.25, 0.08, 0.06))   # 연결고리
        box(bm, (sx * (tl / 2 + 0.06), 0, z0 + 0.12), (0.08, 0.5, 0.14))    # 앞뒤 범퍼
    for sy in (-1, 1):                                        # 옆벽 보강 띠 셋 (비스듬한 벽을 따라) + 끝벽 하나
        for x in (-0.45, 0.0, 0.45):
            rod(bm, (x * bl / tl, sy * (bw / 2 + 0.015), z0), (x, sy * (tw / 2 + 0.015), z0 + h - 0.06), 0.018, seg=6)
    for sx in (-1, 1):
        rod(bm, (sx * (bl / 2 + 0.015), 0, z0), (sx * (tl / 2 + 0.015), 0, z0 + h - 0.06), 0.018, seg=6)
    for sy in (-1, 1):                                        # 테두리 리벳
        for k in range(13): box(bm, (-tl / 2 + 0.06 + k * (tl - 0.12) / 12, sy * (tw / 2 + 0.03), z0 + h - 0.04), (0.022, 0.012, 0.022))
    wh = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            rod(wh, (sx * 0.42, sy * 0.3 - 0.04 * sy, 0.15), (sx * 0.42, sy * 0.3 + 0.04 * sy, 0.15), 0.15, seg=16)
            rod(wh, (sx * 0.42, sy * 0.3 - 0.05 * sy, 0.15), (sx * 0.42, sy * 0.3 - 0.035 * sy, 0.15), 0.17, seg=16)   # 테(플랜지) — 레일 안쪽
            box(wh, (sx * 0.42, sy * 0.4, 0.2), (0.12, 0.1, 0.12))                                                     # 축 상자
        rod(wh, (sx * 0.42, -0.38, 0.15), (sx * 0.42, 0.38, 0.15), 0.03)
    parts = [obj("CarBody", bm, M["steel"]), obj("CarWheels", wh, M["dark_steel"])]
    if coal:
        cb = bmesh.new(); bmesh.ops.create_grid(cb, x_segments=14, y_segments=9, size=0.5)
        import random; rnd = random.Random(7)
        for v in cb.verts:
            v.co = Vector((v.co.x * (tl - 0.1), v.co.y * (tw - 0.1), z0 + h - 0.12 + 0.18 * (1 - (2 * v.co.x) ** 2) * (1 - (2 * v.co.y) ** 2) + rnd.uniform(-0.03, 0.03)))
        parts.append(obj("CarCoal", cb, M["coal"], smooth=True))
    return group("PROP_MineCar", parts)

def coal_heap(M, L, W, z_edge, peak, cx=0.0, n=1600, seed=5):
    """석탄 무더기 (조사 10 · 11 사진: 검은 잔 알갱이 위에 모난 덩어리, 테두리 위로 봉긋).
    가루 언덕(울퉁불퉁 ±2 cm, 석탄 질감) + 덩어리 n 개(1.5~7 cm, 작은 것이 많게) — 덩어리는 뭉툭한 다면체(깨진 상자 모양 점 14 개의 볼록 껍질).
    판 1(점 9~18 개 뾰족한 결정 · 거칠기 0.16 유리)은 "현실적이 아니다 · 빛 반사가 심하다"(09-27 판정 ③) → 무딘 모양 · 반쯤 무광(coal_lump 거칠기 0.5~0.75 얼룩)"""
    import random; rnd = random.Random(seed); hx, hy = L / 2, W / 2
    def h(x, y):
        u, w_ = (x - cx) / hx, y / hy
        return z_edge + peak * max(0.0, 1 - u * u) ** 0.8 * max(0.0, 1 - w_ * w_) ** 0.8
    fb = bmesh.new(); bmesh.ops.create_grid(fb, x_segments=40, y_segments=20, size=0.5)
    for v in fb.verts:
        x, y = cx + 2 * v.co.x * hx, 2 * v.co.y * hy; v.co = Vector((x, y, h(x, y) + rnd.uniform(-0.02, 0.02)))
    lb = bmesh.new()
    corners = [Vector((sx, sy, sz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)] + [Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
    for i in range(n):
        sz = 0.015 + 0.055 * rnd.random() ** 1.8
        x, y = cx + rnd.uniform(-hx + sz, hx - sz), rnd.uniform(-hy + sz, hy - sz)
        R = Matrix.Rotation(rnd.uniform(0, 6.3), 3, "Z") @ Matrix.Rotation(rnd.uniform(0, 6.3), 3, "X") @ Matrix.Rotation(rnd.uniform(0, 6.3), 3, "Y")
        c = Vector((x, y, h(x, y) - sz * 0.25)); sq = Vector((1.0, rnd.uniform(0.65, 1.0), rnd.uniform(0.5, 0.85)))
        vs = [lb.verts.new(c + R @ Vector([q * s_ * sz * 0.62 * rnd.uniform(0.75, 1.15) for q, s_ in zip(p_ * (0.8 if p_.length > 1.2 else 1.25), sq)])) for p_ in corners]
        r = bmesh.ops.convex_hull(lb, input=vs)
        bmesh.ops.delete(lb, geom=list({g for g in r["geom_interior"] + r["geom_unused"] if isinstance(g, bmesh.types.BMVert)}), context="VERTS")
    return [obj("CoalFines", fb, M["coal"], smooth=True), obj("CoalLumps", lb, M["coal_lump"])]   # 덩어리도 그림 재질 — 그림 없는 색만 재질(0.012)은 게임에서 면마다 하얗게 떴다(09-27 캡처, 까닭 못 찾음)

def mine_car_v2(M, coal=True):
    """광차 다시(09-27, 조사 10 docs/기획서/조사/10_광차_레퍼런스.md 공통점): 2톤 — 전체 2.07 × 1.00 × 1.21 m(문경 실물 [10]).
    쇠판 U자 몸통(옆 곧음 + 아래 둥금, 11/21) · 맨 위 테두리 띠 한 줄(17/21) · 따로 된 ㄷ자 쇠 밑틀 둘(11/21) · 작은 원판 바퀴 넷(지름 0.34, 축 사이 0.76, 몸통 밑 가운데 — 15/15, 표 [7])
    · 양 끝 가운데 쇠 범퍼 덩어리(7/21) + 연결 쇠고리(0.45 m) · 핀(0.31 m)(문서 [2][11]) · 석탄 봉긋(9/13). 앞뒤 가로 막대 범퍼 · 나무 · 위가 넓은 상자는 없음(0/21).
    원점 = 레일 윗면 가운데, X = 달리는 쪽."""
    L, W, H = 1.80, 0.93, 1.21                      # 몸통 길이 · 폭(테두리 띠까지 1.00) · 레일에서 몸통 위까지
    side, bot, zb, th = 0.44, 0.46, 0.31, 0.02      # 곧은 옆 높이 · 둥근 바닥 깊이 · 몸통 바닥 높이 · 판 두께 (위 = 1.21)
    zt = zb + bot + side                            # = H 가까이 (테두리 띠가 나머지)
    def prof(hw, inset):                            # U 단면 (y, z): 위 왼쪽 → 옆 → 둥근 바닥 → 옆 → 위 오른쪽
        pts = [(-hw, zt), (-hw, zt - side)]
        for k in range(1, 12):
            t = math.pi * k / 12; pts.append((-hw * math.cos(t), zt - side - (bot - inset) * math.sin(t)))
        return pts + [(hw, zt - side), (hw, zt)]
    bm = bmesh.new()
    outer, inner = prof(W / 2, 0.0), prof(W / 2 - th, th)
    for x0, x1, pr, flip in ((-L / 2, L / 2, outer, False), (-L / 2 + th, L / 2 - th, inner, True)):   # 옆·바닥 판 (바깥 · 안)
        a_ = [bm.verts.new((x0, y, z)) for y, z in pr]; b_ = [bm.verts.new((x1, y, z)) for y, z in pr]
        for i in range(len(pr) - 1):
            f = [a_[i], a_[i + 1], b_[i + 1], b_[i]]; bm.faces.new(list(reversed(f)) if flip else f)
    for sx in (-1, 1):                                                          # 끝판 (U 모양 판, 두께)
        for x, pr, out in ((sx * L / 2, outer, True), (sx * (L / 2 - th), inner, False)):
            f = [bm.verts.new((x, y, z)) for y, z in pr]; bm.faces.new(f if (sx > 0) == out else list(reversed(f)))
    for sx in (-1, 1):                                                          # 맨 위 테두리 띠 (말린 테두리)
        box(bm, (0, sx * (W / 2 + 0.015), zt - 0.03), (L + 0.06, 0.05, 0.07))
        box(bm, (sx * (L / 2 + 0.015), 0, zt - 0.03), (0.05, W + 0.06, 0.07))
    fr = bmesh.new()
    def channel(y, sgn):                                                        # ㄷ자 쇠 밑틀 (등판 + 위아래 날개, 날개는 안쪽으로)
        box(fr, (0, y, 0.30), (1.95, 0.012, 0.14))
        for z in (0.236, 0.364): box(fr, (0, y + sgn * 0.03, z), (1.95, 0.06, 0.012))
    for sy in (-1, 1): channel(sy * 0.21, -sy)
    for x in (-0.55, 0.0, 0.55): box(fr, (x, 0, 0.35), (0.10, 0.48, 0.05))    # 몸통 받침 (밑틀 사이 가로대)
    for sx in (-1, 1):                                                          # 양 끝 쇠 범퍼 덩어리 + 고리 넣는 틈(검은 안쪽) + 핀
        box(fr, (sx * 0.975, 0, 0.34), (0.10, 0.34, 0.20))                          # 끝에서 끝 2.07 m
        box(fr, (sx * 0.98, 0, 0.30), (0.09, 0.36, 0.04))
        rod(fr, (sx * 1.0, 0.0, 0.26), (sx * 1.0, 0.0, 0.57), 0.015, seg=8)         # 핀 31 cm (위로 조금 나옴)
        rod(fr, (sx * 1.0, 0.0, 0.57), (sx * 1.0, 0.035, 0.57), 0.022, seg=8)       # 핀 머리
    ring = bmesh.new()                                                          # 연결 쇠고리 45 cm — 한쪽 끝에서 늘어짐 (핀에 걸림)
    c0 = Vector((1.0, 0, 0.34)); ax = Vector((math.sin(math.radians(35)), 0, -math.cos(math.radians(35))))   # 아래 바깥으로 35°
    lat = Vector((0, 1, 0)); r_ = 0.05; ptsr = []
    for k in range(7): t = math.pi * k / 6; ptsr.append(c0 + ax * r_ + lat * (r_ * math.cos(t)) - ax * (r_ * math.sin(t)))      # 핀 쪽 반원
    for k in range(7): t = math.pi * k / 6; ptsr.append(c0 + ax * (0.45 - r_) - lat * (r_ * math.cos(t)) + ax * (r_ * math.sin(t)))   # 먼 쪽 반원
    for a_, b_ in zip(ptsr, ptsr[1:] + ptsr[:1]): rod(ring, a_, b_, 0.0175, seg=8)
    wh = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            y0 = sy * 0.30
            rod(wh, (sx * 0.38, y0 - 0.04 * sy, 0.17), (sx * 0.38, y0 + 0.04 * sy, 0.17), 0.17, seg=18)          # 원판 바퀴 지름 0.34
            rod(wh, (sx * 0.38, y0 - 0.055 * sy, 0.17), (sx * 0.38, y0 - 0.035 * sy, 0.17), 0.195, seg=18)       # 테(플랜지) — 레일 안쪽
            box(wh, (sx * 0.38, sy * 0.225, 0.20), (0.16, 0.05, 0.13))                                          # 축 상자 (밑틀에)
        rod(wh, (sx * 0.38, -0.36, 0.17), (sx * 0.38, 0.36, 0.17), 0.0375, seg=10)                              # 축 굵기 7.5 cm
    parts = [obj("CarBody", bm, M["steel"]), obj("CarFrame", fr, M["dark_steel"]), obj("CarRing", ring, M["dark_steel"]), obj("CarWheels", wh, M["dark_steel"])]
    if coal: parts += coal_heap(M, L - 0.06, W - 0.06, zt - 0.02, 0.22)
    return group("PROP_MineCar", parts)

def rough_log(side, ends, a, b, r0, r1, rnd, sides=10, step=0.25, bend=0.025, caps=(True, True), hew=None):
    """거친 통나무 한 토막 a→b (조사 11 docs/기획서/조사/11_갱목_동발_레퍼런스.md · 사진 R1 R3): 원통이 아니게 —
    굵기가 길이를 따라 불룩·잘록(±9 % 낮은 물결 + ±4 % 잔 물결) · 옹이 혹 0~2 개 · 한쪽이 굵음(r0→r1) · 휨(길이의 2.5 %까지)
    · hew = 한 면을 도끼로 깎아 평평하게 할 방향(벡터, 캡은 위) — 사진의 캡·기둥에 평평한 면 (09-27 판정 ③ "너무 원통형" → 판 1 은 ±7 % 8 각이었다)
    · 옆 UV = (둘레 m, 길이 m) — 질감 timber 의 세로 결이 길이 방향 · 잘린 끝 = log_end 원 UV(나이테). side / ends = bmesh"""
    a, b = Vector(a), Vector(b); d = b - a; L = d.length; t = d / L
    up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0)); u1 = t.cross(up).normalized(); u2 = t.cross(u1)
    n = max(2, int(L / step) + 1); ph = rnd.uniform(0, 6.283); bdir = u1 * math.cos(ph) + u2 * math.sin(ph); bamp = rnd.uniform(0.3, 1.0) * bend * L
    waves = [(rnd.choice((1, 2, 3)), 2 * math.pi / rnd.uniform(0.6, 1.5), rnd.uniform(0, 6.283), 0.09 / 3) for _ in range(3)] +             [(rnd.choice((3, 4, 5)), 2 * math.pi / rnd.uniform(0.25, 0.5), rnd.uniform(0, 6.283), 0.04 / 2) for _ in range(2)]
    knots = [(rnd.uniform(0, 6.283), rnd.uniform(0.15, 0.85) * L, rnd.uniform(0.1, 0.2)) for _ in range(rnd.choice((0, 1, 1, 2)))]
    hdir = None
    if hew is not None:
        hv = Vector(hew) - t * Vector(hew).dot(t)
        if hv.length > 1e-3: hdir = hv.normalized()
    uvl = side.loops.layers.uv.verify(); circ = 2 * math.pi * (r0 + r1) / 2
    rings = []
    for i in range(n):
        s_ = i / (n - 1); z = s_ * L; c = a + d * s_ + bdir * (bamp * 4 * s_ * (1 - s_)); r = r0 + (r1 - r0) * s_
        pos = []
        for k in range(sides):
            th = 2 * math.pi * k / sides; rad = u1 * math.cos(th) + u2 * math.sin(th)
            f = 1 + sum(A * math.sin(kk * th + m * z + p_) for kk, m, p_, A in waves)
            for kt, kz, ka in knots:
                dth = math.atan2(math.sin(th - kt), math.cos(th - kt)); f += ka * math.exp(-(dth / 0.35) ** 2 - ((z - kz) / 0.08) ** 2)
            q = rad * (r * f)
            if hdir is not None and q.dot(hdir) > 0.78 * r: q -= hdir * (q.dot(hdir) - 0.78 * r)   # 깎은 면
            pos.append(c + q)
        rings.append((pos, [side.verts.new(p_) for p_ in pos + pos[:1]], z))
    for (p0, v0, l0), (p1, v1, l1) in zip(rings, rings[1:]):
        for k in range(sides):
            f = side.faces.new((v0[k], v0[k + 1], v1[k + 1], v1[k]))
            for lp, (uu, vv) in zip(f.loops, ((k, l0), (k + 1, l0), (k + 1, l1), (k, l1))): lp[uvl].uv = (uu / sides * circ, vv)
    euv = ends.loops.layers.uv.verify()
    for (pos, _, z), keep, flip in ((rings[0], caps[0], True), (rings[-1], caps[1], False)):
        if not keep: continue
        cc = sum(pos, Vector()) / len(pos); rr = max((p_ - cc).length for p_ in pos)
        vs = [ends.verts.new(p_) for p_ in pos]; f = ends.faces.new(list(reversed(vs)) if flip else vs)
        for lp in f.loops:
            q = lp.vert.co - cc; lp[euv].uv = (0.5 + 0.47 * q.dot(u1) / rr, 0.5 + 0.47 * q.dot(u2) / rr)

def board(bm, c, along, up, length, width, thick):
    """판자 한 장: along = 긴 쪽, up = 두께 쪽(바깥), 나머지 = 폭. UV = (길이 m, 폭 m) — 질감(wedge · lagging)의 결이 u(가로)라 결이 판자 길이를 따른다
    (상자 투영이면 결이 판자를 가로질러 널 이음 무늬가 타일처럼 보였다 — 09-27)"""
    along = Vector(along).normalized(); up = Vector(up).normalized(); across = up.cross(along).normalized(); up = along.cross(across)
    uvl = bm.loops.layers.uv.verify(); c = Vector(c); o0 = rnd_off = (c.x * 1.7 + c.y * 2.3) % 1.0   # 판자마다 질감 자리를 달리
    V = {(i, j, k): bm.verts.new(c + along * (i * length / 2) + across * (j * width / 2) + up * (k * thick / 2)) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)}
    for keys, uax, vax in (([(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)], 0, 1), ([(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)], 0, 1),
                           ([(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)], 0, 2), ([(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)], 0, 2),
                           ([(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)], 1, 2), ([(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)], 1, 2)):
        f = bm.faces.new([V[k_] for k_ in keys]); size = (length, width, thick)
        for lp, k_ in zip(f.loops, keys): lp[uvl].uv = (k_[uax] * size[uax] / 2 + o0, k_[vax] * size[vax] / 2 + o0 * 3.1)

def timber_set(M, width=3.0, height=2.9):
    """나무 동발 한 틀: 껍질 벗긴 둥근 통나무 기둥 둘(지름 0.22, 안쪽으로 약간 기욺) + 위 통나무(지름 0.24) + 쐐기"""
    bm = bmesh.new()
    for s in (-1, 1):
        rod(bm, (s * width / 2, 0, 0), (s * (width / 2 - 0.12), 0, height - 0.12), 0.11, seg=12)
        box(bm, (s * (width / 2 - 0.35), 0, height + 0.13), (0.25, 0.12, 0.08))
    rod(bm, (-width / 2 - 0.25, 0, height), (width / 2 + 0.25, 0, height), 0.12, seg=12)
    return group("PROP_TimberSet", [obj("TimberSet", bm, M["log"], smooth=True)])

def steel_set(M, width=3.3, height=3.2, planks=True, gap=1.1):
    """강철 아치 두 틀(I 형 0.16 m, 다리 + 반원 위, gap m 간격) + 두 아치 위에 걸쳐 댄 판자 (한국 사진 화순 2022 · 장성 2024)"""
    bm = bmesh.new(); r = width / 2; leg = height - r
    pts = [Vector((-r, 0, 0)), Vector((-r, 0, leg))] + [Vector((-r * math.cos(t), 0, leg + r * math.sin(t))) for t in [math.pi * k / 10 for k in range(1, 10)]] + [Vector((r, 0, leg)), Vector((r, 0, 0))]
    for y in (-gap / 2, gap / 2):
        for a, b in zip(pts, pts[1:]): ibeam(bm, a + Vector((0, y, 0)), b + Vector((0, y, 0)))
    parts = [obj("SteelArch", bm, M["steel"])]
    if planks:
        pb = bmesh.new()
        for t in [math.pi * k / 9 for k in range(1, 9)]:
            c = Vector((-(r + 0.1) * math.cos(t), 0, leg + (r + 0.1) * math.sin(t)))
            box(pb, c, (0.2, gap + 0.3, 0.035), Matrix.Rotation(-t + math.pi / 2, 3, "Y"))
        parts.append(obj("Lagging", pb, M["plank"]))
    return group("PROP_SteelSet", parts)

def chain(M, length=1.5, link=0.07, wire=0.011):
    """쇠사슬: 고리 = 가는 막대 넷의 네모 고리, 번갈아 90° 돌림"""
    bm = bmesh.new(); n = int(length / (link * 0.75))
    for i in range(n):
        R = Matrix.Rotation(math.pi / 2 * (i % 2), 3, "Z"); c = Vector((0, 0, -i * link * 0.75))
        for sx in (-1, 1): box(bm, c + R @ Vector((sx * 0.02, 0, 0)), (wire, wire, link), R)
        for sz in (-1, 1): box(bm, c + Vector((0, 0, sz * link / 2)), (0.04 + wire, wire, wire), R)
    return group("PROP_Chain", [obj("Chain", bm, M["dark_steel"])])

def cage(M, w=2.6, d=2.2, H=4.4, top=None):
    """수갱 케이지(안 움직임): 강철 틀 기둥 넷(I 형, H 까지 — 천장 바위에 박히게) · 보(2.6 m · top) · 케이지 칸(1.8 × 1.4 × 2.3, 긴 옆 둘 = 철망 벽)
    · 양 끝(±X) 미닫이 철망 문 반쯤 열림 — 레일이 지나간다(사용자 승인 배치 09-27) · 위 사슬 둘 · 틀 안 천장 = 검은 굴 (사진: 장성 2023 · 영국 1977 · 독일 2008)"""
    top = H - 0.1 if top is None else top
    fr = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1): ibeam(fr, (sx * w / 2, sy * d / 2, 0), (sx * w / 2, sy * d / 2, H), h=0.2, w=0.16, t=0.016)
    for z in (2.6, top):
        for sy in (-1, 1): ibeam(fr, (-w / 2, sy * d / 2, z), (w / 2, sy * d / 2, z), h=0.2, w=0.14, t=0.016)
        for sx in (-1, 1): ibeam(fr, (sx * w / 2, -d / 2, z), (sx * w / 2, d / 2, z), h=0.2, w=0.14, t=0.016)
    cg = bmesh.new(); cw, cd, ch = 1.8, 1.4, 2.3; z0 = 0.05
    for x in (-cw / 2, cw / 2):
        for y in (-cd / 2, cd / 2): box(cg, (x, y, z0 + ch / 2), (0.06, 0.06, ch))
    for z in (z0, z0 + ch):
        for y in (-cd / 2, cd / 2): box(cg, (0, y, z), (cw, 0.06, 0.06))
        for x in (-cw / 2, cw / 2): box(cg, (x, 0, z), (0.06, cd, 0.06))
    box(cg, (0, 0, z0 + ch + 0.03), (cw, cd, 0.03)); box(cg, (0, 0, z0), (cw, cd, 0.04))
    bars = bmesh.new()
    def mesh_wall(a, b, n):                                  # 세로 쇠살 + 가로 띠 둘
        a, b = Vector(a), Vector(b)
        for k in range(1, n):
            p = a.lerp(b, k / n); rod(bars, p + Vector((0, 0, z0)), p + Vector((0, 0, z0 + ch)), 0.008, seg=6)
        for zz in (0.9, 1.8): box(bars, (a + b) / 2 + Vector((0, 0, z0 + zz)), (abs(b.x - a.x) + 0.02, abs(b.y - a.y) + 0.02, 0.03))
    mesh_wall((-cw / 2, -cd / 2, 0), (cw / 2, -cd / 2, 0), 18); mesh_wall((-cw / 2, cd / 2, 0), (cw / 2, cd / 2, 0), 18)
    gate = bmesh.new()                                        # 양 끝 미닫이 문: 반쯤 열림 (쇠살 폭 0.9 가 한쪽으로 밀려 있음)
    for sx in (-1, 1):
        gx = sx * (cw / 2 + 0.08)
        for k in range(10):
            y = sx * (-cd / 2 + 0.05 + k * 0.09); rod(gate, (gx, y, z0), (gx, y, z0 + 2.0), 0.009, seg=6)
        for zz in (0.1, 1.0, 1.95): box(gate, (gx, sx * (-cd / 2 + 0.45), z0 + zz), (0.03, 0.95, 0.04))
        box(gate, (gx, 0, z0 + 2.08), (0.05, cd + 0.3, 0.05))
    hole = bmesh.new(); box(hole, (0, 0, top + 0.12), (w - 0.1, d - 0.1, 0.02))
    parts = [obj("CageFrame", fr, M["paint"]), obj("CageCar", cg, M["steel"]), obj("CageMesh", bars, M["dark_steel"]),
             obj("CageGate", gate, M["dark_steel"]), obj("ShaftHole", hole, flat("M_Black", (0.0, 0.0, 0.0), 1.0))]
    L = top - (z0 + ch + 0.06)
    for x in (-0.5, 0.5):
        c = chain(M, L); c.location = (x, 0, top); parts.append(c)
    return group("PROP_Cage", parts)

def sign(M, lines, size=(0.9, 0.6), board=(0.92, 0.9, 0.85), ink=(0.7, 0.06, 0.05), font=None, text_h=0.13):
    """판 + 글자(Pretendard OFL). lines = 줄 글자들"""
    bm = bmesh.new(); box(bm, (0, 0, 0), (size[0], 0.02, size[1]))
    parts = [obj("SignBoard", bm, flat("M_Board_%d" % int(board[0] * 100), tuple(v * 0.72 for v in board), 0.85))]   # 탄가루에 전 판 (새 판처럼 하얗지 않게)
    fnt = bpy.data.fonts.load(font, check_existing=True) if font else None
    for i, t in enumerate(lines):
        cu = bpy.data.curves.new("SignText", "FONT"); cu.body = t; cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.size = text_h
        if fnt: cu.font = fnt
        cu.extrude = 0.002
        o = bpy.data.objects.new("SignText", cu); bpy.context.scene.collection.objects.link(o)
        o.rotation_euler = (math.pi / 2, 0, 0); o.location = (0, -0.012, (len(lines) - 1) / 2 * text_h * 1.3 - i * text_h * 1.3)
        o.data.materials.append(flat("M_Ink_%d" % int(ink[0] * 100), ink, 0.5)); parts.append(o)
    return group("PROP_Sign", parts)
