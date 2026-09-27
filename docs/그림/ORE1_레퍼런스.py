# ORE-1 벽에 박힌 광석 — 조사 한 장 그림 (09-27). 문서 = docs/기획서/조사/12_막장_광맥_레퍼런스.md
# 사진은 build/refs/ore/ 에서 읽고, 그림도 build/refs/ore/ 에 쓴다 — 기록 사진·게임 화면이 들어가서
# 공개 저장소에 못 올린다(CLAUDE.md). 이 코드만 커밋한다.
#   python docs/그림/ORE1_레퍼런스.py            → build/refs/ore/ORE1_레퍼런스.png
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import sheet as S
from sheet import text, wrap, SS, C

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..", "build", "refs", "ore")
NOW_SHOT = os.path.join(HERE, "..", "..", "build", "check_m2c", "9_pick_at_wall.png")   # 09-14 캡처 — 광석은 지금과 같은 ore.gltf
OUT = os.path.join(ROOT, "ORE1_레퍼런스.png")
W, H = 2400, 4200
S.new(W, H)
NOW = (255, 154, 60)

def photo(x, y, w, h, path, cap, sz=16, hl=None):
    """사진을 w×h 칸에 맞춰 넣고 아래에 설명(여러 줄)."""
    S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], fill=(28, 26, 25))
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if os.path.exists(full):
        im = Image.open(full).convert("RGB"); k = min(w * SS / im.width, h * SS / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        S.img.paste(im, (int((x + (w * SS - im.width) / SS / 2) * SS), int((y + (h * SS - im.height) / SS / 2) * SS)))
    else:
        text(x + w / 2, y + h / 2, "(사진 없음)\n" + os.path.basename(path), 15, C["sub"], anchor="mm")
    if hl: S.d.rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS], outline=hl, width=4 * SS)
    yy = y + h + 6
    for i, ln in enumerate(cap.split("\n")):
        for piece in wrap(ln, sz, w):
            text(x + 2, yy, piece, sz, C["text"] if i == 0 else C["sub"]); yy += sz * 1.3

def section(y, title, sub=None):
    S.d.rectangle([20 * SS, y * SS, (W - 20) * SS, (y + 3) * SS], fill=(90, 84, 78))
    text(24, y + 10, title, 30, b=True)
    if sub: text(24 + S.d.textlength(title, font=S.F(30, True)) / SS + 18, y + 20, sub, 19, C["sub"])
    return y + 58

def row(y, items, cw=372, ch=250, gap=20, sz=16, capH=80):
    for i, it in enumerate(items):
        p_, c_ = it[0], it[1]
        photo(24 + i * (cw + gap), y, cw, ch, p_, c_, sz=sz, hl=(it[2] if len(it) > 2 else None))
    return y + ch + capH

# ───────────────────────── 그리기 ─────────────────────────
text(24, 16, "ORE-1 벽에 박힌 광석 — 실제 막장·탄층·광맥 조사 (09-27)", 36, b=True)
text(24, 64, "사진 = 기록·박물관·위키미디어·논문·게임 화면(비교용, build/refs 만). 한국 29 · 해외 34 · 게임 11장 중 24장. 크기는 사진 속 사람·손·망치와 견준 짐작.", 19, C["sub"])

# 0. 지금
y = section(110, "0. 지금 우리 게임 광석", "벽에 반쯤 박힌 둥근 검은 덩이 · 삼각형 276 · 27 × 18 × 22 cm · 쇠처럼 반짝 · 30곳 모두 바닥 위 약 1.4 m")
photo(24, y, 520, 292, NOW_SHOT, "ore.gltf (09-14 그대로)\n캡처는 09-14 — 벽·곡괭이·글자는 옛 모습", sz=16, hl=NOW)
bx = 24 + 520 + 40
facts = ["벽에 둥근 덩이가 박힌 모습: 한국 사진 0/29 · 해외 탄층 0/18 · 해외 광맥 벽 0/14.",
         "같은 방식은 게임 하나뿐 — Mining Simulator 2023(회색 돌 위 주황 반구, 아래 ④).",
         "기획서에 '광석이 무엇인지'는 없다. 옛 화면 글자는 '철 N'(09-16 UI-1c 에서 지움, 자리표시였음).",
         "ART-1 석탄 칠(벽에 가로로 긴 띠 9 m × 1.1 m)은 광석 자리와 따로 논다.",
         "MINE-1(합침): 누르고 있으면 콱마다 덩이가 6 cm 까지 밀려 나오고 25° 기울다 빠진다 — 이 움직임은 모양이 바뀌어도 그대로 쓸 수 있다."]
