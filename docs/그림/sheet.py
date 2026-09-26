# 평면도·구조도 그림용 도구 (MAP3_레퍼런스_12.py · MAP3_구조안.py 가 같이 쓴다).
# 좌표는 1배 px, 실제 그림은 SS 배로 그린 뒤 줄인다.
import math, random, os
from PIL import Image, ImageDraw, ImageFont

SS = 2
BG = (43, 40, 38)
C = dict(hub=(126, 208, 126), room=(216, 207, 184), tun=(167, 159, 143), fix=(255, 154, 60),
         rew=(255, 214, 70), exit=(255, 158, 128), mon=(222, 72, 60), door=(255, 122, 26),
         crawl=(80, 210, 200), text=(235, 230, 220), sub=(165, 160, 150), hide=(90, 160, 255),
         dark=(62, 57, 53), ink=(40, 36, 34))
img = d = None
def new(W, H):
    """캔버스를 새로 만든다. 돌려준 img, d 를 받아 쓴다."""
    global img, d
    img = Image.new("RGB", (W * SS, H * SS), BG); d = ImageDraw.Draw(img)
    return img, d
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
    """판 하나. 그림 칸은 DW × DH (1배 px), 위에 제목, 아래에 설명 줄."""
    def __init__(s, ox, oy, title=None, lines=(), DW=720, DH=420):
        s.DW, s.DH = DW, DH
        s.x0, s.y0 = ox + 10, oy + (52 if title else 0)
        if title: text(ox + 12, oy + 8, title, 25, b=True)
        yy = s.y0 + s.DH + 14
        for ln in lines:
            for piece in wrap(ln, 19, DW - 5):
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

def scale(p, kx=1.0, ky=1.0, labk=1.0):
    """판 p 의 좌표를 kx · ky 배로, 글자는 labk 배로 (선 굵기·점 크기는 그대로)."""
    p.T = lambda x, y: ((p.x0 + x * kx) * SS, (p.y0 + y * ky) * SS)
    p.lab = lambda x, y, t, sz=14, col=None, b=False, anchor="mm": P.lab(p, x * kx, y * ky, t, round(sz * labk), col, b, anchor)
    def box(x, y, w, h, col, label=None, sz=16, tc=None, outline=None, ow=3):
        P.box(p, x, y, w, h, col, None, sz, tc, outline, ow)
        if label: text(p.x0 + (x + w / 2) * kx, p.y0 + (y + h / 2) * ky, label, sz, tc or C["ink"], b=True, anchor="mm")
    p.box = box
    return p

# ── 갱도 그림 기호 (MAP3_구조안.py · MAP3_평면_AB.py) ──
LIT = (239, 213, 140)          # 불 켜진 방·길
WATER = (52, 104, 170)
LADDER = (236, 200, 90)
ROCK = (58, 53, 49)
OUTMON = (178, 122, 235)       # 바깥 괴물 (갱도 괴물과 다른 것)

def ladder(p, x, y1, y2, w=14, land=()):
    p.line([(x - w / 2, y1), (x - w / 2, y2)], 3, LADDER); p.line([(x + w / 2, y1), (x + w / 2, y2)], 3, LADDER)
    y = y1 + 6
    while y < y2: p.line([(x - w / 2, y), (x + w / 2, y)], 2, LADDER); y += 11
    for yy in land: p.line([(x - 16, yy), (x + 16, yy)], 5, LADDER)      # 쉬는 발판
def hatch(p, a, b, col=None):
    """갱도 a→b 위에 동발 구간 빗금."""
    L = math.hypot(b[0] - a[0], b[1] - a[1]); ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    t = 0
    while t <= L:
        cx, cy = a[0] + ux * t, a[1] + uy * t
        p.line([(cx - uy * 12 - ux * 4, cy + ux * 12 - uy * 4), (cx + uy * 12 + ux * 4, cy - ux * 12 + uy * 4)], 3, col or C["door"])
        t += 9
def water(p, x, y, w, h): d.rectangle([*p.T(x, y), *p.T(x + w, y + h)], fill=WATER)
def corpse(p, x, y, label=None, sz=13):
    d.rounded_rectangle([*p.T(x - 17, y - 7), *p.T(x + 17, y + 7)], radius=7 * SS, fill=(206, 206, 212), outline=(120, 120, 130), width=2 * SS)
    if label: p.lab(x, y - 20, label, sz, (206, 206, 212), True)
