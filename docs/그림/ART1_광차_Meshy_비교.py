# ART-1 차례 3 — Meshy 시험: 넣은 그림(Blender 광차) · 광장에서 Blender 광차 | Meshy 광차 (같은 자리 · 같은 빛)
#   python docs/그림/ART1_광차_Meshy_비교.py   (먼저 meshy_input.py · gen_meshy.py car1 · props_candidates.py ONLY=B2,M1)
import os
from PIL import Image
import sheet as S
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, "..", "..", "build", "art")
img, d = S.new(1640, 1180)
S.text(20, 14, "Meshy 시험 — 광차 (그림 → 3D 30 크레딧 + 질감 다시 10 크레딧 · 남음 2,769)", 22, b=True)
S.text(20, 48, "넣은 그림 = Blender 로 만든 광차(단색 배경 세 방향). Meshy 는 넣은 모양 · 색을 거의 그대로 따라 했다 — 모서리가 부드러워진 대신 석탄 결 · 보강 띠는 흐려짐.", 14, col=S.C["sub"])
for i in (1, 2, 3):
    im = Image.open(os.path.join(B, "meshy_in", "car_%d_crop.png" % i)).convert("RGB").resize((220 * S.SS, 220 * S.SS))
    img.paste(im, ((20 + (i - 1) * 232) * S.SS, 84 * S.SS))
S.text(20 + 3 * 232 + 10, 180, "← Meshy 에 넣은 그림 3장", 16, b=True)
for j, (f, t) in enumerate((("B2.png", "① Blender 광차 (1,464 면)"), ("M1.png", "② Meshy 광차 (11,300 면, 2K 질감)"), ("M2.png", "③ ② 에 글로 질감만 다시 (같은 그물)"))):
    x, y = (20 + (j % 2) * 810, 320 + (j // 2) * 514) if j < 2 else (20, 834)
    im = Image.open(os.path.join(B, "props_render", f)).convert("RGB").resize((790 * S.SS, 494 * S.SS))
    img.paste(im, (x * S.SS, y * S.SS)) if j < 2 else img.paste(im.resize((520 * S.SS, 325 * S.SS)), (x * S.SS, y * S.SS))
    S.text(x + 8, y + 8, t, 18, b=True, col=S.C["rew"])
S.text(560, 850, "③ 글: '탄가루에 검어진 짙은 회색 쇠 · 녹물 자국 · 찌그러진 모서리 · 윤기 나는 무연탄'", 15, col=S.C["sub"])
S.text(560, 876, "→ 칠 벗겨진 파란 쇠 + 번호 '21' + 녹슨 모서리 (글과 색이 다름), 석탄은 회색 먼지처럼", 15, col=S.C["exit"])
img.resize((img.width // S.SS, img.height // S.SS), Image.LANCZOS).save(os.path.join(HERE, "ART1_광차_Meshy_비교.png"))
print("saved")
