"""3D-P 차례 1 — 같은 비율 비교 그림: 플레이어 밑그림 · 괴물(게임 속 크기 = STALKER_MODEL_SCALE 1.5 배) · 곡괭이(pick_meshy, 게임과 같은 것).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b build/player/player_blockout.blend -P blender/rig/player_lineup.py
출력: build/player/P1_같은비율_앞.png · P1_같은비율_옆.png (정사영 — 그림 위 1 px 가 어디서나 같은 길이)"""
import bpy, os, sys, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import player_blockout as B

OUT = os.path.join(ROOT, "build", "player")
MONSTER = os.path.join(ROOT, "Assets", "Tunnel", "Monster", "miner_m3.glb")      # BuildM1 기본 괴물(m3)
PICK = os.path.join(ROOT, "Assets", "Tunnel", "Props", "pick_meshy.glb")         # Tuning.PICK_MODEL
MONSTER_SCALE = 1.5                                                             # Tuning.STALKER_MODEL_SCALE


def imported(path):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def roots(objs): return [o for o in objs if o.parent is None or o.parent not in objs]


def bbox(objs):
    """뼈대로 움직인 뒤의 실제 점으로 잰다(bound_box 는 쉰 자세 기준이라 틀린다)."""
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in objs:
        if o.type != "MESH": continue
        ev = o.evaluated_get(dg); me = ev.to_mesh(); pts += [o.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


mon = imported(MONSTER)
for o in [o for o in mon if o.type == "MESH" and o.parent is None]:     # 가져오기가 만든 뼈 모양 공(−1~1 m, 이름이 한국어로 들어온다) — 몸이 아니다
    mon.remove(o); bpy.data.objects.remove(o)
for r in roots(mon): r.matrix_world = Matrix.Translation((1.35, 0, 0)) @ Matrix.Scale(MONSTER_SCALE, 4) @ r.matrix_world
lo, hi = bbox(mon)
for r in roots(mon): r.matrix_world = Matrix.Translation((0, 0, -lo.z)) @ r.matrix_world
pk = imported(PICK)
for r in roots(pk): r.matrix_world = Matrix.Translation((-0.85, 0, 0)) @ r.matrix_world
lo2, hi2 = bbox(pk)
for r in roots(pk): r.matrix_world = Matrix.Translation((0, 0, -lo2.z)) @ r.matrix_world
# 1 m 막대 · 1.7 m 눈금
bar = bpy.data.objects.new("Bar", bpy.data.meshes.new("Bar")); bpy.context.scene.collection.objects.link(bar)
import bmesh
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((-1.35, 0, 0.5)) @ Matrix.Diagonal((0.03, 0.03, 1.0, 1)))
bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((-1.35, 0, 1.7)) @ Matrix.Diagonal((0.12, 0.03, 0.01, 1)))
bm.to_mesh(bar.data); bm.free(); B.COL["bar"] = (0.9, 0.9, 0.9); bar.data.materials.append(B.material("bar"))
mlo, mhi = bbox(mon); plo, phi = bbox(pk)
print(f"INFO 괴물 머리 꼭대기(1.5 배, 가져온 자세) {mhi.z - mlo.z:.2f} m · 곡괭이 긴 축 {phi.z - plo.z:.2f} m")
B.setup_render((0.30, 0.30, 0.31), 0.9)
top = max(mhi.z, 1.8)
B.shoot(os.path.join(OUT, "P1_같은비율_앞.png"), "front", top / 2 + 0.05, max(3.9, top + 0.3), (1600, 1600), xc=0.35)
B.shoot(os.path.join(OUT, "P1_같은비율_옆.png"), "right", top / 2 + 0.05, max(3.4, top + 0.3), (1600, 1600))
