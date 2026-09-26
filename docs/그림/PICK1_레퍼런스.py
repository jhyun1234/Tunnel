# PICK-1 · 3D-P 조사 한 장 그림 (옆 가지 pick-hands, 09-27).
# 사진은 build/refs/pick/ 에서 읽고, 그림도 build/refs/pick/ 에 쓴다 — 박물관 사진·게임 화면이 들어가서
# 공개 저장소에 못 올린다(CLAUDE.md). 이 코드만 커밋한다.
#   python docs/그림/PICK1_레퍼런스.py            → build/refs/pick/PICK1_레퍼런스.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, SS, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "refs", "pick")
OUT = os.path.join(ROOT, "PICK1_레퍼런스.png")
W, H = 2400, 3560
S.new(W, H)
WOOD, IRON, NOW = (150, 110, 70), (150, 152, 158), (255, 154, 60)

def photo(x, y, w, h, path, cap, sz=16, hl=None):
    """사진을 w×h 칸에 맞춰 넣고 아래에 설명(여러 줄)."""
    S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], fill=(28, 26, 25))
    full = os.path.join(ROOT, path)
    if os.path.exists(full):
        im = Image.open(full).convert("RGB"); k = min(w * SS / im.width, h * SS / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)     # 작은 화면 캡처는 키운다
        S.img.paste(im, (int((x + (w * SS - im.width) / SS / 2) * SS), int((y + (h * SS - im.height) / SS / 2) * SS)))
    else:
        text(x + w / 2, y + h / 2, "(사진 없음)\n" + path, 15, C["sub"], anchor="mm")
    if hl: S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], outline=hl, width=4 * SS)
    yy = y + h + 6
    for ln in cap.split("\n"):
        for piece in wrap(ln, sz, w):
            text(x + 2, yy, piece, sz, C["text"] if yy == y + h + 6 else C["sub"]); yy += sz * 1.3

def section(y, title, sub=None):
    S.d.rectangle([20 * SS, y * SS, (W - 20) * SS, (y + 3) * SS], fill=(90, 84, 78))
    text(24, y + 10, title, 30, b=True)
    if sub: text(24 + S.d.textlength(title, font=S.F(30, True)) / SS + 18, y + 20, sub, 19, C["sub"])
    return y + 58

# ── 곡괭이 옆모습 (같은 비율 1 cm = K px) ──
K = 3.6
def pick(cx, cy, handle, head, kind, col=IRON, label="", sub="", hl=False):
    """머리 눈(자루 끼우는 곳)이 (cx, cy), 자루는 오른쪽으로. head = 끝에서 끝(cm). 이름은 자루 끝 오른쪽."""
    t = 4.0 * K                                   # 자루 굵기 약 4 cm (보령 사진 3.3~4.4)
    x2 = cx + handle * K
    S.d.rounded_rectangle([cx * SS, (cy - t / 2) * SS, x2 * SS, (cy + t / 2) * SS], radius=int(t / 2 * SS), fill=WOOD)
    L, wb = head * K, 2.6 * K                     # 날 밑동 반폭 약 2.6 cm (너비 5.5~6 cm)
    def arm(length, s, bend):                     # s = -1 위 / +1 아래, 끝이 자루 쪽(+x)으로 bend 만큼 휨
        n = 12; left, right = [], []
        for i in range(n + 1):
            u = i / n; w = wb * (1 - u) ** 0.8 + 0.4 * K * (1 - u)
            xc = cx + bend * u * u; yc = cy + s * length * u
            left.append(((xc - w) * SS, yc * SS)); right.append(((xc + w) * SS, yc * SS))
        S.d.polygon(left + right[::-1], fill=col)
    if kind == "one":        # 한쪽만 뾰족 + 위에 짧은 네모 꼭지(보령·일본·독일)
        up = 0.16 * L
        S.d.rectangle([(cx - wb) * SS, (cy - up) * SS, (cx + wb) * SS, cy * SS], fill=col)
        arm(0.84 * L, 1, 2.5 * K)
    else:                    # 양쪽 뾰족(영국·웨일스·지금 게임) — 끝이 자루 쪽으로 휜다
        for s_ in (-1, 1): arm(L / 2, s_, (4.5 if kind == "now" else 1.5) * K)
    r = 3.4 * K
    S.d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=col)     # 눈
    if hl: S.d.rectangle([(cx - 40) * SS, (cy - 105) * SS, (cx + 640) * SS, (cy + 105) * SS], outline=NOW, width=3 * SS)
    text(x2 + 16, cy - 30, label, 20, NOW if hl else C["text"], b=True)
    yy = cy - 2
    for ln in sub.split(chr(10)):
        text(x2 + 16, yy, ln, 16, C["sub"]); yy += 21

