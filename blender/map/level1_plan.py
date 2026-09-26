"""MAP3 안 A+B — 1편 표 (56차 09-26). 가운데 = MAP2 v4(booth_table, 사용자 손그림) 그대로, 서쪽 산 밑 · 동쪽 산 밑 구역을 손으로 더한다.
  python blender/map/level1_plan.py docs/그림/MAP3_1편_평면.png    → 잰 값(MAP2 재는 법) + 평면 그림
표 형식은 booth_table.build() 와 같다: 굴 = (이름, [(x, y, 바닥, 폭)], 천장, 갱목?, 걷는 길?, 빛, 종류). 좌표 m, 케이지 = (0, 0), 동쪽 +x, 북쪽 +y.
사용자 조건(09-26): 1편 하나가 MAP2 전체의 3배 넘게 · 괴물에게서 도망갈 곳 · 일직선 말고 미로 같은 긴장감 · 괴물은 사다리를 못 오른다.
거르는 값(MAP2 판정 값을 층에): 숨을 곳 · 짧은 고리 · 갈림 없는 굴 15 m 이하 · 막다른 굴 8 m 이하 · 길 잃고 300 m 안에 케이지 50 % 이하."""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import booth_table as bt
import map2_plan as mp


def circle(cx, cy, rx, ry, n=20, a0=0.0):
    return [(cx + rx * math.cos(a0 + 2 * math.pi * i / n), cy + ry * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n + 1)]


