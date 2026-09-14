# 인계 문서 — 다음 세션은 여기서 시작한다

최종 갱신 2026-09-14 (5차). 이 문서 하나만 읽어도 이어서 작업할 수 있어야 한다.

## 1. 지금 어디까지 왔나

| | 상태 |
|---|---|
| 저장소 | https://github.com/jhyun1234/Tunnel (Public, Git LFS) |
| 마일스톤 1 | **사용자 판정 통과 (09-14)**: 조작 · 반각 60° · URP 계속 · 램프 75.2 · 안개 0.00089 · 벽 앞 감광 |
| 마일스톤 2 채굴 | **빌드·배포물 검사 통과, 사용자 판정 대기 (4절).** 포켓 24자리 전부 켬, 소리 파일 없이 소음 원만 (사용자 09-14) |
| 이동 | `Player.cs` — 걷기 4.5 / 달리기 7 / 숙이기 2, 점프, 스태미나, 광석 수(`ore`), 화면 흔들림(`Shake`) |
| 헤드램프 | `Headlamp.cs` — Spot 반각 60°, 사거리 14, 세기 75.2, 가까운 면 감광(광선 9개, REF 4 m · POW 1.4) |
| 채굴 | `Pickaxe.cs`(뷰모델 + 좌클릭 채굴, Godot Pickaxe.gd + Miner.gd) · `OrePocket.cs` · `Ore.cs` · `MiningFx.cs`(먼지·자갈·광석 생성) · `NoiseBus.cs` · `MiningHud.cs`("철 N" + 소음 원) |
| 갱도 | `piece_straight.gltf` ×6 = 42 m. 포켓은 씬 생성기가 조각의 `SLOT_Pocket_*` 24자리에 놓는다 |
| 텍스처 | `Assets/Editor/TextureImportRules.cs` — `*_nor_gl` = NormalMap, `*_Rough`·`*_arm` = 선형 |
| 안개·후처리 | 거리 안개 0.03 + 부피 안개 0.00089 · ACES · 채도 −25 · 비네트 0.35 |
| 수치 | `Assets/Scripts/Tuning.cs` — Godot 이름 그대로. 채굴 절은 Godot 값 그대로(곡괭이 좌표·X축 회전만 Unity 축으로 뒤집음) |

### 마지막 검사 (2026-09-14, `bash tools/build.sh`, RTX 5060 Ti, 1920×1080) — 전부 PASS
- M1: 조각 크기·이음새 0.00 mm · 걷기 8.95 m · 달리기 6.36 m · 앞뒤 대칭 0.93 · 벽 앞 탄 픽셀 1.0 % · 밝기 0.061 · 부피 안개 구조 98 % · fps 안개 켬 320 / 끔 653
- M2:
  - 포켓 24개, 24/24 벽 바위 면보다 앞에 보임
  - 채굴 거리(1.8 m) 화면 탄 픽셀 1.6 %
  - 누르고 있으면 2타에 캐짐 (0.48 초), 타격 소음 반경 25 m
  - 광석이 1.4 초에 0.95 m 굴러 멈춰 있고(자석 전), 그 뒤 0.2 초 만에 주워짐
  - 안 캐지는 포켓을 1 초 누르면 3타
- 사보타주 FAIL 확인: `floor` `lamp` `fog` `thickfog` `nodim` + M2 `bury`(0/24) · `onehit`(1타) · `spam`(1초 14타) · `nomagnet`(못 주움)
- 캡처: `build/check_m2/7_mining_view.png`, `8_mining_break.png` (빌드 산출물, 커밋 안 됨)

### 측정 표 (`Tunnel.exe -sweep`)
- 가까운 면 감광(램프 75.2) → 벽 앞 탄 픽셀 · 갱도 밝기: 없음 45.1 % · 0.0529 / REF 2 = 9.4 % / REF 3 = 2.8 % / **REF 4 = 1.3 % · 0.0515** / REF 4 POW 1.0 = 7.0 % / REF 6 = 0.4 % · 0.0469
- 안개 품질(밀도 0.0015) → 프레임: steps 128 = 2.91 ms · 64 = 2.57 · 32 = 2.28 · 16 = 2.05 ms

## 2. 다음에 할 일 (우선순위 순)

### A. 사람이 답해야 하는 것 — 사용자에게 물어야 진행 가능

1. 마일스톤 2 판정 (4절)
2. 다음 마일스톤 — 제안서로 하나씩. 남은 후보: ② 소음을 듣는 괴물 최소판 · ③ 갱도 조립기(조각 23종) · ④ 정비(갱목 고치기) · ⑤ 소리 파일

### B. 내가 할 수 있는 것

