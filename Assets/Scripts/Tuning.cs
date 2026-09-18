using UnityEngine;

// Godot scripts/Tuning.gd 에서 옮긴 값. 이름을 그대로 둬 MIGRATION_NOTES 8절과 대조한다.
// 마일스톤 1(이동 · 헤드램프 · 안개)에 쓰는 것만 옮겼다. 나머지는 쓰는 기능이 생길 때 옮긴다.
// "Unity 전용" 표시가 없는 값은 Godot 값 그대로다.
public static class Tuning
{
    // 이동
    public const float WALK_SPEED = 4.5f;          // m/s
    public const float RUN_SPEED = 7.0f;           // Godot STANCE["run"].speed
    public const float CROUCH_SPEED = 2.0f;        // Godot STANCE["crouch"].speed
    public const float TIME_TO_TOP_SPEED = 0.12f;  // 초
    public const float TIME_TO_STOP = 0.10f;       // 초
    public const float AIR_CONTROL = 0.25f;
    public const float JUMP_HEIGHT = 1.0f;         // m
    public const float GRAVITY = 24.0f;            // m/s^2
    public const float MOUSE_SENSITIVITY = 0.0022f; // rad / 마우스 픽셀
    public const float PITCH_LIMIT_DEG = 89.0f;

    // 몸
    public const float BODY_RADIUS = 0.4f;
    public const float BODY_HEIGHT = 1.8f;
    public const float EYE_HEIGHT = 1.7f;
    public const float CROUCH_EYE = 1.0f;
    public const float CROUCH_TIME = 0.15f;
    public const float STAMINA_MAX = 100.0f;
    public const float STAMINA_RUN = 20.0f;        // /s 달리면 닳음
    public const float STAMINA_WALK = 10.0f;       // /s 걸으면 참
    public const float STAMINA_IDLE = 20.0f;       // /s 서 있으면 참
    // Unity 전용 (제안서 UI-1b, 설계서 ui_ux Step 2 스태미나 줄): 숫자 없이 몸으로. 걸을 때 램프가 끄덕이고(Godot LAMP_BOB 0.01° 는
    // 14 m 벽에서 2 mm 라 안 보이는 값 — 새로 정한다), 스태미나 "곧" 단계면 폭 3배, 탈진하면 눈이 내려가고 시야가 바닥으로 숙여지며 숨 박자로 화면이 들썩인다
    public const float LAMP_BOB_DEG = 0.6f;        // 도, 걷기 끄덕임 폭 — 사용자가 실행 파일 안 7/8 키로 찾은 값 (09-16 1차 판정, 제안 0.4)
    public const float LAMP_BOB_SOON_MUL = 3.0f;   // 곧 단계 배율
    public const float STAMINA_SOON = 50.0f;       // 이하면 곧 단계
    public const float EXHAUST_EYE = 1.2f;         // m, 탈진 눈높이 (숙이기 1.0 과 헷갈리지 않게)
    public const float EXHAUST_TIME = 0.3f;        // s, 내려가고 올라오는 시간
    // 1차 판정(09-16): 눈높이만 내리고 램프만 20° 숙이니 "숙이기와 헷갈린다, 바닥을 비추는 5 초가 없다" → 시야(카메라) 자체를 바닥으로 숙이고
    // 숨 박자로 화면을 위아래로 들썩인다(사용자 "시야 카메라 바운스"). 마우스 시점은 그 위에서 그대로 된다. 램프는 카메라를 따라오니 저절로 바닥
    public const float EXHAUST_LOOK_DOWN_DEG = 25.0f; // 도, 탈진하면 시야가 아래로 숙여지는 각 (제안값)
    public const float EXHAUST_BREATH_M = 0.03f;     // m, 숨 한 번에 머리가 오르내리는 폭 (제안값: 곡괭이 걷기 흔들림 0.02 보다 크게)
    public const float EXHAUST_BREATH_DEG = 1.5f;    // 도, 숨 한 번에 시야가 끄덕이는 각 (제안값)
    public const float EXHAUST_BREATH_S = 0.7f;      // s, 숨 한 번 (헐떡임 ≈ 85회/분, 제안값)
    // 2차 판정(09-16): "탈진 전과 시야가 같아 보인다" → 흐릿함 + 시점은 좌우만(위아래 잠금) — 옆에서 오는 괴물은 소리로만.
    // 3차 판정(09-16): 시야각 절반(80° → 40°)은 뜻이 아니었다 → 원복. 대신 **램프 세기가 빠른 심장 박동처럼 오르내린다**(아래 LAMP_EXHAUST_*). 좌우 90° 는 답답 → 120°
    public const float EXHAUST_BLUR_RADIUS = 1.5f;   // 가우시안 흐림 반지름 (URP DepthOfField, 0.5~1.5). 손의 곡괭이(오버레이 카메라)는 안 흐려진다
    public const float EXHAUST_BLUR_START = 0.3f;    // m, 이 거리부터 흐려지기 시작
    public const float EXHAUST_BLUR_END = 2.5f;      // m, 이 거리부터 완전히 흐림
    public const float EXHAUST_YAW_LIMIT_DEG = 120.0f; // 탈진 시작 방향에서 좌우로 이만큼만 돌아본다 (3차 판정: 90 은 답답)
    public const float LAMP_EXHAUST_MIN = 15.8f;     // 탈진 램프 세기 최소 — 사용자가 −/= 키로 찾은 값(75.2 ÷ 1.25^7)
    public const float LAMP_EXHAUST_MAX = 38.5f;     // 최대 (75.2 ÷ 1.25^3)
    public const float EXHAUST_PULSE_S = 0.5f;       // s, 박동 하나 (120회/분, 제안값). 박동 순간 MAX 로 뛰고 다음 박동까지 MIN 으로 잦아든다
    public const float BREATH_SOON_MUL = 0.3f;       // 곧 단계(≤ STAMINA_SOON)에도 숨 들썩임을 이 배율로 (2차 판정: "작게 넣어라")

