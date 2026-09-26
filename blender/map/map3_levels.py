"""MAP3 안 A+B — 층마다 표 (56차 09-26): 1편 · 2편 · 윗 갱도(서·동). 손으로 적은 좌표 + MAP2 재는 법 + 평면 그림.
  python blender/map/map3_levels.py docs/그림      → MAP3_1편_평면.png · MAP3_2편_평면.png · MAP3_윗갱도_평면.png + 잰 값
표 형식은 booth_table.build() 와 같다: 굴 = (이름, [(x, y, 바닥, 폭)], 천장, 갱목?, 걷는 길?, 빛, 종류). 좌표 m, 케이지 = (0, 0), 동쪽 +x, 북쪽 +y.
세 층 모두 같은 가로·세로 자리 — 수갱(0, 0) · 서쪽 큰 굴(-125, 2) · 동쪽 구덩이(140, 2) · 사다리는 위아래 층에서 같은 자리.
1편 가운데 = MAP2 v4(booth_table, 사용자 손그림) 그대로.
사용자 조건(09-26): 1편 = MAP2 전체의 3배 넘게 · 괴물에게서 도망갈 곳 · 일직선 말고 미로 같은 긴장감 · 괴물은 사다리를 못 오른다 ·
  맵 곳곳에 고칠 곳(갱목 · 랜턴 · 배수관 · 환기구 등)을 두고 고치면 돈 — 넓어도 도망만 다니지 않게. 고칠 곳 자리는 아래 repairs() 규칙, 값·소리·시간은 따로 정한다.
거르는 값(MAP2 판정 값을 층에): 숨을 곳 · 짧은 고리 · 갈림 없는 굴 15 m 이하 · 막다른 굴 8 m 이하 · 길 잃고 300 m 안에 케이지(윗 갱도는 갱구) 50 % 이하."""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import booth_table as bt
import map2_plan as mp


def circle(cx, cy, rx, ry, n=20, a0=0.0):
    return [(cx + rx * math.cos(a0 + 2 * math.pi * i / n), cy + ry * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n + 1)]


class Lv:
    """한 층의 표를 손으로 적는 도구."""
    def __init__(s, T=(), R=(), PIL=(), crev=(), gaps=()):
        s.T, s.R, s.PIL, s.crev, s.gaps = list(T), list(R), list(PIL), list(crev), list(gaps)
        s.ladders, s.labels, s.voids, s.waters, s.corpses, s.doors, s.exits, s.hubs, s.new = [], [], [], [], [], [], [], [], set()

    def tun(s, name, pts, w=3.0, z=0.0, lz="K", h=3.2, timber=True):
        s.T.append((name, [(x, y, z, w) for x, y in pts], h, timber, True, lz, "tunnel")); s.new.add(name)
    def cave(s, name, pts, w, h=9.0):                                     # 자연 동굴(트인 곳) — 아주 넓은 굴로 그린다
        s.T.append((name, [(x, y, 0.0, w) for x, y in pts], h, False, True, "K", "tunnel")); s.new.add(name)
    def room(s, name, x0, x1, y0, y1, lz="K", h=3.5):
        s.R.append((name, x0, x1, y0, y1, 0.0, h, lz))
    def siding(s, name, a, b, off, w=3.0, lz="K"):                        # 긴 굴 옆 곁길 — 바위 하나를 두고 갈라졌다 합친다 (짧은 고리)
        L = math.dist(a, b); nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
        p = lambda f, o: (a[0] + (b[0] - a[0]) * f + nx * o, a[1] + (b[1] - a[1]) * f + ny * o)
        s.tun(name, [p(0, 0), p(0.25, off), p(0.75, off), p(1, 0)], w, lz=lz)
    def crawl(s, name, a, b, via=(), z=0.0):
        s.T.append((name, [(*p, z, bt.CRAWL_W) for p in (a, *via, b)], bt.CRAWL_H, False, False, "K", "crawl"))
    def through(s, name, a, b):                                           # 뚫린 바위 틈 (사람만, 몸을 옆으로)
        s.crawl(name, a, b); s.crev.append(bt.through_crevice(s.T, name))
    def closed(s, name, wall, n):                                         # 막힌 바위 틈 (숨는 곳)
        s.crev.append(bt.closed_crevice(s.T, name, np.array(wall, float), np.array(n, float) / np.linalg.norm(n), 0.0))
    def hide(s, name, parent, frac, side):                                # 굴 parent 의 frac 자리 벽에 막힌 바위 틈 (side ±1 = 왼쪽/오른쪽 벽)
        pts = next(t for t in s.T if t[0] == parent)[1]; L = bt.seg_len(pts); sp = L * frac
        (x, y) = bt.point_at(pts, sp); (x2, y2) = bt.point_at(pts, min(sp + 0.5, L)); (x1, y1) = bt.point_at(pts, max(sp - 0.5, 0))
        dx, dy = x2 - x1, y2 - y1; l = math.hypot(dx, dy); n = np.array((-dy / l * side, dx / l * side)); w = pts[0][3]
        s.closed(name, np.array((x, y)) + n * w / 2, n)
    def pillar_room(s, x0, x1, y0, y1, rows, px, a=3.0, lz="K"):
        """엇갈린 기둥 방: 가로 통로(방 띠) rows+1 줄 + 줄 사이 세로 통로를 반 칸씩 엇갈리게"""
        ys = [y0 + (y1 - y0 - a) * j / rows for j in range(rows + 1)]
        s.R.extend([("room_r", x0, x1, y, y + a, 0.0, 3.0, lz) for y in ys])
        for j in range(rows):
            off = 0 if j % 2 == 0 else px / 2
            xs = [x for x in np.arange(x0 + off, x1 - a + 0.01, px)] + ([x1 - a] if j % 2 == 0 else [])
            xs = sorted(set(round(x, 2) for x in xs if x <= x1 - a))
            s.R.extend([("room_c", x, x + a, ys[j], ys[j + 1] + a, 0.0, 3.0, lz) for x in xs])
            for xa, xb in zip(xs, xs[1:]):
                if xb - xa - a > 0.5: s.PIL.append((xa + a, xb, ys[j] + a, ys[j + 1]))
            if j % 2 == 1 and xs and xs[0] - x0 > 0.5: s.PIL.append((x0, xs[0], ys[j] + a, ys[j + 1]))
            if xs and x1 - (xs[-1] + a) > 0.5: s.PIL.append((xs[-1] + a, x1, ys[j] + a, ys[j + 1]))
        return ys
    def slope_zone(s, tag, xs, top, ys, z0=0.0, dz=2.5, faces=()):
        """비탈 막장(노보리·채탄장): 세로 굴 xs 를 top(각 굴의 시작 y) 에서 ys[-1] 까지 + 가로 ys + 막장 끝(faces: (시작, 끝))"""
        for i, (x, y0) in enumerate(zip(xs, top)): s.tun("%s_c%d" % (tag, i), [(x, y0), (x, ys[-1])], 2.6, z=z0)
        for j, y in enumerate(ys): s.tun("%s_r%d" % (tag, j), [(xs[0], y), (xs[-1], y)], 2.4, z=z0 + dz * (j + 1))
        for k, (a, b) in enumerate(faces): s.tun("%s_face%d" % (tag, k), [a, b], 2.4, z=z0 + dz * len(ys))
    def rim(s, tag, cx, cy, rx, ry, spokes=(), ledges=(), w=3.0):
        """구덩이·트인 굴 가장자리 길 + 안으로 튀어나온 턱(ledges: 각도, 3.5 m 막다른) + 바깥으로 나가는 굴(spokes: (각도, 끝점))"""
        s.tun(tag, circle(cx, cy, rx, ry, 24), w)
        for i, a in enumerate(ledges):
            s.tun("%s_ledge%d" % (tag, i), [(cx + rx * math.cos(a), cy + ry * math.sin(a)), (cx + (rx - 3.8) * math.cos(a), cy + (ry - 3.8) * math.sin(a))], 2.6)
        for i, (a, end) in enumerate(spokes): s.tun("%s_sp%d" % (tag, i), [(cx + rx * math.cos(a), cy + ry * math.sin(a)), end], 2.8)

    def finish(s):
        # 손으로 적은 끝점이 이웃 굴 가운데 선에서 조금 빗나가면(4.5 m 안) 그 굴 위로 붙인다 — 안 붙으면 막다른 굴로 잰다
        for i, t in enumerate(s.T):
            if t[0] not in s.new or t[6] != "tunnel": continue
            pts = list(t[1])
            for k in (0, -1):
                q = pts[k][:2]; others = [o for o in s.T if o[4] and o[0] != t[0]]
                if bt.room_of(s.R, q) is not None or any(bt.proj(o[1], q)[0] < o[1][0][3] / 2 + 0.6 for o in others): continue
                o = min(others, key=lambda o: bt.proj(o[1], q)[0]); dist, sp, _ = bt.proj(o[1], q)
                if dist < 4.5: pts[k] = (*bt.point_at(o[1], sp), pts[k][2], pts[k][3])
            s.T[i] = (t[0], pts, *t[2:])
        s.T = [t for t in s.T if t[6] != "niche"]
        bt.add_niches(s.T, s.R)                                           # 좁은 대피소 자동 (MAP2 와 같은 규칙: 갈림·숨을 곳 사이 12.5 m 넘지 않게)
        s.through = {c[0] for c in s.crev if c[1] == "through"}
        return s

    def measure_dict(s, home_rooms=("plaza",), home_rect=(-8, 8, -5, 5), keep=None, R=None):
        T = s.T if keep is None else [t for t in s.T if keep(t)]
        return dict(T=T, R=s.R if R is None else R, small_gaps=[], home_rooms=home_rooms, home_rect=home_rect, through=s.through)


