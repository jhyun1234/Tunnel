# Poly Haven CC0 모델 후보 받기 (gltf 1k) → build/art/props_cand/<id>/
import json, os, sys, urllib.request
UA = {'User-Agent': 'TunnelArtFetch/1.0 (student game, CC0 assets)'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA))
OUT = "build/art/props_cand"
IDS = sys.argv[1:]
tot = 0
for i in IDS:
    d = json.load(get("https://api.polyhaven.com/files/" + i))
    g = d["gltf"]["1k"]["gltf"]
    os.makedirs(os.path.join(OUT, i), exist_ok=True)
    files = [(g["url"], os.path.basename(g["url"]))] + [(v["url"], k) for k, v in g.get("include", {}).items()]
    for url, rel in files:
        p = os.path.join(OUT, i, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.exists(p): open(p, 'wb').write(get(url).read())
        tot += os.path.getsize(p)
    print(i, len(files), "files")
print("total MB", round(tot / 1e6, 1))
