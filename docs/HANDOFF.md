# 인계 문서 — 다음 세션은 여기서 시작한다

최종 갱신 2026-09-14. 이 문서 하나만 읽어도 이어서 작업할 수 있어야 한다.

## 1. 지금 어디까지 왔나

| | 상태 |
|---|---|
| 저장소 | https://github.com/jhyun1234/Tunnel (Public, Git LFS) |
| 마일스톤 1 | **빌드·배포물 검사 통과, 사용자 판정 대기.** 씬 `Assets/Scenes/M1_Tunnel.unity` |
| 이동 | `Player.cs` — Godot Player.gd 이동 부분 이식: 걷기 4.5 / 달리기 7 / 숙이기 2, 점프, 스태미나·탈진, 가속 0.12 s·감속 0.10 s |
| 헤드램프 | `Headlamp.cs` — Spot, 반각 60°(Godot 40), 사거리 14, 세기 560, 소프트 섀도, 0.1 s 늦게 따라옴, F 끄기 |
| 갱도 | `piece_straight.gltf`(glTFast 6.14.1)를 7 m 간격 6개 = 42 m. `COL_*` 노드를 MeshCollider로, 양 끝은 보이지 않는 벽 |
| 안개 | 거리 안개 Exponential 0.03 + 부피 안개 패키지 `com.cqf.urpvolumetricfog` 0.5.91(MIT, git) 밀도 0.003. PC_Renderer에 렌더러 기능 추가 |
| 후처리 | ACES, 채도 −25, 비네트 0.35 (`Assets/Settings/M1_Volume.asset`) |
| 수치 | `Assets/Scripts/Tuning.cs` — M1에 쓰는 것만, Godot 이름 그대로 |

### 마지막 검사 (2026-09-14, `bash tools/build.sh`, RTX 5060 Ti, 1920×1080)
- 조각 크기 7.000×5.600×7.000, 이음새 틈 0.00 mm — glTFast 축·배율 문제 없음
- 걷기 2초 8.96 m, 달리기 1초 6.36 m
- 화면 밝기(안개 끔) 0.0602 = Godot 골든 play_09_lamp 0.063의 ×0.96
- 부피 안개: 밝기 ×2.4, 구조 92 % 남음
- fps: 안개 켬 341 (2.93 ms) · 끔 720 (1.39 ms). **첫 실행 한 번은 82 / 200 fps였다** — 워밍업인지 다른 부하인지 미확인
- 사보타주 FAIL 확인: `floor`(grounded), `lamp`(lamp_lights_screen), `fog`(volfog_visible), `thickfog`(volfog_keeps_structure 71 %)

### 측정 표 (`Tunnel.exe -sweep`, 로그 `build/sweep.log`)
- 램프 세기 → 화면 밝기: 35 = 0.0029 · 140 = 0.0166 · 280 = 0.0330 · 560 = 0.0597 · 1120 = 0.0985
- 부피 안개 밀도(램프 560) → 밝기 배율·구조: 0.012 = ×4.9·70 % · 0.006 = ×3.4·83 % · 0.003 = ×2.4·92 % · 0.0015 = ×1.7·97 %
- 안개 품질(밀도 0.0015) → 프레임: steps 128 = 2.91 ms · 64 = 2.57 · 32 = 2.28 · 16 = 2.05 ms

## 2. 다음에 할 일 (우선순위 순)

### A. 사람이 답해야 하는 것 — 사용자에게 물어야 진행 가능

1. 마일스톤 1 판정 (4절)

### B. 내가 할 수 있는 것

1. 판정 결과에 따라 `Tuning.cs` 값 조정 → `MakeScene -force` → `build.sh`
2. GTX 1650급에서의 fps는 측정 수단이 없다. 저사양 판단이 급하면 사용자에게 저사양 PC 실행을 요청
3. glTF 23개 일괄 이식은 판정 뒤. Blender 재수출 설정(스케일·축·AO·메탈릭)은 문제가 보일 때 정한다

## 3. 알고 있는 함정

- 에디터가 열려 있으면 배치 모드가 프로젝트 락에 걸린다.
- **씬은 코드가 만든다** (`BuildM1.MakeScene`). 에디터에서 씬을 손으로 고치면 다음 `-force` 때 사라진다. `Tuning.cs`의 안개 밀도는 씬 생성 때 `M1_Volume.asset`에 구워지므로, 값을 바꾸면 씬을 다시 만들어야 한다.
  ```bash
  cd /c/Users/anjyo/Tunnel/unity && "/c/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe" -batchmode -quit -nographics -projectPath "$(pwd -W)" -executeMethod BuildM1.MakeScene -force -logFile "$(pwd -W)/Logs/make_scene.log"
  ```
- Unity 플레이어는 창이 포커스를 잃으면 멈춘다. 검사 모드는 `Application.runInBackground = true`로 막았다 (이게 없을 때 사보타주 실행이 멈춰 있었다).
- 밝기 비율만 보는 안개 검사는 기준 화면이 거의 검으면 망가진 화면도 통과시킨다 (첫 빌드: 램프 35 + 안개 0.012가 PASS). 그래서 `lamp_near_godot`를 먼저 게이트로 둔다.
- URP 램프 세기는 Godot 값과 단위·거리 감쇠가 달라 옮겨지지 않는다 (Godot 5.0 ≈ URP 560, 화면 평균 기준).
- 갱목이 Godot보다 희다 — Godot은 실행 중 `TIMBER_TINT`(0.6, 0.52, 0.45)를 곱했고 여기는 아직 안 한다. 젖은 바위 셰이더·레일·설비도 없다.
- Godot 좌표는 오른손(-Z 앞), Unity는 왼손(+Z 앞). 직선 조각은 대칭이라 이번에는 드러나지 않았다. 곡선·T 조각에서 방향을 확인할 것.

## 4. 판정 대기

실행 파일: `C:\Users\anjyo\Tunnel\unity\build\Tunnel\Tunnel.exe` (빌드 산출물, 커밋 안 됨)

조작: WASD 이동 · Shift 달리기 · Ctrl 숙이기 · Space 점프 · F 램프 · V 부피 안개 켜기/끄기 · `[` `]` 안개 밀도 ÷1.5/×1.5 · `-` `=` 램프 세기 ÷1.25/×1.25 · F1 표시 끄기 · Esc 마우스 풀기

물어볼 것:
1. 조작해서 재미있는가 — 걷기·달리기·숙이기 속도, 가속·감속이 무른가
2. 램프 반각 60°가 넓은가, 원형 테두리가 보이는가
3. 안개 밀도·램프 세기를 몇으로 두면 좋은가 (화면 왼쪽 위 숫자)
4. 부피 안개가 URP를 계속 쓸 만한 수준인가
