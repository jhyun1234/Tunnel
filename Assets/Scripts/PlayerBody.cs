using System.Linq;
using UnityEngine;
using UnityEngine.Rendering;

// 3D-P 플레이어 몸 (제안서 docs/제안서_3DP_플레이어_모델.md, 승인 09-29). 모델 하나(Assets/Tunnel/Player/player.fbx, 사람형 · Mixamo 뼈대)에 스위치 하나:
//  Self (내 몸, 1인칭) = 카메라에 붙고 팔(PlayerArms)만 그린다 · 곡괭이 층(ViewModel 레이어 — 오버레이 카메라, PickLight 만 비춤) · 그림자 없음.
//    곡괭이가 주인이다 — 곡괭이 움직임은 안 바꾸고 오른손이 뷰모델 곡괭이 손잡이 GRIP_Rear 를 따라간다. 왼손은 캘 때도 화면 밖 — 한 손 캐기
//    (판정 ④ 사용자 09-30 "두 손으로 캘 때 손 위치가 이상하다. 중지와 검지 사이에 자루가 들어가 있다. 한 손으로 캐는 걸로"). 빈손이면 두 손 화면 밖.
//    캐는 동안(동작 표)은 몸이 표 틀(Kevin 몸 자리)에 서고 Kevin 캐기 동작을 곡괭이와 같은 박자로 튼다. 팔이 안 닿으면 (안 그리는) 몸을 손잡이 쪽으로 민다.
//  Other (남의 몸, 3인칭) = 땅에 서서 몸 · 팔 · 소품을 다 그린다 · 보통 층(머리등이 비춤) · 곡괭이 복사본을 오른손에 쥔다. Shift+7 판정 몸 · NET-1 다른 플레이어.
// 스위치는 그리는 것 · 조명 층 · 붙는 곳만 바꾼다 — 모델 · 뼈대 · 동작 묶음은 같다. 세운 몸(Stand)은 내 몸을 복사해 Other 로 바꾼 것.
// 동작 묶음 = Resources/Generated/PlayerAnim (빌드 때 BuildM1 이 Kevin 동작으로 만든다, git 에서 뺌). Kevin 이 없으면 빈 상태 — 손은 그래도 손잡이를 쥔다.
// 손: 팔꿈치 · 어깨는 Unity 사람형 IK(OnAnimatorIK)가 손목을 목표에 끌어다 붙이며 굽히고, 손 방향 · 주먹은 LateUpdate 에서 (손가락 뼈 = 엄지 · 검지).
[DefaultExecutionOrder(100)]   // Player · Pickaxe 가 이번 프레임 곡괭이 자리를 정한 뒤
[RequireComponent(typeof(Animator))]
public class PlayerBody : MonoBehaviour
{
    public enum Mode { Self, Other }
    public Mode mode;
    public Transform cam;          // Self 가 붙는 곳 (메인 카메라)
    public Pickaxe pickaxe;        // Self: 뷰모델 곡괭이 · Other: 곡괭이 모양을 복사해 온다
    // 3D-P2 재질 (BuildM1 이 넣는다): 새 재질 PlayerSkin · 옛(찰흙) 재질 · 탄가루 판 셋. 판정 키(DevHud Shift+1~6)는 아래 정적 값을 바꾸고 lookVer 를 올린다
    public Material skinAsset, clay;
    public Texture[] dirt = new Texture[0];
    public static float clothDetail = Tuning.PLAYER_CLOTH_DETAIL, smoothMul = Tuning.PLAYER_SMOOTH_MUL;
    public static int dirtLevel = Tuning.PLAYER_DIRT_LEVEL, lookVer;
    public static bool clayLook, forceClay, noDetail;       // forceClay · noDetail = 사보타주 claybody · nodetail
    // 몸 크기 (사용자 09-30 "모델 1.72 와 시점 1.78 의 차이가 크다" → 키 하나로 같이): 1인칭 눈 = 모델 눈 × 이 값. 판정 키 Shift+− = 가 Player.standEye 와 같이 바꾼다 (DevHud)
    public static float scale = Tuning.PLAYER_SCALE;
    // 사보타주 (M1Check): 손을 안 붙임 · 1인칭에 몸 전체 · 스위치가 안 먹음 · 세운 몸을 스위치 없이 따로 · Kevin 동작 없이(다른 컴퓨터)
    public static bool noIk, fpBody, noSwitch, standalone, noKevin, twoHands;   // twoHands: 판정 ④ 전 — 캘 때 왼손이 앞 손잡이(GRIP_Front)로
    [System.NonSerialized] public float fpForward = Tuning.PLAYER_FP_OFFSET.z;   // 판정 키 Shift+← →
    [System.NonSerialized] public string action = "idle";                        // Other: idle → mine → turn (Shift+8)

