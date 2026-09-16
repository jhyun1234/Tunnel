using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

// 1인칭 이동 · 마우스 시점 · 점프 · 세 자세 · 스태미나 · 광석 수 · 화면 흔들림. Godot Player.gd 를 옮겼다.
// 입력은 키보드·마우스 장치에서만 읽는다 — 검사(M1Check)도 가상 장치로 같은 길을 지난다.
[RequireComponent(typeof(CharacterController))]
public class Player : MonoBehaviour
{
    public Transform head;                 // 눈 자리. 카메라가 붙는다
    public float stamina = Tuning.STAMINA_MAX;
    public bool exhausted;                 // 0 에서 Shift 를 계속 눌렀다 — 100 찰 때까지 못 움직인다 (시점·숙이기는 됨)
    public string stance = "walk";         // crouch / walk / run
    [System.NonSerialized] public int ore; // 캔 광석 수
    [System.NonSerialized] public bool frozen; // 잡힌 동안 — 입력·시점 잠금 (Stalker 가 켜고 끈다)
    [System.NonSerialized] public int steps;       // 낸 발걸음 수 (검사용)
    [System.NonSerialized] public float stepNoiseMul = 1f;   // 사보타주 quietfeet: 0 이면 발소리 반경 0 = 소음 아님
    [System.NonSerialized] public bool stagger = true;        // 사보타주 nostagger 가 끈다 — 탈진해도 자세 없는(옛) 상태
    [System.NonSerialized] public float blurMul = 1f;         // 검사가 흐림만 끄고 비교한다
    [System.NonSerialized] public float lookDown, breathAmp, pant;   // 탈진 자세: 시야 숙임 각 · 숨 들썩임 폭(0~1) · 탈진 정도(0~1, 시야각·흐림·시점 잠금) (검사가 읽는다)
    float breathPhase, pantYaw;
    Camera cam;
    DepthOfField dof;                      // 탈진 흐림. 씬 Volume 의 실행 중 프로필에 넣는다 — 에셋은 안 바뀐다

    CharacterController cc;
    Vector3 velocity;
    float pitch;
    float eye = Tuning.EYE_HEIGHT;
    float shakeLeft, shakeAmount, shakeSpan;
    [System.NonSerialized] public float gait;   // 걸음 위상(라디안). π 마다 한 발이 땅에 닿는다 — 발소리와 곡괭이 흔들림이 이 하나를 같이 본다. 멈추면 0
    bool wasMoving;

    public CharacterController Controller => cc;
    public float Speed => new Vector2(velocity.x, velocity.z).magnitude;

    public void AddOre(int count) => ore += count;

    // 화면을 짧게 흔든다. 카메라가 아니라 머리 위치만 — 조준은 그대로다
    public void Shake(float amount, float span)
    {
        shakeAmount = amount;
        shakeSpan = span;
        shakeLeft = span;
    }

    void Awake()
    {
        cc = GetComponent<CharacterController>();
        cc.radius = Tuning.BODY_RADIUS;
        SetHeight(Tuning.BODY_HEIGHT);
        Cursor.lockState = CursorLockMode.Locked;
    }

    void Start()
    {
        cam = head.GetComponentInChildren<Camera>();
        var volume = FindFirstObjectByType<Volume>();
        if (volume != null && cam != null)
        {
            if (!volume.profile.TryGet(out dof))
                dof = volume.profile.Add<DepthOfField>(true);
            dof.mode.Override(DepthOfFieldMode.Gaussian);
            dof.gaussianStart.Override(Tuning.EXHAUST_BLUR_START);
            dof.gaussianEnd.Override(Tuning.EXHAUST_BLUR_END);
            dof.gaussianMaxRadius.Override(0f);
            dof.highQualitySampling.Override(true);
            dof.active = false;
        }
    }

    // 마우스 시점. 탈진 중(pant)에는 위아래를 잠그고 좌우는 탈진 시작 방향에서 ±EXHAUST_YAW_LIMIT_DEG 만 — 옆에서 오는 것은 소리로만 (사용자 09-16)
    public void Look(Vector2 d)
    {
        float yaw = transform.eulerAngles.y + d.x * Tuning.MOUSE_SENSITIVITY * Mathf.Rad2Deg;
        if (pant > 0f)
            yaw = pantYaw + Mathf.Clamp(Mathf.DeltaAngle(pantYaw, yaw), -Tuning.EXHAUST_YAW_LIMIT_DEG, Tuning.EXHAUST_YAW_LIMIT_DEG);
        transform.rotation = Quaternion.Euler(0f, yaw, 0f);
        if (pant <= 0f)
            pitch = Mathf.Clamp(pitch - d.y * Tuning.MOUSE_SENSITIVITY * Mathf.Rad2Deg, -Tuning.PITCH_LIMIT_DEG, Tuning.PITCH_LIMIT_DEG);
    }

