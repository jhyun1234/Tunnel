"""제안서 TEX-1 그림: 맵을 위에서 보고 방마다 벽 · 바닥 사진 번호를 칠한다 (굽기 없이 설계 파일만으로).
  python docs/그림/MAP4_벽바닥_색칠지도.py   →  docs/그림/MAP4_벽바닥_색칠지도.png · MAP4_층별_질감표.png
환경 표(ENV)와 방 → 환경 표(ROOM)가 이 제안서의 내용이다. 승인되면 이 표를 blender/map/ 쪽으로 옮겨 굽기가 읽는다.
색 = 실제 사진의 평균 색 × 물들이는 곱 (사진은 build/tex_test — 없으면 회색)."""
import json, math, os
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TT = os.path.join(ROOT, "build", "tex_test"); FAB = os.path.join(TT, "fab", "mine_high"); CC0 = os.path.join(TT, "cc0")
# 벽 번호(비교 그림 MAP4_질감자료_rock.jpg) → (이름, 폴더, 곱) · 곱 = 그림 눈금에서 목표 밝기 약 0.20 (석탄 0.11) — 마지막 값은 실행 파일 키로
WALL = {2: ("Fab 바위벽 (어둡게)", os.path.join(FAB, "ueknfaclw"), 0.55), 3: ("Fab 바위벽", os.path.join(FAB, "ueknfaclw"), 0.70), 4: ("Fab 착암 자국", os.path.join(FAB, "uh1nbhzlw"), 0.52),
        5: ("Fab 회색 셰일", os.path.join(FAB, "uebmddyn"), 0.45), 6: ("Fab 갈색 층진 바위", os.path.join(FAB, "ueijag3ew"), 0.60), 7: ("Fab 석탄 부스러기", os.path.join(TT, "fab_coalground"), 1.0),
        8: ("Rock022 층진 셰일", os.path.join(CC0, "rock", "Rock022"), 0.50), 9: ("Rock050 짙은 회색", os.path.join(CC0, "rock", "Rock050"), 0.55), 10: ("dark_rock 검은 바위", os.path.join(CC0, "rock", "dark_rock"), 1.0),
        11: ("dark_rock_02 검은 셰일", os.path.join(CC0, "rock", "dark_rock_02"), 1.0)}
# 바닥 번호(MAP4_질감자료_floor.jpg) — 사용자가 번호를 따로 안 줬다: 아래 배치는 Claude 가 고른 것 (②~⑪ 안에서)
FLOOR = {2: ("Fab 석탄 부스러기", os.path.join(TT, "fab_coalground"), 1.0), 3: ("brown_mud_rocks_01 잔돌 흙", os.path.join(ROOT, "Assets", "Tunnel", "Pieces", "textures"), 0.75),
         4: ("Fab 어두운 진흙", os.path.join(FAB, "ud0nfezew"), 0.80), 5: ("Gravel040 돌 부스러기", os.path.join(CC0, "floor", "Gravel040"), 0.50), 6: ("Ground110 돌 박힌 흙", os.path.join(CC0, "floor", "Ground110"), 0.55),
         7: ("Rocks006 깬돌", os.path.join(CC0, "floor", "Rocks006"), 0.45), 9: ("brown_mud_02 젖은 흙", os.path.join(CC0, "floor", "brown_mud_02"), 0.75), 11: ("tarred_gravel 다져진 바닥", os.path.join(CC0, "floor", "tarred_gravel"), 0.85)}