# ═════════════════════════════════════════ 1편 ═════════════════════════════════════════
def build_l1():
    B = bt.build(crevices=True)                                           # 가운데 = MAP2 v4 (R2b 바위 틈 포함)
    s = Lv(B["T"], B["R"], B["PILLARS"], B["crevices"], B["gap_big"])
    s.home_rect = B["home_rect"]; s.fake_end = B["fake_end"]
    # ── 서쪽 산 밑: 큰 굴(위로 윗 갱도까지 트임) · 둘레 굴 · 바깥 고리 · 엇갈린 기둥 방 · 노보리 · 채탄장
    s.cave("w_cave_a", [(-142, -6), (-128, 4), (-112, 6)], 18); s.cave("w_cave_b", [(-140, 11), (-133, 11), (-118, -5), (-111, -12)], 14)
    s.tun("w_ring", [(-98, 4), (-100, 18), (-115, 25), (-135, 23), (-152, 13), (-157, -3), (-149, -19), (-129, -25), (-108, -21), (-99, -8), (-98, 4)], 3.0)
    for i, (a, b) in enumerate([((-99, -1), (-106, -1)), ((-104, 16), (-110, 11)), ((-123, 24), (-123, 16)), ((-146, 16), (-140, 10)),
                                ((-155, 3), (-147, 1)), ((-146, -17), (-136, -8)), ((-126, -24), (-126, -14)), ((-106, -19), (-111, -12))]):
        s.tun("w_spoke%d" % i, [a, b], 2.8)
    s.tun("w_main", [(-59.85, 9.66), (-70, 10), (-82, 7), (-98, 5)], 3.3, lz="D")
    s.tun("w_n1", [(-62.16, 19.39), (-72, 24), (-86, 27), (-100, 18)], 3.0)
    s.tun("w_e1", [(-62.3, -6.3), (-75, -9), (-88, -8), (-99, -8)], 3.0)
    s.tun("w_s1", [(-62.3, -19.95), (-78, -26), (-95, -29), (-108, -21)], 3.0)
    s.tun("w_x1", [(-77, 25.5), (-78, 8.3)], 2.8); s.tun("w_x2", [(-86, 6.4), (-85, -8.1)], 2.8); s.tun("w_x3", [(-71, -8.4), (-72, -23.5)], 2.8)
    s.tun("w_outer", [(-72, 24), (-88, 37), (-112, 42), (-140, 40), (-162, 34), (-173, 18), (-175, 0), (-171, -18), (-160, -32), (-140, -41), (-118, -43), (-96, -38), (-78, -26)], 3.0)
    for i, (a, b) in enumerate([((-120, 24.5), (-119, 42)), ((-151, 14), (-164, 32)), ((-157, -3), (-175, -2)), ((-147, -20), (-163, -30)), ((-127, -25), (-124, -43))]):
        s.tun("w_xc%d" % i, [a, b], 2.8)
    wy = s.pillar_room(-208, -178, -28, 14, 4, 7.0)                        # 서쪽 끝 엇갈린 기둥 방 (옛 캔 자리)
    for i, y in enumerate((wy[4] + 1.5, wy[2] + 1.5, wy[0] + 1.5)): s.tun("w_pl%d" % i, [(-174.5 + (0 if i != 1 else -0.5), y), (-178.5, y)], 3.0)
    s.slope_zone("w_nb", [-166, -152, -138], [34, 36, 36], [46, 56], z0=1.0, faces=[((-166, 56), (-170, 60)), ((-138, 56), (-134, 60))])   # 노보리 15°
    s.slope_zone("w_ch", [-158, -145, -132], [-40.5, -39.5, -40.5], [-51, -62], z0=-1.0, dz=-2.5, faces=[((-158, -62), (-164, -64)), ((-132, -62), (-126, -65))])  # 채탄장 15°
    s.tun("w_face1", [(-208, -5), (-214, -6)], 2.4); s.tun("w_face2", [(-196, 14), (-197, 20)], 2.4)
    s.tun("w_sd1", [(-140, 40), (-134, 47), (-122, 48), (-114, 42)], 2.8); s.tun("w_sd3", [(-162, 34), (-172, 44), (-182, 38), (-173, 18)], 2.8)
    s.tun("w_sw", [(-171, -18), (-186, -38), (-204, -42), (-216, -32), (-208, -26)], 3.0); s.tun("w_sd2", [(-140, -41), (-133, -48), (-120, -49), (-114, -43)], 2.8)
    s.through("w_cr1", (-160, 20), (-156, 13)); s.through("w_cr2", (-95, 28), (-100, 21.5)); s.through("w_cr3", (-166, -24), (-160, -18)); s.through("w_cr4", (-178.5, 0), (-175, 0))
    s.crawl("w_cw1", (-88, -9.5), (-93, -27.5)); s.crawl("w_cw2", (-110, 44.5), (-114, 41.5))
    for i, (wall, n) in enumerate([((-86, 28.5), (0, 1)), ((-160, 33), (-1, 0.4)), ((-173.5, -10), (1, 0)), ((-139, -42.5), (0, -1)),
                                   ((-80, -8.2), (0, 1)), ((-112, 43.5), (0, 1)), ((-104, -30), (0, -1)), ((-66, 10.5), (0, 1))]):
        s.closed("w_hide%d" % i, wall, n)
    s.gaps += [(-165, 30, 0), (-190, -30, 0), (-100, -35, 0), (-130, 30, 0)]
    s.ladders += [((-123, 24), "↑ 윗 갱도 (큰 굴 벽)"), ((-209, 10), "↑ 윗 갱도 (공기 나가는 쪽)"), ((-95, -29), "↓ 2편")]
    s.labels += [((-126, -2), "서쪽 큰 굴 — 위로 윗 갱도까지 트임"), ((-193, -33), "엇갈린 기둥 방 (옛 캔 자리)"), ((-152, 64), "노보리 15° (막장)"), ((-145, -69), "채탄장 15° (막장)")]
    # ── 동쪽 산 밑: 2편까지 트인 큰 구덩이 · 가장자리 길 · 바깥 고리 · 엇갈린 기둥 방 · 좁은 곁갱도 무리 · 노보리 · 사갱
    PX, PY = 140.0, 2.0
    s.voids.append((PX, PY, 15.0, 14.2, "동쪽 큰 구덩이 — 2편까지 트임 (걷지 못함)"))
    s.rim("e_rim", PX, PY, 21, 20, ledges=[0.3, 1.9, 3.5, 5.0], w=3.2)
    s.tun("e_main", [(66.15, 10.15), (80, 9), (96, 6), (119.5, 5)], 3.3, lz="D")
    s.tun("e_e1", [(72.45, -8), (88, -12), (104, -15), (122, -10)], 3.0)
    s.tun("e_outer", [(71.05, 27.3), (86, 37), (110, 41), (140, 44), (168, 38), (187, 25), (196, 3), (190, -20), (174, -35), (146, -41), (116, -39), (93, -31), (72.1, -19.95)], 3.0)
    for i, (a, b) in enumerate([((140, 22), (140, 44)), ((156, 15), (172, 34)), ((161, 2), (196, 2.5)), ((155, -12), (173, -34)), ((137, -18), (141, -41)), ((124, 14), (111, 40.5))]):
        s.tun("e_sp%d" % i, [a, b], 2.8)
    s.tun("e_x1", [(88, 36), (96, 6.5)], 2.8); s.tun("e_x2", [(100, 5.8), (104, -15)], 2.8); s.tun("e_x3", [(84, -11.5), (93, -31)], 2.8)
    ey = s.pillar_room(200, 232, -30, 18, 5, 7.0)
    for i, y in enumerate((ey[5] + 1.5, ey[3] + 1.5, ey[1] + 1.5)): s.tun("e_pl%d" % i, [(193 if i != 1 else 195.5, y), (200.5, y)], 3.0)
    s.tun("e_nn_a", [(150, 41.5), (152, 50), (162, 56), (174, 52), (178, 40)], 2.4)
    s.tun("e_nn_b", [(152, 50), (164, 47), (174, 52)], 2.4); s.tun("e_nn_c", [(162, 56), (164, 47)], 2.4); s.tun("e_nn_d", [(174, 52), (186, 58), (190, 50), (184, 30)], 2.4)
    s.tun("e_face1", [(186, 58), (190, 64)], 2.4); s.tun("e_face2", [(232, -10), (238, -11)], 2.4); s.tun("e_face3", [(216, 18), (217, 24)], 2.4)
    s.tun("e_sagang", [(98, 38), (100, 44.5)], 3.0)                        # 사갱 (↑ 마당) — 위로 이어짐
    s.tun("e_sd1", [(146, -41), (138, -48), (124, -48), (116, -39)], 2.8); s.tun("e_sd2", [(110, 41), (118, 50), (132, 51), (140, 44)], 2.8)
    s.tun("e_se", [(190, -20), (204, -40), (224, -44), (238, -32), (232, -24)], 3.0)
    s.slope_zone("e_nb", [154, 167, 180], [-39.5, -38.5, -35], [-51, -62], z0=-1.0, dz=-4.0, faces=[((154, -62), (148, -65)), ((180, -62), (186, -64))])   # 노보리 25°
    s.through("e_cr1", (118, 38.5), (122, 33)); s.through("e_cr2", (178, -26), (171, -21)); s.through("e_cr3", (196, -12), (200.5, -12)); s.through("e_cr4", (80, 33), (82, 26))
    s.crawl("e_cw1", (84, 7.5), (86, -11.5)); s.crawl("e_cw2", (160, -15), (175, -8))
    for i, (wall, n) in enumerate([((110, 42.5), (0, 1)), ((190, 10), (1, 0)), ((160, -38.5), (0, -1)), ((95, 7.5), (0, 1)),
                                   ((128, -43), (-0.3, -1)), ((176, 36.5), (0.5, 1)), ((88, -13.5), (0, -1)), ((75, 29), (-0.5, 1))]):
        s.closed("e_hide%d" % i, wall, n)
    s.gaps += [(195, 30, 0), (120, -45, 0), (210, 22, 0), (90, 45, 0)]
    s.ladders += [((PX, PY - 16.5), "↓ 2편 (구덩이 바닥)"), ((166, 30), "↑ 동쪽 윗 갱도"), ((93, -31), "↓ 2편")]
    s.labels += [((216, -34), "엇갈린 기둥 방"), ((168, 63), "좁은 곁갱도 무리 (갱목 촘촘)"), ((100, 48), "사갱 ↑ 마당"), ((167, -69), "노보리 25° (막장)")]
    s.hubs = [((-4, -14), "배전반")]                                     # 1편 배전반 = MAP2 배전·충전실 쪽 (케이지 광장 남쪽)
    return s.finish()


