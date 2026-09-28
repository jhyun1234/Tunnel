# 3D-P 플레이어 모델 조사 한 장 그림 (09-29). 1980년대 한국 광부 차림 + 해외 비교.
# 사진은 build/refs/player/ 에서 읽고, 그림도 거기에 쓴다 — 박물관·기록원 사진이 들어가서
# 공개 저장소에 못 올린다(CLAUDE.md). 이 코드만 커밋한다. 근거 표 = docs/기획서/조사/13_광부_차림.md
#   python docs/그림/3DP_레퍼런스.py            → build/refs/player/3DP_레퍼런스.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, SS, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "refs", "player")
OUT = os.path.join(ROOT, "3DP_레퍼런스.png")
W, H = 2400, 3400
S.new(W, H)
HL = (255, 154, 60)

def photo(x, y, w, h, path, cap, sz=16):
    """사진을 w×h 칸에 맞춰 넣고 아래에 설명(여러 줄, 첫 줄 밝게)."""
    S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], fill=(28, 26, 25))
    full = os.path.join(ROOT, path)
    if os.path.exists(full):
        im = Image.open(full).convert("RGB"); k = min(w * SS / im.width, h * SS / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        S.img.paste(im, (int((x + (w * SS - im.width) / SS / 2) * SS), int((y + (h * SS - im.height) / SS / 2) * SS)))
    else:
        text(x + w / 2, y + h / 2, "(사진 없음)\n" + path, 15, C["sub"], anchor="mm")
    yy = y + h + 6
    for ln in cap.split("\n"):
        for piece in wrap(ln, sz, w):
            text(x + 2, yy, piece, sz, C["text"] if yy == y + h + 6 else C["sub"]); yy += sz * 1.3

def section(y, title, sub=None):
    S.d.rectangle([20 * SS, y * SS, (W - 20) * SS, (y + 3) * SS], fill=(90, 84, 78))
    text(24, y + 10, title, 30, b=True)
    if sub: text(24 + S.d.textlength(title, font=S.F(30, True)) / SS + 18, y + 20, sub, 19, C["sub"])
    return y + 58

def row(y, items, h, sz=16, gap=20):
    w = (W - 48 - gap * (len(items) - 1)) / len(items)
    for i, (p_, c_) in enumerate(items):
        photo(24 + i * (w + gap), y, w, h, p_, c_, sz)
    return y + h + 110

text(24, 16, "3D-P 플레이어 모델 — 1980년대 한국 광부 차림 조사 (09-29)", 36, b=True)
text(24, 64, "사진 = 국가기록원 · 1981 문화영화 '갱도의 광부들' · e뮤지엄(보령·문경 석탄박물관) · 해외 박물관(참고용, build/refs 만). 치수는 박물관 기록.", 19, C["sub"])

y = section(110, "① 한국 — 사람이 입은 모습", "1976~1992 · 1988 에 가장 가까운 것은 1992 장성")
y = row(y, [("kr/k28_archives_gyeongdong_black_helmets_boots.jpg", "경동탄광(연도 모름, 국가기록원)\n검은 안전모 · 짙은 윗도리+바지 따로\n검은 목 긴 고무장화, 바지를 장화 속에"),
            ("kr/k19_ehistory_1981_helmet_lamp_chest_number.jpg", "1981 문화영화(장성으로 보임)\n노란 안전모, 챙이 빙 둘림 · 앞에 둥근 램프\n짙은 윗도리 · 흰 내의 깃 · 가슴에 흰 번호표"),
            ("kr/k21_ehistory_1981_cord_down_back.jpg", "1981 뒷모습\n램프 줄 = 안전모 뒤 → 등 가운데 → 허리 뒤\n(가슴 앞으로 내린 사람도 있음)"),
            ("kr/k25_archives_1992_jangseong_belt_red_battery.jpg", "1992-02 장성(국가기록원)\n노란 안전모 · 청회색 윗도리+바지 · 흰 면장갑\n초록 탄띠에 빨간 배터리(허리 옆~뒤)"),
            ("kr/k26_ehistory_1992_jangseong_boots_green_box.jpg", "1992-02 장성 막장\n허리 뒤 초록 배터리 · 흰 면장갑\n검은 고무장화 정강이 중간, 바지는 속에")], 300)

y = section(y, "② 한국 — 박물관 유물 (치수 = 기록)", "대부분 '광복 이후'로만 적혀 있어 연도는 모름")
y = row(y, [("kr/k07_emuseum_boryeong_helmet_yellow_bracket.jpg", "안전모(보령) 지름 20 · 높이 16 cm\n합성수지 · 가운데 골 · 앞 램프 받침(나사 4)\n다른 것 28 × 22~23.5 × 12.5~15 cm"),
            ("kr/k06_emuseum_boryeong_helmet_black_bracket.jpg", "검은 안전모(보령)\n경동은 1984 전까지 검정\n1987 파업 뒤 석탄공사는 모두 노랑"),
            ("kr/k04_emuseum_boryeong_caplamp_red_battery.jpg", "캡램프(보령) 배터리 13 × 5 × 19 cm\n빨간 상자 · 알루미늄 뚜껑 · 뒤에 띠 고리 2\n램프 머리 지름 약 6~7 cm(사진에서 잼)"),
            ("kr/k11_emuseum_boryeong_rubber_gloves.jpg", "고무장갑(보령) 길이 22 · 너비 14 cm\n적갈색 · 손목을 넘는 넓은 목\n글 기록: '근로장갑' 손목만 면, 나머지 고무"),
            ("kr/k10_emuseum_boryeong_rubber_boots_34cm.jpg", "장화(보령) 길이 27 · 높이 34 cm\n검은 고무 · 앞코 두툼 · 회색 밑창\n지급품엔 쇠코, 무거워 따로 사 신기도"),
            ("kr/k12_emuseum_mungyeong_belt_eyelets.jpg", "요대(문경) 81 × 6 cm\n군용식 띠 · 쇠 구멍\n배터리 · 수통을 여기에 검")], 250, sz=15)

y = section(y, "③ 해외 — 1974~1981 (비교)", "영국 NCB 1981 지급품 한 벌 · 미국 1974 · 서독 1974~75 · 일본 전후")
y = row(y, [("world/w07_usa_1974_miner_fullbody.jpg", "미국 1974 (퍼블릭 도메인)\n앞 챙 안전모 · 한 벌 작업복\n넓은 가죽 띠 + 놋쇠판"),
            ("world/w16_wgermany_1974_miner_underground.jpg", "서독 1974 갱 안 (CC BY-SA)\n빙 두른 챙 안전모 + 큰 램프\n(1975 사진은 흰 면 윗도리+바지)"),
            ("world/w01_uk_ncb1981_boilersuit.jpg", "영국 1981 NCB\n주황 한 벌 작업복\n(한국엔 한 벌 옷 기록 없음)"),
            ("world/w02_uk_ncb1981_helmet.jpg", "영국 1981 흰 안전모\n빙 두른 챙 · 뒤에 줄 걸이 쇠판\n125 × 216 × 275 mm"),
            ("world/w03_uk_ncb1981_caplamp_battery.jpg", "영국 1981 캡램프\n머리 70 × 75 × 73 mm\n배터리 215 × 140 × 67 mm · 줄 약 1.3 m"),
            ("world/w10_japan_helmet_caplamp_battery.jpg", "일본(전후) 금속 안전모+램프\n배터리 15 × 17 × 5 cm · 2~3.4 kg\n허리띠에 꿰어 참"),
            ("world/w13_japan_safety_boots.jpg", "일본 1965~ 가죽 안전화\n목이 종아리 중간 · 쇠코\n(한국은 고무장화)"),
            ("world/w04_uk_ncb1981_selfrescuer.jpg", "영국 1981 자기구명기 14 × 9 × 7 cm\n허리띠에 참 — 한국은 1989 부터\n'개인장비'(1988 엔 기록 없음)")], 250, sz=14, gap=16)

# 공통점 상자
bx, bw = 24, W - 48
S.d.rounded_rectangle([bx * SS, y * SS, (bx + bw) * SS, (y + 300) * SS], radius=10 * SS, fill=(55, 51, 48))
cols = [("나라가 달라도 같은 것", C["rew"], [
            "빙 두른 챙 안전모(미국만 앞 챙) · 앞 쇠 받침에 둥근 램프(지름 약 6~7 cm)",
            "램프 줄 → 허리 배터리. 배터리 = 벽돌 모양 13~21 × 4~8 × 15~21 cm, 2~3.4 kg, 뒤 고리로 띠에",
            "넓은 띠 하나에 배터리 · 물통(한국 = 군용 탄띠에 수통)",
            "목 긴 장화 · 바지를 장화 속에 · 앞코 쇠(지급품)",
            "목수건(한국 흰 광목 · 서독) · 번호로 사람을 셈(한국 가슴 번호표 · 입갱 표찰)"]),
        ("한국 안에서도 다른 것", HL, [
            "옷 색: 글 = 검정(광부) / 1992 사진 = 청회색 / 유물 = 파랑 · 남색",
            "안전모 색: 석탄공사 노랑(1987 뒤 모두) / 경동 검정(1984 전) / 사진 갈색도",
            "램프 줄: 등 뒤로 / 가슴 앞으로 — 둘 다 있음",
            "장갑: 고무 근로장갑(글 · 유물) / 흰 면장갑(1992 사진)",
            "야광띠: 글엔 '모두' / 사진 · 유물엔 안 보임 · 후산부는 안전모에 안 붙임(경동)"]),
        ("1988 한국에 없던 것 · 못 찾음", C["sub"], [
            "자기구명기 몸에 차기(1989 규칙부터) · 보안경(1990년대 초) · 손목시계(안 차고 들어감)",
            "방진마스크는 목에 걸고만 다님(1980년대 후반에야 제대로 씀)",
            "못 찾음: 배터리 · 램프 무게(한국), 줄 길이, 램프 회사, 안전모 턱끈, 1988 딱 그해 사진"])]
cw = (bw - 60) / 3
for i, (title, col, lines) in enumerate(cols):
    x0 = bx + 20 + i * (cw + 10); yy = y + 16
    text(x0, yy, title, 23, col, b=True); yy += 40
    for ln in lines:
        for piece in wrap("· " + ln, 18, cw - 20):
            text(x0, yy, piece, 18); yy += 25
        yy += 6
y_end = y + 300 + 30
S.img = S.img.crop((0, 0, W * SS, y_end * SS)).resize((W, y_end), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
