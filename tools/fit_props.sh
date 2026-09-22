#!/usr/bin/env bash
# A1 Meshy 소품 파이프라인 (승인 2026-09-23): Meshy 결과(Documents/MineTunnel/mesh/props/meshy_*.glb) → 맞춤 → 그림 1K → 조각 v2(갱목·갓등) → 틈 조각 v2 → 연속 사진
#   bash tools/fit_props.sh
# 뽑기 자체는 Opus5_채굴게임/Claude outputs/괴물_컨셉/gen_meshy.py <이름> --text "…" --poly N --tex 2k --out props (크레딧 — 사람이 정한 것만).
# 다음: Unity MakeScene -force -quit → bash tools/build.sh -only props (사보타주 bigprop · nomat · renametmb)
set -u
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
"$BLENDER" -b --factory-startup -P blender/props/fit_prop.py 2>&1 | grep -E '^(PASS|FAIL|wrote|fit_prop|Traceback|Error|  File)'
[ "${PIPESTATUS[0]}" -eq 0 ] || exit 1
for n in pickaxe timber_log mine_lamp; do
  python tools/shrink_glb.py "Assets/Tunnel/Props/$n.glb" 1024 | grep -E '^FAIL' && exit 1
done
rm -f Assets/Tunnel/Pieces/textures/prop_*
"$BLENDER" -b --factory-startup -P blender/map/piece_v2.py 2>&1 | grep -E '^(PASS|FAIL|wrote|piece_v2|Traceback|Error|  File)'
[ "${PIPESTATUS[0]}" -eq 0 ] || exit 1
PIECE_SRC=piece_straight_v2 PIECE_SUFFIX=_v2 "$BLENDER" -b --factory-startup -P blender/map/make_gaps.py > build/make_gaps_v2.log 2>&1 || { tail -5 build/make_gaps_v2.log; exit 1; }
grep -E '^CHECK' build/make_gaps_v2.log
"$BLENDER" -b --factory-startup -P blender/props/render_prop.py -- pickaxe timber_log mine_lamp 2>&1 | grep -E '^sheet|Traceback'
echo "fit_props: done"
