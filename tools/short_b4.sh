#!/usr/bin/env bash
# 쇼츠 1편: "책상 밑에 숨었는데 손이 더듬어 들어온다" (UP_B4 내 시점 + UP_B4_close 옆모습, 같은 시간축 23.8 s)
# 입력: build/check_3d4/UP_B4.mp4 · UP_B4_close.mp4 (blender/anim/preview_upright.py 가 만든다)
# 출력: build/shorts/short_b4.mp4 (1080x1920, 30 fps, 소리 없음 — 소리는 올릴 때 얹는다)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -W 2>/dev/null || pwd)"
IN="$ROOT/build/check_3d4"; OUT="$ROOT/build/shorts"; mkdir -p "$OUT"
cd /c/Windows/Fonts   # drawtext 의 fontfile 에 드라이브 글자(C:)를 안 쓰려고 — 글꼴을 상대 경로로 부른다
F="fontfile=malgunbd.ttf:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2"
HEAR_IN=16.2; HEAR_OUT=18.6   # "들었나?" — 머리가 나를 향해 딱 들리는 구간 (UP_B4 에서 눈으로 잰 값)
cap() { echo "drawtext=$F:fontsize=${4:-76}:fontcolor=${5:-white}:y=130:text='$3':enable='between(t,$1,$2)'"; }
ffmpeg -v error -y -i "$IN/UP_B4.mp4" -i "$IN/UP_B4_close.mp4" -filter_complex "
color=black:s=1080x1920:r=30:d=23.8[bg];
[0:v]crop=900:720:330:0,scale=1080:864[pov];
[1:v]scale=1080:608[side];
[bg][pov]overlay=0:300[a];[a][side]overlay=0:1164:shortest=1[b];
[b]$(cap 0 4 '책상 밑에 숨었다'),
$(cap 4 10 '손으로 더듬어 찾는다'),
$(cap 10 $HEAR_IN '짚을 때마다 더 가까이'),
$(cap $HEAR_IN $HEAR_OUT '…들었나?' 104 0xff3030),
$(cap $HEAR_OUT 23.8 '소리를 내면 죽는다'),
drawtext=$F:fontsize=34:x=24:y=312:text='내 시점',
drawtext=$F:fontsize=34:x=24:y=1176:text='옆에서 본 모습',
drawtext=$F:fontsize=40:y=1800:text='Tunnel · 1인칭 광산 호러 (개발 중)'[v]" \
  -map "[v]" -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart "$OUT/short_b4.mp4"
echo "OK $OUT/short_b4.mp4"
