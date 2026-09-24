# 제안서 UI-2 — 인트로 화면 (로고 → 시작 메뉴 → 갱도, 끝나면 다시 인트로)

작성 2026-09-22. 출처: 지스타 2026 운영지침 1-1(인트로 필수: 대학 로고 · 사업단 로고 · 팀명 · 게임명, 2초 이상, 스킵 가능) · 4-1(볼륨 조절, 끝나면 초기 상태 복귀) · `docs/design/ui_ux_design.md` 시작 메뉴 줄(검은 바탕 + 글자 4줄, 배경 그림 없음). 마감 **10/2 인트로 캡처 제출**. 분석은 `docs/지스타2026/00_운영지침_분석과_일정.md`.

## 무엇을 하려는지
실행 파일을 켜면 **검은 화면에 로고 두 개 + 팀명 + 게임명**이 2초 이상 떠 있다가(아무 키·클릭이면 바로 넘어감, 단 로고는 2초는 채운다) **시작 메뉴**로 간다. 메뉴는 글자 3줄: 시작 · 소리 크기 · 끝내기. "시작"이면 지금의 갱도(M1_Tunnel). 잡히거나 판이 끝나면 지금은 복도 시작점으로 돌아가는데, 이걸 **인트로로 돌아가게** 바꾼다 — 그러면 지침의 "플레이 종료 후 초기 상태로 자동 복귀"가 된다. 로고 파일은 센터가 원본으로 준다(임의 변형 금지) — 오기 전에는 같은 크기의 회색 네모 두 개를 자리에 둔다.

## 어떻게 만들 것인지
- **새 씬 `Intro.unity`** (빌드 0번, `M1_Tunnel` 은 1번). 카메라 하나 + Canvas(uGUI, 이미 패키지에 있음 `com.unity.ugui`). 인트로 화면과 메뉴 화면은 같은 Canvas의 두 패널.
- **`Intro.cs`**: 켜지면 로고 패널 보임. `INTRO_LOGO_MIN_S` 지나고(또는 그 뒤 첫 입력) 메뉴 패널로. 메뉴: 위아래 화살표·마우스로 고름, Enter·클릭으로 실행. "시작" → `SceneManager.LoadScene("M1_Tunnel")`. "소리 크기" → 좌우 키로 0~100, `AudioListener.volume` 에 바로 넣고 `PlayerPrefs` 에 저장(이건 세이브가 아니라 부스 설정이라 남긴다). "끝내기" → `Application.Quit`.
- **`Stalker.cs` 잡힘 뒤**(UpdateCatch): 검은 화면 3 s 뒤 `restartPos` 로 가던 것을 `SceneManager.LoadScene("Intro")` 로. 갱도 안의 상태는 씬을 다시 불러오니 저절로 처음(광석 0·괴물 homePos·곡괭이 새것).
- **한글 폰트**: 팀명·게임명이 한글이라 내장 글꼴로는 네모가 뜬다. Pretendard(OFL) 한 벌을 `Assets/Fonts/` 에 넣고 라이선스 파일을 같은 폴더에 둔다(CLAUDE.md 소리 규칙과 같은 방식).
- **검사** (`-only intro`, 배포 실행 파일에서): ① 켜고 0.5 s 에 로고 패널이 보이고 메뉴는 안 보인다 ② 0.5 s 에 키를 눌러도 2.0 s 전에는 메뉴로 안 간다 ③ 2.1 s 에 키 → 메뉴 ④ "시작" → 활성 씬이 `M1_Tunnel` ⑤ 갱도에서 잡힘 → 3 s 뒤 활성 씬이 `Intro` ⑥ 소리 크기 50 → `AudioListener.volume` 0.5. 사보타주 `skipearly`(② 가 통과 못 하게 최소 시간 0) · `norestart`(⑤ — 잡힘 뒤 인트로 안 감).
- 캡처: `docs/captures/intro_logo.png`(로고 화면) · `intro_menu.png` — 10/2 제출물.

