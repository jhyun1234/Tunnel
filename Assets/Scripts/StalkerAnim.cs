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
    // 머리 (3D-③b M1d): 괴물이 아는 것 쪽으로 머리부터. 들킴·추격·잡기·빛 조사 = 플레이어에 고정 (사용자 09-19 "확신이 드는 상황에서는 고정"),
    // 소리 조사 = 소리 자리 + 갸웃, 수색 = 0.4 s 마다 무작위 방향으로 끊어 돌림(플레이어를 스쳐도 된다 — 사용자 09-19), 배회 = 동작 그대로
    [System.NonSerialized] public bool driveHead = true;                  // 사보타주 stiffneck 이 끈다
    [System.NonSerialized] public float headYawMax = Tuning.STALKER_HEAD_YAW_MAX;    // DevHud T/Y
    [System.NonSerialized] public float headTilt = Tuning.STALKER_HEAD_TILT_DEG;     // DevHud O/P
    [System.NonSerialized] public int headTest;                            // 행동 꺼짐(9)일 때 DevHud G: 0 끔 · 1 나 따라보기 · 2 수색 · 3 갸웃하며 나 보기
    public static string HeadTestName(int m) => m == 1 ? "follow me" : m == 2 ? "search" : m == 3 ? "listen tilt" : "off";
    public float HeadYaw { get; private set; }                             // 몸 앞 기준 지금 얼굴 좌우 (도) — 진단·검사
    public float HeadTiltNow { get; private set; }
    public int HeadMode { get; private set; }                              // 0 동작 그대로 · 1 플레이어 · 2 수색 · 3 갸웃 플레이어 · 4 소리 자리
    Transform neckB, headB;
    Vector3 faceLocal, upLocal;                                            // 머리 뼈 공간의 얼굴 방향·정수리 방향 (쉬는 자세에서 모델 앞·위)
    float lookYaw, lookPitch, tiltNow, headW, searchT, searchYaw, searchTilt;
    readonly System.Random headRng = new System.Random(7);
    // 목 길게 빼기 (3D-③b M1e): 몸 속 등뼈를 따라 누운 마디 7개 관. 머리 뼈를 밀어내고 마디 뼈를 "머리 → 나오는 곳 → 등뼈" 길 위에 차례로 놓는다.
    // 길이는 모델 크기 1 기준 m. 갸웃이 크면 저절로 나온다(머리가 어깨에 파고들지 않게)
    [System.NonSerialized] public bool driveNeck = true;                  // 사보타주 shortneck 이 끈다 (마디 뼈가 가슴 뼈에 굳은 채, 목 안 나옴)
    [System.NonSerialized] public float neckWant;                         // DevHud Z/X: 빼 둘 길이
    [System.NonSerialized] public float neckOutS = Tuning.STALKER_NECK_OUT_S;   // DevHud C/B
    public float NeckOutNow { get; private set; }
    public bool HasNeck => neckExt != null;
    Transform[] neckExt, spineB;                                           // spineB = Spine2, Spine1, Spine, Hips
    Quaternion[] neckRestM;
    Vector3[] neckRestT;
    Vector3 headRestPos;
    readonly System.Collections.Generic.List<Vector3> path = new System.Collections.Generic.List<Vector3>();
    readonly System.Collections.Generic.List<float> pathS = new System.Collections.Generic.List<float>();
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
        var allT = GetComponentsInChildren<Transform>();
        neckB = System.Array.Find(allT, b => b.name == "mixamorig:Neck");
        headB = System.Array.Find(allT, b => b.name == "mixamorig:Head");
        if (headB != null) { faceLocal = Quaternion.Inverse(headB.rotation) * transform.forward; upLocal = Quaternion.Inverse(headB.rotation) * transform.up; }
        var ext = new Transform[Tuning.STALKER_NECK_JOINTS];
        for (int i = 0; i < ext.Length; i++) ext[i] = System.Array.Find(allT, b => b.name == "mixamorig:NeckExt_" + i);
        var sp = System.Array.ConvertAll(new[] { "Spine2", "Spine1", "Spine", "Hips" }, n => System.Array.Find(allT, b => b.name == "mixamorig:" + n));
        if (headB != null && neckB != null && System.Array.IndexOf(ext, null) < 0 && System.Array.IndexOf(sp, null) < 0)
        {
            neckExt = ext; spineB = sp;
            headRestPos = headB.localPosition;
            BuildPath();                                                   // 쉬는 자세의 길 — 마디마다 쉬는 방향을 적어 둔다
            neckRestM = System.Array.ConvertAll(neckExt, b => Quaternion.Inverse(transform.rotation) * b.rotation);
            neckRestT = new Vector3[neckExt.Length];
            for (int i = 0; i < neckExt.Length; i++) PathAt(BoneS(i), out neckRestT[i]);
        }
        jaw = System.Array.Find(allT, b => b.name == "mixamorig:Jaw");
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

    // 세상 방향 → 몸(모델) 기준 좌우·위아래 (도). 좌우 + = 모델 오른쪽, 위아래 + = 아래
    void YawPitch(Vector3 worldDir, out float yaw, out float pitch)
    {
        Vector3 l = transform.InverseTransformDirection(worldDir);
        yaw = Mathf.Atan2(l.x, l.z) * Mathf.Rad2Deg;
        pitch = -Mathf.Atan2(l.y, new Vector2(l.x, l.z).magnitude) * Mathf.Rad2Deg;
    }

    public Vector3 FaceDir => headB != null ? headB.rotation * faceLocal : transform.forward;
    public Vector3 HeadUpDir => headB != null ? headB.rotation * upLocal : transform.up;

    void Head(float dt)
    {
        Vector3 eye = headB.position;
        Vector3 me = st.player != null ? st.player.position + Vector3.up * Tuning.EYE_HEIGHT : eye + transform.forward;
        var s = st.state;
        int mode = !st.enabled ? headTest
            : s == Stalker.State.Alert || s == Stalker.State.Chase || s == Stalker.State.Catch || (s == Stalker.State.Investigate && st.LightChase) ? 1
            : s == Stalker.State.Investigate ? 4 : s == Stalker.State.Search ? 2 : 0;
        HeadMode = mode;
        float wantYaw = 0f, wantPitch = 0f, wantTilt = 0f;
        if (mode == 1 || mode == 3) YawPitch(me - eye, out wantYaw, out wantPitch);
        else if (mode == 4) YawPitch(st.noisePos + Vector3.up * Tuning.EYE_HEIGHT - eye, out wantYaw, out wantPitch);
        if (mode == 3 || mode == 4) wantTilt = headTilt;
        if (mode == 2)
        {
            searchT -= dt;
            if (searchT <= 0f)
            {
                searchT = Tuning.STALKER_HEAD_SEARCH_STEP_S;
                searchYaw = ((float)headRng.NextDouble() * 2f - 1f) * headYawMax;
                searchTilt = ((float)headRng.NextDouble() * 2f - 1f) * headTilt * Tuning.STALKER_HEAD_SEARCH_TILT_K;
            }
            wantYaw = searchYaw; wantTilt = searchTilt;
        }
        else searchT = 0f;
        wantYaw = Mathf.Clamp(wantYaw, -headYawMax, headYawMax);
        wantPitch = Mathf.Clamp(wantPitch, -Tuning.STALKER_HEAD_PITCH_MAX, Tuning.STALKER_HEAD_PITCH_MAX);
        YawPitch(FaceDir, out float animYaw, out float animPitch);         // 동작이 입힌 얼굴 방향
        headW = Mathf.MoveTowards(headW, mode != 0 ? 1f : 0f, dt / Tuning.STALKER_HEAD_FADE_S);
        if (headW <= 0f)
        {
            lookYaw = animYaw; lookPitch = animPitch; tiltNow = 0f;          // 켜질 때 지금 얼굴에서 출발
            HeadYaw = animYaw; HeadTiltNow = 0f;
            return;
        }
        if (mode == 0) { wantYaw = animYaw; wantPitch = animPitch; wantTilt = 0f; }
        // 목표가 바뀌면 STALKER_HEAD_SNAP_S 안에 딱 — 좌우는 ±180 안에서만 움직여 몸 뒤를 가로질러 돌지 않는다
        float rate = 180f / Tuning.STALKER_HEAD_SNAP_S;
        lookYaw = Mathf.MoveTowards(lookYaw, wantYaw, rate * dt);
        lookPitch = Mathf.MoveTowards(lookPitch, wantPitch, rate * dt);
        tiltNow = Mathf.MoveTowards(tiltNow, wantTilt, rate * dt);
        float dy = (lookYaw - animYaw) * headW, dp = (lookPitch - animPitch) * headW, dr = tiltNow * headW;
        // 모델 공간: 좌우(모델 위 축) → 위아래(돌린 뒤 옆 축) → 갸웃(돌린 뒤 얼굴 축). 세상으로 바꿔 목 몫·머리 몫으로 나눠 앞에 곱한다
        Quaternion yawQ = Quaternion.AngleAxis(dy, Vector3.up);
        Quaternion qm = Quaternion.AngleAxis(dr, Quaternion.AngleAxis(animYaw + dy, Vector3.up) * Vector3.forward)
                        * Quaternion.AngleAxis(dp, Quaternion.AngleAxis(animYaw + dy, Vector3.up) * Vector3.right) * yawQ;
        Quaternion qw = transform.rotation * qm * Quaternion.Inverse(transform.rotation);
        float k = Tuning.STALKER_HEAD_NECK_SHARE;
        neckB.rotation = Quaternion.Slerp(Quaternion.identity, qw, k) * neckB.rotation;
        headB.rotation = Quaternion.Slerp(Quaternion.identity, qw, 1f - k) * headB.rotation;
        YawPitch(FaceDir, out float nowYaw, out _);
        HeadYaw = nowYaw;
        HeadTiltNow = dr;
    }

    static float BoneS(int i) => Tuning.STALKER_NECK_TOP_IN_M + i * Tuning.STALKER_NECK_LEN_M / Tuning.STALKER_NECK_JOINTS;
    Vector3 ToModel(Vector3 world) => transform.InverseTransformPoint(world);

    // 길(모델 공간): 관 꼭대기(머리 속) → 머리 뼈 → [둥근 길] → 목 나오는 곳(Neck 뼈) → 등뼈 → 엉덩이 아래. blender/rig/add_long_neck.py 의 쉬는 길과 같다
    void BuildPath()
    {
        path.Clear(); pathS.Clear();
        Vector3 H = ToModel(headB.position), X = ToModel(neckB.position), S2 = ToModel(spineB[0].position);
        Vector3 headUp = transform.InverseTransformDirection(HeadUpDir).normalized, spineUp = (X - S2).normalized;
        path.Add(H + headUp * Tuning.STALKER_NECK_TOP_IN_M);
        float d = (X - H).magnitude * 0.45f;
        Vector3 p1 = H - headUp * d, p2 = X + spineUp * d;
        for (int k = 0; k <= 16; k++)
        {
            float u = k / 16f, v = 1f - u;
            path.Add(v * v * v * H + 3f * v * v * u * p1 + 3f * v * u * u * p2 + u * u * u * X);
        }
        for (int k = 0; k < spineB.Length; k++) path.Add(ToModel(spineB[k].position));
        path.Add(path[path.Count - 1] + (path[path.Count - 1] - path[path.Count - 2]).normalized * 0.6f);
        float acc = 0f;
        for (int k = 0; k < path.Count; k++)
        {
            if (k > 0) acc += (path[k] - path[k - 1]).magnitude;
            pathS.Add(acc);
        }
    }

    // 관 꼭대기에서 잰 길이 s 의 자리, toHead = 머리 쪽을 보는 방향
    Vector3 PathAt(float s, out Vector3 toHead)
    {
        int k = 1;
        while (k < path.Count - 1 && (pathS[k] < s || pathS[k] - pathS[k - 1] < 1e-6f)) k++;
        Vector3 a = path[k - 1], b = path[k];
        float len = Mathf.Max(1e-6f, pathS[k] - pathS[k - 1]);
        toHead = (a - b) / len;
        return Vector3.LerpUnclamped(a, b, (s - pathS[k - 1]) / len);
    }

    void NeckOut(float dt)
    {
        float tilt = Mathf.Abs(HeadTiltNow);
        float auto = Tuning.STALKER_NECK_TILT_OUT_M * Mathf.InverseLerp(Tuning.STALKER_NECK_TILT_FROM_DEG, Tuning.STALKER_NECK_TILT_FULL_DEG, tilt);
        float want = Mathf.Clamp(Mathf.Max(neckWant, auto), 0f, Tuning.STALKER_NECK_OUT_MAX_M);
        NeckOutNow = Mathf.MoveTowards(NeckOutNow, want, Tuning.STALKER_NECK_OUT_MAX_M / Mathf.Max(0.02f, neckOutS) * dt);
        headB.localPosition = headRestPos;                                 // 동작에 머리 자리 키가 없어 지난 프레임에 민 것이 남는다
        if (NeckOutNow > 0f)
        {
            // 보는 쪽으로 내민다. 얼굴이 위를 볼 때(대기 동작은 턱을 들고 있다)는 위 성분을 버린다 — 3 m 괴물 머리 위는 바로 갱도 천장이다.
            // 아래(나)를 보면 그대로 내려온다
            Vector3 face = transform.InverseTransformDirection(FaceDir).normalized;
            face.y = Mathf.Min(face.y, 0f);
            Vector3 dir = (face.normalized + Vector3.up * Tuning.STALKER_NECK_UP).normalized;
            headB.position += transform.TransformVector(dir * NeckOutNow);
        }
        BuildPath();
        Quaternion q = Quaternion.identity;
        for (int i = neckExt.Length - 1; i >= 0; i--)                      // 몸 속 끝에서 머리 쪽으로: 앞 마디의 돌림을 이어받아 비틀림 없이
        {
            Vector3 p = PathAt(BoneS(i), out Vector3 t);
            q = Quaternion.FromToRotation(q * neckRestT[i], t) * q;
            neckExt[i].SetPositionAndRotation(transform.TransformPoint(p), transform.rotation * q * neckRestM[i]);
        }
    }

    // 검사·진단: 마디 뼈가 지금 자세의 길에서 가장 멀리 벗어난 거리 (모델 m). NeckOut 이 돌면 0 에 가깝다
    public float NeckOffPath()
    {
        if (neckExt == null) return 99f;
        BuildPath();
        float worst = 0f;
        for (int i = 0; i < neckExt.Length; i++)
            worst = Mathf.Max(worst, (ToModel(neckExt[i].position) - PathAt(BoneS(i), out _)).magnitude);
        return worst;
    }

    // 검사: 머리 뼈 ↔ 목 나오는 곳 거리 (모델 m), 이웃 마디 사이 가장 짧은·긴 거리
    public float HeadToExit => headB != null && neckB != null ? (ToModel(headB.position) - ToModel(neckB.position)).magnitude : 0f;
    public void NeckSpacing(out float min, out float max)
    {
        min = float.MaxValue; max = 0f;
        for (int i = 1; neckExt != null && i < neckExt.Length; i++)
        {
            float d = (ToModel(neckExt[i].position) - ToModel(neckExt[i - 1].position)).magnitude;
            min = Mathf.Min(min, d); max = Mathf.Max(max, d);
        }
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
        if (neckB != null && headB != null && driveHead)
            Head(Time.deltaTime);
        if (neckExt != null && driveNeck)
            NeckOut(Time.deltaTime);
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
