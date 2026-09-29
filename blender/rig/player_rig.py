"""3D-P 차례 3 — Mixamo 뼈대 몸에 우리 그림 · 소품을 붙여 Unity 로 내보낸다(제안서 "2. 뼈대", 사용자 09-29 "가로 가라" — 손가락 뼈 엄지 · 검지 그대로).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P blender/rig/player_rig.py
입력: MineTunnel/mesh/mixamo_player_body.fbx(저장소 밖 — Mixamo 원본은 안 올린다, A 자세 그대로 받음)
      build/player/player_mask_full.blend(손질 끝난 몸 그림 · 소품 · 목수건 · 방독면 — 판정 ⑩ 통과)
하는 일:
  ① Mixamo 몸에 우리 그림(4K)을 씌운다 — Mixamo 몸은 원래 몸과 점 · 자리가 같다(0.0 mm)
  ② 몸을 둘로: PlayerArms(아래팔 · 손 뼈가 가장 센 면 — 1인칭에서 이것만 그린다) · PlayerBody(나머지)
  ③ 딱딱한 소품은 뼈 자식으로(자리 그대로): 안전모 · 램프 · 방독면 · 끈 → 머리 / 배터리 · 탄띠 · 수통 → 엉덩이
  ④ 휘는 소품은 뼈에 무게로: 목수건(목 · 가슴) · 램프 줄(머리 → 엉덩이) — 가까운 뼈 둘에 거리 반비례
  ⑤ 한 FBX 로 내보낸다(Assets/Tunnel/Player/player.fbx) · 몸 그림은 Assets/Tunnel/Player/Textures/player_base · player_nor_gl.png — 제안서는 소품을 GLB 로 따로 두려 했지만
     두 파일(FBX · GLB)의 좌표 방향을 맞춰야 해서 뼈 자식으로 한 파일에 넣었다(Unity 가 뼈 밑에 그대로 둔다)
자기 검사(FAIL 이면 종료 1): 손가락 뼈(엄지 · 검지) · 팔 가르기 · 소품 자리 그대로 · 휘는 소품 무게 · 그림 파일 · 물체마다 재질 하나
사보타주: SABOTAGE=noarms(팔 안 가름) → 팔 가르기 FAIL · unparent(소품을 뼈에 안 붙임) → 소품 FAIL · thinprops(단면 곡선 먼저 지움) → 면 FAIL · noflip(안쪽 면 그대로) → 면 방향 FAIL
출력: build/player/player_rig.blend · Assets/Tunnel/Player/player.fbx"""
import bpy, bmesh, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "blender", "props"))
import player_blockout as B

SAB = os.environ.get("SABOTAGE", "")
SRC = os.path.join(os.path.dirname(ROOT), "MineTunnel", "mesh", "mixamo_player_body.fbx")
BLEND = os.path.join(ROOT, "build", "player", "player_mask_full.blend")
OUT_FBX = os.path.join(ROOT, "Assets", "Tunnel", "Player", "player.fbx")
MX = "mixamorig:"
ARM_BONES = ("ForeArm", "Hand")                     # 이름에 들어 있으면 팔(아래팔 · 손 · 손가락)
HEAD_GROUP = ("Helmet_", "Lamp_Body", "Lamp_Bezel", "Lamp_Lens", "Mask_")
HIPS_GROUP = ("Battery_", "Belt_", "Canteen_")
SKIN = {"Towel_Fix": ("Neck", "Spine2", "Spine1"), "Lamp_Cord": ("Head", "Neck", "Spine2", "Spine1", "Spine", "Hips")}

# ── 손질 끝난 장면(그림 · 소품) ──
bpy.ops.wm.open_mainfile(filepath=BLEND)
old = max((o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render), key=lambda o: len(o.data.vertices))
mat = old.data.materials[0]
props = [o for o in bpy.data.objects if o is not old and not o.hide_render and o.type in ("MESH", "CURVE")]
if SAB == "thinprops":                                                              # 옛 순서(단면 곡선을 먼저 지움) — 면 검사가 잡는지
    for o in [o for o in bpy.data.objects if o.hide_render and o.type == "CURVE"]: bpy.data.objects.remove(o)
