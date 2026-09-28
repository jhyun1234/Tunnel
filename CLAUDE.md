# Tunnel

## 무엇을 만드는가

1인칭 탄광 호러, 1~4인(혼자도 넷도 같은 규칙). 헤드램프 하나로 갱도에 내려가 석탄을 캐고
망가진 시설을 고치고 옛 광부의 몸을 데려오며, 소리를 듣고 오는 "그것"(서서 걷는 광부 모양 괴물)을 피한다.
Lethal Company처럼 교대(약 15분)를 되풀이하며 몫을 채우고, 이야기는 The Forest처럼 장소와 물건에 흩어 둔다.
엔딩까지 약 8시간. 지스타 2026 부스판은 그 첫 교대를 혼자 3~5분으로 줄인 것이다.
Godot 4.7.2 프로토타입을 Unity로 다시 만드는 프로젝트다.

**기획의 원본**: `docs/기획서/기획서.md` (v3, 사용자의 출시판 기획서 09-28 을 옮김). 출시판 기능은 이 문서를 따른다.
인원·교대와 몫·이야기 전달 방식·엔딩처럼 뼈대를 바꾸는 제안은 사용자 확인 뒤 기획서부터 고친다.
기획서 9절에서 체크 안 된 "확인 필요"는 Claude 추천값이다 — 그 위에 기능을 쌓기 전에 사용자에게 묻는다.

**재미의 정체**: "소리를 내야 돈이 벌리고, 소리를 내면 죽는다."
이 문장에 기여하지 않는 기능은 제안하지 않는다. 기능 판정 예: 소음·정비 스킬체크·광차·시체 옮기기·목소리 채팅은 강화, 배움 카드는 애매, 동물은 무관.

## 엔진

- 엔진: Unity 6000.4.7f1, **URP** (템플릿 `3d-cross-platform`)
- 최소 사양 목표(잠정): GTX 1650 / 1080p / 60fps
- 명령어는 `game-engine` 스킬에 있다. 경로를 추측하지 말고 그 스킬을 읽는다.
- 빌드·배포물 검사: `bash tools/build.sh` (사보타주: `-sabotage floor|lamp|fog|thickfog`)
- 개발 중 빠른 검사: `bash tools/quick.sh <구간>` (바뀐 구간만, 사보타주 여럿은 `-sab a,b <구간>`). 전체 build.sh 는 커밋 전 한 번
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
- 참고로 받은 다른 게임의 영상·캡처는 `build/refs/`(커밋 안 됨)에만 둔다. 저작권 — 공개 저장소에 올리지 않는다.
- 에셋을 넣기 전에 출처를 확인한다. Hunyuan 2.0·2.1 산출물(`Documents/MineTunnel/mesh/*_s50_o512.glb`, `miner_painted.glb`, `blender/mixamo_v2_hunyuan/`)은 넣지 않는다 — 라이선스가 한국 제외.
- 괴물 `miner_rigged.glb`(md5 `16442855…`)는 TRELLIS.2(MIT) 산출물로 확인됨(2026-09-14, 몸·머리 base color 텍스처가 `trellis2_v1.glb`·`trellis2_head_512.glb`와 바이트 일치, 갱목·쇠는 Blender 기본 도형 + Poly Haven CC0). GLB를 다시 뽑으면 다시 확인한다.
- Mixamo 원본 FBX는 저장소에 올리지 않는다. GLB에 구워 넣은 클립만 된다.
- 소리는 재배포 가능한 라이선스만 넣고, 라이선스 파일을 소리와 같은 폴더에 둔다. 지금: `Assets/Audio/PickHit/` Kenney Impact Sounds (CC0, 2026-09-14 kenney.nl에서 받음).
- 큰 바이너리(fbx·glb·png·wav 등)는 Git LFS로 간다 (`.gitattributes`). `.meta`는 반드시 커밋한다.
- **판정 키(DevHud)에 숫자패드를 쓰지 않는다** — 사용자 키보드는 텐키리스다(09-27 ART-1 판정 ② "밝기 키가 숫자패드라 못 씀"). 숫자 줄 · 글자 · 화살표 · 기호 키로. 옆 가지 세션은 이 컴퓨터의 자동 메모리를 못 볼 수 있어 여기에 적는다.

## 병렬 세션 (작업 폴더 여럿, 사용자 09-27)

- **main = `Tunnel/unity`(이 폴더), 합치기 담당.** 옆 가지는 작업 폴더를 따로 만든다: `cd C:\Users\anjyo\Tunnel\unity; git worktree add ..\unity-<이름> -b <가지>` → 그 폴더에서 세션 하나. 같은 폴더를 두 세션이 쓰지 않는다(Unity 가 폴더마다 하나만 연다). 새 폴더는 처음 Unity 임포트가 오래 걸린다.
- **배포물 검사는 한 번에 하나** — `tools/quick.sh` · `tools/build.sh` 가 `tools/gpu_lock.sh`(잠금 = `Tunnel/.gpu_check_lock`)로 다른 폴더의 검사가 끝날 때까지 기다린다. 그래픽카드가 하나라 fps·밝기 검사가 서로를 떨어뜨린다. 자기 검사 `bash tools/test_gpu_lock.sh`. 사용자가 판정 중이면 어느 폴더도 검사를 안 돌린다(그대로).
- **옆 가지는 되도록 안 고치는 파일**: `BuildM1.cs` · `M1Check.cs` · `Tuning.cs` · `DevHud.cs` · 씬 — Unity 에 붙이는 일은 합칠 때 main 에서. 고쳐야 하면 고친 곳을 옆 가지 HANDOFF 절에 적는다(합칠 때 부딪힘 줄이기).
- **HANDOFF**: 옆 가지는 자기 절 `## 0. 옆 가지 <가지>`에만 쓴다(09-20 m2-body 전례). 맨 위 요약·다음 세션 프롬프트는 main 세션만.
- **합치기**: 사용자가 옆 가지 결과를 통과시키면 main 세션이 `git merge <가지>` → 전체 build.sh → 커밋. 작업 폴더 지우기(`git worktree remove`)는 사용자 확인 뒤 — 에디터·탐색기가 잡고 있으면 안 지워진다(09-20 unity-m2).
- 제안서는 가지마다 하나씩(사용자 규칙 그대로). 푸시는 사용자 지시 때만.

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