    class Hand
    {
        public Transform hand, shoulder;
        public Transform[] fingers;                         // 검지 1 2 3 · 엄지 1 2 3
        public Quaternion[] bind = new Quaternion[6];
        public Vector3 palm, idxAxis, thAxis;                // 쥐는 점(손목 뼈 기준) · 주먹 쥐는 축
        public Quaternion frame;                            // 손 틀: 앞 = 손가락 쪽, 위 = 엄지 쪽
        public Quaternion grip;                             // 쥔 곡괭이 방향 (손목 뼈 기준) — 오른손은 Kevin 이 내려친 순간 쥔 방향을 잰다(MeasureGrip)
        public float w;                                     // 0 = 쉼(동작 · 화면 밖) → 1 = 손잡이를 쥠
        public Vector3 wrist, shLocal;
        public Quaternion want, animRot;
        public bool ik;
    }
    Hand R, L;
    Animator anim;
    Renderer[] rends;
    Renderer arms;
    Material skinRt, clayRt, fpSkin;
    float clay0;                                            // 옛 재질의 매끈함 (0.25) — Shift+3 4 배율을 옛 재질에도 (검사가 "윤 몫"을 견준다)                                // 새 재질의 실행 중 사본(판정 키가 바꾼다 — 에셋은 그대로) · 1인칭 팔만 어둡게 (PLAYER_FP_ARM_TINT)
    int myLookVer = -1;
    SkinnedMeshRenderer bodySkin;
    Vector3 headBind, hipsBind, bodyFix;                    // bodyFix: 동작이 없을 때 몸 가운데를 처음 자리로 (뿌리 기준)
    Transform hips;
    int lateFrames;
    Transform ownPick;
    float wMine, t, yaw0, idleLen = 1f, mineLen = 1f;
    bool hasMine, hasClips;
    bool Still => noKevin || !hasClips;                     // 동작 없음(Kevin 이 없는 컴퓨터) — 사람형 빈 상태는 몸 가운데를 발밑에 둬 93 cm 가라앉았다(09-29 nokevin)
    Vector3 minePos;
    Quaternion mineRot = Quaternion.identity;
    string state = "";
    // 곡괭이 틀에서 손 틀: 날(−X) 쪽 = 손가락, 자루 위(+Y, 머리 쪽) = 오른손 엄지 · 왼손은 엄지가 자루 끝 쪽(두 손 다 위에서 감아쥠)
    static readonly Quaternion PickGripR = Quaternion.LookRotation(Vector3.left, Vector3.up), PickGripL = Quaternion.LookRotation(Vector3.left, Vector3.down);

    public Animator Anim => anim;
    public Transform OwnPick => ownPick;
    public Vector3 RightGripPoint => R.hand.TransformPoint(R.palm);   // 검사: 쥐는 점
    public Vector3 LeftGripPoint => L.hand.TransformPoint(L.palm);
    public bool RightOn => R.w >= 1f;                                // 다 쥔 채 (바뀌는 중이 아님)
    public bool LeftOn => L.w >= 1f;

