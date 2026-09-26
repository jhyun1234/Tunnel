# 공포 게임 12개의 맵 짜임을 같은 방식으로 다시 그린 한 장 (조사 08, 56차 09-26).
# 사실은 docs/기획서/조사/08_공포게임_맵_짜임.md 에서만. 자리·방향은 짜임을 보이려고 단순하게 그린 것.
# 실행: python "docs/그림/MAP3_레퍼런스_12.py"  →  같은 폴더에 MAP3_레퍼런스_12.png
import math, random, os
from PIL import Image, ImageDraw, ImageFont

SS = 2
W, H = 3000, 2680
BG = (43, 40, 38)
C = dict(hub=(126, 208, 126), room=(216, 207, 184), tun=(167, 159, 143), fix=(255, 154, 60),
         rew=(255, 214, 70), exit=(255, 158, 128), mon=(222, 72, 60), door=(255, 122, 26),
         crawl=(80, 210, 200), text=(235, 230, 220), sub=(165, 160, 150), hide=(90, 160, 255),
         dark=(62, 57, 53), ink=(40, 36, 34))
img = Image.new("RGB", (W * SS, H * SS), BG)
d = ImageDraw.Draw(img)
_fc = {}
def F(sz, b=False):
    k = (sz, b)
    if k not in _fc:
        _fc[k] = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if b else "C:/Windows/Fonts/malgun.ttf", int(sz * SS))
    return _fc[k]

def text(x, y, t, sz=18, col=C["text"], b=False, anchor="la"):
    """x, y 는 1배 좌표. 여러 줄이면 줄마다 같은 anchor 로."""
    lines = t.split("\n"); lh = sz * 1.3
    y0 = y - (len(lines) - 1) * lh / 2 if anchor[1] == "m" else y
    for i, ln in enumerate(lines):
        d.text((x * SS, (y0 + i * lh) * SS), ln, font=F(sz, b), fill=col, anchor=anchor)

def wrap(t, sz, maxw, b=False):
    out, cur = [], ""
    for w in t.split(" "):
        nxt = (cur + " " + w).strip()
        if d.textlength(nxt, font=F(sz, b)) / SS > maxw and cur:
            out.append(cur); cur = w
        else:
            cur = nxt
    return out + [cur]

