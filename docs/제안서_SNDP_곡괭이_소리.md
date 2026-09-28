# 제안서 SND-P — 곡괭이 "콱" 소리 바꾸기 (섞기 B)

main, 2026-09-27. **승인 09-28**(물을 것 셋 모두 추천대로: 딸각·쨍은 Kenney 그대로 · 콱 25 → 6 m · 사다리 맨 위 = 쨍) → **구현 09-28 — 실행 파일 판정 대기**(맨 아래 "구현").

**왜** — 사용자(09-27): "지금은 팅~ 팅~ 이런 소리인데 실제로는 이런 소리가 아닐 거라고 생각한다." 앞선 요청(09-26): "곡괭이질 소리가 현실적이었으면 — 지금은 그냥 띵 띵 소리."
**하나씩 낸다.** 이번 SND-P = 곡괭이가 광석을 치는 평소 소리와 덩이가 빠질 때 소리. 번호만: **MINE-2** Kevin 캐기 동작을 게임에 넣기(09-27 시험 통과, 3D-P 몸과 같이) · **SND-R** 고치는 소리(지금은 곡괭이 소리를 빌려 씀).

## 근거 (잰 값 — 도구 `tools/snd_measure.py`, 받은 소리 `build/refs/snd/`)
| | 지금 Kenney `impactMining` | 실제 광질(한국 MBC 0.85 s 간격 4번 · 파키스탄 0.59 s 간격 5번) | **섞기 B** (사용자 선택) |
|---|---|---|---|
| 한 음이 튀는 정도 (dB) | **37~46** — 2,000~3,400 Hz 음 하나가 종처럼 섬 = "팅" | 12~15 | **평균 10.5 · 가장 큰 것 13.8** |
| 소리 무게중심 (Hz) | 800~2,000 | 약 3,700 | 약 4,300 |
| 모양 | 음이 0.2~0.5 s 울림 | 음 없이 0.02~0.08 s 에 끝나는 "딱" | 딱 + 뒤에 남는 낮은 울림 |

- 실제 소리는 남의 영상이라 비교만 하고 게임에는 넣지 않는다. 현장 잡음(바람·말소리) 때문에 소리가 사라지는 시간과 부스러기 꼬리는 재지 못했다.
- 석탄을 친 무료 녹음은 못 찾았다. 후보 16개는 모두 바위·돌을 친 소리다.

**섞기 B 가 만들어진 과정**: 무료 후보 16개 중 실제와 닮은 6개를 같은 크기로 들려줌 → 사용자 "3·4·6 을 적절하게 섞으면" → `tools/snd_mix.py` 가 한 번의 타격으로 겹침 → A 고르게 / B 묵직하게 / C 날카롭게 / 번갈아 중 사용자 **"섞기 B 가 가장 좋다"**.
- 딱 = 후보6 · Pixabay "Mine Stone with a Pickaxe"(CreatorsHome) · 세기 −12 dB
- 쿵 = 후보4 · Freesound CC0 "pickaxe.wav"(14FPanskaPavlik_Filip) · 0 dB
- 와작 = 후보3 · Freesound CC0 "Pick axe striking rocks #1"(guyburns) · −6 dB

원본마다 타격이 11~15 번 들어 있어서, 뽑는 조합을 바꾸면 조금씩 다른 타격 8 개가 나온다. 60 Hz 아래 마이크 울렁임은 걷어 냈다(귀에 안 들림).

## 어떻게 되나

### 1. 어떤 소리가 바뀌나
| 게임 속 소리 | 지금 | 바꾼 뒤 |
|---|---|---|
| 평소 "콱" (괴물 6 m) | Kenney · 크기 0.8 · 높이 ±7 % | **섞기 B 8 개 번갈아** · 높이 ±7 % 그대로 |
| 덩이가 빠질 때 | Kenney 낮게(0.8 배) · 크기 1.0 | **섞기 B** 낮게(0.8 배) · 크기 1.0 |
| 고치는 소리(REP) | Kenney 를 빌려 씀 | 섞기 B 를 빌려 씀 (고치는 소리 차례 SND-R 까지) |
| 미끄러질 조짐 "딸각" | Kenney 작고 높게(0.3 · 1.9 배) | **Kenney 그대로 (물을 것 1)** |
| 미끄러짐 "쨍" (괴물 25 m) | Kenney 크고 높게(1.0 · 1.5 배) | **Kenney 그대로 (물을 것 1)** |

