"""괴물이 틈에서 나오는 소리 섞기 (GAME-1 판정 7 · 8, 사용자 10-05 "돌가루 소리는 5개정도 묶어서 혼합").

  python tools/snd_emerge.py                    # build/refs/snd/emerge/mix/ 에 쓸 곳마다 섞기 A · B · C + 들어 볼 파일 넷
  python tools/snd_emerge.py --game B A A       # 고른 (돌가루 와르르 긁힘) → Assets/Audio/Emerge/Resources/*.ogg (사용자 10-05 "B A A")

재료 (build/refs/snd/emerge/, git 에서 뺌 — 출처 · 라이선스는 docs/기획서/조사/15_돌_부스러기_소리_후보.md, 모두 CC0):
  d1~d3 Sheyvan "Gravel Stone Dirt Debris Falling Small" 1 4 · 1 10 · 1 13   자갈이 졸졸 (7~8 kHz)
  d4    Wagna "sandfall5"                                                     고운 흙 · 먼지 (12 kHz)
  d5    Trancox "PiedraDesmoronandose"                                        돌이 부서져 내림 (앞 2 s)
  d6    lolamadeus "Gravel Impacts and Falls"                                 흘러내리는 덩어리 (4.5~7.0 s)
  b1 b2 iwanPlays "Stones Falling" · "Dropping Rocks"                          돌이 떨어져 구름 (4.2 s)
  b3 b4 Sheyvan "Stone Impact Rubble Debris" 1 · 3                            짧은 잔해 (밝음)
  b5    BigSoundBank "Fall of Stone"                                          돌무더기에 돌이 떨어짐 × 12
  s1    NahuelMartinez "Stone Slab Door Grinding"                            낮은 갈림 (709 Hz, 5~9 s 가 굵다)
  s2    BigSoundBank "Tombstone: Opening"                                     돌판이 미끄러짐
  s3    alegemaate "Stone Scrape"                                             짧은 긁힘
게임에서: 돌가루 = 출구에서 돌가루가 떨어지는 4 s(Director Warn) 동안 · 와르르 = 나오는 순간 · 긁힘 = 돌가루 밑에 낮게.
"""
import os, sys, subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, resample_poly
sys.path.insert(0, os.path.dirname(__file__))
import snd_measure as m

SR = m.SR
SRC = "build/refs/snd/emerge/"
OUT = SRC + "mix/"
GAME = "Assets/Audio/Emerge/Resources/"   # Director 가 Resources.Load 로 부른다 (씬을 짓는 BuildM1.cs 는 안 건드림)
WARN = 4.0          # Tuning.EMERGE_WARN_S
F = {
    "d1": "d1_fs_569737_gravel_small_1_4.mp3", "d2": "d2_fs_569743_gravel_small_1_10.mp3", "d3": "d3_fs_569746_gravel_small_1_13.mp3",
    "d4": "d4_fs_326304_sandfall5.mp3", "d5": "d5_fs_391919_piedra_desmoronandose.mp3", "d6": "d6_fs_179341_gravel_impacts_falls.mp3",
    "b1": "b1_fs_567251_stones_falling.mp3", "b2": "b2_fs_567250_dropping_rocks.mp3", "b3": "b3_fs_569497_rubble_debris_1.mp3",
    "b4": "b4_fs_569499_rubble_debris_3.mp3", "b5": "b5_bsb_1022_fall_of_stone.wav",
    "s1": "s1_fs_844329_stone_slab_grinding.mp3", "s2": "s2_bsb_0580_tombstone_opening.wav", "s3": "s3_fs_667284_stone_scrape.mp3",
}
_cache = {}


def src(k):
    if k not in _cache:
        x = m.load(SRC + F[k])
        _cache[k] = sosfilt(butter(4, 60, "highpass", fs=SR, output="sos"), x)   # 60 Hz 밑 마이크 울렁임 (SND-P 와 같다)
    return _cache[k]


