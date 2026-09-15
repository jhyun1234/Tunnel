# 인계 문서 — 다음 세션은 여기서 시작한다

최종 갱신 2026-09-15 (7차). 이 문서 하나만 읽어도 이어서 작업할 수 있어야 한다.

## 1. 지금 어디까지 왔나

| | 상태 |
|---|---|
| 저장소 | https://github.com/jhyun1234/Tunnel (Public, Git LFS) |
| 마일스톤 1 | **사용자 판정 통과 (09-14)**: 조작 · 반각 60° · URP 계속 · 램프 75.2 · 안개 0.00089 · 벽 앞 감광 |
| 마일스톤 2 채굴 | 1차 판정(09-14) 반영 → **빌드·배포물 검사 통과, 재판정 대기 (4절)** |
| 마일스톤 3 괴물 최소판 | `docs/제안서_M3_소음_듣는_괴물.md` 구현 → **빌드·배포물 검사 통과(09-15), 판정 대기 (4절)**. 캡슐 괴물이 곡괭이 소음(25 m)을 듣고 4.0 m/s 로 온다 |
| 이동 | `Player.cs` — 걷기 4.5 / 달리기 7 / 숙이기 2, 점프, 스태미나, 광석 수(`ore`), 화면 흔들림(`Shake`) |
| 헤드램프 | `Headlamp.cs` — Spot 반각 60°, 사거리 14, 세기 75.2, 가까운 면 감광(광선 9개, REF 4 m · POW 1.4). 곡괭이는 안 비춘다(조명 레이어), 곡괭이 전용 약한 등 `PickLight` 를 같이 켜고 끈다 |
| 채굴 | `Pickaxe.cs`(뷰모델 + 좌클릭 채굴) · `OrePocket.cs` · `Ore.cs` · `MiningFx.cs`(먼지·자갈·광석·타격음) · `NoiseBus.cs` · `MiningHud.cs`("철 N" + 소음 원) |
| 곡괭이 그리기 | ViewModel 레이어(8) → 메인 카메라가 빼고, 오버레이 카메라 `ViewModelCamera` 가 그린다 (벽 속으로 안 들어가 보임) |
| 소리 | `Assets/Audio/PickHit/impactMining_000~004.ogg` — Kenney Impact Sounds (CC0, 라이선스 파일 같은 폴더). 타격마다 무작위, 3D, 소음 반경 25 m 에서 0. 덩이가 빠질 때 음높이 0.8 |
| 괴물 | `Stalker.cs` — 상태 Wander·Investigate·Search. `NoiseBus.Made` 를 듣고 반경 × STALKER_EAR_MUL 안이면 조사. 1타 = 소리 쪽 7 m 만, 3 s 안 2타 = 그 자리. 수색 2~3곳 × 2 s. 길찾기 없음(직선). 캡슐(R 0.6 · H 2.8) + CharacterController. 설계 원본 `Opus5_채굴게임/Claude outputs/괴물AI_설계서_v2.md` |
| 갱도 | `piece_straight.gltf` ×6 = 42 m. 포켓은 씬 생성기가 조각의 `SLOT_Pocket_*` 24자리에 놓는다 |
| 텍스처 | `Assets/Editor/TextureImportRules.cs` — `*_nor_gl` = NormalMap, `*_Rough`·`*_arm` = 선형 |
| 수치 | `Assets/Scripts/Tuning.cs` — Godot 이름 그대로. "Unity 전용" 표시는 판정으로 새로 넣은 값 |

### M2 1차 판정(09-14)과 반영
| 판정 | 반영 |
|---|---|
| 휘두르기 가볍다 | 뒤로 들기 20° 0.08 s → 내려치기 → 박힌 채 멈춤 0.06 s → 되돌리기. 매 타격 화면 흔들림 0.02 m. 한 번 휘두르기 0.49 s (Godot 0.35) |
| 정확하게 캐기 어렵다 | 곡괭이 판정을 반지름 0.12 m 구로 — 포켓 가운데에서 0.22 m 빗나가도 맞고 0.5 m 는 안 맞음 |
| 곡괭이가 벽 안으로 들어간다 | 오버레이 카메라로 그린다 |
| 광석 굴러 나오는 것 잘 보인다 | 그대로 |
| 소음 원은 소리로 안 읽힌다 | Kenney CC0 타격음 추가 (원은 그대로 둠) |
| 곡괭이가 하얗게 뜬다 | 헤드램프 조명 레이어에서 곡괭이 제외 + 전용 등 세기 3.0 |
| 먼지인지 모르겠다 | 0.22 m 밝은 점 → 0.35~0.8 m 옅은 뭉게(수명 1.6~2.4 s, 2배로 커짐, 떠 있음) |