"쨍"을 Kenney 그대로 두자는 까닭: 곡괭이가 바위에 미끄러질 때는 쇠가 튕기면서 울리는 소리가 난다. 평소 소리와 확 달라야 "실수했다"는 것도 바로 알 수 있다.

### 2. 크기 — 평소 "콱"은 걷기 발소리 크기로
새 소리는 음 없이 짧게 끝나서 평균 크기가 Kenney 의 1/2~1/4 이다(짧은 창 평균: 새 0.06~0.16, Kenney 0.27 이상, 둘 다 최대값 0.9 로 맞춘 뒤).
- 지금 검사 `sound_ladder_6db` 는 "숙이기 < 걷기 < 달리기 < 착지 < **타격**, 칸마다 2 배"다. 이 사다리는 괴물이 듣는 거리(2 · 6 · 14 · 20 · 25 m)와 같은 순서를 지킨다(S1, 설계서 sound_design Step 2).
- 그런데 **MINE-1 뒤로 평소 "콱"은 6 m(걷기와 같음)이고 25 m 는 "쨍"뿐**이다. 사다리 맨 위 칸은 이제 "쨍"의 자리다.
- 그래서 사다리를 이렇게 바꾼다(**물을 것 3**).
  - 숙이기 < 걷기 < 달리기 < 착지 < **쨍**, 칸마다 2 배.
  - 평소 **"콱"은 걷기 발소리의 ½~2 배 안**(같은 6 m 이니 비슷한 크기).
  - 새 소리를 억지로 키울 필요가 없어서 원음 모양을 지킨다.
- 8 개는 짧은 창 평균 크기를 서로 같게 맞춘다. 봉우리가 0.95 를 넘으면 그 파일만 조금 낮춘다.
- "콱"이 들리는 거리도 **25 m → 6 m**(괴물이 듣는 거리와 같게, **물을 것 2**)로 바꾼다. 지금은 괴물은 6 m 밖에서 못 듣는데 소리는 25 m 까지 들려서, "이 소리가 괴물에게 들렸나"를 귀로 판단할 수 없다. 덩이가 빠질 때도 6 m. "쨍"은 25 m 그대로.

### 3. 판정 키 (실행 파일 안, F1 줄에 값 표시)
| 키 | 값 | 처음 |
|---|---|---|
| Shift+[ / Shift+] | 평소 "콱" 크기 × 0.9 / × 1.1 (`Tuning.HIT_VOLUME`) | 검사가 정한 값(걷기의 ½~2 배 안) |

빈 키가 없다(Home End 는 벽 젖음, PgUp PgDn 도 다른 판정 값이 씀). 그래서 ORE-1 반짝임(Shift+, .)처럼 Shift 를 붙이고, 안개 [ ] 는 Shift 없을 때만 먹게 한다.
판정 뒤 받은 숫자를 `Tuning` 에 넣는다. 너무 키우면 검사 `pick_soft_like_walk` 가 FAIL 한다. 그때는 사다리를 다시 묻는다.

## 차례
1. **소리 파일** — `tools/snd_mix.py --game` 이 섞기 B 8 개를 `Assets/Audio/PickHit/pick_hit_000~007.ogg` 로 쓴다(mono 44.1 kHz · OGG q5 — `tools/cut_sounds.py` 와 같은 틀). `Assets/Audio/PickHit/SOURCES.txt` 에 원본 셋의 주소 · 라이선스 · 만드는 법을 적는다. 원본은 저장소에 넣지 않는다(`build/refs/snd/cand/`, `SOURCES.md` 의 주소에서 다시 받음 — Pixabay 원본은 따로 나눠 주면 안 된다). Kenney 다섯 개는 `git mv` 로 `Assets/Audio/PickSlip/` 에 옮긴다(라이선스 파일도 같이).
2. **코드** — `MiningFx`: `slipClips` 와 `SlipSound`(조짐 · 쨍) 추가, `HitSound` 가 들리는 거리를 `MINE_NOISE_SOFT` 로. `Pickaxe.cs` 249 · 366 행의 `PickSound` → `SlipSound`. `BuildM1`: `PickSlip` 폴더를 읽어 `fx.slipClips`. `Tuning`: `HIT_VOLUME` 값 · 주석. `DevHud`: Shift+[ / Shift+] (안개 [ ] 는 Shift 없을 때만).
3. **검사** — 아래 표. `bash tools/quick.sh sound mining`(사보타주 포함) → 전체 `bash tools/build.sh`.
4. **실행 파일 판정** — 아래 확인 목록.

