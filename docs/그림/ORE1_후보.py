# ORE-1 차례 1 — 결 후보 둘(한국식 · 네모식)과 지금 광석을 같은 벽 · 같은 머리등으로, 실제 사진 넷 옆에 (09-27).
# 렌더 = blender/art/make_ore.py → build/art/ore1/. 사진이 들어가서 그림은 build/refs/ore/ 에만 쓴다(커밋 안 함). 이 코드만 커밋한다.
#   python docs/그림/ORE1_후보.py            → build/refs/ore/ORE1_후보.png
import os, sys, json
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, SS, C

HERE = os.path.dirname(__file__)
REN = os.path.join(HERE, "..", "..", "build", "art", "ore1")
REF = os.path.join(HERE, "..", "..", "build", "refs", "ore")
OUT = os.path.join(REF, "ORE1_후보.png")
W, H = 2400, 3600
S.new(W, H)
NOW, PICK = (255, 154, 60), (126, 208, 126)
info = json.load(open(os.path.join(REN, "info.json")))

def photo(x, y, w, h, full, cap, sz=16, hl=None):
    S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], fill=(28, 26, 25))
    if os.path.exists(full):
        im = Image.open(full).convert("RGB"); k = min(w * SS / im.width, h * SS / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        S.img.paste(im, (int((x + (w * SS - im.width) / SS / 2) * SS), int((y + (h * SS - im.height) / SS / 2) * SS)))
    else:
        text(x + w / 2, y + h / 2, "(없음)\n" + os.path.basename(full), 15, C["sub"], anchor="mm")
    if hl: S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], outline=hl, width=4 * SS)
    yy = y + h + 6
    for i, ln in enumerate(cap.split("\n")):
        for piece in wrap(ln, sz, w):
            text(x + 2, yy, piece, sz, C["text"] if i == 0 else C["sub"]); yy += sz * 1.3

text(24, 16, "ORE-1 차례 1 — 벽에 박힌 석탄: 결 후보 둘 (09-27)", 36, b=True)
text(24, 64, "승인: 광석 = 석탄 · 탄층 띠 비스듬 30° · 두께 1.2 m. 같은 벽(울퉁불퉁 ±5 cm) · 같은 머리등(원뿔 60°, 게임 LAMP_ANGLE_DEG). 빛·밝기는 게임이 아니다(Blender EEVEE).", 19, C["sub"])
text(24, 92, "가운데 = 캘 덩이 30 × 22 × 18 cm — 벽에서 9 cm 나오고 위가 8° 들림 · 둘레 까만 틈 · 막 벌어진 결 면이라 조금 더 반짝(우리 판단). 둘레 덩이는 가장자리로 갈수록 벽에 묻혀 띠 칠과 이어짐.", 19, C["sub"])

COLS = [("now", "지금 — 둥근 덩이 (ore.gltf 09-14)", "띠 없음(지금 게임 그대로) · 벽에서 0.12 m · × 1.2", NOW),
        ("kr", "후보 ① 한국식 — 비스듬한 평행 금", "금 방향 수평에서 60° · 길쭉한 판 12~30 × 3~8 cm (Rk04 · Rk08)", None),
        ("grid", "후보 ② 네모식 — 직각 두 결", "띠와 나란한 층 6~12 cm × 벽돌 8~20 cm, 줄마다 엇갈림 (Rw13 · Rw19)", None)]
cw, ch = 760, 570
x0 = 24
y = 130
for i, (tag, title, sub, hl) in enumerate(COLS):
    x = x0 + i * (cw + 24)
    text(x, y, title, 24, NOW if hl else C["text"], b=True)
    tri = info[tag]["tris"]
    text(x, y + 34, sub + " · 삼각형 %d" % tri, 16, C["sub"])
y += 70
ROWS = [("close", "0.9 m — 결 모양"), ("near", "1.9 m — 캘 때 서는 거리"), ("far", "4.5 m — 멀리서 알아보나 (밝기만 +1.5 올림: 게임 화면 밝기와 다름)"), ("lump", "빠져 굴러 나온 덩이 (~20 cm, 모난 덩이 — Rk25 · Rw14)")]
for shot, label in ROWS:
    text(24, y, label, 21, b=True); y += 32
    for i, (tag, *_rest) in enumerate(COLS):
        photo(x0 + i * (cw + 24), y, cw, ch, os.path.join(REN, "%s_%s.png" % (tag, shot)), "", hl=_rest[2])
    y += ch + 24

text(24, y, "실제 사진 (조사 12) — 비교용", 24, b=True); y += 40
pw, ph = 575, 400
refs = [("k04_nculture_coalpick_face.jpg", "Rk04 한국 · 콜픽 막장\n벽 전체 탄 · 비스듬한 날·줄 면 · 젖은 듯 반짝"),
        ("k08_nculture_bongsan_pick_colonial.jpg", "Rk08 황해 봉산(일제강점기)\n평행한 금 45~60° · 길쭉한 블록"),
        ("w13_nara_fain1946_undercut.jpg", "Rw13 켄터키 1946\n벽돌처럼 네모 · 위 평평한 판 돌"),
        ("w14_nara_fain1946_shotcoal.jpg", "Rw14 같은 곳 · 발파 직후\n모난 덩이 · 깨진 면마다 번쩍")]
for i, (p_, c_) in enumerate(refs):
    photo(24 + i * (pw + 17), y, pw, ph, os.path.join(REF, p_), c_, sz=16)
y += ph + 70
for ln in ["고를 것: ① 한국식 / ② 네모식 (또는 둘 다 아님 — 무엇이 다른지 말해 주면 고친다).",
           "게임에 넣은 뒤(차례 2) 실행 파일에서 볼 것: 멀리서 알아보이나 · 반짝임 세기(판정 키) · 캐는 동안 덩이가 들뜨고 빠지는 모습 · 띠가 ART-1 벽과 어울리나."]:
    for piece in wrap("· " + ln, 20, W - 60):
        text(24, y, piece, 20); y += 30
y_end = y + 30
S.img = S.img.crop((0, 0, W * SS, y_end * SS)).resize((W, y_end), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
