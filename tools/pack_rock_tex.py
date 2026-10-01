"""TEX-1 바위 사진 묶기: blender/map/map4_tex.json 의 photos → Assets/Fab/Resources/Rock/<키>_DiffRough.png (색 + 알파 = 거칠기) · <키>_nor_gl.jpg (OpenGL 노멀), 2048².
  python tools/pack_rock_tex.py            (있는 파일은 건너뜀 · FORCE=1 이면 다시)
부스 바위 재질(MineRock)이 읽는 꼴과 같다 (Assets/Tunnel/Art/SOURCES.md). Fab 사진이 섞여 있어 폴더째 git 밖(/Assets/Fab/).
이름에 _rough · _arm 이 들어가면 TextureImportRules 가 색 그림을 sRGB 끔으로 읽는다 — 키는 w3 · f6 꼴만."""
import os, sys, json
from PIL import Image
import numpy as np
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); TT = os.path.join(ROOT, "build", "tex_test")
OUT = os.path.join(ROOT, "Assets", "Fab", "Resources", "Rock"); SIZE = 2048
def folder(spec):
    kind, _, rel = spec.partition(":")
    return os.path.join(TT, "cc0", rel) if kind == "cc0" else os.path.join(TT, rel) if kind == "tt" else os.path.join(TT, "fab", "mine_high", rel)
def maps(d):                                                               # blender/map/tex_compare.py maps() 와 같은 고르기
    fs = {f.lower(): os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith((".png", ".jpg", ".jpeg")) and not f.startswith("_")}
    pick = lambda keys, bad=(): next((p for f, p in sorted(fs.items()) if any(k in f for k in keys) and not any(b in f for b in bad)), None)
    return pick(("color", "albedo", "basecolor", "diff")), pick(("normalgl", "normal_gl", "nor_gl", "normal"), ("dx",)), pick(("rough",))
os.makedirs(OUT, exist_ok=True)
photos = json.load(open(os.path.join(ROOT, "blender", "map", "map4_tex.json"), encoding="utf-8"))["photos"]
for key, spec in photos.items():
    col, nor, rou = maps(folder(spec)); assert col and nor and rou, "FAIL: %s 에 색 · 노멀 · 거칠기가 없다 (%s)" % (key, folder(spec))
    a, b = os.path.join(OUT, key + "_DiffRough.png"), os.path.join(OUT, key + "_nor_gl.jpg")
    c = Image.open(col).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    lin = np.asarray(c, dtype=np.float64) / 255; lin = np.where(lin <= 0.04045, lin / 12.92, ((lin + 0.055) / 1.055) ** 2.4)
    print("CHECK pack %-4s %-22s lum %.3f  rgb %.3f %.3f %.3f" % (key, spec, float((lin @ np.array([0.2126, 0.7152, 0.0722])).mean()), *lin.reshape(-1, 3).mean(0)))
    if os.path.exists(a) and os.path.exists(b) and os.environ.get("FORCE") != "1": continue
    c.putalpha(Image.open(rou).convert("L").resize((SIZE, SIZE), Image.LANCZOS)); c.save(a)
    Image.open(nor).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS).save(b, quality=93)
print("CHECK pack_rock_tex %d photos -> %s" % (len(photos), OUT))
