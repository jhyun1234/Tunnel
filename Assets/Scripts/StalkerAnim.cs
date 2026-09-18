using UnityEngine;

// 3D-③ (제안서 docs/제안서_3D3_괴물_동작_연결.md, 승인 09-18): 괴물이 하는 일(Stalker.state)과 실제로 움직인 빠르기를 보고 동작 칸을 고른다.
// 동작 목록 파일(M8_StalkerAnim.controller)에는 연결 줄이 없다 — 여기서 매 프레임 칸 이름으로 바로 넘긴다(행동은 Stalker.cs 한 곳에만).
// 동작은 제자리 걸음이라 재생 배수 = 실제 빠르기 ÷ 원래 걸음 빠르기(Tuning.STALKER_CLIP_SPEED_*) × 크기 — 발이 안 미끄러진다.
// 벽타기는 crawl 을 90° 세워 손발이 벽에 닿게 한다. 행동이 꺼지면(DevHud 0·9) manual 동작을 튼다 — N 키로 차례로 바꾼다.
// 모델 뿌리(Stalker/Body/Model)에 붙는다. Stalker.Update 가 몸을 옮긴 뒤에 돈다.
[DefaultExecutionOrder(100)]
public class StalkerAnim : MonoBehaviour
{
    public static readonly string[] ManualClips = { "idle_crouch", "walk_crouch", "walk_knuckle", "run", "roar", "hit", "crawl", "attack_swipe" };
    [System.NonSerialized] public int gait = Tuning.STALKER_WANDER_GAIT;   // 배회 걸음 A/B/C (U 키)
    [System.NonSerialized] public int manual;                             // 행동 꺼짐일 때 트는 동작 (N 키)
    [System.NonSerialized] public bool rateMatch = true;                  // 사보타주 slide 가 끈다 (늘 1배)
    [System.NonSerialized] public bool tiltClimb = true;                  // 사보타주 uprightclimb 가 끈다 (벽타기 때 안 세움)
    [System.NonSerialized] public bool freezeTime;                        // 검사 연속 사진: 시간을 멈추고 검사가 자리를 정한다
    [System.NonSerialized] public bool oldWalk;                           // 사보타주 oldwalk: 걸음 D 가 옛 walk_crouch 로 (3D-③b M1 전 상태)
    [System.NonSerialized] public bool straightFingers;                   // 사보타주 straightfingers: 손가락 마디를 쉬는 자세(곧음)로 되돌린다 (3D-③b M1b 전 상태)
    Transform[] fingers;
    Quaternion[] fingerRest;
    // 턱 (3D-③b M1c): 동작 이름 → 벌림 각도. 동작 파일엔 턱 키가 없다(walk_knuckle 은 쉬는 자세 키) — LateUpdate 에서 덮는다
    [System.NonSerialized] public bool driveJaw = true;                   // 사보타주 shutjaw 가 끈다
    [System.NonSerialized] public float jawWideDeg = Tuning.STALKER_JAW_WIDE_DEG;   // DevHud H/J
    public float JawDeg { get; private set; }
    Transform jaw;
    Quaternion jawRest;
    Vector3 jawRestPos, jawAxis;                                          // jawAxis = 머리 뼈 공간의 좌우 축 (모델 오른쪽)
    float jawT;
    public int LiftCount { get; private set; }                            // 팔 들기(LateUpdate)가 팔을 든 프레임 수 — 새 동작은 0 이어야 한다
    public string Current { get; private set; } = "";
    public float Rate { get; private set; } = 1f;
    public float Speed { get; private set; }                              // 잰 빠르기 m/s (벽타기는 위로 가는 것 포함)
    public float Tilt { get; private set; }                               // 0 = 서 있음, 1 = 벽에 붙음
    public static string GaitName(int g) => g == 0 ? "A crouch-walk matched" : g == 1 ? "B slow run" : g == 2 ? "C crouch-walk capped" : "D knuckle-walk (new)";

    Stalker st;
    Animator anim;
    Vector3 lastPos, basePos;
    Quaternion baseRot;
    bool moving;

    void Awake()
    {
        st = GetComponentInParent<Stalker>();
        anim = GetComponent<Animator>();
        basePos = transform.localPosition;
        baseRot = transform.localRotation;
        lastPos = st.transform.position;
        fingers = System.Array.FindAll(GetComponentsInChildren<Transform>(), b => b.name.StartsWith("mixamorig:") && b.name.Contains("Hand") && "123".IndexOf(b.name[b.name.Length - 1]) >= 0);
        fingerRest = System.Array.ConvertAll(fingers, b => b.localRotation);   // 동작이 돌기 전 = GLB 쉬는 자세
        jaw = System.Array.Find(GetComponentsInChildren<Transform>(), b => b.name == "mixamorig:Jaw");
        if (jaw != null)
        {
            jawRest = jaw.localRotation;
            jawRestPos = jaw.localPosition;
            jawAxis = Quaternion.Inverse(jaw.parent.rotation) * transform.right;   // + 방향으로 돌리면 턱 끝(앞)이 아래로
        }
    }

