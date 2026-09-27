"""곡괭이 타격 소리 재기 (SND-P). 파일마다 타격을 찾아 한 번 한 번을 같은 잣대로 잰다.

  python tools/snd_measure.py a.ogg b.m4a ...        # 표 출력
  python tools/snd_measure.py --csv out.csv files...  # 표 + CSV
  python tools/snd_measure.py --top 8 real/*.wav      # 현장 녹음: 가장 날카로운 8 번만

잣대 (타격 = 소리가 갑자기 커진 순간):
  ring_db    가장 도드라진 음(300~8000 Hz)이 옆 소리보다 얼마나 튀나 (dB). 크면 "팅" — 음이 있다
  ring_s     그 음이 봉우리에서 20 dB 떨어질 때까지 (s). 길면 "팅~" 하고 울린다
  decay_s    전체 소리가 봉우리에서 30 dB 떨어질 때까지 (s). 짧으면 "퍽"
  bright_hz  첫 50 ms 소리의 무게중심 (Hz). 낮으면 둔탁, 높으면 날카로움
  tail_db    150~600 ms 뒤 소리 크기 − 첫 50 ms (dB). 부스러기가 떨어지면 덜 작아진다
  tail_noise 그 뒤 소리가 쏴~ 하는 잡음인가 (0 음 ~ 1 잡음, spectral flatness)
현장 녹음은 말소리·바람이 섞이니 한 번 한 번보다 가운데값(median)을 본다.
"""
import subprocess, sys, csv
import numpy as np
from scipy.signal import stft, butter, sosfilt

SR = 44100


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(float)


def env_db(x, win=int(0.005 * SR)):
    e = np.sqrt(np.convolve(x * x, np.ones(win) / win, "same")) + 1e-9
    return 20 * np.log10(e)


def onsets(x, top=0):
    """타격 = 높은 소리(2~10 kHz)가 20 ms 안에 12 dB 넘게 뛴 순간 — 말소리는 이 대역에서 이렇게 빨리 안 뛴다.
    0.3 s 안에는 하나만. top > 0 이면 가장 크게 뛴 top 개만 (현장 녹음에서 곡괭이가 가장 날카롭다)."""
    hp = sosfilt(butter(4, [2000, 10000], "bandpass", fs=SR, output="sos"), x)
    e = env_db(hp, int(0.003 * SR))
    floor = e.max() - 35
    d, step = int(0.02 * SR), int(0.002 * SR)
    cand, i = [], d
    while i < len(e) - d:
        jump = e[i] - e[i - d:i].min()
        if e[i] > floor and jump > 12:
            j = i + int(np.argmax(e[i:i + d]))
            cand.append((jump, j)); i = j + int(0.3 * SR); continue
        i += step
    if top:
        cand = sorted(cand, reverse=True)[:top]
    return sorted(j for _, j in cand)


def measure(x, pk, end):
    seg = x[max(0, pk - int(0.01 * SR)):end]
    e = env_db(seg); p = np.argmax(e[: int(0.04 * SR)])
    below = np.where(e[p:] < e[p] - 30)[0]
    decay = below[0] / SR if len(below) else (len(e) - p) / SR
    f, t, Z = stft(seg, SR, nperseg=1024, noverlap=896); A = np.abs(Z) + 1e-12
    t0 = t[0] + p / SR
    band = (f > 300) & (f < 8000)
    early = (t >= t0 + 0.03) & (t <= t0 + 0.15)
    ring_db = ring_s = 0.0
    if early.any():
        spec = 20 * np.log10(A[:, early].mean(1))
        spec = np.maximum(spec, spec[(f > 300) & (f < 8000)].max() - 50)   # 잡음 바닥을 50 dB 아래로 맞춘다 — 조용한 합성음과 시끄러운 현장 녹음을 같은 잣대로
        sb = spec[band]; fb = f[band]
        k = np.argmax(sb - np.array([np.median(sb[max(0, i - 15):i + 16]) for i in range(len(sb))]))
        ring_db = float(sb[k] - np.median(sb[max(0, k - 15):k + 16]))
        line = 20 * np.log10(A[np.where(f == fb[k])[0][0]])
        i0 = np.argmax(line); drop = np.where(line[i0:] < line[i0] - 20)[0]
        ring_s = float(t[i0 + drop[0]] - t[i0]) if len(drop) else float(t[-1] - t[i0])
    head = seg[p: p + int(0.05 * SR)]
    H = np.abs(np.fft.rfft(head * np.hanning(len(head)))); fh = np.fft.rfftfreq(len(head), 1 / SR)
    bright = float((H * fh).sum() / H.sum())
    tail = seg[p + int(0.15 * SR): p + int(0.6 * SR)]
    tail_db, flat = -99.0, 0.0
    if len(tail) > 1024:
        tail_db = float(10 * np.log10((tail ** 2).mean() + 1e-12) - 10 * np.log10((head ** 2).mean() + 1e-12))
        T = np.abs(np.fft.rfft(tail * np.hanning(len(tail))))[(np.fft.rfftfreq(len(tail), 1 / SR) > 200)] + 1e-12
        flat = float(np.exp(np.log(T).mean()) / T.mean())
    return dict(ring_db=ring_db, ring_s=ring_s, decay_s=decay, bright_hz=bright, tail_db=tail_db, tail_noise=flat)


def main(argv):
    out, top = None, 0
    while argv[:1] and argv[0].startswith("--"):
        if argv[0] == "--csv": out = argv[1]
        if argv[0] == "--top": top = int(argv[1])   # 현장 녹음: 가장 날카로운 N 번만
        argv = argv[2:]
    rows = []
    keys = ["ring_db", "ring_s", "decay_s", "bright_hz", "tail_db", "tail_noise"]
    print(f"{'파일':40s} {'타격':>4s} " + " ".join(f"{k:>10s}" for k in keys))
    for path in argv:
        x = load(path)
        hs = onsets(x, top) or [int(np.argmax(np.abs(x)))]
        ms = []
        for i, h in enumerate(hs):
            end = min(len(x), (hs[i + 1] - int(0.02 * SR)) if i + 1 < len(hs) else h + int(0.8 * SR), h + int(0.8 * SR))
            ms.append(measure(x, h, end))
        med = {k: float(np.median([m[k] for m in ms])) for k in keys}
        name = path.replace("\\", "/").split("/")[-1][-40:]
        print(f"{name:40s} {len(hs):4d} " + " ".join(f"{med[k]:10.2f}" for k in keys))
        rows.append(dict(file=path, hits=len(hs), **med))
    if out:
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["file", "hits"] + keys); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1:])
