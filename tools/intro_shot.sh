#!/usr/bin/env bash
# 인트로만 빨리: MakeIntro → 빌드 → exe -check -only intro 를 인트로 검사 줄까지만 돌리고 끈다 (부스 검사 약 5 분은 건너뜀).
# 제출 캡처 build/Tunnel/check/intro_logo.png · intro_menu.png 가 새로 찍힌다. 센터 로고를 Assets/UI/logo_*.png 에 바꿔 넣은 뒤 이것 하나.
#   bash tools/intro_shot.sh                  씬 다시 만들고 빌드하고 찍기 (약 70 s)
#   NOBUILD=1 bash tools/intro_shot.sh nosignlight   지금 exe 로, 사보타주 하나 (intro_sign_lit 가 FAIL 해야 한다)
# 커밋 전에는 전체 bash tools/build.sh 를 그대로 돌린다.
set -u
cd "$(dirname "$0")/.."
UNITY="/c/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe"
ROOT="$(pwd -W)"
mkdir -p build
if [ "${NOBUILD:-}" != "1" ]; then
  "$UNITY" -batchmode -nographics -projectPath "$ROOT" -executeMethod BuildM1.MakeIntro -quit -logFile "$ROOT/build/makeintro.log"
  grep -q "Intro scene saved" build/makeintro.log || { grep -E "error CS|인트로 재료" build/makeintro.log | head; echo "MAKEINTRO FAIL"; exit 1; }
  "$UNITY" -batchmode -nographics -projectPath "$ROOT" -executeMethod BuildM1.BuildWindows -logFile "$ROOT/build/unity.log"
  grep -q "^BUILD Succeeded" build/unity.log || { grep -E "error CS" build/unity.log | tail; echo "BUILD FAIL"; exit 1; }
fi
source tools/gpu_lock.sh; gpu_lock                          # 다른 작업 폴더가 검사 중이면 기다린다
log=build/intro_shot.log
rm -f "$log"
args=(-check -only intro)
[ -n "${1:-}" ] && args+=(-sabotage "$1")
./build/Tunnel/Tunnel.exe "${args[@]}" -screen-width 1920 -screen-height 1080 -screen-fullscreen 0 -logFile "$ROOT/$log" >/dev/null 2>&1 &
pid=$!
for i in $(seq 90); do grep -q "intro_volume_setting_applies" "$log" 2>/dev/null && break; sleep 1; done
sleep 2
kill $pid 2>/dev/null
wait $pid 2>/dev/null
grep "CHECK .*intro" "$log" | cut -c1-330
echo "캡처: build/Tunnel/check/intro_logo.png · intro_menu.png"
