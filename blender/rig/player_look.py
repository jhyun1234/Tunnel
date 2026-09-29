"""3D-P2 차례 1 그림 짜기 (시스템 python + numpy + PIL) — 제안서 docs/제안서_3DP2_플레이어_재질_현실감.md (승인 09-30)
  python blender/rig/player_look.py        (먼저 Blender 로 blender/rig/player_look_bake.py)
입력: build/player/look/{ao,data}.npy · uv.txt (굽기) · Assets/Tunnel/Player/Textures/player_base.png (몸 색 4K, 그대로 둠)
      build/art/cand_tex/*.jpg (CC0 — ART-1 에서 받은 rusty_painted_metal · rusty_metal_03 · Rock035 + 3D-P2 denim_fabric)
출력 Assets/Tunnel/Player/Textures/:
  player_ms.png (2K, URP 쇠 · 매끈함: R = 쇠 0, A = 매끈함 = 1 − 거칠기 — 부위를 몸 색으로 가름: 옷 · 흰 면 · 장화 · 장갑)
  player_ao.png (2K, 가림) · player_detail_mask.png (2K, A = 천 결을 입힐 곳 = 옷 + 흰 면)
  player_base_dirt{1,2,3}.jpg (4K, 탄가루 옅게 · 보통 · 짙게 — 오목한 곳 + 아래쪽 + 큰 얼룩 + 잔 알갱이)
  cloth_detail_nor_gl.png · cloth_detail_albedo.png (512, 이음 없이 되풀이 — denim 에서 솔기 없는 곳, 큰 주름은 빼고 결만)
  props/<재질>_Diffuse.jpg · _ms.png · _nor_gl.jpg (1K, 되풀이 — 소품 UV 1 = 0.3 m)
  look.txt (UV 밀도 — Unity 설정이 천 결 되풀이 크기에 쓴다)
자기 검사(FAIL 이면 종료 1). 사보타주 SABOTAGE=noao(가림을 1 로) → look_ao FAIL · flatrough(윤기 한 값) → look_parts FAIL · notile(되풀이 손질 없이) → look_cloth_tile FAIL"""
import os, sys, numpy as np
from PIL import Image, ImageFilter
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LK = os.path.join(ROOT, "build", "player", "look"); CT = os.path.join(ROOT, "build", "art", "cand_tex")
TX = os.path.join(ROOT, "Assets", "Tunnel", "Player", "Textures"); PX = os.path.join(TX, "props")
os.makedirs(PX, exist_ok=True)
SAB = os.environ.get("SABOTAGE", "")
fails = []
def check(name, ok, msg):
    print(("PASS " if ok else "FAIL ") + name + " — " + msg)
    if not ok: fails.append(name)

# ── 굽기 결과 (Blender 순서 = 아래 줄부터 → 위아래 뒤집어 그림 순서로) ──
ao4 = np.flipud(np.load(os.path.join(LK, "ao.npy"))); da4 = np.flipud(np.load(os.path.join(LK, "data.npy")))
cov = ao4[..., 3] > 0
ao = np.where(cov, ao4[..., 0], 1.0) if SAB != "noao" else np.ones(cov.shape, np.float32)
z, nl, nf = da4[..., 0], da4[..., 1], da4[..., 2]
N = ao.shape[0]
base4 = Image.open(os.path.join(TX, "player_base.png")).convert("RGB")
base = np.asarray(base4.resize((N, N), Image.LANCZOS), np.float32) / 255

# ── 부위 가르기 (몸 색 + 높이) — Meshy 그림 판은 손에 큰 조각을 줘서 장갑이 그림 넓이로는 16 % (손 높이 0.90~1.02 m, 09-30 확인)
lum = base @ np.array([0.2126, 0.7152, 0.0722], np.float32)
glove = (base[..., 0] > base[..., 1] * 1.5) & (base[..., 0] > 0.15)                      # 적갈색 고무 장갑
dark = cov & ~glove & (z < 0.35)                                       # 고무 장화 = 장화 목 34 cm 아래 (짙은 회색이라 색으로는 옷과 못 가름)
white = ~glove & ~dark & (lum > 0.5)                                   # 흰 소매 · 면장갑 등
skin = ~glove & ~dark & ~white & (base[..., 0] > base[..., 1] * 1.15) & (base[..., 0] > base[..., 2] * 1.3) & (lum > 0.3)   # 살(방독면 · 목수건 밑)
hair = ~glove & ~dark & (lum < 0.05)                                   # 머리카락(안전모 밑)
cloth = cov & ~glove & ~dark & ~white & ~skin & ~hair
frac = {k: float((m & cov).sum() / cov.sum()) for k, m in (("cloth", cloth), ("white", white), ("glove", glove), ("boots", dark), ("skin", skin), ("hair", hair))}
print("INFO 부위 몫", {k: f"{v * 100:.1f} %" for k, v in frac.items()})