# 환경 → (설명, 벽, 바닥, 더하는 것)
ENV = {
    "집":       ("불 켜진 곳 — 돌아오면 안심", 3, 11, ""),
    "집 물가":  ("펌프실 — 도랑물이 모이는 곳", 3, 4, "벽 아래 물 자국 띠"),
    "큰 길":    ("서쪽 운반갱도 — 집에서 뻗는 길", 2, 11, ""),
    "바위 굴":  ("단단한 바위를 뚫은 굴(착암 줄)", 4, 5, ""),
    "레일 마당": ("남쪽 조차장 — 레일 밑 깬돌", 4, 7, ""),
    "옛 굴 서": ("오래 버려진 곳(갈색 얼룩)", 6, 3, ""),
    "옛 굴 동": ("오래 버려진 곳(갈색 얼룩)", 6, 5, ""),
    "옛 굴 끝": ("물가로 가는 옛 길", 6, 9, ""),
    "탄층":     ("탄층 가까움(검은 셰일)", 11, 2, ""),
    "석탄 면":  ("막장 — 벽이 석탄", 7, 2, "천장 ⑧"),
    "단층":     ("층이 어긋난 방", 8, 6, ""),
    "무너짐":   ("갓 무너진 곳(깨진 회색 면)", 5, 6, ""),
    "그것의 굴": ("머리등 닿는 6 m 까지 회색, 위는 검정", 9, 6, "6 m 위 ⑩"),
    "물 고인 곳": ("가장 멀고 낮은 곳", 9, 4, "벽 아래 물 자국 띠"),
}
ROOM = {"z6": "집", "R0": "집", "L": "집", "H": "집", "P": "집 물가", "z3": "큰 길", "W1": "큰 길", "LW": "큰 길", "N0": "큰 길", "z7": "바위 굴", "E1": "바위 굴", "S1": "레일 마당", "LD": "레일 마당",
        "M": "옛 굴 서", "K2": "옛 굴 서", "MAG": "옛 굴 서", "E2": "옛 굴 동", "E4": "옛 굴 동", "E3": "옛 굴 동", "V": "옛 굴 동", "X": "옛 굴 동", "R2": "옛 굴 끝",
        "N1": "탄층", "N2": "탄층", "W2": "탄층", "z1": "탄층", "F": "탄층", "z2": "석탄 면", "N3": "단층", "z8": "무너짐", "K": "무너짐", "z9": "그것의 굴", "R1": "물 고인 곳"}
SHORT = {"P": "펌프실", "R0": "대기소", "L": "램프실", "W1": "서쪽 모임터", "W2": "갱목 쌓는 곳", "F": "막장 앞", "M": "옛 채굴 빈터", "K": "붕락 방", "K2": "갱목 창고", "S1": "광차 조차장", "LD": "사다리 굴",
         "H": "대피소", "R2": "선로 끝", "R1": "물 고인 옛 펌프장", "E1": "선풍기 방", "E2": "막아 둔 채굴적", "E4": "권양기 방", "E3": "광차 굽이", "V": "창고 칸 줄", "X": "배전실", "N0": "계단 방", "N1": "저탄장",
         "N2": "북쪽 막장", "N3": "단층 방", "z6": "⑥ 승강장", "z3": "③ 광차 싣는 곳", "z7": "⑦ 바람문", "z8": "⑧ 무너진 기둥", "z1": "① 쇠동발 숲", "z2": "② 채탄 막장", "z9": "⑨ 그것의 굴"}
SCENE_BOX = {"z6": (-8, -5, 8, 5), "z3": (-39.6, -2, -20, 4), "z7": (12, -4, 37, 2), "z8": (-93.9, 1, -74, 5), "z1": (-117, -51, -107, -9), "z2": (-115.5, -80, -108.5, -59), "z9": (112, -98.5, 138, -33.5)}
BOOTH = ("z6", "z3", "z7", "z1", "z8", "z2", "z9")                                   # 부스 조각 장면 (굵은 테두리)

def mean_col(d, mul, prefix=None):
    try:
        f = next(os.path.join(d, x) for x in sorted(os.listdir(d)) if any(k in x.lower() for k in ("color", "albedo", "basecolor", "diff")) and x.lower().endswith((".jpg", ".png")) and (prefix is None or x.lower().startswith(prefix)))
        c = np.asarray(Image.open(f).convert("RGB").resize((64, 64)), dtype=np.float32).reshape(-1, 3).mean(0) * mul
    except Exception: c = np.array([90, 90, 90]) * mul
    return tuple(int(min(255, v * 1.9 + 14)) for v in c)                              # 그림에서 서로 갈려 보이게 밝힘 (게임 밝기가 아니다)