# ───────────────────────── 그리기 ─────────────────────────
text(24, 16, "PICK-1 곡괭이 · 3D-P 1인칭 손·팔 — 조사 (09-27, 옆 가지 pick-hands)", 36, b=True)
text(24, 64, "사진 = 박물관·국가기록원·게임 화면(참고용, build/refs 만). 치수는 박물관 기록. '사진에서 잼' · '검색 요약만' 은 따로 적었다.", 19, C["sub"])

# 1. 한국
y = section(110, "① 한국 탄광 곡괭이", "보령석탄박물관(e뮤지엄) · 지역N문화 — 1980년대 탄은 주로 발파·착암기·콜픽, 손 곡괭이는 선산부·보갱부 개인 도구")
cw, ch = 372, 250
row = [("kr/kr_01_boryeong381.jpg", "보령 곡괭이 381\n자루 64 · 머리 34 · 너비 6 cm · 광복 이후\n한쪽만 뾰족 + 위 짧은 꼭지(사진)"),
       ("kr/kr_02_boryeong383.jpg", "보령 곡괭이 383\n자루 69 · 머리 29 · 너비 5.5 cm\n검게 갈라진 나무 자루, 끝이 뭉개짐"),
       ("kr/kr_03_boryeong386.jpg", "보령 386 (쇠머리만)\n길이 32 · 너비 7 · 높이 6 cm\n둥근 쇠 통에 자루 끝을 끼움(안 뚫고 나감)"),
       ("kr/kr_06_bongsan_seated_pick.jpg", "일제강점기 황해 봉산 탄광\n앉아서 양쪽 뾰족 짧은 곡괭이\n(한국에서 두 모양 다 쓰였을 수 있음)"),
       ("kr/arm_01_coalpick_gloves.jpg", "콜픽(공기로 쪼는 곡괭이) — 두 손\n1960년대 석탄공사, 1970년대 개인 탄광\n연도 모름 · 광물자원공사 사진"),
       ("kr/kr_08_kneeling_face.jpg", "막장에서 무릎 꿇고 일함\n허리 뒤 배터리 · 공기 호스\n노보리 막장은 '기어서'(기록)")]
for i, (p_, c_) in enumerate(row):
    photo(24 + i * (cw + 20), y, cw, ch, p_, c_)
y += ch + 100

# 2. 해외
y = section(y, "② 해외 탄광 곡괭이", "영국·웨일스·미국·일본·독일·폴란드 박물관 기록 — 사진 19장 중 7")
cw2 = 322
row = [("world/w_01_japan_mizumaki_tsuruhashi.jpg", "일본 쓰루하시 4점(전후)\n4 × 31 × 91 cm · 한쪽 뾰족\n날끝만 갈아 끼움"),
       ("world/w_01_japan_ube_tsuruhashi.jpg", "일본 우베 석탄기념관\n보령 것과 같은 모양\n(한쪽 날이 자루 끝에)"),
       ("world/w_01_germany_keilhaue_1950-90.jpg", "독일 Keilhaue 1950~90\n자루 80 · 머리 34.5 cm · 머리 1.1 kg\n한쪽 뾰족 + 뒤 두드리는 면"),
       ("world/w_01_uk_colliers_pick_c1960.jpg", "영국 광부 곡괭이 1960년경\n전체 81 · 머리 28.7 cm\n양쪽 뾰족, 쇠 덮개"),
       ("world/w_01_wales_bottom_mandrel.jpg", "웨일스 만드렐(바닥용)\n전체 64~81 · 머리 34~40 cm\n1.65~2.0 kg · 날을 쐐기로 갈아 끼움"),
       ("world/w_01_uk_midlands_hewer_1944.jpg", "영국 1944 · 높이 1.2 m 탄층\n무릎 꿇고 두 손으로 자루 끝 쥠\n(쥐는 법 글 기록은 없음 — 사진만)"),
       ("world/w_01_us_wv_miner_undercut_1908.jpg", "미국 1908 · 쪼그려 짧은 곡괭이\n탄층 밑파기(holing)\n누워 캐기 사진도 있음(1905)")]
for i, (p_, c_) in enumerate(row):
    photo(24 + i * (cw2 + 20), y, cw2, 230, p_, c_, sz=15)
