"""질감 비교(MAP4 규칙 6) — Meshy Retexture 로 시험 벽(곁갱도 12 m)에 질감을 한 번 입힌다. 유료(보통 10 크레딧) — 한 번만.
  python tools/tex_meshy.py build/tex_test/segment.glb build/tex_test/meshy/segment_meshy.glb
시험 벽은 blender/map/scene_mock.py (SCENE=t EXPORT=...) 로 만든다. 키: ~/.claude/.env_Meshy 의 MESHY_API_KEY (저장소 밖).
API: POST /openapi/v1/retexture (model_url = base64 data URI, text_style_prompt, enable_pbr, texture_resolution) → GET 으로 기다림 → glb 받기.
Meshy 는 결과를 며칠만 보관 — 끝나면 바로 받는다. 쓴 크레딧 · 글은 build/tex_test/meshy/log.txt 에 남긴다."""
import base64, json, pathlib, sys, time, urllib.request

API = "https://api.meshy.ai/openapi/v1/retexture"
KEY = dict(l.split("=", 1) for l in (pathlib.Path.home() / ".claude" / ".env_Meshy").read_text(encoding="utf-8-sig").splitlines() if "=" in l)["MESHY_API_KEY"].strip()
PROMPT = ("Dark, damp underground coal mine tunnel in 1980s Korea. Walls and ceiling of fractured black anthracite coal seams mixed with "
          "grey shale rock, coal dust, wet sheen in places. Floor of trampled black coal dust and mud. Realistic photographic detail.")
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); dst.parent.mkdir(parents=True, exist_ok=True)

def call(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method="POST" if body else "GET",
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: return json.loads(r.read())

tid = call(API, {"model_url": "data:application/octet-stream;base64," + base64.b64encode(src.read_bytes()).decode(),
                 "text_style_prompt": PROMPT, "enable_pbr": True, "texture_resolution": "4k", "remove_lighting": True,
                 "enable_original_uv": False, "target_formats": ["glb"]})["result"]
print("task", tid, flush=True)
while True:
    t = call(API + "/" + tid)
    if t["status"] in ("SUCCEEDED", "FAILED", "CANCELED"): break
    print(t["status"], t.get("progress"), flush=True); time.sleep(10)
with open(dst.parent / "log.txt", "a", encoding="utf-8") as f:
    f.write(f"{time.strftime('%Y-%m-%d %H:%M')} task {tid} {t['status']} credits {t.get('consumed_credits')} src {src.name}\n  {PROMPT}\n")
if t["status"] != "SUCCEEDED": sys.exit("FAILED %s" % t.get("task_error"))
urllib.request.urlretrieve(t["model_urls"]["glb"], dst)
print("OK", dst, dst.stat().st_size, "credits", t.get("consumed_credits"))
