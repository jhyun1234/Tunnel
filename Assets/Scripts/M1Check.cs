using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

// 배포물 검사. exe 를 -check 로 띄우면 돌고, 로그에 "CHECK PASS|FAIL 이름 값" 을 쓰고 종료 코드로 알린다.
// 입력은 가상 키보드·마우스 장치로 넣는다 — Player·Pickaxe 는 사람 장치와 같은 길(Keyboard.current / Mouse.current)로 읽는다.
// -only m1|mining|stalker|chase|retreat|throw|pick|tired|hud|sound 은 그 구간만 돈다 (고치는 중에는 바뀐 구간만, 커밋 전에는 전체).
// -sabotage floor|lamp|fog|thickfog|nodim|bury|onehit|spam|nomagnet|noassist|noviewmodel|picklamp|mute|deaf|bigears|ghost|blind|slowchase|nolose|noadapt|dimeyes|tank|noretreat|softretreat|stunlock|lurechase|nopickup|twopicks|flatsteps|quietfeet|rockflesh|nodull|steadyhands|everlasting|flatnod|nostagger|hudtext|noglow|ballpick|hudon 는 검사가 FAIL 을 내는지 확인하는 용도다.
// -sweep 은 검사 대신 가까운 면 감광 값을 바꿔 가며 갱도·벽 앞 화면 값을 "SWEEP" 줄로 남긴다.
public class M1Check : MonoBehaviour
{
    public Player player;
    public Headlamp lamp;
    public Volume volume;
    public Transform pieces;
    public Pickaxe pickaxe;
    public Stalker stalker;

    const float MinFps = 60f;
    // Godot 골든 캡처 play_09_lamp.png(직선 갱도, 램프 켬) 화면 평균 밝기. 같은 계산(sRGB 휘도 평균)으로 잰 참고값
    const float GodotLum = 0.063f;
    const float BurntLum = 0.85f;                 // 이 밝기 위 픽셀 = 하얗게 탄 픽셀
    // 벽 앞 화면에서 탄 픽셀 비율 상한. 실측(09-14 -sweep, 램프 75.2): 감광 없음 45 % · ref 2 = 9.4 % · pow 1.0 = 7.0 % · ref 3 = 2.8 % · ref 4 pow 1.4 = 1.3 %
    const float MaxBurntNearWall = 0.05f;
    const float MaxBurntPick = 0.05f;             // 곡괭이 화면 영역의 탄 픽셀 비율 상한
    // 램프 안 괴물 캡슐 영역의 평균 밝기 하한 (사용자 09-15 "절대 보이지 않는다"). 갱도 바탕 0.05. 램프 사거리 14 m 라 13 m 는 0.01 이 맞다.
    // 실측(09-15): 검정 재질(0.12) 3 m 0.159 · 7 m 0.055 = 바탕과 같음 → 회갈색(0.40) 3 m 0.303 · 7 m 0.127. 안 그리면(ghost) 0.077 · 0.009
    static readonly Vector3 NearWallPos = new Vector3(2.75f, 0.1f, 15.75f);   // 오른쪽 벽에 몸이 닿는 자리, 기둥 사이
    static readonly Vector3 MidTunnel = new Vector3(0f, 1.9f, 17.5f);
    readonly List<string> fails = new List<string>();
    string outDir;
    string only = "";