    void Awake()
    {
        anim = GetComponent<Animator>();
        anim.runtimeAnimatorController = Resources.Load<RuntimeAnimatorController>(Tuning.PLAYER_ANIM_RESOURCE);
        anim.applyRootMotion = false;
        anim.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        hasClips = anim.runtimeAnimatorController != null && anim.runtimeAnimatorController.animationClips.Length > 0;
        if (anim.runtimeAnimatorController != null)
            foreach (var c in anim.runtimeAnimatorController.animationClips)
            {
                if (c.name.Contains("Idle")) idleLen = c.length;
                if (c.name.Contains("Mining")) { mineLen = c.length; hasMine = true; }
            }
        rends = GetComponentsInChildren<Renderer>(true);
        arms = rends.First(r => r.name == "PlayerArms");
        bodySkin = rends.OfType<SkinnedMeshRenderer>().First(r => r.name == "PlayerBody");
        foreach (var s in rends.OfType<SkinnedMeshRenderer>()) s.updateWhenOffscreen = true;   // 뿌리가 카메라 밑이라 경계 상자가 어긋나 팔이 깜빡이지 않게
        headBind = transform.InverseTransformPoint(anim.GetBoneTransform(HumanBodyBones.Head).position);
        hips = anim.GetBoneTransform(HumanBodyBones.Hips);
        hipsBind = transform.InverseTransformPoint(hips.position);
        R = MakeHand(true);
        L = MakeHand(false);
    }

    Hand MakeHand(bool right)
    {
        HumanBodyBones B(HumanBodyBones r, HumanBodyBones l) => right ? r : l;
        var h = new Hand
        {
            hand = anim.GetBoneTransform(B(HumanBodyBones.RightHand, HumanBodyBones.LeftHand)),
            shoulder = anim.GetBoneTransform(B(HumanBodyBones.RightUpperArm, HumanBodyBones.LeftUpperArm)),
            fingers = new[]
            {
                B(HumanBodyBones.RightIndexProximal, HumanBodyBones.LeftIndexProximal), B(HumanBodyBones.RightIndexIntermediate, HumanBodyBones.LeftIndexIntermediate),
                B(HumanBodyBones.RightIndexDistal, HumanBodyBones.LeftIndexDistal), B(HumanBodyBones.RightThumbProximal, HumanBodyBones.LeftThumbProximal),
                B(HumanBodyBones.RightThumbIntermediate, HumanBodyBones.LeftThumbIntermediate), B(HumanBodyBones.RightThumbDistal, HumanBodyBones.LeftThumbDistal),
            }.Select(b => anim.GetBoneTransform(b)).ToArray(),
        };
        // 손 틀: 손가락 쪽 = 검지 뿌리, 엄지 쪽 = 엄지 뿌리에서 손가락 쪽을 뺀 것, 손바닥 = 둘의 곱(오른손 · 왼손 방향이 반대)
        Vector3 f = h.hand.InverseTransformPoint(h.fingers[0].position).normalized, th = h.hand.InverseTransformPoint(h.fingers[3].position);
        Vector3 tt = (th - f * Vector3.Dot(th, f)).normalized, n = right ? Vector3.Cross(f, tt) : Vector3.Cross(tt, f);
        h.palm = f * Tuning.PLAYER_PALM_ALONG_M + n * Tuning.PLAYER_PALM_IN_M;
        h.frame = Quaternion.LookRotation(f, tt);
        h.grip = h.frame * Quaternion.Inverse(right ? PickGripR : PickGripL);
        for (int i = 0; i < 6; i++) h.bind[i] = h.fingers[i].localRotation;
        h.idxAxis = CurlAxis(h, 0, 1);
        h.thAxis = CurlAxis(h, 3, 5);
        h.shLocal = transform.InverseTransformPoint(h.shoulder.position);
        return h;
    }

    // 주먹 쥐는 축: 뿌리 마디를 30° 돌려 끝 마디가 쥐는 점에 가장 가까워지는 뼈 축 (뼈 축 방향은 리그마다 다르다)
    static Vector3 CurlAxis(Hand h, int root, int tip)
    {
        Vector3 palm = h.hand.TransformPoint(h.palm), best = Vector3.right;
        float bestD = float.MaxValue;
        var q0 = h.fingers[root].localRotation;
        foreach (var ax in new[] { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back })
        {
            h.fingers[root].localRotation = q0 * Quaternion.AngleAxis(30f, ax);
            float d = Vector3.Distance(h.fingers[tip].position, palm);
            if (d < bestD) { bestD = d; best = ax; }
        }
        h.fingers[root].localRotation = q0;
        return best;
    }

    void Start()
    {
        MeasureGrip();
        Apply();
    }