    void Update()
    {
        var kb = Keyboard.current;
        var mouse = Mouse.current;
        float dt = Time.deltaTime;
        if (frozen)
            return;

        if (mouse != null)
        {
            if (Cursor.lockState == CursorLockMode.Locked)
            {
                Look(mouse.delta.ReadValue());
            }
            if (mouse.leftButton.wasPressedThisFrame)
                Cursor.lockState = CursorLockMode.Locked;
        }
        if (kb == null)
            return;
        if (kb.escapeKey.wasPressedThisFrame)
            Cursor.lockState = CursorLockMode.None;

        Vector2 input = Vector2.ClampMagnitude(new Vector2(
            (kb.dKey.isPressed ? 1f : 0f) - (kb.aKey.isPressed ? 1f : 0f),
            (kb.wKey.isPressed ? 1f : 0f) - (kb.sKey.isPressed ? 1f : 0f)), 1f);

        // 자세: Ctrl 숙이기 > Shift 달리기(움직일 때만) > 걷기
        bool wantCrouch = kb.leftCtrlKey.isPressed;
        bool wantRun = kb.leftShiftKey.isPressed && !wantCrouch && input != Vector2.zero;
        if (wantRun && stamina <= 0f && !exhausted)
            exhausted = true;
        if (exhausted)
        {
            wantRun = false;
            input = Vector2.zero;
            if (stamina >= Tuning.STAMINA_MAX)
                exhausted = false;
        }
        stance = wantCrouch ? "crouch" : wantRun ? "run" : "walk";
        if (stance == "run")
            stamina -= Tuning.STAMINA_RUN * dt;
        else
            stamina += (input != Vector2.zero ? Tuning.STAMINA_WALK : Tuning.STAMINA_IDLE) * dt;
        stamina = Mathf.Clamp(stamina, 0f, Tuning.STAMINA_MAX);
        UpdateCrouch(dt);

        bool grounded = cc.isGrounded;
        if (!grounded)
            velocity.y -= Tuning.GRAVITY * dt;
        else if (kb.spaceKey.wasPressedThisFrame && stance != "crouch" && !exhausted)
            velocity.y = Tuning.JumpVelocity;
        else
            velocity.y = -2f;              // 바닥에 붙여 둬야 isGrounded 가 유지된다

        float speed = stance == "crouch" ? Tuning.CROUCH_SPEED : stance == "run" ? Tuning.RUN_SPEED : Tuning.WALK_SPEED;
        Vector3 wish = (transform.rotation * new Vector3(input.x, 0f, input.y)).normalized * speed;
        float rate = input != Vector2.zero ? Tuning.Accel : Tuning.Decel;
        if (!grounded)
            rate *= Tuning.AIR_CONTROL;
        Vector3 flat = Vector3.MoveTowards(new Vector3(velocity.x, 0f, velocity.z), wish, rate * dt);
        velocity.x = flat.x;
        velocity.z = flat.z;

        if ((cc.Move(velocity * dt) & CollisionFlags.Above) != 0 && velocity.y > 0f)
            velocity.y = 0f;

        // 발소리: 땅에서 움직이는 동안 걸음 위상이 π 를 지날 때마다(발이 땅에 닿는 순간) 소음 한 번 (Godot Player.gd 의 간격 = 자세별 STEP_INTERVAL).
        // 곡괭이 흔들림(Pickaxe)이 같은 위상을 쓰므로 소리와 움직임이 맞는다 (사용자 09-16 "사운드 타이밍과 모션 타이밍이 안 맞는다"). 소리는 NoiseSound 가 튼다
        bool moving = grounded && input != Vector2.zero;
        if (moving)
        {
            float interval = stance == "crouch" ? Tuning.STEP_INTERVAL_CROUCH : stance == "run" ? Tuning.STEP_INTERVAL_RUN : Tuning.STEP_INTERVAL;
            float prev = gait;
            gait += dt * Mathf.PI / interval;
            if (!wasMoving || Mathf.Floor(gait / Mathf.PI) > Mathf.Floor(prev / Mathf.PI))
            {
                float radius = stance == "crouch" ? Tuning.NOISE_STEP_CROUCH : stance == "run" ? Tuning.NOISE_STEP_RUN : Tuning.NOISE_STEP;
                steps++;
                NoiseBus.Make(transform.position, radius * stepNoiseMul, "step", this);
            }
        }
        else
            gait = 0f;
        wasMoving = moving;

        Vector3 shake = Vector3.zero;
        if (shakeLeft > 0f)
        {
            shakeLeft -= dt;
            shake = new Vector3(Random.Range(-1f, 1f), Random.Range(-1f, 1f), 0f) * shakeAmount * Mathf.Max(shakeLeft, 0f) / shakeSpan;
        }
        // 탈진 자세 (UI-1b 1·2차 판정): 시야가 EXHAUST_LOOK_DOWN_DEG 숙여지고 시야각 절반·흐릿함·좌우 ±90° 만, 숨 박자(EXHAUST_BREATH_S)로 머리가 오르내리며 끄덕인다.
        // 곧 단계(≤ STAMINA_SOON)에도 숨 들썩임은 BREATH_SOON_MUL 로 작게
        bool panting = exhausted && stagger;
        if (panting && pant <= 0f) pantYaw = transform.eulerAngles.y;   // 탈진 시작 방향 — 좌우 한계의 기준
        pant = Mathf.MoveTowards(pant, panting ? 1f : 0f, dt / Tuning.EXHAUST_TIME);
        lookDown = pant * Tuning.EXHAUST_LOOK_DOWN_DEG;
        if (panting) pitch = Mathf.MoveTowards(pitch, 0f, Tuning.PITCH_LIMIT_DEG / Tuning.EXHAUST_TIME * dt);   // 보던 위아래는 정면으로 — 숙임 각이 그대로 읽히게
        float breathTarget = panting ? 1f : stamina <= Tuning.STAMINA_SOON ? Tuning.BREATH_SOON_MUL : 0f;
        breathAmp = Mathf.MoveTowards(breathAmp, breathTarget, dt / Tuning.EXHAUST_TIME);
        breathPhase = breathAmp > 0f ? breathPhase + dt * Mathf.PI * 2f / Tuning.EXHAUST_BREATH_S : 0f;
        float breath = Mathf.Sin(breathPhase) * breathAmp;
        head.localPosition = new Vector3(0f, eye + breath * Tuning.EXHAUST_BREATH_M, 0f) + shake;
        head.localRotation = Quaternion.Euler(pitch + lookDown + breath * Tuning.EXHAUST_BREATH_DEG, 0f, 0f);
        if (cam != null)
            cam.fieldOfView = Tuning.CAMERA_FOV * Mathf.Lerp(1f, Tuning.EXHAUST_FOV_MUL, pant);
        if (dof != null)
        {
            dof.gaussianMaxRadius.value = Tuning.EXHAUST_BLUR_RADIUS * pant * blurMul;
            dof.active = dof.gaussianMaxRadius.value > 0f;
        }
    }

