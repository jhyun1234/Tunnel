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
        "coal": ("Rock035", 0.0, (0.8, 0.8, 0.8), 1.0, 1.3),        # 석탄 가루 = 검정 · 거칠게 (매끈하게 하면 주황 전등이 금박처럼 번졌다 — 09-27 캡처). 가루는 덩어리가 거의 덮는다
        "coal_lump": ("Rock035", 0.0, (0.75, 0.75, 0.75), 1.0, 0.75)}
# 석탄 둘 다 쇠(metal 1) + 짙은 회색 바탕 = 반사율 약 1.5~2 % — 보통 재질(4 %)은 헤드램프가 1 m 안에서 면마다 하얗게·주황으로 번쩍였다(판정 ③ "빛 반사가 심하다").
# 무연탄은 "쇠 같은 짙은 회색 윤기"라 쇠로 두고 바탕을 어둡게 하면 가루는 거의 검정, 덩어리는 면 몇 개만 은은하게 (09-27). 채도 0 — Rock035 의 푸른 기가 쇠 반사에서 파란 결정처럼 보였다  # 석탄 덩어리 = 검정 + 면마다 조금 반짝 (무연탄)
import random, math
from PIL import ImageFilter
def tile_noise(n, cells, seed, blur):                     # 이어 붙여도 이음새 없는 낮은 주파수 잡음 (0..255)
    rnd = random.Random(seed); g = Image.new("L", (cells, cells))
    g.putdata([rnd.randrange(256) for _ in range(cells * cells)])
    big = Image.new("L", (cells * 3, cells * 3))
    for i in range(3):
        for j in range(3): big.paste(g, (i * cells, j * cells))
    big = big.resize((n * 3, n * 3), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
    return big.crop((n, n, 2 * n, 2 * n))
for name, (src, sat, tint, metal, *rk) in MATS.items():
    c = ImageEnhance.Color(Image.open(os.path.join(CT, src + "_Color.jpg")).convert("RGB")).enhance(sat)
    r, g, b = c.split(); c = Image.merge("RGB", [ch.point(lambda v, k=k: int(v * k)) for ch, k in zip((r, g, b), tint)])
    c.save(os.path.join(OUT, name + "_Diffuse.jpg"), quality=92)
    rough = Image.open(os.path.join(CT, src + "_Roughness.jpg")).convert("L").resize(c.size).point(lambda v, k=(rk or [1.0])[0]: min(255, int(v * k)))   # 거칠기 배율 (석탄)
    Image.merge("RGB", [Image.new("L", c.size, 255), rough, Image.new("L", c.size, int(metal * 255))]).save(os.path.join(OUT, name + "_arm.jpg"), quality=92)
    shutil.copy(os.path.join(CT, src + "_NormalGL.jpg"), os.path.join(OUT, name + "_nor_gl.jpg"))
    if name == "coal_lump":                                  # 덩어리 = 반쯤 무광 (거칠기 0.5~0.75 얼룩) + 약한 바위 노멀 — 판정 ③ "빛 반사가 심하다": 0.16 유리는 면마다 번쩍+번짐, 0.45 은박지, 0.75 고르면 회색 돌 (09-27)
        Image.merge("RGB", [Image.new("L", c.size, 255), tile_noise(c.size[0], 16, 13, 3).point(lambda v: int(128 + v * 0.25)), Image.new("L", c.size, int(metal * 255))]).save(os.path.join(OUT, name + "_arm.jpg"), quality=95)
        nr = Image.open(os.path.join(CT, src + "_NormalGL.jpg")).convert("RGB").resize(c.size)
        Image.blend(nr, Image.new("RGB", c.size, (128, 128, 255)), 0.55).save(os.path.join(OUT, name + "_nor_gl.jpg"), quality=95)
    print(name, c.size)

# ---------- 갱목 다시 (사용자 09-27 "나무들 모델링을 현실적으로" → 조사 11 docs/기획서/조사/11_갱목_동발_레퍼런스.md)
# timber = 통나무 옆면 1 m × 1 m: 껍질 벗긴 거친 나무(rough_wood, 세로 결 · 세로 금) 위에 소나무 껍질(pine_bark — 회색 겉껍질 · 붉은 갈색 속껍질)이 군데군데 (9/12)
#          + 탄가루·물의 회색~검정 막 (11/13). 결은 세로(= 통나무 길이 방향, UV v). 몸통을 도는 고리 줄무늬 없음 (0/21)
# log_end = 잘린 끝 (나이테 · 갈라짐, 밝은 황갈 — 나이테는 잘린 끝에만) · wedge = 막 쪼갠 밝은 쐐기 · lagging = 오래된 덧판 (회색~검정 거친 널)
N = 1024
def src(i, s): return Image.open(os.path.join(CT, "%s_%s.jpg" % (i, s)))
def tiled(i, s, k, mode):                                   # k × k 번 되풀이해 1 m 에 맞춤
    im = src(i, s).convert(mode).resize((N // k, N // k), Image.LANCZOS); out = Image.new(mode, (N, N))
    for a in range(k):
        for b in range(k): out.paste(im, (a * N // k, b * N // k))
    return out
mask = tile_noise(N, 6, 3, 18).point(lambda v: 255 if v > 150 else 0).filter(ImageFilter.GaussianBlur(6))   # 껍질이 남은 곳 (흰색) ≈ 35 %
dust = tile_noise(N, 10, 9, 10)                                                                             # 탄가루 막 얼룩
wood_c, bark_c = tiled("rough_wood", "Color", 2, "RGB"), src("pine_bark", "Color").convert("RGB").resize((N, N), Image.LANCZOS)
wood_c = Image.merge("RGB", [ch.point(lambda v, k=k: int(v * k)) for ch, k in zip(wood_c.split(), (0.92, 0.78, 0.62))])   # 벗겨진 곳 = 황갈 (회색 나무를 따뜻하게)
col = Image.composite(bark_c, wood_c, mask)
film = Image.new("RGB", (N, N), (22, 20, 18))
col = Image.composite(film, col, dust.point(lambda v: int(120 + v * 0.45)))                                # 회색~검정 막 45~90 % (판정 ③: 밝은 갈색 · 주황 점이 번들 — 사진 R1 R3 은 검회색 막이 대부분)
col.save(os.path.join(OUT, "timber_Diffuse.jpg"), quality=92)
rough = Image.composite(src("pine_bark", "Roughness").convert("L").resize((N, N)), tiled("rough_wood", "Roughness", 2, "L"), mask)
Image.merge("RGB", [Image.new("L", (N, N), 255), rough.point(lambda v: min(255, int(215 + v * 0.16))), Image.new("L", (N, N), 0)]).save(os.path.join(OUT, "timber_arm.jpg"), quality=92)   # 거칠기 0.85~1 (마른 나무·탄가루 = 무광, 판정 ③ "빛 반사가 심하다")
Image.composite(src("pine_bark", "NormalGL").convert("RGB").resize((N, N)), tiled("rough_wood", "NormalGL", 2, "RGB"), mask).save(os.path.join(OUT, "timber_nor_gl.jpg"), quality=92)
print("timber", col.size)
# 잘린 끝: 가운데 (0.5, 0.5) · 반지름 0.5 = 통나무 반지름. 나이테(흔들리는 동심원) + 갈라짐 셋 + 가장자리 껍질 띠, 먼지로 조금 어둡게
M_ = 512; rnd = random.Random(21); end = Image.new("RGB", (M_, M_)); px = end.load(); wob = tile_noise(M_, 8, 5, 12).load()
cracks = [rnd.uniform(0, 6.28) for _ in range(3)]
for y in range(M_):
    for x in range(M_):
        dx, dy = (x - M_ / 2) / (M_ / 2), (y - M_ / 2) / (M_ / 2); r = math.hypot(dx, dy); a = math.atan2(dy, dx)
        ring = 0.5 + 0.5 * math.sin((r + (wob[x, y] - 128) / 2500) * 95)
        base = (150 + 35 * ring, 112 + 28 * ring, 70 + 18 * ring)
        if r > 0.9: base = (70, 58, 48)                                                               # 껍질 띠
        if any(abs(((a - c + 3.1416) % 6.2832) - 3.1416) < 0.02 * (1 - r) + 0.004 and r < 0.85 for c in cracks): base = (40, 32, 24)
        k = 0.62 + 0.2 * (1 - r)
        px[x, y] = tuple(int(v * k) for v in base)
end.save(os.path.join(OUT, "log_end_Diffuse.jpg"), quality=92)
Image.merge("RGB", [Image.new("L", (M_, M_), 255), Image.new("L", (M_, M_), 215), Image.new("L", (M_, M_), 0)]).save(os.path.join(OUT, "log_end_arm.jpg"), quality=92)
Image.new("RGB", (M_, M_), (128, 128, 255)).save(os.path.join(OUT, "log_end_nor_gl.jpg"), quality=95)
print("log_end", end.size)
# 쐐기 = 막 쪼갠 밝은 노란 나무 (조사 11: 사진 6 · 문서 4) / 덧판 = 오래된 회색~검정 거친 널 (weathered_planks 를 어둡게, 채도 낮게)
w = ImageEnhance.Brightness(Image.merge("RGB", [ch.point(lambda v, k=k: min(255, int(v * k))) for ch, k in zip(tiled("rough_wood", "Color", 2, "RGB").split(), (1.25, 1.02, 0.66))])).enhance(1.25)
# 판자 질감은 결을 가로(u)로 돌린다 — 판자 그물 UV 가 u = 길이 (mine_props.board). 노멀은 돌리면 X·Y 가 바뀌므로 채널도 맞춘다 (가로 결: R ↔ G, 새 G = 255 − 옛 R)
def rot_nor(im):
    r, g, b = im.convert("RGB").transpose(Image.ROTATE_90).split(); return Image.merge("RGB", [g, r.point(lambda v: 255 - v), b])
rw_rough = tiled("rough_wood", "Roughness", 2, "L").transpose(Image.ROTATE_90); rw_nor = rot_nor(tiled("rough_wood", "NormalGL", 2, "RGB"))
w.transpose(Image.ROTATE_90).save(os.path.join(OUT, "wedge_Diffuse.jpg"), quality=92)
Image.merge("RGB", [Image.new("L", (N, N), 255), rw_rough, Image.new("L", (N, N), 0)]).save(os.path.join(OUT, "wedge_arm.jpg"), quality=92)
rw_nor.save(os.path.join(OUT, "wedge_nor_gl.jpg"), quality=92)
lg = tiled("rough_wood", "Color", 2, "RGB").transpose(Image.ROTATE_90)                                 # 오래된 덧판 = 거친 나무 한 장(널 이음 무늬 없음) · 탄가루로 회색~검정
lg = Image.composite(Image.new("RGB", (N, N), (20, 18, 16)), Image.merge("RGB", [ch.point(lambda v, k=k: int(v * k)) for ch, k in zip(lg.split(), (0.62, 0.56, 0.5))]), dust.point(lambda v: int(60 + v * 0.4)))
lg.save(os.path.join(OUT, "lagging_Diffuse.jpg"), quality=92)
Image.merge("RGB", [Image.new("L", (N, N), 255), rw_rough.point(lambda v: min(255, v + 25)), Image.new("L", (N, N), 0)]).save(os.path.join(OUT, "lagging_arm.jpg"), quality=92)
rw_nor.save(os.path.join(OUT, "lagging_nor_gl.jpg"), quality=92)
print("wedge · lagging")
