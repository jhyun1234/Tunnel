# Tunnel

## 무엇을 만드는가

1인칭 광산 호러. 헤드램프 하나로 갱도를 걸으며 광석을 캐고 고장난 지지목을 고치고,
천장을 기어 다니는 괴물에게 들키지 않고 살아남는다.
Godot 4.7.2 프로토타입을 Unity로 다시 만드는 프로젝트다.

**재미의 정체**: "소리를 내야 돈이 벌리고, 소리를 내면 죽는다."
이 문장에 기여하지 않는 기능은 제안하지 않는다. 기능 판정 예: 소음·정비 스킬체크·광차는 강화, 배움 카드는 애매, 동물은 무관.

## 엔진

- 엔진: Unity 6000.4.7f1, **URP** (템플릿 `3d-cross-platform`)
- 최소 사양 목표(잠정): GTX 1650 / 1080p / 60fps
- 명령어는 `game-engine` 스킬에 있다. 경로를 추측하지 말고 그 스킬을 읽는다.
- 빌드·배포물 검사: `bash tools/build.sh` (사보타주: `-sabotage floor|lamp|fog|thickfog`)
- 산출물: `build/`

## Godot판 참조 (읽기 전용)

- 작업 폴더: `C:\Users\anjyo\Tunnel\new-game` · 저장소: https://github.com/jhyun1234/Godot_Game
- `new-game/MIGRATION_NOTES.md` — 기능 상태, 스크립트 역할, 파이프라인, 미해결 문제, `Tuning.gd` 수치 339개
- `new-game/LOOK_REFERENCE.md` — 렌더링·안개·조명·재질 값
- Blender 원본: `C:\Users\anjyo\Documents\MineTunnel` · 옛 git 기록: `Tunnel/godot-git-backup`
- 이 문서들을 이 저장소로 복사하지 않는다. 경로로 참조한다.

## 이 프로젝트의 규칙

- 감각 수치(이동·램프·안개·괴물)는 Godot `Tuning.gd` 값이 출발점이다. 옮길 때 이름을 유지해 대조할 수 있게 한다.
- 이 저장소는 **Public**이다. API 키·토큰·개인 경로 밖 비밀을 커밋하지 않는다.
- 에셋을 넣기 전에 출처를 확인한다. Hunyuan 2.0·2.1 산출물(`Documents/MineTunnel/mesh/*_s50_o512.glb`, `miner_painted.glb`, `blender/mixamo_v2_hunyuan/`)은 넣지 않는다 — 라이선스가 한국 제외.
- 괴물 `miner_rigged.glb`(md5 `16442855…`)는 TRELLIS.2(MIT) 산출물로 확인됨(2026-09-14, 몸·머리 base color 텍스처가 `trellis2_v1.glb`·`trellis2_head_512.glb`와 바이트 일치, 갱목·쇠는 Blender 기본 도형 + Poly Haven CC0). GLB를 다시 뽑으면 다시 확인한다.
- Mixamo 원본 FBX는 저장소에 올리지 않는다. GLB에 구워 넣은 클립만 된다.
- 큰 바이너리(fbx·glb·png·wav 등)는 Git LFS로 간다 (`.gitattributes`). `.meta`는 반드시 커밋한다.

## 하지 말 것

- Godot 저장소·`new-game` 폴더를 지우거나 고치지 않는다.
- Godot판 `tools/minetunnel/export.sh`를 돌리지 않는다 — `build_piece.py`에 #26 B단계 값이 없어 조각이 옛 형상으로 바뀐다.
- `Assets/`의 기존 파일을 덮어쓰기 전에 물어본다.

## 완료의 정의

기능 하나가 끝났다고 말하려면 다음이 전부 참이어야 한다.

1. `bash tools/build.sh` 가 통과한다 (소스 검사 + **배포물 검사**).
2. 새로 넣은 검사를 일부러 실패시켜 FAIL이 뜨는 것을 확인했다.
3. `docs/HANDOFF.md` 를 갱신했다.
4. 커밋했다.

봇으로 측정할 수 있는 것(DPS, 프레임, 상대 강도)은 숫자로 말한다.
측정할 수 없는 것(지루한가, 손맛이 있는가)은 사용자에게 실행 파일을 주고 물어본다.
측정하지 않고 "괜찮아 보인다"고 쓰지 않는다.

## 현재 상태

`docs/HANDOFF.md` 를 읽어라. 이 파일에는 상태를 적지 않는다 — 두 곳에 적으면 갈린다.
