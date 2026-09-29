"""3D-P 차례 2 — Meshy 결과를 밑그림과 같은 조명 · 같은 카메라로 찍는다(판정 ②).
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/rig/player_meshy_views.py -- <이름>
입력: MineTunnel/mesh/meshy_<이름>.glb (저장소 밖). 키를 장화 신은 키 172 cm 로 맞추고 발바닥을 바닥에.
출력: build/player/P2_<이름>_{앞,옆,뒤,비스듬히,얼굴,손,장화}.png · 잰 값(면 수 · 그림 크기 · 팔 각도 어림)
  ... -- <이름> gear   → 밑그림 장면(build/player/player_blockout.blend)의 소품(안전모 · 램프 · 줄 · 탄띠 · 배터리 · 수통)을
                         Meshy 몸에 씌워 찍는다 → P2_<이름>_소품_{앞,옆,뒤,비스듬히,얼굴}.png (게임에서 보일 모습)"""
import bpy, os, sys, math
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import player_blockout as B

OUT = os.path.join(ROOT, "build", "player")
HEIGHT = B.STATURE + B.SOLE            # 장화 신은 키(밑그림과 같게)
GEAR_PREFIX = ("Helmet", "Lamp", "Battery", "Canteen", "Belt")


def src_of(name): return os.path.join(os.path.dirname(ROOT), "MineTunnel", "mesh", f"meshy_{name}.glb")


def load(name, gear=False):
    """Meshy GLB 를 가져와 키 · 자리를 맞춘다. gear = 밑그림 장면을 열고 밑그림 몸과 같은 키 · 가운데에(소품이 맞게) — 밑그림 몸 · 옷은 숨긴다.
    돌려받는 것: 가져온 그물 물체들."""
    if gear:
        bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "player_blockout.blend"))
        old = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith(GEAR_PREFIX)]
        bpy.context.view_layer.update()
        op = np.array([(o.matrix_world @ v.co)[:] for o in old for v in o.data.vertices]); olo, ohi = op.min(axis=0), op.max(axis=0)
        for o in old: o.hide_render = True
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=src_of(name))
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o not in before]
    bpy.context.view_layer.update()
    pts = np.array([(o.matrix_world @ v.co)[:] for o in meshes for v in o.data.vertices])
    lo, hi = pts.min(axis=0), pts.max(axis=0); c = (lo + hi) / 2
    if gear:
        k = (ohi[2] - olo[2]) / (hi[2] - lo[2]); oc = (olo + ohi) / 2
        M = Matrix.Translation((oc[0], oc[1], olo[2])) @ Matrix.Scale(k, 4) @ Matrix.Translation((-c[0], -c[1], -lo[2]))
    else:
        k = HEIGHT / (hi[2] - lo[2]); M = Matrix.Scale(k, 4) @ Matrix.Translation((-c[0], -c[1], -lo[2]))
    for o in [o for o in bpy.data.objects if o.parent is None and o not in before]: o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    pts = np.array([(o.matrix_world @ v.co)[:] for o in meshes for v in o.data.vertices])
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
    imgs = [(i.name, i.size[0], i.size[1]) for i in bpy.data.images if i.size[0]]
    print(f"INFO 물체 {len(meshes)} · 삼각형 {tris} · 원래 키 {hi[2]-lo[2]:.3f} (× {k:.3f}) · 폭 {np.ptp(pts[:,0]):.2f} · 앞뒤 {np.ptp(pts[:,1]):.2f} m · 그림 {imgs}")
    return meshes


def shoot_set(tag, meshes, close=True):
    B.setup_render((0.30, 0.30, 0.31), 0.9)
    for v, nm in (("front", "앞"), ("right", "옆"), ("back", "뒤"), ("quarter", "비스듬히")):
        B.shoot(os.path.join(OUT, f"P2_{tag}_{nm}.png"), v, 0.93, 2.05)
    head_z = HEIGHT - 0.12
    B.shoot(os.path.join(OUT, f"P2_{tag}_얼굴.png"), "front", head_z, 0.42, (900, 900))
    B.shoot(os.path.join(OUT, f"P2_{tag}_얼굴_옆.png"), "quarter", head_z, 0.42, (900, 900))
    if close:
        pts = np.array([(o.matrix_world @ v.co)[:] for o in meshes for v in o.data.vertices])
        hc = pts[pts[:, 0] < pts[:, 0].min() + 0.12].mean(axis=0)            # 오른손(−x 끝)
        B.shoot(os.path.join(OUT, f"P2_{tag}_손.png"), "front", float(hc[2]), 0.34, (900, 900), xc=float(hc[0]))
        B.shoot(os.path.join(OUT, f"P2_{tag}_장화.png"), "quarter", 0.22, 0.62, (900, 900))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]; name = args[0]; gear = "gear" in args
    meshes = load(name, gear)
    shoot_set(f"{name}_소품" if gear else name, meshes, close=not gear)
    print("done")
