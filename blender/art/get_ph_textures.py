# Poly Haven CC0 질감 받기 (1k jpg: 색 · 거칠기 · 노멀 GL) → build/art/cand_tex/<id>_{Color,Roughness,NormalGL}.jpg (texture_candidates · prop_textures 가 읽는 이름)
#   python blender/art/get_ph_textures.py pine_bark rough_wood ...
import json, os, sys, urllib.request
UA = {'User-Agent': 'TunnelArtFetch/1.0 (student game, CC0 assets)'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "art", "cand_tex")
for i in sys.argv[1:]:
    d = json.load(get("https://api.polyhaven.com/files/" + i))
    for key, suf in (("Diffuse", "Color"), ("Rough", "Roughness"), ("nor_gl", "NormalGL")):
        p = os.path.join(OUT, "%s_%s.jpg" % (i, suf))
        if not os.path.exists(p): open(p, "wb").write(get(d[key]["1k"]["jpg"]["url"]).read())
    print(i, "ok")