curve_names = set()
for o in props:                                                                     # 곡선(목수건 · 램프 줄 · 방독면 끈)은 그물로
    if o.type == "CURVE":
        dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        me.transform(o.matrix_world)
        bm = bmesh.new(); bm.from_mesh(me)                                          # 단면을 돌려 만든 관은 면이 안쪽을 볼 때가 있다(목수건 · 방독면 끈) —
        if bm.calc_volume(signed=True) < 0 and SAB != "noflip":                      # Blender 는 양면을 그려 몰랐고 Unity 는 뒷면을 안 그려 목수건이 사라졌다(09-29)
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(me); bm.free()
        new = bpy.data.objects.new(o.name, me); bpy.context.scene.collection.objects.link(new); curve_names.add(o.name)
        if not me.materials:                                                        # new_from_object 가 재질을 이미 옮긴다(두 번 붙이면 재질 둘)
            for m in o.data.materials: me.materials.append(m)
        props[props.index(o)] = new; bpy.data.objects.remove(o); new.name = new.name.split(".")[0]
    else:
        o.data = o.data.copy(); o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
for o in [o for o in bpy.data.objects if o.hide_render or o is old]: bpy.data.objects.remove(o)   # 밑그림 몸 · 숨긴 것 · 옛 몸 — 곡선을 그물로 바꾼 뒤에(단면 곡선도 숨겨져 있어 먼저 지우면 목수건 · 끈이 면 없는 선이 됐다)
for o in [o for o in bpy.data.objects if o.type == "EMPTY"]:                        # 소품 묶음(빈 물체)은 풀고 자리는 남긴다
    for c in o.children: mw = c.matrix_world.copy(); c.parent = None; c.matrix_world = mw
    bpy.data.objects.remove(o)
bpy.context.view_layer.update()
world0 = {o.name: np.array([v.co[:] for v in o.data.vertices]) for o in props}      # 소품 자리(검사용)

# ── ① Mixamo 몸 ──
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=SRC)
arm = next(o for o in bpy.data.objects if o not in before and o.type == "ARMATURE"); arm.name = "PlayerRig"
body = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
body.data.materials.clear(); body.data.materials.append(mat)
bones = [b.name for b in arm.data.bones]
# 그림은 FBX 에 넣지 않고 파일로 둔다 — Unity 는 FBX 안에 넣은 그림을 꺼내 쓰지 않았다(재질에 그림 없음, 09-29).
# Unity 쪽에서 재질(PlayerSkin.mat)을 만들어 FBX 재질 자리에 끼운다(Assets/Editor/PlayerRigTest.cs EnsureImport). 노멀은 _nor_gl → TextureImportRules
mat.name = "PlayerSkin"
TEX_DIR = os.path.join(os.path.dirname(OUT_FBX), "Textures"); os.makedirs(TEX_DIR, exist_ok=True)
saved = {}
for n in [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"]:
    to = {l.to_node.type for l in n.outputs["Color"].links}
    kind = "base" if "BSDF_PRINCIPLED" in to else "nor_gl" if "NORMAL_MAP" in to else None
    if kind is None: continue                                                       # 금속 · 거칠기 묶음 그림은 URP 와 채널이 달라 안 쓴다(매끈함은 재질 값)
    src = n.image; w, h = src.size; px = np.empty(w * h * 4, dtype=np.float32); src.pixels.foreach_get(px)   # 복사본은 픽셀이 빠져 있어 새 그림에 옮겨 담는다
    img = bpy.data.images.new(f"player_{kind}", w, h, alpha=True); img.pixels.foreach_set(px)
    img.filepath_raw = os.path.join(TEX_DIR, f"player_{kind}.png"); img.file_format = "PNG"; img.save()
    saved[kind] = (w, os.path.getsize(img.filepath_raw))
print("INFO 그림 파일", {k: f"{w} px · {b/1e6:.1f} MB" for k, (w, b) in saved.items()})

# ── ② 팔 / 몸 가르기: 점마다 가장 센 뼈 → 면의 점이 모두 팔 뼈면 팔 ──
me = body.data; gname = {g.index: g.name for g in body.vertex_groups}
dom = np.array([gname[max(v.groups, key=lambda g: g.weight).group] if v.groups else "" for v in me.vertices])
is_arm_v = np.array([any(k in d for k in ARM_BONES) for d in dom])
arm_f = np.array([is_arm_v[list(p.vertices)].all() for p in me.polygons])
n_faces0 = len(me.polygons)
arms = None
if SAB != "noarms":
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bm2 = bm.copy()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(arm_f)[0]], context="FACES")
    bm2.faces.ensure_lookup_table(); bmesh.ops.delete(bm2, geom=[bm2.faces[i] for i in np.where(~arm_f)[0]], context="FACES")
    me_arms = me.copy(); bm2.to_mesh(me_arms); bm.to_mesh(me); bm.free(); bm2.free()
    arms = bpy.data.objects.new("PlayerArms", me_arms); bpy.context.scene.collection.objects.link(arms)
    arms.parent = body.parent; arms.matrix_world = body.matrix_world.copy()
    for g in body.vertex_groups: arms.vertex_groups.new(name=g.name)
    arms.modifiers.new("Armature", "ARMATURE").object = arm
    # bmesh 는 점 무게를 옮긴다(같은 deform 층) — 이름만 다시 맞춘다