    // 오른손이 쥔 곡괭이 방향 = Kevin 이 내려친 순간 이 몸의 손과 동작 표 곡괭이의 사이 (사람형이라 손 방향이 Kevin 과 같다).
    // 지어낸 손 틀(날 = 손가락 쪽, 자루 = 엄지 쪽)로는 세운 몸이 내려칠 때 곡괭이가 가슴을 가로질렀다(09-29 캡처). Kevin · 표가 없으면 지어낸 틀 그대로
    void MeasureGrip()
    {
        var mm = pickaxe != null ? pickaxe.motion : null;
        if (noKevin || !hasMine || mm == null || mm.Samples < 2) return;
        anim.Play("Mine", 0, 0f);
        anim.SetFloat("MineT", mm.strikeT / mineLen);             // 상태 시각은 매개변수가 정한다 (Play 의 시각은 안 먹는다 — 첫 판은 동작 0 초 자세를 쟀다)
        anim.Update(0f);
        R.grip = Quaternion.Inverse(R.hand.rotation) * transform.rotation * mm.pickRot[Mathf.Clamp(Mathf.RoundToInt(mm.strikeT * mm.rate), 0, mm.Samples - 1)];
        Debug.Log($"PLAYER_GRIP {name} right hand at strike {transform.InverseTransformPoint(R.hand.position):F3} (몸 뿌리 기준)");
    }

    // 스위치: 그리는 것 · 조명 층 · 붙는 곳만 바뀐다
    public void SetMode(Mode m)
    {
        if (noSwitch) return;
        mode = m;
        Apply();
    }

    void Apply()
    {
        bool self = mode == Mode.Self;
        ApplyLook();
        foreach (var r in rends)
        {
            r.enabled = !self || r == arms || fpBody;
            r.gameObject.layer = self ? Pickaxe.ViewModelLayer : 0;
            r.renderingLayerMask = self ? Pickaxe.ViewModelRenderingLayer : Pickaxe.DefaultRenderingLayer;
            r.shadowCastingMode = self ? ShadowCastingMode.Off : ShadowCastingMode.On;
        }
        if (self) transform.SetParent(cam, false);
        else
        {
            transform.SetParent(null, true);
            if (ownPick == null) MakeOwnPick();
            LensGlow();
        }
        if (ownPick != null) ownPick.gameObject.SetActive(!self);
        R.w = L.w = wMine = 0f;
        t = 0f;
    }

    // Other: 곡괭이 모양을 복사해 오른손에 — 손 틀과 곡괭이 틀을 맞춘다(1인칭에서 손이 곡괭이를 쥐는 관계를 거꾸로)
    void MakeOwnPick()
    {
        ownPick = R.hand.Find("HeldPick") ?? Instantiate(pickaxe.mesh.gameObject, R.hand).transform;   // 내 몸을 복사한 세운 몸은 이미 들고 있을 수 있다
        ownPick.name = "HeldPick";
        FitPick();
        foreach (var x in ownPick.GetComponentsInChildren<Transform>(true)) x.gameObject.layer = 0;
        foreach (var r in ownPick.GetComponentsInChildren<Renderer>(true))
        {
            r.renderingLayerMask = Pickaxe.DefaultRenderingLayer;
            r.shadowCastingMode = ShadowCastingMode.On;
        }
    }

    // 손에 든 곡괭이는 몸이 커져도 제 크기 — 몸 배율만큼 줄여 넣는다
    void FitPick()
    {
        ownPick.localScale = pickaxe.mesh.localScale / scale;
        ownPick.localRotation = R.grip;
        ownPick.localPosition = R.palm - ownPick.localRotation * Vector3.Scale(ownPick.localScale, Tuning.GRIP_REAR);
    }

    // 남의 램프는 렌즈만 빛난다(빛은 안 낸다 — 남의 머리등 빛은 NET-1). Lit 발광은 빌드에서 변형이 빠져 검게 나왔다(09-15) → 괴물 눈과 같은 Unlit
    void LensGlow()
    {
        var lens = rends.FirstOrDefault(r => r.name == "Lamp_Lens");
        var sh = Shader.Find("Universal Render Pipeline/Unlit");
        if (lens == null || sh == null) return;
        var m = new Material(sh);
        m.SetColor("_BaseColor", Tuning.LAMP_COLOR);
        lens.sharedMaterial = m;
    }

