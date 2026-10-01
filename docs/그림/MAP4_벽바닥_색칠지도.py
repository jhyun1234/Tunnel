"""제안서 TEX-1 그림: 맵을 위에서 보고 방마다 벽 · 바닥 사진 번호를 칠한다 (굽기 없이 설계 파일만으로).
  python docs/그림/MAP4_벽바닥_색칠지도.py   →  docs/그림/MAP4_벽바닥_색칠지도.png · MAP4_층별_질감표.png
환경 표와 방 → 환경 표는 blender/map/map4_tex.json 에서 읽는다 (승인 10-01 뒤 그리로 옮겼다 — 굽기 scene_mock.py 가 같은 표를 읽는다).
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
# 바닥 번호(MAP4_질감자료_floor.jpg) — 벽마다 후보를 같은 굴에 나란히 찍어 가장 이어져 보이는 것으로 골랐다 (docs/그림/MAP4_바닥고르기.jpg, 사용자 10-01 "벽과 바닥이 자연스럽게 이어지는 텍스쳐를 고르면 된다"). 곱 = Tuning.MAP4_FLOOR_DARK 처음 값
FLOOR = {2: ("Fab 석탄 부스러기", os.path.join(TT, "fab_coalground"), 1.0), 4: ("Fab 어두운 진흙", os.path.join(FAB, "ud0nfezew"), 0.85), 6: ("Ground110 돌 박힌 흙", os.path.join(CC0, "floor", "Ground110"), 0.35),
         7: ("Rocks006 깬돌", os.path.join(CC0, "floor", "Rocks006"), 0.32), 10: ("brown_mud_03 진흙 자국", os.path.join(CC0, "floor", "brown_mud_03"), 0.47), 12: ("terrain_red_01 붉은 자갈", os.path.join(CC0, "floor", "terrain_red_01"), 0.87)}
TEXJ = json.load(open(os.path.join(ROOT, "blender", "map", "map4_tex.json"), encoding="utf-8"))
# 환경 → (설명, 벽, 바닥, 더하는 것). 큰 길 = 벽 ② (③ 과 같은 사진을 더 어둡게 — 표에는 dim)
ENV = {k: (e["name"], 2 if e.get("dim") else e["wall"], e["floor"], " · ".join(x for x in ("천장 " + "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"[e["roof"] - 1] if "roof" in e else "", "벽 아래 물 자국 띠" if "band" in e else "", "탄층 띠" if "coalband" in e else "") if x)) for k, e in TEXJ["env"].items() if k != "lairhigh"}
ROOM = dict(TEXJ["room"], **TEXJ["scene"])
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
WM = {k: mean_col(v[1], v[2]) for k, v in WALL.items()}; FM = {k: mean_col(v[1], v[2]) for k, v in FLOOR.items()}
WC = {2: (150, 120, 80), 3: (205, 170, 110), 4: (190, 90, 70), 5: (200, 200, 205), 6: (200, 120, 40), 7: (25, 25, 28), 8: (110, 150, 190), 9: (110, 150, 110), 10: (70, 45, 90), 11: (50, 65, 110)}
FC = {2: (20, 20, 22), 4: (60, 110, 120), 6: (130, 100, 80), 7: (225, 225, 225), 10: (120, 90, 50), 12: (150, 60, 45)}
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
d.text((14, 12), "TEX-1 벽 · 바닥 색칠 지도 (맵에 구운 표 map4_tex.json) — 큰 네모 = 벽, 안쪽 네모 = 바닥, 흰 점 = 잇는 곳(굴 길이), 노란 테두리 = 부스 조각 장면. 색은 번호 알아보기용(사진 색 아님)", font=f2, fill=(240, 240, 240))
y = H - 262; d.text((14, y - 4), "벽 (사용자가 고른 ②~⑪)", font=f2, fill=(255, 210, 120)); d.text((W // 2, y - 4), "바닥 (벽마다 나란히 찍어 고른 것 — MAP4_바닥고르기.jpg)", font=f2, fill=(255, 150, 120))
for i, (k, v) in enumerate(WALL.items()):
    xx, yy = 14 + (i % 2) * 420, y + 26 + (i // 2) * 44; d.rectangle([xx, yy, xx + 40, yy + 34], fill=WC[k]); d.rectangle([xx + 40, yy, xx + 60, yy + 34], fill=WM[k]); d.text((xx + 68, yy + 6), "%s %s  ×%.2f" % (CIRC[k - 1], v[0], v[2]), font=f3, fill=(230, 230, 230))
for i, (k, v) in enumerate(FLOOR.items()):
    xx, yy = W // 2 + (i % 2) * 420, y + 26 + (i // 2) * 44; d.rectangle([xx, yy, xx + 40, yy + 34], fill=FC[k]); d.rectangle([xx + 40, yy, xx + 60, yy + 34], fill=FM[k]); d.text((xx + 68, yy + 6), "%s %s  ×%.2f" % (CIRC[k - 1], v[0], v[2]), font=f3, fill=(230, 230, 230))
im.save(os.path.join(ROOT, "docs", "그림", "MAP4_벽바닥_색칠지도.png")); print("map", im.size, "joins", len(joins))

# ---- 층 표 (제안 — 근거 문서 없음: 같은 열 장의 자리표와 젖음 · 어둡기만 바꾼다)
LV = [("환경", "1편 (붕락) — 이번에 짓는 것", "2편 (물)", "3편 (가스)", "막아 둔 층 (정전)"),
      ("승강장 둘레", "벽③ 바닥⑥", "벽⑨ 바닥⑥ · 물 자국", "벽⑪ 바닥⑩", "벽⑥ 바닥⑦ · 물 자국"),
      ("큰 길", "벽② 바닥⑥", "벽② 바닥⑩", "벽② 바닥⑥", "벽② 더 어둡게 · 바닥④"),
      ("옛 굴", "벽⑥ 바닥⑦ · ⑫ · ⑩", "벽⑥ 바닥⑩ · ④", "벽⑥ 바닥⑦", "벽⑥ 바닥④ (맵의 대부분)"),
      ("탄층 · 막장", "벽⑪ 바닥⑩ · 벽⑦ 바닥②", "벽⑪ 바닥⑩", "벽⑪ · ⑩ · ⑦ 바닥⑩ · ② (맵의 대부분)", "벽⑩ 바닥②"),
      ("무너진 곳", "벽⑤ 바닥⑦", "벽⑤ 바닥⑦", "벽⑤ 바닥⑦", "벽⑤ 바닥⑦"),
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
