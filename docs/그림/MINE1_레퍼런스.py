# MINE-1 캐기 연출 조사 한 장 (옆 가지 pick-hands, 09-27): 실제 광부 곡괭이질 영상 · 게임의 "누르고 있기" 작업 · 잰 박자.
# 영상 캡처는 build/refs/mine/ 에서 읽고, 그림도 build/refs/mine/ 에 쓴다(저작권 — 커밋 안 함). 이 코드만 커밋.
#   python docs/그림/MINE1_레퍼런스.py   → build/refs/mine/MINE1_레퍼런스.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, SS, C

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "refs", "mine")
W, H = 2400, 4000
S.new(W, H)
COL = dict(lift=(120, 170, 230), hold=(150, 150, 150), down=(255, 90, 60), stuck=(255, 200, 80), pry=(200, 120, 255), fall=(120, 220, 140), scrape=(90, 200, 200), loop=(80, 80, 80))

def photo(x, y, w, h, path, cap, sz=15):
    S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], fill=(20, 19, 18))
    full = os.path.join(ROOT, path)
    if os.path.exists(full):
        im = Image.open(full).convert("RGB"); k = min(w * SS / im.width, h * SS / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        S.img.paste(im, (int(x * SS + (w * SS - im.width) / 2), int(y * SS + (h * SS - im.height) / 2)))
    yy = y + h + 5
    for i, ln in enumerate(cap.split("\n")):
        for piece in wrap(ln, sz, w):
            text(x + 2, yy, piece, sz, C["text"] if i == 0 else C["sub"]); yy += sz * 1.3

def section(y, title, sub=None):
    S.d.rectangle([20 * SS, y * SS, (W - 20) * SS, (y + 3) * SS], fill=(90, 84, 78))
    text(24, y + 10, title, 30, b=True)
    if sub: text(24 + S.d.textlength(title, font=S.F(30, True)) / SS + 18, y + 20, sub, 19, C["sub"])
    return y + 58

def row(y, items, w, h, gap=18, sz=15):
    for i, (p, c) in enumerate(items): photo(24 + i * (w + gap), y, w, h, p, c, sz)

text(24, 16, "MINE-1 캐기 연출 — 조사 (09-27, 옆 가지 pick-hands)", 36, b=True)
text(24, 64, "사용자(판정 ②): \"까딱까딱은 재미없다 — 좌클릭을 누르고 있을 때 광질(실제 영상 참조)하는 모습을 연출로.\" 영상 10개(손 곡괭이 8)를 1초 10장으로 뽑아 잼(±0.1 s). 캡처는 참고용 · build/refs 만.", 19, C["sub"])

y = section(110, "① 한국 — 태백 탄광유산전시회 영상 · 막장 채탄 영상", "찍은 해 모름 · 1980년대 한국 막장은 주로 콜픽·착암기, 손 곡괭이는 뒷정리·보갱에")
row(y, [("real/r_kr_taebaek_03.jpg", "서서 · 두 손 다 자루 끝 · 흰 면장갑\n머리 위로 크게 — 한 번 1.1~1.4 s"),
        ("real/r_kr_taebaek_04.jpg", "4번 연달아 박힘: 7.2 · 8.6 · 9.9 · 11.0 s\n간격 1.4 → 1.3 → 1.1 s"),
        ("real/r_kr_taebaek_06.jpg", "박힌 채 자루를 아래로 당겨 덩이 떼기\n0.4 s (33.2~33.6 s)"),
        ("real/r_kr_taebaek_07.jpg", "주먹~머리만 한 덩이가 우르르 · 탄가루\n불꽃은 없음 (모든 영상)"),
        ("real/r_kr_taebaek_08.jpg", "날을 바닥에 눕혀 몸 쪽으로 끌어 긁기\n1.0 s (34.1~35.1 s)"),
        ("real/r_kr_makjang_01.jpg", "막장: 무릎·쪼그려, 팔꿈치 아래로 짧게\n한 번 0.6~0.8 s · 큰 덩이는 곡괭이로 쪼갬")], 372, 230)
y += 230 + 80

y = section(y, "② 해외 — 파키스탄 · 이탈리아 · 인도 · 영국", "한쪽 날 곡괭이와 가장 비슷한 것 = 한국① · 파키스탄 가까이 찍은 장면")
row(y, [("real/r_pk_coal_02.jpg", "파키스탄 2025 · 깊이 쪼그려 탄층 밑동\n7번 연속 간격 0.7~0.95 s (소리와 ±0.1 s)"),
        ("real/r_pk_coal_05.jpg", "맞는 순간 주먹만 한 조각·가루가 확\n(8:26.8)"),
        ("real/r_pk_coal_06.jpg", "금 간 틈에 날을 끼워 자루를 수평으로 당김\n(8:40.0~8:40.5)"),
        ("real/r_pk_coal_09.jpg", "판 모양 덩이(눈대중 50×40 cm)가\n1.8 s 동안 기울다 쿵 (8:42.4)"),
        ("real/r_it_arsa_04.jpg", "이탈리아 1940 · 찍고-당기기 0.6 s\n한 아름 덩이+먼지가 0.6 s 쏟아짐"),
        ("real/r_in_jharia_04.jpg", "인도 2022 · 머리 위로 크게, 간격 1.4~1.9 s\n매번 박힌 채 당겨 비틀기 0.8~1.1 s"),
        ("real/r_uk_pathe_kneel_02.jpg", "영국 1920~30년대 · 무릎, 귀 높이까지만\n6번 간격 0.55~0.8 s, 거의 일정")], 322, 200, sz=14)
y += 200 + 80

# ③ 박자 그림
y = section(y, "③ 잰 박자 — 벽에 박힌 순간(▼)과 그 사이 동작", "첫 타 = 0 s 로 맞춤. 옛 필름(영국·미국·이탈리아)은 재생 속도가 실제와 다를 수 있다")
X0, PX = 330, 250          # 0 s 자리, 1 s = PX px
def tl(yy, label, hits, extras=(), note=""):
    text(24, yy + 6, label, 18, b=True)
    S.d.line([(X0 * SS, (yy + 18) * SS), ((X0 + 7.6 * PX) * SS, (yy + 18) * SS)], fill=(70, 66, 62), width=2 * SS)
    for t0, t1, k in extras:
        S.d.rectangle([(X0 + t0 * PX) * SS, (yy + 8) * SS, (X0 + t1 * PX) * SS, (yy + 28) * SS], fill=COL[k])
    for t in hits:
        x = X0 + t * PX
        S.d.polygon([((x - 9) * SS, (yy - 2) * SS), ((x + 9) * SS, (yy - 2) * SS), (x * SS, (yy + 16) * SS)], fill=COL["down"])
    if note: text(X0 + 7.7 * PX - 1900 + 1900, yy + 6, "", 1)
    if note: text(24, yy + 32, note, 15, C["sub"])
for t in range(0, 8):
    text(X0 + t * PX, y, "%d s" % t, 16, C["sub"], anchor="ma")
y += 30
tl(y, "한국① 서서", [0, 1.4, 2.7, 3.8], [(-0.65, -0.3, "lift"), (-0.3, -0.15, "hold"), (0, 0.5, "stuck")], "들기 0.3~0.4 · 꼭대기 멈춤 0.1~0.2 · 내려치기 0.1~0.2 · 박힘 0.5 · 빼기 0.1  (+ 따로 찍힌 떼기 0.4 · 긁기 1.0)"); y += 64
tl(y, "영국 Pathé 무릎", [0, 0.55, 1.25, 1.95, 2.75, 3.45], [], "귀 높이까지만 · 박힘 0.2 · 빼며 들기 0.2~0.3 · 한 번 0.7 s — 짧고 일정"); y += 64
tl(y, "파키스탄 쪼그려", [0, 0.8, 1.65, 2.45, 3.3, 4.1, 4.9], [(5.3, 5.8, "pry"), (5.8, 7.6, "fall")], "7번 0.7~0.95 s → (다른 때) 틈에 끼워 당김 0.5 → 덩이가 1.8 s 기울다 쿵 — 떼기·쿵은 같은 컷이 아님, 이어 붙여 그림"); y += 64
tl(y, "인도 서서 굽힘", [0, 1.4, 2.9, 4.8], [(0.1, 1.0, "pry"), (1.5, 2.4, "pry"), (3.0, 3.9, "pry")], "매번 박힌 채 당겨 비틀기 0.8~1.1 → 들기 0.2~0.3 → 멈춤 → 내려치기 · 한 번 1.4~1.9 s"); y += 64
# 조사자의 5~8 s 초안
text(24, y + 6, "초안 (영상 박자로 짠 것)", 18, C["rew"], b=True)
seq = [(0, 0.35, "lift"), (0.35, 0.5, "hold"), (0.5, 0.65, "down"), (0.65, 1.15, "stuck"), (1.15, 1.75, "lift"), (1.75, 1.9, "down"), (1.9, 2.4, "stuck"),
       (2.4, 2.95, "lift"), (2.95, 3.1, "down"), (3.1, 4.0, "pry"), (4.0, 4.6, "fall"), (4.6, 5.6, "scrape"), (5.6, 7.6, "loop")]
for t0, t1, k in seq:
    S.d.rectangle([(X0 + t0 * PX) * SS, (y + 4) * SS, (X0 + t1 * PX) * SS, (y + 32) * SS], fill=COL[k])
for t in (0.65, 1.9, 3.1):
    text(X0 + t * PX, y + 36, "콱", 16, COL["down"], b=True, anchor="ma")
text(X0 + 6.6 * PX, y + 10, "계속 누르면 처음부터", 15, C["text"], anchor="ma")
text(24, y + 60, "콱 셋(한국① 박자) → 박힌 채 당겨 비틀기(인도·한국①·파키스탄) → 덩이 떨어짐·가루(한국①·이탈리아) → 날 눕혀 긁기(한국①). 치는 횟수·반복 방식·덩이 크기는 [제안] — 제안서에서 정한다.", 15, C["sub"])
y += 92
lx = 24
for k, name in (("lift", "들기"), ("hold", "꼭대기 멈춤"), ("down", "내려치기 ▼"), ("stuck", "박힌 채 버팀"), ("pry", "당겨 비틀기"), ("fall", "덩이 떨어짐"), ("scrape", "긁기"), ("loop", "반복")):
    S.d.rectangle([lx * SS, y * SS, (lx + 26) * SS, (y + 18) * SS], fill=COL[k]); text(lx + 32, y, name, 16); lx += 60 + S.d.textlength(name, font=S.F(16)) / SS
y += 50

# 같은 것
bx, bw = 24, W - 48
common = [("나라가 달라도 같은 것 (영상)", C["rew"], [
    "천천히 들고 확 내려친다 — 내려치기 0.1~0.2 s 로 가장 짧고, 들기는 그 2~3배(0.2~0.4 s).",
    "박히면 바로 안 뺀다 — 0.3~1.1 s 박힌 채 당기거나 비튼다(한국①·이탈리아·인도·파키스탄·미국). 이것이 '콱'과 '콱' 사이의 쉼.",
    "덩이는 여러 번 친 뒤 한꺼번에 — 큰 덩이는 0.3~1.8 s 기울다 넘어진다. 튀는 것은 탄가루와 주먹만 한 조각, 불꽃은 없다.",
    "뒷손은 늘 자루 끝. 치고 나면 날을 눕혀 몸 쪽으로 긁어낸다. 서 있을 때만 머리 위로 크게 — 무릎·쪼그려는 귀 높이, 박자 0.6~0.8 s."]),
    ("게임의 '누르고 있기'에서 (조사 — 10게임)", (120, 200, 255), [
    "안 지루한 것: 박자를 섞는다(Hell Let Loose 세게 셋 + 톡톡 · Arma 휘두르고 0.5 s 멈춤) · 막대보다 대상이 바뀐다(Minecraft 금 · Squad 뼈대 3단계) · 마지막에 큰 한 방.",
    "공포 게임은 누르는 동안에도 판단이 있다 — Amnesia '누르면 충전되지만 소리를 너무 크게 내지 마라', Dead by Daylight 스킬 체크를 놓치면 큰 소리 + 괴물 알림.",
    "지루한 것: The Long Dark 10 s 정해진 장면(손은 2 s 만, 카메라 흔들림 — 멀미 불평) · RDR2 는 1인칭을 버리고 3인칭 장면 20 s.",
    "떼면: Squad · Hell Let Loose · DbD 는 진행이 남는다(우리 수리 E 와 같음), Minecraft 는 0 으로."])]
for title, col, lines in common:
    text(bx, y, title, 22, col, b=True); y += 34
    for ln in lines:
        for piece in wrap("· " + ln, 18, bw):
            text(bx + 4, y, piece, 18); y += 25
    y += 12

y = section(y + 10, "④ 게임 — 1인칭 '누르고 있기' 작업", "캡처 27장 중 8")
row(y, [("games/h_hll_01.jpg", "Hell Let Loose 망치 짓기\n세게 3번(0.6 s) → 톡톡 1.1 s, 묶음 2.9 s"),
        ("games/h_squad_02.jpg", "Squad 삽 · 1.43 s 아주 일정\n흙덩이 + 뼈대 3단계로 버팀"),
        ("games/h_arma_02.jpg", "Arma Reforger 삽 · 두 팔 크게\n한 번 1.7 s, 박혀 0.5 s 멈춤"),
        ("games/h_minecraft_02.jpg", "Minecraft · 진행 = 블록의 금\n떼면 0 으로 (우리와 안 맞음)"),
        ("games/h_dbd_02.jpg", "Dead by Daylight 수리 스킬 체크\n놓치면 폭발·괴물 알림·10 % 뒤로"),
        ("games/h_amnesia_01.jpg", "Amnesia: The Bunker 손전등 충전\n'소리를 너무 크게 내지 마라'"),
        ("games/h_longdark_02.jpg", "The Long Dark 10 s 정해진 장면\n지루함·멀미 불평 (피할 예)"),
        ("games/h_subnautica_03.jpg", "Subnautica 레이저 절단\n마지막에 달아오른 고리 → 열림")], 280, 158, gap=14, sz=14)
y += 158 + 70
S.img = S.img.crop((0, 0, W * SS, y * SS)).resize((W, y), Image.LANCZOS)
out = os.path.join(ROOT, "MINE1_레퍼런스.png"); S.img.save(out); print(out)