    // Shift+7: 내 몸을 복사해 남의 몸으로 — 같은 모델 · 뼈대 · 동작 묶음
    public static GameObject Stand(PlayerBody src, Vector3 pos, float yaw)
    {
        var go = Instantiate(src.gameObject);
        go.name = "StoodBody";
        var pb = go.GetComponent<PlayerBody>();
        if (standalone)                                           // 사보타주: 스위치 없이 따로 만든 몸
        {
            DestroyImmediate(pb);
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) { r.enabled = true; r.gameObject.layer = 0; }
            go.transform.SetPositionAndRotation(Ground(pos), Quaternion.Euler(0f, yaw, 0f));
            return go;
        }
        pb.CopyHands(src);
        pb.SetMode(Mode.Other);
        pb.PlaceOn(pos, yaw);
        return go;
    }

    void CopyHands(PlayerBody src)                                // 복사본의 Awake 는 움직이던 자세에서 재서 — 처음 자세에서 잰 값을 가져온다
    {
        foreach (var (a, b) in new[] { (R, src.R), (L, src.L) })
        {
            a.palm = b.palm; a.frame = b.frame; a.grip = b.grip; a.idxAxis = b.idxAxis; a.thAxis = b.thAxis;
            System.Array.Copy(b.bind, a.bind, 6);
        }
    }

    public void PlaceOn(Vector3 pos, float yaw)
    {
        transform.SetPositionAndRotation(Ground(pos), Quaternion.Euler(0f, yaw, 0f));
        yaw0 = yaw;
    }

    public void NextAction()
    {
        action = action == "idle" ? "mine" : action == "mine" ? "turn" : "idle";
        t = 0f;
        if (action != "turn") transform.rotation = Quaternion.Euler(0f, yaw0, 0f);
    }

    public static Vector3 Ground(Vector3 p)                     // 발밑 바닥 (플레이어 캡슐 · 방아쇠는 건너뛴다)
    {
        var hits = Physics.RaycastAll(p + Vector3.up * 1.5f, Vector3.down, 5f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore);
        var ground = hits.Where(h => !(h.collider is CharacterController)).OrderBy(h => h.distance).ToArray();
        return ground.Length > 0 ? ground[0].point : p;
    }

    public float SoleY() => transform.TransformPoint(0f, SoleLocal(), 0f).y;   // 검사: 몸 그물(장화 포함)의 가장 낮은 점 (Other 는 뿌리가 곧게 서 있다)

    float SoleLocal()                                             // 몸 그물의 가장 낮은 점 높이 (뿌리 기준)
    {
        var m = new Mesh();
        float y = WorldVerts(bodySkin, m).Min(v => transform.InverseTransformPoint(v).y);
        Destroy(m);
        return y;
    }

    // 뼈로 굽힌 그물 점의 세계 자리. 짝이 맞아야 한다(09-30 몸 ×1.119 에서 잼): BakeMesh(true) 는 크기를 뺀 점 → localToWorldMatrix,
    // BakeMesh(false) 는 크기가 든 점 → 자리 · 회전만. 옛 BakeMesh(true) + 자리 · 회전은 크기 1 에서만 맞았다(몸 꼭대기 1.669 = 참 1.868 ÷ 1.119, 줄 끝이 2.8 cm 떨어진 것처럼 잼)
    public static Vector3[] WorldVerts(SkinnedMeshRenderer s, Mesh m)
    {
        s.BakeMesh(m, true);
        var w = s.transform.localToWorldMatrix;
        return m.vertices.Select(v => w.MultiplyPoint3x4(v)).ToArray();
    }

    void Play(string s)
    {
        if (noKevin) s = "Bare";
        if (s == state || anim.runtimeAnimatorController == null) return;
        anim.CrossFadeInFixedTime(s, state == "" ? 0f : 0.15f);
        state = s;
    }

    // 재질: 판정 키 값을 새 재질 사본에 → 몸 · 팔(1인칭은 어둡게 한 사본). 옛 재질(Shift+6)은 몸만 — 소품은 늘 새 것
    void ApplyLook()
    {
        myLookVer = lookVer;
        if (skinRt == null) skinRt = new Material(skinAsset != null ? skinAsset : bodySkin.sharedMaterial) { name = "PlayerSkin_Rt" };
        skinRt.SetFloat("_DetailNormalMapScale", clothDetail);
        skinRt.SetFloat("_Smoothness", smoothMul);
        if (dirt.Length == 3) skinRt.SetTexture("_BaseMap", dirt[Mathf.Clamp(dirtLevel, 0, 2)]);
        if (noDetail) { skinRt.SetTexture("_DetailNormalMap", null); skinRt.DisableKeyword("_DETAIL_MULX2"); }
        if (clayRt == null && clay != null) { clayRt = new Material(clay) { name = "PlayerSkin_Clay_Rt" }; clay0 = clay.GetFloat("_Smoothness"); }
        if (clayRt != null) clayRt.SetFloat("_Smoothness", clay0 * smoothMul);
        var src = (clayLook || forceClay) && clayRt != null ? clayRt : skinRt;
        if (fpSkin != null) Destroy(fpSkin);
        fpSkin = new Material(src) { name = "PlayerSkin_FP" };
        Color c = src.GetColor("_BaseColor"), k = c * Tuning.PLAYER_FP_ARM_TINT;
        fpSkin.SetColor("_BaseColor", new Color(k.r, k.g, k.b, c.a));
        bodySkin.sharedMaterial = src;
        arms.sharedMaterial = mode == Mode.Self ? fpSkin : src;
    }

    void Param(string name, float v) { if (anim.runtimeAnimatorController != null) anim.SetFloat(name, v); }

    void Update()
    {
        float dt = Time.deltaTime;
        t += dt;
        if (myLookVer != lookVer) ApplyLook();
        if (transform.localScale.x != scale)
        {
            transform.localScale = Vector3.one * scale;
            if (ownPick != null) FitPick();
        }
        if (mode == Mode.Self) SelfUpdate(dt); else OtherUpdate(dt);
    }

    void SelfUpdate(float dt)
    {
        bool hasPick = pickaxe.hasPick, direct = pickaxe.Direct;
        float blend = dt / Tuning.PLAYER_HAND_BLEND_S;
        R.w = Mathf.MoveTowards(R.w, hasPick ? 1f : 0f, blend);
        L.w = Mathf.MoveTowards(L.w, twoHands && hasPick && pickaxe.Mining ? 1f : 0f, blend);
        bool toMine = direct && pickaxe.minePhase != "lower";
        wMine = Mathf.MoveTowards(wMine, toMine ? 1f : 0f, dt / (toMine ? Tuning.MINE_MOTION_BLEND_S : Tuning.MINE_LOWER_S));
        Play(direct ? "Mine" : "Idle");
        if (direct && pickaxe.motion != null) Param("MineT", pickaxe.ClipNow / pickaxe.motion.length);
        Param("IdleT", t / idleLen % 1f);

        // 몸 자리 (카메라 기준): 쉴 때 = 머리 뼈가 눈 + PLAYER_FP_OFFSET, 캘 때 = 동작 표 틀의 Kevin 몸 자리 (몸 크기 배)
        if (direct) { minePos = pickaxe.MotionFramePoint(-Tuning.PLAYER_MINE_EYE * scale); mineRot = pickaxe.MotionFrameRot; }
        Vector3 rest = -headBind * scale + new Vector3(Tuning.PLAYER_FP_OFFSET.x, Tuning.PLAYER_FP_OFFSET.y, fpForward);
        transform.localPosition = Vector3.Lerp(rest, minePos, wMine);
        transform.localRotation = Quaternion.Slerp(Quaternion.identity, mineRot, wMine);

        var rot = pickaxe.mesh.rotation;
        Aim(R, pickaxe.gripRear.position, rot, cam.TransformPoint(Tuning.PLAYER_REST_R));
        Aim(L, pickaxe.gripFront.position, rot, cam.TransformPoint(Tuning.PLAYER_REST_L));
        R.ik = L.ik = true;

        // 팔이 안 닿으면 몸을 민다 (안 그리는 몸 — 손은 곡괭이를 쥔다). 두 손을 번갈아 몇 번
        Vector3 shift = Vector3.zero;
        for (int it = 0; it < 4; it++)
            foreach (var h in new[] { R, L })
            {
                if (h.w <= 0f) continue;
                Vector3 d = (h == R ? pickaxe.gripRear.position : pickaxe.gripFront.position) - (transform.TransformPoint(h.shLocal) + shift);
                float over = d.magnitude - Tuning.PLAYER_ARM_REACH_M * scale;
                if (over > 0f) shift += d.normalized * over;
            }
        transform.position += shift;
    }

    void OtherUpdate(float dt)
    {
        Play(action == "mine" ? "Mine" : "Idle");
        Param("MineT", t / mineLen % 1f);
        Param("IdleT", t / idleLen % 1f);
        if (action == "turn") transform.rotation = Quaternion.Euler(0f, yaw0 + 360f * t / Tuning.PLAYER_TURN_S, 0f);
        R.w = 1f;                                                 // 오른손은 곡괭이를 쥐고 있다(손 자식) · 왼손은 동작 그대로 — 한 손 캐기
        R.ik = L.ik = false;
    }

    // 손목 목표: 쥐는 점이 손잡이에 오게 (손 방향은 쥘수록 곡괭이를 쥔 방향으로), 쥐지 않으면 rest(손목 자리)로
    void Aim(Hand h, Vector3 grip, Quaternion pickRot, Vector3 rest)
    {
        h.want = pickRot * Quaternion.Inverse(h.grip);
        Vector3 onGrip = grip - Quaternion.Slerp(h.animRot, h.want, h.w) * h.palm;
        h.wrist = Vector3.Lerp(rest, onGrip, h.w);
    }

    void OnAnimatorIK(int layer)
    {
        if (Still) anim.bodyPosition += transform.TransformVector(bodyFix);
        if (noIk) return;
        foreach (var (h, goal, hint, side) in new[] { (R, AvatarIKGoal.RightHand, AvatarIKHint.RightElbow, 1f), (L, AvatarIKGoal.LeftHand, AvatarIKHint.LeftElbow, -1f) })
        {
            float w = !h.ik ? 0f : mode == Mode.Self ? 1f : h.w;
            anim.SetIKPositionWeight(goal, w);
            anim.SetIKHintPositionWeight(hint, w);
            if (w <= 0f) continue;
            anim.SetIKPosition(goal, h.wrist);
            var e = Tuning.PLAYER_ELBOW;
            anim.SetIKHintPosition(hint, h.shoulder.position + transform.rotation * new Vector3(e.x * side, e.y, e.z));
        }
    }

    // 손 방향 · 주먹: 동작(+IK)이 끝난 자세 위에 쥐는 만큼
    void LateUpdate()
    {
        if (Still)                                                // 앞뒤 · 옆은 엉덩이를 처음 자리로, 높이는 장화 바닥을 뿌리(발밑)에 — 빈 자세는 무릎 · 발목이 굽어
        {                                                         // 엉덩이로 맞추면 5 cm 뜨고 발끝 뼈로 맞추면 발끝이 5 cm 묻혔다. 자세가 멈춰 있어 처음 몇 프레임만 잰다
            Vector3 h = transform.InverseTransformPoint(hips.position);
            bodyFix.x += hipsBind.x - h.x;
            bodyFix.z += hipsBind.z - h.z;
            if (++lateFrames is >= 2 and <= 4) bodyFix.y -= SoleLocal();
        }
        foreach (var h in new[] { R, L })
        {
            h.animRot = h.hand.rotation;
            if (!noIk && h.w > 0f && (h.ik || h == R && mode == Mode.Other))
            {
                if (h.ik) h.hand.rotation = Quaternion.Slerp(h.animRot, h.want, h.w);
                for (int i = 0; i < 6; i++)
                {
                    var ax = i < 3 ? h.idxAxis : h.thAxis;
                    var fist = h.bind[i] * Quaternion.AngleAxis(i < 3 ? Tuning.PLAYER_FIST_DEG : Tuning.PLAYER_THUMB_DEG, ax);
                    h.fingers[i].localRotation = Quaternion.Slerp(h.fingers[i].localRotation, fist, h.w);
                }
            }
            h.shLocal = transform.InverseTransformPoint(h.shoulder.position);
        }
    }
}
