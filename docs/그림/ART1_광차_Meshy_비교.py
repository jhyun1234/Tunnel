# ART-1 차례 3 — Meshy 시험: 넣은 그림(Blender 광차) · 광장에서 Blender 광차 | Meshy 광차 (같은 자리 · 같은 빛)
#   python docs/그림/ART1_광차_Meshy_비교.py   (먼저 meshy_input.py · gen_meshy.py car1 · props_candidates.py ONLY=B2,M1)
import os
from PIL import Image
import sheet as S
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, "..", "..", "build", "art")
img, d = S.new(1640, 860)
S.text(20, 14, "Meshy 시험 — 광차 하나 (그림 → 3D, 30 크레딧 · 남음 2,779)", 22, b=True)
S.text(20, 48, "넣은 그림 = Blender 로 만든 광차(단색 배경 세 방향). Meshy 는 넣은 모양 · 색을 거의 그대로 따라 했다 — 모서리가 부드러워진 대신 석탄 결 · 보강 띠는 흐려짐.", 14, col=S.C["sub"])
for i in (1, 2, 3):
    im = Image.open(os.path.join(B, "meshy_in", "car_%d_crop.png" % i)).convert("RGB").resize((220 * S.SS, 220 * S.SS))
    img.paste(im, ((20 + (i - 1) * 232) * S.SS, 84 * S.SS))
S.text(20 + 3 * 232 + 10, 180, "← Meshy 에 넣은 그림 3장", 16, b=True)
for j, (f, t) in enumerate((("B2.png", "Blender 광차 (1,464 면)"), ("M1.png", "Meshy 광차 (11,300 면, 2K 질감)"))):
    im = Image.open(os.path.join(B, "props_render", f)).convert("RGB").resize((790 * S.SS, 494 * S.SS))
    img.paste(im, ((20 + j * 810) * S.SS, 320 * S.SS))
    S.text(28 + j * 810, 328, t, 18, b=True, col=S.C["rew"])
img.resize((img.width // S.SS, img.height // S.SS), Image.LANCZOS).save(os.path.join(HERE, "ART1_광차_Meshy_비교.png"))
print("saved")