yy = y + 4
for ln in facts:
    for piece in wrap("· " + ln, 19, W - bx - 30):
        text(bx, yy, piece, 19); yy += 27
    yy += 6
y += 292 + 70

# 1. 한국 탄광
y = section(y, "① 한국 탄광 막장", "막장 면이 보이는 3장은 모두 벽 전체가 탄 — 탄층과 둘레 돌의 경계가 보이는 한국 사진은 0장")
y = row(y, [("k04_nculture_coalpick_face.jpg", "Rk04 광물자원공사 · 콜픽\n벽 전체 탄 · 결 30~45° 비스듬 · 날·줄 면 되풀이 · 젖은 듯 반짝"),
            ("k08_nculture_bongsan_pick_colonial.jpg", "Rk08 황해 봉산(일제강점기)\n평행한 금 45~60° · 길쭉한 블록 · 분필 X · 램프를 벽에 걺"),
            ("k03_nculture_archface_shovel.jpg", "Rk03 강철 아치 안 막장\n면 전체 탄 · 조명에 강하게 반짝 · 모난 판·덩이 2~40 cm"),
            ("k05_nculture_lowface_woodprops.jpg", "Rk05 낮은 채탄 막장\n천장 약 1.5 m · 통나무 동발 · 바닥 분탄이 반짝 점"),
            ("k25_archives_1992_lumps_in_hand.jpg", "Rk25 공보처 1992 · 손에 든 탄\n15~20 cm · 모나고 거칢 · 흰 가루 묻어 무광"),
            ("k14_sisain_2022_jangseong_sorting_lumps.jpg", "Rk14 장성 선탄장 2022\n모난 블록·판 10~25 cm · 큰 것 약 30 cm")])

# 2. 해외 탄층
y = section(y, "② 해외 탄층·막장", "갱 안 막장 벽이 바닥~천장 석탄 8/13 · 천장은 평평한 회색 판 돌 · 조명 받은 깨진 면 반짝 10/13")
y = row(y, [("w13_nara_fain1946_undercut.jpg", "Rw13 켄터키 1946 · 1.2~1.4 m 탄층\n벽돌처럼 네모로 갈라짐 · 평평한 판 돌 천장 · 밑 가로 틈"),
            ("w14_nara_fain1946_shotcoal.jpg", "Rw14 같은 곳 · 발파 직후\n모서리 날카로운 네모 덩이 · 큰 것 30~50 · 대부분 5~20 cm"),
            ("w01_commons_blegny_seam.jpg", "Rw01 벨기에 블레니 지하 30 m\n벽을 덮는 비스듬한 띠 약 30° · 위는 회색 판 돌 · 작은 반짝 점"),
            ("w19_doe1964_drillhole.jpg", "Rw19 미국 1964년경 · 약 1.4 m\n벽돌 쌓은 듯한 네모 조각 · 발파 구멍 지름 약 5 cm"),
            ("w17_iwm1942_coalface_load.jpg", "Rw17 영국 1942\n40~50 cm 덩이를 손으로 · 조명 받은 면만 흰 반사"),
            ("w10_commons_semianthracite_va.jpg", "Rw10 버지니아 반무연탄(바깥)\n60~70° 선 띠 · 낮빛에도 은빛 · 얇은 판·쐐기로 부서짐")])

# 3. 금속 광맥
y = section(y, "③ 금속 광맥 (참고 — 한국 탄전 안에서 나온다는 기록은 못 찾음)", "어두운 돌을 가로지르는 흰 석영 띠 5~30 cm · 녹 얼룩 · 보통 빛에서 금·은 알갱이 0/7")
y = row(y, [("k19_jinsan2015_fig3b_vertical_quartzvein.jpg", "Rk19 진산 금광 본갱(2015 논문)\n거의 수직 흰 석영맥 20~50 cm · 노랑·주황 녹"),
            ("k21_jinsan2015_fig3f_quartz_fluorite_rust.jpg", "Rk21 같은 논문 · 양하판\n흰 석영 + 연녹 형석 · 경계에 주황·갈색 녹 띠"),
            ("k16_jinsan2015_fig2b_quartzbreccia.jpg", "Rk16 진산 신갱\n불규칙한 흰 띠 10~20 cm + 부서진 조각 · 흐린 경계"),
            ("w22_commons_orphangirl_veins1.jpg", "Rw22 몬태나 뷰트\n휘어진 검은 맥 · 안에 녹슨 금빛 알갱이 덩이 둘(1/14)"),
            ("w30_geograph_kellymine_lode.jpg", "Rw30 영국 켈리 · 머리등 빛만\n빛 원 밖은 거의 어둠 · 1 cm 주황갈색 줄"),
            ("w28_muse_cinquevalli_fluorite.jpg", "Rw28 이탈리아 친퀘발리 형석 맥\n벽·천장 한 면 1 m 이상 · 결정면 반짝")])