body.name = "PlayerBody"

# ── ③ 딱딱한 소품: 뼈 자식(자리 그대로) ──
def bone_parent(o, bname):
    mw = o.matrix_world.copy()
    o.parent = arm; o.parent_type = "BONE"; o.parent_bone = bname
    bpy.context.view_layer.update()
    b = arm.data.bones[bname]
    o.matrix_parent_inverse = (arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
    o.matrix_world = mw
rigid = {}
for o in props:
    grp = MX + "Head" if o.name.startswith(HEAD_GROUP) else MX + "Hips" if o.name.startswith(HIPS_GROUP) else None
    if grp is None: continue
    rigid[o.name] = grp
    if SAB != "unparent": bone_parent(o, grp)

# ── ④ 휘는 소품: 가까운 뼈 둘에 거리 반비례 무게 ──
def seg_dist(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)
for o in props:
    if o.name not in SKIN: continue
    co = np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices])
    names = [MX + s for s in SKIN[o.name]]
    D = np.stack([seg_dist(co, np.array((arm.matrix_world @ arm.data.bones[n].head_local)[:]), np.array((arm.matrix_world @ arm.data.bones[n].tail_local)[:])) for n in names], axis=1)
    order = np.argsort(D, axis=1)[:, :2]
    for n in names: o.vertex_groups.new(name=n)
    # 줄 양 끝은 붙은 소품의 뼈에 못 박는다(5 cm 안 = 그 뼈 100 %, 15 cm 까지 섞음) — 가까운 뼈 둘로만 나누면 끝이 목 · 가슴 뼈를 따라가
    # 머리를 숙이면 안전모 뒤 고리에서 6.7 cm 떨어졌다(Unity 검사 player_body_props_attached, 09-29)
    pins = []
    if o.name == "Lamp_Cord" and SAB != "nopin":
        for anchor, bname in (("Helmet_CordClip", "Head"), ("Battery_", "Hips")):
            pts = np.concatenate([np.array([(p.matrix_world @ v.co)[:] for v in p.data.vertices]) for p in props if p.name.startswith(anchor)])
            d = np.array([np.min(np.linalg.norm(pts - c, axis=1)) for c in co])
            pins.append((names.index(MX + bname), np.clip((0.15 - d) / 0.10, 0, 1)))
    for vi in range(len(co)):
        i0, i1 = order[vi]; w0, w1 = 1 / max(D[vi, i0], 1e-4), 1 / max(D[vi, i1], 1e-4); s = w0 + w1
        w = np.zeros(len(names)); w[i0] += w0 / s; w[i1] += w1 / s
        for bi, pin in pins: w = w * (1 - pin[vi]); w[bi] += pin[vi]
        for bi in np.nonzero(w)[0]: o.vertex_groups[names[bi]].add([vi], float(w[bi]), "REPLACE")
    if pins: print(f"INFO 램프 줄 끝 못 박음: 머리 100 % 점 {int((pins[0][1] >= 1).sum())} · 엉덩이 100 % 점 {int((pins[1][1] >= 1).sum())}")
    o.parent = arm; o.matrix_parent_inverse = arm.matrix_world.inverted()
    o.modifiers.new("Armature", "ARMATURE").object = arm
