# 3D-P 차례 2 — Meshy 결과 판정 ② 한 장 (09-29). 그림은 build/player/ 에서 읽고 거기에 쓴다(커밋 안 함).
# 먼저: blender -b --factory-startup -P blender/rig/player_meshy_views.py -- player1   ·   blender -b -P blender/rig/player_meshy_views.py -- player1 gear
#   python docs/그림/3DP_Meshy.py            → build/player/P2_판정2.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "player")
OUT = os.path.join(ROOT, "P2_판정2.png")
W, H = 2400, 3400
S.new(W, H)
HL, OK = (255, 154, 60), (126, 208, 126)
def photo(x, y, w, h, name, cap, sz=16): S.photo(x, y, w, h, os.path.join(ROOT, name), cap, sz)
def section(y, title, sub=None): return S.section(y, W, title, sub)
def row(y, items, h, sz=16, gap=20):
    w = (W - 48 - gap * (len(items) - 1)) / len(items)
    for i, (p_, c_) in enumerate(items): photo(24 + i * (w + gap), y, w, h, p_, c_, sz)
    return y + h + 96

text(24, 16, "3D-P 차례 2 — Meshy 결과 · 판정 ② (09-29)", 36, b=True)
text(24, 64, "입력 = 판정 ① 을 통과한 밑그림 네 장(소품 뺀 몸 · 옷) + 글 설명 · Meshy 한 번 30 크레딧(남은 2,679) · 삼각형 30,762 · 그림 4K · "
             "밑그림과 같은 조명 · 같은 카메라", 19, C["sub"])

y = section(110, "① Meshy 가 만든 몸 (소품 없음)", "A 자세 그대로 · 장화 · 면 손목 · 고무장갑 · 주머니 · 흰 번호표 · 밑단은 밑그림을 따라왔다")
y = row(y, [("P2_player1_앞.png", "앞"), ("P2_player1_옆.png", "옆(오른쪽)"), ("P2_player1_뒤.png", "뒤"), ("P2_player1_비스듬히.png", "비스듬히")], 700)

y = section(y, "② 게임에서 보일 모습 = Meshy 몸 + 코드 소품", "안전모 · 램프 · 번호 · 줄 · 탄띠 · 배터리 · 수통은 차례 1 코드 그대로")
y = row(y, [("P2_player1_소품_앞.png", "앞"), ("P2_player1_소품_옆.png", "옆 — 뒷머리가 안전모 뒤로 불룩 나온다"),
            ("P2_player1_소품_뒤.png", "뒤 — 같은 뒷머리"), ("P2_player1_소품_얼굴.png", "얼굴 — 표정 없는 인형 같은 얼굴 · 목 깁스 같은 목수건"),
            ("P2_player1_소품_얼굴_옆.png", "얼굴 비스듬히")], 520, sz=15)

y = section(y, "③ 가까이 · 밑그림과 비교", None)
y = row(y, [("P2_player1_얼굴.png", "얼굴(안전모 없음) — 밑그림의 바가지 머리를 그대로 따라옴"),
            ("P2_player1_손.png", "오른손 — 손가락 다섯 · 면 손목 · 고무 (좋음)"),
            ("P2_player1_장화.png", "장화 — 매끈한 고무, 발가락 없음 (좋음)"),
            ("P1_앞.png", "(비교) 밑그림 앞"), ("P2_player1_소품_앞.png", "(비교) Meshy 몸 + 소품 앞")], 520, sz=15)

bx, bw, bh = 24, W - 48, 330
S.d.rounded_rectangle([bx * S.SS, y * S.SS, (bx + bw) * S.SS, (y + bh) * S.SS], radius=10 * S.SS, fill=(55, 51, 48))
cols = [("잘된 것", OK, ["장화: 매끈한 검은 고무, 발가락 홈 없음", "장갑: 손가락 다섯 · 흰 면 손목 · 적갈색 고무",
                         "윗도리: 주머니 둘 · 흰 번호표 · 단추 · 밑단 · 소매", "몸 비율 · A 자세 · 키가 밑그림과 같아 소품이 그대로 맞는다",
                         "면 30,762 · 그림 4K — 게임에 넣기 알맞은 크기"]),
        ("문제", HL, ["얼굴: 눈이 작고 표정 없는 인형 같다(3인칭 · 협동에서 보인다)",
                      "목수건: 살색 목깃 + 흰 덩어리 = 목 깁스처럼 보인다(밑그림의 목 경계를 따라옴)",
                      "뒷머리: 밑그림의 바가지 머리 뒤쪽이 안전모 뒤로 불룩 나온다",
                      "옷 · 얼굴이 깨끗하다 — 글 설명의 '낡고 탄가루 묻은' 이 거의 안 들어갔다",
                      "어깨 · 팔이 여전히 굵다(밑그림을 따라옴)"]),
        ("고칠 방법 (고르면 한다)", C["rew"], ["가. Blender 로 손질(0 크레딧): 뒷머리를 안전모 안으로 밀어 넣기 · 목깃을 옷 속으로 줄이고 코드 목수건을 두르기",
                                           "나. 그림만 다시 입히기(Meshy 10 크레딧): 같은 모양 · 같은 UV 에 탄가루 · 낡은 천 · 얼굴 살결을 더 세게 — 얼굴 모양(작은 눈)은 안 바뀐다",
                                           "다. 밑그림의 머리 · 목수건을 고쳐 다시 뽑기(30 크레딧)",
                                           "추천: 가 먼저(돈 안 듦) → 그래도 얼굴 · 때가 부족하면 나"])]
cw = (bw - 60) / 3
for i, (title, col, lines) in enumerate(cols):
    x0 = bx + 20 + i * (cw + 10); yy = y + 16
    text(x0, yy, title, 24, col, b=True); yy += 44
    for ln in lines:
        for piece in wrap("· " + ln, 19, cw - 24):
            text(x0, yy, piece, 19); yy += 27
        yy += 8
y_end = y + bh + 30
S.img = S.img.crop((0, 0, W * S.SS, y_end * S.SS)).resize((W, y_end), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
