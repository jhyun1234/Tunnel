# 맵 그물 점 위치가 옛 glTF 와 같은가 (ART-1: art UV 만 더해야 한다) — python tools/cmp_booth_pos.py <옛 폴더> <새 폴더> (각 폴더에 booth_map.gltf/.bin)
import json, sys, hashlib, os
def load(d):
    g = json.load(open(os.path.join(d, "booth_map.gltf"), encoding="utf-8")); b = open(os.path.join(d, "booth_map.bin"), "rb").read()
    def acc(i):
        a = g["accessors"][i]; bv = g["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]] * a["count"] * (4 if a["componentType"] == 5126 else 2 if a["componentType"] in (5123, 5122) else 1)
        o = bv.get("byteOffset", 0) + a.get("byteOffset", 0); return b[o:o + n]
    out = {}
    for m in g["meshes"]:
        for k, p in enumerate(m["primitives"]):
            out[(m["name"], k)] = {at: hashlib.md5(acc(i)).hexdigest() for at, i in p["attributes"].items()} | {"IDX": hashlib.md5(acc(p["indices"])).hexdigest()}
    return out
old, new = load(sys.argv[1]), load(sys.argv[2])
assert old.keys() == new.keys(), "FAIL: 메시 목록이 다름"
bad = [(k, at) for k in old for at in ("POSITION", "NORMAL", "TEXCOORD_0", "IDX") if at in old[k] and old[k][at] != new[k].get(at)]
art = sum("TEXCOORD_1" in v for v in new.values())
print("CHECK art pos: prims %d · changed POSITION/NORMAL/TEXCOORD_0/indices %d · with TEXCOORD_1 %d" % (len(new), len(bad), art), bad[:5])
assert not bad