    public const float GRID_CELL = 7.0f;           // m, 조각 한 칸
    public const float CAMERA_FOV = 80.0f;         // Godot Player.tscn Camera3D (세로 fov)

    // 헤드램프
    // 원뿔 반각. Godot 40 → 60 (사용자 09-14: 원형 마스크 문제를 옮기지 않게 넓게 시작해서 조인다).
    // Unity Light.spotAngle 은 전체각이라 ×2 로 넣는다.
    public const float LAMP_ANGLE_DEG = 60.0f;
    public const float LAMP_INNER_FRAC = 0.3f;     // Unity 전용: 안쪽 원뿔 = 전체각 × 이 값. Godot LAMP_ATTEN(0.45) 대응이 없어 대신한다
    public const float LAMP_RANGE = 14.0f;         // m
    // Unity 전용 값. Godot 5.0 은 거리 감쇠 0.6(거리^-0.6)이었고 URP 는 거리 제곱 고정이라 값이 옮겨지지 않는다.
    // 사용자 판정 146.8 (09-14 1차, 노멀맵 버그 상태) → 75.2 (= 146.8 ÷ 1.25^3, 09-14 재판정)
    public const float LAMP_ENERGY = 75.2f;
    // Unity 전용: 가까운 면 감광. URP 는 거리 제곱 감쇠라 벽에 붙으면 화면이 하얗게 탔다(사용자 09-14 "램프를 낮춰도 매우 밝다",
    // 실측 벽 앞 탄 픽셀 45 %). 원뿔 안 광선 9개로 비춘 면까지 거리 d 를 재고 세기에 평균 min(1, (d/REF)^POW) 을 곱한다.
    // POW 1.4 = 2 − Godot LAMP_DIST_ATTEN 0.6 — 가까운 면의 밝기 비율이 Godot 곡선과 같아진다. 충돌체가 있는 면만 잰다(갱목 기둥은 없음).
    // 실측(09-14 -sweep, 램프 75.2, 벽 앞 탄 픽셀 · 갱도 밝기): 감광 없음 45.1 % · 0.0529 / REF 2 = 9.4 % · 0.0529 / REF 3 = 2.8 % · 0.0520 /
    // REF 4 = 1.3 % · 0.0515 / REF 4 POW 1.0 = 7.0 % / REF 6 = 0.4 % · 0.0469(갱도가 10 % 어두워짐). Godot 에서 온 REF 4 · POW 1.4 로 둔다.
    // (발광점을 카메라 뒤로 빼는 방법은 실측으로 기각: 뒤로 0.35 m 에서 탄 픽셀 45 → 55 %, 원뿔이 벽을 더 넓게 덮을 뿐)
    public const float LAMP_NEAR_REF = 4.0f;       // m, 이보다 먼 면은 감광 없음
    public const float LAMP_NEAR_POW = 1.4f;
    public const float LAMP_NEAR_TIME = 0.15f;     // 초, 감광이 따라가는 시간 — 광선이 기둥 가장자리를 넘을 때 깜빡이지 않게
    public static readonly Color LAMP_COLOR = new Color(1.00f, 0.96f, 0.88f);
    public const bool LAMP_SHADOW = true;
    // Unity 전용 (제안서 3D-②, 09-17): 헤드램프 그림자 편차. URP 기본(깊이 0.1 · 법선 0.5)이면 12만 면 괴물 몸이 제 그림자를 제 살에
    // 얼룩(shadow acne)으로 찍어 살이 검게 지직거린다(2 m 정면 밝기 그림자 켬÷끔 0.58). 값은 `Tunnel.exe -sweep -bias` 스윕으로 고른다
    // 스윕(09-17) 비율: 깊이 0.1·법선 0.5 = 0.58 (URP 기본) · 0.6·0.5 = 0.84 · 1.0·0.5 = 0.88~0.90 · **1.0·0.25 = 0.956** · 1.0·0 = 0.94 · 1.5·0.25 = 0.94 · 2.0·0.25 = 0.92.
    // 법선 편차는 키울수록 나빠진다(0.5 → 2.0 에서 0.58 → 0.31). 깊이 1.0 을 넘겨도 더 안 좋아진다 → 1.0 · 0.25
    public const float LAMP_SHADOW_DEPTH_BIAS = 1.0f;
    public const float LAMP_SHADOW_NORMAL_BIAS = 0.25f;
    public const float STALKER_ACNE_MIN_RATIO = 0.85f;   // 제안값: 2 m 정면 몸 밝기, 그림자 켬÷끔 이 값 이상이면 얼룩 없음 (실측 0.90~0.96)
    public const float STALKER_BURN_MAX = 0.03f;         // 제안값: 2 m 정면 화면의 하얗게 탄 픽셀 비율 상한. 얼룩 걷힌 뒤 흰 뼈가 램프에 타서 1.45 % (얼룩 있을 땐 0.26 %) — 뼈 밝기는 사용자 판정
    public const float LAMP_FOLLOW_TIME = 0.10f;   // 초, 램프가 시점을 늦게 따라온다
    public static readonly Vector3 LAMP_OFFSET = new Vector3(0.0f, 0.12f, 0.0f); // 카메라 기준, 이마 자리
    public const float LAMP_TOGGLE_TIME = 0.15f;