## 바꾸는 파일
| 파일 | | 이유 |
|---|---|---|
| `Assets/Scenes/Intro.unity` | 새로 | 인트로·메뉴 씬 |
| `Assets/Scripts/Intro.cs` | 새로 | 로고 시간·스킵·메뉴·볼륨 |
| `Assets/Scripts/Stalker.cs` | 고침 | 잡힘 뒤 인트로 씬으로 (잡힘 처리는 Player 가 아니라 Stalker.UpdateCatch 에 있었다) — `returnToIntro`, 검사용 `ForceCatch` |
| `Assets/Scripts/Tuning.cs` | 고침 | INTRO_TEAM · INTRO_TITLE · INTRO_SUBTITLE · INTRO_LOGO_MIN_S · INTRO_LOGO_AUTO_S · INTRO_VOLUME_STEP |
| `Assets/Scripts/M1Check.cs` · `Assets/Editor/BuildM1.cs` | 고침 | `intro` 구간(fails·Check·Finish 를 static 으로 — 인트로 씬 검사가 같이 쌓는다) · `MakeIntro` + 빌드 씬 목록 0 Intro · 1 M1_Tunnel. `build.sh` 는 안 바뀜 |
| `Assets/Fonts/` | 새로 | Pretendard + OFL 파일 |
| `Assets/UI/` | 새로 | 로고 자리 그림 2장(센터 원본으로 교체) |
| `ProjectSettings/ProjectSettings.asset` | 고침 | 기본 해상도 1024×768 → 1920×1080, productName 은 그대로(실행 파일 이름 Tunnel 유지) |

## 정할 수치
| 항목 | 값 | 출처 |
|---|---|---|
| INTRO_LOGO_MIN_S | 2.0 | 지침 1-1 "최소 2초" |
| INTRO_LOGO_AUTO_S | 5.0 | 키가 없어도 이때 메뉴로 (제안값, 구현 때 더함) |
| INTRO_VOLUME_STEP | 10 | 소리 크기 한 칸 (구현 때 더함) |
| 잡힘 → 인트로 | CATCH_RESTART_S 3.0 그대로 | M4 통과값, 새 수치 없음 |
| 로고 크기 | 화면 높이의 18 % 씩, 가로로 둘 나란히 | 제안값 — 센터 로고 비율 보고 조정 |
| 메뉴 글자 | 흰색, 화면 높이의 5 %, 고른 줄은 밝게 | 제안값 |

## 안 하는 것
Esc 일시정지(따로 UI-2b — 부스에선 관람객이 Esc 로 멈춰 두면 줄이 막혀서 오히려 빼는 게 나을 수 있음, 판정 때 묻는다) · "계속" 항목(세이브 없음) · 마우스 감도·전체화면 설정(1080p 고정) · 배경 그림·음악 · 한 판의 결과 화면(광석 수·시간 — 한 판 규칙이 정해진 뒤 UI-2c) · 크레딧 문구(사업 이름 확인 뒤 같은 씬에 한 줄 더함).

## 확인 목록 (F5)
- [ ] 실행 파일을 켜면 검은 화면에 로고 2 · 팀명 · 게임명이 보이고 2초는 아무 키를 눌러도 안 넘어간다
- [ ] 2초 뒤 아무 키로 메뉴, 시작 → 갱도, 잡힘 → 3초 뒤 다시 로고 화면
- [ ] 소리 크기를 0 으로 두고 곡괭이질하면 소리가 안 난다
- [ ] `bash tools/build.sh -only intro` PASS, `-sabotage skipearly` · `norestart` FAIL

## 승인 (09-22)
사용자: 영문 부제 **End of the Dead-End** · UI-2 승인 · 괴물 작업보다 먼저. 팀명은 아직 — `Tuning.INTRO_TEAM` 이 "(팀명)" 자리표시. 로고도 자리표시(회색 네모 `Assets/UI/`).
구현하며 정한 것: 로고 화면은 키가 없어도 INTRO_LOGO_AUTO_S 5 s 에 메뉴로(부스 대기) · 메뉴는 키보드(위아래·W/S·Enter·Space)와 클릭=확인, 마우스로 줄 고르기는 없음 · 잡히면 곧장 인트로(묻지 않음, 물음 3 의 부스 쪽 답).

## 물어볼 것 (승인 전 — 답 받음, 위 승인 절)
1. 팀명은 무엇으로 쓰나 (지침은 팀명·게임명 둘 다 요구)
2. 로고 원본은 센터에 요청했나 — 안 왔으면 회색 네모로 캡처를 먼저 뽑아 두고 오면 교체
3. 잡히면 곧장 인트로로 가는 게 맞나, 아니면 "다시 하기 / 그만" 한 번 묻고 가나 (부스 줄 관리 쪽은 곧장)
4. 이 제안서를 괴물 작업(MR1 맵 단계·m3 판정)보다 앞에 두어도 되나 — 10/2 마감 때문

## 판정 (09-24)
F5 통과(로고 2초 · 메뉴 · 잡히면 인트로 · 소리 크기). 팀명 = 오토마이너(`Tuning.INTRO_TEAM`). 로고 원본은 아직 — 오면 `Assets/UI/` 두 파일 교체 → `MakeIntro` → 캡처. Esc 는 **넣는다**: Esc 로 게임을 멈추고 설정·끝내기를 보인다 → 따로 UI-2b 제안서(끝내기 = 인트로로인가 프로그램 닫기인가 · 멈춘 채 두면 저절로 인트로로 가나).
