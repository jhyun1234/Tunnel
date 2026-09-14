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
    // 실측(09-14 -sweep, 부피 안개 끔, 출발 자리 화면 평균 밝기): 35 = 0.0029 · 140 = 0.0166 · 280 = 0.0330 · 560 = 0.0597 · 1120 = 0.0985.
    // Godot 골든 play_09_lamp 0.063 에 가장 가까운 560. 거리 감쇠 곡선이 달라 가까운 벽·먼 곳 비율은 사람이 본다 (DevHud - =)
    public const float LAMP_ENERGY = 560.0f;
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
    // 부피 안개 (패키지 com.cqf.urpvolumetricfog). Godot 0.012 는 단위가 달라 옮겨지지 않는다.
    // 실측(09-14 -sweep, 램프 560, 화면 밝기 배율 · 구조 남음): 0.012 = ×4.9 · 70 %(갱도 끝이 흰 막) · 0.006 = ×3.4 · 83 % ·
    // 0.003 = ×2.4 · 92 % · 0.0015 = ×1.7 · 97 %(거의 안 보임). 빛줄기가 보이면서 끝의 어둠이 남는 0.003 에서 출발. DevHud [ ] 로 판정
    public const float VOLFOG_DENSITY = 0.003f;
    public const float VOLFOG_ANISOTROPY = 0.6f;
    public const float VOLFOG_SCATTERING = 1.0f;   // Unity 전용: 패키지 VolumetricAdditionalLight 기본값
    public const float VOLFOG_DISTANCE = 40.0f;    // Unity 전용: Godot PIECE_VIEW_RANGE 와 같게
    public const float ADJ_SATURATION = 0.75f;
    public const float VIGNETTE = 0.35f;

    public static float Accel => WALK_SPEED / TIME_TO_TOP_SPEED;
    public static float Decel => WALK_SPEED / TIME_TO_STOP;
    public static float JumpVelocity => Mathf.Sqrt(2.0f * GRAVITY * JUMP_HEIGHT);
}
