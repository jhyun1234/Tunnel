"""곡괭이 타격 소리 겹쳐 만들기 (SND-P, 사용자 09-27 "후보 3·4·6 을 적절하게 섞으면").

  python tools/snd_mix.py            # build/refs/snd/mix/ 에 섞기별 타격 8개 + 들어 볼 줄(0.85 s 간격 6번)

재료(build/refs/snd/cand/, git 에서 뺌 — Pixabay 원본은 따로 나눠 주면 안 된다):
  딱  = 후보6 c13 Pixabay "Mine Stone with a Pickaxe"  — 첫 20 ms 높은 소리 57 %, 20~100 ms 에 −14 dB 로 빨리 끝남
  쿵  = 후보4 c16 Freesound CC0 "pickaxe.wav"           — 딱 뒤 20~300 ms 가 낮은 소리(60~400 Hz) 43~60 %, 셋 중 가장 천천히 줄어듦
  와작 = 후보3 c01 Freesound CC0 "Pick axe striking rocks #1" — 처음부터 중간·높은 소리 80 % 넘음 (부서지는 소리)
(60 Hz 아래 마이크 울렁임을 걷어 낸 뒤 잰 값)
타격마다 봉우리를 맞춰 겹친다. 섞기마다 딱·쿵·와작의 크기(dB)만 다르다.
"""
import os, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
sys.path.insert(0, os.path.dirname(__file__))
import snd_measure as m

SR = m.SR
CAND = "build/refs/snd/cand/"
OUT = "build/refs/snd/mix/"
SRC = {"딱": "c13_px_mine_stone_pickaxe.mp3", "쿵": "c16_fs_pickaxe_school.mp3", "와작": "c01_fs_pickaxe_rocks1.mp3"}
MIXES = {   # 이름: (딱, 쿵, 와작) dB — 각 타격을 먼저 같은 세기로 맞춘 뒤 더한다
    "섞기A_고르게": (0, 0, 0),
    "섞기B_묵직하게": (-12, 0, -6),   # 첫 판(-8, 0, -4)은 A 와 2 dB 차이라 귀로 가리기 어려웠다
    "섞기C_날카롭게": (0, -12, 0),
}
N = 8           # 섞기마다 만드는 타격 수 (게임에서 번갈아 쓴다)
LEN = 0.6       # 타격 하나 최대 길이 (s)


def hits(path):
    # 60 Hz 아래는 걷어 낸다 — 후보4 의 "낮은 소리 51 %" 는 88 % 가 40 Hz 밑(봉우리 11 Hz) 마이크 울렁임이었다(귀에 안 들리고 크기 맞추기만 망친다)
    x = sosfilt(butter(4, 60, "highpass", fs=SR, output="sos"), m.load(path)); hs = m.onsets(x); out = []
    for i, h in enumerate(hs):
        a = h - int(0.005 * SR)
        b = min(len(x), h + int(LEN * SR), hs[i + 1] - int(0.01 * SR) if i + 1 < len(hs) else len(x))
        s = x[a:b].copy()
        f = min(len(s), int(0.03 * SR)); s[-f:] *= np.linspace(1, 0, f)            # 끝 30 ms 줄여 딸깍 없앰
        p = int(np.argmax(np.abs(s[: int(0.03 * SR)])))                              # 봉우리 자리
        s /= np.sqrt((s[max(0, p - 200): p + int(0.08 * SR)] ** 2).mean()) + 1e-9     # 첫 80 ms 세기 = 1
        out.append((s, p))
    return out


def layer(parts):
    pk = max(p for _, p, _ in parts)
    n = max(pk - p + len(s) for s, p, _ in parts)
    y = np.zeros(n)
    for s, p, g in parts:
        o = pk - p; y[o:o + len(s)] += s * 10 ** (g / 20)
    return y


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(927)
    pool = {k: hits(CAND + v) for k, v in SRC.items()}
    print(" · ".join(f"{k} 타격 {len(v)}" for k, v in pool.items()))
    picks = [{k: rng.integers(len(v)) for k, v in pool.items()} for _ in range(N)]   # 섞기끼리 같은 조합 — 비율만 다르게 들린다
    for name, (gd, gk, gw) in MIXES.items():
        seq = np.zeros(int((0.85 * 5 + LEN + 0.2) * SR))
        for i, pk in enumerate(picks):
            y = layer([(*pool["딱"][pk["딱"]], gd), (*pool["쿵"][pk["쿵"]], gk), (*pool["와작"][pk["와작"]], gw)])
            y *= 0.5 / np.abs(y).max()
            wavfile.write(f"{OUT}{name}_{i}.wav", SR, (y * 32767).astype(np.int16))
            if i < 6:
                o = int(0.85 * i * SR + 0.1 * SR); seq[o:o + len(y)] += y
        wavfile.write(f"{OUT}{name}_들어보기.wav", SR, (seq / np.abs(seq).max() * 0.5 * 32767).astype(np.int16))
    # 비교: 겹치지 않고 셋을 번갈아(딱 → 쿵 → 와작 …)
    seq = np.zeros(int((0.85 * 5 + LEN + 0.2) * SR))
    for i in range(6):
        k = ["딱", "쿵", "와작"][i % 3]; s, _ = pool[k][picks[i][k]]
        o = int(0.85 * i * SR + 0.1 * SR); seq[o:o + len(s)] += s / np.abs(s).max()
    wavfile.write(f"{OUT}번갈아_들어보기.wav", SR, (seq / np.abs(seq).max() * 0.5 * 32767).astype(np.int16))


if __name__ == "__main__":
    main()