# 사진 평균 색은 서로 너무 비슷해(전부 회갈색) 지도에서 안 갈린다 → 번호마다 알아보기 색 (사진 색이 아니다 — 범례의 작은 칸이 사진 평균 색)
WM = {k: mean_col(v[1], v[2]) for k, v in WALL.items()}; FM = {k: mean_col(v[1], v[2], "brown_mud_rocks_01" if k == 3 else None) for k, v in FLOOR.items()}
WC = {2: (150, 120, 80), 3: (205, 170, 110), 4: (190, 90, 70), 5: (200, 200, 205), 6: (200, 120, 40), 7: (25, 25, 28), 8: (110, 150, 190), 9: (110, 150, 110), 10: (70, 45, 90), 11: (50, 65, 110)}
FC = {2: (20, 20, 22), 3: (170, 140, 60), 4: (60, 110, 120), 5: (170, 170, 170), 6: (130, 100, 80), 7: (225, 225, 225), 9: (120, 90, 50), 11: (95, 95, 100)}
CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"
plan = json.load(open(os.path.join(ROOT, "blender", "map", "map4_plan.json"), encoding="utf-8"))
N = {n["id"]: n for n in plan["nodes"]}
S = 7.2; X0, Y1 = -128, 48; W, H = int((142 - X0) * S) + 20, int((Y1 + 116) * S) + 330
im = Image.new("RGB", (W, H), (22, 22, 24)); d = ImageDraw.Draw(im)
f1 = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 30); f2 = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 17); f3 = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)
px = lambda x, y: (int((x - X0) * S) + 10, int((Y1 - y) * S) + 60)
def box_of(k):
    if k in SCENE_BOX: return SCENE_BOX[k]
    n = N[k]; return (n["x"] - n["w"] / 2, n["y"] - n["d"] / 2, n["x"] + n["w"] / 2, n["y"] + n["d"] / 2)
def cen(k): b = box_of(k.split(".")[0]); return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
joins = []
for e in plan["edges"]:                                                               # 굴: 양 끝 환경의 벽 색으로 반반 — 다르면 '잇는 곳'
    if e["kind"] == "shaft": continue
    a, b = e["a"].split(".")[0], e["b"].split(".")[0]
    if a not in ROOM or b not in ROOM: continue
    pa, pb = cen(a), cen(b); m = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2); wa, wb = ENV[ROOM[a]][1], ENV[ROOM[b]][1]; fa, fb = ENV[ROOM[a]][2], ENV[ROOM[b]][2]
    d.line([px(*pa), px(*m)], fill=WC[wa], width=13); d.line([px(*m), px(*pb)], fill=WC[wb], width=13)
    d.line([px(*pa), px(*m)], fill=FC[fa], width=5); d.line([px(*m), px(*pb)], fill=FC[fb], width=5)
    if wa != wb or fa != fb: joins.append((m, math.dist(pa, pb), wa, wb, fa, fb))
