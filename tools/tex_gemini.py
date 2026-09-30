"""질감 비교(MAP4 규칙 6, 사용자 09-30 "셋 다 실제로 해 보고 비교") — Gemini 로 반복 질감 후보 한 장.
  python tools/tex_gemini.py <이름> [--model gemini-3.1-flash-image]
키: ~/.claude/.env 의 GEMINI_API_KEY (저장소 밖). 유료 — 한 번에 한 장만 만들고, 사람이 본 뒤 다음을 정한다.
출력: build/tex_test/gemini/<이름>.png + prompts.log(글 전문 · 모델 · 날짜). 글은 GPT(ChatGPT 창)와 같은 것을 쓴다 — 공정한 비교."""
import argparse, datetime, os, pathlib, sys
from google import genai
from google.genai import types

PROMPT = ("Seamless tileable texture, photographed straight-on (orthographic, no perspective) of a dark, damp underground coal mine "
          "tunnel wall in 1980s Korea: fractured black anthracite coal seams mixed with grey shale rock, coal dust, wet sheen in places. "
          "Even, flat, shadowless lighting. No objects, no people, no text. Square image, fills the whole frame.")
ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--model", default="gemini-3.1-flash-image"); a = ap.parse_args()
for l in (pathlib.Path.home() / ".claude" / ".env").read_text(encoding="utf-8-sig").splitlines():
    if "=" in l: k, v = l.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
out = pathlib.Path(__file__).resolve().parent.parent / "build" / "tex_test" / "gemini"; out.mkdir(parents=True, exist_ok=True)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])      # 변수에 잡아 둔다 — 한 줄로 쓰면 요청 전에 닫힌다
r = client.models.generate_content(
    model=a.model, contents=[PROMPT],
    config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1", image_size="2K")))
parts = [p for p in r.candidates[0].content.parts if p.inline_data]
if not parts: sys.exit("no image: %s" % r)
p = out / (a.name + ".png"); p.write_bytes(parts[0].inline_data.data)
with open(out / "prompts.log", "a", encoding="utf-8") as f:
    f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M} {p.name} model={a.model} size=2K\n  {PROMPT}\n")
print("OK", p, p.stat().st_size)
