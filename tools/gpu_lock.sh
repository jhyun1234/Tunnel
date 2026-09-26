# 검사 순서 잠금 — 병렬 세션(작업 폴더 여럿)이 배포물 검사를 동시에 돌리지 않게. 그래픽카드가 하나라 fps·밝기 검사가 서로를 떨어뜨린다(09-24).
# 쓰는 법: source tools/gpu_lock.sh; gpu_lock   (끝나면 EXIT 때 저절로 푼다)
# 잠금 = 작업 폴더들의 부모(Tunnel/) 아래 폴더 하나 — mkdir 는 한 번에 한 쪽만 성공한다. 안에 잡은 셸의 pid · 작업 폴더. 잡은 셸이 죽었으면 뺏는다.
GPU_LOCK="${GPU_LOCK:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.gpu_check_lock}"
gpu_unlock() { [ "$(cat "$GPU_LOCK/pid" 2>/dev/null)" = "$$" ] && rm -rf "$GPU_LOCK"; return 0; }
gpu_lock() {
  local waited=0 pid
  until mkdir "$GPU_LOCK" 2>/dev/null; do
    pid=$(cat "$GPU_LOCK/pid" 2>/dev/null)
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then echo "== gpu lock: 잡은 셸(pid $pid)이 없다 — 뺏는다"; rm -rf "$GPU_LOCK"; continue; fi
    [ $waited -eq 0 ] && echo "== gpu lock: 다른 세션이 검사 중 ($(cat "$GPU_LOCK/who" 2>/dev/null)) — 끝날 때까지 기다린다"
    sleep 5; waited=$((waited + 5))
  done
  echo $$ > "$GPU_LOCK/pid"; pwd > "$GPU_LOCK/who"
  trap gpu_unlock EXIT
  [ $waited -gt 0 ] && echo "== gpu lock: ${waited} s 기다렸다"
  return 0
}