class P:
    """판 하나. 그림 칸은 720 × 420 (1배 px), 아래에 설명 줄."""
    DW, DH = 720, 420
    def __init__(s, ox, oy, title, lines):
        s.x0, s.y0 = ox + 10, oy + 52
        text(ox + 12, oy + 8, title, 25, b=True)
        yy = s.y0 + s.DH + 14
        for ln in lines:
            for piece in wrap(ln, 19, 715):
                text(ox + 12, yy, piece, 19, C["sub"]); yy += 26
    def T(s, x, y): return ((s.x0 + x) * SS, (s.y0 + y) * SS)
    def line(s, pts, w, col, dash=False, dl=10, gap=7):
        P_ = [s.T(*p) for p in pts]
        if dash:
            for (ax, ay), (bx, by) in zip(P_, P_[1:]):
                L = math.hypot(bx - ax, by - ay); t = 0
                while t < L:
                    t2 = min(t + dl * SS, L)
                    d.line([(ax + (bx - ax) * t / L, ay + (by - ay) * t / L), (ax + (bx - ax) * t2 / L, ay + (by - ay) * t2 / L)], fill=col, width=int(w * SS))
                    t = t2 + gap * SS
            return
        d.line(P_, fill=col, width=int(w * SS), joint="curve")
        r = w * SS / 2
        for (px, py) in P_: d.ellipse([px - r, py - r, px + r, py + r], fill=col)
    def box(s, x, y, w, h, col, label=None, sz=16, tc=None, outline=None, ow=3):
        d.rounded_rectangle([*s.T(x, y), *s.T(x + w, y + h)], radius=6 * SS, fill=col, outline=outline, width=ow * SS if outline else 0)
        if label: text(s.x0 + x + w / 2, s.y0 + y + h / 2, label, sz, tc or C["ink"], b=True, anchor="mm")
    def frame(s, x, y, w, h, col, ow=8):
        d.rectangle([*s.T(x, y), *s.T(x + w, y + h)], outline=col, width=ow * SS)
    def blob(s, cx, cy, r, col, seed, label=None, sz=15):
        rnd = random.Random(seed); n = 16
        pts = [s.T(cx + r * (1 + 0.22 * rnd.uniform(-1, 1)) * math.cos(2 * math.pi * i / n) * 1.15,
                   cy + r * (1 + 0.22 * rnd.uniform(-1, 1)) * math.sin(2 * math.pi * i / n) * 0.85) for i in range(n)]
        d.polygon(pts, fill=col)
        if label: s.lab(cx, cy, label, sz, C["ink"], True)
    def dot(s, x, y, r, col, outline=None):
        (px, py) = s.T(x, y); R = r * SS
        d.ellipse([px - R, py - R, px + R, py + R], fill=col, outline=outline, width=2 * SS if outline else 0)
    def ring(s, x, y, rx, ry, col, w=3, dash=True):
        pts = [(x + rx * math.cos(a / 40 * 2 * math.pi), y + ry * math.sin(a / 40 * 2 * math.pi)) for a in range(41)]
        s.line(pts, w, col, dash=dash)
    def star(s, x, y, r=11):
        pts = [s.T(x + (r if i % 2 == 0 else r * 0.42) * math.sin(i * math.pi / 5), y - (r if i % 2 == 0 else r * 0.42) * math.cos(i * math.pi / 5)) for i in range(10)]
        d.polygon(pts, fill=C["rew"], outline=(120, 90, 20))
    def fix(s, x, y, r=12, col=None):
        pts = [s.T(x + (r if i % 2 == 0 else r * 0.72) * math.cos(i * math.pi / 8), y + (r if i % 2 == 0 else r * 0.72) * math.sin(i * math.pi / 8)) for i in range(16)]
        d.polygon(pts, fill=col or C["fix"])
        s.dot(x, y, r * 0.33, C["ink"])
    def exitm(s, x, y, label=None, lpos="below", sz=14):
        s.box(x - 16, y - 10, 32, 20, C["exit"])
        if label:
            dy = 24 if lpos == "below" else -24
            s.lab(x, y + dy, label, sz, C["exit"])
    def bar(s, x, y, vertical=True, col=None, L=26):
        s.line([(x, y - L / 2), (x, y + L / 2)] if vertical else [(x - L / 2, y), (x + L / 2, y)], 8, col or C["door"])
    def lab(s, x, y, t, sz=14, col=None, b=False, anchor="mm"):
        text(s.x0 + x, s.y0 + y, t, sz, col or C["text"], b, anchor)
    def curve(s, a, c, b, n=16):
        return [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0], (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]) for t in (i / n for i in range(n + 1))]
    def wig(s, pts, amp, seed, step=16):
        rnd = random.Random(seed); out = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, by - ay); k = max(1, int(L / step)); nx, ny = -(by - ay) / L, (bx - ax) / L
            for i in range(k):
                t = i / k; o = amp * rnd.uniform(-1, 1) if 0 < i else 0
                out.append((ax + (bx - ax) * t + nx * o, ay + (by - ay) * t + ny * o))
        return out + [pts[-1]]

# ── 머리 ──
text(40, 26, "공포 게임 12개의 맵 짜임 — 같은 방식으로 다시 그림", 44, b=True)
text(40, 92, "MAP3 구조 고민용 (56차 09-26). 사실은 조사 08(docs/기획서/조사/08_공포게임_맵_짜임.md)의 출처에서만 가져왔다.", 21, C["sub"])
text(40, 122, "자리·방향·개수는 짜임을 보이려고 단순하게 그린 것 — 실제 지도와 다를 수 있다. 고칠 곳(톱니)과 괴물 길(빨간 점선)을 먼저 보면 된다.", 21, C["sub"])
# 범례
lg = [("hub", "거점 (안전·밝음)"), ("room", "방 · 넓은 곳"), ("tun", "통로 · 갱도"), ("fix", "고칠 곳 · 켤 곳"),
      ("rew", "보상 (광석·물건·목표)"), ("exit", "출구"), ("mon", "괴물이 다니는 길"), ("mond", "괴물 구멍 · 틈"),
      ("door", "잠긴 문 · 막힌 곳"), ("crawl", "기어가는 틈 · 샛길")]