1. 판정 결과에 따라 `Tuning.cs` → (씬에 굽는 값이면 `MakeScene -force`) → `build.sh`
2. GTX 1650급 fps는 측정 수단이 없다

## 3. 알고 있는 함정

- 에디터가 열려 있으면 배치 모드가 프로젝트 락에 걸린다. 사용자가 에디터로 판정할 때가 있다 — 빌드 전에 `tasklist | grep Unity.exe`.
- **glTFast는 프로젝트 안 외부 텍스처(.gltf + .jpg)의 임포트 설정을 고치지 않는다.** 기본값(sRGB)이면 노멀맵이 기울어 램프 방향에 따라 밝기가 6배 갈린다. 새 텍스처 이름 규칙이 다르면 `TextureImportRules.cs`에 추가한다.
- **URP 스포트는 거리 제곱 감쇠 고정** — 가까운 면 감광은 **충돌체가 있는 면만** 잰다(갱목 기둥·소품엔 충돌체가 없다). 곡괭이 뷰모델도 감광 대상이 아니라 램프에 하얗게 뜬다.
- **채굴 레이는 벽 충돌체를 무시하고 레이 위 가장 가까운 포켓을 친다** (Godot MineRay mask 4와 같다). 포켓 앞면은 벽 충돌 상자보다 몇 cm만 나와 있어서, 벽에 막히게 하면 포켓 아래쪽을 조준했을 때 안 맞았다.
- 포켓의 "통로 쪽"(`outDir`)은 Godot 그대로 **자리 → 조각 원점** 방향이다. 조각 가운데가 아닌 자리(z ±1.75)는 대각선(약 27°)이라, 광석도 대각선으로 튄다.
- 자갈·광석은 Ignore Raycast 레이어(2)에 있고 플레이어와 `Physics.IgnoreCollision` — 곡괭이 레이·램프 감광 레이를 막지 않게.
- **씬은 코드가 만든다** (`BuildM1.MakeScene`). 에디터에서 씬을 손으로 고치면 다음 `-force` 때 사라진다. 안개 밀도·포켓 배치는 씬에 구워지므로 바꾸면 씬을 다시 만든다.
  ```bash
  cd /c/Users/anjyo/Tunnel/unity && "/c/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe" -batchmode -quit -nographics -projectPath "$(pwd -W)" -executeMethod BuildM1.MakeScene -force -logFile "$(pwd -W)/Logs/make_scene.log"
  ```
- 컴포넌트의 public 필드 초기값은 씬에 구워져 `Tuning`을 바꿔도 안 따라온다. 실행 중 조정용 필드는 `[System.NonSerialized]`로 둔다.
- 검사 모드: 창이 포커스를 잃으면 플레이어가 멈추고(`Application.runInBackground`로 막음), Input System이 가상 장치 입력을 막는다(`InputSystem.settings.backgroundBehavior = IgnoreFocus`로 막음).
- 검사 단계가 상태를 바꾸고 끝나면 다음 단계가 망가진다 — 7단계가 램프를 끈 채 끝나 채굴 화면이 검게 나왔다.
- 밝기 비율만 보는 검사는 기준 화면이 거의 검으면 망가진 화면도 통과시킨다. 한 방향·한 자리만 캡처하면 방향 의존 버그와 벽 앞 눈부심을 못 잡는다. 사용자 지적이 오면 그 자리를 검사 캡처에 넣는다.
- 갱목이 Godot보다 희다(`TIMBER_TINT` 미적용). 젖은 바위 셰이더·레일·설비 없음.
- Godot 좌표는 오른손(-Z 앞), Unity는 왼손(+Z 앞). 곡선·T 조각에서 방향을 확인할 것.

## 4. 판정 대기

실행 파일: `C:\Users\anjyo\Tunnel\unity\build\Tunnel\Tunnel.exe`. 에디터 Play로 볼 때는 `Assets/Scenes/M1_Tunnel.unity`.

조작: WASD 이동 · Shift 달리기 · Ctrl 숙이기 · Space 점프 · **좌클릭(누르고 있기) 채굴** · F 램프 · V 부피 안개 · `[` `]` 안개 밀도 · `-` `=` 램프 세기 · F1 표시 끄기 · Esc 마우스 풀기

물어볼 것 (마일스톤 2 채굴):
1. 휘두르기가 무거운가, 가벼운가
2. 두 번 치기가 답답한가
3. 광석이 굴러 나오는 게 보이는가
4. 소음 원을 보고 "소리를 냈다"로 읽히는가
5. 곡괭이가 램프에 하얗게 뜨는 것, 먼지가 밝은 점으로 보이는 것이 거슬리는가
