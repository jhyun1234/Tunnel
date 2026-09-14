# 인계 문서 — 다음 세션은 여기서 시작한다

최종 갱신 2026-09-14 (4차). 이 문서 하나만 읽어도 이어서 작업할 수 있어야 한다.

## 1. 지금 어디까지 왔나

| | 상태 |
|---|---|
| 저장소 | https://github.com/jhyun1234/Tunnel (Public, Git LFS) |
| 마일스톤 1 | **사용자 판정 통과 (09-14): 조작 괜찮다 · 반각 60° 괜찮다 · URP 계속 사용.** 벽 앞 눈부심 수정분만 판정 대기(4절) |
| 이동 | `Player.cs` — Godot Player.gd 이동 부분 이식: 걷기 4.5 / 달리기 7 / 숙이기 2, 점프, 스태미나·탈진, 가속 0.12 s·감속 0.10 s |
| 헤드램프 | `Headlamp.cs` — Spot, 반각 60°, 사거리 14, 세기 75.2(사용자 확정), 소프트 섀도, 0.1 s 늦게 따라옴, F 끄기, **가까운 면 감광**(원뿔 안 광선 9개, `LAMP_NEAR_REF` 4 m · `LAMP_NEAR_POW` 1.4) |
| 갱도 | `piece_straight.gltf`(glTFast 6.14.1)를 7 m 간격 6개 = 42 m. `COL_*` 노드를 MeshCollider로, 양 끝은 보이지 않는 벽 |
| 텍스처 | `Assets/Editor/TextureImportRules.cs` — `*_nor_gl` = NormalMap, `*_Rough`·`*_arm` = 선형 |
| 안개 | 거리 안개 Exponential 0.03 + 부피 안개 패키지 `com.cqf.urpvolumetricfog` 0.5.91(MIT, git) 밀도 0.00089(사용자 확정) |
| 후처리 | ACES, 채도 −25, 비네트 0.35 (`Assets/Settings/M1_Volume.asset`) |
| 수치 | `Assets/Scripts/Tuning.cs` — M1에 쓰는 것만, Godot 이름 그대로. 램프 세기·감광 값은 씬에 굽지 않는다(`NonSerialized`) |

### 마지막 검사 (2026-09-14, `bash tools/build.sh`, RTX 5060 Ti, 1920×1080)
- 조각 7.000×5.600×7.000, 이음새 틈 0.00 mm
- 걷기 2초 8.97 m, 달리기 1초 6.36 m
- 앞뒤 대칭(z 17.5): +Z 0.052 / −Z 0.058
- 벽 앞(몸이 벽에 닿은 자리): 하얗게 탄 픽셀 1.2 %, 감광 0.074 (감광 없으면 45.1 %)
- 화면 밝기(안개 끔) 0.049 = Godot 골든 0.063의 ×0.78
- 부피 안개: 구조 98 %
- fps: 안개 켬 280~327 · 끔 615~670
- 사보타주 FAIL 확인: `floor`, `lamp`, `fog`, `thickfog`, `nodim`(벽 앞 45.1 %). 대칭 검사는 노멀맵 수정 전 빌드에서 FAIL 확인

### 측정 표 (`Tunnel.exe -sweep`, 로그 `build/sweep.log`)
- 가까운 면 감광(램프 75.2) → 벽 앞 탄 픽셀 · 갱도 밝기: 없음 45.1 % · 0.0529 / REF 2 = 9.4 % · 0.0529 / REF 3 = 2.8 % · 0.0520 / **REF 4 = 1.3 % · 0.0515** / REF 4 POW 1.0 = 7.0 % / REF 6 = 0.4 % · 0.0469
- 발광점을 카메라 뒤로 빼기(기각): 0 m 45 % · 0.2 m 53 % · 0.35 m 55 %
- 안개 품질(밀도 0.0015) → 프레임: steps 128 = 2.91 ms · 64 = 2.57 · 32 = 2.28 · 16 = 2.05 ms
- (노멀맵 버그 상태에서 잰 램프 세기·안개 밀도 표는 무효라 지웠다)

## 2. 다음에 할 일 (우선순위 순)

### A. 사람이 답해야 하는 것 — 사용자에게 물어야 진행 가능

1. 벽 앞 감광 판정 (4절)
2. 마일스톤 2 범위 — 제안서로 하나씩 낸다

