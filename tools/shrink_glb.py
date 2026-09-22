"""GLB 속 그림 중 한 변이 MAX(2048) 넘는 것을 MAX 로 줄인다 (제안서 m3-④, 09-22 승인). Blender·재질·UV 는 안 건드린다 — 굽기 마지막에 GLB 만 다시 쓴다.
  python tools/shrink_glb.py Assets/Tunnel/Monster/miner_m3.glb [MAX]
검사(PASS/FAIL 출력, FAIL 이면 종료 코드 1): ① 그림 한 변 ≤ MAX 전부 ② GLB ≤ 85 MB(실측 76.9 — 2K 노멀 PNG 가 장당 6.4~7.2 MB, 제안서 추정 5 보다 크다) ③ 그림 장수·재질 그림 참조 그대로.  사보타주: SABOTAGE=skip(줄이지 않음) -> ①② FAIL"""
import sys, os, io, json, struct
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")

path = sys.argv[1]; MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
SABOTAGE = os.environ.get("SABOTAGE", "")
d = open(path, "rb").read()
assert d[:4] == b"glTF", "GLB 아님"
jlen = struct.unpack_from("<I", d, 12)[0]; js = json.loads(d[20:20 + jlen])
blen = struct.unpack_from("<I", d, 20 + jlen)[0]; bo = 20 + jlen + 8; blob = d[bo:bo + blen]
before = len(d); n_img = len(js.get("images", [])); refs_before = json.dumps(js["materials"], sort_keys=True)

# 버퍼를 통째로 다시 짠다: 그림이 아닌 bufferView 는 그대로 복사, 그림 bufferView 는 줄인 바이트로
chunks = []; off = 0
img_bv = {im["bufferView"]: i for i, im in enumerate(js.get("images", [])) if "bufferView" in im}
shrunk = []
for bi, bv in enumerate(js["bufferViews"]):
    s0 = bv.get("byteOffset", 0); data = blob[s0:s0 + bv["byteLength"]]
    if bi in img_bv and SABOTAGE != "skip":
        im = Image.open(io.BytesIO(data)); w, h = im.size
        if max(w, h) > MAX:
            f = MAX / max(w, h); im2 = im.resize((max(1, round(w * f)), max(1, round(h * f))), Image.LANCZOS)
            out = io.BytesIO()
            if im.format == "JPEG":
                im2.save(out, "JPEG", quality=92)
            else:
                im2.save(out, "PNG", optimize=True)
            shrunk.append("%s %dx%d→%dx%d %.1f→%.1f MB" % (js["images"][img_bv[bi]].get("name", bi), w, h, im2.size[0], im2.size[1], len(data) / 1e6, len(out.getvalue()) / 1e6))
            data = out.getvalue()
    while off % 4:
        chunks.append(b"\0"); off += 1
    bv["byteOffset"] = off; bv["byteLength"] = len(data); chunks.append(data); off += len(data)
blob2 = b"".join(chunks)
while len(blob2) % 4:
    blob2 += b"\0"
js["buffers"][0]["byteLength"] = len(blob2)
jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
while len(jb) % 4:
    jb += b" "
out = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(jb) + 8 + len(blob2)) + struct.pack("<I", len(jb)) + b"JSON" + jb + struct.pack("<I", len(blob2)) + b"BIN\0" + blob2
open(path, "wb").write(out)
for s_ in shrunk:
    print("  줄임", s_)

# 검사 — 다시 읽어서
d = open(path, "rb").read(); jlen = struct.unpack_from("<I", d, 12)[0]; js2 = json.loads(d[20:20 + jlen]); bo = 20 + jlen + 8
sizes = []
for im in js2.get("images", []):
    bv = js2["bufferViews"][im["bufferView"]]; sizes.append(max(Image.open(io.BytesIO(d[bo + bv["byteOffset"]:bo + bv["byteOffset"] + bv["byteLength"]])).size))
fails = 0
def check(ok, msg):
    global fails
    print(("PASS  " if ok else "FAIL  ") + msg); fails += 0 if ok else 1
check(sizes and max(sizes) <= MAX, "shrink_glb: 그림 %d장 한 변 최대 %d (≤ %d)" % (len(sizes), max(sizes) if sizes else 0, MAX))
check(len(d) <= 85e6, "shrink_glb: GLB %.1f MB (≤ 85; 전 %.1f)" % (len(d) / 1e6, before / 1e6))
check(len(js2.get("images", [])) == n_img and json.dumps(js2["materials"], sort_keys=True) == refs_before, "shrink_glb: 그림 %d장 · 재질 그림 참조 그대로" % n_img)
sys.exit(1 if fails else 0)
