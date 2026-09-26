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
source tools/gpu_lock.sh; gpu_lock          # 다른 작업 폴더(병렬 세션)가 검사 중이면 기다린다 — 그래픽카드 하나 · 이 PSO 캐시도 같이 쓴다
rm -rf build/Tunnel/check
rm -f "$LOCALAPPDATA/Temp/jhyun1234/Tunnel/dx12_pso_cache_lib.bin"   # D3D12 파이프라인 캐시 — 재질·셰이더가 바뀐 빌드에서 묵은 캐시가 CHECK ALL PASS 뒤 종료 때 D3D12Core.dll 0xc0000005 (exit 139) 를 냈다 (09-23). 지우면 다시 만든다
./build/Tunnel/Tunnel.exe -check "$@" -screen-width 1920 -screen-height 1080 -screen-fullscreen 0 -logFile "$ROOT/build/check.log"
code=$?
grep "CHECK " build/check.log
if [ $code -eq 0 ] && grep -q "CHECK ALL PASS" build/check.log; then echo "ALL PASS"; exit 0; fi
echo "FAIL (exit $code)"; exit 1