### B. 내가 할 수 있는 것

1. glTF 23개 이식 방식 결정: glTFast 그대로 쓰면서 조각별 크기·방향 검사를 늘릴지, Blender 재수출 설정(스케일·축·AO·메탈릭)을 정할지. 직선 조각에서는 축·배율 문제 없음(틈 0.00 mm)
2. GTX 1650급 fps는 측정 수단이 없다. 저사양 판단이 급하면 사용자에게 저사양 PC 실행을 요청

## 3. 알고 있는 함정

- 에디터가 열려 있으면 배치 모드가 프로젝트 락에 걸린다. 사용자가 에디터로 판정할 때가 있다 — 빌드 전에 `tasklist | grep Unity.exe`.
- **glTFast는 프로젝트 안 외부 텍스처(.gltf + .jpg)의 임포트 설정을 고치지 않는다.** 기본값(sRGB 일반 텍스처)이면 노멀맵이 한쪽으로 기울어 램프 방향에 따라 밝기가 6배 갈린다. 새 텍스처 이름 규칙이 다르면 `TextureImportRules.cs`에 추가한다.
- **URP 스포트는 거리 제곱 감쇠 고정**이라 벽에 붙으면 하얗게 탄다. 세기를 낮춰도 안 된다(갱도가 같이 어두워진다). 가까운 면 감광은 **충돌체가 있는 면만** 잰다 — 갱목 기둥·소품에는 충돌체가 없어 그 뒤 벽까지 거리로 계산된다. 조각을 늘릴 때 정비 대상(갱목)에 충돌체를 줄지 볼 것.
- **씬은 코드가 만든다** (`BuildM1.MakeScene`). 에디터에서 씬을 손으로 고치면 다음 `-force` 때 사라진다. 안개 밀도는 씬 생성 때 `M1_Volume.asset`에 구워지므로, 값을 바꾸면 씬을 다시 만들어야 한다.
  ```bash
  cd /c/Users/anjyo/Tunnel/unity && "/c/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe" -batchmode -quit -nographics -projectPath "$(pwd -W)" -executeMethod BuildM1.MakeScene -force -logFile "$(pwd -W)/Logs/make_scene.log"
  ```
- 컴포넌트의 public 필드 초기값은 씬 생성 때 씬에 구워져 `Tuning` 값을 바꿔도 안 따라온다. 실행 중 조정용 필드는 `[System.NonSerialized]`로 둔다.
- Unity 플레이어는 창이 포커스를 잃으면 멈춘다. 검사 모드는 `Application.runInBackground = true`로 막았다.
- 밝기 비율만 보는 안개 검사는 기준 화면이 거의 검으면 망가진 화면도 통과시킨다. 그래서 `lamp_not_black`을 둔다.
- 화면 한 방향·한 자리만 캡처하는 검사는 방향 의존 버그와 벽 앞 눈부심을 못 잡았다. 사용자 지적이 오면 그 자리를 검사 캡처에 넣는다.
- 갱목이 Godot보다 희다 — Godot은 실행 중 `TIMBER_TINT`(0.6, 0.52, 0.45)를 곱했고 여기는 아직 안 한다. 젖은 바위 셰이더·레일·설비도 없다.
- Godot 좌표는 오른손(-Z 앞), Unity는 왼손(+Z 앞). 직선 조각은 대칭이라 드러나지 않았다. 곡선·T 조각에서 방향을 확인할 것.

## 4. 판정 대기

실행 파일: `C:\Users\anjyo\Tunnel\unity\build\Tunnel\Tunnel.exe` (빌드 산출물, 커밋 안 됨). 에디터 Play로 볼 때는 `Assets/Scenes/M1_Tunnel.unity`.

조작: WASD 이동 · Shift 달리기 · Ctrl 숙이기 · Space 점프 · F 램프 · V 부피 안개 켜기/끄기 · `[` `]` 안개 밀도 · `-` `=` 램프 세기 · F1 표시 끄기 · Esc 마우스 풀기

물어볼 것:
1. 벽에 붙었을 때 이제 거슬리지 않는가 (갱목 고치는 거리)
2. 벽에서 떨어질 때 밝기가 따라 바뀌는 것(0.15초)이 눈에 띄는가

확정된 것 (09-14): 조작 · 반각 60° · URP 계속 · 램프 세기 75.2 · 안개 밀도 0.00089