def seg(x, t0, t1, fade=0.05):
    s = x[int(t0 * SR):int(t1 * SR)].copy()
    f = min(len(s) // 2, int(fade * SR))
    if f > 0:
        s[:f] *= np.linspace(0, 1, f); s[-f:] *= np.linspace(1, 0, f)
    return s


def lp(x, hz): return sosfilt(butter(4, hz, "lowpass", fs=SR, output="sos"), x)
def pitch(x, ratio): return resample_poly(x, 100, int(round(100 * ratio)))   # 높낮이와 빠르기를 같이 (ratio < 1 = 낮고 길게)
def rms_db(x): return 20 * np.log10(np.sqrt(np.mean(x * x)) + 1e-12)


def level(x, db=-24.0):
    """들어 보기용으로 크기를 맞춘다(평균 크기 db, 봉우리 -1 dBFS 넘지 않게). 게임 속 크기는 Tuning 이 정한다."""
    y = x * 10 ** ((db - rms_db(x)) / 20)
    pk = np.abs(y).max()
    return y * (10 ** (-1 / 20) / pk) if pk > 10 ** (-1 / 20) else y


def mix(length, parts):
    """parts = [(조각, 시작 s, dB)]"""
    out = np.zeros(int(length * SR))
    for s, t, db in parts:
        a = int(t * SR); s = s[:max(0, len(out) - a)]
        out[a:a + len(s)] += s * 10 ** (db / 20) / (np.sqrt(np.mean(s * s)) + 1e-12) * 0.05   # 조각마다 같은 크기에서 dB 만큼
    return out


def swell(x, start_db=-9.0, peak_at=0.9):
    """돌가루는 나오기 직전으로 갈수록 커진다 — 처음 start_db 에서 길이의 peak_at 까지 0 dB, 끝 0.15 s 줄임"""
    n = len(x); g = np.ones(n); p = int(n * peak_at)
    g[:p] = 10 ** (np.linspace(start_db, 0, p) / 20)
    f = int(0.15 * SR); g[-f:] *= np.linspace(1, 0, f)
    return x * g


def dust(v):
    d1, d2, d3, d4 = (src(k) for k in ("d1", "d2", "d3", "d4"))
    d5 = seg(src("d5"), 0.0, 2.2); d6 = seg(src("d6"), 4.5, 7.0, 0.1)
    if v == "A":   # 고르게: 자갈 셋을 어긋나게 + 먼지 + 부서짐 한 번
        x = mix(WARN, [(seg(d1, 0, 4.2), 0.0, 0), (seg(d2, 0.3, 4.3), 0.35, -1), (seg(d3, 0, 3.6), 0.8, -2), (seg(d4, 0.4, 4.4), 0.0, -12), (d5, 1.4, -4)])
    elif v == "B":  # 굵게: 부서짐 두 번 + 흘러내리는 덩어리
        x = mix(WARN, [(seg(d1, 0, 4.2), 0.0, -3), (seg(d2, 0, 4.0), 0.2, -6), (seg(d3, 0, 4.0), 0.5, -4), (d5, 0.5, 0), (d5, 2.5, -2), (d6, 1.6, -1)])
    else:           # 곱게: 먼지가 밑바탕, 자갈은 뒤로
        x = mix(WARN, [(lp(seg(d4, 0.3, 4.4), 9000), 0.0, 0), (seg(d1, 0, 4.2), 0.2, -6), (seg(d2, 0, 4.0), 0.9, -7), (seg(d3, 0, 3.4), 1.6, -8), (d5, 2.0, -12)])
    return swell(x)


def burst(v):
    if v == "A":   # 돌이 떨어져 구름
        x = seg(src("b1"), 0.0, 1.7, 0.25)
    elif v == "B":  # 떨어짐 + 짧은 잔해
        x = mix(1.6, [(seg(src("b2"), 0.0, 1.6, 0.25), 0.0, 0), (seg(src("b3"), 0.0, 1.0, 0.1), 0.04, -3)])
    else:           # 돌무더기에 큰 돌 하나 + 잔해
        x = mix(1.6, [(seg(src("b5"), 1.4, 2.9, 0.2), 0.0, 0), (seg(src("b4"), 0.0, 1.2, 0.1), 0.08, -6)])
    return x


def scrape(v):
    if v == "A":   # 낮은 갈림 그대로
        x = seg(src("s1"), 5.0, 5.0 + WARN, 0.6)
    elif v == "B":  # 돌판 미끄러짐을 낮게 (0.7 배)
        x = lp(seg(pitch(src("s2"), 0.7), 1.4, 1.4 + WARN, 0.6), 3000)
    else:           # 짧은 긁힘 둘을 낮게 (0.6 배)
        s = pitch(src("s3"), 0.6)
        x = mix(WARN, [(seg(s, 0, len(s) / SR, 0.1), 0.3, 0), (seg(s, 0, len(s) / SR, 0.1), 2.2, -2)])
    return x


def write(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


def together(dv, bv, sv, scrape_db=-9.0):
    """게임 순서 그대로: 돌가루 4 s (긁힘을 밑에) → 나오는 순간 와르르 → 1 s 여운"""
    d, b, s = level(dust(dv)), level(burst(bv)), level(scrape(sv))
    out = np.zeros(int((WARN + 2.6) * SR))
    out[:len(d)] += d; out[:len(s)] += s * 10 ** (scrape_db / 20)
    a = int(WARN * SR); out[a:a + len(b)] += b * 10 ** (3 / 20)    # 와르르는 3 dB 크게
    return level(out, -22.0)


def main(argv):
    gap = np.zeros(int(0.9 * SR)); V = "ABC"
    if argv[:1] == ["--game"]:
        dv, bv, sv = argv[1:4]
        os.makedirs(GAME, exist_ok=True)
        for name, x in (("emerge_dust_000", dust(dv)), ("emerge_burst_000", burst(bv)), ("emerge_scrape_000", scrape(sv))):
            tmp = OUT + name + ".wav"; write(tmp, level(x, -20.0))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ac", "1", "-ar", str(SR), "-c:a", "libvorbis", "-q:a", "5", GAME + name + ".ogg"], check=True)
            print("->", GAME + name + ".ogg")
        return
    for name, fn in (("돌가루", dust), ("와르르", burst), ("긁힘", scrape)):
        xs = [level(fn(v)) for v in V]
        for v, x in zip(V, xs): write(f"{OUT}{name}_{v}.wav", x)
        write(f"{OUT}비교_{name}_A_B_C.wav", np.concatenate(sum(([x, gap] for x in xs), [])))
    write(f"{OUT}비교_이어서_A_B_C.wav", np.concatenate(sum(([together(v, v, v), gap] for v in V), [])))
    print("->", OUT, "(비교_*.wav 는 A, 쉼, B, 쉼, C 순서)")


if __name__ == "__main__":
    main(sys.argv[1:])