def fac(p, x, y, label, side="r", sz=13):
    p.fix(x, y, 11)
    if side == "r": p.lab(x + 16, y, label, sz, C["fix"], True, anchor="lm")
    elif side == "l": p.lab(x - 16, y, label, sz, C["fix"], True, anchor="rm")
    elif side == "u": p.lab(x, y - 22, label, sz, C["fix"], True)
    else: p.lab(x, y + 22, label, sz, C["fix"], True)
def arrow(p, a, b, col, w=3, dash=False):
    p.line([a, b], w, col, dash=dash)
    L = math.hypot(b[0] - a[0], b[1] - a[1]); ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    d.polygon([p.T(*b), p.T(b[0] - ux * 14 - uy * 7, b[1] - uy * 14 + ux * 7), p.T(b[0] - ux * 14 + uy * 7, b[1] - uy * 14 - ux * 7)], fill=col)
def booth(p, x1, y1, x2, y2, label, lx=None, ly=None):
    p.line([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)], 3, (245, 245, 245), dash=True, dl=12, gap=8)
    p.lab(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else y1 - 14, label, 14, (245, 245, 245), True)
def region(p, x, y, w, h, label, col=(150, 145, 135)):
    p.line([(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], 2, col, dash=True, dl=8, gap=6)
    p.lab(x + 10, y + 16, label, 14, col, True, anchor="lm")
def mon_net(p, dots, links, col=None):
    for (a, c, b) in links: p.line(p.curve(a, c, b), 3, col or C["mon"], dash=True)
    for (x, y) in dots: p.dot(x, y, 8, col or C["mon"])
def block(p, x, y):
    """부스판에서 길을 막는 자리 (MAP2 막힘 돌무더기처럼)."""
    p.dot(x, y, 13, (96, 88, 80), outline=C["door"])
    p.line([(x - 8, y - 8), (x + 8, y + 8)], 4, C["door"]); p.line([(x - 8, y + 8), (x + 8, y - 8)], 4, C["door"])

LEGEND = [("hub", "거점 (안전·밝음)"), ("lit", "불 켜진 방·길"), ("room", "방 · 트인 곳"), ("tun", "갱도"), ("exit", "갱구 · 출구"),
          ("fix", "고칠 시설"), ("hatch", "동발 구간 (무너짐)"), ("rew", "광석"), ("corpse", "시체 (들것)"), ("ladder", "사다리"),
          ("mon", "괴물 틈 · 길"), ("crawl", "바위 틈 (사람만)"), ("water", "물"), ("booth", "부스판 조각")]
def legend(x0, y0, items=LEGEND, per_row=5, colw=270, sz=21):
    LP = P.__new__(P); LP.x0, LP.y0 = x0, y0
    for i, (k, t) in enumerate(items):
        cx, cy = (i % per_row) * colw, 12 + (i // per_row) * 30
        if k in ("hub", "room"): LP.box(cx, cy - 10, 30, 20, C[k])
        elif k == "lit": LP.box(cx, cy - 10, 30, 20, LIT)
        elif k == "tun": LP.line([(cx, cy), (cx + 30, cy)], 8, C["tun"])
        elif k == "exit": LP.exitm(cx + 15, cy)
        elif k == "fix": LP.fix(cx + 15, cy)
        elif k == "hatch": LP.line([(cx, cy), (cx + 30, cy)], 8, C["tun"]); hatch(LP, (cx, cy), (cx + 30, cy))
        elif k == "rew": LP.star(cx + 15, cy)
        elif k == "corpse": corpse(LP, cx + 15, cy)
        elif k == "ladder": ladder(LP, cx + 15, cy - 12, cy + 12)
        elif k == "mon": LP.dot(cx + 6, cy, 6, C["mon"]); LP.line([(cx + 14, cy), (cx + 32, cy)], 3, C["mon"], dash=True, dl=5, gap=4)
        elif k == "outmon": LP.dot(cx + 6, cy, 6, OUTMON); LP.line([(cx + 14, cy), (cx + 32, cy)], 3, OUTMON, dash=True, dl=5, gap=4)
        elif k == "crawl": LP.line([(cx, cy), (cx + 30, cy)], 4, C["crawl"], dash=True, dl=6, gap=4)
        elif k == "water": water(LP, cx, cy - 9, 30, 18)
        elif k == "booth": LP.line([(cx, cy), (cx + 30, cy)], 3, (245, 245, 245), dash=True, dl=6, gap=4)
        elif k == "block": block(LP, cx + 15, cy)
        text(x0 + cx + 42, y0 + cy, t, sz, anchor="lm")