def build():
    B = bt.build(crevices=True)                                           # 가운데 = MAP2 v4 (R2b 바위 틈 포함)
    T, R, PIL = list(B["T"]), list(B["R"]), list(B["PILLARS"])
    T = [t for t in T if t[6] != "niche"]                                 # 대피소는 전체를 다 짠 뒤 한 번에 다시
    crev = list(B["crevices"]); gaps = list(B["gap_big"]); ladders = []; labels = []; ledges = []

    def tun(name, pts, w=3.0, z=0.0, lz="K", h=3.2, timber=True):
        T.append((name, [(x, y, z, w) for x, y in pts], h, timber, True, lz, "tunnel"))
    def cave(name, pts, w, h=9.0):                                        # 자연 동굴(트인 곳) — 아주 넓은 굴로 그린다
        T.append((name, [(x, y, 0.0, w) for x, y in pts], h, False, True, "K", "tunnel"))
    def crawl(name, a, b, via=(), z=0.0):
        T.append((name, [(*p, z, bt.CRAWL_W) for p in (a, *via, b)], bt.CRAWL_H, False, False, "K", "crawl"))
    def through(name, a, b):                                              # 뚫린 바위 틈 (사람만, 몸을 옆으로)
        crawl(name, a, b); crev.append(bt.through_crevice(T, name))
    def closed(name, wall, n):                                            # 막힌 바위 틈 (숨는 곳)
        crev.append(bt.closed_crevice(T, name, np.array(wall, float), np.array(n, float) / np.linalg.norm(n), 0.0))
    def pillar_room(tag, x0, x1, y0, y1, rows, px, a=3.0, lz="K"):
        """엇갈린 기둥 방: 가로 통로(방 띠) rows+1 줄 + 줄 사이 세로 통로를 반 칸씩 엇갈리게 — 바둑판처럼 안 보이게"""
        ys = [y0 + (y1 - y0 - a) * j / rows for j in range(rows + 1)]
        R.extend([("room_r", x0, x1, y, y + a, 0.0, 3.0, lz) for y in ys])
        for j in range(rows):
            off = 0 if j % 2 == 0 else px / 2
            xs = [x for x in np.arange(x0 + off, x1 - a + 0.01, px)] + ([x1 - a] if j % 2 == 0 else [])
            xs = sorted(set(round(x, 2) for x in xs if x <= x1 - a))
            R.extend([("room_c", x, x + a, ys[j], ys[j + 1] + a, 0.0, 3.0, lz) for x in xs])
            for xa, xb in zip(xs, xs[1:]):
                if xb - xa - a > 0.5: PIL.append((xa + a, xb, ys[j] + a, ys[j + 1]))
            if j % 2 == 1 and xs and xs[0] - x0 > 0.5: PIL.append((x0, xs[0], ys[j] + a, ys[j + 1]))
            if xs and x1 - (xs[-1] + a) > 0.5: PIL.append((xs[-1] + a, x1, ys[j] + a, ys[j + 1]))
        return ys

    # ════════ 서쪽 산 밑 — 큰 굴(위로 윗 갱도까지 트임) · 둘레 굴 · 바깥 고리 · 엇갈린 기둥 방 · 노보리 ════════
    cave("w_cave_a", [(-142, -6), (-128, 4), (-112, 6)], 18); cave("w_cave_b", [(-140, 11), (-133, 11), (-118, -5), (-111, -12)], 14)
    ring = [(-98, 4), (-100, 18), (-115, 25), (-135, 23), (-152, 13), (-157, -3), (-149, -19), (-129, -25), (-108, -21), (-99, -8), (-98, 4)]
    tun("w_ring", ring, 3.0)
    for i, (a, b) in enumerate([((-99, -1), (-106, -1)), ((-104, 16), (-110, 11)), ((-123, 24), (-123, 16)), ((-146, 16), (-140, 10)),
                                ((-155, 3), (-147, 1)), ((-146, -17), (-136, -8)), ((-126, -24), (-126, -14)), ((-106, -19), (-111, -12))]):
        tun("w_spoke%d" % i, [a, b], 2.8)
    tun("w_main", [(-59.85, 9.66), (-70, 10), (-82, 7), (-98, 5)], 3.3, lz="D")
    tun("w_n1", [(-62.16, 19.39), (-72, 24), (-86, 27), (-100, 18)], 3.0)
    tun("w_e1", [(-62.3, -6.3), (-75, -9), (-88, -8), (-99, -8)], 3.0)
    tun("w_s1", [(-62.3, -19.95), (-78, -26), (-95, -29), (-108, -21)], 3.0)
    tun("w_x1", [(-77, 25.5), (-78, 8.3)], 2.8); tun("w_x2", [(-86, 6.4), (-85, -8.1)], 2.8); tun("w_x3", [(-71, -8.4), (-72, -23.5)], 2.8)
    outer = [(-72, 24), (-88, 37), (-112, 42), (-140, 40), (-162, 34), (-173, 18), (-175, 0), (-171, -18), (-160, -32), (-140, -41), (-118, -43), (-96, -38), (-78, -26)]
    tun("w_outer", outer, 3.0)
    for i, (a, b) in enumerate([((-120, 24.5), (-119, 42)), ((-151, 14), (-164, 32)), ((-157, -3), (-175, -2)), ((-147, -20), (-163, -30)), ((-127, -25), (-124, -43))]):
        tun("w_xc%d" % i, [a, b], 2.8)
    wy = pillar_room("w_pil", -208, -178, -28, 14, 4, 7.0)                # 서쪽 끝 엇갈린 기둥 방 (옛 캔 자리)
    for i, y in enumerate((wy[4] + 1.5, wy[2] + 1.5, wy[0] + 1.5)):
        tun("w_pl%d" % i, [(-174.5 + (0 if i != 1 else -0.5), y), (-178.5, y)], 3.0)
    # 노보리(북서, 15°): 바깥 고리 북쪽에서 위로 올라가는 비탈 굴 셋 + 가로 둘
    cols = [-166, -152, -138]; rows_ = [36, 46, 56]
    for i, x in enumerate(cols): tun("w_nb_c%d" % i, [(x, rows_[0] - (2 if i == 0 else 0)), (x, rows_[-1])], 2.6, z=1.0)
    for j, y in enumerate(rows_[1:]): tun("w_nb_r%d" % j, [(cols[0], y), (cols[-1], y)], 2.4, z=1.0 + 2.5 * (j + 1))
    for x in (-170, -134): tun("w_nb_face%d" % int(-x), [(x + (4 if x < -150 else -4), 56), (x, 60)], 2.4, z=6.0)      # 막장 끝 4 m
    # 채탄장(서남, 15°): 바깥 고리 남쪽 아래로 비탈 굴 셋 + 가로 둘
    for i, x in enumerate((-158, -145, -132)): tun("w_ch_c%d" % i, [(x, -40.5 + (1 if i == 1 else 0)), (x, -62)], 2.6, z=-1.0)
    for j, y in enumerate((-51, -62)): tun("w_ch_r%d" % j, [(-158, y), (-132, y)], 2.4, z=-1.0 - 2.5 * (j + 1))
    tun("w_ch_face1", [(-158, -62), (-164, -64)], 2.4); tun("w_ch_face2", [(-132, -62), (-126, -65)], 2.4)
    # 막장(짧은 막다른 굴 ≤ 8 m) · 곁길
    tun("w_face1", [(-208, -5), (-214, -6)], 2.4); tun("w_face2", [(-196, 14), (-197, 20)], 2.4)
    tun("w_sd1", [(-140, 40), (-134, 47), (-122, 48), (-114, 42)], 2.8)
    tun("w_sd3", [(-162, 34), (-172, 44), (-182, 38), (-173, 18)], 2.8)
    tun("w_sw", [(-171, -18), (-186, -38), (-204, -42), (-216, -32), (-208, -26)], 3.0)          # 서남 옛 운반갱도 고리
    tun("w_sd2", [(-140, -41), (-133, -48), (-120, -49), (-114, -43)], 2.8)
    # 바위 틈 · 개구멍
    through("w_cr1", (-160, 20), (-156, 13)); through("w_cr2", (-95, 28), (-100, 21.5)); through("w_cr3", (-166, -24), (-160, -18))
    through("w_cr4", (-178.5, 0), (-175, 0))
    crawl("w_cw1", (-88, -9.5), (-93, -27.5)); crawl("w_cw2", (-110, 44.5), (-114, 41.5))
    for i, (wall, n) in enumerate([((-86, 28.5), (0, 1)), ((-160, 33), (-1, 0.4)), ((-173.5, -10), (1, 0)), ((-139, -42.5), (0, -1)),
                                   ((-80, -8.2), (0, 1)), ((-112, 43.5), (0, 1)), ((-104, -30), (0, -1)), ((-66, 10.5), (0, 1))]):
        closed("w_hide%d" % i, wall, n)
    gaps += [(-165, 30, 0), (-190, -30, 0), (-100, -35, 0), (-130, 30, 0)]
    ladders += [((-125, 12), "↑ 윗 갱도 (큰 굴 벽)"), ((-209, 10), "↑ 윗 갱도 (공기 나가는 쪽)")]
    labels += [((-126, -2), "서쪽 큰 굴 — 위로 윗 갱도까지 트임"), ((-193, -33), "엇갈린 기둥 방 (옛 캔 자리)"), ((-152, 62), "노보리 15° (막장)"), ((-145, -68), "채탄장 15° (막장)")]

    # ════════ 동쪽 산 밑 — 2편까지 트인 큰 구덩이 · 가장자리 길 · 바깥 고리 · 엇갈린 기둥 방 · 좁은 곁갱도 무리 ════════
    PX, PY, PR = 140.0, 2.0, 15.0                                          # 구덩이 (걷지 못함 — 2편 바닥까지 떨어짐)
    rim = circle(PX, PY, 21, 20, 24)
    tun("e_rim", rim, 3.2)
    for i, a in enumerate([0.3, 1.9, 3.5, 5.0]):                         # 가장자리에서 구덩이로 튀어나온 턱 (내려다보는 곳, 3.5 m 막다른)
        p0 = (PX + 20 * math.cos(a), PY + 19 * math.sin(a)); p1 = (PX + 16.5 * math.cos(a), PY + 15.5 * math.sin(a))
        tun("e_ledge%d" % i, [p0, p1], 2.6); ledges.append(p1)
    tun("e_main", [(66.15, 10.15), (80, 9), (96, 6), (119.5, 5)], 3.3, lz="D")
    tun("e_e1", [(72.45, -8), (88, -12), (104, -15), (122, -10)], 3.0)
    outer_e = [(71.05, 27.3), (86, 37), (110, 41), (140, 44), (168, 38), (187, 25), (196, 3), (190, -20), (174, -35), (146, -41), (116, -39), (93, -31), (72.1, -19.95)]
    tun("e_outer", outer_e, 3.0)
    for i, (a, b) in enumerate([((140, 22), (140, 44)), ((156, 15), (172, 34)), ((161, 2), (196, 2.5)), ((155, -12), (173, -34)), ((137, -18), (141, -41)), ((124, 14), (111, 40.5))]):
        tun("e_sp%d" % i, [a, b], 2.8)
    tun("e_x1", [(88, 36), (96, 6.5)], 2.8); tun("e_x2", [(100, 5.8), (104, -15)], 2.8); tun("e_x3", [(84, -11.5), (93, -31)], 2.8)
    ey = pillar_room("e_pil", 200, 232, -30, 18, 5, 7.0)
    for i, y in enumerate((ey[5] + 1.5, ey[3] + 1.5, ey[1] + 1.5)):
        tun("e_pl%d" % i, [(193 if i != 1 else 195.5, y), (200.5, y)], 3.0)
    # 좁은 곁갱도 무리(북동, 갱목 촘촘) — 폭 2.4 짧은 굴이 얽힌다
    nx = [(150, 41.5), (152, 50), (162, 56), (174, 52), (178, 40)]
    tun("e_nn_a", nx, 2.4)
    tun("e_nn_b", [(152, 50), (164, 47), (174, 52)], 2.4); tun("e_nn_c", [(162, 56), (164, 47)], 2.4); tun("e_nn_d", [(174, 52), (186, 58), (190, 50), (184, 30)], 2.4)
    tun("e_face1", [(186, 58), (190, 64)], 2.4); tun("e_face2", [(232, -10), (238, -11)], 2.4); tun("e_face3", [(216, 18), (217, 24)], 2.4)
    tun("e_sagang", [(98, 38), (100, 44.5)], 3.0)                        # 사갱 (↑ 마당) — 위로 이어짐
    tun("e_sd1", [(146, -41), (138, -48), (124, -48), (116, -39)], 2.8)
    tun("e_sd2", [(110, 41), (118, 50), (132, 51), (140, 44)], 2.8)
    tun("e_se", [(190, -20), (204, -40), (224, -44), (238, -32), (232, -24)], 3.0)               # 남동 옛 운반갱도 고리
    for i, x in enumerate((154, 167, 180)): tun("e_nb_c%d" % i, [(x, -39.5 - (1.5 if i == 2 else 0)), (x, -62)], 2.6, z=-1.0)       # 노보리(남동, 25°)
    for j, y in enumerate((-51, -62)): tun("e_nb_r%d" % j, [(154, y), (180, y)], 2.4, z=-1.0 - 4.0 * (j + 1))
    tun("e_nb_face1", [(154, -62), (148, -65)], 2.4); tun("e_nb_face2", [(180, -62), (186, -64)], 2.4)
    through("e_cr1", (118, 38.5), (122, 33)); through("e_cr2", (178, -26), (171, -21)); through("e_cr3", (196, -12), (200.5, -12)); through("e_cr4", (80, 33), (82, 26))
    crawl("e_cw1", (84, 7.5), (86, -11.5)); crawl("e_cw2", (160, -15), (175, -8))
    for i, (wall, n) in enumerate([((110, 42.5), (0, 1)), ((190, 10), (1, 0)), ((160, -38.5), (0, -1)), ((95, 7.5), (0, 1)),
                                   ((128, -43), (-0.3, -1)), ((176, 36.5), (0.5, 1)), ((88, -13.5), (0, -1)), ((75, 29), (-0.5, 1))]):
        closed("e_hide%d" % i, wall, n)
    gaps += [(195, 30, 0), (120, -45, 0), (210, 22, 0), (90, 45, 0)]
    ladders += [((PX, PY - 15.5), "↓ 2편 (구덩이 바닥)"), ((166, 30), "↑ 동쪽 윗 갱도")]
    labels += [((PX, PY), "동쪽 큰 구덩이 — 2편까지 트임 (걷지 못함)"), ((216, -34), "엇갈린 기둥 방"), ((168, 62), "좁은 곁갱도 무리 (갱목 촘촘)"), ((100, 48), "사갱 ↑ 마당"), ((167, -68), "노보리 25° (막장)")]

    # 손으로 적은 끝점이 이웃 굴 가운데 선에서 조금 빗나가면(4.5 m 안) 그 굴 위로 붙인다 — 안 붙으면 막다른 굴로 잰다
    for i, t in enumerate(T):
        if not (t[0].startswith(("w_", "e_")) and t[6] == "tunnel"): continue
        pts = list(t[1])
        for k in (0, -1):
            q = pts[k][:2]; others = [o for o in T if o[4] and o[0] != t[0]]
            if bt.room_of(R, q) is not None or any(bt.proj(o[1], q)[0] < o[1][0][3] / 2 + 0.6 for o in others): continue
            o = min(others, key=lambda o: bt.proj(o[1], q)[0]); dist, s, _ = bt.proj(o[1], q)
            if dist < 4.5: pts[k] = (*bt.point_at(o[1], s), pts[k][2], pts[k][3])
        T[i] = (t[0], pts, *t[2:])
    bt.add_niches(T, R)                                                   # 좁은 대피소 자동 (MAP2 와 같은 규칙: 갈림·숨을 곳 사이 12.5 m 넘지 않게)
    return dict(T=T, R=R, PILLARS=PIL, crevices=crev, through={c[0] for c in crev if c[1] == "through"}, gap_big=gaps, ladders=ladders,
                labels=labels, pit=(PX, PY, PR), ledges=ledges, home_rect=B["home_rect"], fake_end=B["fake_end"], booth_blocks=B["blocks"])


