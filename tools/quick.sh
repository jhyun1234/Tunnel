#!/usr/bin/env bash
# 빠른 검사 (개발 중). 빌드(~30 s) 뒤 바뀐 구간만 돌린다. 완료 전 마지막 한 번은 tools/build.sh(전체, 한 창) 그대로.
#   bash tools/quick.sh booth                      구간 하나 (부스 ~145 s — 전체 507 s 대신)
#   bash tools/quick.sh booth stalker              구간 여럿을 동시에 (-only 하나에 창 하나)
#   bash tools/quick.sh -sab tallcap,nocol booth   사보타주들을 동시에 (각각 -only booth) — 각 창에 FAIL 이 떠야 한다
#   JOBS=2 bash tools/quick.sh ...                 한꺼번에 띄우는 창 수 (기본 3)
# 전체를 구간별로 나눠 동시에 돌리는 것은 뺐다 (09-24 두 번 재 봄: 창 셋 522 · 496 s vs 한 창 507 s — 무거운 구간 intro·booth·anim 이
#   같이 돌면 서로 2~3 배 느려진다). 구간 따로 돌리면 실패하는 검사가 있다: stalker_searches_2to3_spots_then_wanders(-only stalker 에서만, 옛 동작으로도 FAIL)
#   NOBUILD=1 bash tools/quick.sh ...              빌드 없이 지금 exe 로 (사보타주만 다시 돌릴 때)
# 사용자가 실행 파일로 판정(F5)하는 동안에는 돌리지 않는다 — 같은 GPU 를 나눠 쓰면 상관없는 구간이 FAIL 한다.
set -u
cd "$(dirname "$0")/.."
UNITY="/c/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe"
ROOT="$(pwd -W)"
JOBS=${JOBS:-3}
mkdir -p build

sabs=""
if [ "${1:-}" = "-sab" ]; then sabs="${2//,/ }"; shift 2; fi
stages="$*"
[ -z "$stages" ] && { echo "구간을 적어라: m1 mining mine player map monster stalker lure chase retreat anim throw pick tired hud sound intro booth repair art ore map4 map4geo map4play map4meet"; exit 2; }

t0=$SECONDS
if [ "${NOBUILD:-}" != "1" ]; then
  "$UNITY" -batchmode -nographics -projectPath "$ROOT" -executeMethod BuildM1.BuildWindows -logFile "$ROOT/build/unity.log"
  if [ $? -ne 0 ] || ! grep -q "^BUILD Succeeded" build/unity.log; then grep -E "error CS" build/unity.log | tail -10; echo "BUILD FAIL"; exit 1; fi
  echo "== build $((SECONDS - t0)) s"
fi

runs=()                                                   # "이름 인자…"
if [ -n "$sabs" ]; then for s in $sabs; do runs+=("sab_$s -only $stages -sabotage $s"); done
else for st in $stages; do runs+=("$st -only $st"); done; fi

job() {                                                   # $1 = 이름, 나머지 = exe 인자
  local name=$1 t=$SECONDS log="build/quick_$1.log" pid i; shift
  rm -f "$log"
  ./build/Tunnel/Tunnel.exe -check "$@" -screen-width 1920 -screen-height 1080 -screen-fullscreen 0 -logFile "$ROOT/$log" >/dev/null 2>&1 &
  pid=$!
  while kill -0 $pid 2>/dev/null && ! grep -qE "CHECK ALL PASS|CHECK FAILED" "$log" 2>/dev/null; do sleep 1; done
  echo $((SECONDS - t)) > "build/quick_$name.sec"
  for i in $(seq 15); do kill -0 $pid 2>/dev/null || break; sleep 1; done
  kill $pid 2>/dev/null                                   # 결과를 다 적고 끝내다 멈춘 창 (09-24: 창 셋을 같이 돌리자 mining 이 끝내기에서 8 분 멈췄다)
  wait $pid 2>/dev/null
}
source tools/gpu_lock.sh; gpu_lock                          # 다른 작업 폴더(병렬 세션)가 검사 중이면 기다린다 — 그래픽카드 하나
rm -f "$LOCALAPPDATA/Temp/jhyun1234/Tunnel/dx12_pso_cache_lib.bin"   # build.sh 와 같은 이유
t1=$SECONDS
for r in "${runs[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n; done
  job $r &
done
wait
echo "== checks $((SECONDS - t1)) s ($JOBS at once)"

bad=0
for r in "${runs[@]}"; do
  name=${r%% *}; log="build/quick_$name.log"
  pass=$(grep -c "CHECK PASS" "$log" 2>/dev/null); fails=$(grep "CHECK FAIL " "$log" 2>/dev/null | cut -c1-300)
  if [ -n "$sabs" ]; then
    if [ -n "$fails" ]; then state="FAIL (good)"; else state="NO FAIL (bad: the check missed it)"; bad=1; fi
  elif grep -q "CHECK ALL PASS" "$log" 2>/dev/null; then state="ALL PASS"
  else state="FAIL"; bad=1; fi
  echo "-- $name: $state · pass $pass · $(cat "build/quick_$name.sec" 2>/dev/null) s"
  [ -n "$fails" ] && echo "$fails"
done
echo "== total $((SECONDS - t0)) s"
exit $bad
