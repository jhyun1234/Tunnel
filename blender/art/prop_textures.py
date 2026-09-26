"""ART-1 차례 3 — Blender 로 만드는 물건의 질감을 게임용으로 굽는다 (시스템 python + PIL).
  python blender/art/prop_textures.py
후보 그림(mine_props.materials)은 Blender 노드로 채도를 낮추고 색을 곱했다 — glTF 는 그 노드를 못 내보내서 결과를 그림으로 굽는다.
입력: build/art/cand_tex/<CC0 id>_{Color,Roughness,NormalGL}.jpg (Poly Haven · ambientCG 1K — 받는 법 제안서 ART-1 차례 3)
출력: Assets/Tunnel/Art/props_tex/<재질>_Diffuse.jpg · _arm.jpg(R = 1, G = 거칠기, B = 쇠) · _nor_gl.jpg — 이름 규칙은 TextureImportRules(_arm · _nor_gl = 선형 · 노멀)."""
import os, shutil
from PIL import Image, ImageEnhance

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CT = os.path.join(ROOT, "build", "art", "cand_tex"); OUT = os.path.join(ROOT, "Assets", "Tunnel", "Art", "props_tex")
os.makedirs(OUT, exist_ok=True)
# 재질 = (CC0 원본, 채도, 색 곱, 쇠) — mine_props.materials 와 같은 값 + 쇠는 더 어둡게(후보 그림에서 밝은 베이지로 보였다, 09-27)
MATS = {"steel": ("rusty_metal_03", 0.3, (0.40, 0.38, 0.36), 0.6), "dark_steel": ("rusty_metal_03", 0.2, (0.24, 0.23, 0.22), 0.6),
        "paint": ("rusty_painted_metal", 0.55, (0.6, 0.6, 0.55), 0.3), "wood": ("weathered_brown_planks", 1.0, (0.5, 0.45, 0.4), 0.0),
        "plank": ("wood_planks_dirt", 1.0, (0.55, 0.5, 0.45), 0.0), "log": ("weathered_brown_planks", 1.0, (0.38, 0.32, 0.27), 0.0),
        "coal": ("Rock035", 1.0, (0.2, 0.2, 0.22), 0.0)}   # 석탄 = 검은 무연탄 (0.35 는 회색 먼지처럼 보였다 — 광차 비교 09-27, 조사 10 색)
for name, (src, sat, tint, metal) in MATS.items():
    c = ImageEnhance.Color(Image.open(os.path.join(CT, src + "_Color.jpg")).convert("RGB")).enhance(sat)
    r, g, b = c.split(); c = Image.merge("RGB", [ch.point(lambda v, k=k: int(v * k)) for ch, k in zip((r, g, b), tint)])
    c.save(os.path.join(OUT, name + "_Diffuse.jpg"), quality=92)
    rough = Image.open(os.path.join(CT, src + "_Roughness.jpg")).convert("L").resize(c.size)
    Image.merge("RGB", [Image.new("L", c.size, 255), rough, Image.new("L", c.size, int(metal * 255))]).save(os.path.join(OUT, name + "_arm.jpg"), quality=92)
    shutil.copy(os.path.join(CT, src + "_NormalGL.jpg"), os.path.join(OUT, name + "_nor_gl.jpg"))
    print(name, c.size)
