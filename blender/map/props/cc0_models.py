"""받아 둔 CC0 모델(Poly Haven, build/tex_test/cc0/models/<이름>/)을 불러와 소품으로 쓴다 — 드럼통 · 나무 상자 · 연장 상자 · 구급함 · 배전함 · 선반 · 관.
다른 소품 파일과 다르다: 짓지 않고 불러오고, 재질도 모델에 딸린 사진 재질을 쓴다 (mats 는 안 쓴다).
  load("barrel_03")                       → 바닥 가운데가 원점, 긴 쪽이 x
  load("medical_box", wall=True)          → 뚜껑이 −y 를 보고 등이 y = 0 (벽), 바닥 z = 0, 손잡이 위 — 벽에 거는 함
  load("modular_industrial_pipes_01:pipe04") → 조각 묶음에서 이름에 그 말이 든 조각만 (parts() 로 이름을 본다)
  load("wooden_crate_01", scale=1.25)     → 크기를 곱해서 (그물에 굽는다)
  table()                                 → 이름 → (x, y, z 크기 m, 삼각형 수)
묶음 (mats 를 주면 _util 재질로 덧붙인 것이 붙는다 — 글씨 판 · 전선):
  firstaid(mats)   → 벽 구급함: 영어 글씨 뚜껑을 흰 판 + 붉은 십자 + "구급함" 으로 덮는다. 등이 y = 0, 바닥 z = 0 (맵에서 1.3~1.4 m 로 올린다)
  switchbox(mats)  → 배전함 + 위에서 벽으로 올라가는 전선. 바닥 가운데가 원점, 벽은 y = +0.25
  pipe_valve()     → 바닥에서 올라와 벽으로 꺾이는 관 + 붉은 손바퀴 밸브(1.05 m 높이, −y 를 본다). 관 가운데가 (0, −0.32), 벽은 y = 0
  rack_full()      → 선반 + 칸마다 연장 상자 · 나무 상자 · 관 이음쇠. 바닥 가운데가 원점
모델 폴더는 git 에 없다 (받는 곳은 폴더마다 source.txt). 없으면 load 가 FileNotFoundError 를 낸다.
"""
import bpy, bmesh, os, glob, json, math
import numpy as np
from mathutils import Matrix

DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "build", "tex_test", "cc0", "models"))
# 권하는 어둡기 (바탕색에 곱하는 값). 조사 12 의 색 밝기를 0.2 안팎으로 내린다 — 0.3 을 넘으면 머리등에 하얗게 탄다. 마지막 판정은 실행 파일에서.
DARK = {"barrel_03": 0.55, "wooden_crate_01": 0.65, "metal_toolbox": 0.45, "medical_box": 0.6, "utility_box_01": 0.45, "worn_metal_rack": 0.5,
        "modular_industrial_pipes_01": 0.5, "modular_airduct_circular_01": 0.3, "modular_fire_escape": 1.0, "rock_07": 0.5, "rock_09": 0.5}
_MESH, _MAT = {}, {}

def _gltf(model):
    f = glob.glob(os.path.join(DIR, model, "*.gltf")) + glob.glob(os.path.join(DIR, model, "*.glb"))
    if not f: raise FileNotFoundError("CC0 모델이 없다: %s (source.txt 의 주소에서 다시 받는다)" % os.path.join(DIR, model))
    return f[0]

def parts(model):
    """조각 묶음 모델 안의 조각 이름들 (gltf 를 글로 읽는다 — Blender 에 안 불러온다)"""
    return [n["name"] for n in json.load(open(_gltf(model), encoding="utf-8"))["nodes"] if "mesh" in n]

def _dark(m, k):
    """재질 사본의 바탕색 그림에 k 를 곱한다 (scene_mock.tint 와 같은 꼴: 그림 → 곱하기 → Principled. glTF 로 나간다). 1024 넘는 그림은 줄인다"""
    key = (m.name, round(k, 3))
    if key in _MAT: return _MAT[key]
    t = m.copy(); t.name = "%s_d%02d" % (m.name, round(k * 100)); nt = t.node_tree
    for n in nt.nodes:
        if n.type == "TEX_IMAGE" and n.image and max(n.image.size) > 1024:
            s = 1024 / max(n.image.size); n.image.scale(max(1, round(n.image.size[0] * s)), max(1, round(n.image.size[1] * s)))
    if k != 1.0:
        inp = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"]
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 1.0
        a, b = [x for x in mix.inputs if x.type == "RGBA"][:2]; b.default_value = (k, k, k, 1)
        if inp.links: nt.links.new(inp.links[0].from_socket, a)
        else: a.default_value = inp.default_value
        nt.links.new(next(x for x in mix.outputs if x.type == "RGBA"), inp)
    _MAT[key] = t; return t

def _tris(me): return sum(len(p.vertices) - 2 for p in me.polygons)

