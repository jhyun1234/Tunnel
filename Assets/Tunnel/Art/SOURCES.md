# ART-1 질감 출처 (모두 CC0 — 누구나 · 팔아도 · 출처 안 적어도 됨)

| 파일 | 원본 | 라이선스 |
|---|---|---|
| `textures/art_rock_Rock031_*` | ambientCG Rock031 (2K JPG) https://ambientcg.com/view?id=Rock031 | CC0 1.0 https://docs.ambientcg.com/license/ |
| `textures/art_coal_Rock035_*` | ambientCG Rock035 (2K JPG) https://ambientcg.com/view?id=Rock035 | CC0 1.0 |
| `textures/art_mud_brown_mud_03_*` | Poly Haven brown_mud_03 (2k jpg) https://polyhaven.com/a/brown_mud_03 | CC0 https://polyhaven.com/license |

이름 규칙: `_DiffRough.png` = 색(RGB) + 거칠기(A — 원본 Roughness 를 알파에 합침, 셰이더가 읽는 횟수를 줄이려고) · `_nor_gl` 노멀(OpenGL). `Assets/Editor/TextureImportRules.cs` 가 이름으로 임포트 설정을 정한다.
고른 날: 2026-09-27 (사용자, `docs/그림/ART1_질감_후보.png` 에서 벽 2 · 석탄 1 · 바닥 2).
셰이더 `Assets/Shaders/HexTile.hlsl` 는 mmikk/hextile-demo(MIT) 방법 — 알림은 파일 머리에.
