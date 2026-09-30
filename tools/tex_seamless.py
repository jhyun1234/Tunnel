"""색 그림 한 장(Gemini · GPT 결과) → 반복해도 이음새가 안 보이는 색 · 노멀 · 거칠기 세 장 (질감 비교, MAP4 규칙 6).
  python tools/tex_seamless.py <그림.png> <출력 폴더>
이음새: 절반 밀어 놓은 그림과 섞는다(가운데 = 원래 그림, 가장자리 = 밀어 놓은 그림 — GIMP "Tile Seamless" 와 같은 방법).
노멀: 밝기를 높이로 보고 기울기로 만든다(OpenGL 방식, 초록 = 위). 거칠기: 어두운 곳(젖은 석탄)을 조금 매끈하게. 둘 다 어림이다.
재어 알린다: 이음새 세기 = 가장자리 두 줄의 차이 ÷ 이웃한 두 줄의 보통 차이 (1 에 가까우면 이음새가 안 보인다)."""
import sys, pathlib
import numpy as np
from PIL import Image

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
a = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32) / 255.0
H, W, _ = a.shape

def seam(img):
    g = img.mean(axis=2); nb = np.abs(np.diff(g, axis=1)).mean()
    return float(np.abs(g[:, 0] - g[:, -1]).mean() / nb), float(np.abs(g[0, :] - g[-1, :]).mean() / np.abs(np.diff(g, axis=0)).mean())

before = seam(a)
off = np.roll(np.roll(a, W // 2, axis=1), H // 2, axis=0)
y, x = np.mgrid[0:H, 0:W]
d = np.maximum(np.abs(x - W / 2) / (W / 2), np.abs(y - H / 2) / (H / 2))       # 0 가운데 → 1 가장자리
w = np.clip((d - 0.55) / 0.4, 0, 1) ** 1.5                                     # 가장자리 쪽만 밀어 놓은 그림으로
col = a * (1 - w[..., None]) + off * w[..., None]
after = seam(col)
Image.fromarray((col * 255).astype(np.uint8)).save(out / "color.png")

h = col.mean(axis=2)
h = (h - h.min()) / (h.max() - h.min() + 1e-6)
k = 6.0                                                                         # 높이 세기 (어림)
dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * k
dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * k
n = np.dstack([-dx, dy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(out / "normal_gl.png")
rough = np.clip(0.55 + 0.4 * h, 0, 1)                                           # 어두운 석탄 = 조금 번들, 밝은 셰일 = 거칠게
Image.fromarray((rough * 255).astype(np.uint8)).save(out / "roughness.png")
print("SEAM before x %.2f y %.2f -> after x %.2f y %.2f  (%dx%d) -> %s" % (*before, *after, W, H, out))
