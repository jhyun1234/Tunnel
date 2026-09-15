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
    public const float LAMP_FOLLOW_TIME = 0.10f;   // 초, 램프가 시점을 늦게 따라온다
    public static readonly Vector3 LAMP_OFFSET = new Vector3(0.0f, 0.12f, 0.0f); // 카메라 기준, 이마 자리
    public const float LAMP_TOGGLE_TIME = 0.15f;

    // 공기 (LOOK_REFERENCE 4-3, 4-4)
    public static readonly Color AMBIENT_COLOR = new Color(0.1f, 0.12f, 0.2f);
    public const float AMBIENT_ENERGY = 0.03f;
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
    public const float PICK_BOB_SPEED = 12.0f;     // rad/s
    // 소음. 반경 m
    public const float NOISE_PICK = 25.0f;         // 곡괭이가 포켓에 닿은 타격
    public const float NOISE_HUD_FADE = 1.0f;      // 초, 왼쪽 아래 원이 사라지는 시간
    public const float NOISE_HUD_PX_PER_M = 2.0f;  // 반경 1 m 당 지름 px

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
    public const float STALKER_RETREAT_HP = 30.0f;      // 제안값. 이하가 되는 순간 철수. 철수 중 피격은 스턴만 — 체력 0 경로 없음
    public const float STALKER_STUN_S = 1.5f;           // s, 곡괭이 스턴 (Godot, 결정 사항)
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
    public const float STALKER_SQUASH_S = 0.3f;         // s, Unity 전용: 맞으면 몸이 납작해지는 시간 (캡슐용 휘청 표시)
    // Unity 전용 제안값: 괴물 눈 두 개가 약하게 빛난다 — 램프를 꺼도 괴물 자리는 보인다 (사용자 09-15 A+C 결정)
    public const float STALKER_EYE_GLOW = 0.6f;    // Unlit 색 배율
    public static readonly Color STALKER_EYE_COLOR = new Color(0.90f, 0.80f, 0.60f);

    public static float Accel => WALK_SPEED / TIME_TO_TOP_SPEED;
    public static float Decel => WALK_SPEED / TIME_TO_STOP;
    public static float JumpVelocity => Mathf.Sqrt(2.0f * GRAVITY * JUMP_HEIGHT);
}
