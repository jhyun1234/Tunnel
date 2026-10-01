"""TEX-1 판정용 묶음 그림 (quick.sh map4 가 찍은 build/Tunnel/check/ 에서):
  python tools/tex1_sheets.py [캡처 폴더]
→ docs/그림/MAP4_벽잇기_게임.jpg  이음 자리(64_map4_seam*) — 굴 가운데 4 m 앞에서 굴을 따라 본 모습, 칸마다 어느 방에서 어느 방으로
→ docs/그림/MAP4_벽사진_1.5m.jpg  벽 사진마다 머리등 켜고 1.5 m 앞(65_map4_burn_w*) — 하얗게 탄 몫은 검사 map4_no_burn 이 잰다
앞뒤 밝기 숫자 · 넓은 방 앞뒤 그림은 build/check_map4/bright_compare.py (git 밖)."""
import sys, os, glob
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "Tunnel", "check")
f1 = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 24); f2 = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 19)
NAME = {"P": "펌프실", "R0": "대기소", "L": "램프실", "W1": "서쪽 모임터", "W2": "갱목 쌓는 곳", "F": "막장 앞", "M": "옛 채굴 빈터", "K": "붕락 방", "K2": "갱목 창고", "S1": "광차 조차장", "H": "대피소", "R2": "선로 끝",
        "R1": "옛 펌프장", "E1": "선풍기 방", "E2": "막아 둔 채굴적", "E3": "광차 굽이", "V": "창고 칸 줄", "X": "배전실", "N0": "계단 방", "N1": "저탄장", "N2": "북쪽 막장", "N3": "단층 방",
        "door": "앞문 틀", "chute": "석탄 홈통", "z6": "승강장", "z3": "광차 싣는 곳", "z7": "바람문", "z8": "무너진 기둥", "z1": "쇠동발 숲", "z2": "채탄 막장", "z9": "그것의 굴"}
WALL = {3: "③ Fab 바위벽", 4: "④ 착암 자국", 5: "⑤ 회색 셰일", 6: "⑥ 갈색 바위", 7: "⑦ 석탄", 8: "⑧ 층진 셰일", 9: "⑨ 짙은 회색", 11: "⑪ 검은 셰일"}
def sheet(files, label, title, out, cols=3, W=800, H=450):
    if not files: print("no captures for", out); return
    sh = Image.new("RGB", (W * cols, 56 + ((len(files) + cols - 1) // cols) * (H + 36)), (14, 14, 16)); dr = ImageDraw.Draw(sh); dr.text((14, 12), title, font=f1, fill=(240, 240, 240))
    for i, f in enumerate(files):
        x, y = (i % cols) * W, 56 + (i // cols) * (H + 36); sh.paste(Image.open(f).convert("RGB").resize((W, H)), (x, y)); dr.text((x + 10, y + H + 5), label(os.path.basename(f)[:-4]), font=f2, fill=(255, 210, 120))
    sh.save(os.path.join(ROOT, "docs", "그림", out), quality=88); print(out.encode("unicode_escape").decode(), sh.size, len(files))
def seam(n): p = n.split("_"); return "%s → %s" % (NAME.get(p[3], p[3]), NAME.get(p[4], p[4]))
sheet(sorted(glob.glob(os.path.join(D, "64_map4_seam*.png"))), seam, "TEX-1 이음 자리 — 환경이 바뀌는 굴 가운데 4 m 앞에서 (실행 파일 -map4, [ ] 키로 같은 자리에 선다)", "MAP4_벽잇기_게임.jpg", cols=4, W=640, H=360)
sheet(sorted(glob.glob(os.path.join(D, "65_map4_burn_w*.png")), key=lambda f: int(os.path.basename(f)[14:-4])), lambda n: "벽 " + WALL.get(int(n[14:]), n[14:]), "TEX-1 벽 사진마다 — 머리등 켜고 벽 1.5 m 앞 (처음 어둡기 값)", "MAP4_벽사진_1.5m.jpg", cols=4, W=640, H=360)
