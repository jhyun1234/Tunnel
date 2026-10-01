"""봇 캡처 묶음 그림 (quick.sh map4shots 가 찍은 build/Tunnel/check/68_shot_*.png):
  python tools/shot_sheet.py <나갈 그림> [이름 앞머리] [캡처 폴더]
이름이 jNN_ 으로 시작하면(판정 지적 재현) 그 줄 맨 앞에 사용자 캡처 build/judge_1002/NN.webp 를 같이 놓는다 — 같은 자리인지 눈으로 견준다.
칸 밑 글자 = 캡처 이름 + 로그(build/quick_map4shots.log)의 "화면 가운데 물체 · 숙였나"."""
import sys, os, glob, re
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1]; pre = sys.argv[2] if len(sys.argv) > 2 else ""; D = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "build", "Tunnel", "check")
f1 = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 20); f2 = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 15)
log = {}
lp = os.path.join(ROOT, "build", "quick_map4shots.log")
if os.path.exists(lp):
    for l in open(lp, encoding="utf-8", errors="replace"):
        m = re.match(r"MAP4SHOT (\S+) (stand|fly) .* crouch (\w+) above (\S+) below (\S+) sees c (\S+)", l)
        if m: log[m.group(1)] = "가운데 %s%s" % (m.group(6), " · 숙임!" if m.group(3) == "True" else "")
files = sorted(glob.glob(os.path.join(D, "68_shot_%s*.png" % pre)))
rows = {}; rest = 0                                                    # jNN → 한 줄, 나머지는 다섯 장씩
for f in files:
    n = os.path.basename(f)[8:-4]; m = re.match(r"j(\d\d)", n)
    if m: rows.setdefault(m.group(1), []).append((n, f))
    else: rows.setdefault("x%03d" % (rest // 5), []).append((n, f)); rest += 1
W, H, PAD = 640, 360, 44
cols = max(len(v) + (1 if not k.startswith("x") else 0) for k, v in rows.items()) if rows else 1
sh = Image.new("RGB", (W * cols, (H + PAD) * len(rows)), (14, 14, 16)); dr = ImageDraw.Draw(sh)
for r, (k, shots) in enumerate(rows.items()):
    x = 0; y = r * (H + PAD)
    if not k.startswith("x"):
        u = os.path.join(ROOT, "build", "judge_1002", k + ".webp")
        if os.path.exists(u):
            im = Image.open(u).convert("RGB"); im.thumbnail((W, H)); sh.paste(im, (x + (W - im.width) // 2, y)); dr.text((x + 8, y + H + 2), "사용자 캡처 %d" % int(k), font=f1, fill=(255, 220, 60))
        x += W
    for n, f in shots:
        sh.paste(Image.open(f).convert("RGB").resize((W, H)), (x, y)); dr.text((x + 8, y + H + 2), n, font=f1, fill=(240, 240, 240)); dr.text((x + 8, y + H + 24), log.get(n, ""), font=f2, fill=(170, 170, 170)); x += W
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True); sh.save(out, quality=86); print(out.encode("unicode_escape").decode(), sh.size, len(files))
