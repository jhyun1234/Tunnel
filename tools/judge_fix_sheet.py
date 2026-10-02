"""판정 지적마다 한 줄: 사용자 캡처 | 고치기 전 봇 캡처 | 고친 뒤 (같은 자리) | 고친 뒤 (곁들임).
  python tools/judge_fix_sheet.py <나갈 그림 앞머리> <고치기 전 폴더> <고친 뒤 폴더> <사용자 캡처 폴더> [한 장에 몇 줄 11]
ROWS = (지적 번호, 한 줄 설명, 사용자 캡처 번호 또는 None, 같은 자리 캡처 이름, 곁들임 캡처 이름 또는 None) — 10-03 판정 ②."""
import sys, os
from PIL import Image, ImageDraw, ImageFont
out, B, A, U = sys.argv[1:5]; per = int(sys.argv[5]) if len(sys.argv) > 5 else 11
ROWS = [
    (1, "승강장 바닥의 판", 1, "j2_01_plate", "j2_01_puddle_gate"), (2, "펌프 밑 판 · 관이 어디로 가나", 2, "j2_02_pump", "j2_02_rising_z6"), (3, "전화기 · 전선", 3, "j2_03_view", "j2_03_wide"),
    (4, "게시판 · 입갱표", 4, "j2_04_view", "j2_04_tags"), (5, "광차 싣는 곳 · 관", 5, "j2_05_loading", "j2_05_chute"), (6, "서쪽 모임터", 6, "j2_06_user", "j2_06_carts"),
    (7, "무너진 기둥 (안 고침 — 물을 것)", 7, "j2_07_user", None), (8, "채탄 막장 끝", 8, "j2_08_face_user", "j2_08_look_back"), (9, "옛 채굴 빈터의 기둥", 9, "j2_09_user", "j2_09_close"),
    (10, "돌 무더기", 10, "j2_10_pileA", "j2_10_pileB"), (11, "출입금지 뒤", 11, "j2_11_fence_user", "j2_11_fence_behind"), (12, "붕락 방 더미 · 천장", 12, "j2_12_k_east", "j2_31_chim_K"),
    (13, "두 나무 기둥", 13, "j2_13_user", "j2_13_raising"), (14, "단층 방 벽", 14, "j2_14_user", "j2_14_rake"), (15, "북쪽 막장", 16, "j2_15_n2face_user", "j2_15_n2_rail"),
    (16, "쇠동발", 17, "j2_16_props_user", "j2_16_props_head"), (17, "저탄장 더미", 18, "j2_17_n1_pile", "j2_17_n1_pile_s"), (18, "천 덮인 광차와 레일", 19, "j2_18_tarp_r2", "j2_18_n1_rail"),
    (19, "램프실", 20, "j2_19_view", "j2_19_lamps_L"), (21, "대피소 드럼통", None, "j2_21_barrels", None), (22, "선로 끝 돌 무더기", None, "j2_22_r2", "j2_17_r2_pile"),
    (23, "옛 펌프장 · 물", None, "j2_23_r1", "j2_23_r1_water"), (24, "큰 빈터 광차 · 암석", None, "j2_24_z9rocks", "j2_24_z9cart2"), (25, "권양기 방", None, "j2_25_winch", "j2_25_e4_slope"),
    (26, "막아 둔 채굴적", None, "j2_11_e2_user", "j2_11_e2_behind"), (27, "선풍기 · 바람 관", None, "j2_27_fan", None), (28, "풍문의 관", None, "j2_28_z7", "j2_28_z7_b"),
    (29, "창고 칸", None, "j2_29_v2", "j2_29_stall4"), (30, "배전실", None, "j2_30_x", "j2_30_x_tr"), (31, "괴물이 나올 곳 (새로 지음)", None, "j2_31_gap_K", "j2_31_gap_in_M"),
]
W, H, PAD = 640, 360, 34
f1 = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 20); f2 = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)
def cell(sh, dr, x, y, path, label, col):
    if path and os.path.exists(path): im = Image.open(path).convert("RGB"); im.thumbnail((W, H)); sh.paste(im, (x + (W - im.width) // 2, y))
    else: dr.text((x + 20, y + H // 2 - 10), "(파일 없음)" if path else "(둘째 묶음 캡처는 대화에만 있다)", font=f2, fill=(120, 120, 120))
    dr.text((x + 6, y + H + 4), label, font=f1, fill=col)
for s in range(0, len(ROWS), per):
    part = ROWS[s:s + per]; sh = Image.new("RGB", (W * 4, (H + PAD) * len(part)), (14, 14, 16)); dr = ImageDraw.Draw(sh)
    for r, (k, what, cap, shot, extra) in enumerate(part):
        y = r * (H + PAD); p = lambda d, n: os.path.join(d, "68_shot_%s.png" % n)
        cell(sh, dr, 0, y, os.path.join(U, "%02d.jpg" % cap) if cap else None, "%d. %s — 사용자 캡처" % (k, what), (255, 220, 60))
        cell(sh, dr, W, y, p(B, shot), "고치기 전 (%s)" % shot, (200, 200, 200))
        cell(sh, dr, W * 2, y, p(A, shot), "고친 뒤", (150, 255, 150))
        if extra: cell(sh, dr, W * 3, y, p(A, extra), "고친 뒤 (%s)" % extra, (150, 255, 150))
    path = "%s_%d.jpg" % (out, s // per + 1); sh.save(path, quality=84); print(path.encode("unicode_escape").decode(), sh.size)