bpy.context.view_layer.update()

# ── 검사 ──
fails = []
fing = [f"{MX}{s}Hand{f}{k}" for s in ("Left", "Right") for f in ("Thumb", "Index") for k in (1, 2, 3)]
B.check(fails, "rig_fingers", all(f in bones for f in fing), f"뼈 {len(bones)} 개 · 손가락 뼈 엄지 · 검지 세 마디씩 양손 {sum(f in bones for f in fing)}/{len(fing)} (사용자 09-29 \"가\": 엄지 · 검지 두 줄)")
na = len(arms.data.polygons) if arms else 0
B.check(fails, "rig_arms_split", arms is not None and na > 500 and na + len(body.data.polygons) == n_faces0,
        f"팔 {na} 면 + 몸 {len(body.data.polygons)} 면 = {na + len(body.data.polygons)} (원래 {n_faces0}) — 팔 = 아래팔 · 손 뼈가 가장 센 면")
moved = []
for o in props:
    if o.name not in rigid: continue
    cur = np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices]); moved.append(float(np.abs(cur - world0[o.name]).max()))
attached = all(o.parent is arm and o.parent_type == "BONE" for o in props if o.name in rigid)
B.check(fails, "rig_props_attached", attached and max(moved) < 1e-4,
        f"딱딱한 소품 {len(rigid)} 개가 뼈 자식(머리 {sum(v.endswith('Head') for v in rigid.values())} · 엉덩이 {sum(v.endswith('Hips') for v in rigid.values())}) · 자리 어긋남 가장 큰 {max(moved)*1000:.3f} mm (< 0.1)")
sk_ok = [o.name for o in props if o.name in SKIN and any(m.type == "ARMATURE" for m in o.modifiers) and all(v.groups for v in o.data.vertices)]
B.check(fails, "rig_skinned_props", sorted(sk_ok) == sorted(SKIN), f"휘는 소품(무게 있음 · 뼈 따라 휨): {sk_ok}")
multi = [o.name for o in [body] + ([arms] if arms else []) + props if o.type == "MESH" and len(o.data.materials) != 1]
B.check(fails, "rig_textures", set(saved) == {"base", "nor_gl"} and saved["base"][0] == 4096, f"그림 파일 {sorted(saved)} (base · nor_gl, base 4096 px)")
thin = [o.name for o in props if len(o.data.polygons) == 0]
B.check(fails, "rig_props_have_faces", not thin, f"소품 {len(props)} 개 모두 면이 있다 — 면 없는 것 {thin or '없음'} (목수건 · 방독면 끈이 선만 남았던 적 있음)")
def signed_vol(o):
    bm = bmesh.new(); bm.from_mesh(o.data); v = bm.calc_volume(signed=True); bm.free(); return v
inward = [o.name for o in props if o.name in curve_names and signed_vol(o) < 0]
B.check(fails, "rig_normals_out", not inward, f"곡선에서 바꾼 소품 {sorted(curve_names)} 의 면이 바깥을 본다 — 안쪽인 것 {inward or '없음'}")
B.check(fails, "rig_one_material", not multi, f"물체마다 재질 하나 — 둘 이상인 것 {multi or '없음'}")
if SAB:
    print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails)); sys.exit(1 if fails else 0)

# ── ⑤ 내보내기 ──
os.makedirs(os.path.dirname(OUT_FBX), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "build", "player", "player_rig.blend"))
for o in bpy.data.objects: o.select_set(o is arm or o in (body, arms) or o in props)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=OUT_FBX, use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=False,
                         path_mode="STRIP", embed_textures=False, apply_scale_options="FBX_SCALE_ALL", mesh_smooth_type="FACE", use_armature_deform_only=True)
print(f"INFO 내보냄 {OUT_FBX} ({os.path.getsize(OUT_FBX)/1e6:.1f} MB) · 물체 {len([o for o in bpy.data.objects if o.select_get()])}")
print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails))
sys.exit(1 if fails else 0)