## 검사 (배포 실행 파일)
| 검사 | 무엇 |
|---|---|
| `hit_sound_no_ring` (새) | 타격 파일마다 한 음이 튀는 정도 < 25 dB(`AudioClip.GetData` 로 실행 파일 안에서 잰다 — Kenney 37~46, 섞기 B 7~14) · 파일 8 개 |
| `pick_soft_like_walk` (새) | 평소 "콱"(가장 작은 것 · 가장 큰 것)이 걷기 발소리의 ½~2 배 · 3D 소리가 6 m 에서 0 |
| `sound_ladder_6db` (바꿈) | 숙이기 < 걷기 < 달리기 < 착지 < **쨍**, 칸마다 2 배 |
| 그대로 | `mine_slip_loud` · `mine_soft_noise_6m`(괴물 소음 규칙은 안 바뀜) · 나머지 sound · mining 구간 |

**사보타주**(각각 FAIL 확인): `ringhit`(타격 파일을 Kenney 로 되돌림 → `hit_sound_no_ring`) · `loudhit`(`HIT_VOLUME` × 4 → `pick_soft_like_walk`) · `mute`(그대로, 타격 파일 없음).

## 확인 목록 (실행 파일 판정)
1. 석탄 벽 앞 머리등 아래에서 누르고 캘 때 "콱"이 **실제 같은가**, "팅"이 사라졌나
2. **크기**(Shift+[ / Shift+], F1 줄 `hit vol`) — 발소리와 비교해 너무 작거나 크지 않나
3. 덩이가 빠질 때(낮은 콱)가 어떤가
4. 미끄러질 조짐 "딸각"과 "쨍"(Kenney 그대로)이 새 "콱"과 **확실히 구분되나**
5. 6 m 밖에서는 "콱"이 안 들리는 것이 어색하지 않나

## 바꾸는 파일
| 파일 | 무엇 |
|---|---|
| `tools/snd_mix.py` | `--game` 출력 (섞기 B 8 개 → `Assets/Audio/PickHit/`) |
| `Assets/Audio/PickHit/` | `pick_hit_000~007.ogg` + `SOURCES.txt` (Kenney 는 빠짐) |
| `Assets/Audio/PickSlip/` (새 폴더) | Kenney `impactMining_000~004.ogg` + 라이선스 (옮김) |
| `Assets/Scripts/MiningFx.cs` | `slipClips` · `SlipSound` · 콱 거리 6 m |
| `Assets/Scripts/Pickaxe.cs` | 조짐 · 쨍이 `SlipSound` 를 부름 (두 줄) |
| `Assets/Editor/BuildM1.cs` | `PickSlip` 폴더 읽기 |
| `Assets/Scripts/Tuning.cs` | `HIT_VOLUME` · 주석 |
| `Assets/Scripts/DevHud.cs` | Shift+[ / Shift+] 키 · 안개 [ ] 는 Shift 없을 때만 — **커밋 안 한 `-film` 3 줄은 이번에도 빼고 커밋** |
| `Assets/Scripts/M1Check.cs` | 새 검사 2 · 사다리 바꿈 · 사보타주 2 |
| `docs/지스타2026/03_에셋_라이선스_목록_초안.md` | 효과음 줄 추가(Freesound 2 · Pixabay 1), Kenney 줄 "미끄러짐 소리"로 |

## 없어지는 것 (승인 전 확인)
- **평소 "콱" · 덩이 빠짐 · 고치는 소리에서 Kenney 소리가 빠진다.** 파일은 지우지 않고 `PickSlip/` 로 옮겨 "딸각" · "쨍"에 계속 쓴다.
- **검사 `sound_ladder_6db` 의 맨 위 칸이 "타격" → "쨍"으로 바뀐다.** 평소 "콱"은 새 검사(걷기의 ½~2 배)로 옮긴다.
- **평소 "콱"이 들리는 거리 25 m → 6 m.**

## 안 하는 것
Kevin 캐기 동작을 게임에 넣기(MINE-2) · 고치는 소리(SND-R) · 부스러기가 떨어지는 소리를 따로 넣기 · 괴물이 소리를 듣는 규칙(반경)은 그대로 · Freesound 원본(로그인 필요)으로 바꾸기 — 지금 발소리도 hq 미리듣기로 만들었다(S1).