    // 숙이기: 눈이 CROUCH_EYE 로 내려가고 캡슐이 그만큼 줄어든다. 탈진(UI-1b)이면 EXHAUST_EYE 로 — "무릎 짚고 헐떡임", 숙이기가 우선
    void UpdateCrouch(float dt)
    {
        float target = stance == "crouch" ? Tuning.CROUCH_EYE : exhausted && stagger ? Tuning.EXHAUST_EYE : Tuning.EYE_HEIGHT;
        if (Mathf.Approximately(eye, target))
            return;
        bool crouching = target == Tuning.CROUCH_EYE || eye <= Tuning.CROUCH_EYE + 0.01f;   // 숙이기 길은 빠르고(0.15 s), 탈진 길은 느리다(0.3 s)
        float rate = crouching ? (Tuning.EYE_HEIGHT - Tuning.CROUCH_EYE) / Tuning.CROUCH_TIME : (Tuning.EYE_HEIGHT - Tuning.EXHAUST_EYE) / Tuning.EXHAUST_TIME;
        eye = Mathf.MoveTowards(eye, target, rate * dt);
        SetHeight(Tuning.BODY_HEIGHT - (Tuning.EYE_HEIGHT - eye));
    }

    void SetHeight(float h)
    {
        cc.height = h;
        cc.center = new Vector3(0f, h * 0.5f, 0f);
    }
}
