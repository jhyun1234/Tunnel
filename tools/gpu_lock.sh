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

# 판정 지키기 — 사용자가 이 폴더의 실행 파일로 판정 중이면(-check 없이 켜져 있으면) 빌드 · 검사를 멈춘다.
# 10-05: 판정 중인 게임이 켜진 채 다시 빌드해 그 게임의 데이터 파일이 바뀌었고, 검사가 그래픽카드를 같이 썼다(사용자 승인 "그것도 같이 넣어라").
judge_guard() {
  local exe n
  exe="$(cygpath -w "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/build/Tunnel/Tunnel.exe")"
  n=$(powershell -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name='Tunnel.exe'\" | Where-Object { \$_.ExecutablePath -eq '$exe' -and \$_.CommandLine -notmatch ' -check( |\$)' }).Count" 2>/dev/null | tr -d '\r')
  if [ "${n:-0}" != "0" ]; then
    echo "== 판정 중: build/Tunnel/Tunnel.exe 가 -check 없이 켜져 있다($n 개). 게임을 끄고 다시 돌려라 — 빌드 · 검사를 하지 않는다"
    exit 3
  fi
}