def booth_slice(s):
    """1편 부스판 조각: 가운데(MAP2 전체, 묶음 1·2 끔) + 서쪽 큰 굴 둘레 — 나머지는 막는다"""
    keep = lambda t: not (t[0].startswith("e_") or (t[0].startswith("w_") and not any(t[0].startswith(p) for p in ("w_main", "w_n1", "w_e1", "w_s1", "w_x1", "w_x2", "w_x3", "w_ring", "w_spoke", "w_cave", "w_cr2", "w_cw1"))))
    return s.measure_dict(home_rect=s.home_rect, keep=keep, R=[r for r in s.R if -64 <= r[1] <= 75])


# ═════════════════════════════════════════ 2편 ═════════════════════════════════════════
def build_l2():
    s = Lv()
    s.room("plaza", -8, 8, -5, 5, lz="D", h=4.0)                          # 2편 정거장 (케이지 바닥)
    # ── 가운데: 운반갱도(들어오는 바람) · 북쪽 나가는 바람 길 · 남쪽 고리 · 저수지와 펌프실
    s.tun("m2_hw", [(-8, 0), (-25, 1), (-45, -2), (-62, 0)], 3.3, lz="D"); s.tun("m2_he", [(8, 0), (25, -1), (45, 2), (62, 0)], 3.3, lz="D")
    s.tun("m2_air", [(-62, 22), (-40, 26), (-15, 24), (0, 28), (20, 24), (40, 27), (62, 22)], 3.0)
    s.tun("m2_xn", [(0, 5), (0, 28)], 2.8); s.tun("m2_xw", [(-25, 1), (-27, 24)], 2.8); s.tun("m2_xe", [(25, -1), (22, 24)], 2.8)
    s.tun("m2_xww", [(-45, -2), (-42, 26)], 2.8); s.tun("m2_xee", [(45, 2), (42, 26)], 2.8); s.doors += [(-43.5, 12), (43.5, 14)]
    s.tun("m2_south", [(-45, -2), (-42, -20), (-26, -34), (0, -38), (26, -34), (42, -20), (45, 2)], 3.0)
    s.waters.append((-20, -28, 6, -12, "pool")); s.labels.append(((-7, -20), "저수지"))
    s.room("pump", 10, 24, -24, -12, lz="L", h=3.8); s.labels.append(((17, -9.5), "펌프실"))
    s.tun("m2_pumpc", [(4, -5), (8, -10), (12, -13)], 2.8, lz="L"); s.tun("m2_pumps", [(18, -24), (19, -35)], 2.8)
    s.tun("m2_sumpw", [(-8, -5), (-24, -10), (-30, -24), (-26, -34)], 2.8)
    s.siding("m2_sd1", (-25, 1), (-45, -2), -7, lz="D"); s.siding("m2_sd2", (25, -1), (45, 2), 7, lz="D")
    s.siding("m2_sd3", (-15, 24), (-40, 26), -7); s.siding("m2_sd4", (20, 24), (40, 27), 7)
    # ── 서쪽: 운반갱도 · 나가는 바람 길 · 기둥 방(채굴적) · 남쪽 고리 · 채탄장(아래로) · 막아 둔 옛 갱도(풍문 너머)
    s.tun("w2_h", [(-62, 0), (-80, -3), (-100, 0), (-122, -2), (-150, 0)], 3.3, lz="D")
    s.tun("w2_air", [(-62, 22), (-85, 30), (-110, 34), (-138, 30), (-155, 18), (-150, 0)], 3.0)
    s.pillar_room(-128, -88, 37, 60, 3, 7.0); s.tun("w2_pl0", [(-118, 32.9), (-118, 37.5)], 3.0); s.tun("w2_pl1", [(-96, 31.8), (-96, 37.5)], 3.0)
    s.tun("w2_south", [(-42, -20), (-60, -28), (-85, -30), (-110, -26), (-135, -18), (-150, 0)], 3.0)
    s.tun("w2_x1", [(-80, -3), (-85, -30)], 2.8); s.tun("w2_x2", [(-100, 0), (-100, 33)], 2.8); s.tun("w2_x3", [(-122, -2), (-120, -25)], 2.8); s.tun("w2_x4", [(-138, 30), (-136, -1)], 2.8)
    s.siding("w2_sd1", (-80, -3), (-100, 0), -7, lz="D"); s.siding("w2_sd2", (-60, -28), (-85, -30), -7)
    s.slope_zone("w2_ch", [-124, -112, -100], [-22, -25, -27.5], [-39, -50], z0=-0.5, dz=-2.5, faces=[((-124, -50), (-130, -53)), ((-100, -50), (-94, -54))])
    s.doors.append((-153, 0))
    s.tun("w2_old", [(-150, 0), (-165, 1), (-180, -4), (-195, 0), (-206, 6)], 2.8); s.tun("w2_old_b", [(-180, -4), (-185, -18), (-198, -22)], 2.6)
    s.tun("w2_old_c", [(-195, 0), (-200, -10), (-198, -22)], 2.6); s.tun("w2_old_face", [(-206, 6), (-212, 8)], 2.4)
    s.waters.append((-206, -26, -178, -12, "flood")); s.corpses.append(((-192, -19), "옛 광부"))
    # ── 동쪽: 큰 굴 바닥(1편 구덩이 밑, 광석 가장 많음) · 둘레 굴 · 바깥 고리 · 기둥 방 · 노보리(아래로)
    s.tun("e2_h", [(62, 0), (80, 3), (96, 1), (108, 2)], 3.3, lz="D")
    s.cave("e2_cave_a", [(124, -2), (140, 4), (156, 0)], 18); s.cave("e2_cave_b", [(134, 16), (147, -12)], 14)
    s.rim("e2_ring", 140, 2, 32, 29, spokes=[(a, (140 + 17 * math.cos(a), 2 + 15 * math.sin(a))) for a in (0.2, 1.2, 2.2, 3.3, 4.3, 5.3)])
    s.tun("e2_outer", [(62, 22), (85, 34), (110, 42), (140, 44), (165, 40), (186, 26), (194, 2), (188, -20), (172, -36), (140, -42), (110, -40), (93, -31), (62, -20)], 3.0)
    s.tun("e2_link", [(42, -20), (62, -20)], 3.0); s.tun("e2_air", [(62, 22), (62, 0)], 2.8)
    for i, (a, b) in enumerate([((140, 31), (140, 44)), ((162, 22), (178, 34)), ((172, 2), (194, 2)), ((163, -19), (180, -30)), ((140, -27), (140, -42)), ((117, -19), (104, -37)), ((117, 22), (107, 41))]):
        s.tun("e2_xc%d" % i, [a, b], 2.8)
    s.pillar_room(150, 192, 47, 68, 3, 7.0); s.tun("e2_pl0", [(160, 42.4), (160, 47.5)], 3.0); s.tun("e2_pl1", [(186, 26), (188, 47.5)], 3.0)
    s.siding("e2_sd1", (110, 42), (140, 44), 7)
    s.slope_zone("e2_nb", [150, 162, 174], [-41, -39, -36], [-51, -62], z0=-0.5, dz=-4.0, faces=[((150, -62), (144, -65)), ((174, -62), (180, -65))])
    # ── 바위 틈 · 숨는 곳 · 큰 틈
    s.through("m2_cr1", (-35, -1.8), (-35, -6.2)); s.through("w2_cr1", (-90, -0.2), (-90, 4.2)); s.through("e2_cr1", (125, 44.3), (125, 48.7)); s.through("m2_cr2", (30, 26.8), (30, 31.2))
    for i, (par, f, sd) in enumerate([("m2_air", 0.25, 1), ("m2_south", 0.5, -1), ("w2_air", 0.5, -1), ("w2_south", 0.6, -1), ("w2_h", 0.8, 1),
                                      ("e2_outer", 0.3, 1), ("e2_outer", 0.75, -1), ("e2_h", 0.5, 1), ("w2_old", 0.5, 1)]):
        s.hide("h2_%d" % i, par, f, sd)
    s.gaps += [(-60, 35, 0), (-140, 42, 0), (0, -46, 0), (120, -48, 0), (198, 22, 0), (-170, -12, 0)]
    s.ladders += [((140, -14.5), "↑ 1편 (구덩이 가장자리)"), ((-95, -29), "↑ 1편"), ((93, -31), "↑ 1편")]
    s.labels += [((-108, 64), "기둥 방 (채굴적)"), ((171, 72), "기둥 방"), ((140, -8), "동쪽 큰 굴 바닥 — 광석 가장 많음, 위로 1편까지 트임"),
                 ((-112, -57), "채탄장 (아래로)"), ((162, -69), "노보리 (아래로)"), ((-190, 12), "막아 둔 옛 갱도 (물·가스) — 풍문 너머, 밤 6~7")]
    s.hubs = [((10, 7), "배전반")]
    return s.finish()


