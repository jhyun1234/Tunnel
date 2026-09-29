# 3D-P 차례 1 — 모양 밑그림 판정 ① 한 장 (09-29). 그림은 build/player/ 에서 읽고 거기에 쓴다(커밋 안 함).
# 먼저: blender -b --factory-startup -P blender/rig/player_blockout.py  →  blender -b build/player/player_blockout.blend -P blender/rig/player_lineup.py
#   python docs/그림/3DP_모양.py            → build/player/P1_판정1.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "player")
OUT = os.path.join(ROOT, "P1_판정1.png")
W, H = 2400, 3600
S.new(W, H)
HL = (255, 154, 60)
def photo(x, y, w, h, name, cap, sz=16): S.photo(x, y, w, h, os.path.join(ROOT, name), cap, sz)
def section(y, title, sub=None): return S.section(y, W, title, sub)
def row(y, items, h, sz=16, gap=20):
    w = (W - 48 - gap * (len(items) - 1)) / len(items)
    for i, (p_, c_) in enumerate(items): photo(24 + i * (w + gap), y, w, h, p_, c_, sz)
    return y + h + 100

text(24, 16, "3D-P 차례 1 — 플레이어 모양 밑그림 · 판정 ① (09-29)", 36, b=True)
text(24, 64, "몸 바탕 = Blender Studio Human Base Meshes(CC0, 키 170 cm 로) · 옷 = 부위마다 부풀린 껍데기(조사 13 치수) · 소품 = 코드. "
             "Meshy 전의 '모양' 판정 — 재질 · 얼굴 · 옷 주름은 Meshy 가 입힌다. ※ = 기록 없이 지어낸 것.", 19, C["sub"])

y = section(110, "① 네 방향 (소품 있음)", "팔 A 자세 45° = Meshy · Mixamo 에 넣는 자세 · 게임에서는 동작이 입혀진다")
y = row(y, [("P1_앞.png", "앞\n노란 안전모 + 램프 · 검은 윗도리(가슴 주머니 2 · 흰 번호표) · 흰 목수건"),
            ("P1_옆.png", "옆(오른쪽)\n램프 줄 = 안전모 뒤 → 등 → 허리 뒤 배터리"),
            ("P1_뒤.png", "뒤\n번호 127(※) · 탄띠 · 오른쪽 빨간 배터리 · 왼쪽 수통(※)"),
            ("P1_비스듬히.png", "비스듬히\n장화 34 cm 에 바지를 넣음 · 면 손목 + 적갈색 고무장갑")], 860)

y = section(y, "② 가까이", "안전모 · 번호 · 램프 · 줄 · 허리 · 장갑")
y = row(y, [("P1_머리_앞.png", "머리 앞\n챙이 눈보다 2.7 cm 위 · 램프 지름 6.5 cm"),
            ("P1_머리_옆.png", "머리 옆\n번호는 뒤와 양옆 세 곳(사용자 승인)"),
            ("P1_머리_뒤.png", "머리 뒤\n뒤 줄 걸이에서 줄이 내려감"),
            ("P1_허리_뒤.png", "허리 뒤\n탄띠 폭 6 cm · 배터리 13 × 5 × 19 cm"),
            ("P1_손.png", "오른손\n근로장갑: 손목 6.5 cm 면 + 고무")], 440, sz=15)

y = section(y, "③ 같은 비율", "정사영 — 그림 위 길이가 어디서나 같다 · 흰 막대 1 m, 가로 눈금 1.7 m")
photo(24, y, 1150, 1150, "P1_같은비율_앞.png",
      "막대 1 m · 곡괭이(게임과 같은 pick_meshy, 긴 축 68 cm) · 플레이어 · 괴물(게임과 같은 1.5 배, 가져온 자세에서 머리 꼭대기 3.51 m)", 16)