### 마지막 검사 (2026-09-14, `bash tools/build.sh`, RTX 5060 Ti, 1920×1080)
- M1: 조각 크기·이음새 0.00 mm · 걷기 8.97 m · 달리기 6.36 m · 앞뒤 대칭 0.91 · 벽 앞 탄 픽셀 1.0 % · 밝기 0.052 · 부피 안개 구조 98 % · fps 안개 켬 285 / 끔 492
- M2:
  - 포켓 24개, 24/24 벽 바위 면보다 앞에 보임
  - 곡괭이 오버레이 · 곡괭이 영역 탄 픽셀 갱도 가운데 0.8 % / 벽 앞 0.9 %
  - 조준 보정 (0.22 m 빗나감 맞음 · 0.5 m 안 맞음)
  - 채굴 거리 화면 탄 픽셀 1.2 %
  - 2타에 캐짐 (0.86 s), 소음 25 m, 귀에 들어온 소리 RMS 최대 0.53~0.83
  - 광석 1.4 s 에 0.95 m 굴러 멈춤, 그 뒤 0.2 s 에 주워짐
  - 1 초 누르면 2타 (휘두르기 0.49 s)
- 사보타주 FAIL 확인: `floor` `lamp` `fog` `thickfog` `nodim` `bury` `onehit` `spam` `nomagnet` `noassist` `noviewmodel` `picklamp`(갱도 가운데 곡괭이 탄 픽셀 13.5 %) `mute`(RMS 0)
- 캡처: `build/check_m2c/` (빌드 산출물, 커밋 안 됨)
- M3 (09-15): 30 m 밖 소음 무시(39.5 m, hits 0) · 1타 6~7 m 다가와 멈춤 · 2타 4.4 s 에 포켓 1.3 m 안 도착 · 수색 2~3곳 뒤 배회 복귀 7.5 s. 사보타주 `deaf`(귀 ×0.4) 3개 FAIL · `bigears`(귀 ×2) 1개 FAIL 확인. 캡처 `build/Tunnel/check/11_stalker_arrived.png`

### 측정 표 (`Tunnel.exe -sweep`)
- 가까운 면 감광(램프 75.2) → 벽 앞 탄 픽셀 · 갱도 밝기: 없음 45.1 % · 0.0529 / REF 2 = 9.4 % / REF 3 = 2.8 % / **REF 4 = 1.3 % · 0.0515** / REF 4 POW 1.0 = 7.0 % / REF 6 = 0.4 % · 0.0469
- 안개 품질(밀도 0.0015) → 프레임: steps 128 = 2.91 ms · 64 = 2.57 · 32 = 2.28 · 16 = 2.05 ms

## 2. 다음에 할 일 (우선순위 순)

### A. 사람이 답해야 하는 것 — 사용자에게 물어야 진행 가능

1. 마일스톤 2 재판정 (4절)
2. 마일스톤 3 판정 (4절 아래)
3. 다음 마일스톤 — 제안서로 하나씩. 순서는 설계서 v2 Step 7: ②b 눈·빛·추격·잡기 → ②c 체력·스턴·철수 → ③ 갱도 조립기(조각 23종) + 감독·NavMesh·배움 카드 → ④ 정비 → ⑤ 나머지 소리

### B. 내가 할 수 있는 것

1. 판정 결과에 따라 `Tuning.cs` → (씬에 굽는 값이면 `MakeScene -force`) → `bash tools/build.sh -only mining` → 커밋 전 `bash tools/build.sh`
2. GTX 1650급 fps는 측정 수단이 없다

## 3. 알고 있는 함정

- 에디터가 열려 있으면 배치 모드가 프로젝트 락에 걸린다. **사용자가 판정하려고 에디터를 자주 연다** — 빌드 전에 `tasklist | grep Unity.exe`, 열려 있으면 닫아 달라고 한다(저장 안 한 변경이 있을 수 있어 직접 끄지 않는다).
- **glTFast는 프로젝트 안 외부 텍스처(.gltf + .jpg)의 임포트 설정을 고치지 않는다.** 기본값(sRGB)이면 노멀맵이 기울어 램프 방향에 따라 밝기가 6배 갈린다. 새 텍스처 이름 규칙이 다르면 `TextureImportRules.cs`에 추가한다.
- **URP 스포트는 거리 제곱 감쇠 고정** — 가까운 면 감광은 **충돌체가 있는 면만** 잰다(갱목 기둥·소품엔 충돌체가 없다).
- **곡괭이 밝기 검사는 갱도 가운데서 해야 한다.** 벽 앞에서는 감광 때문에 램프가 0.07배라, 헤드램프가 곡괭이를 비추게 되돌려도(사보타주 `picklamp`) 3.9 % 로 통과했다. 갱도 가운데 13.5 % 로 FAIL.
- 오버레이 카메라(`ViewModelCamera`)는 후처리를 끈다 — 부피 안개 패스가 후처리 켠 카메라마다 돌아 오버레이에서 한 번 더 그려진다.
- 조명 레이어: 갱도·헤드램프 = 1, 곡괭이·PickLight = 2 (`Pickaxe.DefaultRenderingLayer` / `ViewModelRenderingLayer`). URP 에셋의 조명 레이어는 이미 켜져 있다.
- **채굴 판정은 벽 충돌체를 무시하고 판정 구 위 가장 가까운 포켓을 친다** (Godot MineRay mask 4와 같다). 포켓 앞면은 벽 충돌 상자보다 몇 cm만 나와 있다.
- 포켓의 "통로 쪽"(`outDir`)은 Godot 그대로 **자리 → 조각 원점** 방향이라 조각 가운데가 아닌 자리는 대각선(약 27°)이다.
- 자갈·광석은 Ignore Raycast 레이어(2)에 있고 플레이어와 `Physics.IgnoreCollision`.
- **씬은 코드가 만든다** (`BuildM1.MakeScene`). 에디터에서 씬을 손으로 고치면 다음 `-force` 때 사라진다. 안개 밀도·포켓 배치·소리 클립 목록은 씬에 구워지므로 바꾸면 씬을 다시 만든다.
  ```bash
  cd /c/Users/anjyo/Tunnel/unity && "/c/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe" -batchmode -quit -nographics -projectPath "$(pwd -W)" -executeMethod BuildM1.MakeScene -force -logFile "$(pwd -W)/Logs/make_scene.log"
  ```