# ── 탄가루 · 때: 오목한 곳 + 아래쪽(무릎 밑 · 장화) + 큰 얼룩 + 잔 알갱이 ──
crev = np.clip((0.85 - ao) / 0.5, 0, 1) ** 1.2
low = np.clip((0.55 - z) / 0.45, 0, 1)
blot = np.clip((nl - 0.45) / 0.3, 0, 1)
smudge = np.clip((nf - 0.55) / 0.2, 0, 1)                             # 손때 · 문지른 자국 (몇 cm)
d = np.clip(0.55 * crev + 0.45 * low + 0.45 * blot + 0.25 * smudge + 0.15 * (nf - 0.5), 0, 1)
d *= np.where(white, 1.2, np.where(dark, 0.6, 1.0))
DUST = np.array([0.050, 0.048, 0.045], np.float32)                    # 석탄 가루 (짙은 회색, 살짝 따뜻)
LEVELS = (0.45, 0.8, 1.2)                                              # 옅게 · 보통 · 짙게 (사용자 09-30 처음 = 보통)

# ── 윤기 (URP 매끈함 = 1 − 거칠기) ※ 우리 판단 — 판정 키 Shift+3 4 로 전체 배율 ──
ROUGH = {"cloth": 0.92, "white": 0.95, "boots": 0.55, "glove": 0.65}
rough = np.full(ao.shape, ROUGH["cloth"], np.float32)
if SAB != "flatrough":
    rough[white] = ROUGH["white"]; rough[dark] = ROUGH["boots"]; rough[glove] = ROUGH["glove"]; rough[skin] = 0.6; rough[hair] = 0.7
rough = np.clip(rough + (nf - 0.5) * 0.1 + d * LEVELS[1] * 0.05, 0.02, 1)
def save_rgba(path, rgb, a):
    Image.fromarray(np.dstack([np.clip(rgb, 0, 1), np.clip(a, 0, 1)[..., None]]).__mul__(255).round().astype(np.uint8), "RGBA").save(path)
