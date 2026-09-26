# 광차 다시 (09-27, 58차) — 옛 Blender 광차 | 새 광차(조사 10 공통점) 네 방향 + 공통점 표
#   Blender -P blender/art/cart_compare.py → python docs/그림/ART1_광차_다시.py
#   docs/그림/ART1_광차_다시.png = 사진 없음(저장소) · build/art/cart_v2/광차_다시_사진.png = 한국 사진 넷을 붙인 판(저작권 — 커밋 안 함)
import os, json
from PIL import Image
import sheet as S
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.join(HERE, "..", "..", "build", "art", "cart_v2")
REF = os.path.join(HERE, "..", "..", "build", "refs", "cart")
info = json.load(open(os.path.join(B, "info.json")))
ROWS = [
    ("몸통", "쇠판 U자 — 옆 곧게, 아래 둥글게", "11/21 (한국 5/9)"),
    ("맨 위", "테두리 띠 한 줄", "17/21"),
    ("밑", "따로 된 ㄷ자 쇠 밑틀 둘 + 받침", "11/21"),
    ("바퀴", "작은 원판 넷 · 지름 34 cm · 축 사이 76 cm · 몸통 밑에 숨음", "15/15 · 문서"),
    ("끝", "가운데 쇠 범퍼 덩어리 + 쇠고리 45 cm · 핀 31 cm", "7/21 · 문서 2"),
    ("크기", "2톤 207 × 100 × 121 cm", "문경 실물"),
    ("색", "짙은 회색 쇠 + 탄가루 + 녹 (게임 질감)", "한국 현장 8/8"),
    ("석탄", "테두리 위로 봉긋", "9/13"),
    ("뺀 것", "베이지 · 위가 넓은 상자 · 한쪽 막대 범퍼", "0/21"),
]
def sheet(with_photos):
    H = 1290 if with_photos else 1010
    img, d = S.new(1900, H)
    S.text(20, 14, "광차 다시 — 옛 Blender 광차 | 새 광차 (실제 광차 사진 21 · 문서 9 공통점, 조사 10)", 22, b=True)
    S.text(20, 48, "같은 자리 · 같은 빛 (Blender, 게임 빛 아님). 새 광차는 Blender 코드 모양 — 고르면 이 그림을 넣어 Meshy 로 살을 입힐지 정한다.", 14, col=S.C["sub"])
    for r, (tag, title) in enumerate((("old", "옛 광차 (지금 게임에 임시로)"), ("new", "새 광차"))):
        y = 84 + r * 300
        S.text(20, y, "%s — %s 삼각형 · 길이 %.2f × 폭 %.2f × 레일에서 높이 %.2f m (고리 · 석탄 빼고)" % (title, format(info[tag]["tris"], ","), *info[tag]["size"]), 17, b=True, col=S.C["rew"] if tag == "new" else S.C["sub"])
        for k, ang in enumerate(("34", "side", "end", "top")):
            im = Image.open(os.path.join(B, "%s_%s.png" % (tag, ang))).convert("RGB").resize((375 * S.SS, 250 * S.SS))
            img.paste(im, ((20 + k * 385) * S.SS, (y + 30) * S.SS))
    y = 700
    S.text(20, y, "공통점 → 새 광차에 넣은 것 (n/21 = 사진 21장 중 보인 수)", 17, b=True)
    for i, (a, b, c) in enumerate(ROWS):
        yy = y + 34 + i * 29
        S.text(30, yy, a, 15, b=True); S.text(120, yy, b, 15); S.text(760, yy, c, 15, col=S.C["sub"])
    S.text(1000, y, "못 찾은 것", 17, b=True)
    for i, t in enumerate(("1988 년 · 곳이 확인된 광차 사진", "석공 표준 칠 색 · 판 두께", "(레일 폭은 610 mm — 우리 레일 0.6 m 그대로)")):
        S.text(1010, y + 34 + i * 29, t, 15, col=S.C["sub"])
    if with_photos:
        S.text(20, 1010, "한국 사진 (비교용 — 저장소에 안 올림): 문경 U자 탄차 · 동원탄좌 광차 몸통 · 보령 축전차와 광차 · 보령 광차 운반", 15, col=S.C["sub"])
        for k, f in enumerate(("k12_much_문경_U자탄차.jpg", "k13_ncms_3787_동원탄좌_광차몸통.jpg", "k05_ncms_10707_보령_축전차와광차.jpg", "k04_ncms_10726_보령_광차운반.jpg")):
            im = Image.open(os.path.join(REF, f)).convert("RGB"); im.thumbnail((455 * S.SS, 240 * S.SS))
            img.paste(im, ((20 + k * 470) * S.SS, 1040 * S.SS))
    out = os.path.join(B, "광차_다시_사진.png") if with_photos else os.path.join(HERE, "ART1_광차_다시.png")
    img.resize((img.width // S.SS, img.height // S.SS), Image.LANCZOS).save(out); print("saved", out)
sheet(False); sheet(True)