## 물을 것
1. **"딸각" · "쨍"은 Kenney 소리 그대로** 둘까(쇠가 튕기는 울림 · 평소와 확 다름)? 아니면 이것도 새 소리를 높게 · 크게 해서 쓸까?
2. 평소 "콱"이 **들리는 거리를 25 m → 6 m**(괴물이 듣는 거리와 같게)로 줄여도 되나?
3. **사다리 맨 위를 "쨍"으로**, 평소 "콱"은 걷기 크기로 — 이렇게 바꿔도 되나? (아니면 새 소리를 눌러서 키워 옛 사다리를 지킨다. 그러면 소리 모양이 조금 바뀐다.)

## 구현 (09-28)

- **소리 파일**: `python tools/snd_mix.py --game` → `Assets/Audio/PickHit/pick_hit_000~007.ogg` + `SOURCES.txt`. 8개의 짧은 창(1024 샘플) 크기를 **모두 0.090 으로 같게** 맞췄다 — 제안서대로 "가운데값에 맞추고 봉우리가 0.95 를 넘는 것만 낮추기"를 해 보니 가장 뾰족한 파일(001)이 절반 크기(0.090 vs 0.192)가 돼서, 가장 뾰족한 파일의 봉우리가 0.95 가 되는 크기로 전부 맞췄다. Unity 가 파일마다 다시 키우지 않게 `.meta` 의 normalize 를 껐다(Kenney 파일은 켜져 있음 — 그대로). Kenney 다섯은 `git mv` 로 `Assets/Audio/PickSlip/`(GUID 그대로).
- **코드**: `MiningFx` — `slipClips` · `SlipSound`(25 m) · `HitSound` 는 `hitDistance`(= `MINE_NOISE_SOFT` 6 m) · `hitVolume`(판정 키). `Pickaxe` 두 줄 → `SlipSound`. `BuildM1` 이 `PickSlip` 을 읽는다(없으면 멈춤). `DevHud` Shift+[ / Shift+] (안개 [ ] 는 Shift 없을 때만), F1 줄 `hit vol`. 씬 둘은 `MakeScene -force` · `MakeBooth -force` 로 다시 만듦(`Assets/Settings/*` 는 안 번호만 바뀜 — 전에도 다시 만들 때마다 같았다).
- **`HIT_VOLUME` 0.65**: 첫 값 0.36 은 걷기의 0.52~0.58 배(겨우 통과) → 0.65 로 올려 **걷기의 0.91~1.02 배**.
- **검사 실측** (`-only sound`): `sound_ladder_6db` 숙이기 0.0176 < 걷기 0.0407 < 달리기 0.0882 < 착지 0.1892 < **쨍 0.4191**(×2.21) · `pick_soft_like_walk` 콱 0.0379~0.0424 = 걷기 0.0414 의 0.91~1.02 배, 5 m 0.0098 · 7 m 0.00000 · `hit_sound_no_ring` 8 파일, 가장 큰 울림 16.7 dB(6.6~16.7 — 파이썬 `snd_measure.py` 잣대를 C# 로 옮김, 파이썬 판과 1 dB 안으로 맞음). `-only mining` 11 개 그대로 통과(`mine_soft_noise_6m` · `pick_hit_audible` 0.0661).
- **사보타주** (각각 FAIL 확인): `ringhit`(평소 콱 = Kenney → 걷기의 7.7~10.3 배 · 울림 31~46 dB · 파일 5 개) · `farhit`(새로 — 콱 3D 거리 25 m → 7 m 에서 0.0297) · `mute`(파일 0 개). **`loudhit` 은 뺐다** — AudioSource 크기가 1.0 에서 멈춰 ×4 를 넣어도 1.0/0.65 = 1.5 배가 끝이라 걷기의 2 배를 못 넘는다. 즉 **판정 키로 끝까지 올려도 걷기의 약 1.5 배까지**다(그보다 크게 하려면 파일을 키워야 한다 — 그때 사다리를 다시 묻는다). 너무 큰 쪽은 `ringhit` 이 잡는다.
- **알아 둘 것**: 고치는 소리(REP)는 여전히 타격 파일을 빌려 `HIT_VOLUME × (반경 ÷ 25 m)` 로 튼다 — 동발(25 m)도 이제 걷기 크기다(전에는 Kenney 로 걷기의 약 10 배). 고치는 소리 차례(SND-R)에서 바로잡는다.