    // 공기 (LOOK_REFERENCE 4-3, 4-4)
    public static readonly Color AMBIENT_COLOR = new Color(0.1f, 0.12f, 0.2f);
    public const float AMBIENT_ENERGY = 0.03f;
    public const bool DEVHUD_START_VISIBLE = false;  // Unity 전용 (UI-1d, 설계서 Step 6 빌드 규칙): 실행하면 갱도 화면, F1 로 켠다. 사보타주 hudon 이 true 로
    public static readonly Color BACKGROUND = new Color(0.02f, 0.02f, 0.03f);
    public const float FOG_DENSITY = 0.03f;        // 거리 안개 (Exponential)
    public static readonly Color FOG_COLOR = new Color(0.006f, 0.008f, 0.008f);
    // 부피 안개 (패키지 com.cqf.urpvolumetricfog). Godot 0.012 는 단위가 달라 옮겨지지 않는다 (0.012 = 갱도 끝이 흰 막).
    // 사용자 판정(09-14 M1, 램프 146.8) 0.00089 (= 0.003 ÷ 1.5^3). 노멀맵 버그를 고친 뒤에도 "이대로 간다"고 확정 (09-14)
    public const float VOLFOG_DENSITY = 0.00089f;
    public const float VOLFOG_ANISOTROPY = 0.6f;
    public const float VOLFOG_SCATTERING = 1.0f;   // Unity 전용: 패키지 VolumetricAdditionalLight 기본값
    public const float VOLFOG_DISTANCE = 40.0f;    // Unity 전용: Godot PIECE_VIEW_RANGE 와 같게
    // 눈의 어둠 적응 (Godot #32 수정 2, Atmosphere.gd). 램프를 끄면 환경광이 DARK_ADAPT_TIME 에 걸쳐 DARK_ADAPT_AMBIENT 로 오르고
    // 거리 안개가 DARK_ADAPT_FOG 로 짙어진다(환경광은 거리가 없어 먼 곳은 안개로 잠근다). 켜면 즉시 평소(눈부심).
    // 사용자 09-15 M4 판정 "램프를 끄면 아무것도 안 보여 물러나는 것을 볼 수 없다" → 옮긴다. Godot 값 그대로 출발
    // Godot 3.0 은 Unity 에서 화면 밝기 0.0012 (Godot 실측 0.025 의 1/20, 09-15 스윕: 3.0 → 0.0012 · 8.0 → 0.0241 · 16.0 → 0.1269).
    // 사용자 판정(09-15) 실행 파일에서 1/2 키로 직접 찾음 → 6.4
    public const float DARK_ADAPT_AMBIENT = 6.4f;
    public const float DARK_ADAPT_TIME = 4.0f;     // 초
    public const float DARK_ADAPT_FOG = 0.45f;     // 적응했을 때 거리 안개 밀도 — 2 m 41 %·4 m 17 %·6 m 7 % 만 보인다
    public const float ADJ_SATURATION = 0.75f;
    public const float VIGNETTE = 0.35f;