bx, bw = 1200, W - 1224
S.d.rounded_rectangle([bx * S.SS, y * S.SS, (bx + bw) * S.SS, (y + 1150) * S.SS], radius=10 * S.SS, fill=(55, 51, 48))
text(bx + 18, y + 14, "치수 — 무엇이 기록이고 무엇이 지어낸 것인가", 23, C["rew"], b=True)
rows = [("키", "맨발 170 · 장화 신고 172 · 안전모까지 178 cm", "사용자 승인 09-29 (1979 20~24세 평균 167.7)"),
        ("안전모", "28 × 22.5 × 15 cm · 껍데기 폭 20 · 앞 쇠 받침 나사 4", "보령 · 문경 유물 · 영국 1981"),
        ("램프", "머리 지름 6.5 · 깊이 7 cm · 노란 테", "보령 사진 · 영국 70 × 75 × 73 mm"),
        ("배터리", "13 × 5 × 19 cm · 알루미늄 뚜껑 · 오른쪽 허리 뒤", "보령 유물 · 1981 · 1992 사진"),
        ("탄띠", "폭 6 cm · 국방색 · 허리(배 높이)", "문경 요대 · 1992 사진"),
        ("윗도리", "등길이 71 cm · 가슴 주머니 2 · 흰 번호표", "보령 유물 · 1981 영화"),
        ("장화", "높이 34 cm · 검은 고무 · 바지를 속에", "보령 유물 · 1992 사진"),
        ("장갑", "손목 6.5 cm 면 + 적갈색 고무", "삼척 기록 · 보령 유물 · 사용자 09-27"),
        ("※ 밑창", "2 cm", "기록 없음 — 사진 보고 어림"),
        ("※ 몸", "바탕이 근육질이라 팔 둘레 × 0.82 · 몸통 폭 × 0.92 · 다리 × 0.90", "기록 없음 — 마른 광부 사진 느낌"),
        ("※ 수통", "12 × 7 × 17 cm · 왼쪽 옆", "'탄띠에 수통' 만 기록, 치수 · 자리 없음"),
        ("※ 번호", "127 · 흰 페인트 · 뒤와 양옆", "기획서 '안전모 번호', 실제 기록 없음"),
        ("※ 목수건", "목 밑동에 두른 띠, 뒤 높고 앞 낮음", "'흰 광목' 만 기록, 모양은 어림"),
        ("※ 팔 자세", "A 자세 45°", "Meshy · Mixamo 에 넣기 좋은 자세")]
yy = y + 58
for k, v, src in rows:
    col = HL if k.startswith("※") else C["text"]
    text(bx + 18, yy, k, 18, col, b=True)
    for i, piece in enumerate(wrap(v, 18, 560)):
        text(bx + 150, yy + i * 23, piece, 18)
    for i, piece in enumerate(wrap(src, 16, bw - 740)):
        text(bx + 720, yy + i * 21, piece, 16, C["sub"])
    yy += max(len(wrap(v, 18, 560)) * 23, len(wrap(src, 16, bw - 740)) * 21) + 16
text(bx + 18, yy + 10, "넣지 않은 것(조사 근거): 자기구명기(1989 부터) · 보안경 · 손목시계 · 야광띠(후산부 안전모에 안 붙임) · 대나무 등 주머니 · 방진마스크", 16, C["sub"])
y += 1150 + 100

y = section(y, "④ Meshy 입력 후보 (소품 뺌 · 흰 바탕)", "승인된 방식: 안전모 · 램프 · 배터리 · 띠는 코드로 따로 → Meshy 에는 몸과 옷만")
w4 = 330
for i, (n, c_) in enumerate((("meshy_in_front.png", "앞"), ("meshy_in_left.png", "왼쪽"), ("meshy_in_back.png", "뒤"), ("meshy_in_right.png", "오른쪽"))):
    photo(24 + i * (w4 + 16), y, w4, 412, n, c_, 16)
bx = 24 + 4 * (w4 + 16) + 10; bw = W - bx - 24
S.d.rounded_rectangle([bx * S.SS, y * S.SS, (bx + bw) * S.SS, (y + 460) * S.SS], radius=10 * S.SS, fill=(55, 51, 48))
text(bx + 18, y + 14, "판정 ① 에서 볼 것", 23, C["rew"], b=True)
qs = ["1980년대 한국 탄광 광부로 보이나 — 전체 모습",
      "몸 비율: 아직 어깨 · 팔이 굵은가(바탕이 근육질 몸) — 더 마르게?",
      "안전모 크기 · 높이 · 램프 · 번호 자리(뒤와 양옆)",
      "허리: 탄띠 · 오른쪽 빨간 배터리 · 왼쪽 수통 · 등 뒤 줄",
      "장갑(면 손목 + 적갈색 고무) · 장화 · 목수건",
      "이 네 장(소품 뺀 몸 · 옷)을 Meshy 에 넣어도 되나 (약 30 크레딧 1번, 남은 2,709)"]
yy = y + 58
for i, q in enumerate(qs):
    for j, piece in enumerate(wrap(f"{i + 1}. {q}", 19, bw - 40)):
        text(bx + 22, yy, piece, 19); yy += 27
    yy += 8
y_end = y + 520
S.img = S.img.crop((0, 0, W * S.SS, y_end * S.SS)).resize((W, y_end), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
