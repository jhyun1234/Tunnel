# PICK-1 판정 ① 한 장: 지금 곡괭이 · A(Blender 코드) · B(Meshy) 를 같은 빛·같은 자리에서 (옆 가지 pick-hands, 09-27).
# 재료: blender/props/pick_compare.py → build/pick1/cmp_*.png · pick_views.py → build/pick1/pick_*_persp.png
# 보령 박물관 사진이 들어가서 그림은 build/pick1/ 에만 둔다(커밋 안 함). 이 코드만 커밋.
#   python docs/그림/PICK1_비교.py   → build/pick1/PICK1_비교.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, SS, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
P1 = os.path.join(ROOT, "build", "pick1")
W, H = 2400, 3000
S.new(W, H)
NOW = (255, 154, 60)

def paste(path, x, y, w, h, crop=None, hl=None):
    S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], fill=(20, 19, 18))
    if os.path.exists(path):
        im = Image.open(path).convert("RGB")
        if crop: im = im.crop(crop)
        k = min(w * SS / im.width, h * SS / im.height); im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        S.img.paste(im, (int(x * SS + (w * SS - im.width) / 2), int(y * SS + (h * SS - im.height) / 2)))
    else:
        text(x + w / 2, y + h / 2, "(옛 곡괭이는 안 찍음)", 18, C["sub"], anchor="mm")
    if hl: S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], outline=hl, width=3 * SS)

text(24, 16, "PICK-1 판정 ① — 곡괭이 셋, 같은 빛 · 같은 자리 (09-27)", 36, b=True)
text(24, 64, "Blender Eevee 그림 — 게임 화면이 아니다. 1인칭 칸은 게임의 카메라(시야 80°)·곡괭이 자리(PICK_POS · 기울기)·이마 헤드램프를 옮겨 흉내 냈다. 게임 판정은 ② 실행 파일에서.", 19, C["sub"])

# 기준 사진
y = 110
paste(os.path.join(ROOT, "build", "refs", "pick", "kr", "kr_01_boryeong381.jpg"), 24, y, 420, 280)
text(460, y + 6, "기준 — 보령석탄박물관 곡괭이 381 (e뮤지엄)", 24, C["rew"], b=True)
for i, ln in enumerate(["자루 64 · 머리 34 · 너비 6 cm. 한쪽만 길게 뾰족 + 반대쪽 짧은 네모 꼭지.",
                        "둥근 쇠 통에 자루 끝을 끼움. 쇠 통 아래 납작한 쇠붙이 하나. 거무스름한 나무, 세로 갈라짐.",
                        "A · B 는 자루 66 cm(사용자 09-27) · 머리 32 cm · 긴 축 68 cm 로 맞췄다 (지금 곡괭이: 자루 88 · 머리 46, 화면에서 0.75배)."]):
    text(460, y + 48 + i * 30, ln, 19)

# 열 제목
cols = [("지금 게임 곡괭이", "pick.gltf · 양쪽 휜 날 · 화면 0.75배", "old", NOW),
        ("A · Blender 코드", "make_pick.py · 삼각형 2,506 · 그림 1K 6장 · 2.7 MB · 비용 0", "blender", None),
        ("B · Meshy.ai", "A 를 찍은 그림 4장 입력 · 삼각형 7,938 · 그림 1K 3장 · 1.9 MB · 30 크레딧", "meshy", None)]
x0, cw, gap = 250, 700, 25
y = 420
for i, (t, sub, _, hl) in enumerate(cols):
    x = x0 + i * (cw + gap)
    text(x, y, t, 26, hl or C["text"], b=True)
    for j, piece in enumerate(wrap(sub, 17, cw)): text(x, y + 38 + j * 22, piece, 17, C["sub"])
y += 90

rows = [("1인칭\n지금 드는 자세\n(쉴 때)", "fp", (700, 150, 1920, 1080), 470),
        ("1인칭\n내려친 순간\n(기울기 +55°)", "hit", (700, 150, 1920, 1080), 470),
        ("참고:\n머리를 옆으로\n돌린 자세\n(PICK_YAW 0°)", "side", (700, 150, 1920, 1080), 470),
        ("램프 빛\n옆모습\n(박물관 사진처럼\n눕힘)", "lamp", (0, 280, 1000, 720), 300)]
for lab, tag, crop, rh in rows:
    text(24, y + rh / 2, lab, 20, C["text"], b=True, anchor="lm")
    for i, (_, _, key, hl) in enumerate(cols):
        paste(os.path.join(P1, "cmp_%s_%s.png" % (key, tag)), x0 + i * (cw + gap), y, cw, rh, crop=crop, hl=hl)
    y += rh + 18
rh = 300
text(24, y + rh / 2, "흰 바탕\n비스듬히", 20, C["text"], b=True, anchor="lm")
for i, (_, _, key, hl) in enumerate(cols):
    paste(os.path.join(P1, "pick_%s_persp.png" % key), x0 + i * (cw + gap), y, cw, rh, hl=hl)
y += rh + 30

notes = ["보인 것 — 지금 드는 자세(PICK_YAW 90°)는 날이 벽 쪽을 향해서, 한쪽 날 곡괭이는 1인칭에서 머리가 거의 안 보인다(쇠 통과 꼭지만). 옛 곡괭이는 날이 크게 휘어 보였다. 드는 자세·휘두르는 모양은 손(3D-P)·캐기 연출(MINE-1)과 같이 정한다 — 이번에 안 바꾼다.",
         "B(Meshy)가 지어 넣은 것 — 자루에 쇠띠 두 개(원본·A 에 없음), 자루가 머리 쪽으로 더 굵어짐, 나무가 A 보다 밝다. 날·꼭지·쇠 통 모양은 A 를 거의 그대로 따랐다.",
         "A 가 지어낸 것(출처 없음) — 쐐기 모양 · 나무 갈라짐 수 · 쇠·나무를 얼마나 검게 할지(보령 사진을 보고 어림)."]
for n in notes:
    for piece in wrap("· " + n, 19, W - 60):
        text(24, y, piece, 19); y += 27
    y += 6
y_end = y + 20
S.img = S.img.crop((0, 0, W * SS, y_end * SS)).resize((W, y_end), Image.LANCZOS)
out = os.path.join(P1, "PICK1_비교.png"); S.img.save(out); print(out)