y += 230 + 96

# 3. 같은 비율 옆모습
y = section(y, "③ 같은 비율로 놓은 옆모습", f"1 cm = {K} px · 자루 굵기 4 cm 어림 · 머리 모양은 사진 따라 단순화(우리 그림)")
items = [(88, 46, "now", "지금 게임", "pick.gltf 자루 88 · 머리 46\n화면에선 0.75배 · 손 없음"),
         (64, 34, "one", "보령 381", "자루 64 · 머리 34 cm"),
         (69, 29, "one", "보령 383", "자루 69 · 머리 29 cm"),
         (87, 31, "one", "일본 쓰루하시", "전체 91 · 머리 31 cm"),
         (80, 34.5, "one", "독일 Keilhaue", "자루 80 · 머리 34.5\n머리 1.1 kg"),
         (78, 28.7, "two", "영국 1960년경", "전체 81 · 머리 28.7"),
         (75, 40, "two", "웨일스 만드렐", "전체 64~81 · 머리 34~40\n1.65~2.0 kg"),
         (79, 36, "two", "미국 coal pick 1930s", "79 × 36 cm\n(검색 요약만)")]
RH = 205
for i, (hd, hh, k_, lb, sb) in enumerate(items):
    col_, row_ = i // 4, i % 4
    pick(80 + col_ * 690, y + 105 + row_ * RH, hd, hh, k_, NOW if k_ == "now" else IRON, lb, sb, hl=(k_ == "now"))
S.d.rectangle([80 * SS, (y + 4 * RH + 10) * SS, (80 + 10 * K) * SS, (y + 4 * RH + 16) * SS], fill=C["text"])
text(80 + 10 * K + 8, y + 4 * RH + 2, "10 cm", 16, C["sub"])
# 공통점 상자
bx, by, bw = 1420, y + 10, 955
S.d.rounded_rectangle([bx * SS, by * SS, (bx + bw) * SS, (by + 600) * SS], radius=10 * SS, fill=(55, 51, 48))
text(bx + 18, by + 14, "나라가 달라도 같은 것", 24, C["rew"], b=True)
common = ["자루가 짧다: 64~91 cm — '좁은 곳에서 써서'(스코틀랜드 박물관 설명). 보령 64·69 cm.",
          "머리 끝에서 끝 28~40 cm, 팔이 가늘고 뾰족. 완성품 1.25~2.0 kg (한국 무게 기록 없음).",
          "날만 갈아 끼우는 방식이 영국·독일·폴란드·일본에 따로 있었다 — 날이 무뎌 대장간에 날마다.",
          "캐는 자세 = 무릎 꿇고 · 쪼그려 · 누워서. 사진 속 손은 두 손, 자루 끝 쪽.",
          "나무 자루는 거무스름·갈라짐(보령). 나무 종류 기록은 한국엔 없음(미국 카탈로그만 히코리).",
          "",
          "나라마다 다른 것",
          "한쪽만 뾰족 + 짧은 꼭지·두드리는 면 = 한국(보령) · 일본 · 독일.",
          "양쪽 뾰족 = 영국 · 웨일스 · 폴란드 · 한국 일제강점기 사진 1장.",
          "보령·일본은 둥근 쇠 통에 자루 끝을 끼움 / 영국은 머리가 자루를 뚫고 나감.",
          "",
          "지금 게임 곡괭이와 다른 점",
          "머리 46 cm 양쪽 크게 휜 날 — 자료 가운데 가장 큰 것(40)보다 크고, 한국 박물관 것은 한쪽 날."]
yy = by + 52
for ln in common:
    if ln in ("나라마다 다른 것", "지금 게임 곡괭이와 다른 점"):
        text(bx + 18, yy + 4, ln, 21, C["rew"] if ln[0] == "나" else NOW, b=True); yy += 34; continue
    if not ln: yy += 8; continue
    for piece in wrap("· " + ln, 18, bw - 40):
        text(bx + 22, yy, piece, 18); yy += 25
y = max(y + 4 * RH + 40, by + 620) + 10

