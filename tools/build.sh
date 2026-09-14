#!/usr/bin/env bash
# 빌드 → 배포물(exe) 검사. 사용: bash tools/build.sh [-sabotage floor|lamp|fog|thickfog]
# 에디터가 열려 있으면 프로젝트 락으로 실패한다 — 먼저 닫는다.
set -u
cd "$(dirname "$0")/.."
UNITY="/c/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe"
ROOT="$(pwd -W)"
mkdir -p build

echo "== build"
"$UNITY" -batchmode -nographics -projectPath "$ROOT" -executeMethod BuildM1.BuildWindows -logFile "$ROOT/build/unity.log"
code=$?
grep -E "error CS|^BUILD " build/unity.log | tail -20
if [ $code -ne 0 ] || ! grep -q "^BUILD Succeeded" build/unity.log; then
  echo "BUILD FAIL (exit $code)"; tail -30 build/unity.log; exit 1
fi

echo "== check (exe)"
rm -rf build/Tunnel/check
./build/Tunnel/Tunnel.exe -check "$@" -screen-width 1920 -screen-height 1080 -screen-fullscreen 0 -logFile "$ROOT/build/check.log"
code=$?
grep "CHECK " build/check.log
if [ $code -eq 0 ] && grep -q "CHECK ALL PASS" build/check.log; then echo "ALL PASS"; exit 0; fi
echo "FAIL (exit $code)"; exit 1