save_rgba(os.path.join(TX, "player_ms.png"), np.zeros(ao.shape + (3,), np.float32), 1 - rough)
Image.fromarray((np.clip(ao, 0, 1) * 255).round().astype(np.uint8), "L").save(os.path.join(TX, "player_ao.png"))
mask = np.asarray(Image.fromarray(((cloth | white) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
save_rgba(os.path.join(TX, "player_detail_mask.png"), np.repeat(mask[..., None], 3, 2), mask)

# 때 판 셋 (4K): 2K 때 세기를 4K 로 늘려 원래 색에 — lerp(색, 색 × 0.35 + 가루, k)
B4 = np.asarray(base4, np.float32) / 255
means = []
for i, amt in enumerate(LEVELS, 1):
    k = np.clip(d * amt, 0, 0.9)
    k4 = np.asarray(Image.fromarray((k * 255).astype(np.uint8)).resize(base4.size, Image.BILINEAR), np.float32)[..., None] / 255
    out = B4 * (1 - k4) + (B4 * 0.35 + DUST) * k4
    Image.fromarray((np.clip(out, 0, 1) * 255).round().astype(np.uint8)).save(os.path.join(TX, f"player_base_dirt{i}.jpg"), quality=92)
    means.append(float((out[..., :3].mean(axis=2))[np.asarray(Image.fromarray(cov.astype(np.uint8) * 255).resize(base4.size), bool)].mean()))
print("INFO 때 판 평균 밝기", [f"{m:.3f}" for m in means])

# ── 천 결 (denim_fabric, CC0): 솔기 없는 512 조각(= 0.5 m) → 3 cm 보다 큰 주름은 빼고 결 · 잔주름만 → 이음 없이 되풀이.
#    1 cm 아래 결만 남긴 첫 판은 2 m 에서 화면을 0.6 % 만 바꿨다(09-30 검사) — 2 m 에서 한 픽셀이 약 3 mm 라 결은 안 보이고 잔주름이 보인다 ──
def crop512(name, mode):
    return np.asarray(Image.open(os.path.join(CT, name)).convert(mode).crop((470, 40, 982, 552)), np.float32) / 255
def tileable(a):                                                    # 가장자리는 반 칸 민 판에서 — 되풀이 이음이 안 보이게
    n = a.shape[0]; r = np.roll(np.roll(a, n // 2, 0), n // 2, 1)
    t = np.minimum(np.arange(n), np.arange(n)[::-1]) / (n / 2); w = np.clip(np.minimum.outer(t, t) * 1.6, 0, 1)
    w = w[..., None] if a.ndim == 3 else w
    return a * w + r * (1 - w)
def highpass(a, radius):
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return a - np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255
nrm = crop512("denim_fabric_NormalGL.jpg", "RGB") * 2 - 1
HP = 30                                                               # 픽셀 = mm
nxy = np.dstack([highpass(nrm[..., 0] * 0.5 + 0.5, HP) * 2, highpass(nrm[..., 1] * 0.5 + 0.5, HP) * 2])
nxy = np.clip(nxy * (0.10 / max(np.abs(nxy).mean(), 1e-4)), -0.6, 0.6)   # 평균 기울기 0.10 — 세기는 판정 키 Shift+1 2 로
nxy = tileable(nxy)
nz = np.sqrt(np.clip(1 - (nxy ** 2).sum(2), 0, 1))
Image.fromarray(((np.dstack([nxy, nz]) * 0.5 + 0.5) * 255).round().astype(np.uint8)).save(os.path.join(TX, "cloth_detail_nor_gl.png"))
alb = crop512("denim_fabric_Color.jpg", "L")
alb = tileable(0.5 + np.clip(highpass(alb, HP) * 2.0, -0.18, 0.18))  # 가운데 회색 = 색 그대로(URP 세부 ×2)
Image.fromarray((alb * 255).round().astype(np.uint8), "L").convert("RGB").save(os.path.join(TX, "cloth_detail_albedo.png"))
# 되풀이 이음 = 마지막 줄 → 첫 줄 차이 ÷ 가장자리 바로 안쪽 이웃 줄 차이 (이음이 안 보이면 1 쯤 — 가운데는 두 판을 섞어 결이 조금 옅어서
# 가운데와 견주면 안 된다). 되풀이 손질 전 조각은 SABOTAGE=notile 로 잰다
if SAB == "notile": nxy = np.clip(np.dstack([highpass(nrm[..., 0] * 0.5 + 0.5, HP) * 2, highpass(nrm[..., 1] * 0.5 + 0.5, HP) * 2]) * (0.10 / max(np.abs(nxy).mean(), 1e-4)), -0.6, 0.6)
inner = float((np.abs(nxy[1] - nxy[0]).mean() + np.abs(nxy[-1] - nxy[-2]).mean() + np.abs(nxy[:, 1] - nxy[:, 0]).mean() + np.abs(nxy[:, -1] - nxy[:, -2]).mean()) / 2)
edge = float(np.abs(nxy[0] - nxy[-1]).mean() + np.abs(nxy[:, 0] - nxy[:, -1]).mean()) / inner

# ── 소품 질감 (1K 되풀이): (원본, 채도, 목표 색 = 지금 재질 색, 쇠, 거칠기 배율, 탄가루) ──
PROPS = {
    "PlayerHelmet": ("rusty_metal_03", 0.9, (0.72, 0.52, 0.08), 0.0, 1.0),      # 노랑 칠 + 녹 자국 = 때 · 긁힘 (k19)
    "PlayerBattery": ("rusty_painted_metal", 1.0, (0.45, 0.05, 0.04), 0.0, 1.0), # 빨간 칠 벗겨진 통
    "PlayerOlive": ("denim_fabric", 0.0, (0.17, 0.19, 0.10), 0.0, 1.0),          # 탄띠 · 수통 덮개 = 면 띠 결 (국방색 그대로, 사용자 09-30)
    "PlayerMetal": ("rusty_metal_03", 0.15, (0.55, 0.55, 0.56), 0.7, 1.0),       # 버클 · 받침 · 줄 걸이 = 닳은 쇠
    "PlayerAlu": ("rusty_metal_03", 0.1, (0.70, 0.71, 0.72), 0.8, 0.8),          # 배터리 뚜껑 · 수통 마개
    "PlayerBezel": ("rusty_metal_03", 0.8, (0.80, 0.62, 0.06), 0.3, 0.9),        # 램프 테
    "PM_lens_rim": ("rusty_metal_03", 0.1, (0.25, 0.25, 0.26), 0.8, 0.9),
    "PM_canister": ("rusty_metal_03", 0.3, (0.10, 0.11, 0.08), 0.2, 1.0),
    "PlayerLampBody": ("Rock035", 0.0, (0.05, 0.05, 0.05), 0.0, 0.9),
    "PlayerCord": ("Rock035", 0.0, (0.03, 0.03, 0.03), 0.0, 1.0),
    "PM_rubber_black": ("Rock035", 0.0, (0.035, 0.035, 0.035), 0.0, 0.9),        # 방독면 고무 = 약한 윤 + 먼지
    "PM_strap_black": ("denim_fabric", 0.0, (0.05, 0.05, 0.05), 0.0, 1.1),
    "PB_towel_dirty": ("denim_fabric", 0.0, (0.36, 0.35, 0.32), 0.0, 1.1),
}
dust = np.asarray(Image.open(os.path.join(CT, "Rock035_Color.jpg")).convert("L").resize((1024, 1024)), np.float32) / 255
dust = np.clip((dust - dust.mean()) / (dust.std() * 3) + 0.5, 0, 1)   # 석탄 결 = 때 얼룩
prop_ok = []
for name, (src, sat, target, metal, rmul) in PROPS.items():
    c = np.asarray(Image.open(os.path.join(CT, src + "_Color.jpg")).convert("RGB").resize((1024, 1024)), np.float32) / 255
    g = c @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    c = g[..., None] + (c - g[..., None]) * sat                        # 채도
    c = c * (np.array(target, np.float32) / np.maximum(c.reshape(-1, 3).mean(0), 1e-3))   # 평균을 지금 재질 색에 맞춤
    c = c * (1 - 0.35 * (1 - dust[..., None]) * (1 if metal < 0.5 else 0.6))            # 탄가루 얼룩
    Image.fromarray((np.clip(c, 0, 1) * 255).round().astype(np.uint8)).save(os.path.join(PX, name + "_Diffuse.jpg"), quality=92)
    r = np.asarray(Image.open(os.path.join(CT, src + "_Roughness.jpg")).convert("L").resize((1024, 1024)), np.float32) / 255
    save_rgba(os.path.join(PX, name + "_ms.png"), np.dstack([np.full(r.shape, metal, np.float32)] + [np.zeros(r.shape, np.float32)] * 2), 1 - np.clip(r * rmul, 0.02, 1))
    Image.open(os.path.join(CT, src + "_NormalGL.jpg")).convert("RGB").resize((1024, 1024)).save(os.path.join(PX, name + "_nor_gl.jpg"), quality=92)
    prop_ok.append(name)
m_per_uv = float(open(os.path.join(LK, "uv.txt")).read())
open(os.path.join(TX, "look.txt"), "w").write(f"m_per_uv {m_per_uv:.4f}\n")

# ── 자기 검사 ──
check("look_parts", frac["cloth"] > 0.45 and 0.01 < frac["glove"] < 0.25 and 0.02 < frac["white"] < 0.2 and 0.03 < frac["boots"] < 0.3 and np.ptp([rough[m & cov].mean() for m in (cloth, white, dark, glove) if (m & cov).any()]) > 0.3,
      f"옷 {frac['cloth'] * 100:.0f} % · 흰 면 {frac['white'] * 100:.0f} % · 장갑 {frac['glove'] * 100:.1f} % · 장화 {frac['boots'] * 100:.1f} % · 거칠기 옷 {rough[cloth].mean():.2f} · 흰 {rough[white].mean():.2f} · 장화 {rough[dark & cov].mean() if (dark & cov).any() else 0:.2f} · 장갑 {rough[glove].mean():.2f} (부위 사이 폭 > 0.3)")
check("look_ao", np.percentile(ao[cov], 5) < 0.55 and ao[cov].mean() > 0.6,
      f"가림 덮은 곳 평균 {ao[cov].mean():.2f} · 아래 5 % {np.percentile(ao[cov], 5):.2f} (< 0.55 = 오목한 곳이 어둡다)")
check("look_dirt_levels", means[0] > means[1] > means[2] and means[0] - means[2] > 0.02, f"때 판 밝기 옅게 {means[0]:.3f} > 보통 {means[1]:.3f} > 짙게 {means[2]:.3f}")
check("look_cloth_tile", edge < 1.3 and np.abs(nxy).mean() > 0.01, f"천 결 되풀이 이음 차 ÷ 안쪽 이웃 차 {edge:.2f} (< 1.3) · 결 세기 {np.abs(nxy).mean():.3f}")
check("look_props", len(prop_ok) == len(PROPS), f"소품 재질 {len(prop_ok)} 종 질감")
print("INFO UV 밀도 1 UV =", m_per_uv, "m")
print("ALL PASS" if not fails else "FAILS: " + ", ".join(fails))
sys.exit(1 if fails else 0)