# 4. 광부 팔·손
y = section(y, "④ 1980년대 한국 광부의 팔·손", "지역N문화 탄광 이야기 3619·3683·3649 · 삼척 향토문화 — 사진은 연도 적힌 것만 연도")
cw3 = 430
row = [("kr/arm_05_drill_1976.jpg", "1976 삼척탄광(국가기록원)\n주황 긴 목 고무장갑 · 검은 작업복\n안에 흰 내의 깃"),
       ("kr/arm_02_drill_orangegloves.jpg", "착암기 두 손 · 주황·갈색 고무장갑\n아래팔만 남색 = 토시로 보임(확실치 않음)\n빨간 배터리 허리 뒤, 줄은 등으로"),
       ("kr/arm_04_whitegloves_1992.jpg", "1992 (국가기록원) — 1988 에 가장 가까운 연도\n흰 면장갑 · 청회색 긴소매"),
       ("kr/arm_03_shovel_lampcord.jpg", "삽질 · 회색 긴소매\n안전등 줄 = 안전모 뒤 → 등 → 허리 배터리\n팔 쪽으로는 안 지나감")]
for i, (p_, c_) in enumerate(row):
    photo(24 + i * (cw3 + 18), y, cw3, 270, p_, c_)
bx = 24 + 4 * (cw3 + 18)
facts = ["장갑 = '근로장갑': 손목만 면, 나머지 고무. 끼고 일함(수기: 장갑 속까지 땀).",
         "작업복 = 검정(1970년대 후반~, 광부), 청색은 소장·갱장. 야광띠·사물함 번호.",
         "사계절 내복 + 두꺼운 작업복 — 탄가루 막으려고. 손토시·발토시는 '기본'.",
         "그러나 1980년대에도 더운 막장에선 알몸으로 캔 사람이 있었다(35°C · 90 %).",
         "손: 동발에 긁히고 돌에 손등이 터짐, 상처에 탄가루가 먹줄처럼 뱀.",
         "못 찾음: 손목시계 · 소매 걷기 · 1988 막장 손 사진."]
yy = y
for ln in facts:
    for piece in wrap("· " + ln, 17, W - bx - 30):
        text(bx, yy, piece, 17); yy += 24
    yy += 4
y += 270 + 110

# 5. 게임
y = section(y, "⑤ 1인칭 게임의 손·팔·도구", "15게임 30장 중 9 (YouTube·참고용) — 오른쪽 아래 = 지금 우리 게임 · 휘두르기 시간은 영상 프레임으로 잼(±)")
cw4, ch4 = 452, 254
games = [("games/g_wardogs_3.jpg", "WARDOGS — 한 손 망치 · 회색 뜨개 작업장갑\nX 를 치면 빨리 지어짐 · 칠 때마다 % 오름"),
         ("games/g_wardogs_1.jpg", "WARDOGS — 손·손목만, 장갑 목이 경계\n짙은 파란 소매 · 곡괭이·채굴 장면은 없음"),
         ("games/g_tarkov_1.jpg", "Escape from Tarkov — 노란 뜨개 장갑\n도구는 오른쪽 아래, 일부가 화면 밖"),
         ("games/g_7dtd_2.jpg", "7 Days to Die — 한 손 곡괭이, 한 번 1.05 s\n칠 때마다 흙먼지 · 마지막에 크게 무너짐"),
         ("games/g_rust_1.jpg", "Rust — 칠 때 두 손 머리 위, 팔꿈치까지\n들어 내려치기 0.3~0.4 s · 되돌리기 약 1 s"),
         ("games/g_greenhell_1.jpg", "Green Hell — 맨팔 · 손목에 시계\n도끼가 0.4~0.5 s 박혀 머묾 = 무게"),
         ("games/g_amnesia_1.jpg", "Amnesia: The Bunker — 흙·피 묻은 손\n손목 붕대 · 군복 소맷부리"),
         ("games/g_drg_2.jpg", "Deep Rock Galactic (만화풍 비교)\n0.67 s · 0.1 s 에 내려옴 · 큰 돌조각 = 속도로 손맛"),
         ("games/g_sotf_1.jpg", "Sons of the Forest — 한 번 0.7 s\n칠수록 V자 홈이 깊어짐")]
for i, (p_, c_) in enumerate(games):
    photo(24 + (i % 5) * (cw4 + 20), y + (i // 5) * (ch4 + 80), cw4, ch4, p_, c_, sz=15)
photo(24 + 4 * (cw4 + 20), y + ch4 + 80, cw4, ch4, "now_pick_in_tunnel.png", "지금 우리 게임\n손·팔 없음 · 곡괭이만 오른쪽에 뜸", sz=15, hl=NOW)
y += 2 * ch4 + 80
y_end = y + 90
S.img = S.img.crop((0, 0, W * SS, y_end * SS)).resize((W, y_end), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