# ═════════════════════════════════════════ 윗 갱도 (서 · 동) ═════════════════════════════════════════
def build_up():
    s = Lv()
    s.room("adit", -66, -58, 0, 10, lz="D"); s.room("adit", -218, -210, 7, 17); s.room("adit", 58, 66, 0, 10, lz="D"); s.room("adit", 196, 204, 11, 19)
    s.exits += [((-62, 5), "서쪽 수평 갱구 (마당)"), ((-214, 12), "공기 나가는 갱구 (주선풍기, 밖)"), ((62, 5), "동쪽 수평 갱구 (마당)"), ((200, 15), "옛 갱구 사다릿길 (밖)")]
    # ── 서쪽: 큰 굴 위 가장자리(아래 1편까지 트임) · 채굴적 기둥 방 · 남쪽 고리 · 노보리(위로) · 공기 나가는 갱구
    s.tun("uw_adit", [(-62, 5), (-78, 6)], 3.3, lz="D"); s.tun("uw_main", [(-78, 6), (-90, 8), (-99, 3)], 3.0)
    s.voids.append((-125, 2, 20, 17.5, "서쪽 큰 굴 — 아래 1편 바닥까지 트임"))
    s.rim("uw_rim", -125, 2, 26, 23, ledges=[0.6, 2.6, 4.2])
    s.pillar_room(-150, -102, 31, 54, 3, 7.5)
    s.tun("uw_pl0", [(-125, 25), (-125, 31.5)], 3.0); s.tun("uw_pl1", [(-108, 19.4), (-108, 31.5)], 3.0); s.tun("uw_pl2", [(-145, 16.7), (-145, 31.5)], 3.0)
    s.tun("uw_s", [(-78, 6), (-86, -14), (-104, -28), (-130, -32), (-152, -24), (-166, -8), (-170, 6)], 3.0)
    s.tun("uw_w", [(-151, 2), (-170, 6), (-188, 8), (-205, 10), (-214, 12)], 3.0)
    for i, (a, b) in enumerate([((-107, -13), (-100, -25)), ((-125, -21), (-128, -31.5)), ((-145, -12), (-156, -21))]): s.tun("uw_xc%d" % i, [a, b], 2.8)
    s.siding("uw_sd1", (-104, -28), (-130, -32), -7)
    s.slope_zone("uw_nb", [-196, -184, -172], [8.5, 7.8, 6.3], [21, 34], z0=0.5, dz=3.0, faces=[((-196, 34), (-200, 39)), ((-172, 34), (-168, 39))])
    s.through("uw_cr1", (-117, -31.5), (-117, -35.5)); s.through("uw_cr2", (-135, 24.6), (-135, 31.1))
    for i, (par, f, sd) in enumerate([("uw_s", 0.3, -1), ("uw_s", 0.8, 1), ("uw_w", 0.5, 1), ("uw_rim", 0.15, -1), ("uw_rim", 0.62, -1), ("uw_main", 0.5, 1)]):
        s.hide("hu_%d" % i, par, f, sd)
    # ── 동쪽: 긴 운반갱도(옛 갱구까지) · 북쪽 고리 · 남쪽 고리 · 기둥 사이 · 좁은 곁갱도 무리 · 노보리(위로)
    s.tun("ue_adit", [(62, 5), (78, 6)], 3.3, lz="D")
    s.tun("ue_main", [(78, 6), (95, 10), (115, 8), (135, 12), (155, 8), (175, 12), (200, 15)], 3.0)
    s.tun("ue_n", [(95, 10), (100, 28), (120, 36), (145, 34), (165, 30), (175, 12)], 3.0)
    s.tun("ue_s", [(78, 6), (85, -12), (105, -24), (135, -26), (160, -20), (180, -6), (200, 15)], 3.0)
    s.tun("ue_x1", [(115, 8), (118, 35.5)], 2.8); s.tun("ue_x2", [(135, 12), (135, -26)], 2.8); s.tun("ue_x3", [(152, 8.6), (150, 33)], 2.8)
    s.pillar_room(140, 172, -18, 3, 3, 7.0); s.tun("ue_pl0", [(150, 9), (150, 2.5)], 3.0); s.tun("ue_pl1", [(160, -20), (160, -17.5)], 3.0)
    s.tun("ue_nn_a", [(120, 36), (124, 46), (136, 50), (148, 46), (145, 34)], 2.4); s.tun("ue_nn_b", [(124, 46), (136, 43), (148, 46)], 2.4); s.tun("ue_nn_face", [(136, 50), (137, 56)], 2.4)
    s.slope_zone("ue_nb", [184, 196], [13, 14.5], [26, 38], z0=0.5, dz=3.0, faces=[((184, 38), (180, 43)), ((196, 38), (200, 43))])
    s.through("ue_cr1", (136.5, -8), (140.5, -8)); s.through("ue_cr2", (100, 20), (95.5, 22))
    for i, (par, f, sd) in enumerate([("ue_main", 0.35, 1), ("ue_n", 0.5, 1), ("ue_s", 0.4, -1), ("ue_s", 0.8, -1), ("ue_main", 0.8, -1)]):
        s.hide("he_%d" % i, par, f, sd)
    s.gaps += [(-160, 40, 0), (-95, -35, 0), (-205, 25, 0), (110, 44, 0), (170, -25, 0), (205, 0, 0)]
    s.ladders += [((-123, 24), "↓ 1편 (큰 굴 벽)"), ((-209, 10.9), "↓ 1편"), ((166, 30), "↓ 1편")]
    s.labels += [((-126, 58), "채굴적 (옛 캔 자리 — 기둥)"), ((-184, 43), "노보리 (위로)"), ((156, -22), "기둥 사이"), ((136, 60), "좁은 곁갱도 무리"), ((190, 47), "노보리 (위로)"),
                 ((0, 0), "골짜기 (땅 위) — 이 층은 서쪽 산 · 동쪽 산 속에 따로 있다")]
    s.hubs = [((-70, 11), "배전반"), ((70, 11), "배전반")]
    return s.finish()