# 4. 게임
y = section(y, "④ 게임은 어떻게 어둠 속 광석을 알아보게 하나", "색 대비 5/6 · 빛 받은 곳의 반짝임 4/6 · 스스로 빛남 2/6 · 둥근 덩이 반쯤 박힘 1/6")
y = row(y, [("g03_drg_goldvein.jpg", "Deep Rock Galactic 금\n벽에 붙은 납작한 띠 · 불 비추면 금속 광택"),
            ("g04_drg_morkite.jpg", "DRG 모르카이트\n벽 표면의 넓은 띠 · 빛 없이도 면이 반짝"),
            ("g05_rust_metalnode_sparkle.jpg", "Rust 금속 노드\n반짝이는 점(핫스팟) — 조명 없으면 안 보임"),
            ("g07_7dtd_coalore_underground.jpg", "7 Days to Die 석탄(옛 버전)\n어두운 바탕에 검은 덩이 · 손전등에 번쩍"),
            ("g01_valheim_copperdeposit.jpg", "Valheim 구리\n바위 덩이 · 노란 줄 · 조각마다 부서짐"),
            ("g10_miningsim_orelumps.jpg", "Mining Simulator 2023\n주황 반구가 반쯤 박힘 = 지금 우리 방식", NOW)])

# 5. 공통점 요약
y = section(y, "⑤ 공통점 — 모양을 정할 때 쓸 것", "n/전체 = 사진 수. 숫자 = 문서(출처는 조사 12)")
col1 = ["탄광: 탄은 막장(캐는 벽)에 있다 — 굴진·운반 갱도 벽은 돌(한국 5/14).",
        "막장 벽은 거의 다 석탄(한국 3/3 · 해외 8/13), 위 경계는 뚜렷한 평평한 판 돌(해외 12/18).",
        "석탄은 결 따라 모나게 갈라진다 — 해외 네모 7/18 · 한국 비스듬한 평행 금 30~60°.",
        "램프 빛을 받으면 깨진 면마다 반짝, 먼지·낮빛은 무광.",
        "떨어진 탄: 모난 덩이 + 가루, 대부분 5~20 cm · 큰 것 30~50 cm. 둥근 덩이 0.",
        "한국 탄층: 평균 두께 1.4 m(도계 2.0 · 장성 4.0), 경사 30~70°. 채탄 막장 3.9 × 2.7 m."]
col2 = ["금속 광맥: 어두운 돌 속 흰 석영 띠 5~30 cm(한국 6/7), 경계 뚜렷 반·흐림 반.",
        "녹 얼룩(해외 컬러 8/10) · 금·은 알갱이는 보통 빛에서 안 보임(0/7).",
        "게임: 어둠에서 광석을 알아보게 하는 것은 색 대비 · 빛 받은 반짝임 — 둥근 덩이가 아니다.",
        "머리등만 있으면 빛 원 밖은 거의 안 보인다(Rw30) — 우리 게임과 같은 조건.",
        "못 찾음: 한국 탄층-둘레 돌 경계 사진 · 무연탄 갱 안 막장 · 한국 탄전 속 금속 광맥 기록."]
yy0 = y
for cx, lines in ((24, col1), (24 + (W - 48) // 2 + 10, col2)):
    yy = yy0
    for ln in lines:
        for piece in wrap("· " + ln, 19, (W - 48) // 2 - 30):
            text(cx, yy, piece, 19); yy += 27
        yy += 6
    y = max(y, yy)
y_end = y + 40
S.img = S.img.crop((0, 0, W * SS, y_end * SS)).resize((W, y_end), Image.LANCZOS)
S.img.save(OUT)
print(OUT)
