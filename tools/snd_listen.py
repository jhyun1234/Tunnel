"""소리 후보를 귀로 고르게 같은 크기로 자른다 (SND-P). 원음은 건드리지 않고 크기만 한 번에 올리고 내린다.

  python tools/snd_listen.py 출력폴더 원본.mp3@시작초@길이초=이름 ...

- 크기 = LUFS(사람 귀 기준 평균 크기) -30. 짧게 "탁" 치는 소리는 평균에 비해 봉우리가 높아서 -20·-28 에 맞추면 넘쳐 찌그러졌다(09-27 후보 둘).
- 압축(loudnorm 동적)은 쓰지 않는다 — 타격의 날카로움이 바뀐다.
- 봉우리가 -1 dBFS 를 넘으면 경고만 한다(자르지 않음).
"""
import subprocess, sys, os, re

TARGET = -30.0


def run(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr


def lufs(path):
    return float(re.findall(r"^\s+I:\s+(-?[\d.]+) LUFS", run(["-i", path, "-af", "ebur128", "-f", "null", "-"]), re.M)[-1])


def peak(path):
    return float(re.findall(r"Peak level dB:\s+(-?[\d.inf]+)", run(["-i", path, "-af", "astats", "-f", "null", "-"]))[0])


def main(out, items):
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, "_raw.wav")
    for it in items:
        src, name = it.rsplit("=", 1)
        parts = src.split("@")
        cut = (["-ss", parts[1]] if len(parts) > 1 else []) + (["-t", parts[2]] if len(parts) > 2 else [])
        run(["-y", *cut, "-i", parts[0], "-ac", "1", "-ar", "44100", "-c:a", "pcm_f32le", tmp])
        g = TARGET - lufs(tmp)
        dst = os.path.join(out, name + ".wav")
        run(["-y", "-i", tmp, "-af", f"volume={g:.2f}dB", "-c:a", "pcm_s16le", dst])
        p = peak(tmp) + g
        print(f"{name}: {lufs(dst):.1f} LUFS, 봉우리 {p:.1f} dBFS" + ("  ← 넘침 주의" if p > -1 else ""))
    os.remove(tmp)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
