using UnityEngine;

// 3D-③ (제안서 docs/제안서_3D3_괴물_동작_연결.md, 승인 09-18): 괴물이 하는 일(Stalker.state)과 실제로 움직인 빠르기를 보고 동작 칸을 고른다.
// 동작 목록 파일(M8_StalkerAnim.controller)에는 연결 줄이 없다 — 여기서 매 프레임 칸 이름으로 바로 넘긴다(행동은 Stalker.cs 한 곳에만).
// 동작은 제자리 걸음이라 재생 배수 = 실제 빠르기 ÷ 원래 걸음 빠르기(Tuning.STALKER_CLIP_SPEED_*) × 크기 — 발이 안 미끄러진다.
// 벽타기는 crawl 을 90° 세워 손발이 벽에 닿게 한다. 행동이 꺼지면(DevHud 0·9) manual 동작을 튼다 — N 키로 차례로 바꾼다.
// 모델 뿌리(Stalker/Body/Model)에 붙는다. Stalker.Update 가 몸을 옮긴 뒤에 돈다.
[DefaultExecutionOrder(100)]
public class StalkerAnim : MonoBehaviour
{
    public static readonly string[] ManualClips = { "idle_crouch", "walk_crouch", "walk_knuckle", "glide_walk", "run", "run_knuckle", "glide_fast", "glide_chase", "up_stand", "up_walk", "up_jog", "up_run", "up_grope", "roar", "hit", "crawl", "attack_swipe" };
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
    public int HeadMode { get; private set; }                              // 0 동작 그대로 · 1 플레이어 · 2 수색 · 3 갸웃 플레이어 · 4 소리 자리 · 5 "들었나?" 자리 · 6 옮기는 손
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
    [System.NonSerialized] public bool bouncy;                            // 사보타주 bouncy: 빠른 걸음을 뜀박질 run_knuckle 로 (3D-③b M2b 전 상태)
    [System.NonSerialized] public bool stiffSpine;                        // 사보타주 stiffspine: 배회를 허리가 옆으로 안 휘는 walk_knuckle 로
    [System.NonSerialized] public bool oldRun;                                                   // 사보타주 oldrun: 달리기를 옛 run 으로
    // 서서 오는 괴물 (3D-④ 5b, 영상 UP_U4 통과 09-19): 걸음 F. 클립 up_walk·up_stand·up_run 은 Blender 가 덧칠(숙임·낮춤·팔)을 구운 것이고,
    // 길이가 걸음과 달라 못 굽는 것 — 굳음 · 턱 · 상체가 머리를 늦게 따라감 · 손가락 · 발 디딤 화면 흔들림 — 은 여기서 얹는다
    public bool Upright => gait == 5;
    public string IdleClip => Upright ? "up_stand" : Tuning.STALKER_MODEL_IDLE;
    public bool Frozen { get; private set; }                              // 들킴: 걷다 만 자세 그대로 돌이 된다 (재생 0)
    [System.NonSerialized] public bool driveTorso = true;                 // 사보타주 stifftorso
    [System.NonSerialized] public bool driveFingers = true;               // 사보타주 stillhands
    [System.NonSerialized] public bool stomp = true;                      // 사보타주 noimpact
    public float BodyYaw { get; private set; }                            // 상체가 머리를 따라 돈 각도 (도)
    public readonly System.Collections.Generic.List<Vector2> StompLog = new System.Collections.Generic.List<Vector2>();   // (플레이어까지 거리, 흔든 크기) — 검사
    Transform[] torso, toeB;                                              // Spine, Spine1, Spine2 (부모 먼저)
    readonly Transform[][,] fingerJ = new Transform[2][,];                // [손][손가락 검지·중지·약지·새끼·엄지, 마디 0~2]
    readonly Transform[] handB = new Transform[2];
    readonly Vector3[] curlAxis = new Vector3[2];                         // 손 뼈 공간의 굽힘 축 (+ 로 돌리면 손바닥 쪽으로)
    float fingerT;
    readonly bool[] toeUp = { true, true };
    static readonly string[] FingerNames = { "Index", "Middle", "Ring", "Pinky", "Thumb" };
    // 3D-④ MB 수색 더듬기 (영상 B4 통과 09-20): 첫 수색 자리에서 클립 up_grope(깊이 웅크린 몸 + 모션캡처 허리 흔들림) 위에 —
    // 두 손이 번갈아 가까운 면(바닥·벽·갱목)을 짚는다: 들어서 옮기고 → 손가락을 쫙 펴 벌려 짚고 → 짚은 채 문지른다. 자리·길이는 고르지 않게.
    // 손 = 두 뼈 팔 IK, 더 멀리 = 두 손 가운데 쪽으로 엉덩이가 실리고(발은 다리 IK 로 제자리) 멀리 뻗는 쪽 어깨가 내려간다.
    // "들었나?"(Stalker.Heard) = 재생 0 + 짚기 시계 멈춤, 머리만 그 자리를 딱 + 갸웃. 값·식은 blender/anim/preview_upright.py 와 같다
    [System.NonSerialized] public bool driveGrope = true;                 // 사보타주 nogrope (몸만 웅크리고 손은 클립 그대로)
    [System.NonSerialized] public bool flatHands = true;                  // 사보타주 clawhands (짚을 때 손가락을 안 편다)
    public float GropeW { get; private set; }                             // 0 서 있음 · 1 더듬는 중
    public bool Held { get; private set; }                                // "들었나?"로 굳음
    public bool Still => Frozen || Held;
    public readonly bool[] PatResting = new bool[2];                       // 검사: 그 손이 지금 짚고 있나 (0 왼 · 1 오른)
    public readonly float[] PatTipGap = new float[2], PatStraight = new float[2], PatLow = new float[2], PatReach = new float[2];   // 검사: 네 손끝 중 면에서 가장 뜬 거리 · 손가락 곧음(뿌리–끝 ÷ 마디 합) 최소 · 손끝·손목이 면 밑으로 든 깊이(−) · 손끝이 몸 앞으로 나간 거리 (게임 m)
    public readonly Vector3[] PatPoint = new Vector3[2], PatNormal = new Vector3[2];
    public int PatCount { get; private set; }                             // 손을 옮겨 짚은 횟수
    public int PatOnWall { get; private set; }
    struct Pat { public Vector3 from, to, nFrom, nTo, rub; public float t, move, rest; }
    readonly Pat[] pat = new Pat[2];
    int patActive;
    Transform hipsB;
    readonly Transform[,] legB = new Transform[2, 3], armB = new Transform[2, 3];
    readonly Transform[,] tipJ = new Transform[2, 5];
    readonly Vector3[] fingerAxisL = new Vector3[2], palmL = new Vector3[2];
    readonly Vector3[,,] jointDirL = new Vector3[2, 5, 3];
    Vector3 hipShift;
    float rollNow;
    readonly System.Random gropeRng = new System.Random(11);
    static readonly float[] Spread = { 9f, 2f, 6f, 15f, 22f };            // 도, 검지·중지·약지·새끼·엄지가 제 쪽으로 벌어지는 각
    public string RunClip => oldRun ? "run" : "run_knuckle";
    public int LiftCount { get; private set; }                            // 팔 들기(LateUpdate)가 팔을 든 프레임 수 — 새 동작은 0 이어야 한다
    public string Current { get; private set; } = "";
    public float Rate { get; private set; } = 1f;
    public float Speed { get; private set; }                              // 잰 빠르기 m/s (벽타기는 위로 가는 것 포함)
    public float Tilt { get; private set; }                               // 0 = 서 있음, 1 = 벽에 붙음
    public static string GaitName(int g) => g == 0 ? "A crouch-walk matched" : g == 1 ? "B slow run" : g == 2 ? "C crouch-walk capped" : g == 3 ? "D knuckle-walk" : g == 4 ? "E glide" : "F upright (default)";

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
        torso = System.Array.ConvertAll(new[] { "Spine", "Spine1", "Spine2" }, n => System.Array.Find(allT, b => b.name == "mixamorig:" + n));
        toeB = new[] { System.Array.Find(allT, b => b.name == "mixamorig:LeftToeBase"), System.Array.Find(allT, b => b.name == "mixamorig:RightToeBase") };
        for (int h = 0; h < 2; h++)
        {
            string side = h == 0 ? "Left" : "Right";
            handB[h] = System.Array.Find(allT, b => b.name == $"mixamorig:{side}Hand");
            fingerJ[h] = new Transform[5, 3];
            for (int f = 0; f < 5; f++)
                for (int j = 0; j < 3; j++)
                    fingerJ[h][f, j] = System.Array.Find(allT, b => b.name == $"mixamorig:{side}Hand{FingerNames[f]}{j + 1}");
            // 굽는 쪽: 쉬는 자세(팔 벌린 T, 손바닥 아래)에서 가운데 손가락을 20° 씩 돌려 끝이 가장 많이 내려가는 축 — Blender 와 같은 법, 뼈 축은 가져오기에서 바뀌어 재서 고른다
            Transform tip = System.Array.Find(allT, b => b.name == $"mixamorig:{side}HandMiddle4");
            if (handB[h] == null || tip == null || fingerJ[h][1, 0] == null) { handB[h] = null; continue; }
            float best = 0f;
            foreach (var ax in new[] { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back })
            {
                var keep = new Quaternion[3];
                float y0 = transform.InverseTransformPoint(tip.position).y;
                for (int j = 0; j < 3; j++) { keep[j] = fingerJ[h][1, j].localRotation; fingerJ[h][1, j].rotation = Quaternion.AngleAxis(20f, handB[h].rotation * ax) * fingerJ[h][1, j].rotation; }
                float drop = y0 - transform.InverseTransformPoint(tip.position).y;
                for (int j = 0; j < 3; j++) fingerJ[h][1, j].localRotation = keep[j];
                if (drop > best) { best = drop; curlAxis[h] = ax; }
            }
        }
        hipsB = System.Array.Find(allT, b => b.name == "mixamorig:Hips");
        for (int h = 0; h < 2; h++)
        {
            string side = h == 0 ? "Left" : "Right";
            string[] leg = { "UpLeg", "Leg", "Foot" }, armN = { "Arm", "ForeArm", "Hand" };
            for (int j = 0; j < 3; j++)
            {
                legB[h, j] = System.Array.Find(allT, b => b.name == $"mixamorig:{side}{leg[j]}");
                armB[h, j] = System.Array.Find(allT, b => b.name == $"mixamorig:{side}{armN[j]}");
            }
            if (handB[h] == null || fingerJ[h][1, 0] == null) continue;
            // 쉬는 자세(팔 벌린 T, 손바닥 아래)에서 재어 둔다: 손 뼈 공간의 손가락 방향·손바닥 방향, 마디 뼈 공간의 다음 마디 방향
            fingerAxisL[h] = Quaternion.Inverse(handB[h].rotation) * (fingerJ[h][1, 0].position - handB[h].position).normalized;
            palmL[h] = Quaternion.Inverse(handB[h].rotation) * -transform.up;
            for (int f = 0; f < 5; f++)
            {
                tipJ[h, f] = System.Array.Find(allT, b => b.name == $"mixamorig:{side}Hand{FingerNames[f]}4");
                for (int j = 0; j < 3; j++)
                {
                    Transform a = fingerJ[h][f, j], nx = j < 2 ? fingerJ[h][f, j + 1] : tipJ[h, f];
                    if (a != null && nx != null) jointDirL[h, f, j] = Quaternion.Inverse(a.rotation) * (nx.position - a.position).normalized;
                }
            }
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
                case Stalker.State.Alert when Upright: clip = string.IsNullOrEmpty(Current) ? IdleClip : Current; break;   // 포효 없음 — 하던 동작 그대로 굳는다
                case Stalker.State.Catch when Upright: clip = "up_run"; break;                                             // 휘두르기 없음 — 팔 뻗은 채 그대로 들어온다
                case Stalker.State.Alert: clip = "roar"; fade = Tuning.STALKER_ANIM_FADE_FAST_S; offset = Tuning.STALKER_ROAR_START_S; break;
                case Stalker.State.Stun: clip = "hit"; fade = Tuning.STALKER_ANIM_FADE_FAST_S; break;
                case Stalker.State.Catch: clip = "attack_swipe"; fade = Tuning.STALKER_ANIM_FADE_FAST_S; break;
                case Stalker.State.Climb: clip = "crawl"; wall = true; rate = Speed / (Tuning.STALKER_CLIP_SPEED_CRAWL * Tuning.STALKER_MODEL_SCALE); break;
                case Stalker.State.Hidden: clip = Current; break;           // 몸이 안 보인다
                case Stalker.State.Search when Upright && st.Groping: clip = "up_grope"; fade = Tuning.STALKER_GROPE_FADE_S; moving = false; break;
                default:
                    moving = Speed > Tuning.STALKER_ANIM_STILL * (moving ? 1f : 2f);
                    clip = moving ? Locomotion(out rate) : IdleClip;
                    if (Current == "up_grope") fade = Tuning.STALKER_GROPE_FADE_S;
                    break;
            }
        if (!rateMatch) rate = 1f;
        Rate = rate;
        Frozen = Upright && st.enabled && st.state == Stalker.State.Alert;
        Held = Upright && st.enabled && st.Heard;
        anim.speed = freezeTime || Still ? 0f : rate;
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
            body.rotation = Quaternion.Slerp(st.transform.rotation, Quaternion.LookRotation(st.ClimbFacing), Tilt);
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
            : s == Stalker.State.Investigate ? 4 : Held ? 5 : GropeW > 0.5f && driveGrope ? 6 : s == Stalker.State.Search ? 2
            : Upright && s == Stalker.State.Wander && !moving ? 2 : 0;       // 서서 오는 괴물: 배회하다 멈추면 서서 둘러본다 (영상 U4 "찾고 있다")
        HeadMode = mode;
        float wantYaw = 0f, wantPitch = 0f, wantTilt = 0f;
        if (mode == 1 || mode == 3) YawPitch(me - eye, out wantYaw, out wantPitch);
        else if (mode == 4) YawPitch(st.noisePos + Vector3.up * Tuning.EYE_HEIGHT - eye, out wantYaw, out wantPitch);
        if (mode == 3 || mode == 4) wantTilt = headTilt;
        if (mode == 5) { YawPitch(st.HeardPos + Vector3.up * Tuning.EYE_HEIGHT - eye, out wantYaw, out wantPitch); wantTilt = Tuning.STALKER_HEARD_TILT_DEG; }
        if (mode == 6) YawPitch(PatAt(patActive, out _, out _) - eye, out wantYaw, out wantPitch);
        if (mode == 2)
        {
            searchT -= dt;
            if (searchT <= 0f)
            {
                bool up = Upright && st.enabled;                          // 서서 오는 괴물: 고르지 않은 간격으로 머물고, 영상만큼만 돌린다(55°·35°)
                searchT = up ? Mathf.Lerp(Tuning.STALKER_UP_LOOK_HOLD_MIN_S, Tuning.STALKER_UP_LOOK_HOLD_MAX_S, (float)headRng.NextDouble()) : Tuning.STALKER_HEAD_SEARCH_STEP_S;
                searchYaw = ((float)headRng.NextDouble() * 2f - 1f) * (up ? Tuning.STALKER_UP_LOOK_YAW : headYawMax);
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
            Torso(0f, dt);
            return;
        }
        if (mode == 0) { wantYaw = animYaw; wantPitch = animPitch; wantTilt = 0f; }
        // 목표가 바뀌면 STALKER_HEAD_SNAP_S 안에 딱 — 좌우는 ±180 안에서만 움직여 몸 뒤를 가로질러 돌지 않는다
        float rate = mode == 6 ? Tuning.STALKER_GROPE_LOOK_DPS : 180f / Tuning.STALKER_HEAD_SNAP_S;     // 옮기는 손은 느리게 따라간다 — "들었나?"의 딱 돌림과 대비
        lookYaw = Mathf.MoveTowards(lookYaw, wantYaw, rate * dt);
        lookPitch = Mathf.MoveTowards(lookPitch, wantPitch, rate * dt);
        tiltNow = Mathf.MoveTowards(tiltNow, wantTilt, rate * dt);
        float dy = (lookYaw - animYaw) * headW, dp = (lookPitch - animPitch) * headW, dr = tiltNow * headW;
        dy -= Torso(dy, dt);                                               // 상체가 돈 만큼은 머리가 덜 돈다 — 얼굴이 가는 곳은 같다
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

    // 상체가 머리를 늦게(0.5 s 쯤) 따라간다: 머리 각도의 STALKER_UP_TORSO_SHARE, ± STALKER_UP_TORSO_MAX 까지. 척추 세 마디에 나눠 돌린다. 돌려주는 것 = 지금 상체 각도
    float Torso(float headYaw, float dt)
    {
        bool on = Upright && driveTorso && System.Array.IndexOf(torso, null) < 0;
        float want = on ? Mathf.Clamp(headYaw * Tuning.STALKER_UP_TORSO_SHARE, -Tuning.STALKER_UP_TORSO_MAX, Tuning.STALKER_UP_TORSO_MAX) : 0f;
        if (!Still) BodyYaw = Mathf.Lerp(BodyYaw, want, 1f - Mathf.Exp(-Tuning.STALKER_UP_TORSO_FOLLOW * dt));
        if (!on || Mathf.Abs(BodyYaw) < 0.01f) return 0f;
        Quaternion q = Quaternion.AngleAxis(BodyYaw / 3f, transform.up);
        foreach (var b in torso) b.rotation = q * b.rotation;
        return BodyYaw;
    }

    // 손가락 (영상 U4): 4.5 s 한 바퀴 — 주먹을 천천히 쥐었다 편다 1.4 s → 검지부터 차례로 피아노 치듯 두드린다. 두 손은 엇박자. 굳으면 같이 멈춘다. 질주 클립은 갈고리 손을 구워 뒀다
    void Fingers(float dt)
    {
        if (!Still) fingerT += dt;
        var a = new float[3];
        for (int h = 0; h < 2; h++)
        {
            if (handB[h] == null) continue;
            float u = (fingerT + (h == 1 ? 1.9f : 0f)) % 4.5f;
            Vector3 ax = handB[h].rotation * curlAxis[h];
            for (int f = 0; f < 5; f++)
            {
                if (u < 1.4f)
                {
                    float c = Mathf.Sin(Mathf.PI * Mathf.Clamp01((u - f * 0.05f) / 1.2f)); c *= c;
                    a[0] = 8f + 55f * c; a[1] = 10f + 70f * c; a[2] = 8f + 55f * c;
                }
                else
                {
                    float c = Mathf.Max(0f, Mathf.Sin(2f * Mathf.PI * 1.8f * u - f * 1.15f)); c *= c;
                    a[0] = 8f + 42f * c; a[1] = 10f + 18f * c; a[2] = 8f + 12f * c;
                }
                float k = f == 4 ? 0.5f : 1f;
                for (int j = 0; j < 3; j++)
                    if (fingerJ[h][f, j] != null) fingerJ[h][f, j].rotation = Quaternion.AngleAxis(a[j] * k, ax) * fingerJ[h][f, j].rotation;
            }
        }
    }

    // 무게: 발끝이 내려와 닿는 순간 플레이어 화면을 흔든다 — 가까울수록 세게 (영상 U4 와 같은 식)
    void Stomp()
    {
        bool run = Current == "up_run" || Current == "up_jog";
        for (int i = 0; i < 2; i++)
        {
            if (toeB[i] == null) return;
            bool up = transform.InverseTransformPoint(toeB[i].position).y > Tuning.STALKER_UP_TOE_UP_M;
            bool hit = toeUp[i] && !up;
            toeUp[i] = up;
            if (!hit || Still || !(run || Current == "up_walk") || st.player == null) continue;
            float dist = Vector3.Distance(st.player.position, st.transform.position);
            if (dist > Tuning.STALKER_STOMP_MAX_M) continue;
            float amt = (run ? Tuning.STALKER_STOMP_RUN_M : Tuning.STALKER_STOMP_WALK_M) * Mathf.Pow(Mathf.Min(1f, Tuning.STALKER_STOMP_FULL_M / Mathf.Max(dist, 0.9f)), 0.8f);
            StompLog.Add(new Vector2(dist, amt));
            var pl = st.player.GetComponent<Player>();
            if (pl != null) pl.Shake(amt, Tuning.STALKER_STOMP_SPAN_S);
        }
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
        bool search = Upright && st.enabled && st.state == Stalker.State.Search;                       // 더듬는 동안 목을 천천히 내민다 (영상 B4: 0.25 를 1.0 s 에)
        float want = Mathf.Clamp(Mathf.Max(neckWant, auto, search && st.Groping ? Tuning.STALKER_GROPE_NECK_M : 0f), 0f, Tuning.STALKER_NECK_OUT_MAX_M);
        float spd = search ? Tuning.STALKER_GROPE_NECK_M / Tuning.STALKER_GROPE_NECK_S : Tuning.STALKER_NECK_OUT_MAX_M / Mathf.Max(0.02f, neckOutS);
        if (!Held) NeckOutNow = Mathf.MoveTowards(NeckOutNow, want, spd * dt);
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
        if (Frozen)                                                        // 굳음: 턱만 천천히 벌어진다 — "곧 뛰어오겠다" (영상 U4)
        {
            JawDeg = Mathf.MoveTowards(JawDeg, Tuning.STALKER_JAW_FREEZE_DEG, Tuning.STALKER_JAW_FREEZE_DEG / Tuning.STALKER_ALERT_S * dt);
            jaw.localRotation = Quaternion.AngleAxis(JawDeg, jawAxis) * jawRest;
            jaw.localPosition = jawRestPos;
            return;
        }
        switch (Current)
        {
            case "roar": case "attack_swipe": case "up_run": target = jawWideDeg; break;
            case "run": case "run_knuckle": case "run_stand": case "glide_fast": case "glide_chase": case "up_jog": target = Tuning.STALKER_JAW_CHASE_DEG; break;
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
        string clip = ClipFor(Speed, out float clipSpeed);
        rate = Speed / (clipSpeed * Tuning.STALKER_MODEL_SCALE);
        if (gait == 2 && clip == "walk_crouch") rate = Mathf.Min(rate, Tuning.STALKER_WALK_RATE_CAP);
        return clip;
    }

    // 빠르기 → 클립과 그 클립의 원래 빠르기(모델 크기 1). 검사도 이 길로 "이 빠르기엔 무엇이 나와야 하나"를 묻는다
    public string ClipFor(float v, out float clipSpeed)
    {
        bool fast = v > Tuning.STALKER_ANIM_RUN_ABOVE;
        if (gait == 5)
        {
            bool chase = v > Tuning.STALKER_ANIM_CHASE_ABOVE;               // 두 팔을 뻗는 건 잡으러 올 때만 — 소리 조사·철수는 up_jog
            clipSpeed = chase ? Tuning.STALKER_CLIP_SPEED_UP_RUN : fast ? Tuning.STALKER_CLIP_SPEED_UP_JOG : Tuning.STALKER_CLIP_SPEED_UP_WALK;
            return chase ? "up_run" : fast ? "up_jog" : "up_walk";
        }
        if (gait == 4 && fast && !oldRun && !bouncy)
        {
            // 3D-③b M2b: 미끄러지는 걸음 — 몸 높이 고정·공중 0·옆으로 휘는 허리. 빨라져도 박자는 그대로, 보폭이 다른 클립으로 간다
            bool chase = v > Tuning.STALKER_ANIM_CHASE_ABOVE;
            clipSpeed = chase ? Tuning.STALKER_CLIP_SPEED_GLIDE_CHASE : Tuning.STALKER_CLIP_SPEED_GLIDE_FAST;
            return chase ? "glide_chase" : "glide_fast";
        }
        if (gait == 4 && !fast && !stiffSpine)
        {
            clipSpeed = Tuning.STALKER_CLIP_SPEED_GLIDE_WALK;
            return "glide_walk";
        }
        if (fast || gait == 1)
        {
            clipSpeed = oldRun ? Tuning.STALKER_CLIP_SPEED_RUN : Tuning.STALKER_CLIP_SPEED_RUN_KNUCKLE;
            return RunClip;                                               // 3D-③b M2: 손 둘 → 발 둘로 짚는 뜀박질. 옛 run(Mixamo running crawl)은 손목째 바닥 밑이라 팔 들기에 기댔다
        }
        if ((gait == 3 && !oldWalk) || gait == 4)
        {
            clipSpeed = Tuning.STALKER_CLIP_SPEED_KNUCKLE;               // 3D-③b M1: 두 손·두 발로 짚는 네 점 걸음
            return "walk_knuckle";
        }
        clipSpeed = Tuning.STALKER_CLIP_SPEED_WALK;
        return "walk_crouch";
    }

    // 팔이 바닥(벽타기 땐 벽)을 뚫지 않게: 동작을 입힌 뒤 손끝이 모델 발바닥 면 아래면 어깨를 축으로 팔째 들어 올린다.
    // Mixamo 사람 동작을 팔이 무릎 밑까지 오는 몸에 입혀서 run·crawl 에서 손가락이 바닥 아래 0.5 m 까지 들어갔다(09-18 실측, -only anim).
    // 모델 공간 y = 0 이 발바닥 면이다 — 벽타기로 세우면 그 면이 벽 면이 되므로 같은 계산이 벽에도 먹는다
    [System.NonSerialized] public bool clampArms = true;                  // 사보타주 armsink 가 끈다
    Transform[] arms, tips0, tips1;
    public readonly float[] ArmLow = new float[2];                         // 진단: 마지막으로 잰 손끝 높이 (모델 발바닥 면 위 m)
    public readonly float[] ArmLowRaw = new float[2];                      // 진단: 팔 들기 전 손끝 높이 (게임 m)

    // ---- 3D-④ MB 더듬기
    static float Smooth(float u) { u = Mathf.Clamp01(u); return u * u * (3f - 2f * u); }
    float Rnd(float a, float b) => Mathf.Lerp(a, b, (float)gropeRng.NextDouble());

    // 두 뼈 IK: b(팔꿈치·무릎)를 굽혀 a→c 길이를 맞추고, a 를 돌려 c 를 과녁에 놓는다
    static void TwoBone(Transform a, Transform b, Transform c, Vector3 target, float w)
    {
        float lab = (b.position - a.position).magnitude, lcb = (c.position - b.position).magnitude;
        float lat = Mathf.Clamp((target - a.position).magnitude, 0.01f, (lab + lcb) * 0.999f);
        float want = Mathf.Acos(Mathf.Clamp((lab * lab + lcb * lcb - lat * lat) / (2f * lab * lcb), -1f, 1f)) * Mathf.Rad2Deg;
        Vector3 ba = a.position - b.position, bc = c.position - b.position;
        Vector3 axis = Vector3.Cross(ba, bc);
        if (axis.sqrMagnitude < 1e-8f) axis = Vector3.Cross(ba, Vector3.up);
        b.rotation = Quaternion.Slerp(Quaternion.identity, Quaternion.AngleAxis(want - Vector3.Angle(ba, bc), axis.normalized), w) * b.rotation;
        a.rotation = Quaternion.Slerp(Quaternion.identity, Quaternion.FromToRotation(c.position - a.position, target - a.position), w) * a.rotation;
    }

    // 짚을 자리 고르기: 가끔 옆·앞의 세운 면(벽·갱목)을 먼저 찾고, 없으면 제 쪽 앞 바닥. 플레이어 몸은 면으로 안 친다(닿는다고 찾는 게 아니다 — 찾는 건 Stalker 의 2 m 규칙)
    void PickSpot(int h, out Vector3 point, out Vector3 normal)
    {
        Transform r = st.transform;
        float sd = h == 0 ? -1f : 1f;
        bool Ok(RaycastHit hit) => st.player == null || !hit.transform.IsChildOf(st.player);
        if (gropeRng.NextDouble() < Tuning.STALKER_GROPE_WALL_CHANCE)
        {
            Vector3 dir = (r.forward * Rnd(0.2f, 1f) + r.right * sd * Rnd(0.3f, 1f)).normalized;
            if (Physics.Raycast(transform.position + Vector3.up * Rnd(0.9f, 1.5f), dir, out RaycastHit wh, Tuning.STALKER_GROPE_FAR_M + 0.3f, ~0, QueryTriggerInteraction.Ignore) && Mathf.Abs(wh.normal.y) < 0.5f && Ok(wh))
            {
                point = wh.point; normal = wh.normal; PatOnWall++;
                return;
            }
        }
        Vector3 p = transform.position + r.right * (sd * Rnd(-0.15f, Tuning.STALKER_GROPE_SIDE_M)) + r.forward * Rnd(Tuning.STALKER_GROPE_NEAR_M, Tuning.STALKER_GROPE_FAR_M);
        if (Physics.Raycast(p + Vector3.up * 1.2f, Vector3.down, out RaycastHit fh, 2.5f, ~0, QueryTriggerInteraction.Ignore) && fh.normal.y > 0.5f && Ok(fh))
        { point = fh.point; normal = fh.normal; }
        else { point = p; normal = Vector3.up; }
    }

    void StartMove(int h)
    {
        ref Pat q = ref pat[h];
        q.from = q.to + q.rub; q.nFrom = q.nTo;
        PickSpot(h, out q.to, out q.nTo);
        Vector3 rub = Vector3.ProjectOnPlane(st.transform.forward * Rnd(-1f, 0.4f) + st.transform.right * Rnd(-1f, 1f) + Vector3.up * Rnd(-1f, 1f), q.nTo);
        q.rub = rub.normalized * Rnd(0.4f, 1f) * Tuning.STALKER_GROPE_RUB_M;
        q.move = Rnd(Tuning.STALKER_GROPE_MOVE_MIN_S, Tuning.STALKER_GROPE_MOVE_MAX_S);
        q.rest = Rnd(Tuning.STALKER_GROPE_REST_MIN_S, Tuning.STALKER_GROPE_REST_MAX_S);
        q.t = 0f;
        PatCount++;
    }

    // 그 손의 지금 자리(면 위) · 면 법선 · 짚음 0~1 (떼자마자 조금 오므리고, 내려놓기 전에 편다)
    Vector3 PatAt(int h, out Vector3 normal, out float contact)
    {
        Pat q = pat[h];
        if (q.t >= q.move) { normal = q.nTo; contact = 1f; return q.to + q.rub * Smooth((q.t - q.move) / Mathf.Max(0.01f, q.rest)); }
        float u = Smooth(q.t / q.move);
        normal = Vector3.Slerp(q.nFrom, q.nTo, u).normalized;
        contact = Mathf.Max(Smooth(1f - u / 0.15f), Smooth((u - 0.7f) / 0.3f));
        float lift = Tuning.STALKER_GROPE_LIFT_M * (Vector3.Dot(q.nFrom, q.nTo) > 0.9f ? 1f : 1.6f);
        return Vector3.Lerp(q.from, q.to, u) + normal * (lift * Mathf.Sin(Mathf.PI * u));
    }

    // 몸: 짚기 시계 · 두 손 가운데 쪽으로 엉덩이 실기(발은 제자리) · 멀리 뻗는 쪽 어깨 내리기. 머리·상체 돌림보다 먼저 돈다
    void GropeBody(float dt, bool on)
    {
        if (on && GropeW <= 0f)                                            // 막 웅크리기 시작: 두 손은 제 어깨 앞 바닥에서, 오른손부터 옮긴다
        {
            for (int h = 0; h < 2; h++)
            {
                pat[h] = new Pat { to = transform.position + st.transform.right * (h == 0 ? -0.5f : 0.5f) + st.transform.forward * 1.1f, nTo = Vector3.up, t = 99f, move = 0.01f, rest = 0.01f };
            }
            patActive = 1; StartMove(1);
            hipShift = Vector3.zero; rollNow = 0f;
        }
        GropeW = Mathf.MoveTowards(GropeW, on ? 1f : 0f, dt / Tuning.STALKER_GROPE_FADE_S);
        if (GropeW <= 0f || hipsB == null) return;
        if (on && !Held)
        {
            pat[patActive].t += dt;
            if (pat[patActive].t >= pat[patActive].move + pat[patActive].rest) { patActive = 1 - patActive; StartMove(patActive); }
            Vector3 mid = st.transform.InverseTransformPoint((PatAt(0, out _, out _) + PatAt(1, out _, out _)) * 0.5f) - new Vector3(0f, 0f, 1.1f);
            mid.y = 0f;
            float k = 1f - Mathf.Exp(-3.5f * dt);
            hipShift = Vector3.Lerp(hipShift, Vector3.ClampMagnitude(mid, Tuning.STALKER_GROPE_HIP_SHIFT_M), k);
            float far = armB[0, 0] != null && armB[1, 0] != null ? (PatAt(0, out _, out _) - armB[0, 0].position).magnitude - (PatAt(1, out _, out _) - armB[1, 0].position).magnitude : 0f;
            rollNow = Mathf.Lerp(rollNow, Mathf.Clamp(far * 27f, -Tuning.STALKER_GROPE_ROLL_DEG, Tuning.STALKER_GROPE_ROLL_DEG), k);
        }
        var footP = new Vector3[2]; var footR = new Quaternion[2];
        for (int h = 0; h < 2; h++) if (legB[h, 2] != null) { footP[h] = legB[h, 2].position; footR[h] = legB[h, 2].rotation; }
        hipsB.position += st.transform.TransformVector(hipShift) * GropeW;
        if (torso[0] != null) torso[0].rotation = Quaternion.AngleAxis(rollNow * GropeW, st.transform.forward) * torso[0].rotation;
        for (int h = 0; h < 2; h++)
            if (legB[h, 0] != null && legB[h, 1] != null && legB[h, 2] != null)
            {
                TwoBone(legB[h, 0], legB[h, 1], legB[h, 2], footP[h], 1f);
                legB[h, 2].rotation = footR[h];
            }
    }

    // 손: 손목 과녁(팔 길이 94 % 안으로 면을 따라 당김) → 팔 IK → 손 방향(손가락은 어깨에서 뻗는 쪽, 손바닥은 면 쪽) → 손가락 펴 벌리기 → 가장 낮은 손끝이 면에 닿게 한 번 바로잡기
    void GropeArms()
    {
        for (int h = 0; h < 2; h++)
        {
            PatResting[h] = false;
            if (armB[h, 0] == null || armB[h, 1] == null || handB[h] == null) continue;
            Vector3 point = PatAt(h, out Vector3 n, out float c);
            point += Vector3.up * (1.1f * (1f - GropeW));                  // 몸이 덜 접힌 동안은 손도 그만큼 떠 있다
            Vector3 sh = armB[h, 0].position;
            float len = ((armB[h, 1].position - sh).magnitude + (handB[h].position - armB[h, 1].position).magnitude) * Tuning.STALKER_GROPE_ARM_USE;
            Vector3 yv = Vector3.forward;
            for (int pass = 0; pass < 2; pass++)
            {
                Vector3 target = point + n * (Tuning.STALKER_GROPE_WRIST_M + 0.07f * (1f - c));
                float off = Vector3.Dot(sh - target, n);
                Vector3 s0 = sh - n * off;
                float r = Mathf.Sqrt(Mathf.Max(0.01f, len * len - off * off));
                if ((target - s0).magnitude > r) target = s0 + (target - s0).normalized * r;
                yv = ((target - s0).normalized + n * (0.30f * (1f - c))).normalized;
                TwoBone(armB[h, 0], armB[h, 1], handB[h], target, GropeW);
                Quaternion q = Quaternion.LookRotation(yv, n) * Quaternion.Inverse(Quaternion.LookRotation(fingerAxisL[h], -palmL[h]));
                handB[h].rotation = Quaternion.Slerp(handB[h].rotation, q, GropeW);
                if (pass == 0)
                {
                    float kf = flatHands ? GropeW * (0.55f + 0.45f * c) : 0f;   // 옮기는 동안에도 반쯤은 펴 둔다 — 다 오므리면 낮게 옮길 때 끝이 면 밑으로 들어간다
                    for (int f = 0; f < 5 && kf > 0f; f++)
                    {
                        if (fingerJ[h][f, 0] == null) continue;
                        Vector3 lat = Vector3.ProjectOnPlane(Vector3.ProjectOnPlane(fingerJ[h][f, 0].position - handB[h].position, yv), n).normalized;
                        Vector3 to = (Vector3.ProjectOnPlane(yv, n).normalized + lat * Mathf.Tan(Spread[f] * Mathf.Deg2Rad)).normalized;
                        for (int j = 0; j < 3; j++)
                            if (fingerJ[h][f, j] != null)
                                fingerJ[h][f, j].rotation = Quaternion.Slerp(Quaternion.identity, Quaternion.FromToRotation(fingerJ[h][f, j].rotation * jointDirL[h, f, j], to), kf) * fingerJ[h][f, j].rotation;
                    }
                }
                if (c < 1f || GropeW < 0.97f) break;
                float low = Vector3.Dot(handB[h].position - point, n) - Tuning.STALKER_GROPE_WRIST_M;
                for (int f = 0; f < 4; f++) if (tipJ[h, f] != null) low = Mathf.Min(low, Vector3.Dot(tipJ[h, f].position - point, n));
                if (pass == 0) point += n * (0.006f - low);
            }
            if (c < 1f || GropeW < 0.97f) continue;
            PatResting[h] = true; PatPoint[h] = PatAt(h, out _, out _); PatNormal[h] = n;
            float gap = 0f, lowest = 99f, straight = 1f, reach = 0f;
            for (int f = 0; f < 4; f++)
            {
                if (tipJ[h, f] == null || fingerJ[h][f, 0] == null) continue;
                float d = Vector3.Dot(tipJ[h, f].position - PatPoint[h], n);
                gap = Mathf.Max(gap, d); lowest = Mathf.Min(lowest, d);
                reach = Mathf.Max(reach, Vector3.Dot(tipJ[h, f].position - st.transform.position, st.transform.forward));
                float sum = (fingerJ[h][f, 1].position - fingerJ[h][f, 0].position).magnitude + (fingerJ[h][f, 2].position - fingerJ[h][f, 1].position).magnitude + (tipJ[h, f].position - fingerJ[h][f, 2].position).magnitude;
                straight = Mathf.Min(straight, (tipJ[h, f].position - fingerJ[h][f, 0].position).magnitude / Mathf.Max(1e-4f, sum));
            }
            PatTipGap[h] = gap; PatLow[h] = lowest; PatStraight[h] = straight; PatReach[h] = reach;
        }
    }

    // 천장 밑 숙이기 (MAP1): 애니메이션이 만든 자세에서 머리 꼭대기가 천장 − 여유를 넘는 만큼 엉덩이를 낮추고(다리 IK) 모자라면 허리를 숙인다
    [System.NonSerialized] public bool stoop = true;                      // 사보타주 bigmonster 와 함께 볼 때 끄는 손잡이
    public float StoopDrop { get; private set; }
    public float StoopPitch { get; private set; }
    public float CeilingAbove { get; private set; } = 99f;               // 검사: 그 자리 천장 높이 (발 기준)
    CharacterController stCC;
    void Stoop(float dt)
    {
        if (!stoop || hipsB == null || headB == null || torso[0] == null || Tilt > 0f) { StoopDrop = StoopPitch = 0f; return; }
        Vector3 root = st.transform.position;
        const int mask = ~((1 << 2) | (1 << Pickaxe.ViewModelLayer));
        stCC ??= st.GetComponent<CharacterController>();
        CeilingAbove = Stalker.RayIgnore(root + Vector3.up * 1.0f, Vector3.up, 6f, mask, stCC, out RaycastHit hit) ? hit.distance + 1.0f : 99f;   // 제 캡슐은 뺀다
        Vector3 overHead = new Vector3(headB.position.x, root.y + 1.0f, headB.position.z);   // 천장은 아치라 가장자리가 낮다 — 머리 바로 위도 잰다 (09-24: 가운데만 재서 달릴 때 머리가 4 cm 닿았다)
        if (Stalker.RayIgnore(overHead, Vector3.down, 1.4f, mask, stCC, out _) && Stalker.RayIgnore(overHead, Vector3.up, 6f, mask, stCC, out RaycastHit hh))
            CeilingAbove = Mathf.Min(CeilingAbove, hh.distance + 1.0f);
        float limit = root.y + CeilingAbove - Tuning.STALKER_STOOP_MARGIN;
        float top = headB.position.y + Tuning.STALKER_STOOP_HEAD_TOP;
        float wantDrop = Mathf.Clamp(top - limit, 0f, Tuning.STALKER_STOOP_DROP_MAX);
        // 엉덩이를 낮춘 뒤에도 넘는 만큼 허리 각: 등뼈 뿌리에서 머리 꼭대기로 가는 막대를 앞으로 돌려 잰다 (뼈는 안 건드리고 셈만)
        Vector3 pivot = torso[0].position - Vector3.up * wantDrop, v = headB.position + Vector3.up * Tuning.STALKER_STOOP_HEAD_TOP - Vector3.up * wantDrop - pivot;
        float wantPitch = 0f;
        for (float a = 0f; a <= Tuning.STALKER_STOOP_PITCH_MAX; a += 2.5f)
        {
            wantPitch = a;
            if (pivot.y + (Quaternion.AngleAxis(a, st.transform.right) * v).y <= limit) break;
        }
        float kDown = 1f - Mathf.Exp(-dt / Tuning.STALKER_STOOP_DOWN_S), kUp = 1f - Mathf.Exp(-dt / Tuning.STALKER_STOOP_S);   // 숙이기는 빨리, 펴기는 천천히
        StoopDrop = Mathf.Lerp(StoopDrop, wantDrop, wantDrop > StoopDrop ? kDown : kUp);
        StoopPitch = Mathf.Lerp(StoopPitch, wantPitch, wantPitch > StoopPitch ? kDown : kUp);
        if (StoopDrop < 0.005f && StoopPitch < 0.5f) return;
        var footP = new Vector3[2]; var footR = new Quaternion[2];
        for (int h = 0; h < 2; h++) if (legB[h, 2] != null) { footP[h] = legB[h, 2].position; footR[h] = legB[h, 2].rotation; }
        Quaternion headWorld = headB.rotation;
        hipsB.position -= Vector3.up * StoopDrop;
        torso[0].rotation = Quaternion.AngleAxis(StoopPitch, st.transform.right) * torso[0].rotation;
        headB.rotation = headWorld;                                        // 쳐다보는 방향은 그대로 (허리만 숙인다)
        for (int h = 0; h < 2; h++)
            if (legB[h, 0] != null && legB[h, 1] != null && legB[h, 2] != null)
            {
                TwoBone(legB[h, 0], legB[h, 1], legB[h, 2], footP[h], 1f);
                legB[h, 2].rotation = footR[h];
            }
    }

    void LateUpdate()
    {
        if (Upright)
            GropeBody(Time.deltaTime, st.enabled && st.Groping);
        if (neckB != null && headB != null && driveHead)
            Head(Time.deltaTime);
        if (neckExt != null && driveNeck)
            NeckOut(Time.deltaTime);
        if (Upright)
            Stoop(Time.deltaTime);                                        // 머리 돌리기·목 빼기 뒤에 — 앞에서 하면 그 둘이 머리를 다시 들어 천장에 닿았다 (09-24)
        if (jaw != null && driveJaw)
            Jaw(Time.deltaTime);
        if (Upright && driveFingers && Current != "up_run")
            Fingers(Time.deltaTime);
        if (GropeW > 0f && driveGrope)
            GropeArms();
        if (Upright && stomp)
            Stomp();
        if (straightFingers)
            for (int i = 0; i < fingers.Length; i++) fingers[i].localRotation = fingerRest[i];
        if (!clampArms || GropeW > 0f)                                     // 더듬는 손은 일부러 면에 닿는다 — 팔 들기가 떼어 놓으면 안 된다
            return;
        if (arms == null)
        {
            var all = GetComponentsInChildren<Transform>();
            arms = new[] { System.Array.Find(all, b => b.name == "mixamorig:LeftArm"), System.Array.Find(all, b => b.name == "mixamorig:RightArm") };
            if (arms[0] == null || arms[1] == null) { clampArms = false; return; }
            // 뼈만 — m3 는 갱목·끈 물체가 팔 뼈 밑에 노드로 매달려 있어(09-22) 그 노드가 발톱 끝으로 잡히면 팔을 계속 든다(걷기 팔 들기 344번, 발톱 −0.78 m)
            tips0 = System.Array.FindAll(arms[0].GetComponentsInChildren<Transform>(), b => b.name.StartsWith("mixamorig:"));
            tips1 = System.Array.FindAll(arms[1].GetComponentsInChildren<Transform>(), b => b.name.StartsWith("mixamorig:"));
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