for k, env in ROOM.items():
    if k not in N and k not in SCENE_BOX: continue
    if k in N and N[k]["kind"] == "closet": continue
    b = box_of(k); p0, p1 = px(b[0], b[3]), px(b[2], b[1]); w_, fl = ENV[env][1], ENV[env][2]
    d.rectangle([p0, p1], fill=WC[w_], outline=(255, 215, 120) if k in BOOTH else (10, 10, 10), width=5 if k in BOOTH else 2)
    g = max(6, int(min(p1[0] - p0[0], p1[1] - p0[1]) * 0.22)); d.rectangle([p0[0] + g, p0[1] + g, p1[0] - g, p1[1] - g], fill=FC[fl])   # 안쪽 = 바닥
    z = N[k]["z"] if k in N else {"z1": 3, "z2": 3}.get(k, 0)
    lab = "%s\n벽%s 바닥%s%s" % (SHORT.get(k, k), CIRC[w_ - 1], CIRC[fl - 1], ("  %+g m" % z) if z else "")
    tx, ty = (p0[0] + p1[0]) // 2, (p0[1] + p1[1]) // 2; bb = d.multiline_textbbox((0, 0), lab, font=f3, align="center")
    d.rectangle([tx - bb[2] // 2 - 3, ty - bb[3] // 2 - 2, tx + bb[2] // 2 + 3, ty + bb[3] // 2 + 3], fill=(0, 0, 0)); d.multiline_text((tx - bb[2] // 2, ty - bb[3] // 2), lab, font=f3, fill=(245, 245, 245), align="center")
for m, L, wa, wb, fa, fb in joins:
    p = px(*m); d.ellipse([p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7], fill=(255, 255, 255), outline=(0, 0, 0)); d.text((p[0] + 9, p[1] - 9), "%.0f m" % L, font=f3, fill=(255, 255, 255))
d.text((14, 12), "TEX-1 벽 · 바닥 색칠 지도 (제안) — 큰 네모 = 벽, 안쪽 네모 = 바닥, 흰 점 = 잇는 곳(굴 길이), 노란 테두리 = 부스 조각 장면. 색은 번호 알아보기용(사진 색 아님)", font=f2, fill=(240, 240, 240))
y = H - 262; d.text((14, y - 4), "벽 (사용자가 고른 ②~⑪)", font=f2, fill=(255, 210, 120)); d.text((W // 2, y - 4), "바닥 (Claude 가 고른 것 — 번호를 바꿔 달라)", font=f2, fill=(255, 150, 120))
for i, (k, v) in enumerate(WALL.items()):
    xx, yy = 14 + (i % 2) * 420, y + 26 + (i // 2) * 44; d.rectangle([xx, yy, xx + 40, yy + 34], fill=WC[k]); d.rectangle([xx + 40, yy, xx + 60, yy + 34], fill=WM[k]); d.text((xx + 68, yy + 6), "%s %s  ×%.2f" % (CIRC[k - 1], v[0], v[2]), font=f3, fill=(230, 230, 230))
for i, (k, v) in enumerate(FLOOR.items()):
    xx, yy = W // 2 + (i % 2) * 420, y + 26 + (i // 2) * 44; d.rectangle([xx, yy, xx + 40, yy + 34], fill=FC[k]); d.rectangle([xx + 40, yy, xx + 60, yy + 34], fill=FM[k]); d.text((xx + 68, yy + 6), "%s %s  ×%.2f" % (CIRC[k - 1], v[0], v[2]), font=f3, fill=(230, 230, 230))
im.save(os.path.join(ROOT, "docs", "그림", "MAP4_벽바닥_색칠지도.png")); print("map", im.size, "joins", len(joins))

# ---- 층 표 (제안 — 근거 문서 없음: 같은 열 장의 자리표와 젖음 · 어둡기만 바꾼다)
LV = [("환경", "1편 (붕락) — 이번에 짓는 것", "2편 (물)", "3편 (가스)", "막아 둔 층 (정전)"),
      ("승강장 둘레", "벽③ 바닥⑪", "벽⑨ 바닥⑪ · 물 자국", "벽⑪ 바닥⑪", "벽⑥ 바닥③ · 물 자국"),
      ("큰 길", "벽② 바닥⑪", "벽② 바닥⑨", "벽② 바닥⑪", "벽② 더 어둡게 · 바닥④"),
      ("옛 굴", "벽⑥ 바닥③ · ⑤", "벽⑥ 바닥⑨ · ④", "벽⑥ 바닥③", "벽⑥ 바닥④ (맵의 대부분)"),
      ("탄층 · 막장", "벽⑪ · ⑦ 바닥②", "벽⑪ 바닥②", "벽⑪ · ⑩ · ⑦ 바닥② (맵의 대부분)", "벽⑩ 바닥②"),
      ("무너진 곳", "벽⑤ 바닥⑥", "벽⑤ 바닥⑥", "벽⑤ 바닥⑥", "벽⑤ 바닥⑥"),
      ("물가", "벽⑨ 바닥④ (두 방)", "벽⑨ 바닥④ (맵의 대부분)", "—", "벽⑨ 바닥④"),
      ("젖음 · 물 자국 높이", "보통 · 0.35 m (물가 0.9 m)", "많이 · 1.5 m", "마름 · 없음", "보통 · 0.6 m"),
      ("쇠 (결정 4)", "철판, 물가만 녹슨 쇠", "승강장만 철판, 나머지 녹슨 쇠", "반반", "전부 녹슨 쇠 · 더 어둡게"),
      ("나무 (결정 3)", "거친 나무 + 검은 판자", "썩은 색 쪽으로", "거친 나무", "썩은 색 · 검은 판자 늘림")]
cw = [230, 400, 400, 400, 400]; rh = 46; im2 = Image.new("RGB", (sum(cw) + 20, rh * len(LV) + 70), (22, 22, 24)); d2 = ImageDraw.Draw(im2)
d2.text((12, 12), "TEX-1 층별 질감표 (제안 · 근거 문서 없음) — 새 사진을 더 받지 않고 같은 열 장의 자리와 젖음 · 어둡기만 바꾼다", font=f2, fill=(240, 240, 240))
for r, row in enumerate(LV):
    x = 10
    for c, t in enumerate(row):
        d2.rectangle([x, 50 + r * rh, x + cw[c] - 4, 50 + (r + 1) * rh - 4], fill=(52, 48, 40) if r == 0 else (40, 40, 44) if c == 0 else (34, 38, 34) if c == 1 else (30, 30, 34)); d2.text((x + 8, 50 + r * rh + 11), t, font=f2 if r == 0 or c == 0 else f3, fill=(255, 215, 130) if r == 0 else (235, 235, 235)); x += cw[c]
im2.save(os.path.join(ROOT, "docs", "그림", "MAP4_층별_질감표.png")); print("levels", im2.size)
