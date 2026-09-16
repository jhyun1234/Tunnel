using UnityEngine;
using UnityEngine.InputSystem;

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

    CharacterController cc;
    Vector3 velocity;
    float pitch;
    float eye = Tuning.EYE_HEIGHT;
    float shakeLeft, shakeAmount, shakeSpan;
    float stepLeft;                        // 다음 발걸음까지 (Godot _step_left). 멈추면 0 — 다시 걸으면 바로 한 걸음

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
                Vector2 d = mouse.delta.ReadValue();
                transform.Rotate(0f, d.x * Tuning.MOUSE_SENSITIVITY * Mathf.Rad2Deg, 0f);
                pitch = Mathf.Clamp(pitch - d.y * Tuning.MOUSE_SENSITIVITY * Mathf.Rad2Deg, -Tuning.PITCH_LIMIT_DEG, Tuning.PITCH_LIMIT_DEG);
                head.localRotation = Quaternion.Euler(pitch, 0f, 0f);
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

        // 발소리: 땅에서 움직이는 동안 자세별 간격마다 소음 한 번 (Godot Player.gd). 소리는 NoiseSound 가 튼다
        if (grounded && input != Vector2.zero)
        {
            stepLeft -= dt;
            if (stepLeft <= 0f)
            {
                stepLeft = stance == "crouch" ? Tuning.STEP_INTERVAL_CROUCH : stance == "run" ? Tuning.STEP_INTERVAL_RUN : Tuning.STEP_INTERVAL;
                float radius = stance == "crouch" ? Tuning.NOISE_STEP_CROUCH : stance == "run" ? Tuning.NOISE_STEP_RUN : Tuning.NOISE_STEP;
                steps++;
                NoiseBus.Make(transform.position, radius * stepNoiseMul, "step", this);
            }
        }
        else
            stepLeft = 0f;

        Vector3 shake = Vector3.zero;
        if (shakeLeft > 0f)
        {
            shakeLeft -= dt;
            shake = new Vector3(Random.Range(-1f, 1f), Random.Range(-1f, 1f), 0f) * shakeAmount * Mathf.Max(shakeLeft, 0f) / shakeSpan;
        }
        head.localPosition = new Vector3(0f, eye, 0f) + shake;
    }

    // 숙이기: 눈이 CROUCH_EYE 로 내려가고 캡슐이 그만큼 줄어든다
    void UpdateCrouch(float dt)
    {
        float target = stance == "crouch" ? Tuning.CROUCH_EYE : Tuning.EYE_HEIGHT;
        if (Mathf.Approximately(eye, target))
            return;
        eye = Mathf.MoveTowards(eye, target, (Tuning.EYE_HEIGHT - Tuning.CROUCH_EYE) / Tuning.CROUCH_TIME * dt);
        SetHeight(Tuning.BODY_HEIGHT - (Tuning.EYE_HEIGHT - eye));
    }

    void SetHeight(float h)
    {
        cc.height = h;
        cc.center = new Vector3(0f, h * 0.5f, 0f);
    }
}
