#!/usr/bin/env bash
# gpu_lock.sh 자기 검사: ① 두 셸이 동시에 잡으면 하나가 끝난 뒤에야 다른 하나가 돈다 ② 죽은 셸의 잠금은 뺏는다.
#   bash tools/test_gpu_lock.sh   → PASS / FAIL.  SABOTAGE=1 이면 잠금 없이 돌려 ① 이 FAIL 하는지 본다
set -u
cd "$(dirname "$0")/.."
export GPU_LOCK="$(mktemp -d)/lock"; LOG="$(dirname "$GPU_LOCK")/log"
job() { source tools/gpu_lock.sh; [ "${SABOTAGE:-}" = "1" ] || gpu_lock; echo "start $1 $(date +%s%N)" >> "$LOG"; sleep 2; echo "end $1 $(date +%s%N)" >> "$LOG"; }
( job A ) & ( sleep 0.3; job B ) & wait
s1=$(grep "start A" "$LOG" | cut -d' ' -f3); e1=$(grep "end A" "$LOG" | cut -d' ' -f3); s2=$(grep "start B" "$LOG" | cut -d' ' -f3)
ok1=0; [ "$s2" -ge "$e1" ] && ok1=1
mkdir "$GPU_LOCK"; echo 999999 > "$GPU_LOCK/pid"                         # 죽은 셸이 남긴 잠금
t=$SECONDS; ( source tools/gpu_lock.sh; gpu_lock >/dev/null ); ok2=0; [ $((SECONDS - t)) -lt 5 ] && [ ! -d "$GPU_LOCK" ] && ok2=1
echo "serialized (B starts after A ends) $ok1 · stale lock taken $ok2"
rm -rf "$(dirname "$GPU_LOCK")"
[ $ok1 -eq 1 ] && [ $ok2 -eq 1 ] && echo PASS || { echo FAIL; exit 1; }