    // ---- 채굴 (M2). Godot Tuning.gd 채굴·자갈·광맥 포켓·곡괭이·소음 절 ----
    public const int MAP_SEED = 7;                 // 포켓 회전 난수는 MAP_SEED + 100
    public const float MINE_DAMAGE = 25.0f;        // 1회 타격
    public const float POCKET_HEALTH = 50.0f;      // 2타 — 첫 타에 자갈, 둘째 타에 덩이가 빠진다
    public const float MINE_RANGE = 3.0f;          // m
    // 초, 휘두르기 한 번 전체(들기 + 내려치기 + 멈춤 + 되돌리기). 연타해도 이보다 빠르지 않다. Godot 0.35 = 내려치기 + 되돌리기
    public static float MINE_COOLDOWN => PICK_WINDUP_TIME + PICK_DOWN_TIME + PICK_HITSTOP_TIME + PICK_UP_TIME;
    public const float HIT_RECOIL = 0.12f;         // m, 맞은 포켓이 밀리는 거리
    public const float HIT_RECOIL_TIME = 0.10f;
    public const float CHUNK_SPIN = 4.0f;          // rad/s
    public const float CHUNK_FADE = 0.5f;          // 초, 자갈이 줄어들며 사라지는 시간
    public const int CHUNK_LIMIT = 40;             // 살아 있는 자갈 상한
    // 먼지. Godot(0.22 m 알 12·60개)을 그대로 옮기니 밝은 점으로 보여 "먼지인지 모르겠다"(사용자 09-14) →
    // Unity 전용: 크고 옅은 뭉게가 천천히 퍼지며 커진다. 알이 커진 만큼 수는 줄였다
    public const int HIT_DUST = 6;                 // 알, 평타 먼지
    public const int BREAK_DUST = 24;              // 알, 덩이가 빠질 때 먼지
    public const float DUST_SIZE_MIN = 0.35f;      // m
    public const float DUST_SIZE_MAX = 0.8f;
    public const float DUST_GROW = 2.0f;           // 수명 끝의 크기 배율
    public const float DUST_LIFE_MIN = 1.6f;       // 초
    public const float DUST_LIFE_MAX = 2.4f;
    public const float DUST_SPEED_MIN = 0.2f;      // m/s
    public const float DUST_SPEED_MAX = 0.9f;
    public const float DUST_GRAVITY = 0.03f;       // 중력 배율 — 떠 있다가 아주 천천히 가라앉는다
    public const float DUST_DRAG = 1.5f;
    public static readonly Color DUST_COLOR = new Color(0.40f, 0.37f, 0.33f, 0.30f);
    public const float SHAKE_AMOUNT = 0.06f;       // m, 덩이가 빠질 때만 흔든다
    public const float SHAKE_TIME = 0.15f;
    public const int CHIP_PER_HIT = 2;
    public const float CHIP_POP = 2.4f;            // m/s
    public const float CHIP_LIFE = 1.2f;           // 초
    // 자리당 켜질 확률. Godot 0.10 — M2 판정용 갱도(자리 24)는 전부 켠다 (사용자 09-14)
    public const float POCKET_CHANCE = 1.0f;
    public const float POCKET_WALL_OUT = 0.12f;    // m, 자리에서 통로 쪽으로 내미는 거리 — 벽 요철에 파묻히지 않게
    public const float POCKET_MESH_SCALE = 1.2f;   // Godot OrePocket.tscn Mesh 배율
    public const float POCKET_RADIUS = 0.16f;      // Godot OrePocket.tscn 충돌 구
    public const float ORE_RADIUS = 0.12f;         // Godot Ore.tscn 충돌 구
    public const float POCKET_POP_OUT = 1.4f;      // m/s, 통로 쪽으로 튀는 속도
    public const float ORE_POP_UP = 2.2f;          // m/s
    public const float ORE_POP_SIDE = 0.6f;        // m/s
    public const float ORE_SPIN = 4.0f;            // rad/s
    public const float ORE_ROLL_DAMP = 4.0f;       // 구르기 감쇠 — 1~1.5 m 에서 멎게 (Godot 실측)
    public const float ORE_MAGNET_DELAY = 1.5f;    // 초, 튀어나온 뒤 이만큼은 안 빨려온다 — 구르는 것을 볼 새
    public const float ORE_MAGNET_RANGE = 1.8f;    // m
    public const float ORE_PULL_SPEED = 6.0f;      // m/s
    public const float ORE_COLLECT_DIST = 0.35f;   // m
    // 곡괭이 뷰모델. Unity 는 카메라 앞이 +Z 라 Godot PICK_POS z(-0.60)와 X 축 회전 부호를 뒤집었다
    public static readonly Vector3 PICK_POS = new Vector3(0.32f, -0.42f, 0.60f);
    public const float PICK_SCALE = 0.75f;
    public const float PICK_TILT_DEG = 12.0f;      // Godot -12, 앞으로 눕힌 각
    public const float PICK_YAW_DEG = 90.0f;       // 머리 긴 축(X)을 앞뒤로 세운다
    public const float PICK_ROLL_DEG = 10.0f;      // 자루 끝을 앞으로 기울인 각
    public const float PICK_SWING_DEG = 55.0f;     // 내려치는 각
    public const float PICK_DOWN_TIME = 0.12f;     // 초, 내려치기 — 끝나는 순간이 타격
    public const float PICK_UP_TIME = 0.23f;       // 초, 되돌리기
    // 무게 (사용자 09-14 "휘두르기 가볍다"). Unity 전용: 치기 전에 뒤로 들고, 맞는 순간 잠깐 멈추고, 매 타격 화면을 작게 흔든다
    public const float PICK_WINDUP_DEG = 20.0f;    // 뒤로 드는 각
    public const float PICK_WINDUP_TIME = 0.08f;   // 초 — 누르고 타격까지 = 들기 + 내려치기 0.20 초
    public const float PICK_HITSTOP_TIME = 0.06f;  // 초, 벽에 박힌 채 멈춤
    public const float PICK_HIT_SHAKE_AMOUNT = 0.02f;   // m, 평타 흔들림 (덩이가 빠질 때는 SHAKE_AMOUNT)
    public const float PICK_HIT_SHAKE_TIME = 0.08f;
    // 조준 보정 (사용자 09-14 "정확하게 캐는 게 쉽지 않다"). Unity 전용: 곡괭이 판정을 이 반지름의 구로 쏜다 — 포켓 가장자리에서 이만큼 빗나가도 맞는다
    public const float PICK_AIM_RADIUS = 0.12f;    // m
    // 곡괭이 전용 등 (사용자 09-14 "곡괭이가 하얗게 뜨는 게 거슬린다"). Unity 전용: 헤드램프는 곡괭이를 안 비추고, 이 약한 등만 비춘다
    public const float PICK_LIGHT_ENERGY = 3.0f;
    public const float PICK_LIGHT_RANGE = 2.0f;    // m
    // 타격음 (Kenney Impact Sounds, CC0). 3D 소리, 소음 반경(NOISE_PICK)에서 0 이 된다
    public const float HIT_VOLUME = 0.8f;
    public const float HIT_PITCH_JITTER = 0.07f;   // 매번 같은 소리로 안 들리게
    public const float HIT_BREAK_PITCH = 0.8f;     // 덩이가 빠지는 타격은 낮고 크게
    public const float HIT_MIN_DISTANCE = 2.0f;    // m, 이 안에서는 최대 음량
    public const float PICK_BOB_AMOUNT = 0.02f;    // m
    // PICK_BOB_SPEED 12 rad/s(Godot)는 지웠다 — 흔들림 위상은 Player.gait(π / 자세별 STEP_INTERVAL)라 발소리와 같은 박자 (사용자 09-16)
    // Unity 전용 (제안서 UI-1a, 설계서 ui_ux Step 2): 곡괭이 내구도. 숫자는 화면에 없다 — 15 이하면 닿은 타격마다 손이 떨리고,
    // 0 이 되는 순간 손에서 조각나 바닥에 떨어졌다 사라진다. 고치기 없음, 새 곡괭이는 상점(나중) — 사용자 09-16 결정
    public const float PICK_DURABILITY_MAX = 60f;   // 사용자 판정 09-16: 100(캐기 50번)은 너무 크다 → 캐기 30번 = 60타
    public const float PICK_WEAR_HIT = 1f;         // 포켓·괴물에 닿은 타격마다. 허공은 안 닳는다
    public const float PICK_WEAR_THROW = 5f;       // 던지기마다
    public const float PICK_SHAKY_BELOW = 15f;     // 이하면 떨림 (타격 15번 = 캐기 7번)
    public const float PICK_SHAKE_AMOUNT = 0.04f;  // m, 뷰모델 무작위 흔들림 (걸을 때 흔들림의 2배). 머리는 안 흔든다
    public const float PICK_SHAKE_S = 0.5f;        // s
    public const int PICK_BREAK_PIECES = 8;        // 부서질 때 튀는 조각 수 (곡괭이 재질, 자갈과 같은 물체)
    public const float PICK_BREAK_POP = 1.5f;      // m/s, 조각이 튀는 속도 — 자갈(2.4)보다 느리게, 손에서 흘러내리듯
    public const float PICK_BREAK_LIFE = 1.5f;     // s, 바닥에 놓였다가 줄어들며 사라지기까지
    public const float PICK_BREAK_SCALE = 0.5f;    // 자갈 메시 기준 크기 — 1.0 이면 0.6 m 앞이라 곡괭이 머리보다 크게 보였다(09-16 캡처)
    // 소음. 반경 m
    public const float NOISE_PICK = 25.0f;         // 곡괭이가 포켓에 닿은 타격
    public const float NOISE_HUD_FADE = 1.0f;      // 초, 왼쪽 아래 원이 사라지는 시간
    public const float NOISE_HUD_PX_PER_M = 2.0f;  // 반경 1 m 당 지름 px
    // ---- S1 발소리·착지음 (제안서 S1, 설계서 sound_design.md Step 2·7). 반경·간격은 Godot Tuning.gd STANCE 표 그대로 ----
    public const float NOISE_STEP = 6.0f;          // m, 걷기 발걸음 반경 (같은 칸 안)
    public const float STEP_INTERVAL = 0.5f;       // s, 걷기 4.5 m/s 에서 2.25 m 마다 한 걸음
    public const float NOISE_STEP_CROUCH = 2.0f;   // Godot STANCE["crouch"].radius — 바로 옆에서만
    public const float STEP_INTERVAL_CROUCH = 1.2f; // Godot STANCE["crouch"].step (설계서 제안값 0.8 보다 Godot 값이 우선)
    public const float NOISE_STEP_RUN = 14.0f;     // Godot STANCE["run"].radius — 두 칸 건너에서도
    public const float STEP_INTERVAL_RUN = 0.32f;  // Godot STANCE["run"].step
    // Unity 전용 제안값. 설계서 Step 2 사다리: 이웃끼리 2배(6 dB), 꼭대기는 HIT_VOLUME 0.8. 파일마다 소리 크기가 달라 검사(-only sound)의 RMS 실측으로 맞춘다
    // 실측(09-16, -only sound): 타격 0.8 = RMS 0.504. 파일 소리 크기가 달라 설계서 값(0.05/0.1/0.2/0.4)으로는 달리기 −27 dB·착지가 타격의 1/8 →
    // 꼭대기 0.504 에서 절반씩 내려 놓은 값. 여유는 맨 아래(숙이기)에 둔다 — 정확히 2배씩이면 프레임 흔들림에 깨진다
    // 타격은 5변주 중 가장 작은 파일(RMS 0.399, 1024 샘플 창)이 꼭대기 — 어느 파일이 나와도 순서가 지켜지게
    public const float STEP_VOLUME_CROUCH = 0.09f;
    public const float STEP_VOLUME_WALK = 0.165f;
    public const float STEP_VOLUME_RUN = 0.36f;
    public const float LAND_VOLUME = 0.75f;        // 던진 곡괭이 착지 — 착지 자리 3D, 반경 NOISE_PICK_LAND 에서 0 (파일은 리미터로 2.5배, cut_sounds.py)
    public const float STEP_PITCH_JITTER = 0.05f;  // 발소리 4변주에 더해 매번 조금 다르게

