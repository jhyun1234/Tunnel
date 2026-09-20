#!/usr/bin/env bash
# 소리 없는 쇼츠에 TTS 대본 + 브금을 얹는다.
#   bash tools/short_audio.sh <소리없는.mp4> <나올.mp4> <대본.txt> [브금 끊는 구간 시작 끝]
# 대본.txt = 줄마다 "시작초|문장" (UTF-8). TTS = tools/tts.ps1 (Windows Heami). 목소리는 8 % 낮춘다(덜 안내방송 같게).
# 브금 = ffmpeg 가 그 자리에서 합성하는 낮은 웅웅거림(파일·라이선스 없음). 폰 스피커는 55 Hz 를 못 내서 110·165 Hz 배음과 높은 불협화음(880/932 Hz)을 얹었다.
set -euo pipefail
SILENT="$1"; RESULT="$2"; SCRIPT="$3"; MUTE_IN="${4:-0}"; MUTE_OUT="${5:-0}"
HERE="$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)"
TMP="$(dirname "$RESULT")/tmp/$(basename "$RESULT" .mp4)_tts"; rm -rf "$TMP"; mkdir -p "$TMP"
powershell -NoProfile -ExecutionPolicy Bypass -File "$HERE/tts.ps1" -Lines "$SCRIPT" -OutDir "$TMP"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SILENT")
FADE=$(python -c "print($DUR-1.5)")
INPUTS=(); FILT=""; MIX=""; i=0
while IFS='|' read -r at text; do
  [ -z "${at// }" ] && continue
  len=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/$i.wav")
  echo "TTS $i  ${at}s + ${len}s(낮추면 x1.087)  $text"      # 다음 줄 시작을 넘는지 눈으로 본다
  INPUTS+=(-i "$TMP/$i.wav")
  ms=$(python -c "print(int(float('$at')*1000))")
  FILT+="[$((i+1)):a]aresample=44100,asetrate=44100*0.92,aresample=44100,adelay=$ms:all=1[t$i];"; MIX+="[t$i]"; i=$((i+1))
done < "$SCRIPT"
DRONE="0.22*sin(2*PI*55*t)*(0.7+0.3*sin(2*PI*0.13*t))+0.16*sin(2*PI*110.6*t)+0.10*sin(2*PI*164.2*t)*(0.5+0.5*sin(2*PI*0.09*t))+0.035*(sin(2*PI*880*t)+sin(2*PI*932*t))*(0.5+0.5*sin(2*PI*0.05*t+1))"
ffmpeg -v error -y -i "$SILENT" "${INPUTS[@]}" -filter_complex "
aevalsrc='$DRONE':s=44100:d=$DUR[dr];anoisesrc=c=brown:r=44100:d=$DUR:a=0.25,lowpass=f=350[nz];
[dr][nz]amix=inputs=2:normalize=0,volume=0.25,volume=0:enable='between(t,$MUTE_IN,$MUTE_OUT)',afade=t=in:d=1,afade=t=out:st=$FADE:d=1.5[bgm];
$FILT
${MIX}amix=inputs=$i:normalize=0,volume=1.6[voice];
[bgm][voice]amix=inputs=2:normalize=0,alimiter=limit=0.9[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t "$DUR" -movflags +faststart "$RESULT"
echo "OK $RESULT"
