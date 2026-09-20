#!/usr/bin/env bash
# 쇼츠 2편: "네 발 괴물 5번 만들고 5번 다 버렸다 → 그래서 세웠다" (MA_V1·V3·V5 각 4.37 s "다 아니다" 판정 + UP_U4 6.9 s "일단 통과")
# 다섯 다 넣으면 돌진이 지루하다(판정 09-20) — 서로 가장 다르게 생긴 셋만 넣는다.
# 입력: build/check_3d4/MA_V*.mp4 · UP_U4.mp4 (blender/anim/preview_video.py · preview_upright.py 가 만든다)
# 출력: build/shorts/short_ma.mp4 (1080x1920, 30 fps, TTS 대본 + 합성 브금 — tools/short_audio.sh)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -W 2>/dev/null || pwd)"
IN="$ROOT/build/check_3d4"; OUT="$ROOT/build/shorts"; mkdir -p "$OUT/tmp"
cd /c/Windows/Fonts   # drawtext 의 fontfile 에 드라이브 글자(C:)를 안 쓰려고 — 글꼴을 상대 경로로 부른다
F="fontfile=malgunbd.ttf:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2"
D=4.3667; END="$D*3"   # 네 발 영상 하나 길이 · 네 발 셋이 끝나는 때 (곱셈은 ffmpeg 식이 한다 — Git Bash 에 bc 가 없다)
LABELS=('1번  웅크렸다 돌진' '3번  더 낮게 웅크려서' '5번  바닥에 납작')
TXT=""
for i in 0 1 2; do
  a="$D*$i"; b="$D*($i+1)"
  TXT+="drawtext=$F:fontsize=64:y=1560:text='${LABELS[$i]}':enable='between(t,$a,$b)',"
  TXT+="drawtext=$F:fontsize=120:fontcolor=0xff3030:y=1660:text='탈락':enable='between(t,$a+3.75,$b)',"   # 돌진이 화면을 덮어 검어진 뒤(112번째 프레임~)
done
ffmpeg -v error -y -i "$IN/MA_V1_coil_a_charge.mp4" -i "$IN/MA_V3_coil_c_low_charge_low.mp4" \
  -i "$IN/MA_V5_coil_sprawl_charge_sprawl.mp4" -i "$IN/UP_U4.mp4" -filter_complex "
[0:v]scale=1280:720,setsar=1[s0];[1:v]scale=1280:720,setsar=1[s1];[2:v]scale=1280:720,setsar=1[s2];[3:v]setsar=1[s3];
[s0][s1][s2][s3]concat=n=4:v=1,crop=540:720:370:0,scale=1080:1440,pad=1080:1920:0:240:black,
drawtext=$F:fontsize=70:y=70:text='네 발 괴물을 5번 만들고':enable='lt(t,$END)',
drawtext=$F:fontsize=70:y=160:text='5번 다 버렸다':enable='lt(t,$END)',
$TXT
drawtext=$F:fontsize=84:y=100:text='그래서 세웠다':enable='gte(t,$END)',
drawtext=$F:fontsize=64:y=1560:text='6번  서서 걸어온다':enable='gte(t,$END)',
drawtext=$F:fontsize=110:fontcolor=0x40e060:y=1660:text='일단 통과':enable='gte(t,$END+3.5)',
drawtext=$F:fontsize=36:y=1830:text='Tunnel · 1인칭 광산 호러 (개발 중)'[v]" \
  -map "[v]" -c:v libx264 -crf 18 -pix_fmt yuv420p "$OUT/tmp/short_ma_silent.mp4"
# TTS 대본: 시작초|문장
cat > "$OUT/tmp/short_ma_tts.txt" <<'TTS'
0.3|네 발로 기는 괴물을, 다섯 번 만들었다.
5.0|더 낮게 웅크려도 보고,
8.2|바닥에 납작 붙여도 봤다. 전부 탈락.
13.3|그래서 세웠다.
15.6|서서 걸어오는 쪽이, 일단 통과.
TTS
bash "$ROOT/tools/short_audio.sh" "$OUT/tmp/short_ma_silent.mp4" "$OUT/short_ma.mp4" "$OUT/tmp/short_ma_tts.txt"
