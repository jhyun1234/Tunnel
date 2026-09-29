"""3D-P2 차례 1 굽기 (Blender) — 제안서 docs/제안서_3DP2_플레이어_재질_현실감.md (승인 09-30)
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P blender/rig/player_look_bake.py
  다음: python blender/rig/player_look.py (그림 짜기 — Blender 파이썬엔 PIL 이 없어 둘로 나눔)
입력: build/player/player_rig.blend (blender/rig/player_rig.py 가 만든 것 — 몸 · 팔 · 소품 · 뼈, 처음 자세)
몸(PlayerBody + PlayerArms, 같은 재질 · 같은 UV)을 2K 로 굽는다:
  ① 가림(AO, 거리 0.25 m) — 소품(탄띠 · 목수건 · 방독면 …)이 몸에 드리우는 그늘까지
  ② 자료(EMIT): R = 높이(발밑 0 → m) · G = 큰 얼룩 잡음 · B =잔 잡음 — 3D 자리에서 뽑아 UV 이음새에서 안 끊긴다
  ③ UV 밀도: 면마다 3D 넓이 ÷ UV 넓이 → 1 UV 가 몇 m 인가(가운데값) — 천 결 되풀이 크기
출력: build/player/look/{ao,data}.npy (2048², RGBA float, Blender 순서 = 아래 줄부터) · uv.txt"""
import bpy, os, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "build", "player", "look"); os.makedirs(OUT, exist_ok=True)
R = 2048
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "build", "player", "player_rig.blend"))
sc = bpy.context.scene
sc.render.engine = "CYCLES"
try:                                                        # 그래픽카드로 (없으면 CPU 그대로)
    pr = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            pr.compute_device_type = kind; pr.get_devices()
            if any(d.type == kind for d in pr.devices): break
        except TypeError: pass
    for d in pr.devices: d.use = True
    sc.cycles.device = "GPU"
except Exception as e: print("INFO GPU 못 씀:", e)
sc.cycles.samples = 64
if sc.world is None: sc.world = bpy.data.worlds.new("World")
sc.world.light_settings.distance = 0.25                    # 가림 거리 — 주머니 · 띠 밑 · 겨드랑이 크기

bodies = [bpy.data.objects["PlayerBody"], bpy.data.objects["PlayerArms"]]
mat = bodies[0].data.materials[0]; nt = mat.node_tree
img = bpy.data.images.new("look_bake", R, R, alpha=True, float_buffer=True)
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; nt.nodes.active = tex
for o in bpy.data.objects: o.select_set(o in bodies)
bpy.context.view_layer.objects.active = bodies[0]

def bake(kind, name):
    img.generated_color = (0, 0, 0, 0); img.source = "GENERATED"         # 안 구운 곳 = 알파 0
    bpy.ops.object.bake(type=kind, margin=8, use_clear=True)
    a = np.empty(R * R * 4, np.float32); img.pixels.foreach_get(a)
    np.save(os.path.join(OUT, name + ".npy"), a.reshape(R, R, 4))
    cov = (a.reshape(R, R, 4)[..., 3] > 0).mean()
    print(f"INFO 구움 {name}: 덮은 곳 {cov * 100:.1f} % · R 평균 {a.reshape(R, R, 4)[..., 0][a.reshape(R, R, 4)[..., 3] > 0].mean():.3f}")

bake("AO", "ao")

out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
old = out.inputs["Surface"].links[0].from_socket
geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nl = nt.nodes.new("ShaderNodeTexNoise"); nf = nt.nodes.new("ShaderNodeTexNoise")
nl.inputs["Scale"].default_value = 3.0; nl.inputs["Detail"].default_value = 4.0             # 큰 얼룩 (한 덩이 수십 cm)
nf.inputs["Scale"].default_value = 40.0; nf.inputs["Detail"].default_value = 6.0            # 잔 알갱이 (cm 아래)
comb = nt.nodes.new("ShaderNodeCombineColor"); emi = nt.nodes.new("ShaderNodeEmission")
L = nt.links.new
L(geo.outputs["Position"], sep.inputs[0]); L(geo.outputs["Position"], nl.inputs["Vector"]); L(geo.outputs["Position"], nf.inputs["Vector"])
L(sep.outputs["Z"], comb.inputs[0]); L(nl.outputs["Fac"], comb.inputs[1]); L(nf.outputs["Fac"], comb.inputs[2])
L(comb.outputs[0], emi.inputs["Color"]); L(emi.outputs[0], out.inputs["Surface"])
bake("EMIT", "data")
L(old, out.inputs["Surface"])

# UV 밀도 — 면 3D 넓이 ÷ UV 넓이 (두 몸 모두, 가운데값)
ratios = []
for o in bodies:
    me = o.data; uvl = me.uv_layers.active.data
    for p in me.polygons:
        uv = np.array([uvl[i].uv[:] for i in p.loop_indices])
        a_uv = 0.5 * abs(np.dot(uv[:, 0], np.roll(uv[:, 1], 1)) - np.dot(uv[:, 1], np.roll(uv[:, 0], 1)))
        if a_uv > 1e-9: ratios.append(p.area / a_uv)
m_per_uv = float(np.sqrt(np.median(ratios)))
open(os.path.join(OUT, "uv.txt"), "w").write(f"{m_per_uv:.4f}\n")
print(f"INFO UV 밀도: 1 UV = {m_per_uv:.3f} m (면 {len(ratios)} 개 가운데값)")
