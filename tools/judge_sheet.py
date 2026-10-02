"""판정 재현 묶음 그림: 사용자 캡처 옆에 봇 캡처(68_shot_<앞머리>_NN_*.png)를 지적 번호마다 한 줄로.
  python tools/judge_sheet.py <나갈 그림 앞머리> <캡처 폴더> <사용자 캡처 폴더> [앞머리 j2] [한 장에 몇 줄 4]
지적 번호 → 사용자 캡처 번호는 CAP (10-03 판정 ②: 14번 지적 = 캡처 14 · 15, 그 뒤로 하나씩 밀린다)."""
import sys, os, glob, re
from PIL import Image, ImageDraw, ImageFont
out, D, U = sys.argv[1], sys.argv[2], sys.argv[3]; pre = sys.argv[4] if len(sys.argv) > 4 else "j2"; per = int(sys.argv[5]) if len(sys.argv) > 5 else 4
CAP = {14: [14, 15], 15: [16], 16: [17], 17: [18], 18: [19], 19: [20]}
f1 = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 18); f2 = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 13)
log = {}
lp = os.path.join(D, "shots.log")
if os.path.exists(lp):
    for l in open(lp, encoding="utf-8", errors="replace"):
        m = re.match(r"MAP4SHOT (\S+) (stand|fly) .* crouch (\w+) above (\S+) below (\S+) sees c (\S+)", l)
        if m: log[m.group(1)] = "가운데 %s%s" % (m.group(6)[:34], " · 숙임!" if m.group(3) == "True" else "")
rows = {}
for f in sorted(glob.glob(os.path.join(D, "68_shot_%s_*.png" % pre))):
    n = os.path.basename(f)[8:-4]; m = re.match(pre + r"_(\d\d)", n)
    if m: rows.setdefault(int(m.group(1)), []).append((n, f))
W, H, PAD, MAXC = 480, 270, 40, 6
keys = sorted(rows)
for s in range(0, len(keys), per):
    part = keys[s:s + per]; lines = []
    for k in part:
        cells = [("사용자 캡처 %d" % c, os.path.join(U, "%02d.jpg" % c), True) for c in CAP.get(k, [k])] + [(n, f, False) for n, f in rows[k]]
        for a in range(0, len(cells), MAXC): lines.append((k, cells[a:a + MAXC]))
    sh = Image.new("RGB", (W * MAXC, (H + PAD) * len(lines)), (14, 14, 16)); dr = ImageDraw.Draw(sh)
    for r, (k, cells) in enumerate(lines):
        for c, (n, f, user) in enumerate(cells):
            x, y = c * W, r * (H + PAD)
            if os.path.exists(f):
                im = Image.open(f).convert("RGB"); im.thumbnail((W, H)); sh.paste(im, (x + (W - im.width) // 2, y))
            dr.text((x + 6, y + H + 1), n, font=f1, fill=(255, 220, 60) if user else (240, 240, 240)); dr.text((x + 6, y + H + 22), "" if user else log.get(n, ""), font=f2, fill=(170, 170, 170))
    p = "%s_%d.jpg" % (out, s // per + 1); os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True); sh.save(p, quality=85); print(p.encode("unicode_escape").decode(), sh.size)