    void Update()
    {
        float dt = Time.deltaTime;
        if (dt <= 0f)
            return;
        Vector3 d = st.transform.position - lastPos;
        lastPos = st.transform.position;
        bool climbing = st.enabled && st.state == Stalker.State.Climb;
        float v = (climbing ? d.magnitude : new Vector2(d.x, d.z).magnitude) / dt;
        if (v > 20f) v = Speed;                                           // 순간이동(Teleport)은 빠르기로 안 친다
        Speed = Mathf.Lerp(Speed, v, 1f - Mathf.Exp(-12f * dt));

        string clip;
        float rate = 1f, fade = Tuning.STALKER_ANIM_FADE_S, offset = 0f;
        bool wall = false;
        if (!st.enabled && Speed > Tuning.STALKER_ANIM_STILL * 2f)
            clip = Locomotion(out rate);                                  // 행동 꺼짐이어도 움직이면 걷기 (DevHud U 걸어오기 미리보기 — 배회 걸음 A/B/C 가 먹는다)
        else if (!st.enabled)
        {
            clip = ManualClips[manual];
            wall = clip == "crawl";
        }
        else
            switch (st.state)
            {
                case Stalker.State.Alert: clip = "roar"; fade = Tuning.STALKER_ANIM_FADE_FAST_S; offset = Tuning.STALKER_ROAR_START_S; break;
                case Stalker.State.Stun: clip = "hit"; fade = Tuning.STALKER_ANIM_FADE_FAST_S; break;
                case Stalker.State.Catch: clip = "attack_swipe"; fade = Tuning.STALKER_ANIM_FADE_FAST_S; break;
                case Stalker.State.Climb: clip = "crawl"; wall = true; rate = Speed / (Tuning.STALKER_CLIP_SPEED_CRAWL * Tuning.STALKER_MODEL_SCALE); break;
                case Stalker.State.Hidden: clip = Current; break;           // 몸이 안 보인다
                default:
                    moving = Speed > Tuning.STALKER_ANIM_STILL * (moving ? 1f : 2f);
                    clip = moving ? Locomotion(out rate) : Tuning.STALKER_MODEL_IDLE;
                    break;
            }
        if (!rateMatch) rate = 1f;
        Rate = rate;
        anim.speed = freezeTime ? 0f : rate;
        if (!string.IsNullOrEmpty(clip) && clip != Current)
        {
            anim.CrossFadeInFixedTime(clip, fade, 0, offset);
            Current = clip;
        }

        // 벽타기: 괴물 앞(= 벽 쪽)으로 90° 눕혀 머리가 위, 손발이 벽에. 모델 뿌리(발바닥 면)를 벽 앞 STALKER_CLIMB_GAP 까지 민다
        Tilt = Mathf.MoveTowards(Tilt, wall && tiltClimb ? 1f : 0f, dt / Tuning.STALKER_CLIMB_TILT_S);
        // Stalker 는 벽타기 시작 때 천천히(초당 5) 벽 쪽으로 돈다 — 세우는 동안 Body 를 벽 정면으로 같이 돌려 손발 면이 벽과 나란하게
        var body = transform.parent;
        if (st.enabled && st.state == Stalker.State.Climb)
            body.rotation = Quaternion.Slerp(st.transform.rotation, Quaternion.LookRotation(Vector3.right * (st.transform.position.x >= 0f ? 1f : -1f)), Tilt);
        else
            body.localRotation = Quaternion.identity;
        transform.localRotation = Quaternion.Euler(-90f * Tilt, 0f, 0f) * baseRot;
        transform.localPosition = basePos + Vector3.forward * ((Tuning.STALKER_R - Tuning.STALKER_CLIMB_GAP) * Tilt);
    }

    void Jaw(float dt)
    {
        float target;
        switch (Current)
        {
            case "roar": case "attack_swipe": target = jawWideDeg; break;
            case "run": case "run_stand": target = Tuning.STALKER_JAW_CHASE_DEG; break;
            case "hit": target = Tuning.STALKER_JAW_HIT_DEG; break;
            default:
                jawT += dt;
                target = Tuning.STALKER_JAW_IDLE_DEG + Tuning.STALKER_JAW_BREATH_DEG * Mathf.Sin(2f * Mathf.PI * jawT / Tuning.STALKER_JAW_BREATH_S);
                break;
        }
        float rate = jawWideDeg / (target > JawDeg ? Tuning.STALKER_JAW_OPEN_S : Tuning.STALKER_JAW_CLOSE_S);
        JawDeg = Mathf.MoveTowards(JawDeg, target, rate * dt);
        jaw.localRotation = Quaternion.AngleAxis(JawDeg, jawAxis) * jawRest;
        jaw.localPosition = jawRestPos;
        float slide = Tuning.STALKER_JAW_SLIDE_PER_DEG * Mathf.Max(0f, JawDeg - Tuning.STALKER_JAW_SLIDE_FROM_DEG);
        jaw.position += transform.forward * (slide * transform.lossyScale.y);
    }