- `MakeScene -force` 는 `M1_Volume.asset`·`M2_Dust.mat`·`M3_StalkerBody.mat` 을 지우고 다시 만든다 — git 에 수정으로 뜨는 게 정상.
- 괴물 CharacterController 는 플레이어 몸에 막히면 밀지 않고 STALKER_STUCK_S 1 s 뒤 그 자리를 도착으로 친다. 검사는 소음을 낸 뒤 플레이어를 길에서 비킨다.
- 컴포넌트의 public 필드 초기값은 씬에 구워져 `Tuning`을 바꿔도 안 따라온다. 실행 중 조정용 필드는 `[System.NonSerialized]`로 둔다.
- 검사 모드: 창이 포커스를 잃으면 플레이어가 멈추고(`Application.runInBackground`로 막음), Input System이 가상 장치 입력을 막는다(`backgroundBehavior = IgnoreFocus`로 막음). 검사 단계가 상태를 바꾸고 끝나면 다음 단계가 망가진다(램프를 끈 채 끝나 채굴 화면이 검었다).
- 밝기 비율만 보는 검사는 기준 화면이 거의 검으면 망가진 화면도 통과시킨다. 한 방향·한 자리만 캡처하면 방향 의존 버그·벽 앞 눈부심·곡괭이 눈부심을 못 잡았다. 사용자 지적이 오면 그 자리를 검사 캡처에 넣고, 사보타주로 FAIL을 먼저 본다.
- 갱목이 Godot보다 희다(`TIMBER_TINT` 미적용). 젖은 바위 셰이더·레일·설비 없음. 포켓(광석) 재질이 램프에 흰 반사점을 낸다.
- Godot 좌표는 오른손(-Z 앞), Unity는 왼손(+Z 앞). 곡선·T 조각에서 방향을 확인할 것.

## 4. 판정 대기

실행 파일: `C:\Users\anjyo\Tunnel\unity\build\Tunnel\Tunnel.exe`. 에디터 Play로 볼 때는 `Assets/Scenes/M1_Tunnel.unity` (판정 뒤 에디터를 닫아 줘야 빌드가 된다).

조작: WASD 이동 · Shift 달리기 · Ctrl 숙이기 · Space 점프 · **좌클릭(누르고 있기) 채굴** · F 램프 · V 부피 안개 · `[` `]` 안개 밀도 · `-` `=` 램프 세기 · F1 표시 끄기 · Esc 마우스 풀기

물어볼 것 (마일스톤 2 재판정):
1. 휘두르기 무게 — 들기·멈춤·흔들림이 무겁게 느껴지는가, 누르고 맞기까지(0.2 s)가 굼뜬가
2. 조준이 쉬워졌는가, 곡괭이가 여전히 벽에 파묻혀 보이는가
3. 타격음 — 크기, 곡괭이 소리로 들리는가, 반복이 거슬리는가
4. 곡괭이 밝기(전용 등 3.0)가 어둡거나 밝지 않은가
5. 먼지가 먼지로 보이는가

물어볼 것 (마일스톤 3 괴물 최소판, `docs/제안서_M3_소음_듣는_괴물.md` 확인 목록):
1. 북쪽 끝에서 왕복하는 캡슐이 램프 원뿔 안에서 보이는가 (검은 캡슐이라 어두우면 안 보일 수 있다)
2. 1타 뒤 7 m 다가와 멈추는 게 "의심한다"로 읽히는가
3. 4.0 m/s 로 오는 것이 무서운가, 느린가
4. 화면 왼쪽 위 `stalker` 줄(상태·들은 소음·거리)이 읽히는가