LP = P.__new__(P); LP.x0, LP.y0 = 1880, 20
for i, (k, t) in enumerate(lg):
    cx, cy = (i % 2) * 540, 16 + (i // 2) * 30
    if k in ("hub", "room"): LP.box(cx, cy - 10, 34, 20, C[k])
    elif k == "tun": LP.line([(cx, cy), (cx + 34, cy)], 8, C["tun"])
    elif k == "fix": LP.fix(cx + 17, cy)
    elif k == "rew": LP.star(cx + 17, cy)
    elif k == "exit": LP.exitm(cx + 17, cy)
    elif k == "mon": LP.line([(cx, cy), (cx + 34, cy)], 4, C["mon"], dash=True, dl=7, gap=5)
    elif k == "mond": LP.dot(cx + 17, cy, 8, C["mon"])
    elif k == "door": LP.bar(cx + 17, cy, vertical=False)
    elif k == "crawl": LP.line([(cx, cy), (cx + 34, cy)], 4, C["crawl"], dash=True, dl=7, gap=5)
    LP.lab(cx + 48, cy, t, 18, anchor="lm")

PW, PH, TOP = 740, 680, 196
def origin(r, c): return 20 + c * PW, TOP + 44 + r * (PH + 44)
for r, t in enumerate(["고르신 네 게임", "흩어진 시설을 고치는 게임", "거점 · 지름길 / 판마다 조립되는 맵"]):
    text(30, TOP + r * (PH + 44) + 6, t, 24, C["fix"], b=True)
    d.line([(30 * SS, (TOP + r * (PH + 44) + 38) * SS), ((W - 30) * SS, (TOP + r * (PH + 44) + 38) * SS)], fill=(80, 74, 70), width=2 * SS)

# ── 1. Amnesia: The Bunker ──
p = P(*origin(0, 0), "Amnesia: The Bunker", [
    "가운데 거점(세이브 + 아래층 발전기) + 날개 다섯 · 날개마다 목표 하나",
    "발전기 연료가 계속 줄어 거점으로 돌아와 채운다 — 숨어 있는 시간도 연료가 탄다",
    "괴물 = 벽 구멍 사이를 기어 다님 · 지도 모양은 고정, 물건 자리만 바뀜"])
p.box(325, 4, 70, 30, C["room"], "시작 방", 13)
p.line([(360, 34), (360, 66)], 8, C["tun"])
p.box(262, 66, 196, 78, C["hub"], "거점\n세이브 · 아래층 발전기", 16)
p.fix(446, 80); p.lab(500, 80, "연료", 14, C["fix"], True)
p.box(70, 80, 120, 48, C["room"], "물자 창고", 14); p.star(178, 90)
p.line([(190, 104), (262, 104)], 8, C["tun"])
p.line([(360, 144), (360, 186)], 10, C["tun"])
p.line([(70, 186), (640, 186)], 12, C["tun"]); p.lab(560, 168, "긴 복도", 14, C["sub"])
p.fix(300, 186, 10); p.lab(300, 212, "잠금 바퀴", 12, C["fix"])
p.exitm(668, 186, "막힌 탈출구", sz=13)
for x, name, st in [(100, "장교 숙소", False), (245, "병사 숙소", True), (385, "감옥", True), (525, "무기고", True)]:
    p.line([(x, 186), (x, 246)], 8, C["tun"])
    p.box(x - 58, 246, 116, 58, C["room"], name, 14)
    if st: p.star(x + 46, 258)
p.line([(100, 304), (100, 340)], 8, C["tun"]); p.box(42, 340, 116, 50, C["room"], "정비실", 14); p.star(146, 352)
p.line(p.wig([(583, 280), (640, 330)], 5, 3), 8, C["tun"]); p.blob(650, 360, 42, C["dark"], 7); p.lab(650, 360, "터널\n(가장 깊음)", 13, C["text"], True); p.star(682, 338)
for (x, y) in [(42, 270), (187, 292), (327, 300), (467, 262), (158, 372)]: p.dot(x, y, 8, C["mon"])
p.line(p.curve((42, 270), (110, 225), (187, 292)), 3, C["mon"], dash=True)
p.line(p.curve((187, 292), (260, 345), (327, 300)), 3, C["mon"], dash=True)
p.line(p.curve((327, 300), (400, 330), (467, 262)), 3, C["mon"], dash=True)
p.lab(255, 368, "벽 구멍 (괴물)", 13, C["mon"])
p.lab(4, 412, "방향·자리는 그림용", 12, C["sub"], anchor="lm")

# ── 2. Lethal Company — Mineshaft ──
p = P(*origin(0, 1), "Lethal Company — Mineshaft 실내", [
    "입구 방 → 작은 승강기 → 아래층 복도(허브) → 파란 불 문 → 동굴 가지",
    "폐품은 깊은 동굴에, 비상구는 허브에만 → \"더 들어갈까, 돌아갈까\"",
    "괴물 = 동굴 벽의 검은 틈에서 나옴 · 판마다 새로 조립 · 고치는 목표는 거의 없음"])
p.exitm(115, 16); p.lab(150, 16, "정문", 13, C["exit"], anchor="lm"); p.lab(40, 16, "바깥", 13, C["sub"])
p.line([(115, 26), (115, 60)], 8, C["tun"])
p.box(30, 60, 170, 86, C["room"], "입구 방\n2층 · 레일 · 광차", 15)
p.line([(115, 146), (115, 246)], 3, C["hub"])
p.box(96, 176, 38, 44, BG, outline=C["hub"], ow=3); p.lab(180, 198, "승강기", 14, C["hub"], True)
p.box(30, 246, 360, 42, C["room"], "아래층 복도 (허브)", 15)
p.exitm(360, 222, "비상구", lpos="above", sz=13)
for x in (70, 200, 330): p.bar(x, 296, vertical=False, col=C["hide"])
p.lab(470, 276, "← 파란 불 문부터 동굴", 13, C["hide"])
caves = [[(70, 300), (50, 350), (70, 404)], [(70, 300), (140, 360), (170, 400)], [(200, 300), (250, 350), (330, 400)],
         [(330, 300), (450, 340), (560, 300), (680, 370)], [(560, 300), (610, 220), (690, 150)], [(450, 340), (470, 400)]]
for i, c in enumerate(caves): p.line(p.wig(c, 7, 11 + i), 9, C["tun"])
for (x, y) in [(70, 404), (170, 400), (330, 400), (680, 370), (690, 150), (470, 400), (610, 222)]: p.star(x, y)
for (x, y) in [(240, 356), (520, 318), (640, 190), (106, 350), (400, 318)]: p.dot(x, y, 8, C["mon"])
p.lab(600, 400, "동굴 가지 (폐품이 몰림)", 14, C["text"])
p.dot(610, 340, 14, (20, 18, 17)); p.lab(640, 340, "구덩이", 12, C["sub"], anchor="lm")

# ── 3. Deep Rock Galactic ──
p = P(*origin(0, 2), "Deep Rock Galactic", [
    "큰 동굴 방 3~6개를 굵기가 다른 터널로 잇는다 = \"진주와 실\"",
    "끝방에 광석이 많다 · 방 모양이 다음 출구로 이끈다 · \"미로처럼 느껴지면 안 된다\"",
    "방 틀은 사람이 손으로, 잇기는 자동 · 부서진 로봇 고치기·드릴 주유 같은 임무도 있음"])
p.line([(80, 120), (250, 95)], 6, C["tun"]); p.lab(150, 138, "좁음", 12, C["sub"])
p.line([(250, 95), (430, 205)], 26, C["tun"]); p.lab(370, 128, "아주 넓음", 12, C["sub"])
p.line(p.wig([(250, 95), (240, 300)], 8, 5), 10, C["tun"])
p.line(p.wig([(240, 300), (430, 205)], 5, 6), 4, C["tun"]); p.lab(345, 280, "비좁음", 12, C["sub"])
p.line([(430, 205), (600, 285)], 15, C["tun"])
p.blob(80, 120, 42, C["room"], 1); p.box(66, 108, 28, 24, C["hub"]); p.lab(80, 164, "착지", 13, C["hub"], True)
p.blob(250, 95, 62, C["room"], 2); p.star(236, 80); p.star(274, 108)
p.blob(240, 300, 52, C["room"], 3); p.star(246, 300)
p.blob(430, 205, 76, C["room"], 4); p.star(410, 190); p.star(452, 222)
p.blob(605, 290, 98, C["room"], 5); p.lab(605, 262, "끝방: 광석 많음", 15, C["ink"], True)
for (x, y) in [(560, 300), (590, 320), (625, 305), (650, 330), (605, 340), (660, 285)]: p.star(x, y)
p.exitm(470, 385, "탈출 캡슐 — 40~200 m 떨어진 곳에 새로 내려옴", sz=12)

# ── 4. Alien: Isolation ──
p = P(*origin(0, 3), "Alien: Isolation", [
    "전철역(허브)마다 구역 하나 · 방마다 출입구 2개 이상",
    "막다른 방·일자 복도·갇히는 곳 없음 · 바닥 밑·환기구 샛길 · 숨는 사물함",
    "전원 복구·발전기 재시작이 되풀이되는 목표 · 괴물은 환기구 안에서 곧게 다님"])
p.line([(40, 30), (680, 30)], 6, C["hub"])
for x in (100, 360, 620): p.box(x - 30, 16, 60, 28, C["hub"], "역", 13)
p.line([(100, 44), (100, 80)], 6, C["tun"]); p.lab(100, 96, "다른 구역", 12, C["sub"])
p.line([(620, 44), (620, 80)], 6, C["tun"]); p.lab(620, 96, "다른 구역", 12, C["sub"])
rooms = {1: (190, 110, 120, 80), 2: (350, 96, 150, 100), 3: (540, 120, 110, 70), 4: (180, 250, 140, 90), 5: (360, 240, 120, 110), 6: (520, 250, 140, 80)}
def ctr(k): x, y, w, h = rooms[k]; return (x + w / 2, y + h / 2)
p.line([(360, 44), (425, 96)], 7, C["tun"])
for a, b in [(1, 2), (2, 3), (1, 4), (2, 5), (3, 6), (4, 5), (5, 6), (1, 5)]: p.line([ctr(a), ctr(b)], 7, C["tun"])
for k, (x, y, w, h) in rooms.items(): p.box(x, y, w, h, C["room"])
p.line([(170, 212), (680, 212)], 4, C["mon"], dash=True); p.lab(600, 226, "환기구 (괴물)", 13, C["mon"])
p.line([(170, 380), (540, 380)], 4, C["crawl"], dash=True); p.lab(355, 400, "바닥 밑 샛길", 13, C["crawl"])
p.box(196, 300, 14, 28, C["hide"]); p.box(640, 290, 14, 28, C["hide"]); p.lab(203, 346, "사물함", 12, C["hide"])
p.fix(420, 300); p.lab(420, 330, "전원 복구", 13, C["fix"], True)
p.bar(680, 290); p.line([(690, 290), (715, 290)], 5, C["tun"], dash=True); p.lab(610, 360, "잠긴 문 — 나중 도구로 열고 돌아옴", 12, C["door"])

# ── 5. Dead by Daylight ──
p = P(*origin(1, 0), "Dead by Daylight", [
    "네모 울타리 안 · 큰 건물 1 + 오두막 1 은 늘 같은 자리(이정표), 나머지 칸은 판마다 바뀜",
    "발전기 7개 중 5개를 고쳐야 출구 문 2곳에 전기가 들어온다 (혼자 1개 90초)",
    "고치는 중 타이밍 실패 = 발전기 폭발 + 괴물에게 '큰 소리 알림'"])
p.frame(60, 20, 600, 380, C["tun"], 6)
p.box(250, 130, 170, 120, C["room"], "큰 건물", 17); p.box(500, 284, 76, 56, C["room"], "오두막", 14)
for (x, y) in [(100, 70), (560, 60), (110, 300), (330, 320)]:
    d.rectangle([*p.T(x, y), *p.T(x + 54, y + 44)], outline=C["tun"], width=4 * SS)
p.lab(137, 132, "빙빙 도는 칸", 12, C["sub"])
for (x, y) in [(120, 180), (200, 50), (440, 60), (610, 190), (190, 370), (420, 300), (620, 370)]: p.fix(x, y)
p.exitm(60, 230); p.lab(66, 262, "출구", 13, C["exit"], anchor="lm"); p.exitm(660, 110); p.lab(654, 142, "출구", 13, C["exit"], anchor="rm")
for a in range(8):
    t = a * math.pi / 4; p.line([(420 + 16 * math.cos(t), 300 + 16 * math.sin(t)), (420 + 30 * math.cos(t), 300 + 30 * math.sin(t))], 4, C["mon"])
p.lab(470, 262, "쾅!", 20, C["mon"], True)
p.dot(250, 360, 11, C["mon"]); p.lab(250, 388, "괴물", 13, C["mon"], True)
p.line([(390, 310), (262, 356)], 3, C["mon"], dash=True)

# ── 6. Texas Chain Saw Massacre ──
p = P(*origin(1, 1), "The Texas Chain Saw Massacre", [
    "지하 미로에서 시작 → 트인 지상 → 가장자리 출구 넷 · 좁은 지하에서 바깥으로 나오면 안도",
    "출구마다 다른 수리: 발전기 끄기 · 배터리 끄기 · 밸브 끼워 돌리기(증기가 보임) · 퓨즈 퍼즐(지하)",
    "서두르면 소리 막대가 넘쳐 소리가 난다 · 할아버지는 소리가 쌓이면 깨어나 움직이는 사람을 알린다"])
p.line([(0, 206), (720, 206)], 2, C["sub"]); p.lab(8, 190, "지상", 13, C["sub"], anchor="lm"); p.lab(8, 222, "지하", 13, C["sub"], anchor="lm")
d.rectangle([*p.T(40, 212), *p.T(700, 412)], fill=(34, 31, 29))
for i, c in enumerate([[(90, 380), (200, 330), (300, 380), (420, 320)], [(200, 330), (180, 250)], [(420, 320), (420, 240)],
                       [(420, 320), (560, 360), (640, 380)], [(560, 360), (600, 250)], [(300, 380), (340, 300)]]):
    p.line(p.wig(c, 6, 20 + i), 7, C["tun"])
p.box(76, 368, 32, 24, C["hub"]); p.lab(92, 404, "시작", 12, C["hub"], True)
for x in (180, 420, 600): p.line([(x, 250), (x, 180)], 6, C["tun"])
p.lab(470, 232, "계단·구멍", 12, C["sub"])
p.box(130, 90, 120, 70, C["room"]); p.box(310, 70, 150, 100, C["room"]); p.box(520, 96, 120, 70, C["room"])
p.line([(250, 125), (310, 125)], 7, C["tun"]); p.line([(460, 125), (520, 125)], 7, C["tun"])
p.dot(385, 118, 11, C["mon"]); p.lab(385, 146, "할아버지", 13, C["mon"], True)
p.exitm(26, 130); p.fix(70, 176); p.lab(70, 200, "발전기", 12, C["fix"])
p.line([(40, 130), (70, 176)], 2, C["fix"], dash=True, dl=5, gap=4)
p.exitm(694, 130); p.fix(660, 180); p.lab(660, 158, "배터리", 12, C["fix"])
p.exitm(385, 16); p.fix(300, 30); p.lab(300, 54, "밸브", 12, C["fix"])
p.exitm(680, 395); p.fix(640, 380); p.lab(610, 404, "퓨즈", 12, C["fix"])

# ── 7. Still Wakes the Deep (Addair 구간) ──
p = P(*origin(1, 2), "Still Wakes the Deep — 한 구간", [
    "괴물이 도는 큰 방 하나 안에서 수리 4단계 (틈 → 스위치 순서 → 열쇠로 발전기 → 계전기)",
    "방 둘레와 가운데에 기어가는 틈 · 통풍구가 제어실과 발전기를 잇는다",
    "전체 게임은 시추선 모듈 다섯을 지나는 일직선 이야기 · 싸움 없음, 숨기·던져 유인만"])
p.box(60, 50, 540, 320, (74, 68, 64))
p.box(270, 160, 120, 80, (110, 102, 96), "발전기", 15, C["text"])
p.box(130, 90, 70, 50, (110, 102, 96)); p.box(460, 260, 80, 60, (110, 102, 96))
p.line([(80, 70), (580, 70), (580, 350), (80, 350), (80, 70)], 4, C["crawl"], dash=True)
p.line([(330, 70), (330, 160)], 4, C["crawl"], dash=True); p.line([(330, 240), (330, 350)], 4, C["crawl"], dash=True)
p.lab(200, 364, "둘레·가운데 기어가는 틈", 13, C["crawl"])
p.box(620, 150, 90, 90, C["room"], "제어실", 15); p.line([(600, 195), (620, 195)], 8, C["tun"])
p.line([(390, 200), (620, 215)], 3, C["crawl"], dash=True); p.lab(520, 228, "통풍구", 12, C["crawl"])
p.ring(330, 200, 230, 115, C["mon"], 3); p.lab(150, 240, "괴물 순찰", 13, C["mon"], True)
p.lab(90, 330, "①", 20, C["fix"], True)
p.fix(665, 262); p.lab(665, 290, "② 스위치", 13, C["fix"], True)
p.fix(330, 256); p.lab(330, 282, "③ 열쇠로 재시동", 13, C["fix"], True)
p.fix(500, 120); p.lab(500, 146, "④ 계전기", 13, C["fix"], True)

# ── 8. Voices of the Void ──
p = P(*origin(1, 3), "Voices of the Void", [
    "가운데 기지 + 둘레에 위성 접시들(작은 서버실) + 변압기 셋",
    "매일 변압기 하나가 닳고, 0 이 되면 기지가 정전 → 직접 나가서 빨간 버튼",
    "고장 난 서버는 빨간불(멀리서 보임) · 접시 배치 모양은 그림용 (확인 못 함)"])
dishes = [(360 + 290 * math.cos(a), 205 + 165 * math.sin(a)) for a in [i * 2 * math.pi / 10 + 0.3 for i in range(10)]]
for (x, y) in dishes: p.line([(360, 205), (x, y)], 3, C["tun"])
p.box(305, 170, 110, 70, C["hub"], "기지", 18)
for i, (x, y) in enumerate(dishes):
    p.dot(x, y, 14, C["room"])
    if i == 3: p.dot(x + 14, y - 12, 6, C["mon"])
p.lab(dishes[5][0], dishes[5][1] + 30, "위성 접시", 13, C["room"])
for (x, y) in [(150, 120), (600, 330), (470, 40)]: p.fix(x, y, 14)
p.dot(600, 330, 24, None, outline=C["mon"]); p.lab(600, 368, "오늘 닳는 변압기", 13, C["fix"], True)
p.lab(150, 146, "변압기", 13, C["fix"], True)

# ── 9. Dead Space (2023) ──
p = P(*origin(2, 0), "Dead Space (2023)", [
    "트램 역(허브) + 구역 여섯이 바퀴살처럼 · 구역 안은 방과 복도가 고리로 다시 만난다",
    "장마다 배의 설비를 되살린다 (엔진 연료 넣기 · 원심분리기 재가동)",
    "차단기: 연료 · 조명 · 산소 중 둘만 켤 수 있다 → 무엇을 포기할지 고른다"])
zones = ["기관·채굴", "수경재배", "격납고", "의료", "숙소", "함교"]
for i, z in enumerate(zones):
    a = -math.pi / 2 + i * math.pi / 3; x, y = 360 + 265 * math.cos(a), 208 + 160 * math.sin(a)
    p.line([(360, 208), (x, y)], 6, C["hub"])
    p.box(x - 66, y - 34, 132, 68, C["room"]); p.ring(x, y + 6, 40, 17, C["tun"], 4, dash=False); p.lab(x, y - 20, z, 14, C["ink"], True)
p.dot(360, 208, 46, C["hub"]); p.lab(360, 208, "트램 역", 16, C["ink"], True)
p.fix(460, 50); p.lab(520, 50, "연료 넣기", 13, C["fix"], True)
for j, (t, on) in enumerate([("연료", True), ("조명", True), ("산소", False)]):
    p.box(560 + j * 50, 364, 36, 22, C["fix"] if on else (90, 84, 80)); p.lab(578 + j * 50, 400, t, 12, C["text"])
p.lab(470, 375, "차단기: 둘만", 13, C["fix"], True)
p.bar(170, 390, vertical=False); p.lab(120, 405, "보안 등급 문", 12, C["door"])

# ── 10. Resident Evil 2 (2019) 경찰서 ──
p = P(*origin(2, 1), "Resident Evil 2 (2019) — 경찰서", [
    "가운데 큰 홀(2층 높이) + 좌우 날개(3층까지) + 지하 · 그림은 한 층만",
    "날개 안은 긴 고리 복도인데 바리케이드로 끊겨 옆방으로 돌아가야 한다",
    "열쇠 하나가 여러 문을 열어 지름길이 생긴다 · 추적자는 하나, 발소리 = 실제 위치"])
p.line([(40, 70), (250, 70), (250, 310), (40, 310), (40, 70)], 12, C["tun"])
p.line([(470, 70), (680, 70), (680, 310), (470, 310), (470, 70)], 12, C["tun"])
for (x, y, w, h) in [(80, 100, 60, 50), (150, 100, 70, 60), (80, 220, 80, 60), (520, 110, 70, 60), (590, 220, 60, 60)]: p.box(x, y, w, h, C["room"])
p.box(290, 80, 140, 220, C["room"], "큰 홀\n(2층 높이)", 17)
p.line([(250, 190), (290, 190)], 10, C["tun"]); p.line([(430, 190), (470, 190)], 10, C["tun"])
p.bar(145, 70); p.bar(40, 190, vertical=False); p.lab(145, 44, "바리케이드", 12, C["door"])
p.bar(450, 190, col=C["door"]); p.lab(450, 222, "셔터", 12, C["door"])
p.line([(360, 300), (360, 340)], 4, C["sub"], dash=True); p.box(300, 340, 120, 50, C["dark"], "지하", 15, C["text"])
p.lab(420, 318, "여신상 → 지하", 12, C["sub"], anchor="lm")
p.star(115, 250); p.lab(115, 290, "열쇠", 12, C["rew"], True)
for (x, y) in [(250, 120), (290, 260), (470, 260)]:
    p.bar(x, y); p.line([(115, 250), (x, y)], 2, C["rew"], dash=True, dl=5, gap=4)
for k in range(7): p.dot(680 - 0, 290 - k * 30, 5, C["mon"])
p.lab(610, 340, "발소리 = 실제 위치", 13, C["mon"], True)

# ── 11. R.E.P.O. ──
p = P(*origin(2, 2), "R.E.P.O.", [
    "트럭 도착 방(추출 1) → 모듈 방들 → 반대쪽 끝에 추출 2~4 → 트럭으로 돌아와야 끝",
    "값나가는 물건을 들고 와야 한다 · 부딪히면 값이 깎이고, 떨어뜨리면 소리 → 괴물이 조사",
    "판마다 방 배치가 바뀐다 · 소리만 듣는 괴물, 눈으로 찾는 괴물이 따로"])
mods = [(130, 160, 110, 80), (290, 70, 90, 70), (290, 260, 100, 80), (430, 160, 120, 90), (440, 330, 80, 60), (580, 60, 100, 70), (590, 230, 110, 80)]
def mc(i): x, y, w, h = mods[i]; return (x + w / 2, y + h / 2)
p.line([(90, 200), mc(0)], 8, C["tun"])
for a, b in [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (3, 5), (3, 6)]: p.line([mc(a), mc(b)], 7, C["tun"])
p.box(20, 176, 70, 48, C["exit"], "트럭", 15)
for m in mods: p.box(*m, C["room"])
for (x, y, lb) in [(185, 200, "추출 1"), (630, 95, "추출"), (645, 270, "추출")]:
    d.rectangle([*p.T(x - 20, y - 14), *p.T(x + 20, y + 14)], outline=C["hub"], width=4 * SS); p.lab(x, y + 26, lb, 12, C["hub"], True)
for (x, y) in [(320, 95), (340, 300), (470, 190), (520, 220), (470, 360), (360, 290)]: p.star(x, y)
p.ring(490, 205, 50, 50, C["mon"], 3); p.lab(490, 130, "떨어뜨리면 소리", 13, C["mon"], True)
p.dot(680, 300, 10, C["mon"]); p.line([(670, 296), (538, 222)], 3, C["mon"], dash=True)

# ── 12. SCP: Containment Breach ──
p = P(*origin(2, 3), "SCP: Containment Breach", [
    "20×20 격자, 한 칸 = 8×8 m 방 (막다른 · 곧은 · 꺾인 · T · 네거리) · 판마다 자동 생성",
    "구역 셋을 검문소로 나눈다 · 카드키 등급을 올려 가며 문을 연다",
    "같은 크기 칸만 이어 붙이면 '격자' 느낌이 난다 — 지금 MAP3 두 판(8 m 칸)이 이쪽에 가깝다"])
cols, rows, gx, gy, cs, gp = 11, 6, 90, 22, 38, 20
zc = [C["room"], C["room"], (205, 140, 128), (205, 140, 128), (232, 205, 130), (232, 205, 130)]
rnd = random.Random(9); cells = [(c, r) for r in range(rows) for c in range(cols)]
def cc(c, r): return (gx + c * (cs + gp) + cs / 2, gy + r * (cs + gp) + cs / 2 + (18 if r >= 2 else 0) + (18 if r >= 4 else 0))
seen = {(5, 0)}; edges = []; front = [(5, 0)]
while front:                         # 격자 위 무작위 나무 (짜임을 보이려는 그림용)
    c, r = front.pop(rnd.randrange(len(front)))
    for dc, dr in rnd.sample([(1, 0), (-1, 0), (0, 1), (0, -1)], 4):
        n = (c + dc, r + dr)
        cross = sorted((r, n[1])) in ([1, 2], [3, 4])     # 구역 경계는 검문소(5열)로만 넘는다
        if 0 <= n[0] < cols and 0 <= n[1] < rows and n not in seen and (not cross or c == 5):
            seen.add(n); edges.append(((c, r), n)); front.append(n)
for a, b in edges: p.line([cc(*a), cc(*b)], 6, C["tun"])
for (c, r) in cells:
    x, y = cc(c, r); p.box(x - cs / 2, y - cs / 2, cs, cs, zc[r])
for r in (1, 3): x, y = cc(5, r); p.bar(x, y + 38, vertical=False)
p.lab(40, cc(0, 0)[1] + 29, "가벼운\n격리", 12, C["room"]); p.lab(40, cc(0, 2)[1] + 29, "무거운\n격리", 12, (205, 140, 128)); p.lab(40, cc(0, 4)[1] + 29, "입구\n구역", 12, (232, 205, 130))
p.lab(cc(5, 1)[0] + 70, cc(5, 1)[1] + 38, "검문소", 12, C["door"], True)
p.exitm(cc(2, 5)[0], 408); p.exitm(cc(9, 5)[0], 408)

# ── 아래 띠: 겹쳐 보면 ──
by = TOP + 3 * (PH + 44) + 10
text(30, by, "겹쳐 보면 (Claude 의 정리 — 사실은 위 그림과 조사 08 의 출처)", 26, C["fix"], b=True)
notes = [
    "① \"캐고 나가면 끝\"을 넘는 할 일은 대부분 전기·연료·수리다 — 열둘 중 여덟 (Bunker · DRG · Alien · DbD · TCSM · Still Wakes · VotV · Dead Space).",
    "② 고치는 행동이 소리를 내는 게임이 있다 (DbD 폭발 · TCSM 소리 막대 · 밸브 증기) — \"소리를 내야 돈, 소리를 내면 죽음\"과 같은 규칙.",
    "③ 넓은 곳 하나 + 좁은 길, 크기 차이를 크게 (DRG 거대한 동굴 ↔ 좁은 통로 · TCSM 좁은 지하 → 트인 바깥 · RE2 높은 홀).",
    "④ 막다른 곳 대신 고리, 그리고 한 번 열면 생기는 지름길 (Alien 막다른 방 없음 · RE2 열쇠 하나 = 여러 문 · Dead Space 구역 안 고리).",
    "⑤ 안전한 거점 + 시간이 가면 나빠지는 것이 밖으로 밀어낸다 (Bunker 연료 · VotV 변압기 · Lethal 자정 출발).",
    "⑥ 같은 크기 칸만 이어 붙이면 격자 느낌 (SCP) — MAP3 두 판이 답답해 보인 까닭 중 하나로 보인다."]
for i, n in enumerate(notes): text(40, by + 46 + i * 34, n, 21)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MAP3_레퍼런스_12.png")
img.resize((W, H), Image.LANCZOS).save(out)
print(out)