# ═════════════════════════════════════════ 고칠 곳 ═════════════════════════════════════════
import repair_spots as rsp
REPAIR = rsp.LETTER
def repairs(s):
    """고칠 곳 자리 (규칙은 repair_spots.py — Blender 부스 맵과 같은 규칙) → [(종류, (x, y))]"""
    return [(k, q) for k, q, _ in rsp.spots(s.T, hubs=[(q, 0.0) for q, _ in s.hubs])]


# ═════════════════════════════════════════ 그림 ═════════════════════════════════════════
def draw(s, title, rows, out, districts=(), bounds=(), hull=None, hull_label=None, rep=()):
    from PIL import Image, ImageDraw, ImageFont
    SS = 2; W = 3000; TOP = 360
    xs_ = [p[0] for t in s.T for p in t[1]] + [r[1] for r in s.R] + [r[2] for r in s.R]; ys_ = [p[1] for t in s.T for p in t[1]] + [r[3] for r in s.R] + [r[4] for r in s.R]
    S1 = (W - 120) / (max(xs_) - min(xs_)); H = int(TOP + S1 * (max(ys_) - min(ys_)) + 90); S = S1 * SS
    img = Image.new("RGB", (W * SS, H * SS), "#2c2926"); d = ImageDraw.Draw(img)
    Fn = lambda sz, b=False: ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if b else "C:/Windows/Fonts/malgun.ttf", int(sz * SS))
    OX = W * SS / 2 - S * (max(xs_) + min(xs_)) / 2; OY = TOP * SS + S * max(ys_)
    P = lambda x, y: (OX + S * x, OY - S * y)
    COL = {"L": "#efd68e", "D": "#d6cdb6", "K": "#aaa290"}
    def poly(pts, w, col):
        q = [P(*p[:2]) for p in pts]; d.line(q, fill=col, width=max(1, int(w * S)), joint="curve")
        for X, Y in q: r = w * S / 2; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col)
    def rect(x0, x1, y0, y1, col, outline=None): d.rectangle([P(x0, y1), P(x1, y0)], fill=col, outline=outline, width=2 * SS if outline else 0)
    def dot(x, y, col, r=6): X, Y = P(x, y); r *= SS; d.ellipse([X - r, Y - r, X + r, Y + r], fill=col, outline="#1d1b19", width=SS)
    def txt(x, y, t_, sz=15, col="#f4f1ea", b=True, anchor="mm"): d.text(P(x, y), t_, font=Fn(sz, b), fill=col, anchor=anchor)
    def dashed(pts, col, w=3):
        q = [P(*p) for p in pts]
        for a_, b_ in zip(q, q[1:]):
            L_ = math.dist(a_, b_); n_ = max(1, int(L_ / (14 * SS)))
            for i in range(0, n_, 2): d.line([a_[0] + (b_[0] - a_[0]) * i / n_, a_[1] + (b_[1] - a_[1]) * i / n_, a_[0] + (b_[0] - a_[0]) * (i + 1) / n_, a_[1] + (b_[1] - a_[1]) * (i + 1) / n_], fill=col, width=w * SS)
    for (x0, y0, x1, y1, kd) in s.waters:
        if kd == "pool": rect(x0, x1, y0, y1, "#3468aa")
    for t in s.T:
        if t[6] == "tunnel": poly(t[1], t[1][0][3], "#cfc6b0" if t[1][0][3] > 10 else COL[t[5]])
    for r in s.R:
        if r[0] == "goaf": rect(r[1], r[2], r[3], r[4], "#4a4540")
        else: rect(r[1], r[2], r[3], r[4], "#7fd67f" if r[0] in ("plaza", "adit") else COL[r[7]])
    for x0, x1, y0, y1 in s.PIL: rect(x0, x1, y0, y1, "#3a3632")
    for (x0, y0, x1, y1, kd) in s.waters:                                   # 물이 찬 굴: 굴 위에 가로 물결 줄 (굴이 보이게)
        if kd == "flood":
            for yy in np.arange(y0, y1, 1.2): d.line([P(x0, yy), P(x1, yy)], fill="#3f7fcf", width=2 * SS)
    for (cx, cy, rx, ry, lab) in s.voids:
        X, Y = P(cx, cy); d.ellipse([X - rx * S, Y - ry * S, X + rx * S, Y + ry * S], fill="#141211", outline="#c9c1ad", width=3 * SS); txt(cx, cy, lab, 14, "#c9c1ad")
    for t in s.T:
        if t[6] == "niche": poly(t[1], 1.1, "#3d8fe0")
        if t[6] == "crawl": poly(t[1], 0.9, "#9ff0ff")
        if t[6] == "crevice": poly(t[1], 0.9, "#19d9c8" if t[0] in s.through else "#f04fbf")
        if t[6] == "crevice_room": poly(t[1], 1.4, "#f04fbf")
    for (x, y) in s.doors:
        X, Y = P(x, y); d.rectangle([X - 9 * SS, Y - 3 * SS, X + 9 * SS, Y + 3 * SS], fill="#ff7a1a")
    for g in s.gaps: dot(g[0], g[1], "#d33c2c", 7)
    for (x, y), lab in s.corpses:
        X, Y = P(x, y); d.rounded_rectangle([X - 14 * SS, Y - 6 * SS, X + 14 * SS, Y + 6 * SS], radius=6 * SS, fill="#cecfd4", outline="#78787f", width=SS); txt(x, y + 4, lab, 13, "#cecfd4")
    for (x, y), lab in s.exits:                                            # 맨 끝 갱구는 글자를 안쪽으로
        X, Y = P(x, y); d.rectangle([X - 12 * SS, Y - 8 * SS, X + 12 * SS, Y + 8 * SS], fill="#ff9e80")
        edge = x <= min(xs_) + 15 and "lm" or x >= max(xs_) - 15 and "rm" or "mm"
        txt(x + {"lm": -3, "rm": 3, "mm": 0}[edge], y - 6, lab, 13, "#ff9e80", anchor=edge)
    for kind, (x, y) in rep:
        X, Y = P(x, y); r = 9 * SS; d.ellipse([X - r, Y - r, X + r, Y + r], fill="#ff9a3c", outline="#1d1b19", width=SS)
        d.text((X, Y), REPAIR[kind], font=Fn(10, True), fill="#1d1b19", anchor="mm")
    for (x, y), lab in s.ladders:
        X, Y = P(x, y)
        for sg in (-1, 1): d.line([X + 6 * sg * SS, Y - 14 * SS, X + 6 * sg * SS, Y + 14 * SS], fill="#ffe066", width=3 * SS)
        for k in range(-2, 3): d.line([X - 6 * SS, Y + k * 6 * SS, X + 6 * SS, Y + k * 6 * SS], fill="#ffe066", width=2 * SS)
        d.text((X + 12 * SS, Y), lab, font=Fn(13, True), fill="#ffe066", anchor="lm")
    for (x, y), lab in s.labels: txt(x, y, lab, 15)
    if getattr(s, "fake_end", None): fe = s.fake_end; rect(fe[0] - 1.6, fe[0] + 1.6, fe[1] - 0.2, fe[1] + 1.4, "#ff9c7a")
    if any(r[0] == "plaza" for r in s.R): txt(0, 0, "케이지", 13, "#1d1b19")
    for x, lab in districts: txt(x, max(ys_) + 7, lab, 19, "#c9c1ad")
    for xb in bounds:
        X0, Y0 = P(xb, max(ys_) + 3); X1, Y1 = P(xb, min(ys_) - 3); yy = Y0
        while yy < Y1: d.line([X0, yy, X0, min(yy + 10 * SS, Y1)], fill="#6b645a", width=2 * SS); yy += 18 * SS
    if hull: dashed(hull, "#f5f5f5"); txt(*hull_label[0], hull_label[1], 15, "#f5f5f5")
    sx, sy = P(min(xs_), min(ys_) - 4); d.line([sx, sy, sx + 30 * S, sy], fill="#f4f1ea", width=3 * SS); d.text((sx + 15 * S, sy + 14 * SS), "30 m", font=Fn(13), fill="#f4f1ea", anchor="mm")
    d.text((30 * SS, 18 * SS), title, font=Fn(34, True), fill="#f4f1ea")
    cx = [30, 480, 900, 1330, 1760]
    for i, row in enumerate(rows):
        for j, c in enumerate(row):
            d.text((cx[j] * SS, (66 + i * 24) * SS), c, font=Fn(15 if i else 14, i == 0 or j == 0), fill="#efd68e" if i == 0 else ("#c9c1ad" if j == 0 else "#f4f1ea"))
    lx, ly = 2200, 70
    items = [("#7fd67f", "케이지 광장 · 갱구 안쪽"), ("#efd68e", "불 켜진 길·방"), ("#d6cdb6", "꺼진 전등 길"), ("#aaa290", "어두운 굴"), ("#cfc6b0", "큰 굴(트인 곳)"), ("#3a3632", "기둥(바위)"),
             ("#3d8fe0", "좁은 대피소"), ("#9ff0ff", "개구멍"), ("#19d9c8", "뚫린 바위 틈"), ("#f04fbf", "막힌 바위 틈(숨는 곳)"), ("#d33c2c", "큰 틈(괴물)"), ("#ffe066", "사다리 (괴물 못 오름)"),
             ("#141211", "구덩이·트인 아래"), ("#3468aa", "물"), ("#ff7a1a", "풍문(늘 닫기)"), ("#ff9e80", "갱구 · 출구")]
    for i, (c, t_) in enumerate(items):
        X, Y = (lx + (i % 2) * 400) * SS, (ly + (i // 2) * 22) * SS
        d.rectangle([X, Y - 7 * SS, X + 14 * SS, Y + 7 * SS], fill=c, outline="#6b645a"); d.text((X + 20 * SS, Y), t_, font=Fn(14), fill="#f4f1ea", anchor="lm")
    X, Y = lx * SS, (ly + 8 * 22 + 6) * SS; d.ellipse([X, Y - 8 * SS, X + 16 * SS, Y + 8 * SS], fill="#ff9a3c", outline="#1d1b19", width=SS)
    d.text((X + 22 * SS, Y), "고칠 곳 — 갱: 갱목 · 등: 전등 · 수: 배수관 · 환: 환기 · 공: 공기 호스 · 레: 레일 · 배: 배전반", font=Fn(14), fill="#f4f1ea", anchor="lm")
    img.resize((W, H), Image.LANCZOS).save(out); print("saved", out)


def stat_rows(cols, keys=("area", "hides", "small", "longest", "dead", "wander"), ref=None):
    """표 줄: cols = [(제목, 잰 값 dict, 고칠 곳 목록)]"""
    heads = ["", *[c[0] for c in cols]]
    f = {"area": ("걸을 수 있는 바닥", lambda r: "%.0f m² (MAP2 의 %.1f 배)" % (r["area"], r["area"] / ref["area"])),
         "hides": ("숨을 곳 (대피소 · 개구멍 · 바위 틈)", lambda r: "%d" % r["hides"]),
         "small": ("짧은 고리 (한 바퀴 60 m 이하)", lambda r: "%d" % r["small"]),
         "longest": ("갈림·숨을 곳 없는 가장 긴 굴", lambda r: "%.0f m (%s)" % (r["longest"], r["at"])),
         "dead": ("막다른 굴 가장 긴 것", lambda r: "%.0f m" % r["dead"]),
         "wander": ("길 잃고 300 m 안에 나가는 곳 (가운데값)", lambda r: "%.0f %% (%.0f m)" % (r["within300"], r["median"]))}
    rows = [heads] + [[f[k][0]] + [f[k][1](c[1]) + (c[3] if k == "area" and len(c) > 3 else "") for c in cols] for k in keys]
    rows.append(["고칠 곳"] + ["%d 곳" % len(c[2]) if c[2] is not None else "—" for c in cols])
    k0 = cols[0][2]
    rows.append(["고칠 곳 종류 (%s)" % cols[0][0], " · ".join("%s %d" % (k, sum(1 for kk, _ in k0 if kk == k)) for k in REPAIR if any(kk == k for kk, _ in k0))])
    return rows


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else None
    L1, L2, UP = build_l1(), build_l2(), build_up()
    r1 = mp.measure(L1.measure_dict(home_rect=L1.home_rect)); rb = mp.measure(booth_slice(L1))
    r2 = mp.measure(L2.measure_dict()); ru = mp.measure(UP.measure_dict(home_rooms=("adit",), home_rect=(-66, -58, 0, 10)))
    rm = mp.measure(mp.MAP2_V4)
    B2 = bt.build(crevices=True); cut = ("W_", "E_", "T_", "fake", "sd_arc", "sd_edge", "link12", "link23", "v_z1", "v_z3", "c_z1", "c_link12")    # MAP2 부스판 (map2_plan 과 같은 자름)
    rmb = mp.measure(dict(T=[t for t in B2["T"] if not t[0].startswith(cut)], small_gaps=[], home_rooms=("plaza",), home_rect=B2["home_rect"], through={c[0] for c in B2["crevices"] if c[1] == "through"},
                          R=[x for x in B2["R"] if not any(z["x0"] - 0.5 <= x[1] and x[2] <= z["x1"] + 0.5 and z["y0"] - 0.5 <= x[3] and x[4] <= z["y1"] + 6 for z in (B2["Z"]["Z1"], B2["Z"]["Z3"]))]))
    k1, k2, ku = repairs(L1), repairs(L2), repairs(UP)
    kb = [k for k in k1 if -161 <= k[1][0] <= 76 and -44 <= k[1][1] <= 49]
    for name, r, k in (("1편", r1, k1), ("1편 부스판", rb, kb), ("2편", r2, k2), ("윗 갱도", ru, ku), ("MAP2", rm, None)):
        print("%s: 바닥 %.0f m² · 굴 %.0f m · 짧은 고리 %d · 숨을 곳 %d · 가장 긴 %.0f m (%s) · 막다른 %.0f m (%s) · 300 m 안 %.0f %% · 가운데값 %.0f m%s"
              % (name, r["area"], r["length"], r["small"], r["hides"], r["longest"], r["at"], r["dead"], r["dead_at"], r.get("within300", -1), r.get("median", -1),
                 "" if k is None else " · 고칠 곳 %d" % len(k)))
    if outdir:
        hull = [(-161, -28), (-161, 28), (-121, 29), (-97, 33), (-66, 49), (76, 49), (76, -44), (-66, -44), (-97, -34), (-121, -31), (-161, -28)]
        draw(L1, "MAP3 안 A+B — 1편 평면 (가운데 MAP2 + 서쪽·동쪽 산 밑)", stat_rows([("1편 전체", r1, k1), ("부스판 조각", rb, kb, " · 부스판의 %.1f 배" % (rb["area"] / rmb["area"])), ("MAP2 (판정 받은 맵)", rm, None)], ref=rm),
             os.path.join(outdir, "MAP3_1편_평면.png"), districts=[(-128, "서쪽 산 밑 (새로)"), (0, "가운데 = MAP2 (사용자 손그림 그대로)"), (150, "동쪽 산 밑 (새로)")],
             bounds=(-63.5, 74), hull=hull, hull_label=((-112, -36), "부스판 조각 (혼자 3~5분) — 흰 점선 밖은 막는다"), rep=k1)
        draw(L2, "MAP3 안 A+B — 2편 평면 (가장 깊은 층 · 저수지 · 큰 굴 바닥 · 막아 둔 옛 갱도)", stat_rows([("2편", r2, k2), ("MAP2 (판정 받은 맵)", rm, None)], ref=rm),
             os.path.join(outdir, "MAP3_2편_평면.png"), districts=[(-150, "서쪽 (옛 갱도 쪽)"), (0, "가운데 (케이지 바닥 · 저수지)"), (150, "동쪽 (큰 굴 바닥)")], rep=k2)
        draw(UP, "MAP3 안 A+B — 윗 갱도 평면 (서쪽 산 속 · 동쪽 산 속, 골짜기 바닥보다 높다)", stat_rows([("윗 갱도 (서 + 동)", ru, ku), ("MAP2 (판정 받은 맵)", rm, None)], ref=rm),
             os.path.join(outdir, "MAP3_윗갱도_평면.png"), districts=[(-140, "서쪽 산 속"), (135, "동쪽 산 속")], rep=ku)