    void Start()
    {
        string[] args = Environment.GetCommandLineArgs();
        bool sweep = Array.IndexOf(args, "-sweep") >= 0;
        if (!sweep && Array.IndexOf(args, "-check") < 0)
        {
            enabled = false;
            return;
        }
        int o = Array.IndexOf(args, "-only");
        if (o >= 0 && o + 1 < args.Length) only = args[o + 1];
        int s = Array.IndexOf(args, "-sabotage");
        string sabotage = s >= 0 && s + 1 < args.Length ? args[s + 1] : "";
        outDir = Path.Combine(Path.GetDirectoryName(Application.dataPath), "check");
        Directory.CreateDirectory(outDir);
        Application.runInBackground = true;     // 창이 포커스를 잃어도 멈추지 않게
        InputSystem.settings.backgroundBehavior = InputSettings.BackgroundBehavior.IgnoreFocus;   // 포커스를 잃어도 가상 장치 입력을 막지 않게
        QualitySettings.vSyncCount = 0;
        Application.targetFrameRate = -1;
        var hud = GetComponent<DevHud>();
        if (hud != null) hud.enabled = false;   // 글자가 밝기·구조 값에 섞이지 않게

        volume.profile.TryGet(out VolumetricFogVolumeComponent fog);
        if (sabotage == "floor")
            foreach (var c in pieces.GetComponentsInChildren<MeshCollider>())
                if (c.name.Contains("floor")) c.enabled = false;
        if (sabotage == "lamp")
            lamp.GetComponent<Light>().enabled = false;
        if (sabotage == "fog")
            fog.density.value = 0f;
        if (sabotage == "thickfog")
            fog.density.value = 0.012f;          // Godot 값 그대로 — 갱도 끝이 흰 막이 되던 밀도
        if (sabotage == "nodim")
            lamp.nearPow = 0f;                   // 가까운 면 감광 끔 — 벽 앞이 하얗게 타던 상태
        if (sabotage == "bury")                  // 포켓을 벽 속으로 0.4 m — 묻힌 포켓
            foreach (var pk in FindObjectsByType<OrePocket>(FindObjectsSortMode.None))
                pk.transform.position -= pk.outDir * 0.4f;
        if (sabotage == "onehit")
            pickaxe.damage = Tuning.POCKET_HEALTH;
        if (sabotage == "spam")                  // 간격 없이 빠르게 휘두른다
        {
            pickaxe.cooldownTime = 0f;
            pickaxe.swingTimeMul = 0.2f;
        }
        if (sabotage == "nomagnet")
            Ore.MagnetRange = 0f;
        if (sabotage == "noassist")
            pickaxe.aimRadius = 0f;
        if (sabotage == "noviewmodel")           // 곡괭이를 기본 레이어로 — 벽 속으로 파고들던 상태
            foreach (var t in pickaxe.GetComponentsInChildren<Transform>(true))
                t.gameObject.layer = 0;
        if (sabotage == "picklamp")              // 헤드램프가 곡괭이도 비춘다 — 하얗게 뜨던 상태
            lamp.GetComponent<Light>().GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer | Pickaxe.ViewModelRenderingLayer;
        if (sabotage == "mute")
            MiningFx.I.hitClips = new AudioClip[0];
        if (sabotage == "deaf")                 // 귀 ×0.4 = 곡괭이 소음 10 m — 20 m 에서 못 듣는다
            stalker.earMul = 0.4f;
        if (sabotage == "bigears")              // 귀 ×2 = 50 m — 30 m 밖에서도 온다
            stalker.earMul = 2f;
        if (sabotage == "ghost")                // 괴물 몸을 안 그린다 — 보임 검사가 잡는지
            foreach (var r in stalker.GetComponentsInChildren<Renderer>()) r.enabled = false;
        if (sabotage == "capsule")              // 3D-①: 모델 없음 (옛 캡슐 자리표시 상태) — 모델 검사가 잡는지
            stalker.transform.Find("Body/Model")?.gameObject.SetActive(false);
        if (sabotage == "acne")                 // 3D-②: 그림자 편차를 URP 기본으로 — 살 얼룩 검사가 잡는지
        {
            lamp.shadowDepthBias = 0.1f; lamp.shadowNormalBias = 0.5f; lamp.ApplyShadowBias();
        }
        if (sabotage == "noshadow")             // 3D-① 진단: 모델이 그림자를 안 만든다 — 2 m 살의 지직거림이 자기 그림자 얼룩(shadow acne)인지
            foreach (var r in stalker.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = ShadowCastingMode.Off;
        if (sabotage == "dimlamp")              // 3D-① 진단: 램프 1/4 — 지직거림이 과다 노출인지
            lamp.energy *= 0.25f;
        if (sabotage == "flatskin")             // 3D-①: 살 노멀맵 뺌 — 노멀 검사·그늘 값이 잡는지
            foreach (var r in stalker.GetComponentsInChildren<Renderer>())
                foreach (var m in r.materials)
                    if (m.name.StartsWith("살")) { m.SetTexture("normalTexture", null); m.DisableKeyword("_NORMALMAP"); }
        if (sabotage == "blind")                // 눈 0 m — 램프를 봐도 모른다
            stalker.eyeM = 0f;
        if (sabotage == "slowchase")            // 추격 3.0 m/s — 걷는 사람도 못 잡는다
            stalker.chaseSpeed = 3f;
        if (sabotage == "nolose")               // 못 봐도 안 놓는다
            stalker.loseS = 99f;
        if (sabotage == "tank")                 // 곡괭이가 안 먹힌다
            stalker.dmgMul = 0f;
        if (sabotage == "noretreat")            // 철수선 없음 — 체력이 0 까지 간다
            stalker.retreatHp = -1f;
        if (sabotage == "softretreat")          // 철수 중에도 맞는다(깎이고 멈춘다) — 연타로 벽에 못 가던 상태
            stalker.retreatArmor = false;
        if (sabotage == "stunlock")             // 스턴 중에도 맞는다 — 연타로 1.5 s 안에 세 대
            stalker.stunImmune = false;
        if (sabotage == "lurechase")            // 추격 중에도 던진 곡괭이 소리에 돌아선다 — 도망이 너무 쉬운 상태
            stalker.lureInChase = true;
        if (sabotage == "nopickup")             // 줍기 거리 0 — E 가 안 먹는다
            pickaxe.thrown.reach = 0f;
        if (sabotage == "twopicks")             // 던져도 손에 남는다 — 곡괭이가 둘인 상태
            pickaxe.oneOnly = false;
        if (sabotage == "flatsteps")            // 발소리 음량이 자세 무관 같다 — 사다리가 없는 상태
            NoiseSound.I.flat = true;
        if (sabotage == "quietfeet")            // 발소리 반경 0 — 괴물이 발소리를 못 듣는(옛) 상태
            player.stepNoiseMul = 0f;
        if (sabotage == "rockflesh")            // 괴물을 쳐도 광물 소리 — 구분이 안 되던(옛) 상태
            NoiseSound.I.fleshClips = MiningFx.I.hitClips;
        if (sabotage == "nodull")               // 곡괭이가 안 닳는다 (UI-1a 전 상태)
            pickaxe.dulls = false;
        if (sabotage == "steadyhands")          // 15 이하에서도 손이 안 떨린다
            pickaxe.shaky = false;
        if (sabotage == "everlasting")          // 0 이어도 안 부서지고 캐진다
            pickaxe.breaks = false;
        if (sabotage == "flatnod")              // 곧 단계에도 램프 끄덕임 폭 그대로
            lamp.soonNod = false;
        if (sabotage == "nostagger")            // 탈진해도 자세 없음 (UI-1b 전 상태)
            player.stagger = false;
        if (sabotage == "hudtext")              // 갱도 화면에 "철 N" 글자 (UI-1c 전 상태)
            FindFirstObjectByType<MiningHud>().oreText = true;
        if (sabotage == "noglow")               // 던진 곡괭이 머리가 안 빛난다
            pickaxe.thrown.glows = false;
        if (sabotage == "hudon")                // DevHud 가 켜진 채 시작 (UI-1d 전 상태)
            hud.startVisible = true;
        if (sabotage == "ballpick")             // 충돌체가 공 하나(옛) — 머리가 바닥을 뚫던 상태
        {
            foreach (var col in pickaxe.thrown.GetComponentsInChildren<Collider>()) col.enabled = false;
            pickaxe.thrown.gameObject.AddComponent<SphereCollider>().radius = 0.15f;
        }
        if (sabotage == "noadapt")              // 눈 적응 없음 — 램프 끄면 검은 화면 그대로
            lamp.darkAdaptAmbient = Tuning.AMBIENT_ENERGY;
        if (sabotage == "bigrelief")            // 3D-②b 진단: 요철 세기 4배 — 7/8 키(normalTexture_scale)가 화면에 먹는지 (사용자 09-18 "변하는지 확인이 안 된다")
        {
            var lk4 = stalker.GetComponentInChildren<StalkerLook>(); lk4.normalScale = 4f; lk4.Apply();
        }
        if (sabotage == "dimeyes")              // 괴물 눈 발광 끔 (3D-②b: 눈구멍 발광 0)
        {
            var lk = stalker.GetComponentInChildren<StalkerLook>(); lk.eyeEmission = 0f; lk.Apply();
        }
        Debug.Log($"CHECK start sabotage='{sabotage}' only='{only}' sweep={sweep} screen {Screen.width}x{Screen.height}");
        StartCoroutine(sweep ? (Array.IndexOf(args, "-bias") >= 0 ? BiasSweep() : Sweep()) : Run(fog));
    }

    IEnumerator Run(VolumetricFogVolumeComponent fog)
    {
        var cc = player.GetComponent<CharacterController>();
        stalker.enabled = false;                 // 괴물 무관 구간은 괴물을 끈다 (DevHud 0 키와 같다) — 켜 두면 램프 빛을 보고 와서 잡는다
        yield return new WaitForSeconds(1.5f);   // 바닥에 내려앉는다
        if (only == "" || only == "m1")
            yield return M1(cc, fog);
        if (only == "" || only == "mining")
            yield return Mining(cc);
        stalker.enabled = true;
        if (only == "" || only == "monster")
            yield return MonsterStage(cc);
        if (only == "" || only == "stalker")
            yield return StalkerStage(cc);
        if (only == "" || only == "chase")
            yield return ChaseStage(cc);
        if (only == "" || only == "retreat")
            yield return RetreatStage(cc);
        if (only == "" || only == "throw")
            yield return ThrowStage(cc);
        if (only == "" || only == "pick")
            yield return PickStage(cc);
        if (only == "" || only == "tired")
            yield return TiredStage(cc);
        if (only == "" || only == "hud")
            yield return HudStage(cc);
        if (only == "" || only == "sound")
            yield return SoundStage(cc);
        Finish();
    }

    // UI-1a: 곡괭이 내구도. 닿은 타격 −1 · 던지기 −5 · PICK_SHAKY_BELOW 이하 떨림 · 0 이면 손에서 조각나 떨어졌다 사라지고 빈손
    IEnumerator PickStage(CharacterController cc)
    {
        var st = stalker;
        var mouse = InputSystem.AddDevice<Mouse>("PickMouse");
        var kb = InputSystem.AddDevice<Keyboard>("PickKeyboard");
        var thrown = pickaxe.thrown;
        var fx = MiningFx.I;
        float t;
        st.enabled = false;
        lamp.lampOn = true;
        player.frozen = false;
        if (!pickaxe.hasPick) pickaxe.Return();
        pickaxe.durability = Tuning.PICK_DURABILITY_MAX;
        pickaxe.hitsLanded = 0;
        float dmg0 = pickaxe.damage;
        pickaxe.damage = 0f;                     // 포켓이 안 빠지게 — 한 포켓을 여러 번 친다 (닳음은 닿은 타격 수로 센다)
        var pockets = new List<OrePocket>(FindObjectsByType<OrePocket>(FindObjectsSortMode.None));
        pockets.Sort((a, b) => (a.transform.position - MidTunnel).sqrMagnitude.CompareTo((b.transform.position - MidTunnel).sqrMagnitude));
        OrePocket pk = pockets.Find(x => !x.Breaking) ?? pockets[0];

        // ① 포켓을 여러 번 치면 닿은 타격마다 PICK_WEAR_HIT
        StandAt(cc, pk);
        yield return null;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(Tuning.MINE_COOLDOWN * 10f + 0.3f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
        yield return new WaitForSeconds(Tuning.MINE_COOLDOWN);
        int hits = pickaxe.hitsLanded;
        Check("pick_wears_per_landed_hit", hits >= 8 && pickaxe.hasPick && pickaxe.durability == Tuning.PICK_DURABILITY_MAX - hits * Tuning.PICK_WEAR_HIT,
            $"{hits} landed hits, durability {Tuning.PICK_DURABILITY_MAX:0} → {pickaxe.durability:0} (expect {Tuning.PICK_DURABILITY_MAX - hits * Tuning.PICK_WEAR_HIT:0})");

        // ② 한 번 던지고 주우면 PICK_WEAR_THROW
        float d0 = pickaxe.durability;
        Vector3 P = new Vector3(0f, 0.1f, 6f);
        Teleport(cc, P, 0f);
        yield return null;
        yield return RightClick(mouse);
        t = 0f;
        while (!thrown.Frozen && t < Tuning.THROW_STUCK_S + 4f) { t += Time.deltaTime; yield return null; }
        Vector3 land = thrown.transform.position;
        Teleport(cc, new Vector3(land.x, 0.1f, land.z - 2f), 0f);
        yield return null;
        yield return PressKey(kb, Key.E);
        Check("pick_wears_on_throw", pickaxe.hasPick && pickaxe.durability == d0 - Tuning.PICK_WEAR_THROW,
            $"durability {d0:0} → {pickaxe.durability:0} (expect {d0 - Tuning.PICK_WEAR_THROW:0}), hasPick {pickaxe.hasPick}");

        // ③ 40 이면 닿은 타격 뒤 뷰모델이 제자리, PICK_SHAKY_BELOW 이면 0.02 m 이상 흔들린다 (서 있을 때, 머리는 안 흔든다)
        float devAt40 = 0f, devAt15 = 0f;
        int hitsAt40 = 0, hitsAt15 = 0;
        foreach (float d in new[] { 40f, Tuning.PICK_SHAKY_BELOW })
        {
            pickaxe.durability = d;
            pickaxe.hitsLanded = 0;
            StandAt(cc, pk);
            yield return new WaitForSeconds(0.3f);               // 걷기 흔들림이 멎게
            float dev = 0f;
            InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
            for (t = 0f; t < 1.0f; t += Time.deltaTime)
            {
                dev = Mathf.Max(dev, (pickaxe.transform.localPosition - Tuning.PICK_POS).magnitude);
                yield return null;
            }
            InputSystem.QueueStateEvent(mouse, new MouseState());
            yield return new WaitForSeconds(Tuning.MINE_COOLDOWN);
            if (d == 40f) { devAt40 = dev; hitsAt40 = pickaxe.hitsLanded; } else { devAt15 = dev; hitsAt15 = pickaxe.hitsLanded; }
        }
        Check("pick_shakes_below_15", hitsAt40 >= 1 && hitsAt15 >= 1 && devAt40 < 0.005f && devAt15 >= 0.02f && player.gait <= 0f,
            $"viewmodel max offset at 40: {devAt40:F3} m ({hitsAt40} hits) · at {Tuning.PICK_SHAKY_BELOW:0}: {devAt15:F3} m ({hitsAt15} hits), PICK_SHAKE_AMOUNT {Tuning.PICK_SHAKE_AMOUNT}, gait {player.gait:F2}");

        // ④ 1 에서 한 대 → 0: 손이 비고(뷰모델 꺼짐·던진 곡괭이 없음) 조각 PICK_BREAK_PIECES 가 생겼다가 사라진다
        pickaxe.durability = 1f;
        pickaxe.hitsLanded = 0;
        StandAt(cc, pk);
        yield return null;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        t = 0f;
        while (pickaxe.hitsLanded < 1 && t < 1.5f) { t += Time.deltaTime; yield return null; }
        InputSystem.QueueStateEvent(mouse, new MouseState());
        yield return null;
        int pieces = fx.PiecesAlive;
        bool emptyHand = !pickaxe.hasPick && !pickaxe.mesh.gameObject.activeSelf && !thrown.gameObject.activeSelf && pickaxe.Broken;
        Check("pick_breaks_at_zero", pickaxe.hitsLanded == 1 && pickaxe.durability == 0f && emptyHand && pieces == Tuning.PICK_BREAK_PIECES,
            $"hits {pickaxe.hitsLanded}, durability {pickaxe.durability:0}, hasPick {pickaxe.hasPick}, viewmodel {pickaxe.mesh.gameObject.activeSelf}, thrown active {thrown.gameObject.activeSelf}, pieces {pieces} (expect {Tuning.PICK_BREAK_PIECES})");
        for (int i = 0; i < 4; i++)                                         // 조각이 손에서 바닥으로 가는 사이 (0.15 s 마다) — 사람이 볼 캡처
        {
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(Path.Combine(outDir, $"15_pick_broken_{i * 0.15f:0.00}s.png"));
            yield return new WaitForSeconds(0.15f);
        }
        t = 0.6f;
        while (fx.PiecesAlive > 0 && t < Tuning.PICK_BREAK_LIFE + Tuning.CHUNK_FADE + 1.5f) { t += Time.deltaTime; yield return null; }
        Check("pick_pieces_vanish", fx.PiecesAlive == 0, $"pieces {fx.PiecesAlive} after {t:F1} s (PICK_BREAK_LIFE {Tuning.PICK_BREAK_LIFE} + fade {Tuning.CHUNK_FADE})");

        // ⑤ 빈손: 포켓 앞 좌클릭 → 포켓 체력 그대로·소음 0, 우클릭 → 던진 곡괭이 안 생김
        pickaxe.damage = dmg0;
        float hp0 = pk.health;
        int noise0 = NoiseBus.Total, hits0 = pickaxe.hitsLanded;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(0.6f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
        yield return null;
        yield return RightClick(mouse);
        Check("broken_pick_cannot_mine_or_throw", pk.health == hp0 && NoiseBus.Total == noise0 && pickaxe.hitsLanded == hits0 && !pickaxe.hasPick && !thrown.gameObject.activeSelf,
            $"pocket hp {hp0:0} → {pk.health:0}, noises +{NoiseBus.Total - noise0}, hits +{pickaxe.hitsLanded - hits0}, hasPick {pickaxe.hasPick}, thrown active {thrown.gameObject.activeSelf}");

        // ⑥ 되살리기 — DevHud 4 키와 같은 길 (상점이 생기기 전 판정용)
        pickaxe.Adjust(Tuning.PICK_DURABILITY_MAX);
        yield return null;
        Check("pick_restored_by_devhud_key", pickaxe.hasPick && pickaxe.mesh.gameObject.activeSelf && pickaxe.durability == Tuning.PICK_DURABILITY_MAX,
            $"hasPick {pickaxe.hasPick}, viewmodel {pickaxe.mesh.gameObject.activeSelf}, durability {pickaxe.durability:0}");
        st.enabled = true;
    }

    // UI-1b: 지쳤을 때 자세. 걸으면 램프가 LAMP_BOB_DEG 끄덕이고, 스태미나 ≤ STAMINA_SOON 이면 3배 + 작은 숨 들썩임, 탈진하면 눈 EXHAUST_EYE·시야 EXHAUST_LOOK_DOWN_DEG 아래·
    // 흐림·좌우 ±EXHAUST_YAW_LIMIT_DEG 만·숨 들썩임·램프 세기 박동
    IEnumerator TiredStage(CharacterController cc)
    {
        var st = stalker;
        var kb = InputSystem.AddDevice<Keyboard>("TiredKeyboard");
        float t;
        st.enabled = false;
        lamp.lampOn = true;
        player.frozen = false;
        player.exhausted = false;
        Vector3 P = new Vector3(0f, 0.1f, 6f);

        // ① 100 에서 걸으면 램프가 카메라보다 ±LAMP_BOB_DEG 안에서 끄덕인다(최대 편차 = 폭 ±20 %), 서면 0
        float amp100 = 0f, amp30 = 0f;
        foreach (float s0 in new[] { Tuning.STAMINA_MAX, 30f })          // 30: 걸으면 10/s 차서 1.3 s 뒤 43, 아직 곧 단계
        {
            player.stamina = s0;
            Teleport(cc, P, 0f);
            yield return new WaitForSeconds(0.3f);
            float amp = 0f;
            InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
            yield return new WaitForSeconds(0.3f);                           // 가속
            Quaternion camPrev = lamp.cam.rotation;
            for (t = 0f; t < 1f; t += Time.deltaTime)
            {
                if (Quaternion.Angle(camPrev, lamp.cam.rotation) < 0.01f)          // 시점이 돈 프레임은 뺀다 — 램프 늦게 따라오기(LAMP_FOLLOW_TIME)가 섞인다(사람 마우스)
                    amp = Mathf.Max(amp, Mathf.Abs(LampPitch()));
                camPrev = lamp.cam.rotation;
                yield return null;
            }
            InputSystem.QueueStateEvent(kb, new KeyboardState());
            if (s0 == Tuning.STAMINA_MAX) amp100 = amp; else amp30 = amp;
        }
        yield return new WaitForSeconds(0.5f);
        float still = Mathf.Abs(LampPitch());
        // 곧 단계에 서 있으면 작은 숨 들썩임(BREATH_SOON_MUL), 100 이면 없음
        float breathSoon = 0f, breathFull = 0f;
        foreach (float s0 in new[] { 30f, Tuning.STAMINA_MAX })
        {
            player.stamina = s0;
            yield return new WaitForSeconds(Tuning.EXHAUST_TIME + 0.1f);
            float lo = float.MaxValue, hi = float.MinValue;
            for (t = 0f; t < 1f; t += Time.deltaTime)
            {
                lo = Mathf.Min(lo, player.head.localPosition.y);
                hi = Mathf.Max(hi, player.head.localPosition.y);
                player.stamina = s0;                                       // 서 있으면 20/s 차서 곧 단계를 벗어난다
                yield return null;
            }
            if (s0 == 30f) breathSoon = hi - lo; else breathFull = hi - lo;
        }
        float expectSoon = Tuning.EXHAUST_BREATH_M * 2f * Tuning.BREATH_SOON_MUL;
        Check("breath_bounce_small_when_tired", breathSoon >= expectSoon * 0.8f && breathSoon <= expectSoon * 1.2f && breathFull < 0.002f,
            $"head up-down standing at 30: {breathSoon * 100f:F2} cm (expect {expectSoon * 100f:F2} ±20 %), at 100: {breathFull * 100f:F2} cm");
        float expect1 = lamp.bobDeg, expect3 = lamp.bobDeg * Tuning.LAMP_BOB_SOON_MUL;
        Check("lamp_nods_when_walking", amp100 >= expect1 * 0.8f && amp100 <= expect1 * 1.2f && still < 0.05f,
            $"lamp pitch vs camera walking at 100: max {amp100:F3}° (LAMP_BOB_DEG {expect1:F3} ±20 %), standing {still:F3}°");
        // ② 곧 단계(≤ STAMINA_SOON)면 3배
        Check("lamp_nod_triples_when_tired", amp30 >= expect3 * 0.8f && amp30 <= expect3 * 1.2f,
            $"walking at 30: max {amp30:F3}° (expect {expect3:F3} ±20 %, x{Tuning.LAMP_BOB_SOON_MUL} of {amp100:F3})");

        // ③ 0 에서 Shift+W 를 계속 누르면 탈진 — 0.5 s 안에 눈 EXHAUST_EYE, 시야 EXHAUST_LOOK_DOWN_DEG 아래(±숨 끄덕임), 1 s 동안 머리가 EXHAUST_BREATH_M 로 오르내림, 0.3 m 안 움직임, 램프 세기 박동.
        //    갱도 가운데(z≈16, 북쪽 21 m 남음)에서 탈진하게 2 s 달린 뒤 스태미나를 1 로 — 5 s 를 다 달리면 끝 벽 앞이라 화면이 벽으로 찬다(09-16)
        player.stamina = Tuning.STAMINA_MAX;
        Teleport(cc, new Vector3(0f, 0.1f, 2f), 0f);
        yield return null;
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W, Key.LeftShift));
        yield return new WaitForSeconds(2f);
        player.stamina = 1f;
        t = 0f;
        while (!player.exhausted && t < 2f) { t += Time.deltaTime; yield return null; }
        float tEx = t;
        yield return new WaitForSeconds(0.5f);
        Vector3 pe = player.transform.position;
        float downEx = CameraPitch(), yMin = float.MaxValue, yMax = float.MinValue, eMin = float.MaxValue, eMax = float.MinValue, ePrev = lamp.pulseEnergy;
        int beats = 0;
        for (t = 0f; t < 1.3f; t += Time.deltaTime)                      // 숨 한 번 0.7 s 를 넘게 재서 위아래를 다 본다. 램프는 박동 0.5 s 라 2~3번 뛴다(창의 시작 위상에 따라)
        {
            yMin = Mathf.Min(yMin, player.head.localPosition.y);
            yMax = Mathf.Max(yMax, player.head.localPosition.y);
            eMin = Mathf.Min(eMin, lamp.pulseEnergy);
            eMax = Mathf.Max(eMax, lamp.pulseEnergy);
            if (lamp.pulseEnergy > ePrev + 5f) beats++;                    // 박동 = 한 프레임에 확 뛰는 순간
            ePrev = lamp.pulseEnergy;
            yield return null;
        }
        float eyeEx = (yMin + yMax) * 0.5f, breathEx = yMax - yMin;
        float movedEx = Flat(player.transform.position - pe);
        // 시점: 좌우는 탈진 시작 방향에서 ±EXHAUST_YAW_LIMIT_DEG 까지만, 위아래는 안 움직인다 (Player.Look — 마우스와 같은 길)
        float yaw0 = player.transform.eulerAngles.y, pitch0 = CameraPitch();
        float px = 1f / (Tuning.MOUSE_SENSITIVITY * Mathf.Rad2Deg);      // 1° 에 해당하는 마우스 픽셀
        player.Look(new Vector2(0f, 126f * px));                          // 위로 126° 요청 — 잠김 (360° 를 넘기면 각이 감겨 못 잰다)
        yield return null;
        float pitchAfter = CameraPitch();
        player.Look(new Vector2(150f * px, 0f));
        float yawR = Mathf.DeltaAngle(yaw0, player.transform.eulerAngles.y);
        player.Look(new Vector2(-270f * px, 0f));
        float yawL = Mathf.DeltaAngle(yaw0, player.transform.eulerAngles.y);
        player.Look(new Vector2(120f * px, 0f));                          // 정면으로 (−120 + 120)
        Check("exhausted_posture", player.exhausted && tEx < 1f && Mathf.Abs(eyeEx - Tuning.EXHAUST_EYE) < 0.05f && Mathf.Abs(downEx - Tuning.EXHAUST_LOOK_DOWN_DEG) <= Tuning.EXHAUST_BREATH_DEG + 0.5f && breathEx >= Tuning.EXHAUST_BREATH_M * 2f * 0.8f && movedEx < 0.3f,
            $"exhausted {player.exhausted} {tEx:F2} s after stamina 1 (z {player.transform.position.z:F1}), +0.5 s: eye {eyeEx:F2} m (EXHAUST_EYE {Tuning.EXHAUST_EYE}), camera {downEx:F1}° down (EXHAUST_LOOK_DOWN_DEG {Tuning.EXHAUST_LOOK_DOWN_DEG} ±{Tuning.EXHAUST_BREATH_DEG}), head up-down {breathEx * 100f:F1} cm in 1.3 s (EXHAUST_BREATH_M ×2 = {Tuning.EXHAUST_BREATH_M * 200f:F0} cm), moved {movedEx:F2} m in 1.3 s");
        Check("exhausted_look_limits", Mathf.Abs(yawR - Tuning.EXHAUST_YAW_LIMIT_DEG) < 1f && Mathf.Abs(yawL + Tuning.EXHAUST_YAW_LIMIT_DEG) < 1f && Mathf.Abs(pitchAfter - pitch0) <= Tuning.EXHAUST_BREATH_DEG * 2f + 0.5f && Mathf.Abs(Camera.main.fieldOfView - Tuning.CAMERA_FOV) < 0.5f,
            $"look right 150° → yaw {yawR:F1}°, left → {yawL:F1}° (limit ±{Tuning.EXHAUST_YAW_LIMIT_DEG}), look up 126° → camera pitch {pitch0:F1} → {pitchAfter:F1}° (locked), fov {Camera.main.fieldOfView:F0}° (unchanged)");
        Check("exhausted_lamp_pulses", eMin >= Tuning.LAMP_EXHAUST_MIN - 0.5f && eMin <= Tuning.LAMP_EXHAUST_MIN + 2f && eMax >= Tuning.LAMP_EXHAUST_MAX - 2f && eMax <= Tuning.LAMP_EXHAUST_MAX + 0.5f && beats >= 2 && beats <= 3,
            $"lamp energy over 1 s: {eMin:F1} ~ {eMax:F1} (LAMP_EXHAUST_MIN {Tuning.LAMP_EXHAUST_MIN} ~ MAX {Tuning.LAMP_EXHAUST_MAX}, normal {lamp.energy}), {beats} beats in 1.3 s (EXHAUST_PULSE_S {Tuning.EXHAUST_PULSE_S} → 2~3)");
        // 바닥을 비춘다: 화면 아래 절반이 밝아지고 위 절반은 어두워진다 — 같은 자리·같은 방향의 회복 뒤 화면과 비교
        Vector3 botEx = default, topEx = default, botOk = default, topOk = default;
        Rect bottom = new Rect(0f, 0f, Screen.width, Screen.height * 0.5f), top = new Rect(0f, Screen.height * 0.5f, Screen.width, Screen.height * 0.5f);
        // 램프가 0.5 s 박동이라 캡처 사이를 1.0 s(= Capture 의 0.6 + 0.4)로 맞춰 셋을 같은 위상에서 찍는다
        yield return Capture("17_exhausted", v => botEx = v, bottom);
        yield return new WaitForSeconds(1f - 0.6f);
        yield return Capture("17_exhausted_top", v => topEx = v, top);
        // 흐림: 같은 탈진 화면에서 흐림만 끄면 구조(밝기 기울기)가 살아난다
        Vector3 sharp = default;
        player.blurMul = 0f;
        yield return new WaitForSeconds(1f - 0.6f);
        yield return Capture("17_exhausted_noblur", v => sharp = v, bottom);
        player.blurMul = 1f;
        float gBlur = botEx.y / Mathf.Max(botEx.x, 1e-6f), gSharp = sharp.y / Mathf.Max(sharp.x, 1e-6f);   // 밝기로 나눈다 — 램프 박동으로 두 캡처의 밝기가 다르다
        Check("exhausted_blur", gBlur < gSharp * 0.8f, $"bottom-half gradient/lum blurred {gBlur:F1} vs blur off {gSharp:F1} ({gBlur / Mathf.Max(gSharp, 1e-6f) * 100f:F0} %, need < 80 %; raw {botEx.y:F2}@{botEx.x:F3} vs {sharp.y:F2}@{sharp.x:F3})");

        // ④ 100 이 차면 풀린다 — 0.5 s 안에 눈 EYE_HEIGHT, 램프 각 0
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        t = 0f;
        while (player.exhausted && t < 6f) { t += Time.deltaTime; yield return null; }
        float tBack = t;
        yield return new WaitForSeconds(0.5f);
        float eyeBack = player.head.localPosition.y, pitchBack = CameraPitch();
        yield return Capture("18_recovered", v => botOk = v, bottom);
        yield return Capture("18_recovered_top", v => topOk = v, top);
        // 램프가 탈진 중엔 어두워지므로(15.8~38.5) 절대 밝기가 아니라 아래/위 몫으로 본다: 빛이 바닥으로 몰린다
        float shareEx = botEx.x / Mathf.Max(botEx.x + topEx.x, 1e-6f), shareOk = botOk.x / Mathf.Max(botOk.x + topOk.x, 1e-6f);
        Check("exhausted_looks_at_floor", shareEx > 0.75f && shareEx > shareOk + 0.15f,
            $"bottom half share of light exhausted {shareEx * 100f:F0} % (bottom {botEx.x:F4} top {topEx.x:F4}) vs recovered {shareOk * 100f:F0} % ({botOk.x:F4} / {topOk.x:F4})");
        float yawFree0 = player.transform.eulerAngles.y;
        player.Look(new Vector2(150f * px, 0f));
        float yawFree = Mathf.Abs(Mathf.DeltaAngle(yawFree0, player.transform.eulerAngles.y));
        player.Look(new Vector2(-150f * px, 0f));
        Check("exhaustion_recovers", !player.exhausted && tBack < 6f && player.stamina >= Tuning.STAMINA_MAX - 0.5f && Mathf.Abs(eyeBack - Tuning.EYE_HEIGHT) < 0.05f && Mathf.Abs(pitchBack) < 0.5f && !player.BlurOn && Mathf.Abs(lamp.pulseEnergy - lamp.energy) < 0.01f && yawFree > Tuning.EXHAUST_YAW_LIMIT_DEG + 5f,
            $"recovered after {tBack:F1} s (stamina {player.stamina:0}), +0.5 s: eye {eyeBack:F2} m, camera {pitchBack:F2}°, blur {player.BlurOn}, lamp {lamp.pulseEnergy:F1} (normal {lamp.energy}), look right 150° → {yawFree:F0}° (free)");
        Teleport(cc, P, 0f);
        st.enabled = true;
    }

    float LampPitch() => Vector3.SignedAngle(lamp.cam.forward, lamp.transform.forward, lamp.cam.right);   // 도, + 면 램프가 카메라보다 아래
    float CameraPitch() => Vector3.SignedAngle(player.transform.forward, lamp.cam.forward, player.transform.right);   // 도, + 면 시야가 몸보다 아래

    // UI-1c: 갱도 화면 글자 0. 소음 원은 DevHud 켰을 때만. 던진 곡괭이는 reach 안에서 머리가 빛난다
    IEnumerator HudStage(CharacterController cc)
    {
        var st = stalker;
        var mouse = InputSystem.AddDevice<Mouse>("HudMouse");
        var kb = InputSystem.AddDevice<Keyboard>("HudKeyboard");
        var thrown = pickaxe.thrown;
        var hud = GetComponent<DevHud>();
        float t;
        st.enabled = false;
        lamp.lampOn = true;
        player.frozen = false;
        if (!pickaxe.hasPick) pickaxe.Return();
        Vector3 P = new Vector3(0f, 0.1f, 6f);

        // ① DevHud 꺼진 채: 소음(포켓 타격)을 내고 던져 빈손이어도 플레이어 화면에 글자 0·원 0, 왼쪽 아래 글자 자리에 흰 픽셀 0
        var pockets = new List<OrePocket>(FindObjectsByType<OrePocket>(FindObjectsSortMode.None));
        pockets.Sort((a, b) => (a.transform.position - MidTunnel).sqrMagnitude.CompareTo((b.transform.position - MidTunnel).sqrMagnitude));
        OrePocket pk = pockets.Find(x => !x.Breaking) ?? pockets[0];
        float dmg0 = pickaxe.damage;
        pickaxe.damage = 0f;
        StandAt(cc, pk);
        yield return null;
        int noise0 = NoiseBus.Total;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(0.3f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
        yield return new WaitForSeconds(Tuning.MINE_COOLDOWN);
        pickaxe.damage = dmg0;
        Teleport(cc, P, 0f);
        yield return null;
        yield return RightClick(mouse);
        int labels0 = MiningHud.LabelsDrawn, circles0 = MiningHud.CirclesDrawn;
        Vector3 corner = default;
        yield return Capture("19_no_text", v => corner = v, new Rect(0f, 0f, 320f, 130f));   // Capture 의 0.6 s 안에 소음 원(NOISE_HUD_FADE 1 s)이 아직 살아 있다
        Check("tunnel_screen_has_no_text", NoiseBus.Total > noise0 && !pickaxe.hasPick && !hud.enabled && MiningHud.LabelsDrawn == labels0 && MiningHud.CirclesDrawn == circles0 && corner.z == 0f,
            $"noises +{NoiseBus.Total - noise0}, hasPick {pickaxe.hasPick}, DevHud {(hud.enabled ? "on" : "off")}, labels +{MiningHud.LabelsDrawn - labels0}, circles +{MiningHud.CirclesDrawn - circles0}, bottom-left 320x130 bright pixels {corner.z * 100f:F1} %");

        // ② DevHud 는 꺼진 채 시작(UI-1d) — 컴포넌트를 켜고 한 프레임 지나도 표시 없음, F1 → 표시 + 소음 원, F1 → 다시 없음
        hud.enabled = true;
        yield return null;
        yield return null;
        bool startsHidden = !DevHud.Visible;
        yield return PressKey(kb, Key.F1);
        yield return null;
        bool shownByF1 = DevHud.Visible;
        circles0 = MiningHud.CirclesDrawn;
        NoiseBus.Make(player.transform.position, Tuning.NOISE_STEP, "step", player);
        yield return new WaitForSeconds(0.3f);
        int circlesOn = MiningHud.CirclesDrawn - circles0;
        yield return PressKey(kb, Key.F1);
        yield return null;
        bool hiddenAgain = !DevHud.Visible;
        hud.enabled = false;
        yield return null;
        Check("devhud_starts_hidden_f1_toggles", startsHidden && shownByF1 && hiddenAgain, $"visible at start {!startsHidden} (DEVHUD_START_VISIBLE {Tuning.DEVHUD_START_VISIBLE}), after F1 {shownByF1}, after F1 again {!hiddenAgain}");
        Check("noise_circle_only_with_devhud", circlesOn >= 1 && DevHud.Visible == false, $"circles drawn with DevHud shown: {circlesOn}, Visible after off: {DevHud.Visible}");

        // ③ 던진 곡괭이 머리: 4 m 에서 원래 재질·어두움, 2 m 에서 빛남 재질·밝음(램프 끄고), 주우면 원래대로
        t = 0f;
        while (!thrown.Frozen && t < Tuning.THROW_STUCK_S + 4f) { t += Time.deltaTime; yield return null; }
        Vector3 land = thrown.transform.position;
        lamp.lampOn = false;
        var camMain = pickaxe.cam.GetComponent<Camera>();
        float px = 1f / (Tuning.MOUSE_SENSITIVITY * Mathf.Rad2Deg);
        Vector3 lumFar = default, lumNear = default;
        bool farOrig = false, nearGlow = false;
        foreach (float d in new[] { 4f, 2f })
        {
            Vector3 at = new Vector3(land.x, 0.1f, land.z - d);
            Teleport(cc, at, Quaternion.LookRotation(Flat3(land - at)).eulerAngles.y);
            player.Look(new Vector2(0f, -30f * px));                    // 바닥의 곡괭이가 화면에 들어오게 30° 내려본다
            yield return null;
            Rect headRect = ScreenRect(camMain, new[] { thrown.head });
            if (d == 4f) { farOrig = !thrown.Glowing; yield return Capture("20_pick_head_far", v => lumFar = v, headRect); }
            else { nearGlow = thrown.Glowing; yield return Capture("20_pick_head_near", v => lumNear = v, headRect); }
            player.Look(new Vector2(0f, 30f * px));
        }
        yield return PressKey(kb, Key.E);
        bool restored = pickaxe.hasPick && !thrown.gameObject.activeSelf && !thrown.Glowing;
        Check("pick_head_glows_within_reach", farOrig && lumFar.x < 0.005f && nearGlow && lumNear.x > 0.01f && lumNear.x > lumFar.x * 10f && restored,   // 실측 0.024(머리 사각형엔 바닥도 섞인다) vs 0.0001
            $"lamp off — 4 m: glowing {!farOrig}, head lum {lumFar.x:F4} · 2 m: glowing {nearGlow}, head lum {lumNear.x:F4} (PICK_GLOW {Tuning.PICK_GLOW}) · after E: hasPick {pickaxe.hasPick}, glowing {thrown.Glowing}");
        lamp.lampOn = true;
        Teleport(cc, P, 0f);
        st.enabled = true;
    }

    // S1: 내 소리 순서. 숙이기 < 걷기 < 달리기 < 착지 < 타격, 이웃끼리 RMS 2배(6 dB). 발소리는 괴물 귀에도 들어간다
    IEnumerator SoundStage(CharacterController cc)
    {
        var st = stalker;
        var kb = InputSystem.AddDevice<Keyboard>("SoundKeyboard");
        var audio = new float[1024];
        Vector3 P = new Vector3(0f, 0.1f, 6f);
        st.enabled = false;
        lamp.lampOn = true;
        player.frozen = false;
        if (!pickaxe.hasPick) pickaxe.Return();
        yield return new WaitForSeconds(2f);        // 앞 구간(던진 곡괭이 착지 1.4 s)의 소리 꼬리가 숙이기 측정에 섞였다 — 전체 실행에서만 FAIL (09-16)

        // ① 자세별 2.6 s 이동: 발소리 RMS 최대 · 소음 반경 · 걸음 수
        string[] names = { "crouch", "walk", "run" };
        Key[][] keys = { new[] { Key.W, Key.LeftCtrl }, new[] { Key.W }, new[] { Key.W, Key.LeftShift } };
        float[] wantR = { Tuning.NOISE_STEP_CROUCH, Tuning.NOISE_STEP, Tuning.NOISE_STEP_RUN };
        float[] interval = { Tuning.STEP_INTERVAL_CROUCH, Tuning.STEP_INTERVAL, Tuning.STEP_INTERVAL_RUN };
        float[] rms = new float[3], radius = new float[3];
        int[] n = new int[3];
        NoiseSound.I.maxRepeat = 0;
        for (int i = 0; i < 3; i++)
        {
            Teleport(cc, P, 0f);
            player.stamina = Tuning.STAMINA_MAX;
            yield return null;
            int s0 = player.steps;
            InputSystem.QueueStateEvent(kb, new KeyboardState(keys[i]));
            float loud = 0f;
            for (float t = 0f; t < 2.6f; t += Time.deltaTime) { loud = Mathf.Max(loud, ListenerRms(audio)); yield return null; }
            InputSystem.QueueStateEvent(kb, new KeyboardState());
            for (float t = 0f; t < 0.4f; t += Time.deltaTime) { loud = Mathf.Max(loud, ListenerRms(audio)); yield return null; }
            rms[i] = loud;
            radius[i] = NoiseBus.LastRadius;
            n[i] = player.steps - s0;
            yield return new WaitForSeconds(0.5f);
        }
        int[] wantN = { 3, 5, 8 };
        bool stepsOk = true;
        string stepsInfo = "";
        for (int i = 0; i < 3; i++)
        {
            stepsOk &= Mathf.Approximately(radius[i], wantR[i]) && n[i] >= wantN[i] && n[i] <= wantN[i] + 2;
            stepsInfo += $"{names[i]} {n[i]} steps (2.6 s / {interval[i]} s) radius {radius[i]:0} m (want {wantR[i]:0}); ";
        }
        Check("step_noise_radius_interval", stepsOk && NoiseBus.LastKind == "step", stepsInfo);
        Check("step_variations_no_repeat", n[1] + n[2] >= 10 && NoiseSound.I.maxRepeat < 2, $"{n[1] + n[2]} steps, same file in a row max {NoiseSound.I.maxRepeat + 1}");

        // ② 착지·타격을 발 앞(2 m 안 = 최대 음량)에서 튼다 — 사다리는 거리 감쇠 전 크기로 비교한다
        Teleport(cc, P, 0f);
        yield return new WaitForSeconds(0.3f);
        //    변주 파일마다 크기가 달라 착지는 가장 큰 파일, 타격은 가장 작은 파일로 비교한다 (어느 짝이 나와도 순서가 지켜지게)
        float land = 0f, hit = 99f;
        Vector3 at = P + Vector3.forward * 1f + Vector3.up * 1.5f;
        foreach (var clip in NoiseSound.I.landClips)
        {
            float one = 0f;
            NoiseSound.Play3D(at, clip, Tuning.LAND_VOLUME, Tuning.NOISE_PICK_LAND);
            for (float t = 0f; t < clip.length + 0.2f; t += Time.deltaTime) { one = Mathf.Max(one, ListenerRms(audio)); yield return null; }
            land = Mathf.Max(land, one);
        }
        foreach (var clip in MiningFx.I.hitClips)
        {
            float one = 0f;
            NoiseSound.Play3D(at, clip, Tuning.HIT_VOLUME, Tuning.NOISE_PICK);
            for (float t = 0f; t < clip.length + 0.2f; t += Time.deltaTime) { one = Mathf.Max(one, ListenerRms(audio)); yield return null; }
            hit = Mathf.Min(hit, one);
        }
        if (hit > 90f) hit = 0f;                                          // 타격 파일이 없다(사보타주 mute)
        float[] ladder = { rms[0], rms[1], rms[2], land, hit };
        string[] ladderNames = { "crouch", "walk", "run", "land", "hit" };
        bool ladderOk = true;
        string ladderInfo = "";
        for (int i = 0; i < 5; i++)
        {
            float db = 20f * Mathf.Log10(Mathf.Max(ladder[i], 1e-6f));
            ladderInfo += $"{ladderNames[i]} {ladder[i]:F4} ({db:F1} dB)";
            if (i > 0)
            {
                float ratio = ladder[i] / Mathf.Max(ladder[i - 1], 1e-6f);
                ladderOk &= ratio >= 2f;
                ladderInfo += $" x{ratio:F2}";
            }
            ladderInfo += "; ";
        }
        Check("sound_ladder_6db", ladderOk && ladder[0] > 0.0005f, ladderInfo);

        // ③ 괴물 귀: 램프 끄고 12 m 앞 괴물 쪽으로 달리면 온다(14 m), 8 m 에서 걷기(6 m)·3 m 에서 숙이기(2 m)는 안 온다 — 멀어지는 쪽으로 움직인다
        lamp.lampOn = false;
        st.enabled = true;
        string[] earNames = { "run12", "walk8", "crouch3" };
        float[] dist = { 12f, 8f, 3f };
        Key[][] earKeys = { new[] { Key.W, Key.LeftShift }, new[] { Key.S }, new[] { Key.S, Key.LeftCtrl } };
        bool[] wantHear = { true, false, false };
        bool earOk = true;
        string earInfo = "";
        for (int i = 0; i < 3; i++)
        {
            Teleport(cc, P, 0f);
            player.stamina = Tuning.STAMINA_MAX;
            st.Teleport(P + Vector3.forward * dist[i], 180f);
            st.lastHeard = "-";
            yield return null;
            InputSystem.QueueStateEvent(kb, new KeyboardState(earKeys[i]));
            float t = 0f;
            while (t < 1.5f && !st.lastHeard.StartsWith("step")) { t += Time.deltaTime; yield return null; }
            InputSystem.QueueStateEvent(kb, new KeyboardState());
            yield return null;
            bool heard = st.lastHeard.StartsWith("step");
            bool moving = st.state == Stalker.State.Investigate || st.state == Stalker.State.Search;
            earOk &= heard == wantHear[i] && moving == wantHear[i];
            earInfo += $"{earNames[i]}: heard '{st.lastHeard}' state {st.state} at {t:F1} s (want {(wantHear[i] ? "hear" : "ignore")}); ";
            yield return new WaitForSeconds(0.3f);
        }
        Check("stalker_hears_steps", earOk, earInfo);

        // ④ 괴물을 곡괭이로 치면 광물 소리가 아니라 몸에 맞는 소리(pick_flesh)가 난다
        lamp.lampOn = true;
        Teleport(cc, P, 0f);
        st.Teleport(P + Vector3.forward * 2.2f, 180f);
        st.hp = Tuning.STALKER_HP;
        st.hitsSeen = 0;
        yield return null;
        NoiseSound.last3D = "-";
        var mouse = InputSystem.AddDevice<Mouse>("SoundMouse");
        yield return Click(mouse);
        yield return new WaitForSeconds(0.5f);
        Check("stalker_hit_sound_is_flesh", st.hitsSeen >= 1 && NoiseSound.last3D.StartsWith("pick_flesh"), $"hits seen {st.hitsSeen}, last 3D sound '{NoiseSound.last3D}'");
        InputSystem.RemoveDevice(mouse);
        st.hp = Tuning.STALKER_HP;
        st.enabled = false;
        st.Teleport(st.homePos);
        lamp.lampOn = true;
        Teleport(cc, P, 0f);
        InputSystem.RemoveDevice(kb);
    }

    // M6: 곡괭이 던지기. 플레이어는 z 6 에서 +Z 를 본다. 괴물은 필요한 검사에서만 켠다
    IEnumerator ThrowStage(CharacterController cc)
    {
        var st = stalker;
        var mouse = InputSystem.AddDevice<Mouse>("ThrowMouse");
        var kb = InputSystem.AddDevice<Keyboard>("ThrowKeyboard");
        var thrown = pickaxe.thrown;
        Vector3 P = new Vector3(0f, 0.1f, 6f);
        float t;

        // ① 던지면 뷰모델이 꺼지고 ThrownPick 이 날아가 3 s 안에 착지, 소음 pick_land 20 m 한 번, 5 m 이상 날아간다
        st.enabled = false;
        lamp.lampOn = true;
        Teleport(cc, P, 0f);
        player.frozen = false;
        if (!pickaxe.hasPick) pickaxe.Return();
        yield return null;
        int noise0 = NoiseBus.Total;
        yield return RightClick(mouse);
        bool vmOff = !pickaxe.mesh.gameObject.activeSelf;
        bool active = thrown.gameObject.activeSelf;
        t = 0f;
        while (!thrown.landed && t < 3f) { t += Time.deltaTime; yield return null; }
        float landT = t;
        float range = Flat(thrown.landPos - P);
        Check("throw_lands_with_noise_20m", vmOff && active && !pickaxe.hasPick && thrown.landed && NoiseBus.Total == noise0 + 1 && NoiseBus.LastKind == "pick_land" && NoiseBus.LastRadius == Tuning.NOISE_PICK_LAND && Mathf.Abs(range - Tuning.THROW_RANGE_M) <= 0.5f,
            $"viewmodel off {vmOff}, thrown active {active}, hasPick {pickaxe.hasPick}, landed {thrown.landed} at {landT:F2} s on {thrown.landedOn} at {thrown.landPos}, {range:F1} m from thrower (THROW_RANGE_M {Tuning.THROW_RANGE_M} ±0.5), noise {NoiseBus.LastKind} {NoiseBus.LastRadius:0} m (+{NoiseBus.Total - noise0})");

        // ② 던진 뒤엔 못 캔다: 포켓 앞에서 좌클릭 → 포켓 체력 그대로, 소음 없음
        var pockets = new List<OrePocket>(FindObjectsByType<OrePocket>(FindObjectsSortMode.None));
        pockets.Sort((a, b) => (a.transform.position - MidTunnel).sqrMagnitude.CompareTo((b.transform.position - MidTunnel).sqrMagnitude));
        OrePocket pk = pockets.Find(x => !x.Breaking && x.health >= Tuning.POCKET_HEALTH) ?? pockets[0];
        StandAt(cc, pk);
        yield return null;
        float hp0 = pk.health;
        noise0 = NoiseBus.Total;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(0.6f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
        yield return null;
        Check("no_mining_without_pick", pk.health == hp0 && NoiseBus.Total == noise0 && !pickaxe.hasPick, $"pocket hp {hp0:0} → {pk.health:0}, noises +{NoiseBus.Total - noise0}, hasPick {pickaxe.hasPick}");

        // ③ 유인: 램프 끄고, 착지점에서 15 m 북쪽에 배회하는 괴물 → Investigate 로 착지점 쪽으로 5 m 이상 온다 (첫 소리 = 7 m 규칙)
        pickaxe.Return();
        lamp.lampOn = false;
        Teleport(cc, P, 0f);
        yield return null;
        Vector3 expectLand = P + Vector3.forward * range;
        Vector3 S = new Vector3(0f, 0.1f, Mathf.Min(expectLand.z + 15f, st.zMax - 1f));
        st.enabled = true;
        st.Teleport(S, 180f);
        st.hp = Tuning.STALKER_HP;
        yield return null;
        yield return RightClick(mouse);
        t = 0f;
        while (!thrown.landed && t < 3f) { t += Time.deltaTime; yield return null; }
        float sd0 = Flat(st.transform.position - thrown.landPos);
        t = 0f;
        while (t < 4f && !((st.state == Stalker.State.Investigate || st.state == Stalker.State.Search) && Flat(st.transform.position - S) >= 5f)) { t += Time.deltaTime; yield return null; }
        float moved = Flat(st.transform.position - S);
        float sd1 = Flat(st.transform.position - thrown.landPos);
        Check("landing_noise_lures_wanderer", sd0 <= Tuning.NOISE_PICK_LAND && st.lastHeard.StartsWith("pick_land") && (st.state == Stalker.State.Investigate || st.state == Stalker.State.Search) && moved >= 5f && sd1 < sd0,
            $"stalker {sd0:F1} m from landing, heard '{st.lastHeard}', state {st.state} after {t:F1} s, moved {moved:F1} m, now {sd1:F1} m from landing");

        // ④ 추격 중엔 무시: 35 m 북쪽에서 추격해 오는 괴물 — 던져도 상태 Chase 그대로, pick_land 를 안 듣는다
        pickaxe.Return();
        Teleport(cc, P, 0f);
        st.Teleport(new Vector3(0f, 0.1f, Mathf.Min(P.z + 35f, st.zMax - 1f)), 180f);
        float loseS0 = st.loseS;
        st.loseS = 99f;                                                // 못 보는 동안 추격을 놓지 않게 — 값만 바꿈
        st.state = Stalker.State.Chase;
        st.lastSeen = P;
        st.lastHeard = "-";
        yield return null;
        yield return RightClick(mouse);
        t = 0f;
        while (!thrown.landed && t < 3f) { t += Time.deltaTime; yield return null; }
        yield return new WaitForSeconds(0.3f);
        Check("chaser_ignores_landing_noise", thrown.landed && st.state == Stalker.State.Chase && !st.lastHeard.StartsWith("pick_land"),
            $"landed {thrown.landed}, state {st.state}, heard '{st.lastHeard}', {Flat(st.transform.position - player.transform.position):F1} m away");
        st.loseS = loseS0;
        st.enabled = false;
        st.Teleport(st.homePos);

        // ⑤ 줍기: 4 m 에서 E 는 안 먹고, 2 m 에서 E 면 다시 든다. 착지 뒤 굴러가다 THROW_STUCK_S 에 멈춘 자리 기준
        t = 0f;
        while (!thrown.Frozen && t < Tuning.THROW_STUCK_S + 2f) { t += Time.deltaTime; yield return null; }
        Vector3 land = thrown.transform.position;
        float rolled = Flat(land - thrown.landPos);
        Bounds lying = thrown.MeshBounds;                                 // 바닥(y 0)에 눕는다 — 어느 점도 바닥 아래로 안 가고, 서 있지도 않는다
        Check("thrown_pick_rests_on_floor", thrown.Frozen && lying.min.y > -0.03f && lying.max.y < 0.35f,
            $"mesh lowest {lying.min.y:F3} m, highest {lying.max.y:F3} m above floor after freeze (frozen {thrown.Frozen})");
        Teleport(cc, new Vector3(land.x, 0.1f, land.z - 4f), 0f);
        yield return null;
        yield return PressKey(kb, Key.E);
        bool farNo = !pickaxe.hasPick && thrown.gameObject.activeSelf;
        Teleport(cc, new Vector3(land.x, 0.1f, land.z - 2f), 0f);
        yield return null;
        yield return PressKey(kb, Key.E);
        Check("pickup_with_e_within_reach", farNo && pickaxe.hasPick && pickaxe.mesh.gameObject.activeSelf && !thrown.gameObject.activeSelf,
            $"rolled {rolled:F1} m after landing, frozen {thrown.Frozen}; E at 4 m: hasPick {!farNo}; E at 2 m: hasPick {pickaxe.hasPick}, viewmodel {pickaxe.mesh.gameObject.activeSelf}, thrown active {thrown.gameObject.activeSelf}");

        // ⑥ 맞히기: 5 m 앞 괴물에 던지면 체력 −25 · 스턴, 곡괭이는 괴물 2 m 안에 떨어진다
        lamp.lampOn = false;
        Teleport(cc, P, 0f);
        st.enabled = true;
        Vector3 T = P + Vector3.forward * 5f;
        st.Teleport(T, 180f);
        st.hp = Tuning.STALKER_HP;
        st.hitsSeen = st.hitsTaken = 0;
        yield return null;
        float hpBefore = st.hp;
        yield return RightClick(mouse);
        t = 0f;
        while (st.state != Stalker.State.Stun && t < 1.5f) { t += Time.deltaTime; yield return null; }
        bool stunnedByThrow = st.state == Stalker.State.Stun;
        yield return new WaitForSeconds(0.6f);                         // 곡괭이가 1.9 m 에서 떨어지는 시간. 스턴(0.5 s) 뒤 추격이 5 m 를 오기 전
        float dropD = Flat(thrown.transform.position - T);
        Check("thrown_pick_hits_and_stuns", stunnedByThrow && st.hp == hpBefore - Tuning.STALKER_HIT_DMG && st.hitsTaken == 1 && thrown.landed && dropD < 2f,
            $"stunned {stunnedByThrow} (now {st.state}), hp {hpBefore:0} → {st.hp:0}, taken {st.hitsTaken}, landed {thrown.landed} {dropD:F1} m from stalker");
        st.enabled = false;                                            // 스턴이 끝나면 추격 — 5 m 라 바로 잡힌다. 여기서 끈다
        st.Teleport(st.homePos);
        player.frozen = false;
        if (!pickaxe.hasPick) pickaxe.Return();                        // 다음 구간은 곡괭이를 들고 시작한다
        lamp.lampOn = true;
        st.enabled = true;
    }

    IEnumerator M1(CharacterController cc, VolumetricFogVolumeComponent fog)
    {
        // 1. 조각 크기와 이음새 — glTFast 가 축·배율을 바꿨으면 여기서 걸린다
        var shells = new List<Renderer>();
        foreach (var r in pieces.GetComponentsInChildren<MeshRenderer>())
            if (r.name.StartsWith("SHL_")) shells.Add(r);
        shells.Sort((a, b) => a.bounds.center.z.CompareTo(b.bounds.center.z));
        Vector3 size = shells.Count > 0 ? shells[0].bounds.size : Vector3.zero;
        Check("piece_size_7x5.6x7", (size - new Vector3(7f, 5.6f, 7f)).magnitude < 0.01f, size.ToString("F3"));
        float gap = shells.Count > 1 ? 0f : 99f;
        for (int i = 1; i < shells.Count; i++)
            gap = Mathf.Max(gap, Mathf.Abs(shells[i].bounds.min.z - shells[i - 1].bounds.max.z));
        Check("seam_gap_under_5mm", gap < 0.005f, $"{gap * 1000f:F2} mm, pieces {shells.Count}");

        // 2. 바닥에 선다
        Check("grounded", cc.isGrounded && Mathf.Abs(player.transform.position.y) < 0.2f, $"y={player.transform.position.y:F3}");

        // 3. 걷기 2초 · 달리기 1초 (가상 키보드)
        var kb = InputSystem.AddDevice<Keyboard>("CheckKeyboard");
        Vector3 p0 = player.transform.position;
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
        yield return new WaitForSeconds(2f);
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        yield return new WaitForSeconds(0.5f);
        float walked = Flat(player.transform.position - p0);
        Check("walk_2s_m", walked > 8.3f && walked < 9.6f, $"{walked:F2} (expect ~8.96)");

        player.transform.rotation = Quaternion.LookRotation(Vector3.back);   // 되돌아 달린다 — 갱도 42 m 안
        yield return null;
        p0 = player.transform.position;
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W, Key.LeftShift));
        yield return new WaitForSeconds(1f);
        float ran = Flat(player.transform.position - p0);
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        yield return new WaitForSeconds(0.5f);
        Check("run_1s_m", ran > 6.3f && ran < 7.6f, $"{ran:F2} (expect 6.3~7.1, frame timing)");
        player.transform.rotation = Quaternion.identity;

        // 4. 램프 설정
        var light = lamp.GetComponent<Light>();
        Check("lamp_config", light.type == LightType.Spot && Mathf.Approximately(light.spotAngle, Tuning.LAMP_ANGLE_DEG * 2f)
            && light.shadows != LightShadows.None && lamp.GetComponent<VolumetricAdditionalLight>() != null,
            $"spotAngle={light.spotAngle} shadows={light.shadows}");

        // 5. 앞뒤 대칭: 갱도 가운데(조각 이음새 z 17.5)에서 +Z / -Z. 갱도가 대칭이라 밝기가 비슷해야 한다.
        // 사용자 지적(09-14 "+Z 쪽으로 램프 빛이 안 보인다") — 노멀맵 sRGB 임포트 때 +Z 0.022 / -Z 0.130
        Vector3 back = player.transform.position;
        Vector3 plusZ = default, minusZ = default, nearWall = default;
        Teleport(cc, new Vector3(0f, 0.1f, 17.5f), 0f);
        yield return Capture("4_mid_plusZ", v => plusZ = v);
        Teleport(cc, new Vector3(0f, 0.1f, 17.5f), 180f);
        yield return Capture("5_mid_minusZ", v => minusZ = v);
        float sym = Mathf.Min(plusZ.x, minusZ.x) / Mathf.Max(Mathf.Max(plusZ.x, minusZ.x), 1e-5f);
        Check("lamp_symmetric_z", sym > 0.67f, $"+Z {plusZ.x:F4} -Z {minusZ.x:F4} (min/max {sym:F2})");

        // 6. 벽 앞: 몸이 벽에 닿은 자리에서 벽을 본다. 사용자 지적(09-14 "벽에 가까이 붙으면 램프를 낮춰도 매우 밝다")
        Teleport(cc, NearWallPos, 90f);
        yield return Capture("6_near_wall", v => nearWall = v);
        Check("near_wall_not_burnt", nearWall.z < MaxBurntNearWall, $"burnt {nearWall.z * 100f:F1} % (limit {MaxBurntNearWall * 100f:F0} %) lum {nearWall.x:F3} dim {lamp.nearDim:F3}");
        Teleport(cc, back, 0f);

        // 7. 화면: 램프+안개 / 램프만 / 램프 끔. 밝기(lum)·구조(grad, 이웃 픽셀 차)·fps 는 사람이 보는 화면에서 잰다
        Vector3 fogShot = default, noFogShot = default, darkShot = default;
        float fpsFog = 0f, fpsNoFog = 0f;
        yield return Capture("1_lamp_fog", v => fogShot = v);
        yield return MeasureFps(5f, v => fpsFog = v);
        float density = fog.density.value;
        fog.enabled.value = false;
        yield return Capture("2_lamp_nofog", v => noFogShot = v);
        yield return MeasureFps(5f, v => fpsNoFog = v);
        fog.enabled.value = true;
        fog.density.value = density;
        lamp.lampOn = false;
        yield return Capture("3_lamp_off", v => darkShot = v);
        lamp.lampOn = true;

        Check("lamp_lights_screen", fogShot.x > 0.01f && fogShot.x > darkShot.x * 3f, $"on {fogShot.x:F4} off {darkShot.x:F4}");
        // 기준 화면이 거의 검으면 아래 안개 구조 비교가 뜻이 없다 — 첫 빌드(램프 35, 밝기 0.003)에서 망가진 안개가 PASS 했다
        Check("lamp_not_black", noFogShot.x > 0.008f, $"nofog lum {noFogShot.x:F4} (Godot {GodotLum} 의 x{noFogShot.x / GodotLum:F2})");
        // 안개가 보여야 하고(밝기 +2 % 이상), 갱도 형태를 지우면 안 된다(구조 85 % 이상 남음 — 실측 0.012 는 70 % 로 끝이 흰 막이었다)
        Check("volfog_visible", fogShot.x > noFogShot.x * 1.02f, $"lum fog {fogShot.x:F4} nofog {noFogShot.x:F4}");
        Check("volfog_keeps_structure", fogShot.y >= noFogShot.y * 0.85f, $"grad fog {fogShot.y:F2} nofog {noFogShot.y:F2} ({fogShot.y / noFogShot.y * 100f:F0} %)");
        Check("fps_fog_min60", fpsFog >= MinFps, $"fog {fpsFog:F0} fps ({1000f / fpsFog:F2} ms) · nofog {fpsNoFog:F0} fps ({1000f / fpsNoFog:F2} ms) · {SystemInfo.graphicsDeviceName}");
    }

    // 8. 채굴 (M2): 포켓 24자리 · 묻힘 · 곡괭이 오버레이·밝기 · 조준 보정 · 채굴 거리 눈부심 · 두 번에 캐짐 · 소음 · 타격음 · 광석 구르기 · 줍기 · 휘두르기 간격
    IEnumerator Mining(CharacterController cc)
    {
        var pockets = new List<OrePocket>(FindObjectsByType<OrePocket>(FindObjectsSortMode.None));
        Check("pockets_24", pockets.Count == 24, $"{pockets.Count}");

        // 묻힘: 통로 쪽 2 m 에서 포켓 가운데로 쏜 광선이 조각 바위 면보다 포켓에 먼저 닿아야 한다. 바위 면 충돌체는 이 검사 동안만 붙인다
        var temp = new List<MeshCollider>();
        foreach (var r in pieces.GetComponentsInChildren<MeshRenderer>())
            if (r.name.StartsWith("SHL_"))
            {
                var mc = r.gameObject.AddComponent<MeshCollider>();
                mc.sharedMesh = r.GetComponent<MeshFilter>().sharedMesh;
                temp.Add(mc);
            }
        Physics.SyncTransforms();
        int visible = 0;
        foreach (var pk in pockets)
        {
            var hits = Physics.RaycastAll(pk.transform.position + pk.outDir * 2f, -pk.outDir, 2.5f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore);
            Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
            if (hits.Length > 0 && hits[0].collider.GetComponent<OrePocket>() == pk) visible++;
        }
        foreach (var mc in temp) Destroy(mc);
        yield return null;
        Check("pockets_not_buried", pockets.Count > 0 && visible == pockets.Count, $"{visible}/{pockets.Count} visible");

        pockets.Sort((a, b) => (a.transform.position - MidTunnel).sqrMagnitude.CompareTo((b.transform.position - MidTunnel).sqrMagnitude));
        OrePocket first = pockets[0], second = pockets[1];
        var mouse = InputSystem.AddDevice<Mouse>("CheckMouse");
        lamp.lampOn = true;

        // 곡괭이는 ViewModel 레이어 → 오버레이 카메라가 그린다 (사용자 09-14 "곡괭이가 벽 안으로 들어간다")
        var mainCam = pickaxe.cam.GetComponent<Camera>();
        var stack = mainCam.GetUniversalAdditionalCameraData().cameraStack;
        Camera vm = stack.Count > 0 ? stack[0] : null;
        int vmBit = 1 << Pickaxe.ViewModelLayer;
        var pickRenderers = pickaxe.GetComponentsInChildren<Renderer>(true);
        bool pickOnLayer = pickRenderers.Length > 0;
        foreach (var r in pickRenderers) pickOnLayer &= r.gameObject.layer == Pickaxe.ViewModelLayer;
        Check("viewmodel_overlay", pickOnLayer && (mainCam.cullingMask & vmBit) == 0 && vm != null && vm.cullingMask == vmBit,
            $"pick on layer {pickOnLayer}, main culls it {(mainCam.cullingMask & vmBit) == 0}, overlay {(vm != null ? vm.name : "none")}");

        // 곡괭이 화면 영역이 하얗게 타지 않고, 어둡지도 않다 (사용자 09-14 "곡괭이가 하얗게 뜨는 게 거슬린다").
        // 두 자리에서 본다: 갱도 가운데(램프 감광 없음 — 곡괭이가 가장 밝게 뜨는 곳)와 벽에 몸이 닿은 자리(곡괭이가 벽 위에 보이는지)
        Teleport(cc, new Vector3(0f, 0.1f, 17.5f), 0f);
        yield return null;
        Rect pickRect = ScreenRect(mainCam, pickRenderers);
        Vector3 pickTunnel = default, pickWall = default;
        yield return Capture("10_pick_in_tunnel", v => pickTunnel = v, pickRect);
        Teleport(cc, NearWallPos, 90f);
        yield return Capture("9_pick_at_wall", v => pickWall = v, pickRect);
        Check("pick_not_burnt", pickRect.width > 0f && Mathf.Max(pickTunnel.z, pickWall.z) < MaxBurntPick && pickTunnel.x > 0.03f,
            $"tunnel burnt {pickTunnel.z * 100f:F1} % lum {pickTunnel.x:F3} · wall burnt {pickWall.z * 100f:F1} % lum {pickWall.x:F3} · in {pickRect.width:F0}x{pickRect.height:F0} px");

        // 조준 보정: 포켓 가장자리(구 0.16)에서 조금 빗나가도(가운데에서 0.22 m) 맞고, 0.5 m 빗나가면 안 맞는다 (사용자 09-14 "정확하게 캐는 게 쉽지 않다")
        StandAt(cc, first);
        Vector3 at = player.transform.position;
        float baseYaw = Quaternion.LookRotation(-first.outDir).eulerAngles.y;
        float eyeGap = first.transform.position.y - pickaxe.cam.position.y;
        float horizNear = Mathf.Sqrt(Mathf.Max(0.22f * 0.22f - eyeGap * eyeGap, 0f));
        Teleport(cc, at, baseYaw + Mathf.Asin(horizNear / 1.8f) * Mathf.Rad2Deg);
        bool nearHit = pickaxe.HasTarget;
        Teleport(cc, at, baseYaw + Mathf.Asin(0.5f / 1.8f) * Mathf.Rad2Deg);
        bool farHit = pickaxe.HasTarget;
        Teleport(cc, at, baseYaw);
        Check("aim_assist", nearHit && !farHit, $"0.22 m off hits {nearHit}, 0.5 m off hits {farHit}");

        // 채굴 거리(1.8 m)에서 포켓을 본 화면
        Vector3 view = default;
        yield return Capture("7_mining_view", v => view = v);
        Check("mining_view_not_burnt", view.z < MaxBurntNearWall, $"burnt {view.z * 100f:F1} % lum {view.x:F3} dim {lamp.nearDim:F2}");

        // 누르고 있으면 두 번째 타격에 캐진다. 그동안 귀(AudioListener)에 들어온 소리 크기를 잰다
        int noise0 = NoiseBus.Total, ore0 = player.ore;
        var audio = new float[512];
        float loudest = 0f;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        float t = 0f;
        while (first != null && t < 2f) { t += Time.deltaTime; loudest = Mathf.Max(loudest, ListenerRms(audio)); yield return null; }
        InputSystem.QueueStateEvent(mouse, new MouseState());
        for (float u = 0f; u < 0.3f; u += Time.deltaTime) { loudest = Mathf.Max(loudest, ListenerRms(audio)); yield return null; }
        int strikes = NoiseBus.Total - noise0;
        Check("pocket_breaks_on_2nd_hit", first == null && strikes == 2, $"strikes {strikes}, broke {first == null} after {t:F2} s");
        Check("pick_noise_25m", NoiseBus.LastKind == "pick" && Mathf.Approximately(NoiseBus.LastRadius, Tuning.NOISE_PICK), $"{NoiseBus.LastKind} {NoiseBus.LastRadius} m");
        Check("pick_hit_audible", loudest > 0.005f, $"listener rms max {loudest:F4}");

        // 광석: 1.4 초(자석 전)까지 구르고 멈춰 있다, 그 뒤 빨려와 줍힌다
        var ore = FindAnyObjectByType<Ore>();
        yield return Capture("8_mining_break", v => { });
        while (ore != null && ore.Age < 1.4f) yield return null;
        bool rolled = ore != null && !ore.Pulled;
        float roll = ore != null ? Flat(ore.transform.position - ore.spawnPos) : -1f;
        float oreY = ore != null ? ore.transform.position.y : -99f;
        Check("ore_rolls_and_waits", rolled && roll > 0.5f && roll < 2.5f && oreY > -0.1f, $"roll {roll:F2} m y {oreY:F2} at 1.4 s, waited {rolled}");
        t = 0f;
        while (player.ore == ore0 && t < 4f) { t += Time.deltaTime; yield return null; }
        Check("ore_picked_up", player.ore == ore0 + 1, $"ore {player.ore} (+{t:F1} s)");

        // 안 캐지는 포켓을 1초 누르고 있으면 휘두르기는 3번 이하 (한 번에 MINE_COOLDOWN)
        StandAt(cc, second);
        yield return new WaitForSeconds(0.6f);
        second.health = 1e6f;
        noise0 = NoiseBus.Total;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(1f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
        strikes = NoiseBus.Total - noise0;
        Check("swing_interval_max3_per_s", strikes >= 2 && strikes <= 3, $"strikes {strikes} in 1 s (swing {Tuning.MINE_COOLDOWN:F2} s)");
    }

    // M5: 체력·스턴·철수. 플레이어를 괴물 앞 2.2 m(사거리 3 m 안)에 세우고 한 번 클릭 = 한 대. 괴물은 매번 z 20 에 북쪽을 보고 선다
    IEnumerator RetreatStage(CharacterController cc)
    {
        var st = stalker;
        var mouse = InputSystem.AddDevice<Mouse>("RetreatMouse");
        lamp.lampOn = true;
        Vector3 S = new Vector3(0f, 0.1f, 20f);
        Vector3 fwd = Vector3.forward;
        Vector3 P = S - fwd * 1.6f;                                   // 남쪽 1.6 m 에서 북쪽(괴물)을 본다 — 1.0 m 밀린 뒤에도 사거리 3 m 안
        var bodyT = st.transform.Find("Body");
        float t;

        // ① 1대: 체력 75, 1.5 s 멈춤(0.2 s 에 1.0 m 밀림, 나머지 서서 봄), 스턴 중 한 대 더는 안 먹힌다, 끝나면 추격
        st.Teleport(S, 180f);
        st.hp = Tuning.STALKER_HP;
        st.hitsSeen = st.hitsTaken = 0;                                // 앞 구간에서 닿은 것은 센다 — 여기서 0 부터
        Teleport(cc, P, 0f);
        player.frozen = false;
        yield return null;
        float hp0 = st.hp;
        float cool0 = pickaxe.cooldownTime, mul0 = pickaxe.swingTimeMul;
        pickaxe.cooldownTime = 0f;                                     // 스턴 0.5 s 안에 두 타가 닿게 이 두 번만 빠르게 (사람은 0.69 s 걸려 못 한다). 첫 타 뒤엔 되돌리기(0.29 s)가 두 번째를 막는다
        pickaxe.swingTimeMul = 0.2f;
        yield return Click(mouse);
        t = 0f;
        while (st.state != Stalker.State.Stun && t < 1f) { t += Time.deltaTime; yield return null; }
        float stunStart = Time.time;
        yield return null;                                             // 납작해진 몸이 한 프레임 뒤에 보인다
        float hp1 = st.hp;
        float squash = bodyT != null ? bodyT.localScale.y : -1f;
        Vector3 at = st.transform.position;
        yield return new WaitForSeconds(0.1f);                         // 첫 휘두르기(0.1 s)가 끝난 뒤
        yield return Click(mouse);                                     // 스턴 중 한 대 더 — 닿지만 안 먹혀야 한다
        yield return new WaitForSeconds(0.15f);
        pickaxe.cooldownTime = cool0;
        pickaxe.swingTimeMul = mul0;
        int taken = st.hitsTaken;
        while (st.state == Stalker.State.Stun && Time.time - stunStart < 3f) yield return null;
        float stunT = Time.time - stunStart;
        float back = Flat(st.transform.position - at);
        Check("hit_damages_and_stuns", hp0 == Tuning.STALKER_HP && hp1 == hp0 - Tuning.STALKER_HIT_DMG && stunT > Tuning.STALKER_STUN_S - 0.2f && stunT < Tuning.STALKER_STUN_S + 0.3f && back > 0.6f && back < 1.4f && st.state == Stalker.State.Chase && squash < bodyT.localScale.y,
            $"hp {hp0:0} → {hp1:0}, stun {stunT:F2} s (STALKER_STUN_S {Tuning.STALKER_STUN_S}), knocked {back:F2} m, then {st.state}, squash y {squash:F2}→{bodyT.localScale.y:F2}");
        Check("hits_during_stun_ignored", st.hp == hp1 && taken == 1 && st.hitsTaken == 1 && st.hitsSeen == 2, $"hp {st.hp:0} after a 2nd swing during stun, swings landed {st.hitsSeen}, taken {st.hitsTaken}");

        // ② 2대째·3대째: 체력 50 → 25, 세 번째는 멈춤 없이 그 자리에서 철수
        for (int i = 0; i < 2; i++)
        {
            st.Teleport(S, 180f);                                        // 자리만 되돌린다 — 체력은 그대로 (Teleport 는 hp 를 안 건드린다)
            Teleport(cc, P, 0f);
            player.frozen = false;                                       // 스턴 끝에 추격 → 잡힘이 한 프레임에 끼어들 수 있다
            yield return null;
            yield return Click(mouse);
            t = 0f;
            while (st.state != Stalker.State.Stun && t < 1f) { t += Time.deltaTime; yield return null; }
            if (i == 0) { while (st.state == Stalker.State.Stun) yield return null; }
            else { while (st.state != Stalker.State.Retreat && st.state != Stalker.State.Stun && t < 1f) { t += Time.deltaTime; yield return null; } }
        }
        float hp3 = st.hp;
        Vector3 retreatFrom = player.transform.position;
        bool noStun = st.state != Stalker.State.Stun;
        while (st.state == Stalker.State.Stun) yield return null;
        yield return null;
        Check("third_hit_retreats_at_once", hp3 == Tuning.STALKER_HP - 3f * Tuning.STALKER_HIT_DMG && hp3 <= Tuning.STALKER_RETREAT_HP && noStun && st.state == Stalker.State.Retreat,
            $"hp after 3 hits {hp3:0} (retreat line {Tuning.STALKER_RETREAT_HP}), stunned first {!noStun}, state {st.state}");

        // ③ 철수 중 무적: 길 앞 1.5 m 에 서서 쳐도 곡괭이가 안 닿고(hitsSeen 그대로) 멈추지 않고 체력 그대로, 철수 계속. 0.6 s 뒤 비킨다(1 s 막히면 그 자리를 도착으로 친다)
        Vector3 dir = Flat3(st.retreatSpot - st.transform.position).normalized;
        Teleport(cc, st.transform.position + dir * 1.5f, Quaternion.LookRotation(-dir).eulerAngles.y);
        yield return null;
        int seen0 = st.hitsSeen;
        bool target = pickaxe.HasTarget;
        yield return Click(mouse);
        bool stunned = false;
        t = 0f;
        while (t < 0.6f) { stunned |= st.state == Stalker.State.Stun; t += Time.deltaTime; yield return null; }
        Teleport(cc, retreatFrom, 0f);
        yield return null;
        Check("retreat_is_immune", !target && !stunned && st.hitsSeen == seen0 && st.hp == hp3 && (st.state == Stalker.State.Retreat || st.state == Stalker.State.Climb),
            $"pick target {target}, stunned {stunned}, swings landed +{st.hitsSeen - seen0}, hp {st.hp:0} (was {hp3:0}), state {st.state}");

        // ④ 철수 자리: 플레이어에서 8~14 m, 램프 원뿔(60°) 안. 7 m 를 벗어난 뒤 다시 안 들어온다 (#16)
        float minAfter = 99f;
        bool left = false;
        t = 0f;
        while (st.state == Stalker.State.Retreat && t < 10f)
        {
            float d = Flat(st.transform.position - retreatFrom);
            if (d > Tuning.GRID_CELL) left = true;
            else if (left) minAfter = Mathf.Min(minAfter, d);
            t += Time.deltaTime;
            yield return null;
        }
        float spotD = Flat(st.retreatSpot - st.retreatFrom);
        float spotAng = Vector3.Angle(Flat3(st.retreatFwd), Flat3(st.retreatSpot - st.retreatFrom));
        Check("retreat_spot_in_lamp_cone_8_14m", st.state == Stalker.State.Climb && spotD >= Tuning.STALKER_RETREAT_MIN_M - 0.5f && spotD <= Tuning.STALKER_RETREAT_MAX_M + 0.5f && spotAng <= Tuning.LAMP_ANGLE_DEG && st.retreatInCone && minAfter > Tuning.GRID_CELL,
            $"spot {spotD:F1} m at {spotAng:F0}° (cone ±{Tuning.LAMP_ANGLE_DEG}), inCone {st.retreatInCone}, re-entered 7 m: {(minAfter <= Tuning.GRID_CELL ? "yes " + minAfter.ToString("F1") : "no")}, state {st.state} after {t:F1} s");

        // ⑤ 벽타기 3~5 s 뒤 사라진다, 숨은 시간은 90 s 로 시작
        float y0 = st.transform.position.y;
        t = 0f;
        while (st.state == Stalker.State.Climb && t < 8f) { t += Time.deltaTime; yield return null; }
        bool shown = false;
        foreach (var r in st.GetComponentsInChildren<Renderer>()) shown |= r.enabled;
        Check("climbs_wall_then_vanishes", st.state == Stalker.State.Hidden && t > 3f && t < 5f && !shown && Mathf.Abs(st.hiddenLeft - Tuning.STALKER_REGEN_S) < 1f,
            $"climb {t:F1} s from y {y0:F1}, state {st.state}, visible {shown}, hidden {st.hiddenLeft:0} s (STALKER_REGEN_S {Tuning.STALKER_REGEN_S})");

        // ⑥ 재등장: 숨은 시간만 2 s 로 줄인다(값만 바꿈). 체력 100, 플레이어에서 먼 틈, 배회. 램프는 꺼서 나오자마자 빛을 보고 움직이지 않게
        lamp.lampOn = false;
        st.hiddenLeft = 2f;
        t = 0f;
        while (st.state == Stalker.State.Hidden && t < 5f) { t += Time.deltaTime; yield return null; }
        shown = true;
        foreach (var r in st.GetComponentsInChildren<Renderer>()) shown &= r.enabled;
        float far = 0f;
        foreach (var c in st.cracks) far = Mathf.Max(far, Flat(c - player.transform.position));
        float d2 = Flat(st.transform.position - player.transform.position);
        Check("reappears_at_far_crack_full_hp", st.state == Stalker.State.Wander && st.hp == Tuning.STALKER_HP && shown && d2 > 15f && Mathf.Abs(d2 - far) < 1.5f,
            $"state {st.state}, hp {st.hp:0}, visible {shown}, {d2:F1} m from player (far crack {far:F1} m)");
        lamp.lampOn = true;
    }

    // M4: 눈·빛·추격·잡기. 플레이어는 z 10 에서 +Z 를 본다. 괴물은 앞(+Z)이나 뒤(-Z)에 놓고 플레이어 쪽을 보게 한다
    IEnumerator ChaseStage(CharacterController cc)
    {
        var st = stalker;
        var kb = InputSystem.AddDevice<Keyboard>("ChaseKeyboard");
        Vector3 P = new Vector3(0f, 0.1f, 10f);
        Vector3 fwd = Vector3.forward;
        float t;

        // ① 램프 켜고 8 m 앞 → alert. ② alert → chase 1.0 s
        lamp.lampOn = true;
        Teleport(cc, P, 0f);
        st.Teleport(P + fwd * 8f, 180f);
        t = 0f;
        while (st.state != Stalker.State.Alert && t < 2f) { t += Time.deltaTime; yield return null; }
        float tAlert = t;
        Check("stalker_sees_lamp_in_12m", st.state == Stalker.State.Alert && tAlert < 1f, $"alert after {tAlert:F2} s, sense {st.sense}, state {st.state}");
        t = 0f;
        while (st.state == Stalker.State.Alert && t < 3f) { t += Time.deltaTime; yield return null; }
        Check("alert_1s_before_chase", st.state == Stalker.State.Chase && t > 0.9f && t < 1.3f, $"chase after {t:F2} s (STALKER_ALERT_S {Tuning.STALKER_ALERT_S})");
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));

        // ③ 램프 끄고 같은 자리 → 모른다
        lamp.lampOn = false;
        yield return new WaitForSeconds(Tuning.LAMP_TOGGLE_TIME + 0.1f);
        st.Teleport(P + fwd * 8f, 180f);
        yield return new WaitForSeconds(2f);
        Check("stalker_blind_when_lamp_off", st.state != Stalker.State.Alert && st.state != Stalker.State.Chase && st.sense == "-", $"state {st.state}, sense {st.sense}");

        // ④ 램프 켜고 20 m → 빛. 2 s 에 배회 속도(2.5)로 4~6 m 다가온다
        lamp.lampOn = true;
        Vector3 from = P + fwd * 20f;
        st.Teleport(from, 180f);
        yield return new WaitForSeconds(2f);
        float moved = Flat(from - st.transform.position);
        Check("stalker_light_30m_slow_approach", st.state == Stalker.State.Investigate && moved > 3.5f && moved < 6.5f, $"moved {moved:F1} m in 2 s, state {st.state}, sense {st.sense}");
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));

        // ⑤ 5 m 뒤에서 걷는 플레이어를 7 s 안에 잡는다. ⑥ 검은 화면 → 3.0 s 뒤 복도 시작점 · 광석 0 · 괴물 북쪽 끝
        Teleport(cc, P, 0f);
        player.ore = 3;
        st.Teleport(P - fwd * 5f, 0f);
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
        int c0 = st.catches;
        t = 0f;
        while (st.catches == c0 && t < 8f) { t += Time.deltaTime; yield return null; }
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        float tCatch = t;
        Check("chase_catches_walker", st.catches == c0 + 1 && tCatch < 7f, $"caught after {tCatch:F1} s, state {st.state}");
        Vector3 blackV = default;
        yield return Capture("13_caught_black", v => blackV = v);      // 0.6 s 뒤 = 검은 화면 안
        int r0 = st.restarts;
        t = 0.6f;
        while (st.restarts == r0 && t < 5f) { t += Time.deltaTime; yield return null; }
        yield return null;
        float toStart = Flat(player.transform.position - st.restartPos);
        Check("catch_black_then_restart_3s", blackV.x < 0.02f && st.restarts == r0 + 1 && t > 2.7f && t < 3.4f && toStart < 0.5f && player.ore == 0 && !player.frozen && st.transform.position.z > st.zMax - 5f,
            $"black lum {blackV.x:F3}, restart at {t:F1} s, {toStart:F2} m from start, ore {player.ore}, frozen {player.frozen}, stalker z {st.transform.position.z:F1}");
        yield return new WaitForSeconds(Tuning.CATCH_FADE_OUT_S);

        // ⑦ 5 m 뒤에서 달리는 플레이어는 4 s 동안 안 잡힌다
        Teleport(cc, new Vector3(0f, 0.1f, 4f), 0f);
        player.stamina = Tuning.STAMINA_MAX;
        st.Teleport(new Vector3(0f, 0.1f, -1f), 0f);
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W, Key.LeftShift));
        c0 = st.catches;
        bool chased = false;
        for (t = 0f; t < 4f && st.catches == c0; t += Time.deltaTime) { chased |= st.state == Stalker.State.Chase; yield return null; }
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        Check("runner_escapes_4s", st.catches == c0 && chased, $"caught {st.catches != c0}, chased {chased}, gap {st.DistToPlayer:F1} m at 4 s");
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));

        // ⑧ 추격 중 램프 끄고 뒤로 빠지면 3.0 s 에 놓고, 마지막 본 자리로 가서 수색
        Teleport(cc, P, 0f);
        st.Teleport(P + fwd * 8f, 180f);
        t = 0f;
        while (st.state != Stalker.State.Chase && t < 3f) { t += Time.deltaTime; yield return null; }
        lamp.lampOn = false;
        Teleport(cc, P - fwd * 12f, 0f);
        t = 0f;
        while (st.state == Stalker.State.Chase && t < 5f) { t += Time.deltaTime; yield return null; }
        float tLose = t;
        while (st.state != Stalker.State.Search && t < 10f) { t += Time.deltaTime; yield return null; }
        float toLast = Flat(st.transform.position - P);
        Check("stalker_loses_after_3s", tLose > 2.7f && tLose < 3.6f && st.state == Stalker.State.Search && toLast < 3f, $"left chase at {tLose:F1} s, searching {toLast:F1} m from last seen, state {st.state}");
        lamp.lampOn = true;

        // ⑨ 어둠 적응 (사용자 09-15 "램프를 끄면 아무것도 안 보인다" → A, 값 6.4 는 사용자가 1/2 키로 찾음). 괴물은 끄고 북쪽 끝에 세운다 — 배회하며 화면에 들어오면 밝기가 2.5배 흔들렸다.
        // 램프는 0.2 s 켜서 적응을 풀고 끈다 (한 프레임만 켜면 안 풀렸다, 09-15)
        st.enabled = false;
        st.Teleport(st.homePos);
        Teleport(cc, P, 0f);
        lamp.lampOn = true;
        yield return new WaitForSeconds(0.2f);
        lamp.lampOn = false;
        Vector3 dark0 = default, adapted = default;
        yield return Capture("15_dark_0s", x => dark0 = x);
        float adapt0 = lamp.adapt;
        yield return new WaitForSeconds(Tuning.DARK_ADAPT_TIME);
        yield return Capture("15_dark_adapted", x => adapted = x);
        float fogNow = RenderSettings.fogDensity;
        Check("dark_adapt_shapes_visible", adapt0 < 0.3f && lamp.adapt >= 1f && adapted.x > dark0.x * 3f && adapted.x > 0.006f && adapted.x < 0.05f && Mathf.Abs(fogNow - Tuning.DARK_ADAPT_FOG) < 0.01f,
            $"lum off 0.6 s {dark0.x:F4} (adapt {adapt0:F2}) → adapted {adapted.x:F4} (6.4 → 0.012, allow 0.006~0.05; noadapt 0.0002), fog {fogNow:F2} (DARK_ADAPT_FOG {Tuning.DARK_ADAPT_FOG})");
        lamp.lampOn = true;
        yield return null;
        yield return null;
        Check("lamp_on_resets_adapt", lamp.adapt == 0f && Mathf.Abs(RenderSettings.fogDensity - Tuning.FOG_DENSITY) < 1e-4f, $"adapt {lamp.adapt:F2}, fog {RenderSettings.fogDensity:F3}");

        // ⑩ 괴물 눈 발광 (C): 램프 끄고 5 m 앞에 세운(꺼 둔) 괴물의 눈 영역 밝기
        yield return new WaitForSeconds(0.2f);
        lamp.lampOn = false;
        st.Teleport(P + fwd * 5f, 180f);
        // 3D-②b: 눈 구체가 없다 — 몸 화면 영역에서 밝기 0.1 넘는 표본 픽셀 수(발광 눈구멍)를 센다
        var look = st.GetComponentInChildren<StalkerLook>();
        var camMain = pickaxe.cam.GetComponent<Camera>();
        Vector3 eyes = default;
        Rect eyeRect = ScreenRect(camMain, look.Renderers);   // 몸 전체 — 어둠 속에서 0.1 을 넘는 건 발광 눈구멍뿐
        yield return Capture("16_eyes_in_dark", x => eyes = x, eyeRect);
        Check("stalker_eyes_glow_in_dark", eyeRect.width > 0f && lastBright >= Tuning.STALKER_EYE_BRIGHT_MIN, $"model region {eyeRect.width:F0}x{eyeRect.height:F0} px at 5 m: bright samples {lastBright} (min {Tuning.STALKER_EYE_BRIGHT_MIN}), lum {eyes.x:F3}, lamp off, adapt {lamp.adapt:F2}, eye emission {look.eyeEmission:F2}");
        lamp.lampOn = true;
        st.enabled = true;
    }

    // M3: 소음을 듣는 괴물. 포켓은 안 캐지게(health 1e6) 두고 소음만 낸다. 괴물 자리는 소리를 내기 직전에 놓는다 — 그 순간의 거리가 기준이다
    // 3D-①: 괴물 모델 miner_rigged (캡슐 대신). 램프 켜고 행동을 끈 채 갱도 가운데 앞 14·7·2 m 에 세워 찍고, 2 m 에서 4방향과 램프 좌우 20° 를 찍는다.
    // 형태·색 판정은 사용자 몫(캡처 13_monster_*). 여기서는 모델·동작·노멀이 들어왔는지, 밝기가 캡슐 때 기준 안인지, 분홍(재질 없음)·흰 점이 없는지만 잰다
    IEnumerator MonsterStage(CharacterController cc)
    {
        var st = stalker;
        st.enabled = false;
        lamp.lampOn = true;
        var mainCam = pickaxe.cam.GetComponent<Camera>();
        var model = st.transform.Find("Body/Model");
        bool modelOn = model != null && model.gameObject.activeInHierarchy;
        var anim = modelOn ? model.GetComponent<Animator>() : null;
        var skinMats = new List<Material>();
        if (modelOn)
            foreach (var r in model.GetComponentsInChildren<Renderer>())
                foreach (var m in r.sharedMaterials)
                    if (m != null && m.name.StartsWith("살")) skinMats.Add(m);
        yield return null;
        int clipCount = anim != null && anim.runtimeAnimatorController != null ? anim.runtimeAnimatorController.animationClips.Length : 0;
        bool idle = anim != null && anim.GetCurrentAnimatorStateInfo(0).IsName(Tuning.STALKER_MODEL_IDLE);
        bool normals = skinMats.Count > 0 && skinMats.TrueForAll(m => m.GetTexture("normalTexture") != null);
        Check("monster_model_animated_with_normals", modelOn && clipCount == 14 && idle && normals,
            $"model {(model == null ? "none" : modelOn ? "on" : "off")}, clips {clipCount} (want 14), playing {Tuning.STALKER_MODEL_IDLE} {idle}, skin materials {skinMats.Count} with normal map {normals}");

        var bodyR = modelOn ? model.GetComponentsInChildren<Renderer>() : st.GetComponentsInChildren<Renderer>();
        Vector3 P = new Vector3(0f, 0.1f, 3.5f);
        Teleport(cc, P, 0f);
        var vis = new Dictionary<float, Vector3>();
        var hid = new Dictionary<float, Vector3>();
        var rects = new Dictionary<float, Rect>();
        int magenta = 0;
        foreach (float dist in new[] { 14f, 7f, 2f })
        {
            st.Teleport(P + Vector3.forward * dist, 180f);        // 플레이어를 본다
            Rect r = default;
            Vector3 v = default, h = default;
            yield return Capture($"13_monster_at_{dist:0}m", x => v = x, default, () => r = ScreenRect(mainCam, bodyR));
            vis[dist] = v; rects[dist] = r; magenta += lastMagenta;
            // 같은 자리에서 모델을 숨기고 한 번 더 — 둘의 차이가 "보인다"의 잣대 (어두운 모델은 밝기만으로 바탕과 못 가른다)
            bool[] was = bodyR.Select(x => x.enabled).ToArray();
            foreach (var x in bodyR) x.enabled = false;
            yield return Capture($"13_monster_at_{dist:0}m_hidden", x => h = x, r);
            for (int k = 0; k < bodyR.Length; k++) bodyR[k].enabled = was[k];
            hid[dist] = h;
            Debug.Log($"MONSTER_VIS {dist:0} m lum {v.x:F4} (hidden {h.x:F4}) structure {v.y:F2} (hidden {h.y:F2}) burnt {v.z * 100f:F2} % magenta {lastMagenta} rect {r.width:F0}x{r.height:F0}");
        }
        float dLum7 = Mathf.Abs(vis[7f].x - hid[7f].x), dStr7 = vis[7f].y - hid[7f].y;
        Check("monster_dark_at_14m_visible_at_7m", rects[7f].width > 0f && vis[14f].x <= Tuning.STALKER_MODEL_LUM_MAX_14M && (dLum7 >= Tuning.STALKER_MODEL_CONTRAST_MIN_7M || dStr7 >= 3f),
            $"14 m lum {vis[14f].x:F3} (max {Tuning.STALKER_MODEL_LUM_MAX_14M}) · 7 m shown vs hidden: lum {vis[7f].x:F3}/{hid[7f].x:F3} Δ{dLum7:F3} (min {Tuning.STALKER_MODEL_CONTRAST_MIN_7M}), structure {vis[7f].y:F1}/{hid[7f].y:F1} Δ{dStr7:F1} (min 3) · 2 m lum {vis[2f].x:F3}");

        // 2 m 4방향 — 사용자가 뭉개진 곳을 표시할 캡처 (3D-②). yaw 180 = 플레이어를 본다. 이름은 플레이어가 보는 쪽 (yaw 90 = 모델이 +X 를 봄 → 왼쪽 옆구리가 보인다)
        string[] dirNames = { "front", "left", "right", "back" };
        float[] dirYaw = { 180f, 90f, 270f, 0f };
        for (int i = 0; i < 4; i++)
        {
            st.Teleport(P + Vector3.forward * 2f, dirYaw[i]);
            Vector3 v = default;
            yield return Capture($"13_monster_2m_{dirNames[i]}", x => v = x, default, () => ScreenRect(mainCam, bodyR));
            magenta += lastMagenta;
            Debug.Log($"MONSTER_2M {dirNames[i]} lum {v.x:F4} structure {v.y:F2} burnt {v.z * 100f:F2} % magenta {lastMagenta}");
            if (i == 0) vis[2.5f] = v;   // 정면 2 m 의 탄 픽셀 비율
        }
        Check("monster_no_magenta_no_burn", magenta == 0 && vis[2.5f].z < Tuning.STALKER_BURN_MAX, $"magenta pixels {magenta} (want 0), burnt at 2 m front {vis[2.5f].z * 100f:F2} % (max {Tuning.STALKER_BURN_MAX * 100f:F0} %)");
        // 3D-②b ⑧ 살 요철: 2 m 정면 구조값(이웃 밝기 차) — 점토 상태 24.6, 색→요철·잔결·거칠기 그림 뒤 올라야 한다. flatskin(노멀 뺌)이 FAIL
        Check("monster_skin_has_relief", vis[2.5f].y >= Tuning.STALKER_RELIEF_MIN, $"2 m front structure {vis[2.5f].y:F1} (min {Tuning.STALKER_RELIEF_MIN}), normal scale {st.GetComponentInChildren<StalkerLook>().normalScale:F2}");
        // 얼굴: 2 m 정면은 머리가 화면 위로 나간다(모델 키 3.7 m) — 30° 올려다보고 한 장 (Player.Look — 마우스와 같은 길)
        st.Teleport(P + Vector3.forward * 2f, 180f);
        float px = 1f / (Tuning.MOUSE_SENSITIVITY * Mathf.Rad2Deg);
        player.Look(new Vector2(0f, 30f * px));
        yield return Capture("13_monster_2m_face", x => { });
        // 램프 끄고 같은 자리 — 눈구멍 발광이 어둠에서 두 점으로 남는지 (사용자가 본다)
        lamp.lampOn = false;
        yield return new WaitForSeconds(Tuning.LAMP_TOGGLE_TIME + 0.1f);
        yield return Capture("13_monster_2m_face_dark", x => { });
        lamp.lampOn = true;
        yield return new WaitForSeconds(Tuning.LAMP_TOGGLE_TIME + 0.1f);
        player.Look(new Vector2(0f, -30f * px));

        // 3D-② ⑦ 살 얼룩: 2 m 정면 몸 밝기, 모델 그림자 켬 ÷ 끔 (URP 기본 편차 0.1·0.5 에서 0.58 — 살이 검게 지직거렸다, 사용자 09-17)
        float acne = 0f;
        yield return ShadowRatio("13_monster_2m_acne", bodyR, mainCam, x => acne = x);
        Check("monster_skin_no_acne", acne >= Tuning.STALKER_ACNE_MIN_RATIO, $"lum ratio shadows on/off {acne:F3} (min {Tuning.STALKER_ACNE_MIN_RATIO}) with bias depth {lamp.shadowDepthBias} normal {lamp.shadowNormalBias}");

        // 3D-② 부작용 확인: 편차를 키우면 그림자가 물체에서 떨어져 뜬다 — 바닥에 던진 곡괭이 밑 그림자를 3 m 뒤에서 찍는다 (사용자가 본다)
        st.Teleport(st.homePos);
        if (!pickaxe.hasPick) pickaxe.Return();
        var mouse = InputSystem.AddDevice<Mouse>("MonsterMouse");
        Teleport(cc, P, 0f);
        yield return null;
        yield return RightClick(mouse);
        float tw = 0f;
        var thrown = pickaxe.thrown;
        while (!thrown.Frozen && tw < Tuning.THROW_STUCK_S + 4f) { tw += Time.deltaTime; yield return null; }
        Vector3 land = thrown.transform.position;
        Teleport(cc, new Vector3(land.x, 0.1f, land.z - 3f), 0f);
        yield return Capture("13_shadow_contact", x => { });
        pickaxe.Return();
        InputSystem.RemoveDevice(mouse);

        // 그늘: 2 m 정면에서 램프(머리)를 왼쪽·오른쪽 20° 로 — 몸 영역의 구조값(이웃 밝기 차)을 기록한다. 문턱은 flatskin 실측 뒤 (제안서 ⑤)
        st.Teleport(P + Vector3.forward * 2f, 180f);
        float[] shade = new float[2];
        string[] side = { "left", "right" };
        for (int i = 0; i < 2; i++)
        {
            Teleport(cc, P, i == 0 ? -20f : 20f);
            Vector3 v = default;
            yield return Capture($"13_monster_2m_lamp_{side[i]}", x => v = x, default, () => ScreenRect(mainCam, bodyR));
            shade[i] = v.y;
        }
        // 09-17 실측: 노멀 있음 29.8/27.7 · flatskin 29.7/27.7 — 차이가 잡음 이하라 문턱을 못 세운다 (베이크한 노멀은 12만 면 몸이 이미 가진 요철이라 거의 안 보인다). 값만 남긴다
        Debug.Log($"MONSTER_SHADE structure lamp left {shade[0]:F2} · right {shade[1]:F2}");

        st.Teleport(st.homePos);
        Teleport(cc, P, 0f);
        st.enabled = true;
    }

    IEnumerator StalkerStage(CharacterController cc)
    {
        var st = stalker;
        var pockets = new List<OrePocket>(FindObjectsByType<OrePocket>(FindObjectsSortMode.None));
        pockets.Sort((a, b) => a.transform.position.z.CompareTo(b.transform.position.z));
        OrePocket south = pockets[0];
        OrePocket mid = pockets.Find(pk => pk.transform.position.z > 12f && pk.transform.position.z < 20f) ?? pockets[pockets.Count / 2];
        foreach (var pk in pockets) pk.health = 1e6f;
        var mouse = InputSystem.AddDevice<Mouse>("StalkerMouse");
        lamp.lampOn = true;

        // 0. 보이는가 — 캡슐 때 밝기 검사(12_stalker_at_*)는 3D-① 의 MonsterStage(13_monster_at_*, 그림/숨김 차이)로 옮겼다
        lamp.lampOn = false;                       // 귀 검사는 램프를 끄고 — M4 눈·빛이 끼어들지 않게 (램프 끄면 소리만 남는 것이 규칙이다)
        yield return new WaitForSeconds(Tuning.LAMP_TOGGLE_TIME + 0.1f);

        // 1. 30 m 밖 1타 → 안 듣는다
        StandAt(cc, south);
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));
        yield return null;
        float d0 = Flat(south.transform.position - st.transform.position);
        yield return Click(mouse);
        yield return new WaitForSeconds(2f);
        Check("stalker_ignores_beyond_25m", d0 > 30f && st.hits == 0 && st.state == Stalker.State.Wander, $"noise at {d0:F1} m, hits {st.hits}, state {st.state}");

        // 2. 20 m 안 1타 → 소리 쪽으로 한 칸(7 m)만 다가와 멈춘다
        StandAt(cc, mid);
        Vector3 from = new Vector3(0f, 0.1f, Mathf.Min(mid.transform.position.z + 20f, st.zMax));
        st.Teleport(from);
        yield return null;
        yield return Click(mouse);
        yield return new WaitForSeconds(3f);      // 7 m ÷ 4.0 = 1.75 s
        float moved = Flat(st.transform.position - from);
        float toPocket = Flat(mid.transform.position - st.transform.position);
        Check("stalker_one_hit_approaches_7m", st.hits == 1 && moved > 5f && moved < 9f && toPocket > 5f && st.state == Stalker.State.Search,
            $"moved {moved:F1} m, {toPocket:F1} m from pocket, state {st.state}");

        // 3. 20 m 안 2타 연속 → 그 자리(2 m 안)까지 온다
        yield return new WaitForSeconds(Tuning.STALKER_HEAR_CONFIRM_S);   // 앞 소리와 이어지지 않게
        st.Teleport(from);
        yield return null;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(Tuning.MINE_COOLDOWN * 1.6f);      // 2타
        InputSystem.QueueStateEvent(mouse, new MouseState());
        // 길을 비켜 남쪽 4 m 에서 포켓 쪽을 본다 — 괴물이 플레이어 몸에 막히지 않게, 오는 장면을 찍는다
        Teleport(cc, new Vector3(-Mathf.Sign(mid.transform.position.x) * 1.0f, 0.1f, mid.transform.position.z - 4f), 0f);
        float t = 0f;
        while (st.state != Stalker.State.Search && t < 8f) { t += Time.deltaTime; yield return null; }
        toPocket = Flat(mid.transform.position - st.transform.position);
        Check("stalker_two_hits_arrives_2m", st.hits == 2 && st.state == Stalker.State.Search && toPocket < Tuning.STALKER_FOUND_M && t < 6f,
            $"hits {st.hits}, {toPocket:F2} m from pocket after {t:F1} s, state {st.state}");
        Teleport(cc, new Vector3(0f, 0.1f, st.zMin + 1f), 0f);    // 수색 길에서 비킨다

        // 4. 2~3곳을 2 s 씩 들여다본 뒤 배회로 돌아간다. 수색 곳이 우연히 플레이어 2 m 안이면 들키는 게(found) 규칙이라 그것도 통과로 친다
        t = 0f;
        bool found = false;
        while (st.state == Stalker.State.Search && t < 40f) { t += Time.deltaTime; found |= st.sense == "found"; yield return null; }
        Check("stalker_searches_2to3_spots_then_wanders", found || (st.state == Stalker.State.Wander && st.spotsVisited >= Tuning.STALKER_SPOTS_MIN && st.spotsVisited <= Tuning.STALKER_SPOTS_MAX),
            $"spots {st.spotsVisited}, state {st.state} after {t:F1} s{(found ? ", found player within 2 m" : "")}");

        // 5. 도착 장면 캡처 (램프 켜고) — 2타로 다시 부른 뒤 4 m 남쪽에서 본다
        StandAt(cc, mid);
        st.Teleport(from);
        yield return null;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(Tuning.MINE_COOLDOWN * 1.6f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
        Teleport(cc, new Vector3(-Mathf.Sign(mid.transform.position.x) * 1.0f, 0.1f, mid.transform.position.z - 4f), 0f);
        t = 0f;
        while (st.state != Stalker.State.Search && t < 8f) { t += Time.deltaTime; yield return null; }
        lamp.lampOn = true;
        yield return Capture("11_stalker_arrived", v => { });
    }

    IEnumerator RightClick(Mouse mouse)
    {
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Right));
        yield return new WaitForSeconds(0.05f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
        yield return null;
    }

    IEnumerator PressKey(Keyboard kb, Key key)
    {
        InputSystem.QueueStateEvent(kb, new KeyboardState(key));
        yield return new WaitForSeconds(0.05f);
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        yield return null;
    }

    IEnumerator Click(Mouse mouse)
    {
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(0.05f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
    }

    void StandAt(CharacterController cc, OrePocket pk)
    {
        Vector3 at = pk.transform.position + pk.outDir * 1.8f;
        at.y = 0.1f;
        Teleport(cc, at, Quaternion.LookRotation(-pk.outDir).eulerAngles.y);
    }

    // 값 고르기용 측정: 가까운 면 감광(기준 거리·지수)마다 갱도(z 17.5, +Z)와 벽 앞 화면. 판정이 아니라 숫자 표를 남긴다
    // 3D-②: 2 m 정면 몸 영역 밝기 — 모델 그림자 켬 ÷ 끔. 1.0 = 얼룩 없음. 캡처 이름 name(켬)·name_noshadow(끔)
    IEnumerator ShadowRatio(string name, Renderer[] bodyR, Camera mainCam, Action<float> result)
    {
        Vector3 on = default, off = default;
        Rect r = default;
        yield return Capture(name, x => on = x, default, () => r = ScreenRect(mainCam, bodyR));
        var was = bodyR.Select(x => x.shadowCastingMode).ToArray();
        foreach (var x in bodyR) x.shadowCastingMode = ShadowCastingMode.Off;
        yield return Capture(name + "_noshadow", x => off = x, r);
        for (int k = 0; k < bodyR.Length; k++) bodyR[k].shadowCastingMode = was[k];
        float ratio = off.x > 0f ? on.x / off.x : 0f;
        Debug.Log($"SHADOW_RATIO {name} lum on {on.x:F4} off {off.x:F4} ratio {ratio:F3} structure on {on.y:F1} off {off.y:F1}");
        result(ratio);
    }

    // `-sweep -bias`: 헤드램프 그림자 편차 조합을 돌며 2 m 정면 살 얼룩 비율을 잰다 → Tuning.LAMP_SHADOW_*_BIAS 를 고른다 (제안서 3D-②)
    IEnumerator BiasSweep()
    {
        yield return new WaitForSeconds(1.5f);
        var cc = player.GetComponent<CharacterController>();
        var st = stalker;
        st.enabled = false;
        lamp.lampOn = true;
        var mainCam = pickaxe.cam.GetComponent<Camera>();
        var bodyR = st.transform.Find("Body/Model").GetComponentsInChildren<Renderer>();
        Vector3 P = new Vector3(0f, 0.1f, 3.5f);
        Teleport(cc, P, 0f);
        st.Teleport(P + Vector3.forward * 2f, 180f);
        // 1차(09-17): 깊이 {0.1,0.3,0.6,1.0} × 법선 {0.5,1,2} — 법선을 키우면 나빠진다(0.5→2.0: 0.58→0.31), 깊이는 도움(1.0·0.5 = 0.879). 2차: 깊이 더 · 법선 더 작게
        foreach (float depth in new[] { 1.0f, 1.5f, 2.0f })
            foreach (float normal in new[] { 0f, 0.25f, 0.5f })
            {
                lamp.shadowDepthBias = depth; lamp.shadowNormalBias = normal; lamp.ApplyShadowBias();
                yield return null;
                float ratio = 0f;
                yield return ShadowRatio($"sweep_bias_d{depth:0.0}_n{normal:0.0}", bodyR, mainCam, x => ratio = x);
                Debug.Log($"SWEEP bias depth {depth:0.0} normal {normal:0.0} ratio {ratio:F3}");
            }
        Debug.Log("CHECK ALL PASS");
        Application.Quit(0);
    }

    IEnumerator Sweep()
    {
        yield return new WaitForSeconds(1.5f);
        var cc = player.GetComponent<CharacterController>();
        foreach (var (reference, pow) in new[] { (4f, 0f), (2f, 1.4f), (3f, 1.4f), (4f, 1.4f), (4f, 1.0f), (6f, 1.4f) })
        {
            lamp.nearRef = reference;
            lamp.nearPow = pow;
            Vector3 far = default, near = default;
            Teleport(cc, new Vector3(0f, 0.1f, 17.5f), 0f);
            yield return Capture($"sweep_far_r{reference:0}_p{pow:0.0}", v => far = v);
            float farDim = lamp.nearDim;
            Teleport(cc, NearWallPos, 90f);
            yield return Capture($"sweep_near_r{reference:0}_p{pow:0.0}", v => near = v);
            Debug.Log($"SWEEP ref {reference:0} pow {pow:0.0} lamp {lamp.energy} | tunnel dim {farDim:F2} lum {far.x:F4} burnt {far.z * 100f:F1} % | near wall dim {lamp.nearDim:F3} lum {near.x:F3} burnt {near.z * 100f:F1} %");
        }
        Debug.Log("CHECK ALL PASS");
        Application.Quit(0);
    }

    void Teleport(CharacterController cc, Vector3 pos, float yaw)
    {
        cc.enabled = false;
        player.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f));
        cc.enabled = true;
    }

    void Finish()
    {
        string summary = fails.Count == 0 ? "CHECK ALL PASS" : "CHECK FAILED: " + string.Join(", ", fails);
        Debug.Log(summary);
        Application.Quit(fails.Count == 0 ? 0 : 1);
    }

    void Check(string name, bool ok, string value)
    {
        Debug.Log($"CHECK {(ok ? "PASS" : "FAIL")} {name} {value}");
        if (!ok) fails.Add(name);
    }

    static float Flat(Vector3 v) => new Vector2(v.x, v.z).magnitude;
    static Vector3 Flat3(Vector3 v) => new Vector3(v.x, 0f, v.z);

    static float ListenerRms(float[] buffer)
    {
        AudioListener.GetOutputData(buffer, 0);
        double sum = 0;
        foreach (float v in buffer) sum += v * v;
        return Mathf.Sqrt((float)(sum / buffer.Length));
    }

    // 렌더러들이 화면에서 차지하는 사각형 (픽셀, 왼쪽 아래 원점)
    static Rect ScreenRect(Camera cam, Renderer[] renderers)
    {
        Vector2 min = new Vector2(float.MaxValue, float.MaxValue), max = new Vector2(float.MinValue, float.MinValue);
        foreach (var r in renderers)
        {
            Bounds b = r.bounds;
            for (int i = 0; i < 8; i++)
            {
                Vector3 corner = b.center + Vector3.Scale(b.extents, new Vector3((i & 1) * 2 - 1, (i >> 1 & 1) * 2 - 1, (i >> 2 & 1) * 2 - 1));
                Vector3 p = cam.WorldToScreenPoint(corner);
                if (p.z <= 0f) continue;
                min = Vector2.Min(min, p);
                max = Vector2.Max(max, p);
            }
        }
        min = Vector2.Max(min, Vector2.zero);
        max = Vector2.Min(max, new Vector2(Screen.width, Screen.height));
        return max.x > min.x && max.y > min.y ? Rect.MinMaxRect(min.x, min.y, max.x, max.y) : default;
    }

    // x = 평균 밝기(sRGB 휘도 0~1), y = 구조(이웃 픽셀 밝기 차 평균 × 1000), z = 하얗게 탄 픽셀 비율(BurntLum 위). region 이 있으면 그 안만
    // regionAt 은 찍는 순간에 영역을 다시 잰다 — 움직이는 것(괴물)은 0.6 s 기다리는 동안 자리가 바뀐다
    IEnumerator Capture(string name, Action<Vector3> result, Rect region = default, Func<Rect> regionAt = null)
    {
        yield return new WaitForSeconds(0.6f);        // 램프 페이드·안개 누적·램프 늦게 따라오기가 끝나게
        if (regionAt != null) region = regionAt();
        yield return new WaitForEndOfFrame();
        var tex = ScreenCapture.CaptureScreenshotAsTexture();
        File.WriteAllBytes(Path.Combine(outDir, name + ".png"), tex.EncodeToPNG());
        Color32[] px = tex.GetPixels32();
        int w = tex.width, h = tex.height;
        Destroy(tex);
        int x0 = 0, y0 = 0, x1 = w - 1, y1 = h - 1;
        if (region.width > 0f)
        {
            x0 = Mathf.Clamp((int)region.xMin, 0, w - 2);
            y0 = Mathf.Clamp((int)region.yMin, 0, h - 2);
            x1 = Mathf.Clamp((int)region.xMax, x0 + 1, w - 1);
            y1 = Mathf.Clamp((int)region.yMax, y0 + 1, h - 1);
        }
        double sum = 0, grad = 0;
        int n = 0, burnt = 0, magenta = 0, bright = 0;
        for (int y = y0; y < y1; y += 3)
            for (int x = x0; x < x1; x += 3)
            {
                var c = px[y * w + x];
                float l = Lum(c);
                sum += l;
                n++;
                if (l > BurntLum) burnt++;
                if (c.r > 200 && c.b > 200 && c.g < 80) magenta++;   // 재질 없음 표시(분홍) — glTF 텍스처를 못 읽으면 뜬다
                if (l > 0.1f) bright++;
                grad += Mathf.Abs(Lum(px[y * w + x + 1]) - l) + Mathf.Abs(Lum(px[(y + 1) * w + x]) - l);
            }
        n = Mathf.Max(n, 1);
        lastMagenta = magenta;
        lastBright = bright;
        result(new Vector3((float)(sum / n), (float)(grad / n * 1000.0), (float)burnt / n));
    }
    int lastMagenta;   // 마지막 Capture 영역에서 3픽셀 간격으로 센 분홍 픽셀 수
    int lastBright;    // 마지막 Capture 영역에서 3픽셀 간격으로 센 밝기 0.1 넘는 픽셀 수 (어둠 속 눈 발광)

    static float Lum(Color32 c) => (0.2126f * c.r + 0.7152f * c.g + 0.0722f * c.b) / 255f;

    static IEnumerator MeasureFps(float seconds, Action<float> result)
    {
        float t = 0f;
        int frames = 0;
        while (t < seconds)
        {
            yield return null;
            t += Time.unscaledDeltaTime;
            frames++;
        }
        result(frames / t);
    }
}
