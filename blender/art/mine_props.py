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
    wh = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            rod(wh, (sx * 0.42, sy * 0.3 - 0.04 * sy, 0.15), (sx * 0.42, sy * 0.3 + 0.04 * sy, 0.15), 0.15, seg=16)
        rod(wh, (sx * 0.42, -0.38, 0.15), (sx * 0.42, 0.38, 0.15), 0.03)
    parts = [obj("CarBody", bm, M["steel"]), obj("CarWheels", wh, M["dark_steel"])]
    if coal:
        cb = bmesh.new(); bmesh.ops.create_grid(cb, x_segments=14, y_segments=9, size=0.5)
        import random; rnd = random.Random(7)
        for v in cb.verts:
            v.co = Vector((v.co.x * (tl - 0.1), v.co.y * (tw - 0.1), z0 + h - 0.12 + 0.18 * (1 - (2 * v.co.x) ** 2) * (1 - (2 * v.co.y) ** 2) + rnd.uniform(-0.03, 0.03)))
        parts.append(obj("CarCoal", cb, M["coal"], smooth=True))
    return group("PROP_MineCar", parts)

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

def cage(M, w=2.6, d=2.2, H=4.4):
    """수갱 케이지(안 움직임): 강철 틀 기둥 넷(I 형) · 위 보 · 케이지 칸(1.8 × 1.4 × 2.3, 철망 벽) · 앞 미닫이 철망 문 · 위 사슬 · 천장 쪽 검은 굴 (사진: 장성 2023 · 영국 1977 · 독일 2008)"""
    fr = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1): ibeam(fr, (sx * w / 2, sy * d / 2, 0), (sx * w / 2, sy * d / 2, H), h=0.2, w=0.16, t=0.016)
    for z in (2.6, H - 0.1):
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
    mesh_wall((-cw / 2, -cd / 2, 0), (-cw / 2, cd / 2, 0), 14); mesh_wall((cw / 2, -cd / 2, 0), (cw / 2, cd / 2, 0), 14)
    mesh_wall((-cw / 2, cd / 2, 0), (cw / 2, cd / 2, 0), 18)
    gate = bmesh.new()                                        # 앞(−Y) 미닫이 문: 반쯤 열림
    for k in range(10):
        x = -cw / 2 + 0.05 + k * 0.09; rod(gate, (x, -cd / 2 - 0.08, z0), (x, -cd / 2 - 0.08, z0 + 2.0), 0.009, seg=6)
    for zz in (0.1, 1.0, 1.95): box(gate, (-cw / 2 + 0.45, -cd / 2 - 0.08, z0 + zz), (0.95, 0.03, 0.04))
    box(gate, (0, -cd / 2 - 0.08, z0 + 2.08), (cw + 0.3, 0.05, 0.05))
    hole = bmesh.new(); box(hole, (0, 0, H + 0.02), (w - 0.1, d - 0.1, 0.02))
    parts = [obj("CageFrame", fr, M["paint"]), obj("CageCar", cg, M["steel"]), obj("CageMesh", bars, M["dark_steel"]),
             obj("CageGate", gate, M["dark_steel"]), obj("ShaftHole", hole, flat("M_Black", (0.0, 0.0, 0.0), 1.0))]
    c = chain(M, 1.7); c.location = (-0.5, 0, H - 0.1); parts.append(c)
    c2 = chain(M, 1.7); c2.location = (0.5, 0, H - 0.1); parts.append(c2)
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
