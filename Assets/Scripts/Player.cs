using System.Collections.Generic;
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
    [System.NonSerialized] public bool snapDown = true;       // 사보타주 nosnap 이 끈다 — 비탈을 내려가며 떴다 붙었다 하던(옛) 상태
    [System.NonSerialized] public float blurMul = 1f;         // 검사가 흐림만 끄고 비교한다
    public bool BlurOn => dof != null && dof.active;          // 검사: 탈진 아닐 때 흐림이 없어야 한다
    [System.NonSerialized] public float lookDown, breathAmp, pant;   // 탈진 자세: 시야 숙임 각 · 숨 들썩임 폭(0~1) · 탈진 정도(0~1, 시야각·흐림·시점 잠금) (검사가 읽는다)
    float breathPhase, pantYaw;
    // R2b 바위 틈 비집기 (Crevice): 입구에서 틈 쪽을 보고 E → 조작 잠김, 캡슐을 끄고 틈 가운데 선을 따라 옮긴다. 값은 판정 키 F7 F8 · F9 F10 (DevHud)
    [System.NonSerialized] public float squeezeS = Tuning.SQUEEZE_S;
    [System.NonSerialized] public float squeezeTurnDeg = Tuning.SQUEEZE_TURN_DEG;
    [System.NonSerialized] public float squeezeMul = 1f;      // 사보타주 squeezelong 이 2 로 — 정한 시간보다 오래 걸리는 상태
    [System.NonSerialized] public float squeezeLower;         // 0~1, 곡괭이를 내린 정도 (Pickaxe 가 본다)
    public bool Squeezing => sqRoute != null;
    public bool Busy => frozen || Squeezing;                  // 곡괭이 던지기·줍기가 안 먹는다
    List<Vector3> sqRoute;
    float[] sqAt;
    float sqT, sqDur, sqStartYaw, sqEndYaw;
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
        var volume = FindFirstObjectByType<Volume>();
        if (volume != null)
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
        {
            if (Squeezing) EndSqueeze();                       // 틈 속에서 잡혔다 — 캡슐을 다시 켜 둔다 (재시작이 옮긴다)
            return;
        }
        if (Squeezing)
        {
            SqueezeStep(dt);
            return;
        }

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
        if (kb.eKey.wasPressedThisFrame && cc.isGrounded && !exhausted && Crevice.Find(transform.position, transform.forward, out var route, out var endLook))
        {
            StartSqueeze(route, endLook);
            return;
        }

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
        // 비탈 내려가기: 노보리(25°)를 걸어 내려가면 한 프레임에 떨어지는 높이가 바닥 붙이기(−2 m/s)보다 커서 떴다 붙었다 한다 →
        // 붙을 때마다 걷기 시작으로 쳐서 발소리가 프레임마다 났다 (사용자 09-24 영상: 오를 때 0.5 s, 내릴 때 0.05~0.07 s).
        // 걸을 수 있는 가장 가파른 비탈이 이번 이동만큼 떨어뜨리는 거리를 내려 본다 — 바닥에 닿으면 붙은 채, 못 닿으면(턱 밖) 되돌려 그대로 떨어진다.
        // (발밑 광선으로 바닥을 찾던 첫 판은 비탈에서 캡슐 밑과 바닥 사이가 광선보다 멀어 못 붙였다)
        if (grounded && !cc.isGrounded && velocity.y <= 0f && snapDown)
        {
            float drop = new Vector2(velocity.x, velocity.z).magnitude * dt * Mathf.Tan(cc.slopeLimit * Mathf.Deg2Rad) + 0.02f;
            cc.Move(Vector3.down * drop);
            if (!cc.isGrounded)
                cc.Move(Vector3.up * drop);
        }

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
        // 탈진 자세 (UI-1b 1~3차 판정): 시야가 EXHAUST_LOOK_DOWN_DEG 숙여지고 흐릿함·좌우 ±EXHAUST_YAW_LIMIT_DEG 만, 숨 박자(EXHAUST_BREATH_S)로 머리가 오르내리며 끄덕인다. 램프 박동은 Headlamp.
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
        if (dof != null)                                             // 흐림은 탈진 중에만 — 풀리는 순간 바로 끈다 (3차 판정: 탈진 아닐 때 흐릿함 금지)
        {
            dof.gaussianMaxRadius.value = panting ? Tuning.EXHAUST_BLUR_RADIUS * pant * blurMul : 0f;
            dof.active = panting && dof.gaussianMaxRadius.value > 0f;
        }
    }

    void StartSqueeze(List<Vector3> route, Vector3 endLook)
    {
        sqRoute = route;
        sqAt = new float[route.Count];
        for (int i = 1; i < route.Count; i++)
            sqAt[i] = sqAt[i - 1] + Vector3.Distance(route[i - 1], route[i]);
        sqDur = SqueezeTime(sqAt[sqAt.Length - 1]);
        sqT = 0f;
        sqStartYaw = transform.eulerAngles.y;
        sqEndYaw = Quaternion.LookRotation(endLook).eulerAngles.y;
        cc.enabled = false;
        velocity = Vector3.zero;
        gait = 0f;
        wasMoving = false;
    }

    public float SqueezeTime(float length) => squeezeS * squeezeMul * length / Tuning.SQUEEZE_REF_M;   // 같은 빠르기 — 뚫린 틈(7~8 m)은 막힌 틈(3.7 m)보다 오래

    // 천천히 떠나 천천히 선다. 바위 속(길의 둘째 점 ~ 끝에서 둘째 점)에서는 몸을 옆으로 돌리고(SQUEEZE_TURN_DEG) 머리가 비비적댄다.
    // 들어가기 전에는 서 있던 쪽에서 틈 쪽으로 돌고, 막힌 틈 안쪽 방에서는 입구(밖)를 보게 돈다
    void SqueezeStep(float dt)
    {
        sqT += dt;
        float total = sqAt[sqAt.Length - 1];
        float s = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(sqT / sqDur)) * total;
        int i = 1;
        while (i < sqAt.Length - 1 && sqAt[i] < s) i++;
        Vector3 a = sqRoute[i - 1], b = sqRoute[i];
        transform.position = Vector3.Lerp(a, b, Mathf.InverseLerp(sqAt[i - 1], sqAt[i], s));
        Vector3 dir = b - a;
        dir.y = 0f;
        float rockIn = sqAt[1], rockOut = sqAt[sqAt.Length - 2];
        float side = Mathf.Clamp01((s - (rockIn - 0.5f)) / 0.8f) * Mathf.Clamp01((rockOut + 0.3f - s) / 0.6f);
        float yaw = Mathf.LerpAngle(sqStartYaw, Quaternion.LookRotation(dir).eulerAngles.y, Mathf.Clamp01(s / 0.6f)) + side * squeezeTurnDeg;
        yaw = Mathf.LerpAngle(yaw, sqEndYaw, Mathf.Clamp01((s - (total - 0.8f)) / 0.8f));
        transform.rotation = Quaternion.Euler(0f, yaw, 0f);
        pitch = Mathf.MoveTowards(pitch, 0f, 90f * dt);
        squeezeLower = Mathf.Clamp01(Mathf.Min(sqT, sqDur - sqT) / 0.3f);
        float rub = Mathf.Sin(sqT * Mathf.PI * 2f * 1.6f) * Tuning.SQUEEZE_BOB_M * side;
        head.localPosition = new Vector3(rub, eye + Mathf.Abs(rub) * 0.5f, 0f);
        head.localRotation = Quaternion.Euler(pitch, 0f, 0f);
        if (sqT >= sqDur)
            EndSqueeze();
    }

    void EndSqueeze()
    {
        transform.position = sqRoute[sqRoute.Count - 1];
        sqRoute = null;
        squeezeLower = 0f;
        cc.enabled = true;
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
