using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;

// 배포물 검사. exe 를 -check 로 띄우면 돌고, 로그에 "CHECK PASS|FAIL 이름 값" 을 쓰고 종료 코드로 알린다.
// 입력은 가상 키보드·마우스 장치로 넣는다 — Player·Pickaxe 는 사람 장치와 같은 길(Keyboard.current / Mouse.current)로 읽는다.
// -only booth 은 부스 맵(MAP2) 씬 검사만 — 전체 실행은 인트로 → 부스 맵 → 복도 차례로 돈다. -only repair 는 부스 맵의 REP-1 고칠 곳만.
// -only m1|mining|monster|stalker|chase|retreat|anim|throw|pick|tired|hud|sound|intro|props 은 그 구간만 돈다 (intro 는 씬을 떠나므로 늘 마지막; 인트로 씬 쪽 검사는 Intro.cs) (고치는 중에는 바뀐 구간만, 커밋 전에는 전체).
// -sabotage floor|lamp|fog|thickfog|nodim|bury|onehit|spam|nomagnet|noassist|noviewmodel|picklamp|mute|deaf|bigears|ghost|blind|slowchase|nolose|noadapt|dimeyes|tank|noretreat|softretreat|stunlock|lurechase|nopickup|twopicks|flatsteps|quietfeet|rockflesh|nodull|steadyhands|everlasting|flatnod|nostagger|hudtext|noglow|ballpick|hudon|noanim|slide|uprightclimb|armsink|nopreview|oldwalk|oldrun|bouncy|stiffspine|straightfingers|shutjaw|stiffneck|shortneck|flatprops|skipearly|norestart|alwayslamp|nolamp|nogap|bigprop|nomat|renametmb|blockcut|blockleak|nonav|tallcap|bigmonster|nocol|smallmap|nohub|nosidings|nofakeexit|monsterfloat|crevshift|squeezelong|nicheplug|instantfix|silentfix|nobreak 는 검사가 FAIL 을 내는지 확인하는 용도다.
// -sweep 은 검사 대신 가까운 면 감광 값을 바꿔 가며 갱도·벽 앞 화면 값을 "SWEEP" 줄로 남긴다.
public class M1Check : MonoBehaviour
{
    // 걸음 클립마다 모으는 표본 (anim 구간의 Sample 이 채운다)
    class GaitAcc
    {
        public int frames, lifts;
        public int[] handOn = new int[2];
        public float sh, hip, reach, rawMin = 99f;                         // reach = 두 손이 가슴보다 앞선 거리의 합 (몸 앞 방향, 게임 m)
        public List<float> rates = new List<float>(), chest = new List<float>(), pelvis = new List<float>(), headYaw = new List<float>();
        public List<float[]> heights = new List<float[]>();                 // 두 손 발톱 끝 · 두 발끝의 바닥 위 높이
        public float Med(List<float> l) => l.Count > 0 ? l.OrderBy(v => v).ElementAt(l.Count / 2) : 0f;
        public float Range(List<float> l) => l.Count > 0 ? l.Max() - l.Min() : 0f;
        public float Sd(List<float> l) { if (l.Count == 0) return 99f; float m = l.Average(); return Mathf.Sqrt(l.Average(v => (v - m) * (v - m))); }
        public int Airborne(float above)                                     // 네 손발이 모두 제 가장 낮은 높이 + above 위에 뜬 프레임
        {
            if (heights.Count == 0) return 0;
            var min = Enumerable.Range(0, 4).Select(i => heights.Min(h => h[i])).ToArray();
            return heights.Count(h => Enumerable.Range(0, 4).All(i => h[i] > min[i] + above));
        }
    }

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
    public static readonly List<string> fails = new List<string>();   // static: Intro 씬(UI-2)의 검사도 여기 쌓고, 씬이 바뀌어도 남는다
    bool noRestart;                                                     // 사보타주 norestart: 잡혀도 인트로로 안 간다 (UI-2 전 상태)
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
        if (sabotage == "nosnap")               // 비탈을 내려갈 때 바닥에 안 붙인다 — 발소리가 프레임마다 나던(09-24 전) 상태
            player.snapDown = false;
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
        var sanim = stalker.GetComponentInChildren<StalkerAnim>();
        if (sabotage == "noanim" && sanim != null)       // 3D-③ 전 상태: 무엇을 하든 idle_crouch 하나
            sanim.enabled = false;
        if (sabotage == "slide" && sanim != null)        // 동작 빠르기를 늘 1배 — 발이 미끄러진다
            sanim.rateMatch = false;
        if (sabotage == "uprightclimb" && sanim != null) // 벽타기 때 몸을 안 세운다
            sanim.tiltClimb = false;
        if (sabotage == "armsink" && sanim != null)      // 팔 들어 올리기 끔 — run·crawl 손가락이 바닥·벽 속 0.5 m
            sanim.clampArms = false;
        if (sabotage == "oldwalk" && sanim != null)      // 3D-③b M1 전 상태: 걸음 D 가 옛 walk_crouch (×3.63 잔걸음)
            sanim.oldWalk = true;
        if (sabotage == "oldrun" && sanim != null)       // 3D-③b M2 전 상태: 달리기가 옛 run (손목째 바닥 밑 → 팔 들기)
            sanim.oldRun = true;
        if (sabotage == "bouncy" && sanim != null)       // 3D-③b M2b 전 상태: 빠른 걸음이 뜀박질 run_knuckle (몸이 튀고 공중에 뜬다)
            sanim.bouncy = true;
        if (sabotage == "roarback" && sanim != null)     // 3D-④ 5b 전 상태: 미끄러지는 네 발 걸음 + 제자리 포효 + 휘두르기
            sanim.gait = 4;
        if (sabotage == "stillhands" && sanim != null)   // 손가락이 안 움직인다
            sanim.driveFingers = false;
        if (sabotage == "stifftorso" && sanim != null)   // 머리를 돌려도 상체가 안 따라간다 (영상 U3 "일시정지 같다")
            sanim.driveTorso = false;
        if (sabotage == "noimpact" && sanim != null)     // 발을 디뎌도 화면이 안 흔들린다
            sanim.stomp = false;
        if (sabotage == "solidgap")                      // 3D-④ MR1 맵: 벽 틈 입구가 막혀 있다 (충돌 벽을 안 판 조각과 같다)
            foreach (var back in pieces.GetComponentsInChildren<MeshCollider>().Where(c => c.name.StartsWith("COL_gap_back")))
            {
                var plug = new GameObject("SabotagePlug").AddComponent<BoxCollider>();
                plug.transform.position = new Vector3(Mathf.Sign(back.bounds.center.x) * (Tuning.TUNNEL_WALL_X + 0.5f), 1.5f, back.bounds.center.z);
                plug.size = new Vector3(0.6f, 3f, 2f);
            }
        propsSabotage = sabotage;                        // A1 소품: bigprop(기둥·곡괭이 2배) · nomat(소품 재질 없음 → 분홍) · renametmb(기둥 이름 바꿈) — PropsStage 가 건다
        if (sabotage == "nogrope")                       // 3D-④ MB 전 상태: 수색 첫 자리에서도 서서 둘러보기만
            stalker.grope = false;
        if (sabotage == "clawhands" && sanim != null)    // 짚을 때 손가락을 안 편다 (영상 B2 판정 "전부 펴졌으면" 전)
            sanim.flatHands = false;
        if (sabotage == "nohear")                        // 더듬다 소리를 들어도 안 굳고 바로 간다 ("들었나?" 없음)
            stalker.heardPause = false;
        if (sabotage == "handfind")                      // 손보다 멀리까지 찾는다 (규칙 = 손 닿는 2.5 m, 사용자 MB 판정 09-20)
            stalker.foundM = 3.0f;
        if (sabotage == "shortfind")                     // 옛 2 m 규칙: 손이 닿는 2.3 m 에 있어도 안 들킨다
            stalker.foundM = 2.0f;
        if (sabotage == "stiffspine" && sanim != null)   // 배회가 허리가 옆으로 안 휘는 walk_knuckle
            sanim.stiffSpine = true;
        if (sabotage == "straightfingers" && sanim != null)   // 3D-③b M1b 전 상태: 손가락 곧음
            sanim.straightFingers = true;
        if (sabotage == "shutjaw" && sanim != null)      // 3D-③b M1c 전 상태: 턱이 안 움직인다
            sanim.driveJaw = false;
        flatProps = sabotage == "flatprops";
        if (sabotage == "stiffneck" && sanim != null)    // 3D-③b M1d 전 상태: 머리가 동작 그대로 (몸과 같이 돈다)
            sanim.driveHead = false;
        if (sabotage == "shortneck" && sanim != null)    // 3D-③b M1e 전 상태: 목이 안 나온다 (마디 뼈는 가슴 뼈에 굳은 채)
            sanim.driveNeck = false;
        if (sabotage == "nopreview" && hud != null)     // U 가 세운 괴물을 안 걸린다 (사용자 09-18 "U 가 적용 안 된다" 상태)
            hud.previewOn = false;
        noRestart = sabotage == "norestart";
        if (sabotage == "alwayslamp" || sabotage == "nolamp" || sabotage == "nogap")   // m3-③ M1 램프 미끼: 안 꺼짐 · 안 켜짐 · 어둠 없이 바로 눈
        {
            var lk = stalker.GetComponentInChildren<StalkerLook>();
            lk.sabAlwaysLamp = sabotage == "alwayslamp"; lk.sabNoLamp = sabotage == "nolamp"; lk.sabNoGap = sabotage == "nogap";
        }
        if (sabotage == "dimeyes")              // 괴물 눈 발광 끔 (3D-②b: 눈구멍 발광 0)
        {
            var lk = stalker.GetComponentInChildren<StalkerLook>(); lk.eyeEmission = 0f; lk.Apply();
        }
        Debug.Log($"CHECK start sabotage='{sabotage}' only='{only}' sweep={sweep} scene {SceneManager.GetActiveScene().name} screen {Screen.width}x{Screen.height}");
        sabotageName = sabotage;
        if (SceneManager.GetActiveScene().name == Tuning.BOOTH_SCENE)
        {
            StartCoroutine(BoothRun());
            return;
        }
        StartCoroutine(sweep ? (Array.IndexOf(args, "-bias") >= 0 ? BiasSweep() : Sweep()) : Run(fog));
    }

    IEnumerator Run(VolumetricFogVolumeComponent fog)
    {
        var cc = player.GetComponent<CharacterController>();
        stalker.enabled = false;                 // 괴물 무관 구간은 괴물을 끈다 (DevHud 0 키와 같다) — 켜 두면 램프 빛을 보고 와서 잡는다
        stalker.returnToIntro = false;           // 잡힘은 옛 제자리 재시작으로 — 다른 구간이 씬을 안 떠나게. intro 구간만 진짜 길
        yield return new WaitForSeconds(1.5f);   // 바닥에 내려앉는다
        if (only == "" || only == "m1")
            yield return M1(cc, fog);
        if (only == "" || only == "mining")
            yield return Mining(cc);
        if (only == "" || only == "map")
            yield return MapStage(cc);
        if (only == "props" || (only == "" && Tuning.PIECE_SUFFIX != ""))   // A1 소품이 켜져 있을 때만 (09-23 판정 불통과로 옛 조각으로 되돌림 — -only props 는 언제든 직접)
            yield return PropsStage(cc);
        stalker.enabled = true;
        if (only == "" || only == "monster")
            yield return MonsterStage(cc);
        if (only == "" || only == "stalker")
            yield return StalkerStage(cc);
        if (only == "" || only == "lure")
            yield return LureStage(cc);
        if (only == "" || only == "chase")
            yield return ChaseStage(cc);
        if (only == "" || only == "retreat")
            yield return RetreatStage(cc);
        if (only == "" || only == "anim")
            yield return AnimStage(cc);
        if (only == "" || only == "anim" || only == "grope")
            yield return GropeStage(cc);
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
        if (only == "" || only == "intro")
        {
            yield return IntroStage(cc);         // 씬을 떠난다 — 통과면 Intro.Start 가 Finish 한다, 안 떠나면 IntroStage 가
            yield break;
        }
        Finish();
    }

    // ================= 부스 한 층 맵 MAP2 (제안서 docs/제안서_MAP2_맵_5배.md · MAP1 은 docs/제안서_MAP1_부스_갱도_모양.md). 끝나면 전체 실행은 복도 씬으로 넘어간다
    string sabotageName = "";

    IEnumerator BoothRun()
    {
        var cc = player.GetComponent<CharacterController>();
        stalker.enabled = false;
        stalker.returnToIntro = false;
        Check("booth_scene_loaded", SceneManager.GetActiveScene().name == Tuning.BOOTH_SCENE && NavMesh.CalculateTriangulation().indices.Length > 0,
            $"scene {SceneManager.GetActiveScene().name} (from intro start: {only == ""}) · navmesh tris {NavMesh.CalculateTriangulation().indices.Length / 3}");
        yield return new WaitForSeconds(1.5f);
        if (only != "repair")
            yield return BoothStage(cc);
        if (only == "" || only == "repair")
            yield return RepairStage(cc);
        if (only == "")
        {
            SceneManager.LoadScene("M1_Tunnel");                // 복도 씬의 M1Check 가 나머지 구간을 잇는다 (fails 는 static)
            yield break;
        }
        Finish();
    }

    // ================= REP-1 고칠 곳 (제안서 docs/제안서_REP1_고칠_곳.md, 승인 09-26)
    // ① 망가진 갱목 앞에서 E 를 8 s 누르면 고쳐지고 돈이 값만큼 ② 4 s 누르고 떼었다 다시 → 진행이 남는다 ③ 고치는 동안 종류 반경의 소리(갱목 25 m · 전등 4 m), 전등은 켜진다
    // ④ 판 중에 멀쩡한 곳이 망가진다, 20 m 안은 안 ⑤ 판 시작 30 %. 사보타주: instantfix(시간 0 → ①②) · silentfix(소리 없음 → ③) · nobreak(판 중 안 망가짐 → ④)
    IEnumerator RepairStage(CharacterController cc)
    {
        var dir = FindFirstObjectByType<RepairDirector>();
        var all = Repairable.All.ToList();
        if (dir == null || all.Count == 0)
        {
            Check("repair_spots_all_kinds", false, $"director {dir != null} · spots {all.Count}");
            yield break;
        }
        if (sabotageName == "instantfix") Repairable.timeMul = 0f;
        if (sabotageName == "silentfix") Repairable.noiseMul = 0f;
        if (sabotageName == "nobreak") dir.enabled = false;
        var kb = InputSystem.AddDevice<Keyboard>("RepairKeyboard");
        string kinds = string.Join(" ", all.GroupBy(r => r.kind).OrderBy(g => g.Key).Select(g => $"{g.Key} {g.Count()}"));
        Check("repair_spots_all_kinds", all.Select(r => r.kind).Distinct().Count() == 7 && all.Count >= 30, $"{all.Count} spots · {kinds}");
        int lamps = all.Count(r => r.kind == "lamp"), want = Mathf.RoundToInt((all.Count - lamps) * Tuning.REP_BROKEN_START);
        Check("repair_start_broken_30pct", Mathf.Abs(dir.startBroken - want) <= 1 && dir.lampsStart == lamps,
            $"{dir.startBroken}/{all.Count - lamps} non-lamp broken at start (want {want} = {Tuning.REP_BROKEN_START * 100f:0} %) · dead lamps broken {dir.lampsStart}/{lamps} (want all — MAP2 dark zones)");
        bool FarFromCrevice(Repairable r) => Crevice.All.All(c => Vector3.Distance(c.path[0], r.standAt) > 3f);   // E 가 틈 비집기로 가지 않게
        IEnumerator StandAt(Repairable r)
        {
            cc.enabled = false;
            player.transform.position = r.standAt + Vector3.up * 0.1f;
            Vector3 d = r.focus - r.standAt; d.y = 0f;
            player.transform.rotation = Quaternion.LookRotation(d);
            cc.enabled = true;
            yield return new WaitForSeconds(0.5f);
        }
        IEnumerator HoldE(float s)
        {
            InputSystem.QueueStateEvent(kb, new KeyboardState(Key.E));
            yield return new WaitForSeconds(s);
            InputSystem.QueueStateEvent(kb, new KeyboardState());
            yield return null;
        }
        var noises = new List<float>();
        void OnNoise(Vector3 at, float radius, string kind, object who) { if (kind == "repair") noises.Add(radius); }
        NoiseBus.Made += OnNoise;

        // ① 갱목 8 s
        var tim = all.Where(r => r.kind == "timber" && FarFromCrevice(r)).OrderBy(r => Vector3.Distance(r.standAt, player.transform.position)).First();
        tim.Break();
        yield return StandAt(tim);
        float money0 = Economy.Repair;
        noises.Clear();
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.E));
        yield return new WaitForSeconds(7.0f);
        bool held = player.Repairing, at7 = tim.broken;
        float prog7 = tim.progress;
        yield return new WaitForSeconds(1.3f);
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        yield return null;
        bool at83 = !tim.broken;
        float paid = Economy.Repair - money0;
        Check("repair_timber_hold_8s", held && at7 && at83,
            $"repairing while holding E {held} · still broken at 7.0 s {at7} (progress {prog7 * 100f:0} %) · fixed at 8.3 s {at83} (want {Tuning.RepairTime("timber"):0} s) at {tim.name}");
        Check("repair_pays_value", tim.Value > 0f && Mathf.Abs(paid - tim.Value) < 0.5f,
            $"paid {paid:0.0} (want {tim.Value:0.0} = ore {Tuning.ORE_VALUE:0} x {Tuning.RepairTime("timber"):0} s / {Tuning.MINE_TIME_REF} s / {Tuning.ORE_OVER_REPAIR})");
        int timberNoises = noises.Count;
        float timberR = noises.Count > 0 ? noises.Max() : 0f;

        // ② 떼도 진행이 남는다
        tim.Break();
        yield return HoldE(4.0f);
        yield return new WaitForSeconds(1.0f);
        float kept = tim.progress;
        bool stillBroken = tim.broken;
        yield return HoldE(4.3f);
        Check("repair_progress_kept", stillBroken && kept > 0.4f && kept < 0.6f && !tim.broken,
            $"after 4 s hold + 1 s release: broken {stillBroken} progress {kept * 100f:0} % (want ~50) · after 4.3 s more fixed {!tim.broken}");

        // ③ 소리 반경은 종류마다 · 전등은 고치면 켜진다
        var lampR = all.Where(r => r.kind == "lamp" && FarFromCrevice(r)).OrderBy(r => Vector3.Distance(r.standAt, player.transform.position)).First();
        lampR.Break();
        yield return StandAt(lampR);
        noises.Clear();
        yield return HoldE(Tuning.RepairTime("lamp") + 0.4f);
        float lampRad = noises.Count > 0 ? noises.Max() : 0f;
        Check("repair_noise_by_kind", timberNoises >= 5 && Mathf.Approximately(timberR, Tuning.RepairNoise("timber")) && noises.Count >= 2 && Mathf.Approximately(lampRad, Tuning.RepairNoise("lamp")),
            $"timber 8.3 s: {timberNoises} noises max {timberR:0} m (want >=5 · {Tuning.RepairNoise("timber"):0} m) · lamp: {noises.Count} noises max {lampRad:0} m (want {Tuning.RepairNoise("lamp"):0} m)");
        Check("repair_lamp_lights", lampR.lampLight != null && lampR.lampLight.enabled && !lampR.broken,
            $"fixed lamp {lampR.name}: light {(lampR.lampLight != null && lampR.lampLight.enabled ? "on" : "off")} · broken {lampR.broken}");
        NoiseBus.Made -= OnNoise;

        // ④ 판 중에 망가진다 (간격을 1 s 로 당겨 본다) — 20 m 안은 안
        int before = dir.brokeLater;
        float every = dir.breakEvery;
        dir.minBreakDist = 999f;
        dir.breakEvery = 1.0f;
        dir.timer = 0.5f;
        yield return new WaitForSeconds(2.7f);
        int broke = dir.brokeLater - before;
        Check("repair_breaks_over_time_far", broke >= 2 && dir.minBreakDist > Tuning.REP_BREAK_MIN_M,
            $"{broke} broke in 2.7 s at 1 s interval (want >=2) · nearest {dir.minBreakDist:0.0} m from player (want > {Tuning.REP_BREAK_MIN_M:0} m)");
        dir.breakEvery = every;
        dir.timer = every;
        Repairable.timeMul = 1f;
        Repairable.noiseMul = 1f;
        InputSystem.RemoveDevice(kb);
    }

    Transform Slot(string name) => pieces.GetComponentsInChildren<Transform>(true).First(t => t.name == name);
    static Vector3 OnNav(Vector3 p, float r = 4f) => NavMesh.SamplePosition(p, out NavMeshHit h, r, NavMesh.AllAreas) ? h.position : p;
    static float PathLen(Vector3 a, Vector3 b)
    {
        var path = new NavMeshPath();
        if (!NavMesh.CalculatePath(OnNav(a), OnNav(b), NavMesh.AllAreas, path) || path.status != NavMeshPathStatus.PathComplete) return -1f;
        float L = 0f;
        for (int i = 1; i < path.corners.Length; i++) L += Vector3.Distance(path.corners[i - 1], path.corners[i]);
        return L;
    }

    IEnumerator BoothStage(CharacterController cc)
    {
        var kb = InputSystem.AddDevice<Keyboard>("BoothKeyboard");
        var blocks = pieces.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("BLK_")).Select(t => t.gameObject).OrderBy(b => b.name).ToArray();
        IEnumerator Groups(bool west, bool east)                        // 막힘 묶음 켜기 — 길찾기 바닥 파내기는 다음 프레임들에
        {
            foreach (var b in blocks) b.SetActive(DevHud.BlockGroup(b) == 1 ? west : east);
            yield return new WaitForSeconds(0.4f);
        }
        var model = stalker.transform.Find("Body/Model");
        var scc = stalker.GetComponent<CharacterController>();
        var rubble = Slot("PRP_Rubble_FakeExit");
        string[] plazaExits = { "link_nw", "link_ne", "link_e", "link_w", "south" };
        void Plug(string slot)                                            // 사보타주용: 굴을 막는 보이지 않는 기둥 (길찾기 바닥도 파낸다)
        {
            var go = new GameObject("SabotagePlug_" + slot);
            go.transform.position = Slot(slot).position + Vector3.up * 1.5f;
            var col = go.AddComponent<CapsuleCollider>(); col.radius = 2.0f; col.height = 6f;
            var ob = go.AddComponent<NavMeshObstacle>(); ob.shape = NavMeshObstacleShape.Capsule; ob.radius = 2.0f; ob.height = 6f; ob.carving = true;
        }
        if (sabotageName == "blockcut")          // 걷는 길(큰길 → ① 채탄장) 한가운데 보이지 않는 기둥 — 길찾기 바닥은 그대로라 봇이 부딪힌다
        {
            var wall = new GameObject("SabotageWall").AddComponent<CapsuleCollider>();
            wall.transform.position = Slot("SLOT_Mid_v_z1").position + Vector3.up * 1.5f;
            wall.radius = 1.7f; wall.height = 4f;
        }
        if (sabotageName == "blockleak") { blocks[0].GetComponent<Collider>().enabled = false; blocks[0].GetComponent<NavMeshObstacle>().enabled = false; }
        if (sabotageName == "nonav") NavMesh.RemoveAllNavMeshData();
        if (sabotageName == "tallcap") { scc.height = Tuning.STALKER_H; scc.center = Vector3.up * Tuning.STALKER_H * 0.5f; }
        if (sabotageName == "bigmonster") model.GetComponent<StalkerAnim>().stoop = false;   // 숙이기 끔 = 선 키 그대로 (천장 밑 머리 검사가 잡는지)
        if (sabotageName == "nocol" && Physics.Raycast(player.transform.position + Vector3.up, Vector3.down, out RaycastHit under, 3f, ~(1 << 2), QueryTriggerInteraction.Ignore))
            under.collider.enabled = false;                                // 케이지 칸 충돌 끔
        if (sabotageName == "smallmap") foreach (var n in plazaExits) Plug($"SLOT_In_{n}_0");                  // 케이지 광장에서 나가는 굴 다섯을 다 막음 = 좁은 맵
        if (sabotageName == "nohub") foreach (var n in plazaExits.Take(3)) Plug($"SLOT_In_{n}_0");             // 광장에서 나가는 굴 셋을 막음 — 길 잃은 사람이 정거장으로 못 온다
        if (sabotageName == "nosidings") foreach (var t in pieces.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("SLOT_Mid_sd_")).ToArray()) Plug(t.name);   // 곁길 8 을 다 막음
        if (sabotageName == "nofakeexit") rubble.GetComponent<Collider>().enabled = false;                    // 가짜 출구 끝 무너짐이 없다
        yield return Groups(false, false);                                // 검사는 맵 전체에서 (묶음은 아래서)
        Vector3 spawn = OnNav(player.transform.position);
        Vector3 SlotAt(string n) => Slot(n).position;
        var veins = Enumerable.Range(1, 30).Select(i => SlotAt("SLOT_Pocket_" + i)).ToList();
        Vector3 hA = SlotAt("SLOT_Home_A"), hB = SlotAt("SLOT_Home_B");
        Vector2 homeMin = new Vector2(Mathf.Min(hA.x, hB.x), Mathf.Min(hA.z, hB.z)), homeMax = new Vector2(Mathf.Max(hA.x, hB.x), Mathf.Max(hA.z, hB.z));
        var crawlNames = pieces.GetComponentsInChildren<Transform>(true).Select(t => t.name).ToHashSet();
        var crawls = Enumerable.Range(1, 99).TakeWhile(i => crawlNames.Contains($"SLOT_Crawl_{i}_A"))
            .Select(i => (a: SlotAt($"SLOT_Crawl_{i}_A"), b: SlotAt($"SLOT_Crawl_{i}_B"))).ToList();
        // 사람만 지나가는 길 = 개구멍 + 뚫린 바위 틈(R2b, 비집는 길) — 틈은 지그재그라 꺾는 점마다 잇는다
        var passages = crawls.Select(k => new List<Vector3> { k.a, k.b }).Concat(Crevice.All.Where(c => c.through).Select(c => c.path.ToList())).ToList();
        static bool Clear(List<Vector3> pl) => pl.Zip(pl.Skip(1), (a, b) => !Physics.Linecast(a + Vector3.up * 0.6f, b + Vector3.up * 0.6f, ~(1 << 2), QueryTriggerInteraction.Ignore)).All(x => x);
        IEnumerable<(Vector3, Vector3)> OpenCrawls()                     // 사람이 지나가는 길 (막힘 돌무더기가 안 막은 것) — 양 끝을 1 m 씩 늘려 바닥에 잇는다
        {
            foreach (var pl in passages)
            {
                Vector3 a = pl[0], b = pl[pl.Count - 1], d = Flat3(b - a).normalized;
                if (Clear(pl)) yield return (a - d, b + d);
            }
        }

        // ---- 1. 넓이 · 도망 · 길 잃고 걷기 · 막힘 · 가짜 출구 · 구멍 (길찾기 바닥 = 괴물 반지름 0.6 m 를 뺀 바닥)
        if (NavMesh.CalculateTriangulation().indices.Length == 0)       // 바닥이 없으면 아래 재기가 예외로 멈춘다(사보타주 nonav) — FAIL 을 적고 끝낸다
        {
            Check("booth_size", false, "no navmesh (floor the monster can walk) — nothing to measure");
            InputSystem.RemoveDevice(kb);
            yield break;
        }
        float t0 = Time.realtimeSinceStartup;
        float mapA = BoothMeasure.ReachArea(spawn);
        var laps = BoothMeasure.Loops(BoothMeasure.Raster(NavMesh.CalculateTriangulation()));
        var wFull = BoothMeasure.Wander(BoothMeasure.Raster(NavMesh.CalculateTriangulation(), OpenCrawls()), homeMin, homeMax, 200, 1);
        yield return Groups(true, true);
        float boothA = BoothMeasure.ReachArea(spawn);
        var lapsBooth = BoothMeasure.Loops(BoothMeasure.Raster(NavMesh.CalculateTriangulation()));
        var wBooth = BoothMeasure.Wander(BoothMeasure.Raster(NavMesh.CalculateTriangulation(), OpenCrawls()), homeMin, homeMax, 200, 1);
        int veinsBooth = veins.Count(q => PathLen(spawn, q) > 0f);
        yield return Groups(false, false);
        int shortLaps = laps.Count(l => l <= 60f);
        Check("booth_size", mapA >= 1950f && boothA >= 1500f, $"floor the monster can walk (navmesh) reachable from the cage: whole map {mapA:F0} m² ({mapA / 436f:F1} × MAP1 436, ≥ 1950) · booth (both block groups on) {boothA:F0} m² ({boothA / 436f:F1} ×, ≥ 1500) · structure measured in {Time.realtimeSinceStartup - t0:F1} s");
        Check("booth_escape", shortLaps >= 30, $"rock pillars with floor all round and one lap ≤ 60 m: {shortLaps} (≥ 30, plan 35) · booth {lapsBooth.Count(l => l <= 60f)} · laps m: {string.Join(" ", laps.OrderBy(l => l).Select(l => l.ToString("F0")))}");
        // 부스판 70: 사용자 플레이 판정 09-25 "c_z5 9.8 m 뚫린 틈을 그대로, 이 정도는 통과" — 잰 값 71 % (막다른 구멍이던 c_z5 를 진짜로 이으니 75 → 71, 55차)
        Check("booth_return", wFull.within300 >= 40f && wBooth.within300 >= 70f,
            $"lost walker (never turns back except at dead ends, random at every fork, crawls too), {wFull.runs} starts: home to the cage plaza within 300 m {wFull.within300:F0} % (≥ 40, plan 47), median {wFull.median:F0} m · booth {wBooth.within300:F0} % (≥ 70 user-judged, plan 85), median {wBooth.median:F0} m · graph {wFull.nodes} forks/ends, {wFull.edges} tunnels, {wFull.deadEnds} dead ends, {wFull.homeNodes} plaza points");

        var notes = new List<string>(); bool blocksOk = true;
        foreach (var blk in blocks)
        {
            Vector3 c = blk.transform.TransformPoint(blk.GetComponent<MeshFilter>().sharedMesh.bounds.center);   // 꺼진 물체는 Renderer.bounds 가 비어 있다
            var inPass = passages.OrderBy(pl => pl.Zip(pl.Skip(1), (a, b) => Flat(c - Vector3.Lerp(a, b, Mathf.Clamp01(Vector3.Dot(c - a, b - a) / Mathf.Max((b - a).sqrMagnitude, 1e-4f))))).Min()).First();
            if (inPass.Zip(inPass.Skip(1), (a, b) => Flat(c - Vector3.Lerp(a, b, Mathf.Clamp01(Vector3.Dot(c - a, b - a) / Mathf.Max((b - a).sqrMagnitude, 1e-4f))))).Min() < 1.0f)
            {                                                                                // 개구멍·바위 틈 속 돌무더기(괴물 바닥 밖): 사람 몸이 막힌다
                bool clearOff = Clear(inPass);
                blk.SetActive(true); yield return null;
                bool shut = inPass.Zip(inPass.Skip(1), (a, b) => Physics.Linecast(a + Vector3.up * 0.6f, b + Vector3.up * 0.6f, out RaycastHit ch, ~(1 << 2), QueryTriggerInteraction.Ignore) && ch.collider.gameObject == blk).Any(x => x);
                blk.SetActive(false);
                blocksOk &= clearOff && shut;
                notes.Add($"{blk.name} {(inPass.Count > 2 ? "crevice" : "crawl")}: open {clearOff} → shut {shut}");
                continue;
            }
            c = OnNav(c);
            Vector3 a = c, b = c; float best = 99f;
            for (int k = 0; k < 8; k++)                              // 막힘 양쪽의 바닥 두 점: 꺼진 채로 곧게 이어지는 방향
            {
                Vector3 d = Quaternion.Euler(0f, k * 22.5f, 0f) * Vector3.forward;
                if (!NavMesh.SamplePosition(c + d * 2.8f, out NavMeshHit ha, 1.0f, NavMesh.AllAreas) || !NavMesh.SamplePosition(c - d * 2.8f, out NavMeshHit hb, 1.0f, NavMesh.AllAreas)
                    || Flat(ha.position - (c + d * 2.8f)) > 0.3f || Flat(hb.position - (c - d * 2.8f)) > 0.3f) continue;          // 비탈 위(v_z1)는 양쪽 바닥 높이가 달라 0.3 m 공으로는 못 찾았다 — 위에서 본 거리로
                float L = PathLen(ha.position, hb.position);
                if (L > 0f && L / 5.6f < best) { best = L / 5.6f; a = ha.position; b = hb.position; }
            }
            float off = PathLen(a, b);
            blk.SetActive(true);
            yield return new WaitForSeconds(0.3f);
            float on = PathLen(a, b);
            bool through = Physics.Linecast(a + Vector3.up, b + Vector3.up, out RaycastHit bh, ~(1 << 2), QueryTriggerInteraction.Ignore) && bh.collider.gameObject == blk;
            blk.SetActive(false);
            bool ok = off > 0f && off < 7f && (on < 0f || on > off + 5f) && through;
            blocksOk &= ok;
            notes.Add($"{blk.name}: across {off:F1} m → {(on < 0f ? "no path" : on.ToString("F0") + " m around")} · body blocks {through}");
        }
        yield return new WaitForSeconds(0.3f);
        Check("booth_blocks", blocksOk && veinsBooth >= 5 && veinsBooth < veins.Count, string.Join(" · ", notes) + $" · both groups on: {veinsBooth}/{veins.Count} veins reachable (≥ 5, fewer than all)");

        Vector3 rc = rubble.TransformPoint(rubble.GetComponent<MeshFilter>().sharedMesh.bounds.center), fm = SlotAt("SLOT_Mid_fake_exit") + Vector3.up * 1.2f;
        bool fHit = Physics.Raycast(fm, rc - fm, out RaycastHit fh, 40f, ~(1 << 2), QueryTriggerInteraction.Ignore);
        float fakeLen = PathLen(spawn, SlotAt("SLOT_Mid_fake_exit"));
        Check("booth_fake_exit", fHit && fh.collider.transform == rubble && fakeLen > 0f,
            $"from halfway up the fake exit incline ({fakeLen:F0} m walk from the cage) the way ahead ends in {(fHit ? fh.collider.name : "nothing")} at {(fHit ? fh.distance : 0f):F1} m (want PRP_Rubble_FakeExit)");

        var tri = NavMesh.CalculateTriangulation(); var rnd = new System.Random(7); int leaks = 0, pts0 = 0; string leakAt = "";
        var dirs = new List<Vector3>();
        for (int x = -1; x <= 1; x++) for (int y = -1; y <= 1; y++) for (int z = -1; z <= 1; z++) if (x != 0 || y != 0 || z != 0) dirs.Add(new Vector3(x, y, z).normalized);
        for (int n = 0; n < 600 && tri.indices.Length > 0; n++)
        {
            int k = rnd.Next(tri.indices.Length / 3) * 3;
            Vector3 o = (tri.vertices[tri.indices[k]] + tri.vertices[tri.indices[k + 1]] + tri.vertices[tri.indices[k + 2]]) / 3f + Vector3.up * 1.0f;
            pts0++;
            foreach (var d in dirs)
                if (!Physics.Raycast(o, d, 200f, ~(1 << 2), QueryTriggerInteraction.Ignore)) { leaks++; leakAt = $"({o.x:F1}, {o.y:F1}, {o.z:F1}) dir {d}"; break; }
        }
        Check("booth_sealed", pts0 >= 600 && leaks == 0, $"{pts0} floor points × 26 rays (200 m): {leaks} escaped the map {leakAt}");

        // ---- 2. 걷기: 케이지 → 막장 A(① 채탄장) · C(② 기둥 사이) · B(③ 노보리) → 케이지. W 키로 걷고 방향만 봇이 돌린다. 걸으며 0.5 m 마다 폭·천장을 잰다. 광맥 30곳은 길이 있는지만
        string Far(int from, int to) => Enumerable.Range(from, to - from + 1).Select(i => "SLOT_Pocket_" + i).OrderByDescending(s => PathLen(spawn, SlotAt(s))).First();
        string faceA = Far(1, 8), faceB = Far(9, 16), faceC = Far(17, 28);
        float lenA = PathLen(spawn, SlotAt(faceA)), lenB = PathLen(spawn, SlotAt(faceB)), lenC = PathLen(spawn, SlotAt(faceC));
        int veinPaths = veins.Count(q => PathLen(spawn, q) > 0f);
        int reached = 0; float walked = 0f, minW = 99f, minH = 99f, tw = Time.time; string worstAt = "", lowAt = "";
        var trail = new List<string> { "x,y,z" };
        var legs = new List<Vector3> { SlotAt(faceA), SlotAt(faceC), SlotAt(faceB), spawn };
        foreach (var goal0 in legs)
        {
            Vector3 goal = OnNav(goal0);
            var path = new NavMeshPath();
            bool has = NavMesh.CalculatePath(OnNav(player.transform.position), goal, NavMesh.AllAreas, path) && path.corners.Length > 0;
            var pts = has ? path.corners.ToList() : new List<Vector3> { goal };
            float legLen = 0f; for (int i = 1; i < pts.Count; i++) legLen += Vector3.Distance(pts[i - 1], pts[i]);
            float limit = Mathf.Max(legLen, Flat(goal - player.transform.position)) / Tuning.WALK_SPEED * 1.8f + 4f, t = 0f;
            int ci = Mathf.Min(1, pts.Count - 1);
            Vector3 last = player.transform.position; float sinceSample = 0f;
            InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
            while (t < limit && Flat(goal - player.transform.position) > 0.9f)
            {
                while (ci < pts.Count - 1 && Flat(pts[ci] - player.transform.position) < 0.5f) ci++;
                Vector3 to = Flat3(pts[ci] - player.transform.position);
                if (to.sqrMagnitude > 1e-4f) player.transform.rotation = Quaternion.LookRotation(to);
                yield return null;
                t += Time.deltaTime;
                Vector3 p = player.transform.position; float step = Flat(p - last); walked += step; sinceSample += step; last = p;
                if (sinceSample >= 0.5f)
                {
                    sinceSample = 0f;
                    Vector3 side = Vector3.Cross(Vector3.up, player.transform.forward).normalized, o = p + Vector3.up * 1.0f;
                    float l = Stalker.RayIgnore(o, side, 20f, ~(1 << 2), cc, out RaycastHit hl) ? hl.distance : 20f;      // 제 캡슐은 뺀다 (안에서 쏜 광선이 맞았다)
                    float r = Stalker.RayIgnore(o, -side, 20f, ~(1 << 2), cc, out RaycastHit hr) ? hr.distance : 20f;
                    float up = Stalker.RayIgnore(p + Vector3.up * 0.2f, Vector3.up, 20f, ~(1 << 2), cc, out RaycastHit hu) ? hu.distance + 0.2f : 20f;
                    if (l + r < minW) { minW = l + r; worstAt = $"({p.x:F1}, {p.z:F1})"; }
                    if (up < minH) { minH = up; lowAt = $"({p.x:F1}, {p.y:F1}, {p.z:F1}) hit {(hu.collider != null ? hu.collider.name : "-")}"; }
                    trail.Add($"{p.x:F2},{p.y:F2},{p.z:F2}");
                }
            }
            InputSystem.QueueStateEvent(kb, new KeyboardState());
            yield return null;
            if (Flat(goal - player.transform.position) <= 0.9f) reached++;
            else Debug.Log($"CHECK note booth walk: stuck {Flat(goal - player.transform.position):F1} m short of ({goal.x:F1}, {goal.y:F1}, {goal.z:F1}) at ({player.transform.position.x:F1}, {player.transform.position.y:F1}, {player.transform.position.z:F1}) after {t:F1} s (path {(has ? path.status.ToString() : "none")}, {pts.Count} corners)");
        }
        File.WriteAllLines(Path.Combine(outDir, "26_booth_walk_trail.csv"), trail);           // 봇이 걸은 자리 (위에서 본 그림으로 확인)
        {
            var navTri = NavMesh.CalculateTriangulation();
            var obj = navTri.vertices.Select(v => $"v {v.x:F3} {v.y:F3} {v.z:F3}").ToList();
            for (int i = 0; i < navTri.indices.Length; i += 3) obj.Add($"f {navTri.indices[i] + 1} {navTri.indices[i + 1] + 1} {navTri.indices[i + 2] + 1}");
            File.WriteAllLines(Path.Combine(outDir, "26_booth_navmesh.obj"), obj);
        }
        bool lensOk = Mathf.Abs(lenA - FaceA_M) <= FaceA_M * 0.15f && Mathf.Abs(lenB - FaceB_M) <= FaceB_M * 0.15f && Mathf.Abs(lenC - FaceC_M) <= FaceC_M * 0.15f;
        Check("booth_walk_route", reached == legs.Count && lensOk && veinPaths == veins.Count,
            $"walked to {reached}/{legs.Count} stops (faces A · C · B + back to the cage) in {Time.time - tw:F0} s, {walked:F0} m · path cage → face A {faceA} {lenA:F0} m ({FaceA_M:F0}) · C {faceC} {lenC:F0} m ({FaceC_M:F0}) · B {faceB} {lenB:F0} m ({FaceB_M:F0}), ±15 % · veins with a path {veinPaths}/{veins.Count}");
        Check("booth_clearance", minW >= 1.9f && minH >= 2.5f, $"along the walked route: narrowest {minW:F2} m at {worstAt} (≥ 1.9) · lowest ceiling {minH:F2} m at {lowAt} (≥ 2.5)");   // 벽 옆은 아치라 가운데보다 낮다

        // ---- 2b. 비탈 입구마다 곧장 걸어 들어가기 — 사람처럼 갈림에서 굴 쪽을 보고 W 만 누른다 (MAP1 09-24 사용자 "크로스컷 1 로 못 들어간다": 비탈 시작의 턱)
        {
            var mouths = pieces.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("SLOT_Mouth_")).ToArray();
            var eNotes = new List<string>(); bool eOk = true; int tried = 0;
            foreach (var m in mouths)
            {
                Vector3 inP = SlotAt("SLOT_In_" + m.name.Substring("SLOT_Mouth_".Length));
                if (Mathf.Abs(inP.y - m.position.y) < 0.15f) continue;                        // 입구 2.5 m 안이 평평한 굴은 뺀다
                tried++;
                Vector3 start = OnNav(m.position), dir = Flat3(inP - m.position).normalized;
                Teleport(cc, start + Vector3.up * 0.1f, Quaternion.LookRotation(dir).eulerAngles.y);
                yield return new WaitForSeconds(0.15f);
                InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
                float t = 0f;
                while (t < 1.6f) { player.transform.rotation = Quaternion.LookRotation(dir); yield return null; t += Time.deltaTime; }
                InputSystem.QueueStateEvent(kb, new KeyboardState());
                float prog = Vector3.Dot(Flat3(player.transform.position - start), dir);
                if (prog >= 3f) continue;
                string blocker = "";
                foreach (float hgt in new[] { 0.3f, 1.0f, 1.7f })
                    if (Stalker.RayIgnore(player.transform.position + Vector3.up * hgt, dir, 1.0f, ~(1 << 2), cc, out RaycastHit bh))
                        blocker += $" at {hgt:F1} m: {bh.collider.name} {bh.distance:F2} m";
                eOk = false;
                eNotes.Add($"{m.name.Substring(11)} {prog:F1} m BLOCKED{blocker} · feet y {player.transform.position.y:F2}");
            }
            Check("booth_enter_tunnels", eOk && tried >= 10, $"walking straight into {tried} sloped tunnel mouths with W for 1.6 s (≥ 3 m each)" + (eNotes.Count > 0 ? ": " + string.Join(" · ", eNotes) : ": all in"));
        }

        // ---- 2c. 노보리(25°) 발소리: 오를 때와 내릴 때 같은 박자 — 내릴 때 몸이 떴다 붙었다 하면 발소리가 프레임마다 났다 (사용자 09-24 영상)
        Vector3 nbLow = SlotAt("SLOT_Mouth_E_z3_col1_0"), nbHigh = SlotAt("SLOT_Mouth_E_z3_col1_1");
        {
            var sNotes = new List<string>(); bool sOk = true;
            foreach (var (nm, from, toward) in new[] { ("up", nbLow, nbHigh), ("down", nbHigh, nbLow) })
            {
                Vector3 start = OnNav(from), dir = Flat3(toward - from).normalized;
                Teleport(cc, start + Vector3.up * 0.1f, Quaternion.LookRotation(dir).eulerAngles.y);
                yield return new WaitForSeconds(0.3f);
                int s0 = player.steps; float y0 = player.transform.position.y, t = 0f;
                InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
                while (t < 2.5f) { player.transform.rotation = Quaternion.LookRotation(dir); yield return null; t += Time.deltaTime; }
                InputSystem.QueueStateEvent(kb, new KeyboardState());
                yield return null;
                int n = player.steps - s0; float want = 2.5f / Tuning.STEP_INTERVAL;           // 첫 발 1 + 0.5 s 마다 1
                bool ok = n >= want - 1f && n <= want + 2f;
                sOk &= ok;
                sNotes.Add($"{nm} {n} steps in 2.5 s, height {player.transform.position.y - y0:+0.0;-0.0} m{(ok ? "" : " WRONG")}");
            }
            Check("booth_slope_steps", sOk, $"walking the noburi slope (want {2.5f / Tuning.STEP_INTERVAL - 1f:F0}~{2.5f / Tuning.STEP_INTERVAL + 2f:F0} steps each way): " + string.Join(" · ", sNotes));
        }

        // ---- 3. 개구멍: 사람은 숙여서 끝까지(서서는 못 감) · 괴물은 길찾기로 구멍 길이의 2배 넘게 돌아간다
        {
            var cNotes = new List<string>(); bool cOk = true; int ci = 0;
            foreach (var (a, b) in crawls)
            {
                ci++;
                Vector3 dir = Flat3(b - a).normalized; float L = Flat(b - a);
                bool[] got = new bool[2]; string stuckAt = "";
                for (int crouch = 0; crouch < 2; crouch++)
                {
                    Teleport(cc, OnNav(a - dir * 1.0f, 1.5f) + Vector3.up * 0.1f, Quaternion.LookRotation(dir).eulerAngles.y);
                    if (crouch == 1) { InputSystem.QueueStateEvent(kb, new KeyboardState(Key.LeftCtrl)); yield return new WaitForSeconds(0.3f); }   // 숙인 채로 시작
                    InputSystem.QueueStateEvent(kb, crouch == 1 ? new KeyboardState(Key.W, Key.LeftCtrl) : new KeyboardState(Key.W));
                    float t = 0f, limit = (L + 2f) / (crouch == 1 ? Tuning.CROUCH_SPEED : Tuning.WALK_SPEED) * 1.5f + 1f;   // 서서도 길이만큼 (2 s 로 재면 10 m 구멍은 천장이 높아도 "못 감" — 09-25 사보타주 unitywide 가 못 잡았다)
                    while (t < limit && Flat(b - player.transform.position) > 0.8f) { player.transform.rotation = Quaternion.LookRotation(Flat3(b - player.transform.position).normalized); yield return null; t += Time.deltaTime; }
                    got[crouch] = Flat(b - player.transform.position) <= 0.8f;
                    if (crouch == 1 && !got[1]) stuckAt = $" ({Flat(b - player.transform.position):F1} m short at ({player.transform.position.x:F1}, {player.transform.position.y:F2}, {player.transform.position.z:F1}), {t:F1} s, {1f / Mathf.Max(Time.smoothDeltaTime, 1e-4f):F0} fps)";
                    InputSystem.QueueStateEvent(kb, new KeyboardState());
                    yield return new WaitForSeconds(0.2f);                                      // 일어선다
                }
                float mon = PathLen(a, b);
                bool ok = !got[0] && got[1] && (mon < 0f || mon > 2f * L);
                cOk &= ok;
                cNotes.Add($"crawl {ci} ({L:F1} m): standing {(got[0] ? "GOT THROUGH" : "stuck")} · crouched {(got[1] ? "through" : "STUCK" + stuckAt)} · monster {(mon < 0f ? "no path" : mon.ToString("F0") + " m around")}");
            }
            Check("booth_crawl", cOk && crawls.Count == 4, string.Join(" · ", cNotes));        // 8 중 짧은 넷은 R2b 뚫린 바위 틈이 됐다 (아래 3c)
        }

        // ---- 3b. 대피소: 사람이 서서 들어가 안쪽 자리(SLOT_Niche)에 선다 · 괴물 바닥·몸은 안으로 안 들어온다. 전부 캡슐로 재고, 가장 좁은 여섯은 봇이 걸어 들어간다
        {
            var niches = pieces.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("SLOT_Niche_")).ToArray();
            int capsuleOk = 0, monsterOut = 0; var nNotes = new List<string>(); var widths = new List<(Transform s, float w, Vector3 front, bool fits)>();
            float pr = Tuning.BODY_RADIUS - 0.05f;                                              // 복셀 벽의 0.05 m 요철 — 실제 발걸음은 아래 걷기가 잰다
            foreach (var s in niches)
            {
                Vector3 p = s.position, front = OnNav(p);                                       // 가장 가까운 괴물 바닥 = 대피소 앞 굴
                bool navIn = Flat(front - p) < 1.0f;
                Vector3 d = p - front;
                bool fits = !Physics.CheckCapsule(p + Vector3.up * (0.2f + pr), p + Vector3.up * (0.2f + Tuning.BODY_HEIGHT - pr), pr, ~(1 << 2), QueryTriggerInteraction.Ignore)
                    && !Physics.CapsuleCast(front + Vector3.up * (0.2f + pr), front + Vector3.up * (0.2f + Tuning.BODY_HEIGHT - pr), pr, d.normalized, d.magnitude, ~(1 << 2), QueryTriggerInteraction.Ignore);
                bool monsterFits = !Physics.CheckCapsule(p + Vector3.up * (0.2f + Tuning.STALKER_R), p + Vector3.up * (0.2f + Tuning.BOOTH_STALKER_H - Tuning.STALKER_R), Tuning.STALKER_R, ~(1 << 2), QueryTriggerInteraction.Ignore);
                if (fits) capsuleOk++;
                if (!navIn && !monsterFits) monsterOut++; else nNotes.Add($"{s.name} MONSTER gets in (navmesh {Flat(front - p):F1} m away, body fits {monsterFits})");
                Vector3 side = Vector3.Cross(Vector3.up, Flat3(d).normalized), o = p + Vector3.up * 1.0f;
                float w = (Physics.Raycast(o, side, out RaycastHit wl, 3f, ~(1 << 2), QueryTriggerInteraction.Ignore) ? wl.distance : 3f) + (Physics.Raycast(o, -side, out RaycastHit wr, 3f, ~(1 << 2), QueryTriggerInteraction.Ignore) ? wr.distance : 3f);
                widths.Add((s, w, front, fits));
            }
            // 봇이 걸어 들어가는 것: 가장 좁은 여섯 + 캡슐이 안 맞은 것 (캡슐은 어림 — 사람이 걷는 길이 정답)
            int walkedIn = 0; var narrow = widths.OrderBy(x => x.w).Take(6).Concat(widths.Where(x => !x.fits)).Distinct().ToList();
            if (sabotageName == "nicheplug" && narrow.Count > 0)            // 걸어 들어갈 대피소 하나를 가운데서 막는다 — 봇이 못 들어가야 한다
            {
                var plug = new GameObject("SabotageNichePlug").AddComponent<BoxCollider>();
                plug.transform.position = (narrow[0].s.position + narrow[0].front) * 0.5f + Vector3.up * 1.0f; plug.size = Vector3.one * 0.9f;
            }
            foreach (var (s, w, front, fits) in narrow)
            {
                // 사람처럼 대피소 정면에서 곧게: 안쪽 자리에서 1° 마다 쏜 광선 중 2.4 m 넘게 트인 방향들의 가운데 = 입구 쪽 축.
                // (가장 가까운 길찾기 바닥 점에서 비스듬히 가면 폭 1.0 m 에 몸 0.8 m 라 입구 모서리에 걸렸다 — 09-25 SLOT_Niche_44, 축에서 0.24 m 비낌)
                Vector3 o = s.position + Vector3.up * 1.0f, near = Flat3(front - s.position).normalized, sum = Vector3.zero;
                for (int k = -60; k <= 60; k++)
                {
                    Vector3 d = Quaternion.Euler(0f, k, 0f) * near;
                    if (!Physics.Raycast(o, d, 2.4f, ~(1 << 2), QueryTriggerInteraction.Ignore)) sum += d;
                }
                Vector3 axis = sum.sqrMagnitude > 0f ? sum.normalized : near, start = s.position + axis * 3.0f;
                start.y = front.y;
                Vector3 dir = -axis;
                Teleport(cc, start + Vector3.up * 0.1f, Quaternion.LookRotation(dir).eulerAngles.y);
                yield return new WaitForSeconds(0.15f);
                InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
                float t = 0f;
                while (t < 2.0f && Flat(s.position - player.transform.position) > 0.5f) { player.transform.rotation = Quaternion.LookRotation(Flat3(s.position - player.transform.position).normalized); yield return null; t += Time.deltaTime; }
                InputSystem.QueueStateEvent(kb, new KeyboardState());
                bool inOk = Flat(s.position - player.transform.position) <= 0.5f && player.stance == "walk";
                if (inOk) walkedIn++; else nNotes.Add($"{s.name} ({w:F2} m wide{(fits ? "" : ", capsule did not fit")}) bot stopped {Flat(s.position - player.transform.position):F1} m short");
                yield return null;
            }
            Check("booth_niche", monsterOut == niches.Length && walkedIn == narrow.Count && niches.Length >= 40,
                $"{niches.Length} refuges: monster floor and body stay out {monsterOut} · person capsule fits standing {capsuleOk} · walked in standing by the bot {walkedIn}/{narrow.Count} (6 narrowest {string.Join(" ", widths.OrderBy(x => x.w).Take(6).Select(x => x.w.ToString("F2")))} m + capsule misses {widths.Count(x => !x.fits)})" + (nNotes.Count > 0 ? " · " + string.Join(" · ", nNotes.Take(8)) : ""));
        }

        // ---- 3c. R2b 바위 틈 (제안서 docs/제안서_R2b_바위틈_비집기.md 차례 4): 봇이 입구에서 틈 쪽을 보고 E — 조작이 잠기고 옮겨져 반대편(뚫린) · 숨는 자리(막힌)에 선다.
        //      뚫린 틈은 양쪽에서, 막힌 틈은 들어갔다 숨는 자리에서 다시 E 로 나온다. 옮겨지는 동안 카메라가 바위 속에 들어가면 안 된다. 괴물 바닥·몸은 틈 속에 없다
        {
            var crevs = Crevice.All.OrderBy(c => int.Parse(c.name.Substring("Crevice_".Length))).ToList();
            if (sabotageName == "crevshift")                                   // 비집는 길을 옆으로 0.35 m — 틈 벽 속을 지나간다
                foreach (var c in crevs)
                    for (int i = 1; i < c.path.Length - 1; i++) c.path[i] += Vector3.Cross(Vector3.up, Flat3(c.path[i + 1] - c.path[i - 1]).normalized) * 0.35f;
            if (sabotageName == "squeezelong") player.squeezeMul = 2f;
            var cam = Camera.main.transform;
            int camMask = ~((1 << 2) | (1 << Pickaxe.ViewModelLayer));
            var eNotes = new List<string>(); var tNotes = new List<string>(); bool enterOk = crevs.Count == 14, timeOk = true; int runs = 0;
            foreach (var c in crevs)
                foreach (bool back in new[] { false, true })                    // 뚫린: 이쪽 → 저쪽, 저쪽 → 이쪽 · 막힌: 들어가기, 나오기
                {
                    var p = c.path.ToList();
                    if (back) p.Reverse();
                    string nm = $"{c.name.Substring(8)}{(c.through ? "t" : "c")}{(back ? "<" : ">")}";
                    if (!(back && !c.through && Flat(player.transform.position - p[0]) < Tuning.SQUEEZE_REACH_M))   // 막힌 틈 나오기는 들어간 자리 그대로 (들어가며 입구 쪽을 보게 돌았다)
                    {
                        Teleport(cc, p[0] + Vector3.up * 0.1f, Quaternion.LookRotation(Flat3(p[1] - p[0])).eulerAngles.y);
                        yield return new WaitForSeconds(0.3f);
                    }
                    Vector3 feet = player.transform.position;
                    float L = Vector3.Distance(feet, p[1]); for (int i = 2; i < p.Count; i++) L += Vector3.Distance(p[i - 1], p[i]);
                    float want = Tuning.SQUEEZE_S * L / Tuning.SQUEEZE_REF_M, tE = Time.time;
                    int inRock = 0, frames = 0; bool locked = true;
                    InputSystem.QueueStateEvent(kb, new KeyboardState(Key.E, Key.W));        // W 도 누른 채 — 조작이 잠겼으면 안 움직인다
                    yield return null;
                    InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
                    bool started = player.Squeezing;
                    while (player.Squeezing && Time.time - tE < want * 3f + 2f)
                    {
                        if (Physics.CheckSphere(cam.position, 0.07f, camMask, QueryTriggerInteraction.Ignore)) inRock++;
                        if (player.Controller.enabled) locked = false;
                        frames++;
                        yield return null;
                    }
                    float took = Time.time - tE;
                    InputSystem.QueueStateEvent(kb, new KeyboardState());
                    yield return null;
                    Vector3 end = player.transform.position; float r = Tuning.BODY_RADIUS - 0.05f;
                    bool fits = !Physics.OverlapCapsule(end + Vector3.up * (0.2f + r), end + Vector3.up * (Tuning.BODY_HEIGHT - r), r, ~(1 << 2), QueryTriggerInteraction.Ignore).Any(col => col != cc);
                    float faceErr = Vector3.Angle(player.transform.forward, Flat3(!c.through && !back ? p[p.Count - 2] - p[p.Count - 1] : p[p.Count - 1] - p[p.Count - 2]));
                    InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));                // 조작이 돌아왔나 — 0.5 s 걸어 본다
                    yield return new WaitForSeconds(0.5f);
                    InputSystem.QueueStateEvent(kb, new KeyboardState());
                    yield return new WaitForSeconds(0.1f);
                    float moved = Flat(player.transform.position - end);
                    bool ok = started && locked && Flat(end - p[p.Count - 1]) < 0.3f && fits && inRock == 0 && faceErr < 20f && moved >= 0.3f;
                    enterOk &= ok; runs++;
                    if (!ok) eNotes.Add($"{nm} started {started} locked {locked} end {Flat(end - p[p.Count - 1]):F2} m off · capsule fits {fits} · camera in rock {inRock}/{frames} frames · facing off {faceErr:F0}° · walked after {moved:F2} m");
                    bool tOk = Mathf.Abs(took - want) <= 0.2f;
                    timeOk &= tOk;
                    tNotes.Add($"{nm} {L:F1} m {took:F2}/{want:F2} s{(tOk ? "" : " WRONG")}");
                }
            Check("crevice_enter", enterOk && runs == 28, $"{crevs.Count} crevices ({crevs.Count(c => c.through)} through, {crevs.Count(c => !c.through)} closed), {runs} squeezes (through both ways, closed in and out): E with W held → locked, moved along the crack, ends on the far side / hide spot facing the way out, body fits, camera never inside rock, walks again" + (eNotes.Count > 0 ? " · " + string.Join(" · ", eNotes.Take(8)) : ": all ok"));
            Check("crevice_squeeze_time", timeOk && runs == 28, $"E → control back = SQUEEZE_S {Tuning.SQUEEZE_S:F2} s per {Tuning.SQUEEZE_REF_M:F1} m ± 0.2 s: " + string.Join(" ", tNotes));

            var mNotes = new List<string>(); int inside = 0, pts = 0;
            foreach (var c in crevs)
            {
                var q = new List<(Vector3 x, bool room)>();                     // 바위 속 점: 둘째 ~ 끝에서 둘째 꺾는 점과 그 사이 + 막힌 틈은 안쪽 방(숨는 자리 — 방은 괴물 몸이 들어갈 만하다, 길이 없어야 한다)
                for (int i = 1; i < c.path.Length - 1; i++) { q.Add((c.path[i], false)); if (i < c.path.Length - 2) q.Add(((c.path[i] + c.path[i + 1]) * 0.5f, false)); }
                if (!c.through) { q.Add(((c.path[c.path.Length - 2] + c.path[c.path.Length - 1]) * 0.5f, true)); q.Add((c.path[c.path.Length - 1], true)); }
                Vector3 outside = OnNav(c.path[0]);
                foreach (var (x, room) in q)
                {
                    pts++;
                    bool nav = NavMesh.SamplePosition(x, out NavMeshHit h, 0.5f, NavMesh.AllAreas) && Flat(h.position - x) < 0.3f && PathLen(outside, h.position) > 0f;
                    bool body = !Physics.CheckCapsule(x + Vector3.up * (0.2f + Tuning.STALKER_R), x + Vector3.up * (0.2f + Tuning.BOOTH_STALKER_H - Tuning.STALKER_R), Tuning.STALKER_R, ~(1 << 2), QueryTriggerInteraction.Ignore);
                    if (nav || (body && !room)) { inside++; mNotes.Add($"{c.name} ({x.x:F1}, {x.z:F1}) navmesh reachable {nav} body fits {body}"); }
                }
            }
            Check("crevice_no_monster", inside == 0 && pts >= 50, $"{pts} points inside the crevices (crack + closed-crevice room): monster floor reachable from outside or body fits in the crack {inside}" + (mNotes.Count > 0 ? " · " + string.Join(" · ", mNotes.Take(6)) : ""));
            player.squeezeMul = 1f;
        }

        // ---- 4. 괴물: 길찾기로 막장 셋까지 걸어서 닿는다. 걷는 동안(조사 걸음·첫 자리 더듬기) 머리 꼭대기와 그 자리 천장을 잰다
        Teleport(cc, spawn + Vector3.up * 0.1f, 0f);
        lamp.lampOn = false;
        Vector3 home = OnNav(SlotAt("SPAWN_Stalker"));
        var head = stalker.GetComponentsInChildren<Transform>().First(b => b.name == "mixamorig:Head");
        float minGap = 99f, tallest = 0f, maxDrop = 0f, maxPitch = 0f; int overRock = 0; string gapAt = "", tallAt = "", rockAt = ""; var arrive = new List<string>(); bool allReach = true;
        stalker.enabled = true;
        foreach (var face in new[] { faceA, faceC, faceB })
        {
            Vector3 goal = OnNav(SlotAt(face));
            stalker.Teleport(home + Vector3.up * 0.1f, Quaternion.LookRotation(Flat3(SlotAt("LOOK_Stalker") - home)).eulerAngles.y);   // 사람이 볼 시작 자세 그대로
            yield return null;
            bool pathOk = PathLen(home, goal) > 0f;
            NoiseBus.Make(goal, 999f, "booth_test", null);
            NoiseBus.Make(goal, 999f, "booth_test", null);               // 두 번 = 그 자리까지 (조사)
            float t = 0f, limit = Mathf.Max(PathLen(home, goal), Flat(goal - home)) / Tuning.STALKER_SPEED_INVESTIGATE * 2f + 6f, searchT = 0f;
            while (t < limit && searchT < 3f)
            {
                yield return null;
                t += Time.deltaTime;
                if (stalker.state == Stalker.State.Search) searchT += Time.deltaTime;
                float feet = stalker.transform.position.y, top = head.position.y + 0.3f;   // 머리 뼈 + 0.3 m (모델 크기 1.5 의 머리 윗부분)
                var sa = stalker.GetComponentInChildren<StalkerAnim>();
                if (top - feet > tallest) { tallest = top - feet; tallAt = $"{stalker.state}/{sa?.Current}"; }
                if (sa != null) { maxDrop = Mathf.Max(maxDrop, sa.StoopDrop); maxPitch = Mathf.Max(maxPitch, sa.StoopPitch); }
                Vector3 hx = head.position;                                                  // 머리 높이에서 — 발 높이에서 쏘면 오르막 앞은 바닥 속에서 출발한다 (09-24 헛 FAIL)
                if (!Stalker.RayIgnore(hx, Vector3.down, head.position.y - feet + 1.0f, ~(1 << 2), scc, out RaycastHit fl)) { if (overRock++ == 0) rockAt = $"{stalker.state}/{sa?.Current} head ({head.position.x:F1}, {head.position.y:F1}, {head.position.z:F1}) feet y {feet:F1}"; continue; }   // 머리가 바닥 위가 아니다 — 천장 재기에서 뺀다, 수만 센다
                hx.y = fl.point.y + 0.3f;
                if (Stalker.RayIgnore(hx, Vector3.up, 6f, ~(1 << 2), scc, out RaycastHit hc))
                {
                    float g = hc.point.y - top;
                    if (g < minGap) { minGap = g; gapAt = $"{stalker.state}/{sa?.Current} at ({head.position.x:F1}, {feet:F1}, {head.position.z:F1}) head top {top - feet:F2} m, ceiling {hc.point.y - feet:F2} m ({hc.collider.name})"; }
                }
            }
            float miss = Flat(goal - stalker.transform.position);
            if (miss >= 2.0f) Debug.Log($"CHECK note booth stalker stopped at ({stalker.transform.position.x:F1}, {stalker.transform.position.y:F1}, {stalker.transform.position.z:F1}) state {stalker.state}, goal ({goal.x:F1}, {goal.y:F1}, {goal.z:F1})");
            bool ok = pathOk && miss < 2.0f && searchT > 0f;
            allReach &= ok;
            arrive.Add($"{face.Replace("SLOT_Pocket_", "vein ")}: {(ok ? "arrived" : "FAILED")} {miss:F1} m off in {t:F1} s (path {(pathOk ? "yes" : "none")})");
        }
        // 비탈 내려가기: 노보리 꼭대기에서 밑의 소리로 (조사 5 m/s — 25° 면 1초에 2.3 m 떨어진다, 바닥 붙이기는 −1 m/s). 발밑 틈을 프레임마다
        float maxAir = 0f; int airFrames = 0, slopeFrames = 0;
        if (sabotageName == "monsterfloat") stalker.snapDown = false;
        {
            Vector3 top = OnNav(nbHigh), low = OnNav(nbLow);
            stalker.Teleport(top + Vector3.up * 0.1f, Quaternion.LookRotation(Flat3(low - top)).eulerAngles.y);
            yield return new WaitForSeconds(0.3f);
            NoiseBus.Make(low, 999f, "booth_test", null);
            NoiseBus.Make(low, 999f, "booth_test", null);
            float t = 0f;
            while (t < 8f && Flat(low - stalker.transform.position) > 1.5f)
            {
                yield return null;
                t += Time.deltaTime;
                if (stalker.transform.position.y > low.y + 0.3f && stalker.transform.position.y < top.y - 0.3f && Stalker.RayIgnore(stalker.transform.position + Vector3.up * 0.5f, Vector3.down, 3f, ~(1 << 2), scc, out RaycastHit gh))
                {
                    float air = gh.distance - 0.5f; slopeFrames++;                            // 캡슐 밑 공은 비탈에 가운데가 아닌 곳으로 닿는다 — 붙어 있어도 0.1 m 쯤 (그래서 판정은 땅에 붙었나로)
                    maxAir = Mathf.Max(maxAir, air);
                    if (!scc.isGrounded) airFrames++;
                }
            }
        }
        stalker.enabled = false;
        int reachAll = veins.Concat(stalker.cracks).Count(q => PathLen(home, q) > 0f);
        Check("booth_stalker_reaches", allReach && reachAll == veins.Count + stalker.cracks.Length, string.Join(" · ", arrive) + $" · paths from its lair to {reachAll}/{veins.Count + stalker.cracks.Length} veins and big-gap spots");
        Check("booth_stalker_fits", minGap >= 0.1f && overRock == 0, $"closest head top to the ceiling {minGap:F2} m (≥ 0.10): {gapAt} · tallest head top above its feet {tallest:F2} m ({tallAt}) · stoop up to hips −{maxDrop:F2} m, back {maxPitch:F0}° · frames with the head past a wall (not over floor) {overRock} {rockAt}");
        Check("booth_stalker_slope", slopeFrames >= 20 && airFrames <= slopeFrames / 20, $"walking down the noburi (25°) at investigate speed: off the ground in {airFrames}/{slopeFrames} frames (≤ 5 %), feet up to {maxAir:F2} m above the floor below the middle"); 

        // ---- 5. 빛 (램프 끔, 눈이 어둠에 다 익은 뒤): 켜진 전등 옆 벽이 전등을 끄면 확 어두워진다 · 꺼진 전등 옆 벽은 켜진 전등 옆보다 어둡다
        var lit = FindObjectsByType<Light>(FindObjectsSortMode.None).Where(l => l.type == LightType.Point && l.name == "Lamp").OrderBy(l => Flat(l.transform.position - spawn)).ToArray();
        var dead = GameObject.Find("BoothLights").transform.Cast<Transform>().Where(t => t.name == "DeadLamp").OrderBy(t => Flat(t.position - spawn)).ToArray();
        float yaw = Quaternion.LookRotation(Flat3(SlotAt("LOOK_Player") - spawn)).eulerAngles.y;
        float WallYaw(Vector3 at)                                        // 가장 가까운 벽 쪽
        {
            float bestD = 99f, bestY = 0f;
            for (int k = 0; k < 16; k++)
            {
                Vector3 d = Quaternion.Euler(0f, k * 22.5f, 0f) * Vector3.forward;
                if (Physics.Raycast(at + Vector3.up * 1.5f, d, out RaycastHit h, 10f, ~(1 << 2), QueryTriggerInteraction.Ignore) && h.distance < bestD) { bestD = h.distance; bestY = k * 22.5f; }
            }
            return bestY;
        }
        Vector3 litAt = OnNav(lit[Mathf.Min(4, lit.Length - 1)].transform.position), deadAt = OnNav(dead[0].position);
        Vector3 v1 = Vector3.zero, v2 = Vector3.zero, v3 = Vector3.zero;
        var mid = new Rect(Screen.width * 0.25f, Screen.height * 0.25f, Screen.width * 0.5f, Screen.height * 0.5f);
        yield return new WaitForSeconds(Tuning.DARK_ADAPT_TIME + 1f);
        Teleport(cc, litAt + Vector3.up * 0.1f, WallYaw(litAt)); yield return Capture("26_booth_light_lit", v => v1 = v, mid);
        foreach (var l in lit) l.enabled = false;
        yield return Capture("26_booth_light_lit_off", v => v2 = v, mid);
        foreach (var l in lit) l.enabled = true;
        Teleport(cc, deadAt + Vector3.up * 0.1f, WallYaw(deadAt)); yield return Capture("26_booth_light_dead", v => v3 = v, mid);
        Check("booth_light_zones", v1.x > 2f * v2.x && v1.x > 2f * v3.x, $"lamp off, wall beside a lit lamp {v1.x:F3} · same wall with the booth lights off {v2.x:F3} · wall beside a dead lamp {v3.x:F3} (lit > 2 × both)");

        // ---- 6. fps (램프 켬, 묶음은 사람이 받는 기본값): 정거장 · 기둥 사이 · 큰길 · 노보리 밑
        yield return Groups(Tuning.BOOTH_BLOCKS[0], Tuning.BOOTH_BLOCKS[1]);
        lamp.lampOn = true;
        var spots = new[] { (spawn, yaw, "station"), (home, yaw + 180f, "pillars"), (OnNav(SlotAt("SLOT_Mid_main")), yaw + 90f, "main road"), (OnNav(nbLow), yaw, "noburi") };
        float worst = 9999f; var fpsNotes = new List<string>();
        foreach (var (pos, y, nm) in spots)
        {
            Teleport(cc, pos + Vector3.up * 0.1f, y);
            yield return new WaitForSeconds(0.5f);
            float f = 0f; yield return MeasureFps(2f, v => f = v);
            worst = Mathf.Min(worst, f); fpsNotes.Add($"{nm} {f:F0}");
        }
        Teleport(cc, spawn + Vector3.up * 0.1f, yaw);
        yield return Capture("26_booth_station", _ => { });
        Check("booth_fps", worst >= MinFps, $"fps {string.Join(" · ", fpsNotes)} (≥ {MinFps:F0})");
        InputSystem.RemoveDevice(kb);
    }

    // 케이지에서 막장까지 길찾기 길이 (MAP2 첫 실행에서 잰 값 — 맵이 바뀌면 여기서 걸린다)
    const float FaceA_M = 67f, FaceB_M = 74f, FaceC_M = 68f;   // 09-25

    // UI-2 (지침 4-1 "플레이 종료 후 초기 상태로 자동 복귀"): 잡히면 CATCH_RESTART_S 뒤 Intro 씬으로. 씬이 바뀌면 이 컴포넌트는 사라지므로
    // 통과는 Intro.Start(expectReturn)가 적고 Finish 한다. 여기까지 살아 있으면 = 안 돌아간 것 → FAIL. 사보타주 norestart
    IEnumerator IntroStage(CharacterController cc)
    {
        var st = stalker;
        st.enabled = true;
        st.returnToIntro = !noRestart;
        Intro.expectReturn = true;
        Teleport(cc, new Vector3(0f, 0.1f, 6f), 0f);
        player.frozen = false;
        yield return null;
        st.Teleport(new Vector3(0f, 0.1f, 7.2f), 180f);
        st.ForceCatch();
        float t = 0f;
        while (t < Tuning.CATCH_RESTART_S + 2f) { t += Time.deltaTime; yield return null; }
        Check("intro_returns_after_catch", false, $"still in {SceneManager.GetActiveScene().name} {t:F1} s after catch (restarts {st.restarts}, returnToIntro {st.returnToIntro})");
        Finish();
    }

    // UI-1a: 곡괭이 내구도. 닿은 타격 −1 · 던지기 −5 · PICK_SHAKY_BELOW 이하 떨림 · 0 이면 손에서 조각나 떨어졌다 사라지고 빈손
    bool flatProps;                                      // 사보타주 flatprops (갱목·못·가죽끈 반들거림 그림 뺌)

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
    // 3D-④ MR1 맵: 벽 틈에 사람이 지나는 길로(W 키로 걸어서) 들어가 본다. 틈 자리는 조각의 COL_gap_back 에서 읽는다 — 어느 벽인지 검사가 미리 알지 않는다
    IEnumerator MapStage(CharacterController cc)
    {
        var kb = InputSystem.AddDevice<Keyboard>("MapKeyboard");
        var backs = pieces.GetComponentsInChildren<MeshCollider>().Where(c => c.name.StartsWith("COL_gap_back")).OrderBy(c => c.bounds.center.z).ToArray();
        int big = 0, small = 0;
        var notes = new List<string>();
        bool bigOk = true, smallOk = true;
        foreach (var back in backs)
        {
            var roof = back.transform.parent.GetComponentsInChildren<MeshCollider>().First(c => c.name.StartsWith("COL_gap_roof"));
            bool isSmall = roof.bounds.min.y < Tuning.BODY_HEIGHT;           // 서서는 못 들어가는 높이
            if (isSmall) small++; else big++;
            float side = Mathf.Sign(back.bounds.center.x), z = back.bounds.center.z;
            if (isSmall ? small == 1 : big == 1)                              // 사람이 볼 그림: 3 m 앞 비스듬히, 램프 켠 채
            {
                Teleport(cc, new Vector3(-side * 0.5f, 0.1f, z - 3f), side * 51f);
                yield return new WaitForSeconds(0.5f);
                yield return Capture(isSmall ? "23_map_gap_small" : "23_map_gap_big", _ => { });
            }
            foreach (bool crouch in isSmall ? new[] { false, true } : new[] { false })
            {
                Teleport(cc, new Vector3(side * 1.5f, 0.1f, z), side > 0f ? 90f : -90f);
                yield return new WaitForSeconds(0.3f);
                InputSystem.QueueStateEvent(kb, crouch ? new KeyboardState(Key.W, Key.LeftCtrl) : new KeyboardState(Key.W));
                yield return new WaitForSeconds(crouch ? 2.6f : 1.6f);
                float inM = Mathf.Abs(player.transform.position.x) - Tuning.TUNNEL_WALL_X;      // 벽면에서 안으로 들어간 거리
                InputSystem.QueueStateEvent(kb, new KeyboardState());
                yield return new WaitForSeconds(0.3f);
                bool want = !isSmall || crouch;
                bool ok = want ? inM >= Tuning.MAP_GAP_ENTER_M : inM < 0.3f;
                if (isSmall) smallOk &= ok; else bigOk &= ok;
                notes.Add($"{(isSmall ? "small" : "big")} gap z {z:F0} {(crouch ? "crouched" : "standing")}: {inM:F2} m past the wall (want {(want ? "≥ " + Tuning.MAP_GAP_ENTER_M : "< 0.3")})");
            }
        }
        Teleport(cc, new Vector3(0f, 0.1f, 3f), 0f);
        yield return new WaitForSeconds(0.2f);
        Check("map_gaps_placed", big == Tuning.MAP_GAP_BIG_PIECES.Length && small == Tuning.MAP_GAP_SMALL_PIECES.Length, $"big gaps {big} (want {Tuning.MAP_GAP_BIG_PIECES.Length}) · small gaps {small} (want {Tuning.MAP_GAP_SMALL_PIECES.Length})");
        Check("map_big_gap_walk_in", big > 0 && bigOk, string.Join(" · ", notes.Where(n => n.StartsWith("big"))));
        Check("map_small_gap_crouch_only", small > 0 && smallOk, string.Join(" · ", notes.Where(n => n.StartsWith("small"))));
        InputSystem.RemoveDevice(kb);
    }

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
        yield return null;
        float hp1 = st.hp;
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
        // 납작해지기(몸 0.3 s 세로 0.85배)는 3D-③ 에서 지웠다 — hit 동작이 대신한다(-only anim 이 본다)
        Check("hit_damages_and_stuns", hp0 == Tuning.STALKER_HP && hp1 == hp0 - Tuning.STALKER_HIT_DMG && stunT > Tuning.STALKER_STUN_S - 0.2f && stunT < Tuning.STALKER_STUN_S + 0.3f && back > 0.6f && back < 1.4f && st.state == Stalker.State.Chase,
            $"hp {hp0:0} → {hp1:0}, stun {stunT:F2} s (STALKER_STUN_S {Tuning.STALKER_STUN_S}), knocked {back:F2} m, then {st.state}");
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

    // A1 Meshy 소품 1차 (승인 09-23): 조각 _v2 의 갱목(통나무)·갓등, 곡괭이 pickaxe.glb — 실제 크기 · 바닥 붙음 · 면·그림 예산 · 재질 빠짐(분홍) 0 · 갱목 이름 그대로.
    // 그림 24_prop_timber(기둥 2 m 정면) · 24_prop_lamp(갓등 6 m 앞) · 24_prop_pick(곡괭이 뷰모델) — 사람 판정용
    string propsSabotage = "";
    IEnumerator PropsStage(CharacterController cc)
    {
        var mainCam = player.GetComponentInChildren<Camera>();
        var posts = pieces.GetComponentsInChildren<Renderer>().Where(r => r.name.StartsWith("TMB_straight_") && r.name.Contains("_post_")).OrderBy(r => r.bounds.center.z).ToArray();
        var lamps = pieces.GetComponentsInChildren<Renderer>().Where(r => r.name == "PRP_straight_bulb").OrderBy(r => r.bounds.center.z).ToArray();
        var pickRs = pickaxe.mesh.GetComponentsInChildren<Renderer>(true);
        if (propsSabotage == "bigprop") { pickaxe.mesh.localScale *= 2f; foreach (var r in posts) r.transform.localScale *= 2f; }
        if (propsSabotage == "nomat") { foreach (var r in posts.Concat(lamps).Concat(pickRs)) r.sharedMaterial = null; }
        if (propsSabotage == "renametmb") { foreach (var r in posts) if (r.name.EndsWith("_post_R")) r.name = "TMB_x_post_R"; }
        yield return null;
        // ① 실제 크기: 곡괭이 = 그물 경계(제 좌표) × (지금 배율 ÷ PICK_SCALE) · 기둥·갓등 = 세상 경계 상자 높이
        var pb = new Bounds(); bool first = true;
        foreach (var mf in pickaxe.mesh.GetComponentsInChildren<MeshFilter>(true))
        {
            var b = mf.sharedMesh.bounds; b.center = mf.transform.localPosition + b.center;
            if (first) { pb = b; first = false; } else pb.Encapsulate(b);
        }
        float pickLen = pb.size.y * pickaxe.mesh.localScale.y / Tuning.PICK_SCALE;
        float postH = posts.Length > 0 ? posts[0].bounds.size.y : 0f, lampH = lamps.Length > 0 ? lamps[0].bounds.size.y : 0f;
        bool sizeOk = Mathf.Abs(pickLen - Tuning.PICK_LENGTH_M) <= Tuning.PICK_LENGTH_M * 0.1f && Mathf.Abs(postH - Tuning.TIMBER_POST_M) <= Tuning.TIMBER_POST_M * 0.1f && Mathf.Abs(lampH - Tuning.LAMP_FIXTURE_M) <= Tuning.LAMP_FIXTURE_M * 0.1f;
        Check("props_real_size", posts.Length > 0 && lamps.Length > 0 && sizeOk, $"pick {pickLen:F2} m (want {Tuning.PICK_LENGTH_M} ±10 %) · post {postH:F2} (want {Tuning.TIMBER_POST_M}) · lamp {lampH:F2} (want {Tuning.LAMP_FIXTURE_M}) · posts {posts.Length} lamps {lamps.Length}");
        // ② 바닥·천장: 기둥 밑이 바닥(원본 −0.05) ±10 cm, 갓등 위 끝이 전선 밑(4.55) ±5 cm
        float postBottom = posts.Length > 0 ? posts[0].bounds.min.y : 99f, lampTop = lamps.Length > 0 ? lamps[0].bounds.max.y : 0f;
        Check("props_on_floor", Mathf.Abs(postBottom + 0.05f) < 0.1f && Mathf.Abs(lampTop - 4.55f) < 0.05f, $"post bottom y {postBottom:F2} (want -0.05 ±0.1) · lamp top y {lampTop:F2} (want 4.55 ±0.05)");
        // ③ 예산: 갱목(기둥·가로대·널)·갓등·곡괭이 삼각형 합, 소품 그림(prop_*·곡괭이) 한 변
        long tris = 0;
        foreach (var mf in pieces.GetComponentsInChildren<MeshFilter>().Where(m => m.name.StartsWith("TMB_") || m.name == "PRP_straight_bulb").Concat(pickaxe.mesh.GetComponentsInChildren<MeshFilter>(true)))
            tris += mf.sharedMesh.triangles.Length / 3;
        int texMax = 0; var texNames = new List<string>();
        foreach (var r in posts.Concat(lamps).Concat(pickRs))
            foreach (var m in r.sharedMaterials)
            {
                if (m == null) continue;
                foreach (var id in m.GetTexturePropertyNameIDs())
                {
                    var t = m.GetTexture(id);
                    if (t == null || !(r.name.StartsWith("PICK_") || t.name.StartsWith("prop_"))) continue;
                    texMax = Mathf.Max(texMax, Mathf.Max(t.width, t.height)); if (!texNames.Contains(t.name)) texNames.Add(t.name);
                }
            }
        Check("props_budget", tris <= Tuning.PROPS_TRIS_MAX && texMax > 0 && texMax <= Tuning.PROPS_TEX_MAX, $"prop triangles {tris} (max {Tuning.PROPS_TRIS_MAX}) · prop textures {texNames.Count}, max side {texMax} (max {Tuning.PROPS_TEX_MAX})");
        // ④ 재질 빠짐: 기둥 2 m 정면 · 갓등 6 m 앞(눈 1.6 → 4.4 높이는 25° 위, 세로 시야 80° 안) · 곡괭이 뷰모델 — 각 영역에서 분홍 픽셀 0
        int magentaSum = 0; string where = ""; float timberLum = 0f, pickLum = 0f;
        if (posts.Length > 2)
        {
            var post = posts[2];                                     // 조각 0 의 세 번째 기둥
            Vector3 c = post.bounds.center; float side = Mathf.Sign(c.x);
            Teleport(cc, new Vector3(c.x - side * 2f, 0.1f, c.z), side > 0f ? 90f : -90f);
            yield return Capture("24_prop_timber", v => timberLum = v.x, regionAt: () => ScreenRect(mainCam, new[] { post }));
            magentaSum += lastMagenta; where += $"timber {lastMagenta}";
        }
        if (lamps.Length > 0)
        {
            var lamp = lamps[1 < lamps.Length ? 1 : 0];
            Vector3 c = lamp.bounds.center;
            Teleport(cc, new Vector3(Mathf.Sign(c.x) * 1.5f, 0.1f, c.z - 6f), 0f);
            yield return Capture("24_prop_lamp", _ => { }, regionAt: () => ScreenRect(mainCam, new[] { lamp }));
            magentaSum += lastMagenta; where += $" · lamp {lastMagenta}";
        }
        Teleport(cc, new Vector3(0f, 0.1f, 17.5f), 0f);
        yield return Capture("24_prop_pick", v => pickLum = v.x, regionAt: () => ScreenRect(mainCam, pickRs));
        magentaSum += lastMagenta; where += $" · pick {lastMagenta}";
        Check("props_no_magenta", magentaSum == 0, $"magenta pixels {where}");
        // ⑥ 법선이 면 감기(winding)와 같은 쪽: fit_prop 의 축 행렬이 거울이면(09-23 실제 사고) 면이 뒤집혀 램프 앞에서 새까맣다 — 화면 밝기(평균 0.15)로는 안 잡혔다.
        //    삼각형마다 꼭짓점 순서로 구한 기하 법선과 저장된 법선의 내적 > 0 인 몫 ≥ 0.9 (곡괭이 · 기둥 · 갓등)
        var agree = new List<string>(); bool windOk = true;
        foreach (var mf in new[] { posts[0].GetComponent<MeshFilter>(), lamps[0].GetComponent<MeshFilter>() }.Concat(pickaxe.mesh.GetComponentsInChildren<MeshFilter>(true)))
        {
            var m = mf.sharedMesh; var v = m.vertices; var nn = m.normals; var tri = m.triangles; int ok = 0, all = tri.Length / 3;
            for (int i = 0; i + 2 < tri.Length; i += 3)
            {
                Vector3 g = Vector3.Cross(v[tri[i + 1]] - v[tri[i]], v[tri[i + 2]] - v[tri[i]]);
                if (Vector3.Dot(g, nn[tri[i]] + nn[tri[i + 1]] + nn[tri[i + 2]]) > 0f) ok++;
            }
            float f = all > 0 ? (float)ok / all : 0f; windOk &= f >= 0.9f; agree.Add($"{mf.name} {f:F2}");
        }
        Check("props_normals_match_winding", windOk, $"triangles whose stored normal faces the winding side (min 0.90): {string.Join(" · ", agree)} · timber 2 m lum {timberLum:F3} · pick lum {pickLum:F3}");
        // ⑤ 갱목 이름 그대로: 조각마다 post_L·post_R·cap × 4벌 (고장 지지목 코드가 이름으로 찾는다)
        int named = 0;
        foreach (Transform piece in pieces)
            for (int n = 0; n < 4; n++)
                foreach (var suffix in new[] { "_post_L", "_post_R", "_cap" })
                    if (piece.GetComponentsInChildren<Transform>().Any(t => t.name == $"TMB_straight_{n}{suffix}")) named++;
        int wantNamed = pieces.GetComponentsInChildren<MeshFilter>().Count(m => m.name.StartsWith("SHL_")) * 12;
        Check("timber_names_kept", named == wantNamed && wantNamed > 0, $"TMB_straight_<n>_{{post_L,post_R,cap}} found {named} (want {wantNamed})");
        Teleport(cc, new Vector3(0f, 0.1f, 3f), 0f);
        yield return null;
    }

    // 3D-③: 행동마다 맞는 동작 · 발 미끄러짐 · 벽타기 자세 · 손이 바닥·벽을 안 뚫음 · 포효 구간 · fps. 연속 사진 21_anim_*_sheet (4×3, 한 칸 480×270)
    // 3D-④ MB 수색 더듬기 (영상 B4 통과 09-20). 램프 끈 나는 갱도 입구 쪽 멀리 — 괴물 앞에서 소리 둘 → 조사 → 그 자리에서 더듬기
    IEnumerator GropeStage(CharacterController cc)
    {
        var st = stalker;
        var model = st.transform.Find("Body/Model");
        var anim = model.GetComponent<Animator>();
        var sa = model.GetComponent<StalkerAnim>();
        var bones = model.GetComponentsInChildren<Transform>().Where(b => b.name.StartsWith("mixamorig:")).ToArray();
        Transform Bone(string n) => bones.FirstOrDefault(b => b.name == "mixamorig:" + n);
        var feet = new[] { Bone("LeftFoot"), Bone("RightFoot") };
        var body = new[] { Bone("Hips"), Bone("LeftHand"), Bone("RightHand"), Bone("LeftToeBase"), Bone("RightToeBase"), Bone("Spine2") };
        if (sa == null || feet.Contains(null) || body.Contains(null)) { Check("anim_grope_bones_found", false, "model bones missing"); yield break; }
        float chance0 = st.heardChance;
        IEnumerator ToGrope(Vector3 S, float chance)
        {
            lamp.lampOn = false;
            player.frozen = false;
            Teleport(cc, new Vector3(0f, 0.1f, 3f), 0f);                 // 수색 자리(조사한 곳 둘레 ±3칸)가 내 2 m 안에 떨어지지 않게 멀리 — 14 m 였을 땐 전체 실행에서 나를 찾아 버렸다
            st.Teleport(S, 180f);
            st.hp = Tuning.STALKER_HP;
            st.heardChance = chance;
            yield return new WaitForSeconds(0.3f);
            Vector3 N = S - Vector3.forward * 4f;
            NoiseBus.Make(N, 30f, "test", this);
            yield return new WaitForSeconds(0.2f);
            NoiseBus.Make(N, 30f, "test", this);
            float w = 0f;
            while (st.state != Stalker.State.Search && w < 8f) { w += Time.deltaTime; yield return null; }
        }

        // ① 첫 자리에서만 더듬는다 · 손이 펴져 면에 닿는다 · 멀리 뻗는다 · 발은 제자리
        yield return ToGrope(new Vector3(0f, 0.1f, 34f), 0f);
        bool gropedFirst = st.Groping;
        float gropeS = 0f, t = 0f;
        int rest = 0, flat = 0, clipOk = 0, frames = 0, laterGrope = 0, laterFrames = 0;
        float straight = 1f, low = 99f, reach = 0f, footMove = 0f;
        var used = new bool[2];
        Vector3[] foot0 = null;
        int pats0 = sa.PatCount;
        while (st.state == Stalker.State.Search && t < 25f)
        {
            yield return new WaitForEndOfFrame();
            t += Time.deltaTime;
            if (!st.Groping) { if (st.spotsVisited > 1) { laterFrames++; if (sa.Current == "up_grope" && sa.GropeW > 0.99f) laterGrope++; } continue; }
            gropeS += Time.deltaTime;
            if (sa.GropeW < 0.99f) continue;
            frames++;
            if (sa.Current == "up_grope") clipOk++;
            if (foot0 == null) foot0 = feet.Select(f => f.position).ToArray();
            for (int i = 0; i < 2; i++) footMove = Mathf.Max(footMove, (feet[i].position - foot0[i]).magnitude);
            for (int h = 0; h < 2; h++)
            {
                if (!sa.PatResting[h]) continue;
                rest++; used[h] = true;
                if (sa.PatTipGap[h] <= 0.09f) flat++;
                straight = Mathf.Min(straight, sa.PatStraight[h]); low = Mathf.Min(low, sa.PatLow[h]); reach = Mathf.Max(reach, sa.PatReach[h]);
            }
        }
        int pats = sa.PatCount - pats0;
        Check("anim_grope_first_spot_only", gropedFirst && clipOk >= 0.95f * frames && frames >= 60 && Mathf.Abs(gropeS - Tuning.STALKER_GROPE_S) <= 0.5f && laterFrames >= 20 && laterGrope == 0,
            $"groping on arrival {gropedFirst} · up_grope in {clipOk}/{frames} crouched frames · groped {gropeS:F1} s (want {Tuning.STALKER_GROPE_S} ± 0.5) · at later spots {laterGrope}/{laterFrames} frames crouched (want 0) · left Search after {t:F1} s as {st.state}, sense {st.sense}, last heard {st.lastHeard}, {st.DistToPlayer:F1} m from me");
        Check("anim_grope_hands_plant_flat", rest >= 60 && flat >= 0.85f * rest && straight >= 0.93f && low >= -0.03f && pats >= 3 && used[0] && used[1],
            $"{rest} planted hand-frames, all four fingertips within 9 cm of the surface in {(rest > 0 ? 100f * flat / rest : 0f):F0} % (min 85) · fingers straight min {straight:F3} (min 0.93, claw ≈ 0.80) · deepest under surface {Mathf.Min(low, 0f):F3} m (max 0.03) · {pats} pats, left {used[0]} right {used[1]}, on upright surfaces {sa.PatOnWall}");
        Check("anim_grope_reaches_far", reach >= 2.2f && reach <= 2.9f, $"planted fingertips reach {reach:F2} m ahead of the body (want 2.2–2.9; rule to be found is {Tuning.STALKER_FOUND_M} m)");
        Check("anim_grope_feet_stay", frames >= 60 && footMove <= 0.03f, $"ankles move at most {footMove * 100f:F1} cm while the hips shift toward the hands (max 3)");

        // ② "들었나?": 더듬는 중 옆에서 소리 → 몸은 굳고 머리만 그쪽을 딱 → STALKER_HEARD_S 뒤에 조사하러 간다
        yield return ToGrope(new Vector3(0f, 0.1f, 34f), 0f);
        t = 0f;
        while (sa.GropeW < 0.99f && t < 3f) { t += Time.deltaTime; yield return null; }
        yield return new WaitForSeconds(1.0f);
        Vector3 H = st.transform.position + st.transform.right * 4f + st.transform.forward * 1f;
        NoiseBus.Make(H, 30f, "test", this);
        yield return null;
        bool heard = st.Heard;
        float heldS = 0f, move = 0f, faceAt = -1f, speedMax = 0f;
        var prev = body.Select(b => model.InverseTransformPoint(b.position)).ToArray();
        Transform headB = Bone("Head");
        while (st.Heard && heldS < 5f)
        {
            yield return new WaitForEndOfFrame();
            if (!st.Heard) break;                                       // 이 프레임에 풀렸다 — 풀린 뒤의 움직임을 재면 안 된다
            heldS += Time.deltaTime;
            if (heldS > 0.25f) speedMax = Mathf.Max(speedMax, anim.speed);    // 첫 0.25 s 는 뺀다: 소리가 난 프레임은 StalkerAnim.Update 가 이미 지나갔고, 머리를 딱 돌리는 동안 상체가 조금 딸려 간다
            for (int i = 0; i < body.Length; i++) { Vector3 q = model.InverseTransformPoint(body[i].position); if (heldS > 0.25f) move = Mathf.Max(move, (q - prev[i]).magnitude); prev[i] = q; }
            float err = Vector3.Angle(Flat3(sa.FaceDir), Flat3(H - headB.position));
            if (faceAt < 0f && err <= 15f) faceAt = heldS;
        }
        yield return null;
        Check("anim_heard_freezes_and_looks", heard && Mathf.Abs(heldS - Tuning.STALKER_HEARD_S) <= 0.25f && move <= 0.003f && speedMax == 0f && faceAt >= 0f && faceAt <= 0.35f && st.state == Stalker.State.Investigate,
            $"froze on noise {heard} for {heldS:F2} s (want {Tuning.STALKER_HEARD_S} ± 0.25) · hips/hands/toes/chest move at most {move * 1000f:F1} mm per frame (max 3) · playback {speedMax:F1} (want 0) · face on the noise after {faceAt:F2} s (max 0.35, -1 = never) · then {st.state} (want Investigate)");

        // ③ 조용히 있어도 가끔 (heardChance 1 로): 굳었다가 다시 더듬는다
        int h0 = st.heardCount;
        yield return ToGrope(new Vector3(0f, 0.1f, 34f), 1f);
        t = 0f;
        while (!st.Heard && st.state == Stalker.State.Search && t < 8f) { t += Time.deltaTime; yield return null; }
        bool rnd = st.Heard;
        while (st.Heard) yield return null;
        yield return new WaitForSeconds(0.3f);
        Check("anim_heard_sometimes_without_noise", rnd && st.heardCount == h0 + 1 && st.Groping, $"froze without any noise {rnd} (count +{st.heardCount - h0}) · afterwards still groping {st.Groping} ({st.state})");

        // ④ 찾는 규칙 = 손 닿는 2.5 m — 2.8 m 옆에 있으면 안 들키고, 2.3 m 면 들킨다
        yield return ToGrope(new Vector3(0f, 0.1f, 34f), 0f);
        yield return new WaitForSeconds(1.0f);
        Teleport(cc, st.transform.position + st.transform.right * 2.8f, 0f);
        player.frozen = true;
        yield return new WaitForSeconds(1.5f);
        var at28 = st.state;
        Teleport(cc, st.transform.position + st.transform.right * 2.3f, 0f);
        yield return new WaitForSeconds(0.5f);
        var at23 = st.state;
        Check("search_found_rule_2_5m", at28 == Stalker.State.Search && at23 != Stalker.State.Search && at23 != Stalker.State.Wander,
            $"lamp off, 2.8 m beside the groping creature for 1.5 s: {at28} (want Search) · moved to 2.3 m: {at23} (want Alert/Chase)");
        // ⑤ 사람이 볼 그림: 4 m 앞에서 램프를 켜고(눈·빛 감각은 잠시 0 — 게임에선 이러면 들킨다) 0.4 s 간격 12장
        yield return ToGrope(new Vector3(0f, 0.1f, 34f), 0f);
        st.eyeM = 0f; st.lightM = 0f;
        Vector3 camAt = st.transform.position + st.transform.forward * 4f + st.transform.right * 1.2f, toIt = st.transform.position + st.transform.forward * 1f - camAt;
        Teleport(cc, camAt, Mathf.Atan2(toIt.x, toIt.z) * Mathf.Rad2Deg);
        player.frozen = true;
        lamp.lampOn = true;
        yield return new WaitForSeconds(0.8f);
        yield return Sheet("22_grope_sheet", 12, i => Wait(0.4f));
        lamp.lampOn = false;
        st.eyeM = Tuning.STALKER_EYE_M; st.lightM = Tuning.STALKER_LIGHT_M;
        player.frozen = false;
        st.heardChance = chance0;
        st.Teleport(new Vector3(0f, 0.1f, 38f), 180f);
        Teleport(cc, new Vector3(0f, 0.1f, 4f), 0f);
        t = 0f;
        while (st.state != Stalker.State.Wander && t < 10f) { t += Time.deltaTime; yield return null; }   // 다음 구간은 배회에서 시작한다
    }

    IEnumerator AnimStage(CharacterController cc)
    {
        var st = stalker;
        var model = st.transform.Find("Body/Model");
        var anim = model.GetComponent<Animator>();
        var sa = model.GetComponent<StalkerAnim>();
        var mouse = InputSystem.AddDevice<Mouse>("AnimMouse");
        var bones = model.GetComponentsInChildren<Transform>().Where(b => b.name.StartsWith("mixamorig:")).ToArray();
        Transform Bone(string n) => bones.FirstOrDefault(b => b.name == "mixamorig:" + n);
        Transform hips = Bone("Hips"), head = Bone("Head");
        var hands = new[] { Bone("LeftHand"), Bone("RightHand") };
        var toes = new[] { Bone("LeftToeBase"), Bone("RightToeBase") };
        if (hips == null || head == null || hands.Contains(null) || toes.Contains(null))
        {
            Check("anim_bones_found", false, $"{bones.Length} mixamorig bones, hips {hips != null} head {head != null} hands {!hands.Contains(null)} toes {!toes.Contains(null)}");
            yield break;
        }
        bool Playing(string n) => anim.IsInTransition(0) ? anim.GetNextAnimatorStateInfo(0).IsName(n) : anim.GetCurrentAnimatorStateInfo(0).IsName(n);
        var seen = new Dictionary<string, bool>();
        float t;
        // 3D-③b M1c 턱: 행동 내내 프레임마다 (상태, 동작, 턱 각도, 턱 끝 ↔ 머리 꼭대기 거리) 적기 — ② 뒤에 검사
        Transform jawTip = Bone("JawTip"), jawTop = Bone("HeadTop_End");
        var jawLog = new List<(Stalker.State s, string clip, float deg, float chin, float time)>();
        bool jawOn = jawTip != null && jawTop != null;
        IEnumerator JawWatch()
        {
            while (jawOn)
            {
                yield return new WaitForEndOfFrame();
                jawLog.Add((st.state, sa.Current, sa.JawDeg, Vector3.Distance(jawTip.position, jawTop.position), Time.time));
            }
        }
        // 3D-④ 5b: 들킴 동안 몸이 돌처럼 멈췄나(엉덩이·두 손·두 발끝이 모델 공간에서 프레임 사이 움직인 거리) · 머리가 나를 보나 / 배회 동안 검지가 굽었다 펴지나
        var stillB = new[] { hips, hands[0], hands[1], toes[0], toes[1] };
        var stillPrev = new Vector3[stillB.Length];
        bool stillHave = false, upWatch = true;
        float alertMoveMax = 0f, alertFaceErr = 99f, alertT0 = -1f, chordLo = 9f, chordHi = 0f;
        int alertFrames = 0;
        var idx = Enumerable.Range(1, 4).Select(i => Bone("LeftHandIndex" + i)).ToArray();
        IEnumerator UpWatch()
        {
            while (upWatch)
            {
                yield return new WaitForEndOfFrame();
                if (st.state == Stalker.State.Alert)
                {
                    if (alertT0 < 0f) alertT0 = Time.time;
                    var now = stillB.Select(b => model.InverseTransformPoint(b.position)).ToArray();
                    if (stillHave && Time.time - alertT0 > 0.1f)
                    {
                        alertFrames++;
                        for (int i = 0; i < now.Length; i++) alertMoveMax = Mathf.Max(alertMoveMax, (now[i] - stillPrev[i]).magnitude);
                        alertFaceErr = Vector3.Angle(sa.FaceDir, player.transform.position + Vector3.up * Tuning.EYE_HEIGHT - head.position);
                    }
                    stillPrev = now; stillHave = true;
                }
                else stillHave = false;
                if (st.state == Stalker.State.Wander && !idx.Contains(null))
                {
                    float segs = 0f;
                    for (int i = 0; i < 3; i++) segs += Vector3.Distance(idx[i].position, idx[i + 1].position);
                    float c = Vector3.Distance(idx[0].position, idx[3].position) / segs;
                    chordLo = Mathf.Min(chordLo, c); chordHi = Mathf.Max(chordHi, c);
                }
            }
        }
        StartCoroutine(UpWatch());
        if (jawOn) StartCoroutine(JawWatch());
        else Check("anim_jaw_bone", false, $"JawTip {jawTip != null} HeadTop_End {jawTop != null} — GLB 에 턱 뼈가 없다");

        // 걷기·달리기 표본: 프레임마다(그린 뒤라 뿌리와 뼈가 같은 순간) 두 발끝의 땅 위 빠르기 중 느린 쪽 = 딛고 있는 발.
        // 걸을 땐 늘 한 발은 땅에 서 있다 — 느린 발도 움직이면 미끄러진다. "더 낮은 발"로 고르면 웅크려 걷기는 두 발이 다 낮아 흔드는 발이 섞였다(첫 실행 09-18)
        // 손: 가장 낮은 높이·가장 바깥 x. 모든 뼈 중 가장 낮은 것(바닥 = 괴물 뿌리 높이, 손가락 끝까지)이 검사 잣대
        // 기본 걸음(E 미끄러지는 걸음)에서 빠르기마다 나와야 하는 클립 — StalkerAnim 과 같은 길로 묻는다. 사보타주면 여기도 옛 클립이 나온다(이름 검사가 FAIL)
        float glideWalkRate = 0f, glideChaseRate = 0f, glideRetreatRate = 0f;
        string glideNames = "-";
        string walkClip = sa.ClipFor(Tuning.STALKER_SPEED_WANDER, out _), fastClip = sa.ClipFor(Tuning.STALKER_SPEED_RETREAT, out _), chaseClip = sa.ClipFor(Tuning.STALKER_SPEED_CHASE, out _);
        var slip = new Dictionary<string, List<Vector2>>{ [walkClip] = new List<Vector2>(), [fastClip] = new List<Vector2>(), [chaseClip] = new List<Vector2>() };
        var acc = new Dictionary<string, GaitAcc>();
        Transform chestB = Bone("Spine2");
        Transform[] shoulders = { Bone("LeftArm"), Bone("RightArm") }, thighs = { Bone("LeftUpLeg"), Bone("RightUpLeg") };
        var handTips = hands.Select(h => h.GetComponentsInChildren<Transform>().Where(b => b.name.StartsWith("mixamorig:")).ToArray()).ToArray();   // 뼈만 (갱목·끈 노드 제외)
        int accLiftPrev = 0;
        float handLow = 99f, handOut = 0f, boneLow = 99f;
        string boneLowName = "-";
        IEnumerator Sample(string clip, float seconds, Func<bool> go)
        {
            bool have = false;
            Vector3 p0 = default, p1 = default;
            float s = 0f;
            accLiftPrev = sa.LiftCount;
            if (!acc.TryGetValue(clip, out var A)) acc[clip] = A = new GaitAcc();
            while (s < seconds && go())
            {
                yield return new WaitForEndOfFrame();
                float dt = Time.deltaTime;
                s += dt;
                int liftD = sa.LiftCount - accLiftPrev;
                accLiftPrev = sa.LiftCount;
                if (!anim.GetCurrentAnimatorStateInfo(0).IsName(clip) || anim.IsInTransition(0)) { have = false; continue; }
                float floor = st.transform.position.y;
                {
                    A.frames++;
                    A.lifts += liftD;
                    A.rates.Add(sa.Rate);
                    A.rawMin = Mathf.Min(A.rawMin, sa.ArmLowRaw[0], sa.ArmLowRaw[1]);
                    var h4 = new float[4];
                    for (int i = 0; i < 2; i++)
                    {
                        h4[i] = handTips[i].Min(b => b.position.y) - floor;
                        h4[2 + i] = toes[i].position.y - floor;
                        if (h4[i] <= 0.05f) A.handOn[i]++;
                    }
                    A.heights.Add(h4);
                    A.sh += (shoulders[0].position.y + shoulders[1].position.y) * 0.5f - floor;
                    A.hip += (thighs[0].position.y + thighs[1].position.y) * 0.5f - floor;
                    A.chest.Add(chestB.position.y - floor);
                    A.reach += model.InverseTransformDirection((hands[0].position + hands[1].position) * 0.5f - chestB.position).z * Tuning.STALKER_MODEL_SCALE;
                    Vector3 pv = model.InverseTransformDirection(thighs[0].position - thighs[1].position), hf = model.InverseTransformDirection(sa.FaceDir);
                    A.pelvis.Add(Mathf.Atan2(pv.z, Mathf.Abs(pv.x)) * Mathf.Rad2Deg);      // 골반이 몸 앞 방향에서 좌우로 돈 각도
                    A.headYaw.Add(Mathf.Atan2(hf.x, hf.z) * Mathf.Rad2Deg);
                }
                if (have && dt > 0f)
                {
                    float v0 = Flat(toes[0].position - p0) / dt, v1 = Flat(toes[1].position - p1) / dt;
                    int k = v0 <= v1 ? 0 : 1;
                    slip[clip].Add(new Vector2(toes[k].position.y - floor, Mathf.Min(v0, v1)));
                }
                p0 = toes[0].position;
                p1 = toes[1].position;
                have = true;
                foreach (var h in hands)
                {
                    handLow = Mathf.Min(handLow, h.position.y - floor);
                    handOut = Mathf.Max(handOut, Mathf.Abs(h.position.x));
                }
                foreach (var b in bones)
                    if (b.position.y - floor < boneLow) { boneLow = b.position.y - floor; boneLowName = $"{b.name} ({clip})"; }
            }
        }
        // 느린 발이 땅에 닿은 프레임만(가장 낮은 높이 + 5 cm 안) 중앙값 — 달리기는 두 발이 다 뜬 순간이 있다
        float SlipOf(string clip, out int n)
        {
            var l = slip[clip];
            n = 0;
            if (l.Count == 0) return 99f;
            float minY = l.Min(v => v.x);
            var g = l.Where(v => v.x <= minY + 0.05f).Select(v => v.y).OrderBy(v => v).ToList();
            n = g.Count;
            return n > 0 ? g[n / 2] : 99f;
        }

        // ① 배회: 놓인 자리에서 1.0 s 멈춤 = idle_crouch, 걸어가면 walk_crouch. 램프 끔(눈·빛이 안 끼게)
        lamp.lampOn = false;
        yield return new WaitForSeconds(Tuning.LAMP_TOGGLE_TIME + 0.1f);
        Teleport(cc, new Vector3(0f, 0.1f, 3f), 0f);
        player.frozen = false;
        st.enabled = true;
        st.Teleport(new Vector3(0f, 0.1f, 25f), 180f);
        yield return new WaitForSeconds(0.6f);
        seen["idle (wander pause)"] = Playing(sa.IdleClip);
        t = 0f;
        while (sa.Current != walkClip && t < 3f) { t += Time.deltaTime; yield return null; }
        yield return new WaitForSeconds(Tuning.STALKER_ANIM_FADE_S + 0.1f);
        seen["walk (wander)"] = Playing(walkClip);
        float walkRate = sa.Rate;
        yield return Sample(walkClip, 5f, () => st.state == Stalker.State.Wander);

        // ①b 3D-③b M1 새 걷기 (배회 걸음 D = walk_knuckle): 배수 · 딛은 손발 미끄러짐 · 손 짚는 몫 · 팔 들기 0번 · 어깨 > 엉덩이 · 머리 꼭대기 · 머리 흔들림
        Transform chest = Bone("Spine2"), headTop = Bone("HeadTop_End") ?? head;
        int gPrev = sa.gait;
        sa.gait = 3;
        st.Teleport(new Vector3(0f, 0.1f, 25f), 180f);
        t = 0f;
        yield return new WaitForSeconds(0.5f);                       // 놓인 자리 멈춤(1.0 s) — 순간이동 전 걷던 빠르기가 식게
        t = 0f;
        while (!(sa.Current != sa.IdleClip && sa.Speed > 0.75f * Tuning.STALKER_SPEED_WANDER) && t < 4f) { t += Time.deltaTime; yield return null; }
        yield return new WaitForSeconds(Tuning.STALKER_ANIM_FADE_S + 0.1f);
        string kClip = sa.Current;
        float kRate = sa.Rate, kSpeed = sa.Speed;
        int liftPrev = sa.LiftCount, kLifts = 0, kFrames = 0;
        float rawMin = 99f;
        var kSlip = new List<float>();
        int[] handOn = new int[2];
        float shSum = 0f, hipSum = 0f, topMin = 99f;
        var headYs = new List<float>(); var chestYs = new List<float>();
        // 손가락 굽음: 엄지 뺀 네 손가락 (뿌리 → 끝 곧은 거리 ÷ 마디 길이 합)의 손마다 평균, 한 주기 최댓값 — Blender walk_knuckle.py chord() 와 같은 뼈 점·같은 평균
        var fingerJoints = new[] { "Left", "Right" }.SelectMany(s => new[] { "Index", "Middle", "Ring", "Pinky" }
            .Select(f => Enumerable.Range(1, 4).Select(i => Bone($"{s}Hand{f}{i}")).ToArray())).ToArray();
        float chordMax = 0f;
        var chordSum = new float[fingerJoints.Length]; var chordTop = new float[fingerJoints.Length];
        Vector3[] prevC = new Vector3[4];
        bool kHave = false;
        t = 0f;
        while (t < 5f && st.state == Stalker.State.Wander)
        {
            yield return new WaitForEndOfFrame();
            float dt = Time.deltaTime;
            t += dt;
            int liftNow = sa.LiftCount, liftD = liftNow - liftPrev;
            liftPrev = liftNow;
            if (sa.Current != kClip || anim.IsInTransition(0) || sa.Speed < 0.75f * Tuning.STALKER_SPEED_WANDER) { kHave = false; continue; }   // 멈춤과 섞이는 0.2 s 는 뺀다 — 안전망이 거기서 드는 건 옛 동작 몫
            kLifts += liftD;
            rawMin = Mathf.Min(rawMin, sa.ArmLowRaw[0], sa.ArmLowRaw[1]);
            float floor = st.transform.position.y;
            var c = new Vector3[4];
            for (int i = 0; i < 2; i++)
            {
                c[i] = handTips[i].OrderBy(b => b.position.y).First().position;   // 손: 가장 낮은 발톱 끝
                c[2 + i] = toes[i].position;
                if (c[i].y - floor <= 0.05f) handOn[i]++;
            }
            if (kHave && dt > 0f)
            {
                var planted = Enumerable.Range(0, 4).Where(i => c[i].y - floor <= 0.06f).Select(i => Flat(c[i] - prevC[i]) / dt).ToList();
                if (planted.Count > 0) kSlip.Add(planted.Min());                 // 딛은 손발 중 가장 덜 움직이는 것 — 걸을 땐 늘 하나는 서 있다
            }
            prevC = c;
            kHave = true;
            kFrames++;
            shSum += (shoulders[0].position.y + shoulders[1].position.y) * 0.5f - floor;
            hipSum += (thighs[0].position.y + thighs[1].position.y) * 0.5f - floor;
            topMin = Mathf.Min(topMin, headTop.position.y - floor);
            headYs.Add(head.position.y); chestYs.Add(chest.position.y);
            var handMean = new float[2];
            for (int k = 0; k < fingerJoints.Length; k++)
            {
                var fj = fingerJoints[k];
                if (fj.Any(b => b == null)) { handMean[k / 4] = 9f; continue; }
                float segs = 0f;
                for (int i = 0; i < 3; i++) segs += Vector3.Distance(fj[i].position, fj[i + 1].position);
                float ch = Vector3.Distance(fj[0].position, fj[3].position) / segs;
                handMean[k / 4] += ch / 4f; chordSum[k] += ch; chordTop[k] = Mathf.Max(chordTop[k], ch);
            }
            chordMax = Mathf.Max(chordMax, handMean[0], handMean[1]);
        }
        sa.gait = gPrev;
        float Sd(List<float> l) { if (l.Count == 0) return 0f; float m = l.Average(); return Mathf.Sqrt(l.Average(v => (v - m) * (v - m))); }
        float kSlipMed = kSlip.Count > 0 ? kSlip.OrderBy(v => v).ElementAt(kSlip.Count / 2) : 99f;
        float hand0 = kFrames > 0 ? handOn[0] / (float)kFrames : 0f, hand1 = kFrames > 0 ? handOn[1] / (float)kFrames : 0f;
        float shAvg = kFrames > 0 ? shSum / kFrames : 0f, hipAvg = kFrames > 0 ? hipSum / kFrames : 0f;
        float kWant = Tuning.STALKER_SPEED_WANDER / (Tuning.STALKER_CLIP_SPEED_KNUCKLE * Tuning.STALKER_MODEL_SCALE);   // 배회가 1.85 가 된 뒤(09-19)로는 0.74 — 걸음 D 는 비교용으로만 남았다
        Check("anim_knuckle_walk_clip_rate", kClip == "walk_knuckle" && Mathf.Abs(kRate - kWant) <= 0.1f,
            $"wander gait D plays {kClip} x{kRate:F2} at {kSpeed:F2} m/s (want walk_knuckle x{kWant:F2} ± 0.10)");
        Check("anim_knuckle_walk_plants", kFrames >= 60 && kSlipMed <= Tuning.STALKER_FOOT_SLIP_MAX && Mathf.Min(hand0, hand1) >= Tuning.STALKER_HAND_PLANT_MIN && kLifts == 0,
            $"{kFrames} frames: planted hand/foot moves {kSlipMed:F2} m/s (max {Tuning.STALKER_FOOT_SLIP_MAX}) · claw tips on floor L {hand0:P0} R {hand1:P0} (min {Tuning.STALKER_HAND_PLANT_MIN:P0}) · arm lifts {kLifts} in pure walk frames (want 0), {sa.LiftCount} in total, claw tip before lift lowest {rawMin:F3} m (lift below {Tuning.STALKER_ARM_FLOOR_MARGIN})");
        Check("anim_knuckle_walk_shape", kFrames >= 60 && shAvg > hipAvg && topMin >= Tuning.STALKER_HEAD_TOP_MIN && Sd(headYs) <= 0.5f * Sd(chestYs) + 0.002f,
            $"shoulders {shAvg:F2} m > hips {hipAvg:F2} m · head top lowest {topMin:F2} m (min {Tuning.STALKER_HEAD_TOP_MIN}) · head bob {Sd(headYs):F3} vs chest {Sd(chestYs):F3} m");

        Check("anim_knuckle_walk_fingers", kFrames >= 60 && chordMax <= Tuning.STALKER_FINGER_CHORD_MAX,
            $"fingers curled: per-hand mean of root-to-tip ÷ joint lengths, largest {chordMax:F3} (max {Tuning.STALKER_FINGER_CHORD_MAX}, straight ≈ 0.88) · per finger L/R Index Middle Ring Pinky avg {string.Join(" ", chordSum.Select(v => (v / Mathf.Max(1, kFrames)).ToString("F3")))} top {string.Join(" ", chordTop.Select(v => v.ToString("F3")))}");

        // ② 들킴 → 포효, 1.0 s 뒤 추격 → run, 잡기 → attack_swipe. 플레이어는 서 있다
        lamp.lampOn = true;
        Vector3 P = new Vector3(0f, 0.1f, 8f);
        Teleport(cc, P, 0f);
        st.Teleport(P + Vector3.forward * 10f, 180f);
        t = 0f;
        while (st.state != Stalker.State.Alert && t < 2f) { t += Time.deltaTime; yield return null; }
        yield return new WaitForSeconds(0.15f);
        seen[sa.Upright ? "freeze (alert)" : "roar (alert)"] = sa.Upright ? sa.Frozen && anim.speed == 0f : Playing("roar");
        while (st.state == Stalker.State.Alert) yield return null;
        yield return new WaitForSeconds(0.15f);
        seen["run (chase)"] = Playing(chaseClip) || Playing(fastClip);      // 추격 첫 0.3 s 는 빠르기가 붙는 중이라 조사용 클립을 지나간다
        float chaseRate = sa.Rate;
        yield return Sample(chaseClip, 3f, () => st.state == Stalker.State.Chase);
        t = 0f;
        while (st.state != Stalker.State.Catch && t < 3f) { t += Time.deltaTime; yield return null; }
        yield return null;
        yield return null;
        seen[sa.Upright ? "up_run (catch)" : "attack_swipe (catch)"] = Playing(sa.Upright ? "up_run" : "attack_swipe");
        int r0 = st.restarts;
        t = 0f;
        while (st.restarts == r0 && t < 5f) { t += Time.deltaTime; yield return null; }
        yield return new WaitForSeconds(Tuning.CATCH_FADE_OUT_S);

        // ③ 스턴 → hit. 철수(체력 50 에서 한 대 = 25) → run, 벽타기 → crawl + 벽 자세
        Vector3 S = new Vector3(0f, 0.1f, 20f);
        Vector3 Pp = S - Vector3.forward * 1.6f;
        st.Teleport(S, 180f);
        st.hp = Tuning.STALKER_HP;
        Teleport(cc, Pp, 0f);
        player.frozen = false;
        yield return null;
        yield return Click(mouse);
        t = 0f;
        while (st.state != Stalker.State.Stun && t < 1f) { t += Time.deltaTime; yield return null; }
        yield return null;
        yield return null;
        seen["hit (stun)"] = Playing("hit");
        while (st.state == Stalker.State.Stun) yield return null;
        yield return new WaitForSeconds(0.7f);                      // 곡괭이가 다시 휘둘러지게
        st.Teleport(S, 180f);
        st.hp = Tuning.STALKER_RETREAT_HP + Tuning.STALKER_HIT_DMG - 5f;   // 한 대면 철수선 밑
        Teleport(cc, Pp, 0f);
        player.frozen = false;
        yield return null;
        yield return Click(mouse);
        t = 0f;
        while (st.state != Stalker.State.Retreat && t < 1f) { t += Time.deltaTime; yield return null; }
        yield return new WaitForSeconds(0.3f);
        seen["run (retreat)"] = Playing(fastClip);
        yield return Sample(fastClip, 5f, () => st.state == Stalker.State.Retreat);
        t = 0f;
        while (st.state != Stalker.State.Climb && t < 3f) { t += Time.deltaTime; yield return null; }
        yield return new WaitForSeconds(Tuning.STALKER_CLIMB_TILT_S + 0.3f);
        seen["crawl (climb)"] = Playing("crawl");
        float side = st.transform.position.x >= 0f ? 1f : -1f;
        string pierceName = "-", pierceWhy = "";
        float headAbove = 99f, pierce = -99f, nearest = 99f, climbRate = sa.Rate;
        int climbFrames = 0;
        bool shot = false;
        while (st.state == Stalker.State.Climb)
        {
            yield return new WaitForEndOfFrame();
            if (sa.Tilt < 0.99f && sa.tiltClimb) continue;
            headAbove = Mathf.Min(headAbove, head.position.y - hips.position.y);
            var ob = bones.OrderByDescending(b => b.position.x * side).First();
            float outMost = ob.position.x * side;
            if (outMost - Tuning.TUNNEL_WALL_X > pierce) { pierce = outMost - Tuning.TUNNEL_WALL_X; pierceName = ob.name; pierceWhy = $"root x {st.transform.position.x:F2} y {st.transform.position.y:F2}, model origin x {model.position.x:F2}, model up {model.up}, bone model-y {model.InverseTransformPoint(ob.position).y * Tuning.STALKER_MODEL_SCALE:F3}, tilt {sa.Tilt:F2}, clamp saw {sa.ArmLow[0]:F3}/{sa.ArmLow[1]:F3}"; }
            nearest = Mathf.Min(nearest, Tuning.TUNNEL_WALL_X - outMost);
            climbFrames++;
            if (!shot && climbFrames == 20) { shot = true; StartCoroutine(Capture("21_anim_climb", _ => { })); }   // 플레이어 자리에서 본 벽타기
        }
        st.hiddenLeft = 0f;                                          // 숨은 채 두면 뒤 사진에 몸이 안 나온다 — 바로 나오게
        t = 0f;
        while (st.state == Stalker.State.Hidden && t < 2f) { t += Time.deltaTime; yield return null; }

        Check("anim_state_to_clip", seen.Values.All(v => v) && seen.Count == 8,
            string.Join(", ", seen.Select(kv => $"{kv.Key} {(kv.Value ? "ok" : "NO")}")) + $" (rates walk x{walkRate:F2} chase x{chaseRate:F2} (0.15 s in) climb x{climbRate:F2})");
        float walkSlip = SlipOf(walkClip, out int nWalk), runSlip = SlipOf(chaseClip, out int nRun);
        Check("anim_feet_do_not_slide", walkSlip <= Tuning.STALKER_FOOT_SLIP_MAX && runSlip <= Tuning.STALKER_FOOT_SLIP_MAX && nWalk >= 20 && nRun >= 20,
            $"planted foot moves walk {walkSlip:F2} m/s ({nWalk} frames) · run {runSlip:F2} m/s ({nRun} frames) (max {Tuning.STALKER_FOOT_SLIP_MAX})");
        // 3D-③b M2b 미끄러지는 걸음: 몸이 안 튀고 공중에 안 뜬다 · 손이 짚는다 · 배회 때 허리만 옆으로 휘고 머리는 가만히 · 빨라져도 박자는 그대로
        GaitAcc Acc(string c) => acc.TryGetValue(c, out var a) ? a : new GaitAcc();
        GaitAcc gw = Acc(walkClip), gc = Acc(chaseClip), gf = Acc(fastClip);
        float ClipLen(string c) => anim.runtimeAnimatorController.animationClips.Where(x => x.name == c).Select(x => x.length).DefaultIfEmpty(1f).First();
        glideWalkRate = gw.Med(gw.rates); glideChaseRate = gc.Med(gc.rates); glideRetreatRate = gf.Med(gf.rates);
        glideNames = $"{walkClip}/{fastClip}/{chaseClip}";
        // 3D-④ 5b 서서 오는 괴물 (영상 UP_U4 통과 09-19). 옛 anim_glide_* 다섯을 갈음한다
        upWatch = false;
        Check("anim_up_freeze_on_alert", alertFrames >= 20 && alertMoveMax <= 0.003f && alertFaceErr <= 10f,
            $"alert {alertFrames} frames: hips/hands/toes move at most {alertMoveMax * 1000f:F1} mm per frame in model space (max 3 — stone) · face {alertFaceErr:F0}° off me at the end (max 10)");
        float reachC = gc.frames > 0 ? gc.reach / gc.frames : 0f, reachW = gw.frames > 0 ? gw.reach / gw.frames : 0f;
        Check("anim_up_run_reaches", gc.frames >= 60 && reachC >= 0.4f && reachC >= reachW + 0.3f && gc.lifts == 0 && gw.lifts == 0,
            $"{gc.frames} pure chase frames: hands ahead of chest {reachC:F2} m (min 0.4, wander {reachW:F2}) · arm lifts chase {gc.lifts} · wander {gw.lifts} (want 0)");
        // 문턱: 손가락을 안 움직여도(사보타주 stillhands) 모션캡처·걸음 D 의 손가락 차이로 0.75–0.96 = 0.20 이 나온다(09-19 실측) → 주먹 ≤ 0.45 · 폭 ≥ 0.4 (실측 0.25–0.93)
        Check("anim_up_fingers_move", chordHi - chordLo >= 0.4f && chordLo <= 0.45f,
            $"left index root-to-tip ÷ joint lengths while wandering: {chordLo:F2} (fist) – {chordHi:F2} (open), range {chordHi - chordLo:F2} (min 0.4, fist max 0.45)");
        var far = sa.StompLog.Where(v => v.x > 6f).ToList(); var near = sa.StompLog.Where(v => v.x < 4f).ToList();
        Check("anim_up_footfall_shakes", far.Count >= 1 && near.Count >= 1 && far.Average(v => v.y) < near.Average(v => v.y),
            $"footfalls that shook my view: {sa.StompLog.Count} · beyond 6 m {far.Count} avg {(far.Count > 0 ? far.Average(v => v.y) : 0f) * 100f:F1} cm · inside 4 m {near.Count} avg {(near.Count > 0 ? near.Average(v => v.y) : 0f) * 100f:F1} cm (far must be weaker)");
        Check("anim_climb_on_wall", climbFrames >= 10 && headAbove > 0.3f && pierce <= 0.02f && nearest <= 0.2f,
            $"{climbFrames} frames, head above hips ≥ {headAbove:F2} m, deepest bone past wall {pierceName} {pierce:F2} m [{pierceWhy}], closest bone gap {nearest:F2} m");
        Check("anim_hands_stay_in_tunnel", boneLow >= -0.05f && handOut <= Tuning.TUNNEL_WALL_X,
            $"walk/run hands lowest {handLow:F2} m above floor, farthest |x| {handOut:F2} m (wall {Tuning.TUNNEL_WALL_X}); lowest bone {boneLowName} {boneLow:F2} m");

        if (jawOn)
        {
            jawOn = false;
            // 배회 = 걷기·대기 동작이 STALKER_JAW_CLOSE_S + 0.1 s 넘게 이어진 뒤만 (잡기 뒤 다시 배회할 때 40° 에서 다무는 0.4 s 는 뺀다)
            var wan = new List<(Stalker.State s, string clip, float deg, float chin, float time)>();
            float calmSince = jawLog.Count > 0 ? jawLog[0].time : 0f;
            foreach (var j in jawLog)
            {
                bool calm = j.s == Stalker.State.Wander && (j.clip == walkClip || j.clip == sa.IdleClip || j.clip == "walk_crouch" || j.clip == "walk_knuckle" || j.clip == "idle_crouch");
                if (!calm) calmSince = float.MaxValue;
                else if (calmSince == float.MaxValue) calmSince = j.time;
                if (calm && j.time > calmSince + Tuning.STALKER_JAW_CLOSE_S + 0.1f && j.time > jawLog[0].time + 1f) wan.Add(j);
            }
            var al = jawLog.SkipWhile(j => j.s != Stalker.State.Alert).TakeWhile(j => j.s == Stalker.State.Alert).ToList();   // 첫 들킴만 — 추격 뒤 다시 들키면 턱이 40° 에서 내려온다
            var ca = jawLog.Where(j => j.s == Stalker.State.Catch).ToList();
            float chase0 = jawLog.FirstOrDefault(j => j.s == Stalker.State.Chase).time;
            var ch = jawLog.Where(j => j.s == Stalker.State.Chase && j.clip == chaseClip && j.time > chase0 + 0.5f).ToList();
            float wMin = wan.Count > 0 ? wan.Min(j => j.deg) : -1f, wMax = wan.Count > 0 ? wan.Max(j => j.deg) : -1f;
            float aMax = al.Count > 0 ? al.Max(j => j.deg) : -1f, cMax = ca.Count > 0 ? ca.Max(j => j.deg) : -1f, chAvg = ch.Count > 0 ? ch.Average(j => j.deg) : -1f;
            var a30 = al.FirstOrDefault(j => j.deg >= 30f);
            float snap = al.Count > 0 && a30.clip != null ? a30.time - al[0].time : 99f;
            // 서서 오는 괴물: 들킴 = 굳은 채 턱만 천천히(STALKER_ALERT_S 에 걸쳐 22° 까지), 추격·잡기 = 크게 벌린 채
            float a02 = al.Where(j => j.time <= al[0].time + 0.2f).Select(j => j.deg).DefaultIfEmpty(99f).Max();
            Check("anim_jaw_follows_behavior", wan.Count >= 30 && wMin >= 5f - 0.01f && wMax <= 12f && aMax >= 15f && aMax <= 25f && cMax >= 35f && chAvg >= 35f,
                $"jaw wander {wMin:F1}–{wMax:F1}° ({wan.Count} frames, want 5–12) · alert max {aMax:F1}° (want 15–25) · catch max {cMax:F1}° · chase avg {chAvg:F1}° ({ch.Count} frames) (want ≥ 35)");
            Check("anim_jaw_opens_slowly_on_alert", a02 <= 18f && aMax >= 15f, $"jaw {a02:F1}° 0.2 s into alert (max 18 — no snap), {aMax:F1}° by the end (min 15)");
            float chinIdle = wan.Count > 0 ? wan.OrderBy(j => j.chin).ElementAt(wan.Count / 2).chin : 0f;
            var wide = al.Concat(ca).OrderByDescending(j => j.deg).FirstOrDefault();
            Check("anim_jaw_chin_drops", wide.clip != null && wide.chin - chinIdle >= Tuning.STALKER_JAW_CHIN_DROP_MIN,
                $"chin ↔ head top {chinIdle:F3} m while wandering → {wide.chin:F3} m at {wide.deg:F0}° ({wide.clip}) = +{wide.chin - chinIdle:F3} m (min {Tuning.STALKER_JAW_CHIN_DROP_MIN}) — minus means the jaw turned the wrong way");
        }

        // ④ fps: 램프 켜고 괴물이 빛을 따라 걸어온다(눈만 잠시 0 — 12 m 에서 들켜 멈추지 않게). ⑤ 7 m 쯤을 걸어오는 연속 사진 0.1 s 간격
        Teleport(cc, new Vector3(0f, 0.1f, 4f), 0f);
        player.frozen = false;
        st.eyeM = 0f;
        st.Teleport(new Vector3(0f, 0.1f, 26f), 180f);
        float fps = 0f;
        yield return MeasureFps(2f, v => fps = v);
        Check("anim_fps", fps >= MinFps, $"{fps:F0} fps while the monster walks toward the lamp");
        t = 0f;
        while (st.DistToPlayer > 9f && t < 10f) { t += Time.deltaTime; yield return null; }
        yield return Sheet("21_anim_walk_in_sheet", 12, i => Wait(0.1f));
        st.eyeM = Tuning.STALKER_EYE_M;

        // ⑥ 행동 끄고 옆 3 m 에서 동작마다 한 바퀴 12장 (DevHud N 키와 같은 manual 길). 포효는 두 손이 가장 멀어지는 순간을 잰다
        st.enabled = false;
        st.Teleport(new Vector3(0.8f, 0.1f, 20f), 0f);
        Teleport(cc, new Vector3(-2.2f, 0.1f, 20f), 90f);
        float roarPeak = -1f, best = -1f;
        foreach (string clip in StalkerAnim.ManualClips)
        {
            sa.manual = Array.IndexOf(StalkerAnim.ManualClips, clip);
            sa.freezeTime = false;
            yield return new WaitForSeconds(Tuning.STALKER_CLIMB_TILT_S + 0.2f);
            sa.freezeTime = true;
            if (clip == "walk_crouch" || clip == "walk_knuckle" || clip == "run" || clip == "run_knuckle" || clip.StartsWith("glide_") || clip == "crawl")
            {
                // 진단: 동작 1배일 때 바닥에 닿은 발끝이 모델 뒤쪽으로 가는 빠르기(게임 크기 m/s) = 원래 걸음 빠르기. 가장 낮은 뼈 높이도
                float len = anim.runtimeAnimatorController.animationClips.First(c => c.name == clip).length;
                var smp = new List<Vector2>();
                float lowest = 99f; string lowestName = "-";
                Vector3 prevL = default; int prevI = -1;
                for (int k = 0; k <= 120; k++)
                {
                    anim.Play(clip, 0, k / 120f);
                    anim.Update(0f);
                    Vector3 a = model.InverseTransformPoint(toes[0].position) * Tuning.STALKER_MODEL_SCALE, b = model.InverseTransformPoint(toes[1].position) * Tuning.STALKER_MODEL_SCALE;
                    foreach (var bn in bones) { float by = model.InverseTransformPoint(bn.position).y * Tuning.STALKER_MODEL_SCALE; if (by < lowest) { lowest = by; lowestName = bn.name; } }
                    int li = a.y <= b.y ? 0 : 1;
                    Vector3 l = li == 0 ? a : b;
                    if (li == prevI) smp.Add(new Vector2(l.y, -(l.z - prevL.z) / (len / 120f)));
                    prevI = li; prevL = l;
                }
                float minY = smp.Min(v => v.x);
                var pl = smp.Where(v => v.x <= minY + 0.05f).Select(v => v.y).ToList();
                Debug.Log($"ANIM stride {clip}: planted toe backward {pl.Average():F2} m/s (median {pl.OrderBy(v => v).ElementAt(pl.Count / 2):F2}, {pl.Count} of {smp.Count} samples), toe min y {minY:F2}, lowest bone {lowestName} y {lowest:F2} (model space × {Tuning.STALKER_MODEL_SCALE})");
            }
            if (clip == "roar")
            {
                float len = anim.runtimeAnimatorController.animationClips.First(c => c.name == "roar").length;
                for (float s = 0f; s <= len; s += 0.02f)
                {
                    anim.Play("roar", 0, s / len);
                    anim.Update(0f);
                    float d = Vector3.Distance(hands[0].position, hands[1].position);
                    if (d > best) { best = d; roarPeak = s; }
                }
            }
            string c0 = clip;
            yield return Sheet($"21_anim_{clip}_sheet", 12, i => PlayAt(anim, c0, i / 12f));
        }
        // ⑥b 3D-③b M1: 옛 걷기 / 새 걷기 나란히 — 같은 자리·같은 방향, 7 m 정면 · 2 m 옆, 한 주기 12장 (사용자가 비교한다)
        // 3D-③b M2: 옛 달리기 / 새 달리기도 같은 자리에서 (42_run_*)
        foreach (var (clip, tag) in new[] { ("walk_crouch", "22_walk_old"), ("walk_knuckle", "22_walk_new"), ("run", "42_run_old"), ("run_knuckle", "42_run_new"),
            ("glide_walk", "44_glide_walk"), ("glide_fast", "44_glide_fast"), ("glide_chase", "44_glide_chase") })
        {
            sa.manual = Array.IndexOf(StalkerAnim.ManualClips, clip);
            sa.freezeTime = false;
            st.Teleport(new Vector3(0f, 0.1f, 17f), 180f);
            Teleport(cc, new Vector3(0f, 0.1f, 10f), 0f);
            yield return new WaitForSeconds(Tuning.STALKER_ANIM_FADE_S + 0.2f);
            sa.freezeTime = true;
            string c0 = clip;
            yield return Sheet($"{tag}_7m_sheet", 12, i => PlayAt(anim, c0, i / 12f));
            st.Teleport(new Vector3(0.8f, 0.1f, 20f), 0f);
            Teleport(cc, new Vector3(-1.2f, 0.1f, 20f), 90f);
            yield return Sheet($"{tag}_2m_sheet", 12, i => PlayAt(anim, c0, i / 12f));
        }
        // ⑥c 3D-③b M1c 턱: 3.5 m 정면 · 3.1 m 옆(갱도 폭 안) — 대기 / 포효(두 손 가장 멀 때) / 잡기 가운데 + 7 m 포효 정면 (사용자가 본다). 2 m 는 머리가 화면 위로 잘렸다(09-19)
        if (jawTip != null)
        {
            lamp.lampOn = true;
            float roarLen = anim.runtimeAnimatorController.animationClips.First(c => c.name == "roar").length;
            foreach (var (clip, tag, at) in new[] { ("idle_crouch", "idle", 0.3f), ("roar", "roar", Mathf.Clamp01(roarPeak / roarLen)), ("attack_swipe", "catch", 0.5f) })
            {
                sa.manual = Array.IndexOf(StalkerAnim.ManualClips, clip);
                sa.freezeTime = false;
                st.Teleport(new Vector3(0f, 0.1f, 20f), 180f);
                Teleport(cc, new Vector3(0f, 0.1f, 16.5f), 0f);
                yield return new WaitForSeconds(Tuning.STALKER_ANIM_FADE_S + 0.3f);
                sa.freezeTime = true;
                anim.Play(clip, 0, at);
                yield return null;
                yield return Capture($"25_jaw_{tag}_front_3.5m", _ => { });
                st.Teleport(new Vector3(0.8f, 0.1f, 20f), 180f);
                Teleport(cc, new Vector3(-2.3f, 0.1f, 20f), 90f);
                yield return Capture($"25_jaw_{tag}_side_3.1m", _ => { });
                if (tag == "roar")
                {
                    Teleport(cc, new Vector3(0f, 0.1f, 13f), 0f);
                    yield return Capture("25_jaw_roar_7m", _ => { });
                }
                Debug.Log($"ANIM jaw capture {tag}: {sa.Current} jaw {sa.JawDeg:F1}°");
            }
        }
        // ⑥d 3D-③b M1d 머리 (DevHud G 와 같은 길 — 세운 괴물의 머리 시험): 몸 뒤 160° 의 나를 본다 · 갸웃 · 수색 끊어 돌림 + 사진
        {
            sa.manual = Array.IndexOf(StalkerAnim.ManualClips, "idle_crouch");
            sa.freezeTime = false;
            lamp.lampOn = true;
            Vector3 M0 = new Vector3(0f, 0.1f, 20f);
            float Flat3(Vector3 a, Vector3 b) { a.y = 0f; b.y = 0f; return Vector3.Angle(a, b); }
            // 몸은 +z(북)를 본다. 나는 몸 오른쪽 뒤 160°, 3.5 m — 갱도 폭 안
            st.Teleport(M0, 0f);
            Vector3 behind = M0 + Quaternion.Euler(0f, 160f, 0f) * Vector3.forward * 3.5f;
            behind.x = Mathf.Clamp(behind.x, -2.4f, 2.4f);
            Teleport(cc, behind, Quaternion.LookRotation(M0 - behind).eulerAngles.y);
            float ShYaw() { Vector3 l = model.InverseTransformDirection(Bone("RightArm").position - Bone("LeftArm").position); return Mathf.Atan2(l.z, Mathf.Abs(l.x)) * Mathf.Rad2Deg; }
            sa.headTest = 1;
            yield return new WaitForSeconds(0.6f);
            Vector3 toMe = cc.transform.position - M0;
            float faceBody = Flat3(sa.FaceDir, model.forward), faceErr = Flat3(sa.FaceDir, toMe), meBody = Flat3(toMe, model.forward);
            yield return Capture("26_head_follow_me_behind", _ => { });
            Check("anim_head_turns_past_human", faceBody >= meBody - 15f && faceBody >= 140f && faceErr <= 15f,
                $"body faces north, I stand {meBody:F0}° behind-right: face turned {faceBody:F0}° from body (want ≥ 140, human ≈ 80), {faceErr:F0}° off me (max 15), yaw max {sa.headYawMax:F0}°");
            // 3D-④ 5b: 머리를 크게 돌리면 상체(두 어깨를 잇는 선)가 늦게, 덜 따라 돈다 — 1.2 s 더 기다려 다 따라온 뒤에 잰다
            yield return new WaitForSeconds(1.2f);
            yield return new WaitForEndOfFrame();
            float shOn = ShYaw();
            bool torsoWas = sa.driveTorso;                            // 같은 자세에서 상체 따라가기만 껐다 켜서 그 몫만 잰다 (대기 동작이 입힌 어깨 방향은 빠진다)
            sa.driveTorso = false;
            yield return null;
            yield return new WaitForEndOfFrame();
            float shYaw = Mathf.Abs(Mathf.DeltaAngle(shOn, ShYaw()));
            sa.driveTorso = torsoWas;
            Check("anim_up_torso_follows_head", shYaw >= 12f && shYaw <= 35f && Mathf.Abs(sa.BodyYaw) <= Tuning.STALKER_UP_TORSO_MAX + 0.1f,
                $"head turned {faceBody:F0}°: shoulder line turned {shYaw:F0}° with it (want 12–35), torso drive {sa.BodyYaw:F0}° (max {Tuning.STALKER_UP_TORSO_MAX})");
            // 갸웃: 앞 3.5 m 에서 나를 보며
            st.Teleport(M0, 180f);
            Teleport(cc, M0 + Vector3.back * 3.5f, 0f);
            sa.headTest = 3;
            yield return new WaitForSeconds(0.6f);
            float tilt = Vector3.Angle(sa.HeadUpDir, model.up);
            yield return Capture("26_head_listen_tilt", _ => { });
            Check("anim_head_tilts", tilt >= sa.headTilt - 30f, $"head top leans {tilt:F0}° from body up (listen tilt {sa.headTilt:F0}°, want ≥ {sa.headTilt - 30f:F0} — pitch toward me eats some)");
            // 수색: 3 s 동안 얼굴 좌우를 프레임마다 — 움직임(프레임당 > 3°)이 시작하는 횟수 = 끊어 돌린 횟수
            sa.headTest = 2;
            yield return new WaitForSeconds(0.3f);
            int steps = 0, frames = 0, movingFrames = 0;
            bool wasMoving = false;
            float prevYaw = sa.HeadYaw;
            t = 0f;
            while (t < 3f)
            {
                yield return null;
                t += Time.deltaTime;
                float dYaw = Mathf.Abs(Mathf.DeltaAngle(prevYaw, sa.HeadYaw));
                prevYaw = sa.HeadYaw;
                bool moving = dYaw > 3f;
                if (moving && !wasMoving) steps++;
                if (moving) movingFrames++;
                wasMoving = moving;
                frames++;
            }
            Check("anim_head_search_steps", steps >= 5 && movingFrames <= frames / 2,
                $"search: head jumped {steps} times in 3 s (want ≥ 5), moving {movingFrames} of {frames} frames (want ≤ half — holds between jumps)");
            yield return Sheet("26_head_search_sheet", 12, i => Wait(0.1f));
            sa.headTest = 0;
            // ⑥e 3D-③b M1e 목 길게 빼기 (DevHud Z/X 와 같은 값 neckWant): 안 뺐을 때 마디가 등뼈 길 위 · 60 cm 빼기 · 갸웃하면 저절로 나옴 + 사진
            {
                st.Teleport(M0, 180f);
                Teleport(cc, M0 + Vector3.back * 3.5f, 0f);
                yield return new WaitForSeconds(0.6f);
                float gap0 = sa.HeadToExit;
                float off0 = sa.NeckOffPath();
                sa.manual = Array.IndexOf(StalkerAnim.ManualClips, "walk_knuckle");     // 등을 굽힌 자세에서도 길 위에
                yield return new WaitForSeconds(0.8f);
                float offBent = sa.NeckOffPath();
                sa.manual = Array.IndexOf(StalkerAnim.ManualClips, "idle_crouch");
                yield return new WaitForSeconds(0.6f);
                Check("anim_neck_hidden_at_rest", sa.HasNeck && sa.NeckOutNow <= 0f && off0 <= Tuning.STALKER_NECK_OFF_PATH_MAX && offBent <= Tuning.STALKER_NECK_OFF_PATH_MAX,
                    $"neck bones found {sa.HasNeck}, out {sa.NeckOutNow * 100f:F0} cm; joints off the head→exit→spine path: idle {off0 * 100f:F1} cm · bent-over walk {offBent * 100f:F1} cm (max {Tuning.STALKER_NECK_OFF_PATH_MAX * 100f:F0}, model units)");
                yield return Capture("34_neck_out_00cm", _ => { });
                sa.headTest = 1;                                                          // 나 따라보기 — 목은 얼굴이 보는 쪽으로 나온다
                foreach (int cm in new[] { 20, 40, 60 })
                {
                    sa.neckWant = cm / 100f;
                    yield return new WaitForSeconds(sa.neckOutS + 0.3f);
                    yield return Capture($"34_neck_out_{cm}cm", _ => { });
                }
                float grew = sa.HeadToExit - gap0;
                sa.NeckSpacing(out float dMin, out float dMax);
                float link = Tuning.STALKER_NECK_LEN_M / Tuning.STALKER_NECK_JOINTS;
                Check("anim_neck_extends", Mathf.Abs(grew - 0.6f) <= 0.05f && dMin >= 0.6f * link && dMax <= 1.05f * link && sa.NeckOffPath() <= Tuning.STALKER_NECK_OFF_PATH_MAX,
                    $"asked 60 cm: head moved {grew * 100f:F0} cm from the neck exit (want 60 ± 5), joints {dMin * 100f:F1}–{dMax * 100f:F1} cm apart (link {link * 100f:F1}), off path {sa.NeckOffPath() * 100f:F1} cm");
                sa.headTest = 0;                                                          // 옆 사진은 앞을 본 채로
                Teleport(cc, M0 + Vector3.left * 2.3f + Vector3.back * 0.5f, 90f);
                yield return new WaitForSeconds(0.5f);
                yield return Capture("34_neck_out_60cm_side", _ => { });
                Teleport(cc, M0 + Vector3.back * 3.5f, 0f);
                sa.neckWant = 0f;
                yield return new WaitForSeconds(sa.neckOutS + 0.3f);
                sa.headTest = 3;                                                          // 갸웃하며 나 보기 → 목이 저절로
                yield return new WaitForSeconds(1.0f);
                Check("anim_neck_frees_tilt", Mathf.Abs(sa.HeadTiltNow) >= 90f && sa.NeckOutNow >= Tuning.STALKER_NECK_TILT_OUT_M - 0.01f,
                    $"listen tilt {sa.HeadTiltNow:F0}°: neck came out by itself {sa.NeckOutNow * 100f:F0} cm (want {Tuning.STALKER_NECK_TILT_OUT_M * 100f:F0} — Blender self-check: at that length 0 head points inside the body)");
                yield return Capture("34_neck_tilt_auto", _ => { });
                sa.headTest = 0;
                yield return new WaitForSeconds(0.6f);
                // 사용자 판정 자리(09-19 "뚝 생겨난다 · 호스 같다 · 머리 밑이 뚫려 보인다"): 2 m 앞에서 올려다보며 0 → 15 cm, 1.2 m 밑에서 머리 밑
                {
                    float px1 = 1f / (Tuning.MOUSE_SENSITIVITY * Mathf.Rad2Deg);
                    sa.headTest = 1;
                    Teleport(cc, M0 + Vector3.back * 2f, 0f);
                    player.Look(new Vector2(0f, 35f * px1));
                    yield return new WaitForSeconds(0.6f);
                    float keepS = sa.neckOutS;
                    sa.neckOutS = 0.3f * Tuning.STALKER_NECK_OUT_MAX_M / Tuning.STALKER_NECK_OUT_M;   // 15 cm 가 0.3 s 에 걸쳐 나오게 (연속 사진용)
                    sa.neckWant = Tuning.STALKER_NECK_OUT_M;
                    yield return Sheet("35_neck_pop_2m_sheet", 8, i => Wait(0.05f));
                    sa.neckOutS = keepS;
                    yield return Capture("35_neck_15cm_2m_up", _ => { });
                    player.Look(new Vector2(0f, -35f * px1));
                    Teleport(cc, M0 + Vector3.back * 1.2f, 0f);
                    player.Look(new Vector2(0f, 60f * px1));
                    yield return new WaitForSeconds(0.5f);
                    yield return Capture("35_neck_15cm_under_1.2m", _ => { });
                    Teleport(cc, M0 + Vector3.back * 1.0f + Vector3.right * 0.9f, -40f);
                    yield return new WaitForSeconds(0.5f);
                    yield return Capture("35_neck_15cm_under_side", _ => { });
                    player.Look(new Vector2(0f, -60f * px1));
                    sa.neckWant = 0f; sa.headTest = 0;
                    Teleport(cc, M0 + Vector3.back * 3.5f, 0f);
                    yield return new WaitForSeconds(0.6f);
                }
            }
            // 갱목·못·가죽끈 사진 (09-19): 등 뒤 2 m · 왼팔 2 m · 등 뒤 7 m — 머리 시험 끔, 대기 자세
            st.Teleport(M0, 0f);
            Teleport(cc, M0 + Vector3.back * 2f + Vector3.right * 0.3f, 0f);
            yield return Capture("30_timber_back_2m", _ => { });
            Teleport(cc, M0 + Vector3.left * 2f + Vector3.forward * 0.3f, 90f);
            yield return Capture("30_timber_forearm_2m", _ => { });
            Teleport(cc, M0 + Vector3.back * 7f, 0f);
            yield return Capture("30_timber_back_7m", _ => { });
        }
        sa.freezeTime = false;
        sa.manual = 0;

        // ⑦ 판정 키 (사람 길 = 가상 키보드): 9 로 세우고 U → 8 m 에서 걸어오기, U 마다 배회 걸음 B → C → D → A 가 동작에 먹는다 (사용자 09-18 "U 가 적용 안 된다")
        var hud = GetComponent<DevHud>();
        var kb = InputSystem.AddDevice<Keyboard>("AnimKeyboard");
        hud.enabled = true;
        Teleport(cc, new Vector3(0f, 0.1f, 6f), 0f);
        yield return null;
        yield return PressKey(kb, Key.Digit9);
        int g0 = sa.gait;
        var gaitSeen = new List<string>();
        bool gaitOk = true;
        for (int i = 0; i < Tuning.STALKER_GAIT_COUNT; i++)
        {
            yield return PressKey(kb, Key.U);
            yield return new WaitForSeconds(0.8f);
            gaitSeen.Add($"{StalkerAnim.GaitName(sa.gait)} = {sa.Current} x{sa.Rate:F2} at {sa.Speed:F1} m/s");
            gaitOk &= hud.walkPreview && sa.Speed > 2f && (sa.gait == 5 ? sa.Current == "up_walk" && sa.Rate > 1.2f && sa.Rate < 1.5f
                : sa.gait == 1 ? sa.Current == sa.RunClip && sa.Rate < 0.8f
                : sa.gait == 2 ? sa.Current == "walk_crouch" && Mathf.Abs(sa.Rate - Tuning.STALKER_WALK_RATE_CAP) < 0.05f
                : sa.gait == 3 ? sa.Current == "walk_knuckle" && Mathf.Abs(sa.Rate - 1f) < 0.2f
                : sa.gait == 4 ? sa.Current == "glide_walk" && Mathf.Abs(sa.Rate - 1f) < 0.2f
                : sa.Current == "walk_crouch" && sa.Rate > 3f);
        }
        Check("anim_gait_key_walks_in", gaitOk && sa.gait == g0, string.Join(" · ", gaitSeen) + $", preview {hud.walkPreview}");
        yield return PressKey(kb, Key.Digit9);
        hud.enabled = false;
        Check("anim_roar_peak_in_alert", roarPeak >= Tuning.STALKER_ROAR_START_S && roarPeak <= Tuning.STALKER_ROAR_START_S + Tuning.STALKER_ALERT_S,
            $"hands farthest apart ({best:F2} m) at {roarPeak:F2} s of roar; alert plays {Tuning.STALKER_ROAR_START_S:F2}–{Tuning.STALKER_ROAR_START_S + Tuning.STALKER_ALERT_S:F2} s");
        // ⑧ 3D-③b M1d: 배회하다 소리를 들으면 머리가 먼저 확 꺾인다 (몸보다 먼저) + 갸웃, 그 뒤 수색에선 끊어 돌린다. 램프 끔, 나는 몸 뒤(눈 원뿔 밖)
        {
            lamp.lampOn = false;
            st.enabled = true;
            Vector3 W0 = new Vector3(0f, 0.1f, 22f);
            st.Teleport(W0, 0f);
            Teleport(cc, W0 + Vector3.back * 7f, 0f);
            player.frozen = true;
            yield return new WaitForSeconds(0.15f);                   // 배회가 몸을 돌리기 전에 — 소리는 몸 오른쪽 뒤
            Vector3 noise = W0 + Quaternion.Euler(0f, 120f, 0f) * Vector3.forward * 6f;
            noise.x = Mathf.Clamp(noise.x, -2.4f, 2.4f);
            NoiseBus.Make(noise, 20f, "check_head", null);
            float headFirst = 99f, bodyThen = 0f, tiltMax = 0f, snapT = 99f, heMin = 999f, beAtMin = 0f, tAtMin = 0f;
            t = 0f;
            while (t < 0.6f)
            {
                yield return new WaitForEndOfFrame();
                t += Time.deltaTime;
                Vector3 toN = noise - model.position; toN.y = 0f;
                Vector3 f = sa.FaceDir; f.y = 0f;
                Vector3 b = model.forward; b.y = 0f;
                float he = Vector3.Angle(f, toN), be = Vector3.Angle(b, toN);
                if (he < heMin) { heMin = he; beAtMin = be; tAtMin = t; }
                // 몸도 빨리 돈다(0.15 s 에 110°) — 머리가 앞서는 폭은 25~40° 를 오간다. 30° 문턱은 새 달리기에서 26~27° 로 아깝게 빠졌다(09-19 시간대별 기록) → 20°. 목을 굳히면(stiffneck) 0° 라 여전히 FAIL
                if (he <= 20f && be >= he + 20f && t < snapT) { snapT = t; headFirst = he; bodyThen = be; }
                tiltMax = Mathf.Max(tiltMax, Vector3.Angle(sa.HeadUpDir, model.up));
            }
            string heard = $"{st.state} heard '{st.lastHeard}'";
            string invClip = sa.Current; float invRate = sa.Rate;
            Check("anim_up_clip_by_speed", glideNames == "up_walk/up_jog/up_run" && invClip == "up_jog" && Mathf.Abs(invRate - 1f) <= 0.08f
                    && Mathf.Abs(glideWalkRate - 1f) <= 0.05f && Mathf.Abs(glideChaseRate - 1f) <= 0.05f && Mathf.Abs(glideRetreatRate - 0.8f) <= 0.05f,
                $"clips wander/retreat/chase = {glideNames} (want up_walk/up_jog/up_run) · median rates wander x{glideWalkRate:F2} · chase x{glideChaseRate:F2} (want 0.95–1.05) · retreat x{glideRetreatRate:F2} (want 0.75–0.85) · investigate 0.6 s in: {invClip} x{invRate:F2} (want up_jog x0.92–1.08)");
            Check("anim_head_snaps_to_noise", snapT <= 0.3f && tiltMax >= sa.headTilt - 30f,
                $"{heard}: head within {headFirst:F0}° of the noise {snapT:F2} s after it (max 0.3) while the body was still {bodyThen:F0}° off · head top leaned up to {tiltMax:F0}° (listen tilt {sa.headTilt:F0}) · closest head {heMin:F0}° at {tAtMin:F2} s with body {beAtMin:F0}° off, clip {sa.Current}");
            t = 0f;
            while (st.state != Stalker.State.Search && t < 15f) { t += Time.deltaTime; yield return null; }
            // 첫 수색 자리에서는 STALKER_GROPE_S 6 s 동안 웅크려 더듬는다(09-20) — 그동안 머리는 옮기는 손을 천천히 따라가(mode 6) 끊어 돌리지 않는다 → 더듬기가 끝난 뒤를 잰다
            t = 0f;
            while (st.state == Stalker.State.Search && st.Groping && t < Tuning.STALKER_GROPE_S + 3f) { t += Time.deltaTime; yield return null; }
            int steps = 0, frames = 0;
            bool wasMoving = false;
            float prevYaw = sa.HeadYaw;
            t = 0f;
            // 머무는 시간이 0.6~1.2 s 무작위라 3 s 에 2~5번 — 6 s 안에 4번이면 통과(4번 채우면 바로 끝)
            while (t < 6f && steps < 4 && (st.state == Stalker.State.Search || sa.HeadMode == 2) && !st.Groping)      // 수색이 끝나도 서서 둘러보는 동안(mode 2)은 같은 머리 규칙
            {
                yield return null;
                t += Time.deltaTime;
                float dYaw = Mathf.Abs(Mathf.DeltaAngle(prevYaw, sa.HeadYaw) - 0f);
                prevYaw = sa.HeadYaw;
                bool moving = dYaw > 3f;
                if (moving && !wasMoving) steps++;
                wasMoving = moving;
                frames++;
            }
            Check("anim_head_search_in_behavior", steps >= 4,
                $"real search after the grope ({st.state}, groping {st.Groping}): head jumped {steps} times in {t:F1} s (want 4 within 6 s)");
            player.frozen = false;
            lamp.lampOn = true;
        }
        st.enabled = true;
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));
    }

    static IEnumerator Wait(float s) { yield return new WaitForSeconds(s); }

    static IEnumerator PlayAt(Animator a, string clip, float normalized)
    {
        a.Play(clip, 0, normalized);
        yield return null;
    }

    // 화면을 count 번 찍어 4열 격자 한 장으로 (한 칸 = 화면 1/4 크기). step(i) 가 매 장 앞에서 자리·시간을 정한다
    IEnumerator Sheet(string name, int count, Func<int, IEnumerator> step)
    {
        const int cols = 4;
        int rows = (count + cols - 1) / cols;
        int tw = Screen.width / 4, th = Screen.height / 4;
        var sheet = new Texture2D(tw * cols, th * rows, TextureFormat.RGB24, false);
        var tile = new Color32[tw * th];
        for (int i = 0; i < count; i++)
        {
            yield return step(i);
            yield return new WaitForEndOfFrame();
            var tex = ScreenCapture.CaptureScreenshotAsTexture();
            var src = tex.GetPixels32();
            for (int y = 0; y < th; y++)
                for (int x = 0; x < tw; x++)
                    tile[y * tw + x] = src[Mathf.Min(y * 4, tex.height - 1) * tex.width + Mathf.Min(x * 4, tex.width - 1)];
            Destroy(tex);
            sheet.SetPixels32((i % cols) * tw, (rows - 1 - i / cols) * th, tw, th, tile);
        }
        sheet.Apply();
        File.WriteAllBytes(Path.Combine(outDir, name + ".png"), sheet.EncodeToPNG());
        Destroy(sheet);
    }

    // M4: 눈·빛·추격·잡기. 플레이어는 z 10 에서 +Z 를 본다. 괴물은 앞(+Z)이나 뒤(-Z)에 놓고 플레이어 쪽을 보게 한다
    // m3-③ M1 램프 미끼 (제안서 docs/제안서_m3_눈_발광_램프_미끼_갱목.md): 멀면 안전모 램프, 가까우면 램프가 꺼지고 → 어둠 → 눈.
    // 괴물 행동은 끄고(거리 규칙만 잰다) 내 램프도 끈다 — 화면에서 0.1 을 넘는 것은 괴물의 발광뿐이다. 상태 규칙(추격 중엔 꺼짐)은 ⑤ 에서 행동을 켜고 잰다.
    IEnumerator LureStage(CharacterController cc)
    {
        var st = stalker;
        var look = st.GetComponentInChildren<StalkerLook>();
        var camMain = pickaxe.cam.GetComponent<Camera>();
        Vector3 P = new Vector3(0f, 0.1f, 4f), fwd = Vector3.forward;
        if (look == null || !look.HasLamp)
        {
            Check("lure_lamp_visible_far", false, "this body has no lamp glass material ('램프_유리') — lure cannot run");
            yield break;
        }
        st.enabled = false;
        lamp.lampOn = false;
        Teleport(cc, P, 0f);
        float off = look.lureOffM, on = off + (Tuning.STALKER_LURE_ON_M - Tuning.STALKER_LURE_OFF_M);
        Vector3 v = default;

        // ① 멀리서 불빛이 보인다 (30 · 25 · 20 · 15 m 기록, 25 m 로 판정) — 눈은 꺼져 있다
        var far = new List<string>(); int bright25 = 0; float eye25 = 1f, lamp25 = 0f;
        foreach (float d in new[] { 30f, 25f, 20f, 15f })
        {
            st.Teleport(P + fwd * d, 180f);
            yield return new WaitForSeconds(1.2f);
            yield return Capture($"40_lure_{d:0}m", x => v = x, ScreenRect(camMain, look.Renderers));
            far.Add($"{d:0} m: {lastBright} px lum {v.x:F4}");
            if (d == 25f) { bright25 = lastBright; eye25 = look.EyeNow; lamp25 = look.LampNow; }
        }
        lamp.lampOn = true;                      // 내 램프를 켠 채로도 (평소 안개 0.03 · 램프 사거리 14 m 밖이라 괴물 몸은 안 보인다)
        st.Teleport(P + fwd * 25f, 180f);
        yield return new WaitForSeconds(1.2f);
        yield return Capture("40_lure_25m_mylamp_on", x => v = x, ScreenRect(camMain, look.Renderers));
        far.Add($"25 m with my lamp on: {lastBright} px");
        int bright25On = lastBright;
        lamp.lampOn = false;
        yield return new WaitForSeconds(0.3f);
        Check("lure_lamp_visible_far", bright25 >= Tuning.STALKER_LURE_BRIGHT_MIN_25M && bright25On >= Tuning.STALKER_LURE_BRIGHT_MIN_25M && lamp25 >= 0.99f && eye25 <= 0.01f,
            $"my lamp off, bright samples in the model region — {string.Join(" · ", far)} (25 m min {Tuning.STALKER_LURE_BRIGHT_MIN_25M}); at 25 m lamp {lamp25:F2} eyes {eye25:F2}");

        // ② 꺼지는 거리: off + 0.6 m 에서는 켜진 채, off − 0.6 m 에서 꺼진다 → 어둠 → 눈. 프레임마다 잰다
        st.Teleport(P + fwd * (off + 0.6f), 180f);
        yield return new WaitForSeconds(1.2f);
        bool stillOn = look.LampNow >= 0.99f;
        st.Teleport(P + fwd * (off - 0.6f), 180f);
        float t = 0f, tLampOff = -1f, tEyeStart = -1f, tEyeFull = -1f, dark = 0f;
        while (t < 3f)
        {
            yield return null; t += Time.deltaTime;
            if (tLampOff < 0f && look.LampNow <= 0f) tLampOff = t;
            if (look.LampNow <= 0f && look.EyeNow <= 0f) dark += Time.deltaTime;
            if (tLampOff >= 0f && tEyeStart < 0f && look.EyeNow > 0f) tEyeStart = t;
            if (tEyeFull < 0f && look.EyeNow >= 1f) tEyeFull = t;
        }
        Check("lure_lamp_dies_then_eyes", stillOn && tLampOff >= 0f && tLampOff <= Tuning.STALKER_LURE_FLICKER_S + 0.1f && Mathf.Abs(dark - Tuning.STALKER_LURE_GAP_S) <= 0.12f && tEyeFull > tLampOff && tEyeFull <= 2f,
            $"at {off + 0.6f:F1} m lamp still on {stillOn}; stepped to {off - 0.6f:F1} m: lamp out after {tLampOff:F2} s (max {Tuning.STALKER_LURE_FLICKER_S + 0.1f:F2}), total darkness {dark:F2} s (want {Tuning.STALKER_LURE_GAP_S} ± 0.12), eyes start {tEyeStart:F2} s · full {tEyeFull:F2} s");
        yield return Sheet("41_lure_switch_sheet", 8, i => i == 0 ? Relight(st, look, P + fwd * (off + 3f), P + fwd * (off - 0.6f)) : Wait(0.18f));

        // ③ 경계에서 안 깜빡인다: 꺼진 뒤 off + 2 m 로 물러나도 꺼진 채, on + 0.6 m 에서 다시 켜진다
        st.Teleport(P + fwd * (off - 0.6f), 180f);
        yield return new WaitForSeconds(1.6f);
        st.Teleport(P + fwd * (off + 2f), 180f);
        yield return new WaitForSeconds(1.5f);
        float lampMid = look.LampNow, eyeMid = look.EyeNow;
        st.Teleport(P + fwd * (on + 0.6f), 180f);
        yield return new WaitForSeconds(1.5f);
        Check("lure_no_flicker_at_edge", lampMid <= 0.01f && eyeMid >= 0.99f && look.LampNow >= 0.99f && look.EyeNow <= 0.01f,
            $"after going dark, back at {off + 2f:F0} m: lamp {lampMid:F2} eyes {eyeMid:F2} (want 0 / 1); at {on + 0.6f:F1} m: lamp {look.LampNow:F2} eyes {look.EyeNow:F2} (want 1 / 0)");

        // ④ 눈이 어둠 속에서 보인다 (5 m) — 기존 stalker_eyes_glow_in_dark 와 같은 잣대
        st.Teleport(P + fwd * 5f, 180f);
        yield return new WaitForSeconds(2f);
        yield return Capture("42_lure_eyes_5m", x => v = x, ScreenRect(camMain, look.Renderers));
        Check("lure_eyes_glow_near", lastBright >= Tuning.STALKER_EYE_BRIGHT_MIN && look.LampNow <= 0f, $"5 m, my lamp off: bright samples {lastBright} (min {Tuning.STALKER_EYE_BRIGHT_MIN}), lamp {look.LampNow:F2} eyes {look.EyeNow:F2}");

        // ⑤ 추격 중에는 멀어도 램프가 꺼져 있다: 갱도 끝에서 내 램프를 켜고 8 m 로 추격을 건 뒤, 내가 반대 끝(26 m 밖)으로 옮겨 간다 — 추격은 놓칠 때까지 3 s 남는다
        Vector3 P2 = new Vector3(0f, 0.1f, 34f);
        st.enabled = true;
        lamp.lampOn = true;
        Teleport(cc, P2, 180f);
        st.Teleport(P2 - fwd * 8f, 0f);
        t = 0f;
        while (st.state != Stalker.State.Chase && t < 4f) { t += Time.deltaTime; yield return null; }
        bool chasing = st.state == Stalker.State.Chase;
        lamp.lampOn = false;
        Teleport(cc, new Vector3(0f, 0.1f, 0f), 0f);
        float lampMaxChase = 0f, farMin = 99f; t = 0f;
        while (st.state == Stalker.State.Chase && t < 2f) { t += Time.deltaTime; lampMaxChase = Mathf.Max(lampMaxChase, look.LampNow); farMin = Mathf.Min(farMin, st.DistToPlayer); yield return null; }
        Check("lure_lamp_off_in_chase", chasing && t >= 1f && farMin > look.lureOffM + 5f && lampMaxChase <= 0f, $"chase started {chasing}; I moved {farMin:F0} m away, still chasing for {t:F1} s: brightest lamp {lampMaxChase:F2} (want 0)");
        st.enabled = true;                                 // 끈 채 두면 다음 절(ChaseStage)에서 괴물이 서서 못 본다 — 전체 build.sh 에서 7개 FAIL(09-22, -only 로는 안 걸렸다)
        lamp.lampOn = true;
        st.Teleport(st.homePos);
    }

    // 연속 사진 첫 장 앞: 먼 데서 램프를 켜 두었다가 꺼지는 거리 안으로 옮긴다
    IEnumerator Relight(Stalker st, StalkerLook look, Vector3 farPos, Vector3 nearPos)
    {
        st.Teleport(farPos + Vector3.forward * 6f, 180f);
        yield return new WaitForSeconds(1.5f);
        st.Teleport(nearPos, 180f);
    }

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
        yield return new WaitForSeconds(Tuning.STALKER_LURE_FLICKER_S + Tuning.STALKER_LURE_GAP_S + Tuning.STALKER_LURE_FADE_S + 0.4f);   // m3-③: 먼 데서 옮겨 오면 램프가 꺼지고 → 어둠 → 눈이 켜질 때까지
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
        var lureLook = st.GetComponentInChildren<StalkerLook>();
        if (lureLook != null) lureLook.lure = false;      // 이 절은 살 모습만 잰다(14 m 에서 어두운가 등) — 램프 미끼가 켜져 있으면 14 m 에서 빛난다. 미끼는 LureStage 가 사람 경로로 잰다
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
        // 갱목·못·가죽끈 (09-19 timber_detail.py): 재질마다 색·요철·반들거림 그림 — 상자에 사진만 입힌 옛 모습(반들거림 없음)으로 돌아가면 FAIL
        var propMats = new List<Material>();
        if (modelOn)
            foreach (var r in model.GetComponentsInChildren<Renderer>())
                foreach (var m in r.sharedMaterials)
                    if (m != null && (m.name.StartsWith("뒤틀린_갱목") || m.name.StartsWith("녹슨_주철") || m.name.StartsWith("가죽끈")) && !propMats.Contains(m)) propMats.Add(m);
        if (flatProps)                                   // 사보타주 flatprops: 반들거림 그림을 뺀다
            foreach (var m in propMats) m.SetTexture("metallicRoughnessTexture", null);
        int propFull = propMats.Count(m => m.GetTexture("baseColorTexture") != null && m.GetTexture("normalTexture") != null && m.GetTexture("metallicRoughnessTexture") != null);
        Check("monster_props_pbr", propMats.Count >= 5 && propFull == propMats.Count,
            $"timber/nail/strap materials {propMats.Count} (want ≥ 5), with colour + normal + roughness maps {propFull}: {string.Join(", ", propMats.Select(m => m.name))}");
        Check("monster_model_animated_with_normals", modelOn && clipCount == Tuning.STALKER_CLIP_COUNT && idle && normals,
            $"model {(model == null ? "none" : modelOn ? "on" : "off")}, clips {clipCount} (want {Tuning.STALKER_CLIP_COUNT}), playing {Tuning.STALKER_MODEL_IDLE} {idle}, skin materials {skinMats.Count} with normal map {normals}");

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

        if (lureLook != null) lureLook.lure = true;
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
        Check("stalker_two_hits_arrives_2m", st.hits == 2 && st.state == Stalker.State.Search && toPocket < Tuning.STALKER_NOISE_SAME_M && t < 6f,
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

    public static void Finish()
    {
        string summary = fails.Count == 0 ? "CHECK ALL PASS" : "CHECK FAILED: " + string.Join(", ", fails);
        Debug.Log(summary);
        Application.Quit(fails.Count == 0 ? 0 : 1);
    }

    public static void Check(string name, bool ok, string value)
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
