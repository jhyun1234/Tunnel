"""Freesound CC0 원본(hq ogg 미리듣기)에서 한 소리씩 잘라 Assets/Audio/Player/ 에 넣는다 (제안서 S1).
쓰는 법: python tools/cut_sounds.py <원본 폴더>   — 원본은 저장소에 없다(SOURCES.txt 의 URL 에서 다시 받는다).
자르기: 10 ms 창 RMS 가 최대의 THRESH 배를 넘는 순간을 시작으로, 다음 시작 전 또는 MAXLEN 까지. 앞 20 ms 여유, 끝 50 ms 페이드. mono 44.1 kHz ogg q5.
같은 원본이면 같은 파일이 나온다(무작위 없음)."""
import os, sys, subprocess, numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), "..", "Assets", "Audio", "Player")
# (원본 파일, 출력 이름, 몇 개, 최대 길이 s, 문턱, 소리 사이 최소 간격 s — 튄 소리를 새 시작으로 안 세게, ffmpeg 필터)
# 착지는 짧은 딱 소리라 최대값을 맞춰도 RMS 가 타격음의 1/4 — 리미터로 2.5배 올린다(사다리 "착지 ≤ 타격/2" 를 음량 1.0 안에서 맞추려고)
CUTS = [
    ("walk_389454.ogg", "step_dirt", 4, 0.55, 0.25, 0.25, "anull"),
    ("crouch_504383.ogg", "step_crouch", 1, 1.3, 0.15, 2.0, "anull"),   # 발 끄는 소리 1.2 s 통째로 (숙이기 간격 1.2 s 와 맞물린다)
    ("land_426848.ogg", "pick_land", 2, 1.4, 0.25, 1.0, "alimiter=level_in=2.5:limit=0.95:level=false"),
    # pick_flesh 는 아래 MIX 로 만든다 (사용자 09-16 3차: 단일 파일 24개 다 "타격감 없음" → 두 소리를 겹친 것 중 04 선택)
]
# 겹쳐 만드는 소리: (출력 이름, [(원본, pitch, 저역만 남길 Hz 또는 None, 세기, 시작 지연 s)])
MIXES = [
    ("pick_flesh", [("thud_276600.ogg", 0.7, 700, 1.0, 0.0),      # 몸에 맞는 둔탁음을 낮게·먹먹하게 — '퍽'
                    ("flesh_321810.ogg", 1.0, None, 0.7, 0.0)]),  # 손으로 막는 소리 — 살 닿는 '탁'
]

def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()

def onsets(a, thresh, min_gap=0.25):
    win = int(0.01 * SR)
    env = np.sqrt(np.convolve(a * a, np.ones(win) / win, mode="same"))
    limit = env.max() * thresh
    found, i = [], 0
    while i < len(env):
        if env[i] > limit and (not found or i - found[-1] > min_gap * SR):
            found.append(i)
            i += int(min_gap * SR)
        else:
            i += 1
    return found

def load_for_mix(path, pitch, lowpass):
    af = f"asetrate={int(SR * pitch)},aresample={SR}" + (f",lowpass=f={lowpass}" if lowpass else "")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-af", af, "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32).copy()
    env = np.abs(a)
    on = int(np.argmax(env > env.max() * 0.2))                       # 소리가 시작되는 곳에 맞춘다 — 겹칠 때 같은 순간에 나게
    a = a[max(0, on - int(0.005 * SR)):][:int(1.2 * SR)]
    return a / max(np.abs(a).max(), 1e-6)

def write(path, clip):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "libvorbis", "-q:a", "5", path],
                   input=clip.astype(np.float32).tobytes(), check=True)

def main(src):
    os.makedirs(OUT, exist_ok=True)
    for out, parts in MIXES:
        clips = [(load_for_mix(os.path.join(src, name), pitch, lp), gain, delay) for name, pitch, lp, gain, delay in parts]
        n = max(int(d * SR) + len(c) for c, _, d in clips)
        mix = np.zeros(n + int(0.05 * SR), np.float32)
        for c, gain, delay in clips:
            i = int(delay * SR)
            mix[i:i + len(c)] += c * gain
        mix /= max(np.abs(mix).max(), 1e-6) / 0.9
        path = os.path.join(OUT, f"{out}_000.ogg")
        write(path, mix)
        print(f"  {os.path.basename(path)} {len(mix) / SR:.2f} s  rms {np.sqrt(np.mean(mix ** 2)):.3f}  (mix of {len(parts)})")
    for name, out, count, maxlen, thresh, gap, filt in CUTS:
        a = decode(os.path.join(src, name))
        on = onsets(a, thresh, gap)
        print(f"{name}: {len(on)} onsets at", [f"{o / SR:.2f}" for o in on])
        for k in range(min(count, len(on))):
            s = max(0, on[k] - int(0.02 * SR))
            e = min(len(a), on[k] + int(maxlen * SR), on[k + 1] - int(0.02 * SR) if k + 1 < len(on) else len(a))
            clip = a[s:e].copy()
            fade = min(int(0.05 * SR), len(clip))
            clip[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
            clip /= max(np.abs(clip).max(), 1e-6) / 0.9              # 파일마다 최대값 0.9 — 음량은 Tuning 이 정한다
            path = os.path.join(OUT, f"{out}_{k:03d}.ogg")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", filt, "-c:a", "libvorbis", "-q:a", "5", path],
                           input=clip.tobytes(), check=True)
            rms = np.sqrt(np.mean(clip ** 2))
            print(f"  {os.path.basename(path)} {len(clip) / SR:.2f} s  rms {rms:.3f}")

if __name__ == "__main__":
    main(sys.argv[1])