def as_measure(m, keep=None):
    T = m["T"] if keep is None else [t for t in m["T"] if keep(t)]
    return dict(T=T, R=m["R"], small_gaps=[], home_rooms=("plaza",), home_rect=m["home_rect"], through=m["through"])


def booth_slice(m):
    """부스판 조각: 가운데(MAP2 전체, 묶음 1·2 끔) + 서쪽 큰 굴 둘레 — 나머지는 막는다"""
    keep = lambda t: not (t[0].startswith("e_") or (t[0].startswith("w_") and not any(t[0].startswith(p) for p in ("w_main", "w_n1", "w_e1", "w_s1", "w_x1", "w_x2", "w_x3", "w_ring", "w_spoke", "w_cave", "w_cr2", "w_cw1"))))
    R = [r for r in m["R"] if -64 <= r[1] <= 75]
    return dict(T=[t for t in m["T"] if keep(t)], R=R, small_gaps=[], home_rooms=("plaza",), home_rect=m["home_rect"], through=m["through"])


def draw(m, rs, out):
    from PIL import Image, ImageDraw, ImageFont
    SS = 2; W = 3000; TOP = 330
    xs_ = [p[0] for t in m["T"] for p in t[1]]; ys_ = [p[1] for t in m["T"] for p in t[1]]
    S1 = (W - 120) / (max(xs_) - min(xs_)); H = int(TOP + S1 * (max(ys_) - min(ys_)) + 90); S = S1 * SS
    img = Image.new("RGB", (W * SS, H * SS), "#2c2926"); d = ImageDraw.Draw(img)
    Fn = lambda sz, b=False: ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if b else "C:/Windows/Fonts/malgun.ttf", int(sz * SS))
    OX = W * SS / 2 - S * (max(xs_) + min(xs_)) / 2; OY = TOP * SS + S * max(ys_)
    P = lambda x, y: (OX + S * x, OY - S * y)
    COL = {"L": "#efd68e", "D": "#d6cdb6", "K": "#aaa290"}
    def poly(pts, w, col):
        q = [P(*p[:2]) for p in pts]; d.line(q, fill=col, width=max(1, int(w * S)), joint="curve")
        for X, Y in q: r = w * S / 2; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col)
    def rect(x0, x1, y0, y1, col): d.rectangle([P(x0, y1), P(x1, y0)], fill=col)
    def dot(x, y, col, r=6): X, Y = P(x, y); r *= SS; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col, outline="#1d1b19", width=SS)
    def txt(x, y, s, sz=15, col="#f4f1ea", b=True, anchor="mm"): d.text(P(x, y), s, font=Fn(sz, b), fill=col, anchor=anchor)
    for t in m["T"]:
        if t[6] == "tunnel": poly(t[1], t[1][0][3], "#cfc6b0" if t[1][0][3] > 10 else COL[t[5]])
    for r in m["R"]:
        if r[0] == "goaf": rect(r[1], r[2], r[3], r[4], "#4a4540")
        else: rect(r[1], r[2], r[3], r[4], "#7fd67f" if r[0] == "plaza" else COL[r[7]])
    for x0, x1, y0, y1 in m["PILLARS"]: rect(x0, x1, y0, y1, "#3a3632")
    px, py, pr = m["pit"]; X, Y = P(px, py); rr = pr * S; d.ellipse([X - rr, Y - rr * 0.95, X + rr, Y + rr * 0.95], fill="#141211", outline="#c9c1ad", width=3 * SS)
    for t in m["T"]:
        if t[6] == "niche": poly(t[1], 1.1, "#3d8fe0")
        if t[6] == "crawl": poly(t[1], 0.9, "#9ff0ff")
        if t[6] == "crevice": poly(t[1], 0.9, "#19d9c8" if t[0] in m["through"] else "#f04fbf")
        if t[6] == "crevice_room": poly(t[1], 1.4, "#f04fbf")
    for g in m["gap_big"]: dot(g[0], g[1], "#d33c2c", 7)
    for (x, y), s in m["ladders"]:
        X, Y = P(x, y)
        for sg in (-1, 1): d.line([X + 6 * sg * SS, Y - 14 * SS, X + 6 * sg * SS, Y + 14 * SS], fill="#ffe066", width=3 * SS)
        for k in range(-2, 3): d.line([X - 6 * SS, Y + k * 6 * SS, X + 6 * SS, Y + k * 6 * SS], fill="#ffe066", width=2 * SS)
        d.text((X + 12 * SS, Y), s, font=Fn(13, True), fill="#ffe066", anchor="lm")
    for (x, y), s in m["labels"]: txt(x, y, s, 15)
    fe = m["fake_end"]; rect(fe[0] - 1.6, fe[0] + 1.6, fe[1] - 0.2, fe[1] + 1.4, "#ff9c7a")
    txt(0, 0, "케이지", 13, "#1d1b19")
    hull = [(-161, -28), (-161, 28), (-121, 29), (-97, 33), (-66, 49), (76, 49), (76, -44), (-66, -44), (-97, -34), (-121, -31), (-161, -28)]   # 부스판 조각 (이 밖은 막음)
    q = [P(*p) for p in hull]
    for a_, b_ in zip(q, q[1:]):
        L_ = math.dist(a_, b_); n_ = max(1, int(L_ / (14 * SS)))
        for i in range(0, n_, 2): d.line([a_[0] + (b_[0] - a_[0]) * i / n_, a_[1] + (b_[1] - a_[1]) * i / n_, a_[0] + (b_[0] - a_[0]) * (i + 1) / n_, a_[1] + (b_[1] - a_[1]) * (i + 1) / n_], fill="#f5f5f5", width=3 * SS)
    txt(-112, -36, "부스판 조각 (혼자 3~5분) — 흰 점선 밖은 막는다", 15, "#f5f5f5")
    for x, s in ((-128, "서쪽 산 밑 (새로)"), (0, "가운데 = MAP2 (사용자 손그림 그대로)"), (150, "동쪽 산 밑 (새로)")): txt(x, max(ys_) + 7, s, 19, "#c9c1ad")
    for xb in (-63.5, 74):                                                 # 가운데와 새 구역의 경계
        X0, Y0 = P(xb, max(ys_) + 3); X1, Y1 = P(xb, min(ys_) - 3); yy = Y0
        while yy < Y1: d.line([X0, yy, X0, min(yy + 10 * SS, Y1)], fill="#6b645a", width=2 * SS); yy += 18 * SS
    sx, sy = P(min(xs_), min(ys_) - 4); d.line([sx, sy, sx + 30 * S, sy], fill="#f4f1ea", width=3 * SS); d.text((sx + 15 * S, sy + 14 * SS), "30 m", font=Fn(13), fill="#f4f1ea", anchor="mm")
    r, rb, r2, r2b = rs
    d.text((30 * SS, 18 * SS), "MAP3 안 A+B — 1편 평면 (가운데 MAP2 + 서쪽·동쪽 산 밑)", font=Fn(34, True), fill="#f4f1ea")
    rows = [("", "1편 전체", "부스판 조각", "MAP2 (판정 받은 맵)", "기준 (MAP2 판정 값)"),
            ("걸을 수 있는 바닥", "%.0f m² (MAP2 의 %.1f 배)" % (r["area"], r["area"] / r2["area"]), "%.0f m² (MAP2 부스판의 %.1f 배)" % (rb["area"], rb["area"] / r2b["area"]), "%.0f m² · 부스판 %.0f m²" % (r2["area"], r2b["area"]), "1편 = MAP2 의 3배 넘게 · 부스판 = 2배"),
            ("숨을 곳 (대피소 · 개구멍 · 바위 틈)", "%d" % r["hides"], "%d" % rb["hides"], "%d" % r2["hides"], "MAP2 만큼 촘촘히"),
            ("짧은 고리 (한 바퀴 60 m 이하)", "%d" % r["small"], "%d" % rb["small"], "%d" % r2["small"], "MAP2 만큼 촘촘히"),
            ("갈림·숨을 곳 없는 가장 긴 굴", "%.0f m" % r["longest"], "%.0f m" % rb["longest"], "%.0f m" % r2["longest"], "15 m 이하"),
            ("막다른 굴 가장 긴 것", "%.0f m" % r["dead"], "%.0f m" % rb["dead"], "%.0f m" % r2["dead"], "8 m 이하"),
            ("길 잃고 300 m 안에 케이지 (가운데값)", "%.0f %% (%.0f m)" % (r["within300"], r["median"]), "%.0f %% (%.0f m)" % (rb["within300"], rb["median"]), "%.0f %% · 부스판 %.0f %%" % (r2["within300"], r2b["within300"]), "50 % 이하 = 헤맨다")]
    cx = [30, 480, 900, 1330, 1760]
    for i, row in enumerate(rows):
        for j, c in enumerate(row):
            d.text((cx[j] * SS, (70 + i * 25) * SS), c, font=Fn(15 if i else 14, i == 0 or j == 0), fill="#efd68e" if i == 0 else ("#c9c1ad" if j == 0 else "#f4f1ea"))
    lx, ly = 2230, 80
    for i, (c, s) in enumerate([("#7fd67f", "케이지 광장"), ("#efd68e", "불 켜진 길·방"), ("#aaa290", "어두운 굴"), ("#cfc6b0", "큰 굴(트인 곳)"), ("#3a3632", "기둥(바위)"),
                                ("#4a4540", "채굴적(괴물 집)"), ("#3d8fe0", "좁은 대피소"), ("#9ff0ff", "개구멍"), ("#19d9c8", "뚫린 바위 틈"), ("#f04fbf", "막힌 바위 틈(숨는 곳)"),
                                ("#d33c2c", "큰 틈(괴물)"), ("#ffe066", "사다리 (괴물 못 오름)"), ("#141211", "구덩이 (2편까지)"), ("#ff9c7a", "가짜 출구 끝")]):
        X, Y = (lx + (i % 2) * 380) * SS, (ly + (i // 2) * 22) * SS
        d.rectangle([X, Y - 7 * SS, X + 14 * SS, Y + 7 * SS], fill=c, outline="#6b645a"); d.text((X + 20 * SS, Y), s, font=Fn(14), fill="#f4f1ea", anchor="lm")
    img.resize((W, H), Image.LANCZOS).save(out); print("saved", out)


if __name__ == "__main__":
    m = build()
    r = mp.measure(as_measure(m)); rb = mp.measure(booth_slice(m))
    r2 = mp.measure(mp.MAP2_V4)
    B2 = bt.build(crevices=True); b2 = mp.measure(dict(T=[t for t in B2["T"] if not (t[0].startswith(("W_", "E_", "T_", "fake", "sd_arc", "sd_edge", "link12", "link23", "v_z1", "v_z3", "c_z1", "c_link12")))],
                                                   R=[x for x in B2["R"] if not any(z["x0"] - 0.5 <= x[1] and x[2] <= z["x1"] + 0.5 and z["y0"] - 0.5 <= x[3] and x[4] <= z["y1"] + 6 for z in (B2["Z"]["Z1"], B2["Z"]["Z3"]))],
                                                   small_gaps=[], home_rooms=("plaza",), home_rect=B2["home_rect"], through={c[0] for c in B2["crevices"] if c[1] == "through"}))
    for k, v in (("1편", r), ("부스판", rb), ("MAP2", r2), ("MAP2 부스판", b2)):
        print("%s: 바닥 %.0f m² · 굴 %.0f m · 짧은 고리 %d · 숨을 곳 %d · 가장 긴 %.0f m (%s) · 막다른 %.0f m (%s) · 300 m 안 %.0f %% · 가운데값 %.0f m"
              % (k, v["area"], v["length"], v["small"], v["hides"], v["longest"], v["at"], v["dead"], v["dead_at"], v.get("within300", -1), v.get("median", -1)))
    if len(sys.argv) > 1: draw(m, (r, rb, r2, b2), sys.argv[1])