def _mesh(name, dark, max_tris, wall, scale=1.0):
    key = (name, round(dark, 3), max_tris, wall, round(scale, 3))
    if key in _MESH: return _MESH[key]
    model, _, part = name.partition(":")
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=_gltf(model), merge_vertices=True); new = [o for o in bpy.data.objects if o not in before]
    ms = [o for o in new if o.type == "MESH" and part.lower() in o.name.lower()]
    if not ms: raise ValueError("%s 안에 '%s' 조각이 없다. 있는 것: %s" % (model, part, parts(model)))
    for o in ms:                                                     # 놓인 자리 · 돌림 · 크기를 그물에 굽는다
        M = o.matrix_world.copy(); o.data.transform(M); o.parent = None; o.matrix_world = Matrix.Identity(4)
        if M.determinant() < 0: o.data.flip_normals()
    a = ms[0]
    if len(ms) > 1:                                                  # 뚜껑 · 손잡이 · 걸쇠를 한 물체로
        with bpy.context.temp_override(active_object=a, object=a, selected_objects=ms, selected_editable_objects=ms): bpy.ops.object.join()
    n0 = _tris(a.data); me = a.data
    if n0 > max_tris:                                                # 삼각형이 많으면 줄인다
        a.modifiers.new("dec", "DECIMATE").ratio = max_tris / n0
        me = bpy.data.meshes.new_from_object(a.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    else: me = me.copy()
    bm = bmesh.new(); bm.from_mesh(me)                               # 면 없는 선 · 점은 게임에 안 나온다 — 지운다
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context="EDGES"); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me); bm.free()
    for o in new:
        try: bpy.data.objects.remove(o, do_unlink=True)
        except ReferenceError: pass                                  # 합치면서 이미 없어진 것
    def bb():
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3); return co.min(0), co.max(0)
    if wall: me.transform(Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Rotation(math.pi, 4, "Z"))   # 눕힌 함을 세운다: 뚜껑 → −y, 손잡이 → 위
    else:
        lo, hi = bb()
        if hi[1] - lo[1] > hi[0] - lo[0] + 1e-4: me.transform(Matrix.Rotation(math.radians(90), 4, "Z"))  # 긴 쪽을 x 로
    if scale != 1.0: me.transform(Matrix.Scale(scale, 4))
    lo, hi = bb(); me.transform(Matrix.Translation((-(lo[0] + hi[0]) / 2, -hi[1] if wall else -(lo[1] + hi[1]) / 2, -lo[2])))
    for i, m in enumerate(me.materials): me.materials[i] = _dark(m, dark)
    me.name = "CC0_" + name.replace(":", "_"); lo, hi = bb()
    _MESH[key] = (me, tuple(round(float(v), 3) for v in hi - lo), n0); return _MESH[key]

def load(name, dark=0.5, max_tris=6000, wall=False, scale=1.0):
    """모델 하나 → [물체]. 두 번째부터는 같은 그물을 나눠 쓰는 사본"""
    me = _mesh(name, dark, max_tris, wall, scale)[0]
    o = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(o); return [o]

def table():
    """이름 → (x, y, z 크기 m, 삼각형 수). 조각 묶음은 조각마다 '묶음:조각' 으로"""
    out = {}
    for d in sorted(os.listdir(DIR)):
        if not os.path.isdir(os.path.join(DIR, d)): continue
        ps = parts(d); names = [d] if len(ps) == 1 or not d.startswith("modular") else ["%s:%s" % (d, p) for p in ps]
        for n in names:
            me, size, n0 = _mesh(n, DARK.get(d, 0.5), 6000, False); out[n] = (*size, _tris(me)); print("CC0 %-70s %.2f x %.2f x %.2f m  tris %d -> %d" % (n, *size, n0, _tris(me)))
    return out

def _at(name, M, **kw):
    """load + 놓기 (권하는 어둡기로)"""
    o = load(name, DARK[name.partition(":")[0]], **kw)[0]; o.matrix_world = M; return o

def T(x, y, z, rz=0.0): return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rz), 4, "Z")

def firstaid(mats=None):
    """벽 구급함 (0.53 x 0.10 x 0.35). 모델 뚜껑의 영어 'FIRST AID' 는 광산에 안 맞는다 — 흰 칠 판 + 붉은 십자 + '구급함' 으로 덮는다 (3 m 에서 십자가 먼저 읽힌다)"""
    out = [_at("medical_box", Matrix.Identity(4), wall=True)]
    if not mats: return out
    import _util
    y = -0.098; bm = bmesh.new(); _util.box(bm, (0, y - 0.004, 0.172), (0.47, 0.012, 0.29)); out.append(_util.obj("FIRSTAID_PLATE", bm, mats["white"]))
    bm = bmesh.new(); _util.box(bm, (-0.125, y - 0.012, 0.172), (0.17, 0.006, 0.055)); _util.box(bm, (-0.125, y - 0.012, 0.172), (0.055, 0.006, 0.17)); out.append(_util.obj("NOCOL_FIRSTAID_CROSS", bm, mats["red"]))
    out.append(_util.text_mesh("NOCOL_FIRSTAID_TEXT", "구급함", (0.095, y - 0.010, 0.142), 0.085, mats["red"]))
    return out