    // 걷기·달리기 고르기: 걷기 빠르기 이하면 배회 걸음 안(gait)대로
    string Locomotion(out float rate)
    {
        if (Speed > Tuning.STALKER_ANIM_RUN_ABOVE || gait == 1)
        {
            rate = Speed / (Tuning.STALKER_CLIP_SPEED_RUN * Tuning.STALKER_MODEL_SCALE);
            return "run";
        }
        if (gait == 3 && !oldWalk)
        {
            rate = Speed / (Tuning.STALKER_CLIP_SPEED_KNUCKLE * Tuning.STALKER_MODEL_SCALE);   // 3D-③b M1: 두 손·두 발로 짚는 네 점 걸음
            return "walk_knuckle";
        }
        rate = Speed / (Tuning.STALKER_CLIP_SPEED_WALK * Tuning.STALKER_MODEL_SCALE);
        if (gait == 2) rate = Mathf.Min(rate, Tuning.STALKER_WALK_RATE_CAP);
        return "walk_crouch";
    }

    // 팔이 바닥(벽타기 땐 벽)을 뚫지 않게: 동작을 입힌 뒤 손끝이 모델 발바닥 면 아래면 어깨를 축으로 팔째 들어 올린다.
    // Mixamo 사람 동작을 팔이 무릎 밑까지 오는 몸에 입혀서 run·crawl 에서 손가락이 바닥 아래 0.5 m 까지 들어갔다(09-18 실측, -only anim).
    // 모델 공간 y = 0 이 발바닥 면이다 — 벽타기로 세우면 그 면이 벽 면이 되므로 같은 계산이 벽에도 먹는다
    [System.NonSerialized] public bool clampArms = true;                  // 사보타주 armsink 가 끈다
    Transform[] arms, tips0, tips1;
    public readonly float[] ArmLow = new float[2];                         // 진단: 마지막으로 잰 손끝 높이 (모델 발바닥 면 위 m)
    public readonly float[] ArmLowRaw = new float[2];                      // 진단: 팔 들기 전 손끝 높이 (게임 m)

    void LateUpdate()
    {
        if (jaw != null && driveJaw)
            Jaw(Time.deltaTime);
        if (straightFingers)
            for (int i = 0; i < fingers.Length; i++) fingers[i].localRotation = fingerRest[i];
        if (!clampArms)
            return;
        if (arms == null)
        {
            var all = GetComponentsInChildren<Transform>();
            arms = new[] { System.Array.Find(all, b => b.name == "mixamorig:LeftArm"), System.Array.Find(all, b => b.name == "mixamorig:RightArm") };
            if (arms[0] == null || arms[1] == null) { clampArms = false; return; }
            tips0 = arms[0].GetComponentsInChildren<Transform>();
            tips1 = arms[1].GetComponentsInChildren<Transform>();
        }
        float floor = Tuning.STALKER_ARM_FLOOR_MARGIN / Tuning.STALKER_MODEL_SCALE;   // 모델 공간 (크기 1)
        for (int side = 0; side < 2; side++)
        {
            var tips = side == 0 ? tips0 : tips1;
            // 어깨→가장 깊은 손끝 방향을 위(모델 +y)로 세우는 축으로 STALKER_ARM_LIFT_STEP 씩 — 손끝 하나만 정확히 맞추는 회전은 다른 손끝을
            // 끌어내려 번갈아 뚫었다(09-18). 팔이 거의 수직으로 늘어졌으면 앞(+z, 벽타기에선 위쪽)으로 든다 — 옆으로 비틀려 90° 들어도 못 빠져나왔다
            ArmLow[side] = Lowest(tips, out Vector3 low);
            ArmLowRaw[side] = ArmLow[side] * Tuning.STALKER_MODEL_SCALE;
            if (ArmLow[side] < floor)
            {
                LiftCount++;
                Vector3 dir = low - transform.InverseTransformPoint(arms[side].position);
                Vector3 horiz = new Vector3(dir.x, 0f, dir.z);
                if (horiz.magnitude < 0.3f * dir.magnitude) horiz = Vector3.forward;
                Quaternion.FromToRotation(horiz, Vector3.up).ToAngleAxis(out _, out Vector3 axis);
                Quaternion step = Quaternion.AngleAxis(Tuning.STALKER_ARM_LIFT_STEP, transform.TransformDirection(axis));
                for (int i = 0; i < 30 && ArmLow[side] < floor; i++)
                {
                    arms[side].rotation = step * arms[side].rotation;
                    ArmLow[side] = Lowest(tips, out _);
                }
            }
            ArmLow[side] *= Tuning.STALKER_MODEL_SCALE;
        }
    }

    float Lowest(Transform[] tips, out Vector3 at)
    {
        at = new Vector3(0f, float.MaxValue, 0f);
        foreach (var tp in tips)
        {
            Vector3 q = transform.InverseTransformPoint(tp.position);
            if (q.y < at.y) at = q;
        }
        return at.y;
    }
}
