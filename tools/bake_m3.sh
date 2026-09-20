#!/usr/bin/env bash
# 새 몸 m3 굽기: 손가락 뼈 맞춤 → 걸음·클립 굽기 → Assets/Tunnel/Monster/miner_m3.glb (덮어쓴다)
#   bash tools/bake_m3.sh            # 몸 blend(stage17)가 이미 있을 때 — 보통 이것
#   bash tools/bake_m3.sh body       # blender/rig/m2_body.py 부터 (Cycles 굽기 포함, 오래 걸린다)
# 옛 몸(miner_rigged.glb)의 기본값은 안 건드린다 — m3 에만 다른 값은 여기 환경 변수로 준다.
set -u
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
MT="C:/Users/anjyo/Documents/MineTunnel"
if [ "${1:-}" = "body" ]; then
  "$BLENDER" -b --factory-startup -P blender/rig/m2_body.py || exit 1
fi
SHOTS="$PWD/build/check_m3" "$BLENDER" -b --factory-startup -P blender/rig/m3_fingers.py || exit 1
# CHORD_MAX: 새 손가락 뼈는 곧을 때 0.930 · 걷기 굽힘(10,15,10) 0.882 (09-20 실측) — 그 사이. 옛 손은 0.879 · 0.800 → 0.84
CHORD_MAX=0.905 \
SRC_BLEND="$MT/blender/miner_v5_stage18_m3_fingers.blend" \
OUT_GLB="$PWD/Assets/Tunnel/Monster/miner_m3.glb" \
OUT_BLEND="$MT/blender/walk_knuckle_m3.blend" \
  "$BLENDER" -b --factory-startup -P blender/anim/walk_knuckle.py 2>&1 | grep -E "^(PASS|FAIL)|^walk_knuckle|^exported|Traceback|Error"
# 알려진 FAIL 3개(09-20): up_grope 두 손 앞 0.035 m · 살 그림 해시(새 몸이라 다르다) · 갱목 재질 0(뺐다). 그 밖의 FAIL 이 있으면 고친다.