def switchbox(mats=None):
    """배전함 (0.52 x 0.43 x 1.12) — 혼자 서 있으면 길거리 함으로 보인다: 지붕 뒤에서 나온 굵은 전선이 벽(y = +0.25)을 타고 2.5 m 까지 올라간다"""
    out = [_at("utility_box_01", Matrix.Identity(4))]
    if not mats: return out
    import _util
    for x, r, top in ((-0.035, 0.03, 2.5), (0.035, 0.02, 2.42)):      # 굵은 전선 + 가는 전선이 붙어서 (떨어뜨리면 사다리로 보인다), 벽에 쇠 띠로 묶음
        bm = bmesh.new(); _util.sweep(bm, [(x, 0.12, 1.08), (x, 0.13, 1.30), (x + 0.02, 0.20, 1.46), (x + 0.03, 0.25 - r, 1.62), (x + 0.03, 0.25 - r, top - 0.25), (x + 0.03, 0.25, top)], r, seg=8)
        out.append(_util.obj("NOCOL_SWITCH_CABLE", bm, mats["rubber"], smooth=True))
    bm = bmesh.new()
    for z in (1.75, 2.2): _util.box(bm, (0.03, 0.215, z), (0.17, 0.07, 0.035))
    out.append(_util.obj("NOCOL_SWITCH_CLAMP", bm, mats["iron"])); return out

def pipe_valve(mats=None):
    """밸브 달린 관: 바닥 테(플랜지) → 곧은 관 0.86 m → 밸브(붉은 손바퀴가 −y, 1.05 m) → 굽은 관이 1.58 m 에서 벽(y = 0)으로 들어간다. 조각 pipe01 · pipe08 · pipe04"""
    K = "modular_industrial_pipes_01:"; y = -0.32
    return [_at(K + "pipe01", T(0, y, 0)),
            _at(K + "pipe08", T(0.0295, y - 0.0505, 0.859, -90)),        # 밸브 조각의 관 가운데가 조각 가운데에서 비켜 있다 — 맞춰 옮긴다
            _at(K + "pipe04", T(0, y, 1.238, -90) @ Matrix.Translation((0, 0, 0.445)) @ Matrix.Rotation(math.pi, 4, "X") @ Matrix.Translation((-0.1085, 0, 0)))]   # 굽은 관을 뒤집어 위 끝이 아래로, 옆 끝이 벽으로

def rack_full(mats=None):
    """찬 선반 (0.92 x 0.60 x 1.90, 칸 윗면 0.43 · 0.92 · 1.41 · 1.90): 아래 칸 나무 상자, 둘째 칸 연장 상자, 셋째 칸 관 이음쇠 둘 — 빈 선반은 안 쓰던 것으로 보인다"""
    K = "modular_industrial_pipes_01:"
    return [_at("worn_metal_rack", Matrix.Identity(4)),
            _at("wooden_crate_01", T(-0.02, 0.02, 0.43, 4), scale=0.85, max_tris=2500),
            _at("metal_toolbox", T(-0.17, -0.06, 0.92, -14), max_tris=3000),
            _at(K + "pipe06", T(0.22, 0.05, 0.92, 30)), _at(K + "pipe07", T(-0.12, 0.03, 1.41, 75))]

def build(mats=None):
    """본보기: 벽(y = 0) 앞 창고 구석 — 선 드럼통 + 쓰러진 드럼통, 나무 상자 셋(둘은 틀어 쌓고 하나는 앞에 비스듬히) + 그 위 벽의 구급함, 배전함 + 전선, 밸브 관, 찬 선반. 미리보기 옵션 '{"_wall": 0.0}'"""
    out = [_at("barrel_03", T(0.36, -0.40, 0)),
           _at("barrel_03", T(-0.75, -1.05, 0.319, 20) @ Matrix.Rotation(math.radians(90), 4, "Y")),   # 쓰러져 누운 통 (옆구리가 바닥에)
           _at("wooden_crate_01", T(1.52, -0.36, 0, -3), scale=1.25), _at("wooden_crate_01", T(1.47, -0.38, 0.438, 9), scale=1.25),
           _at("wooden_crate_01", T(1.15, -1.05, 0, 38))]
    def grp(objs, M):
        for o in objs: o.matrix_world = M @ o.matrix_world
        out.extend(objs)
    grp(firstaid(mats), T(1.5, 0, 1.35))
    grp(switchbox(mats), T(2.55, -0.25, 0))
    grp(pipe_valve(mats), T(3.2, 0, 0))
    grp(rack_full(mats), T(4.05, -0.33, 0))
    return out

if __name__ == "__main__":                                           # blender -b --factory-startup -P cc0_models.py → 크기 표 + 두 번째 load 가 그물을 나눠 쓰는지
    t = table(); a, b = load("barrel_03")[0], load("barrel_03")[0]
    assert a.data is b.data and a.matrix_world == Matrix.Identity(4), "사본이 그물을 나눠 쓰지 않는다"
    assert all(v[3] <= 6000 * 1.02 for v in t.values()), "삼각형 줄이기가 안 먹었다"
    print("CC0 OK %d" % len(t))
