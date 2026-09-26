# ART-1 질감 출처 (모두 CC0 — 누구나 · 팔아도 · 출처 안 적어도 됨)

| 파일 | 원본 | 라이선스 |
|---|---|---|
| `textures/art_rock_Rock031_*` | ambientCG Rock031 (2K JPG) https://ambientcg.com/view?id=Rock031 | CC0 1.0 https://docs.ambientcg.com/license/ |
| `textures/art_coal_Rock035_*` | ambientCG Rock035 (2K JPG) https://ambientcg.com/view?id=Rock035 | CC0 1.0 |
| `textures/art_mud_brown_mud_03_*` | Poly Haven brown_mud_03 (2k jpg) https://polyhaven.com/a/brown_mud_03 | CC0 https://polyhaven.com/license |
| `props_tex/*` (차례 3 Blender 물건 질감) | Poly Haven rusty_metal_03 · rusty_painted_metal · weathered_brown_planks · wood_planks_dirt (1k) · ambientCG Rock035 (1K) — `blender/art/prop_textures.py` 가 채도·색을 구움 | CC0 |
| `plaza_src/<id>/textures/*` (차례 3 광장 물건) | Poly Haven 모델 1k: modular_industrial_pipes_01 · modular_electric_cables · caged_hanging_light · industrial_caged_sconce · modular_airduct_circular_01 · rusted_spade_01 · crowbar_01 · sledgehammer_01 · picke_dirty_01 · wooden_crate_01 · wooden_bucket_01 · wooden_ladder · worn_metal_rack (https://polyhaven.com/a/<id>, 2026-09-27 받음) | CC0 https://polyhaven.com/license |
| `plaza_src/meshy_car2/textures/*` · 광차 그물 | Meshy 그림 → 3D (유료 구독 = 소유, 2026-09-27). 넣은 그림 = 우리 Blender 광차(`mine_props.mine_car_v2`) 세 방향. 원본 `Documents/MineTunnel/mesh/props/meshy_car2.glb`, 기록 `MINER_ASSET_PIPELINE.md` | Meshy 유료 |
| `plaza_props.gltf` · `.bin` | 위 Poly Haven 모델 그물 + Blender 코드로 만든 것(`blender/art/mine_props.py` · `make_plaza_props.py`), 판 글자 = Pretendard(OFL, `Assets/Fonts/`) | CC0 + 우리 것 |

이름 규칙: `_DiffRough.png` = 색(RGB) + 거칠기(A — 원본 Roughness 를 알파에 합침, 셰이더가 읽는 횟수를 줄이려고) · `_nor_gl` 노멀(OpenGL). `Assets/Editor/TextureImportRules.cs` 가 이름으로 임포트 설정을 정한다.
고른 날: 2026-09-27 (사용자, `docs/그림/ART1_질감_후보.png` 에서 벽 2 · 석탄 1 · 바닥 2).
셰이더 `Assets/Shaders/HexTile.hlsl` 는 mmikk/hextile-demo(MIT) 방법 — 알림은 파일 머리에.