    // ---- 괴물 (M3 소음 듣는 최소판). Godot Tuning.gd 괴물(#35) 절. 눈·빛·추격·잡기·천장은 다음 마일스톤 ----
    public const float STALKER_R = 0.6f;               // m, 충돌 캡슐 반지름
    public const float STALKER_H = 2.8f;               // m, 충돌 캡슐 높이
    public const float STALKER_SPEED_WANDER = 2.5f;    // m/s, Godot STALKER_SPEED["wander"]
    public const float STALKER_SPEED_INVESTIGATE = 5.0f;   // Godot 4.0. 사용자 판정(09-15) "모델이 들어가고 5.0 이면 무섭겠다" → 5.0
    public const float STALKER_SPEED_SEARCH = 2.5f;
    public const float STALKER_EAR_MUL = 1.0f;         // 소음 반경에 곱함 — 반경 안이면 듣는다
    public const int STALKER_SEARCH_CELLS = 3;         // 수색 범위 (격자 칸)
    public const int STALKER_SPOTS_MIN = 2;            // 수색 곳 수
    public const int STALKER_SPOTS_MAX = 3;
    public const float STALKER_DWELL_S = 2.0f;         // s, 곳마다 머무는 시간
    public const float STALKER_FOUND_M = 2.0f;         // m, 수색 자리에서 이 안이면 들킴 (M3 에서는 '도착' 기준으로만 쓴다)
    public const int STALKER_WANDER_CELLS = 3;         // 배회 반경 (격자 칸)
    public const float STALKER_WANDER_PAUSE_S = 1.0f;  // s, 배회 도착마다 멈춤
    // Unity 전용 (제안서 M3 제안값): 1타 = 방향만, 2타 연속 = 정확 (설계서 v2 Step 5)
    public const float STALKER_HEAR_SOFT_M = GRID_CELL; // m, 첫 소리에 소리 쪽으로 다가가는 거리 (한 칸)
    public const float STALKER_HEAR_CONFIRM_S = 3.0f;   // s, 이 안에 같은 자리에서 한 번 더 들리면 그 자리까지 간다
    public const float STALKER_ARRIVE_M = 0.5f;         // m, 목적지 도착 판정
    public const float STALKER_LANE_X = 2.2f;           // m, 괴물이 다니는 폭 (벽 3.16 − 몸 0.6 − 여유)
    public const float STALKER_STUCK_S = 1.0f;          // s, 이만큼 막혀 있으면 그 자리를 도착으로 친다
    // ---- M4 (②b) 눈·빛·추격·잡기. Godot 그대로 ----
    public const float STALKER_EYE_H = 2.4f;            // m, 눈(시선 레이) 높이
    public const float STALKER_EYE_DEG = 60.0f;         // 눈 원뿔 반각. 램프 켜진 몸만, 시선이 안 가려야
    public const float STALKER_EYE_M = 12.0f;           // m, 눈 사거리
    public const float STALKER_LIGHT_M = 30.0f;         // m, 빛: 켜진 램프가 시선에 들면 그 자리로 천천히(배회 속도)
    public const float STALKER_ALERT_S = 1.0f;          // s, 들키면 포효하고 이만큼 뒤에 추격 — 빠져나갈 틈
    public const float STALKER_SPEED_CHASE = 6.5f;      // m/s. 걷는 사람(4.5)은 잡히고, 달리면(7.0) 5초 벌 수 있다
    public const float STALKER_LOSE_S = 3.0f;           // s, 추격 중 이만큼 못 보면 마지막 자리 조사
    public const float STALKER_CATCH_M = 1.5f;          // m, 잡는 거리 (추격 중)
    // Unity 전용 (제안서 M4 제안값, 설계서 v2 Step 2 교차 검토: 검은 화면 1.0 s 이상, 잡힌 뒤 3.0 s 재시작 — 시네마틱과 일치)
    public const float CATCH_FADE_S = 0.3f;             // s, 잡힌 뒤 검어지는 시간
    public const float CATCH_BLACK_MIN_S = 1.0f;        // s, 검은 화면 최소 (검사 기준)
    public const float CATCH_RESTART_S = 3.0f;          // s, 잡힌 뒤 재시작까지
    public const float CATCH_FADE_OUT_S = 0.5f;         // s, 재시작 뒤 밝아지는 시간
    // ---- M5 (②c) 체력·스턴·철수. 설계서 v2 Step 4·6 (교차 검토 반영) ----
    public const float STALKER_HP = 100.0f;             // 제안값. 곡괭이 3대(75)면 철수선 밑
    public const float STALKER_HIT_DMG = 25.0f;         // 제안값, 곡괭이 한 대
    // 제안값. 이하가 되는 순간 철수. 철수 중에는 못 친다(무적) — 사용자 판정(09-15 M6 F5): "스턴만"이던 규칙은 타이밍 연타로 벽에 못 가게 막혔다
    public const float STALKER_RETREAT_HP = 30.0f;
    // s, 곡괭이 스턴. Godot 1.5(결정 사항) → 사용자 판정(09-15 M6 F5) "1.5 s 는 길다" → 0.5. 밀림 0.2 s 뒤 0.3 s 서서 본다
    public const float STALKER_STUN_S = 0.5f;
    // 사용자 판정(09-15 M5 1차): "포효 0.7 + 뒷걸음 0.8" 은 뒷걸음 뒤 돌진이 '준비 동작'으로 읽혀 "맞아서 밀렸다"가 안 됐다 →
    // 맞는 순간 STALKER_STUN_KNOCK_M 만큼 STALKER_STUN_KNOCK_S 에 밀리고(충격), 남은 시간은 서서 플레이어를 본다. 시네마틱 설계서 Step 4 와 어긋남 — 결정 변경 제안
    public const float STALKER_STUN_KNOCK_M = 1.0f;     // m, Unity 전용 제안값
    public const float STALKER_STUN_KNOCK_S = 0.2f;     // s
    // 사용자 판정(09-15): 스턴마다 다시 걸리니 연타로 1.5 s 안에 세 대를 다 넣어 "너무 쉽다" → 스턴 중 피격은 무효(피해·스턴 없음). 한 번 다가올 때 한 대만 먹힌다
    public const bool STALKER_STUN_IMMUNE = true;
    public const float STALKER_SPEED_RETREAT = 4.0f;    // m/s (Godot STALKER_SPEED["retreat"])
    public const float STALKER_WALL_SPEED = 1.2f;       // m/s, 벽을 기어 오르는 속도 (Godot)
    public const float TUNNEL_ARCH_Y = 4.4f;            // m, 벽이 끝나는 높이 — 여기까지 오르면 사라진다 (Godot)
    public const float TUNNEL_WALL_X = 3.16f;           // m, 보이는 벽까지 (Godot)
    public const float STALKER_RETREAT_MIN_M = 8.0f;    // m, 철수 자리: 플레이어 램프 원뿔 안 8~14 m (교차 검토 승인 2026-09-15)
    public const float STALKER_RETREAT_MAX_M = 14.0f;
    public const float STALKER_REGEN_S = 90.0f;         // s, 제안값. 숨었다가 체력 100 으로 재등장 (층마다 −25 % 는 층이 생길 때)
    // STALKER_SQUASH_S(맞으면 몸 0.3 s 납작, 캡슐 시절 피격 표시)는 3D-③ 에서 지웠다 — 모델 전체를 고무처럼 찌그러뜨렸다. hit 동작이 대신한다 (사용자 승인 09-18)
    // ---- M6 곡괭이 던지기 (#34, 규칙 개정 4). Godot Tuning.gd 그대로. 설계서 v2 Step 4 "착지 소음은 유인" · Step 6 "던지기도 25 + 스턴" ----
    // m/s. Godot 14 → Unity(중력 9.81)에서 실측 8.9 m 는 "멀다"(사용자 09-15 M6 판정) → 사거리 6 m 가 되는 값. 감쇠 1.0 이라 거리는 속도에 비례하지 않는다 — 검사가 잰다
    public const float THROW_SPEED = 9.8f;
    public const float THROW_RANGE_M = 6.0f;            // m, 사용자 판정 사거리 — 검사가 ±0.5 m 로 확인한다 (Unity 전용)
    public const float THROW_UP_DEG = 10.0f;            // 카메라 앞에서 위로
    // THROW_BODY_R 0.15(충돌 구 하나)는 지웠다 — 공만 바닥에 닿아 자루·머리가 바닥을 뚫고 거꾸로 매달렸다(사용자 09-16). 충돌체는 자루·목·머리 상자 3개(BuildM1)
    public const float NOISE_PICK_LAND = 20.0f;         // m, 착지 소음 (광차와 같은 급). 유인 — 배회·수색 중에만 먹힌다 (Stalker.OnNoise)
    public const float THROW_STUCK_S = 3.0f;            // s, 착지 뒤 이만큼 지나면 얼린다 (틈에 끼지 않게)
    public const float CARRY_REACH = 2.5f;              // m, E 가 먹는 거리 (줍기)
    // Unity 전용 (제안서 UI-1c, 설계서 결정 변경 제안 3): 글자 대신 — 이 거리 안이면 던진 곡괭이 머리가 Unlit 로 살짝 빛난다(괴물 눈과 같은 방법)
    public static readonly Color PICK_GLOW_COLOR = new Color(1.0f, 0.85f, 0.5f);   // 녹슨 쇠 + 약간 노랑
    public const float PICK_GLOW = 2.235f;              // 사용자가 7/8 키로 찾은 값 (09-16 1차 판정: 0.3 은 안 보임, 2.235 면 가까이 가면 반짝인다)
    // Unity 전용 제안값: 괴물 눈 두 개가 약하게 빛난다 — 램프를 꺼도 괴물 자리는 보인다 (사용자 09-15 A+C 결정)
    public const float STALKER_EYE_GLOW = 0.6f;    // Unlit 색 배율
    public static readonly Color STALKER_EYE_COLOR = new Color(0.90f, 0.80f, 0.60f);
    // Unity 전용 (제안서 3D-①, 09-17): 괴물 모델 Assets/Tunnel/Monster/miner_rigged.glb (TRELLIS.2 몸 + Mixamo 동작 14개, stage12 로 노멀·PNG 구움)
    public const float STALKER_MODEL_SCALE = 1.5f;          // Godot MINER_SCALE (사용자 09-11 "1.0 은 안 무섭다")
    public const float STALKER_MODEL_YAW = 0f;              // 도. 모델 정면이 이동 방향(+Z)이 아니면 180
    public const string STALKER_MODEL_IDLE = "idle_crouch"; // 멈춰 있을 때 동작. 행동 끄면(DevHud 0·9) 이것부터
    // 3D-② (09-17 판정 "구체 두 개가 눈구멍에 박혀 이질감"): 눈 = 눈구멍 속 작은 빛점. 지름 0.04(눈구멍 폭 0.08 의 절반), 안쪽으로 0.04 m
    // 3D-②b (09-17 판정 "구체 두 개가 너무 잘 보인다"): 눈 구체 없음. 머리 그림의 발광 그림(눈구멍 자리, stage12 4b)이 빛난다.
    // 아래 셋은 사용자가 실행 파일 DevHud 키로 찾는 값 — 7/8 요철 세기 · ,/. 거칠기 배율 · k/l 눈 발광 (StalkerLook.cs)
    public const float STALKER_SKIN_NORMAL_SCALE = 1.95f;   // 사용자가 7/8 키로 찾은 값 (09-18, 1.25^3). 시작값 1.0. glTFast 속성이 아니라 ScaleNormal.shader 로 적용한다
    public const float STALKER_SKIN_ROUGH_MUL = 0.6f;       // 사용자가 ,/. 키로 찾은 값 (09-18). 시작값 1.0
    public const float STALKER_EYE_EMISSION = 0.31f;        // 사용자가 k/l 키로 찾은 값 (09-18 재판정, 눈구멍 자리 고친 뒤). 0.08 은 발광이 광대뼈 넓은 얼룩일 때 값. 시작값 0.6
    public const float STALKER_RELIEF_MIN = 28f;            // 2 m 정면 몸 영역 구조값(이웃 밝기 차×1000) 하한. 실측(09-17): 점토 상태 24.6 · flatskin 26.1 · 요철 그림 30.7 → 그 사이
    public const int STALKER_EYE_BRIGHT_MIN = 1;            // 램프 끄고 5 m 몸 영역에서 밝기 0.1 넘는 표본 픽셀(3픽셀 간격) 수 하한. 사용자 값 발광 0.08 은 어둡다(0.2 문턱에선 1개) → 문턱 0.1 · 1개. dimeyes 0
    public const float STALKER_MODEL_LUM_MAX_14M = 0.02f;   // 제안값(캡슐 13 m 실측 0.009): 램프 끝이라 안 보여야. 첫 실측 0.006
    // 7 m 보임 = 모델을 그렸을 때와 숨겼을 때 같은 화면 영역의 차이. 모델이 검댕처럼 어두워 밝기 자체(첫 실측 0.036)로는 바탕(0.05)과 못 가른다
    public const float STALKER_MODEL_CONTRAST_MIN_7M = 0.010f;   // 제안값: 밝기 차 ≥ 0.010 또는 구조(이웃 밝기 차×1000) 차 ≥ 3
    // ---- 3D-③ 동작 연결 (제안서 docs/제안서_3D3_괴물_동작_연결.md, 승인 09-18). StalkerAnim.cs ----
    // 동작 원래 걸음 빠르기 m/s (모델 크기 1.0). Blender stage5_merge.py 가 제자리로 만들기 전에 잰 값 — Documents/MineTunnel/blender/stage5.log "CLIP natural speed"
    // 게임 괴물은 STALKER_MODEL_SCALE 배 크니 그만큼 빠르다. 재생 배수 = 실제 빠르기 ÷ (이 값 × 크기) 면 발이 안 미끄러진다
    public const float STALKER_CLIP_SPEED_WALK = 0.45f;     // walk_crouch
    public const float STALKER_CLIP_SPEED_RUN = 3.04f;      // run. stage5.log 3.01 → 게임 안 실측(-only anim "ANIM stride": 딛은 발 4.56 m/s ÷ 1.5)으로 고침 — 3.01 이면 발 미끄러짐 0.31 m/s
    public const float STALKER_CLIP_SPEED_CRAWL = 0.57f;    // crawl (벽타기)
    public const float STALKER_ANIM_RUN_ABOVE = 3.0f;       // m/s, 제안값. 이보다 빠르면 run (배회·수색 2.5 는 걷기, 철수 4.0 부터 달리기)
    public const float STALKER_ANIM_STILL = 0.3f;           // m/s, 이보다 느리면 멈춤 동작. 움직임 시작은 2배(0.6)부터 — 경계에서 깜빡이지 않게
    public const float STALKER_ANIM_FADE_S = 0.2f;          // s, 제안값. 두 동작을 겹쳐 넘기는 시간
    public const float STALKER_ANIM_FADE_FAST_S = 0.1f;     // s, 포효·스턴·잡기는 빨리 들어간다
    public const float STALKER_ROAR_START_S = 1.2f;         // s, roar(2.83 s) 중 들킴 1.0 s 동안 틀 구간의 시작 = 두 손이 가장 멀어지는 순간 1.70 s(-only anim 실측 09-18) − 0.5 s
    // 배회 걸음 (걷기 빠르기 이하일 때): 0 = A 웅크려 걷기, 발 맞춤(약 3.7배) · 1 = B 달리기, 발 맞춤(약 0.56배) · 2 = C 웅크려 걷기 STALKER_WALK_RATE_CAP 배까지만(나머지는 미끄러짐). 사용자가 U 키로 고른다
    public const int STALKER_WANDER_GAIT = 0;
    public const float STALKER_WALK_RATE_CAP = 2.0f;
    public const float STALKER_CLIMB_GAP = 0.05f;           // m, 벽타기 때 손발이 닿는 면과 벽 사이 (crawl 을 90° 세워 손발이 벽에)
    public const float STALKER_CLIMB_TILT_S = 0.3f;         // s, 서 있다가 벽에 붙는(세워지는) 시간
    public const float STALKER_ARM_FLOOR_MARGIN = 0.02f;   // m, 손끝이 발바닥 면(벽타기 땐 벽) 위로 이만큼은 떠 있게 — 팔째 들어 올린다 (StalkerAnim.LateUpdate)
    public const float STALKER_ARM_LIFT_STEP = 3f;          // 도, 손끝이 면 아래면 어깨에서 이만큼씩 (최대 30번 = 90°) 들어 올린다
    public const float STALKER_FOOT_SLIP_MAX = 0.4f;        // m/s. 걷기·달리기 중 딛은 발(두 발 중 느린 발)이 땅 위에서 움직이는 빠르기 중앙값 상한. 제안값 0.3 → 실측(09-18) 걷기 0.03 · 달리기 0.29~0.32 로 문턱에 걸려 흔들려 0.4. 사보타주 slide 는 1 m/s 넘게

    public static float Accel => WALK_SPEED / TIME_TO_TOP_SPEED;
    public static float Decel => WALK_SPEED / TIME_TO_STOP;
    public static float JumpVelocity => Mathf.Sqrt(2.0f * GRAVITY * JUMP_HEIGHT);
}
