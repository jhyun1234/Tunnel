using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using Unity.AI.Navigation;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.UI;

// 마일스톤 1·2 씬 만들기와 Windows 빌드. 배치 모드에서 부른다 (명령은 docs/HANDOFF.md, tools/build.sh).
public static class BuildM1
{
    const string ScenePath = "Assets/Scenes/M1_Tunnel.unity";
    const string BoothScenePath = "Assets/Scenes/" + Tuning.BOOTH_SCENE + ".unity";   // MAP1 부스 한 층 — MakeBooth 가 만든다, 인트로 "시작"이 여기로
    const string BoothMapPath = "Assets/Tunnel/Pieces/booth_map.gltf";                  // blender/map/make_booth.py
    const string BoothNavPath = "Assets/Scenes/Booth_NavMesh.asset";
    const string BulbOnMatPath = "Assets/Settings/M9_BulbOn.mat";
    const string BulbOffMatPath = "Assets/Settings/M9_BulbOff.mat";
    const string IntroScenePath = "Assets/Scenes/Intro.unity";   // UI-2 인트로 (지스타 지침 1-1) — MakeIntro 가 만든다, 빌드 0번
    const string FontPath = "Assets/Fonts/Pretendard-Regular.otf"; // 한글 글꼴 (OFL, 같은 폴더 LICENSE_Pretendard_OFL.txt)
    const string LogoUnivPath = "Assets/UI/logo_university.png";   // 회색 자리표시 — 센터가 주는 원본으로 바꾼다 (임의 변형 금지)
    const string LogoCenterPath = "Assets/UI/logo_center.png";
    const string PiecePath = "Assets/Tunnel/Pieces/piece_straight" + Tuning.PIECE_SUFFIX + ".gltf";      // A1: _v2 = Meshy 갱목·갓등 (blender/map/piece_v2.py)
    const string GapBigPath = "Assets/Tunnel/Pieces/piece_gap_big" + Tuning.PIECE_SUFFIX + ".gltf";      // 3D-④ MR1 맵: 큰 벽 틈(괴물 굴) · 작은 벽 틈(플레이어 전용) — blender/map/make_gaps.py
    const string GapSmallPath = "Assets/Tunnel/Pieces/piece_gap_small" + Tuning.PIECE_SUFFIX + ".gltf";
    const string ProfilePath = "Assets/Settings/M1_Volume.asset";
    const string RendererPath = "Assets/Settings/PC_Renderer.asset";
    const string ExePath = "build/Tunnel/Tunnel.exe";
    const string PickPath = Tuning.PICK_MODEL;          // A1: Assets/Tunnel/Props/pickaxe.glb (blender/props/fit_prop.py)
    const string OrePath = "Assets/Tunnel/Pieces/ore.gltf";
    const string ChipsPath = "Assets/Tunnel/Pieces/mine_chips.gltf";
    const string DustMatPath = "Assets/Settings/M2_Dust.mat";
    const string ArtTexDir = "Assets/Tunnel/Art/textures/";            // ART-1 CC0 질감 (Assets/Tunnel/Art/SOURCES.md)
    const string MineRockMatPath = "Assets/Tunnel/Art/M11_MineRock.mat";
    const string ArtProfilePath = "Assets/Settings/M11_BoothVolume.asset";
    // 기본 = 새 몸 m3(Meshy 부위 조립, tools/bake_m3.sh — 사용자 판정 통과 09-22). 옛 TRELLIS 몸은 TUNNEL_MONSTER=Assets/Tunnel/Monster/miner_rigged.glb 로 (검사 문턱은 m3 값)
    static readonly string MonsterPath = Environment.GetEnvironmentVariable("TUNNEL_MONSTER") ?? "Assets/Tunnel/Monster/miner_m3.glb";   // 3D-①: stage12_unity_glb.py 산출 (Documents/MineTunnel)
    const string StalkerAnimPath = "Assets/Settings/M8_StalkerAnim.controller";
    const string CrackMatPath = "Assets/Settings/M5_Crack.mat";
    const string PickGlowMatPath = "Assets/Settings/M7_PickGlow.mat";
    const string HitSoundDir = "Assets/Audio/PickHit";   // Kenney Impact Sounds impactMining_* (CC0)
    const string PlayerSoundDir = "Assets/Audio/Player";  // 발소리·착지 (Freesound CC0, SOURCES.txt)
    const int PieceCount = 6;              // 직선 조각 한 종류를 줄지어 42 m — 달리기 판정 길이 + 이음새 확인

    public static void MakeScene() => Make(false);
    // MAP1: 같은 씬 생성기로 부스 맵을. 공유 에셋(볼륨 프로필·동작 상태기·재질)은 새로 만들지 않고 읽는다 — 새로 만들면 GUID 가 바뀌어 복도 씬 참조가 끊긴다
    public static void MakeBooth() => Make(true);

    static T LoadOr<T>(bool reuse, string path, Func<T> make) where T : UnityEngine.Object
        => reuse && AssetDatabase.LoadAssetAtPath<T>(path) is T a ? a : make();

    static void Make(bool booth)
    {
        string scenePath = booth ? BoothScenePath : ScenePath;
        if (File.Exists(scenePath) && !Environment.GetCommandLineArgs().Contains("-force"))
        {
            Debug.LogError($"{scenePath} 가 이미 있다 — 덮어쓰려면 -force");
            EditorApplication.Exit(2);
            return;
        }
        var piece = AssetDatabase.LoadAssetAtPath<GameObject>(PiecePath);
        var gapBig = AssetDatabase.LoadAssetAtPath<GameObject>(GapBigPath);
        var gapSmall = AssetDatabase.LoadAssetAtPath<GameObject>(GapSmallPath);
        var pick = AssetDatabase.LoadAssetAtPath<GameObject>(PickPath);
        var ore = AssetDatabase.LoadAssetAtPath<GameObject>(OrePath);
        var chips = AssetDatabase.LoadAssetAtPath<GameObject>(ChipsPath);
        var monster = AssetDatabase.LoadAssetAtPath<GameObject>(MonsterPath);
        if (piece == null || gapBig == null || gapSmall == null || pick == null || ore == null || chips == null || monster == null)
        {
            Debug.LogError("piece_straight / pick / ore / mine_chips / miner_rigged glTF 를 못 읽었다 (glTFast 임포트 확인)");
            EditorApplication.Exit(3);
            return;
        }
        var hitClips = AssetDatabase.FindAssets("t:AudioClip", new[] { HitSoundDir })
            .Select(g => AssetDatabase.LoadAssetAtPath<AudioClip>(AssetDatabase.GUIDToAssetPath(g))).ToArray();
        if (hitClips.Length == 0)
        {
            Debug.LogError($"{HitSoundDir} 에 소리 파일이 없다");
            EditorApplication.Exit(4);
            return;
        }
        AudioClip[] Clips(string prefix) => AssetDatabase.FindAssets("t:AudioClip", new[] { PlayerSoundDir })
            .Select(g => AssetDatabase.LoadAssetAtPath<AudioClip>(AssetDatabase.GUIDToAssetPath(g)))
            .Where(c => c.name.StartsWith(prefix)).OrderBy(c => c.name).ToArray();
        AudioClip[] stepClips = Clips("step_dirt"), crouchClips = Clips("step_crouch"), landClips = Clips("pick_land"), fleshClips = Clips("pick_flesh");
        if (stepClips.Length < 4 || crouchClips.Length == 0 || landClips.Length == 0 || fleshClips.Length == 0)
        {
            Debug.LogError($"{PlayerSoundDir} 에 step_dirt 4 · step_crouch · pick_land · pick_flesh 가 없다 (tools/cut_sounds.py)");
            EditorApplication.Exit(5);
            return;
        }

        AddFogFeature();
        var profile = LoadOr(booth, ProfilePath, MakeProfile);
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        // 공기 (LOOK_REFERENCE 4-3, 4-4). 태양·하늘·반사 없음 — 빛은 헤드램프 하나
        RenderSettings.skybox = null;
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = Tuning.AMBIENT_COLOR * Tuning.AMBIENT_ENERGY;
        RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
        RenderSettings.reflectionIntensity = 0f;
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.Exponential;
        RenderSettings.fogDensity = Tuning.FOG_DENSITY;
        RenderSettings.fogColor = Tuning.FOG_COLOR;

        // 갱도: 조각의 COL_* 노드를 충돌로, 보이지 않게. 부스 = 한 덩어리 맵 + 길찾기 바닥
        Transform pieces;
        GameObject[] blocks = new GameObject[0];
        if (booth)
            pieces = PlaceBoothMap(out blocks);
        else
        {
        pieces = new GameObject("Pieces").transform;
        for (int i = 0; i < PieceCount; i++)
        {
            var kind = Tuning.MAP_GAP_BIG_PIECES.Contains(i) ? gapBig : Tuning.MAP_GAP_SMALL_PIECES.Contains(i) ? gapSmall : piece;
            var go = Instance(kind, pieces);
            go.name = $"{kind.name}_{i}";
            go.transform.position = new Vector3(0f, 0f, i * Tuning.GRID_CELL);
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            {
                if (!mf.name.StartsWith("COL_")) continue;
                mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
                UnityEngine.Object.DestroyImmediate(mf.GetComponent<MeshRenderer>());
            }
        }
        EndWall(pieces, "End_S", -Tuning.GRID_CELL * 0.5f);
        EndWall(pieces, "End_N", (PieceCount - 0.5f) * Tuning.GRID_CELL);
        }

        // 광맥 포켓: 조각의 SLOT_Pocket_* 자리마다 POCKET_CHANCE 로 (Godot PocketSpawner.gd). 통로 쪽 = 자리에서 조각 원점 쪽
        var rng = new System.Random(Tuning.MAP_SEED + 100);
        var pocketsRoot = new GameObject("Pockets").transform;
        foreach (var slot in pieces.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("SLOT_Pocket_")).ToArray())
        {
            if (rng.NextDouble() >= Tuning.POCKET_CHANCE)
                continue;
            var pieceRoot = slot;
            while (pieceRoot.parent != pieces && pieceRoot.parent != null)
                pieceRoot = pieceRoot.parent;
            Vector3 outDir = pieceRoot.position - slot.position;             // 조각: 통로 쪽 = 조각 원점 쪽
            if (booth && NavMesh.SamplePosition(slot.position, out NavMeshHit nh, 4f, NavMesh.AllAreas))
                outDir = nh.position - slot.position;                          // 부스: 가장 가까운 걷는 바닥 쪽
            outDir.y = 0f;
            outDir.Normalize();
            var go = new GameObject("OrePocket");
            go.transform.SetParent(pocketsRoot);
            go.transform.SetPositionAndRotation(slot.position + outDir * Tuning.POCKET_WALL_OUT,
                Quaternion.Euler((float)rng.NextDouble() * 360f, (float)rng.NextDouble() * 360f, (float)rng.NextDouble() * 360f));
            go.AddComponent<SphereCollider>().radius = Tuning.POCKET_RADIUS;
            var pocketMesh = Instance(ore, go.transform);
            pocketMesh.transform.localScale = Vector3.one * Tuning.POCKET_MESH_SCALE;
            var pocket = go.AddComponent<OrePocket>();
            pocket.mesh = pocketMesh.transform;
            pocket.outDir = outDir;
        }

        // 플레이어
        var player = new GameObject("Player");
        player.transform.position = new Vector3(0f, 0.1f, 0f);
        if (booth)
        {
            Vector3 sp = Find(pieces, "SPAWN_Player").position, lookAt = Find(pieces, "LOOK_Player").position;
            player.transform.SetPositionAndRotation(sp + Vector3.up * 0.1f, Quaternion.LookRotation(Vector3.ProjectOnPlane(lookAt - sp, Vector3.up)));
        }
        player.AddComponent<CharacterController>();
        var p = player.AddComponent<Player>();
        var head = new GameObject("Head").transform;
        head.SetParent(player.transform, false);
        head.localPosition = new Vector3(0f, Tuning.EYE_HEIGHT, 0f);
        p.head = head;
        var camGo = new GameObject("Camera") { tag = "MainCamera" };
        camGo.transform.SetParent(head, false);
        var cam = camGo.AddComponent<Camera>();
        cam.fieldOfView = Tuning.CAMERA_FOV;
        cam.nearClipPlane = 0.05f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Tuning.BACKGROUND;
        cam.cullingMask = ~(1 << Pickaxe.ViewModelLayer);
        var camData = camGo.AddComponent<UniversalAdditionalCameraData>();
        camData.renderPostProcessing = true;
        camGo.AddComponent<AudioListener>();

        // 곡괭이는 오버레이 카메라가 따로 그린다 — 벽 속으로 파고들어도 늘 벽 위에 보이게 (사용자 09-14 "곡괭이가 벽 안으로 들어간다")
        var vmGo = new GameObject("ViewModelCamera");
        vmGo.transform.SetParent(camGo.transform, false);
        var vmCam = vmGo.AddComponent<Camera>();
        vmCam.fieldOfView = Tuning.CAMERA_FOV;
        vmCam.nearClipPlane = 0.01f;
        vmCam.farClipPlane = 5f;
        vmCam.clearFlags = CameraClearFlags.Depth;
        vmCam.cullingMask = 1 << Pickaxe.ViewModelLayer;
        var vmData = vmGo.AddComponent<UniversalAdditionalCameraData>();
        vmData.renderType = CameraRenderType.Overlay;
        vmData.renderShadows = false;
        vmData.renderPostProcessing = false;     // 켜면 부피 안개 패스가 오버레이 카메라에서 한 번 더 돈다
        camData.cameraStack.Add(vmCam);

        // 곡괭이 뷰모델 (카메라 밑). 자세·배율은 Pickaxe.Awake 가 Tuning 에서 넣는다
        var pickGo = new GameObject("Pickaxe");
        pickGo.transform.SetParent(camGo.transform, false);
        var pickaxe = pickGo.AddComponent<Pickaxe>();
        pickaxe.cam = camGo.transform;
        pickaxe.player = p;
        pickaxe.mesh = Instance(pick, pickGo.transform).transform;
        foreach (var t in pickGo.GetComponentsInChildren<Transform>(true))
            t.gameObject.layer = Pickaxe.ViewModelLayer;
        foreach (var r in pickGo.GetComponentsInChildren<Renderer>(true))
            r.renderingLayerMask = Pickaxe.ViewModelRenderingLayer;

        var lampGo = new GameObject("Headlamp");
        var lampLight = lampGo.AddComponent<Light>();
        Headlamp.Apply(lampLight);
        lampGo.transform.SetPositionAndRotation(camGo.transform.TransformPoint(Tuning.LAMP_OFFSET), camGo.transform.rotation);
        var lamp = lampGo.AddComponent<Headlamp>();
        lamp.cam = camGo.transform;
        var vol = lampGo.AddComponent<VolumetricAdditionalLight>();
        vol.Anisotropy = Tuning.VOLFOG_ANISOTROPY;
        vol.Scattering = Tuning.VOLFOG_SCATTERING;
        lampLight.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer;   // 곡괭이는 안 비춘다

        // 곡괭이 전용 약한 등 — 램프와 같이 켜지고 꺼진다 (사용자 09-14 "곡괭이가 하얗게 뜨는 게 거슬린다")
        var pickLightGo = new GameObject("PickLight");
        pickLightGo.transform.SetParent(camGo.transform, false);
        pickLightGo.transform.localPosition = Tuning.LAMP_OFFSET;
        var pickLight = pickLightGo.AddComponent<Light>();
        pickLight.type = LightType.Spot;
        pickLight.spotAngle = Tuning.LAMP_ANGLE_DEG * 2f;
        pickLight.range = Tuning.PICK_LIGHT_RANGE;
        pickLight.color = Tuning.LAMP_COLOR;
        pickLight.intensity = Tuning.PICK_LIGHT_ENERGY;
        pickLight.shadows = LightShadows.None;
        pickLight.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.ViewModelRenderingLayer;
        lamp.pickLight = pickLight;

        var volume = new GameObject("Global Volume").AddComponent<Volume>();
        volume.isGlobal = true;
        volume.sharedProfile = profile;

        var dev = new GameObject("Dev");
        var hud = dev.AddComponent<DevHud>();
        hud.lamp = lamp;
        hud.player = p;
        hud.volume = volume;
        var check = dev.AddComponent<M1Check>();
        check.player = p;
        check.lamp = lamp;
        check.volume = volume;
        check.pieces = pieces;
        check.pickaxe = pickaxe;

        // M3 괴물. 북쪽 끝에서 시작. 충돌은 캡슐(R 0.6 · H 2.8) 그대로, 겉모습은 3D-① 모델
        var stalkerGo = new GameObject("Stalker");
        stalkerGo.transform.position = booth ? Find(pieces, "SPAWN_Stalker").position + Vector3.up * 0.1f : new Vector3(0f, 0.1f, (PieceCount - 1) * Tuning.GRID_CELL);
        float stalkerH = booth ? Tuning.BOOTH_STALKER_H : Tuning.STALKER_H;   // 부스: 실제 갱도 천장 2.2~2.7 m
        var scc = stalkerGo.AddComponent<CharacterController>();
        scc.radius = Tuning.STALKER_R;
        scc.height = stalkerH;
        scc.center = new Vector3(0f, stalkerH * 0.5f, 0f);
        // Body = 캡슐 가운데 높이의 빈 축, 크기 1. 캡슐 크기(비균등)였던 것은 3D-③ 에서 1 로 — 납작해지기를 지웠고(사용자 09-18),
        // 비균등 부모 밑에서 모델을 벽타기로 90° 세우면 몸이 비스듬히 찌그러진다. 캡슐 렌더러(회갈색 자리표시)는 3D-① 에서 뗐다
        var body = new GameObject("Body");
        body.transform.SetParent(stalkerGo.transform);
        body.transform.localPosition = new Vector3(0f, stalkerH * 0.5f, 0f);
        // 3D-①: 모델을 Body 밑에, STALKER_MODEL_SCALE 배 균등, 발이 괴물 뿌리(바닥)에 온다. 자리·기울기는 StalkerAnim 이 벽타기 때 바꾼다
        var model = Instance(monster, body.transform);
        model.name = "Model";
        model.transform.localScale = Vector3.one * Tuning.STALKER_MODEL_SCALE;
        model.transform.localPosition = new Vector3(0f, -body.transform.localPosition.y, 0f);
        model.transform.localRotation = Quaternion.Euler(0f, Tuning.STALKER_MODEL_YAW, 0f);
        var animator = model.GetComponent<Animator>() ?? model.AddComponent<Animator>();
        animator.runtimeAnimatorController = LoadOr<RuntimeAnimatorController>(booth, StalkerAnimPath, MakeStalkerAnimator);
        animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;   // 화면 밖에서도 움직인다 — 검사가 순간이동시켜 찍는다
        foreach (var smr in model.GetComponentsInChildren<SkinnedMeshRenderer>())
            smr.updateWhenOffscreen = true;                          // 뼈가 움직여도 화면 사각형(ScreenRect)이 맞게
        // 앞 표시 — 눈 두 개 (사용자 09-15 "캡슐이라 플레이어를 보는지 배회인지 판정이 안 선다"). 눈높이 STALKER_EYE_H, 몸 앞면
        // Unlit — 빛과 무관하게 늘 같은 밝기로 보인다 (램프를 꺼도 눈은 보인다). Lit + _EMISSION 은 빌드에서 변형이 빠져 검게 나왔다(09-15)
        // 3D-②b: 눈 구체 없음(사용자 09-17 "구체 두 개가 너무 잘 보인다"). 눈은 머리 그림의 발광(stage12 4b) — StalkerLook 이 세기를 넣는다
        model.AddComponent<StalkerAnim>();                           // 3D-③: 행동에 맞는 동작을 튼다 (Stalker 는 부모에서 찾는다)
        var look = model.AddComponent<StalkerLook>();
        look.scaleShader = AssetDatabase.LoadAssetAtPath<Shader>("Assets/Shaders/ScaleNormal.shader");   // 요철 세기용 (glTFast 의 normalTexture_scale 이 URP 에서 안 먹는다)
        look.glowShader = AssetDatabase.LoadAssetAtPath<Shader>("Assets/Shaders/LureGlow.shader");     // 램프 미끼 빛무리 (빌드에 들어가게 참조로)
        if (look.glowShader == null)
            Debug.LogError("Assets/Shaders/LureGlow.shader 를 못 읽었다");
        if (look.scaleShader == null)
        {
            Debug.LogError("Assets/Shaders/ScaleNormal.shader 를 못 읽었다");
            EditorApplication.Exit(8);
        }
        if (booth)
        {
            Vector3 lookS = Find(pieces, "LOOK_Stalker").position - stalkerGo.transform.position;
            stalkerGo.transform.rotation = Quaternion.LookRotation(Vector3.ProjectOnPlane(lookS, Vector3.up));
        }
        var stalker = stalkerGo.AddComponent<Stalker>();
        stalker.player = player.transform;
        stalker.playerHead = head;
        stalker.playerBody = p;
        stalker.lamp = lamp;
        stalker.restartPos = player.transform.position;
        stalker.homePos = stalkerGo.transform.position;
        if (booth)
        {
            stalker.cracks = pieces.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("SLOT_GapBig_")).Select(t => t.position + Vector3.up * 0.1f).ToArray();   // 재등장 = 큰 틈 자리
            stalker.zMin = stalker.zMax = 0f;                                                      // = 길찾기
            PlaceBoothLights(pieces, hud);
            hud.boothBlocks = blocks;
            hud.repairs = PlaceRepairs(pieces, p);                             // REP-1 고칠 곳
        }
        else
        {
        // 갈라진 틈 2곳 (M5 재등장 자리) — 복도 양 끝 벽 아래, 자리표시 검은 판. 미로가 생기면 레벨 설계서 M3-e 자리로
        var crackMat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "M5_Crack", color = new Color(0.02f, 0.02f, 0.02f) };
        crackMat.SetFloat("_Smoothness", 0.1f);
        AssetDatabase.DeleteAsset(CrackMatPath);
        AssetDatabase.CreateAsset(crackMat, CrackMatPath);
        var cracks = new Vector3[2];
        for (int i = 0; i < 2; i++)
        {
            float z = i == 0 ? stalker.zMin + 1f : stalker.zMax - 1f;
            float side = i == 0 ? -1f : 1f;
            var crack = GameObject.CreatePrimitive(PrimitiveType.Cube);
            crack.name = i == 0 ? "Crack_S" : "Crack_N";
            UnityEngine.Object.DestroyImmediate(crack.GetComponent<Collider>());
            crack.transform.SetParent(pieces);
            crack.transform.position = new Vector3(side * (Tuning.TUNNEL_WALL_X - 0.05f), 0.3f, z);
            crack.transform.localScale = new Vector3(0.2f, 0.6f, 1.6f);
            crack.GetComponent<MeshRenderer>().sharedMaterial = crackMat;
            cracks[i] = new Vector3(side * Tuning.STALKER_LANE_X, 0.1f, z);
        }
        stalker.cracks = cracks;
        stalker.zMin = -Tuning.GRID_CELL * 0.5f + Tuning.STALKER_R + 0.2f;
        stalker.zMax = (PieceCount - 0.5f) * Tuning.GRID_CELL - Tuning.STALKER_R - 0.2f;
        }
        hud.stalker = stalker;
        check.stalker = stalker;
        hud.pickaxe = pickaxe;

        // M6 던진 곡괭이 — 씬에 하나, 꺼진 채. Pickaxe.Throw 가 켠다. 광석과 같은 Ignore Raycast 레이어(시선·조준 구에 안 걸린다)
        var thrownGo = new GameObject("ThrownPick");
        thrownGo.layer = MiningFx.IgnoreRaycastLayer;
        thrownGo.AddComponent<Rigidbody>();
        var thrownMesh = Instance(pick, thrownGo.transform).transform;
        thrownMesh.localScale = Vector3.one * Tuning.PICK_SCALE;
        var box = new Bounds();
        bool first = true;
        foreach (var r in thrownMesh.GetComponentsInChildren<Renderer>())
        {
            r.gameObject.layer = MiningFx.IgnoreRaycastLayer;
            r.gameObject.AddComponent<BoxCollider>();           // 메시 크기에 맞는 상자 — 자루·목·머리. 공 하나면 머리가 바닥을 뚫었다(09-16)
            if (first) { box = r.bounds; first = false; } else box.Encapsulate(r.bounds);
        }
        thrownMesh.localPosition = -box.center;             // 메시 원점이 자루 끝이라 AABB 가운데를 몸체 중심으로
        var thrown = thrownGo.AddComponent<ThrownPick>();
        thrown.pickaxe = pickaxe;
        thrown.player = p;
        pickaxe.thrown = thrown;
        // UI-1c: reach 안이면 머리가 빛난다 — Unlit (괴물 눈과 같은 방법, Lit 발광은 빌드에서 안 나온다)
        thrown.glowMaterial = LoadOr(booth, PickGlowMatPath, () =>
        {
            var glowMat = new Material(Shader.Find("Universal Render Pipeline/Unlit")) { name = "M7_PickGlow", color = Tuning.PICK_GLOW_COLOR * Tuning.PICK_GLOW };
            AssetDatabase.DeleteAsset(PickGlowMatPath);
            AssetDatabase.CreateAsset(glowMat, PickGlowMatPath);
            return glowMat;
        });
        thrown.head = thrownMesh.GetComponentsInChildren<Renderer>().First(r => r.name == "PICK_Head");
        thrownGo.SetActive(false);

        var mining = new GameObject("Mining");
        var fx = mining.AddComponent<MiningFx>();
        fx.player = p;
        fx.orePrefab = ore;
        fx.chipMeshes = chips.GetComponentsInChildren<MeshFilter>().Select(f => f.sharedMesh).ToArray();
        fx.chipMaterial = chips.GetComponentInChildren<MeshRenderer>().sharedMaterial;
        fx.dustMaterial = LoadOr(booth, DustMatPath, MakeDustMaterial);
        fx.hitClips = hitClips;
        var noiseSound = mining.AddComponent<NoiseSound>();
        noiseSound.player = p;
        noiseSound.stepClips = stepClips;
        noiseSound.crouchClips = crouchClips;
        noiseSound.landClips = landClips;
        noiseSound.fleshClips = fleshClips;
        var miningHud = mining.AddComponent<MiningHud>();
        hud.miningHud = miningHud;
        miningHud.player = p;
        miningHud.pickaxe = pickaxe;
        if (booth) PlaceArt(pieces, camGo.transform, fx.dustMaterial);   // ART-1 현실감 (Insert 옛/새)

        EditorSceneManager.SaveScene(scene, scenePath);
        EditorBuildSettings.scenes = new[] { IntroScenePath, ScenePath, BoothScenePath }.Where(File.Exists).Select(sp => new EditorBuildSettingsScene(sp, true)).ToArray();
        PlayerSettings.productName = "Tunnel";
        PlayerSettings.companyName = "jhyun1234";
        AssetDatabase.SaveAssets();
        Debug.Log($"M1 scene saved: {scenePath}");
    }

    static Transform Find(Transform root, string name) => root.GetComponentsInChildren<Transform>(true).First(t => t.name == name);

    // 부스 맵을 놓고 충돌을 붙이고, 막힘 돌무더기를 끈 채로 길찾기 바닥을 굽는다 (막힘은 NavMeshObstacle 이 켜질 때 파낸다)
    static Transform PlaceBoothMap(out GameObject[] blocks)
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(BoothMapPath);
        if (prefab == null)
        {
            Debug.LogError($"{BoothMapPath} 를 못 읽었다 (blender/map/make_booth.py)");
            EditorApplication.Exit(10);
        }
        var map = Instance(prefab, null).transform;
        map.name = "BoothMap";
        foreach (var mf in map.GetComponentsInChildren<MeshFilter>(true))
        {
            string n = mf.name;
            if (n.StartsWith("COL_"))
            {
                mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
                UnityEngine.Object.DestroyImmediate(mf.GetComponent<MeshRenderer>());
            }
            else if (n.StartsWith("BLK_"))                                 // 돌무더기: 볼록 충돌 + 켜지면 길찾기 바닥을 파낸다
            {
                mf.gameObject.AddComponent<MeshCollider>().convex = true;
                var ob = mf.gameObject.AddComponent<NavMeshObstacle>();
                ob.shape = NavMeshObstacleShape.Box;
                ob.center = mf.sharedMesh.bounds.center;
                ob.size = mf.sharedMesh.bounds.size;
                ob.carving = true;
            }
            else if (n == "PRP_Rubble_FakeExit")                           // 가짜 출구 끝 무너짐 — 몸이 막힌다 (검사 booth_fake_exit)
                mf.gameObject.AddComponent<MeshCollider>().convex = true;
            else if (n.StartsWith("PRP_Crevice_"))                         // R2b 바위 틈 입구 바위 — 모난 바위 여럿이 한 그물이라 볼록으로 못 싼다
                mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
            else if (n == "PRP_Fence" || n == "PRP_WindDoor" || n == "PRP_Plate")   // 못 지나가는 것 — 울타리는 천장까지 막는다(넘어가지 않게)
            {
                var bc = mf.gameObject.AddComponent<BoxCollider>();
                if (n == "PRP_Fence") { var c = bc.center; c.y += (2.4f - bc.size.y) * 0.5f; bc.center = c; bc.size = new Vector3(bc.size.x, 2.4f, Mathf.Max(bc.size.z, 0.3f)); }
            }
        }
        // R2b 바위 틈: SLOT_Crevice_<i>_P0..Pn = 비집는 길 (바위 밖 선 자리 → 틈 → 숨는 자리 / 반대편), _Out 이 있으면 뚫린 틈
        var slots = map.GetComponentsInChildren<Transform>(true).GroupBy(t => t.name).ToDictionary(g => g.Key, g => g.First());   // 그물 노드 이름이 겹칠 수 있다
        for (int i = 1; slots.ContainsKey($"SLOT_Crevice_{i}_P0"); i++)
        {
            var c = new GameObject($"Crevice_{i}").AddComponent<Crevice>();
            c.transform.SetParent(map, false);
            c.path = Enumerable.Range(0, 99).TakeWhile(k => slots.ContainsKey($"SLOT_Crevice_{i}_P{k}")).Select(k => slots[$"SLOT_Crevice_{i}_P{k}"].position).ToArray();
            c.through = slots.ContainsKey($"SLOT_Crevice_{i}_Out");
        }
        blocks = map.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("BLK_")).Select(t => t.gameObject).OrderBy(b => b.name).ToArray();
        foreach (var b in blocks) b.SetActive(false);
        var surf = map.gameObject.AddComponent<NavMeshSurface>();
        surf.collectObjects = CollectObjects.Children;
        surf.useGeometry = NavMeshCollectGeometry.PhysicsColliders;
        surf.BuildNavMesh();
        AssetDatabase.DeleteAsset(BoothNavPath);
        AssetDatabase.CreateAsset(surf.navMeshData, BoothNavPath);
        foreach (var b in blocks) b.SetActive(Tuning.BOOTH_BLOCKS[DevHud.BlockGroup(b) - 1]);
        var tri = NavMesh.CalculateTriangulation();
        Debug.Log($"BOOTH navmesh: {tri.vertices.Length} verts, {tri.indices.Length / 3} tris");
        return map;
    }

    // REP-1 고칠 곳 (docs/제안서_REP1_고칠_곳.md): 부스 맵의 SLOT_Repair_<종류>_<i>(바닥 자리)마다. 가장 가까운 벽을 광선으로 찾아 벽에 붙인다.
    // 모습은 자리표시 모양(상자·원기둥) — Broken / Fixed 두 무리. 전등은 PlaceBoothLights 의 꺼진 전등(DeadLamp)에 빛을 달아 고치면 켠다. 충돌 없음(길찾기 바닥 그대로)
    static RepairDirector PlaceRepairs(Transform map, Player player)
    {
        Material Mat(string name, string shader, Color c)
        {
            string path = $"Assets/Settings/{name}.mat";
            AssetDatabase.DeleteAsset(path);
            var m = new Material(Shader.Find(shader)) { name = name, color = c };
            AssetDatabase.CreateAsset(m, path);
            return m;
        }
        const string LitS = "Universal Render Pipeline/Lit", UnlitS = "Universal Render Pipeline/Unlit";
        var wood = Mat("M10_RepWood", LitS, new Color(0.36f, 0.24f, 0.14f));
        var iron = Mat("M10_RepIron", LitS, new Color(0.32f, 0.3f, 0.28f));
        var cloth = Mat("M10_RepCloth", LitS, new Color(0.42f, 0.4f, 0.33f));
        var rubber = Mat("M10_RepRubber", LitS, new Color(0.08f, 0.08f, 0.08f));
        var water = Mat("M10_RepWater", UnlitS, new Color(0.35f, 0.5f, 0.6f));
        var lampOn = Mat("M10_RepPanelOn", UnlitS, new Color(1f, 0.7f, 0.3f));
        var lampOff = Mat("M10_RepPanelOff", UnlitS, new Color(0.12f, 0.03f, 0.02f));
        var bulbOn = AssetDatabase.LoadAssetAtPath<Material>(BulbOnMatPath);
        var bulbOff = AssetDatabase.LoadAssetAtPath<Material>(BulbOffMatPath);
        var deadLamps = GameObject.Find("BoothLights").transform.Cast<Transform>().Where(t => t.name == "DeadLamp").ToList();
        Physics.SyncTransforms();

        GameObject Part(PrimitiveType type, Transform parent, Vector3 pos, Quaternion rot, Vector3 scale, Material mat)
        {
            var g = GameObject.CreatePrimitive(type);
            UnityEngine.Object.DestroyImmediate(g.GetComponent<Collider>());
            g.transform.SetParent(parent, true);
            g.transform.SetPositionAndRotation(pos, rot);
            g.transform.localScale = scale;
            var r = g.GetComponent<MeshRenderer>();
            r.sharedMaterial = mat;
            r.shadowCastingMode = ShadowCastingMode.Off;
            return g;
        }
        GameObject Rod(Transform parent, Vector3 a, Vector3 b, float r, Material mat)       // 원기둥 a → b, 반지름 r
            => Part(PrimitiveType.Cylinder, parent, (a + b) * 0.5f, Quaternion.FromToRotation(Vector3.up, b - a), new Vector3(r * 2f, Vector3.Distance(a, b) * 0.5f, r * 2f), mat);
        Transform Group(Transform parent, string name) { var g = new GameObject(name).transform; g.SetParent(parent, false); return g; }

        var root = new GameObject("Repairs").transform;
        int n = 0;
        foreach (var slot in map.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("SLOT_Repair_")).OrderBy(t => t.name))
        {
            string kind = slot.name.Split('_')[2];
            Vector3 p = slot.position;
            float best = 99f; Vector3 wall = p, nrm = Vector3.forward;       // 가장 가까운 벽 (허리 높이 수평 광선 24 방향)
            for (int k = 0; k < 24; k++)
            {
                Vector3 d = Quaternion.Euler(0f, k * 15f, 0f) * Vector3.forward;
                if (Physics.Raycast(p + Vector3.up * 1.2f, d, out RaycastHit h, 8f, ~(1 << 2), QueryTriggerInteraction.Ignore) && h.distance < best)
                { best = h.distance; wall = new Vector3(h.point.x, p.y, h.point.z); nrm = Vector3.ProjectOnPlane(h.normal, Vector3.up).normalized; }
            }
            Vector3 tg = Vector3.Cross(Vector3.up, nrm).normalized, up = Vector3.up;
            var go = new GameObject($"Repair_{kind}_{++n}");
            go.transform.SetParent(root);
            go.transform.position = p;
            var rep = go.AddComponent<Repairable>();
            rep.kind = kind;
            var brk = Group(go.transform, "Broken"); var fix = Group(go.transform, "Fixed");
            rep.brokenLook = brk.gameObject; rep.fixedLook = fix.gameObject;
            Quaternion face = Quaternion.LookRotation(nrm, up);
            switch (kind)
            {
                case "timber":                                             // 동발: 벽에 선 기둥 — 망가지면 통로 쪽으로 12° 기운다
                {
                    Vector3 c = wall + nrm * 0.16f + up * 1.2f;
                    Part(PrimitiveType.Cube, fix, c, face, new Vector3(0.22f, 2.4f, 0.22f), wood);
                    Part(PrimitiveType.Cube, brk, c + nrm * 0.12f, Quaternion.AngleAxis(12f, tg) * face, new Vector3(0.22f, 2.4f, 0.22f), wood);
                    rep.focus = c; rep.standAt = wall + nrm * 1.0f; break;
                }
                case "rail":                                               // 레일 두 줄 (궤간 0.6) — 망가지면 한 줄이 벌어진다
                {
                    Vector3 c = p + up * 0.05f, off = Vector3.Cross(tg, up).normalized * 0.3f;
                    Quaternion along = Quaternion.LookRotation(tg, up);
                    foreach (var g in new[] { fix, brk }) Part(PrimitiveType.Cube, g, c + off, along, new Vector3(0.07f, 0.1f, 1.8f), iron);
                    Part(PrimitiveType.Cube, fix, c - off, along, new Vector3(0.07f, 0.1f, 1.8f), iron);
                    Part(PrimitiveType.Cube, brk, c - off * 1.4f, Quaternion.AngleAxis(12f, up) * along, new Vector3(0.07f, 0.1f, 1.8f), iron);
                    rep.focus = c; rep.standAt = p + tg * 1.3f; break;
                }
                case "drain":                                              // 벽을 따라가는 배수관 — 망가지면 이음새가 벌어져 물이 샌다
                {
                    Vector3 c = wall + nrm * 0.12f + up * 0.35f;
                    Rod(fix, c - tg, c + tg, 0.07f, iron);
                    Rod(brk, c - tg, c - tg * 0.1f, 0.07f, iron); Rod(brk, c + tg * 0.12f, c + tg, 0.07f, iron);
                    Part(PrimitiveType.Cube, brk, c + tg * 0.01f - up * 0.17f, face, new Vector3(0.05f, 0.34f, 0.05f), water);
                    Part(PrimitiveType.Cube, brk, new Vector3(c.x, p.y + 0.01f, c.z) + nrm * 0.25f, face, new Vector3(0.7f, 0.01f, 0.45f), water);
                    rep.focus = c; rep.standAt = wall + nrm * 1.0f; break;
                }
                case "vent":                                               // 천장 밑 풍관 — 망가지면 찢어진 천이 펄럭인다
                {
                    Vector3 c = wall + nrm * 0.4f + up * 2.15f;
                    foreach (var g in new[] { fix, brk }) Rod(g, c - tg * 1.1f, c + tg * 1.1f, 0.22f, cloth);
                    var hinge = Group(brk, "Flap"); hinge.position = c - up * 0.2f; hinge.rotation = Quaternion.LookRotation(tg, up);
                    Part(PrimitiveType.Cube, hinge, hinge.position - up * 0.15f, hinge.rotation, new Vector3(0.45f, 0.3f, 0.02f), cloth);
                    rep.flap = hinge; rep.focus = c; rep.standAt = wall + nrm * 1.1f; break;
                }
                case "panel":                                              // 배전반: 벽에 붙은 상자 + 표시등 (꺼짐/켜짐)
                {
                    Vector3 c = wall + nrm * 0.08f + up * 1.3f;
                    foreach (var g in new[] { fix, brk }) Part(PrimitiveType.Cube, g, c, face, new Vector3(0.5f, 0.7f, 0.14f), iron);
                    Part(PrimitiveType.Sphere, fix, c + nrm * 0.08f + up * 0.22f, face, Vector3.one * 0.07f, lampOn);
                    Part(PrimitiveType.Sphere, brk, c + nrm * 0.08f + up * 0.22f, face, Vector3.one * 0.07f, lampOff);
                    rep.focus = c; rep.standAt = wall + nrm * 1.0f; break;
                }
                case "hose":                                               // 바닥의 공기 호스 — 망가지면 풀린 끝이 들려 휘청인다
                {
                    Vector3 c = wall + nrm * 0.35f + up * 0.04f;
                    Rod(fix, c - tg * 0.9f, c + tg * 0.9f, 0.035f, rubber);
                    Rod(brk, c - tg * 0.9f, c + tg * 0.3f, 0.035f, rubber);
                    var hinge = Group(brk, "Flap"); hinge.position = c + tg * 0.3f; hinge.rotation = Quaternion.LookRotation(tg, up);
                    Rod(hinge, hinge.position, hinge.position + tg * 0.6f + up * 0.2f, 0.035f, rubber);
                    rep.flap = hinge; rep.focus = c; rep.standAt = wall + nrm * 1.0f; break;
                }
                case "lamp":                                               // 꺼진 전등(DeadLamp) — 고치면 켜진 전등과 같은 빛
                {
                    var dl = deadLamps.OrderBy(t => Vector2.Distance(new Vector2(t.position.x, t.position.z), new Vector2(p.x, p.z))).First();
                    rep.bulb = dl.GetComponentInChildren<MeshRenderer>();
                    rep.bulbOn = bulbOn; rep.bulbOff = bulbOff;
                    var l = dl.gameObject.AddComponent<Light>();
                    l.type = LightType.Point; l.color = Tuning.BOOTH_LIGHT_COLOR; l.intensity = Tuning.BOOTH_LIGHT_ENERGY; l.range = Tuning.BOOTH_LIGHT_RANGE;
                    l.shadows = LightShadows.Soft; l.enabled = false;
                    l.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer;
                    rep.lampLight = l;
                    rep.focus = new Vector3(p.x, p.y + 1.2f, p.z); rep.standAt = p + tg * 0.8f; break;
                }
            }
            if (NavMesh.SamplePosition(rep.standAt, out NavMeshHit nh, 1.5f, NavMesh.AllAreas)) rep.standAt = nh.position;
            brk.gameObject.SetActive(false);
        }
        var dir = root.gameObject.AddComponent<RepairDirector>();
        dir.player = player;
        Debug.Log($"BOOTH repairs: {n} ({string.Join(" ", root.GetComponentsInChildren<Repairable>(true).GroupBy(r => r.kind).Select(g => g.Key + " " + g.Count()))})");
        return dir;
    }

    // ART-1 현실감 시험 (docs/제안서_ART1_현실감_광장_시험.md): 부스 맵 바위(SHL_Booth_* · PRP_Crevice_*)의 벽·바닥 재질을 MineRock 으로 · 전등마다 튀는 빛(그림자 없음)
    // · 카메라 둘레 떠다니는 먼지(헤드램프에만 보이는 먼지 재질) · 부스 화면 설정(겹치는 볼륨: 필름 입자 · 빛 번짐 · 대비). ArtLook 이 Insert 로 옛/새를 바꾼다
    static void PlaceArt(Transform map, Transform cam, Material dustMat)
    {
        Texture2D T(string f)
        {
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(ArtTexDir + f);
            if (t == null) { Debug.LogError($"ART: {ArtTexDir}{f} 가 없다"); EditorApplication.Exit(11); }
            return t;
        }
        var shader = Shader.Find("Tunnel/MineRock");
        if (shader == null) { Debug.LogError("ART: Tunnel/MineRock 셰이더를 못 찾았다"); EditorApplication.Exit(12); }
        AssetDatabase.DeleteAsset(MineRockMatPath);
        var mat = new Material(shader) { name = "M11_MineRock" };
        foreach (var (prop, file) in new[] {
            ("_BaseMap", "art_rock_Rock031_DiffRough.png"), ("_BumpMap", "art_rock_Rock031_nor_gl.jpg"),        // 색 그림 알파 = 거칠기
            ("_CoalMap", "art_coal_Rock035_DiffRough.png"), ("_CoalNormal", "art_coal_Rock035_nor_gl.jpg"),
            ("_MudMap", "art_mud_brown_mud_03_DiffRough.png"), ("_MudNormal", "art_mud_brown_mud_03_nor_gl.jpg") })
            mat.SetTexture(prop, T(file));
        AssetDatabase.CreateAsset(mat, MineRockMatPath);

        var art = new GameObject("ArtLook").AddComponent<ArtLook>();
        var rs = map.GetComponentsInChildren<MeshRenderer>(true).Where(r => r.name.StartsWith("SHL_Booth_") || r.name.StartsWith("PRP_Crevice_")).ToArray();
        art.renderers = rs;
        art.oldMats = rs.SelectMany(r => r.sharedMaterials).ToArray();
        art.newMat = mat;

        var mains = GameObject.Find("BoothLights").GetComponentsInChildren<Light>(true).Where(l => l.type == LightType.Point).ToArray();   // 켜진 전등 + 고치면 켜지는 전등
        art.mains = mains;
        art.bounces = mains.Select(m =>
        {
            var go = new GameObject("Bounce");
            go.transform.SetParent(m.transform, false);
            go.transform.localPosition = Vector3.down * Tuning.ART_BOUNCE_DROP;
            var b = go.AddComponent<Light>();
            b.type = LightType.Point; b.color = Tuning.BOOTH_LIGHT_COLOR * Tuning.ART_BOUNCE_TINT; b.range = Tuning.ART_BOUNCE_RANGE;
            b.shadows = LightShadows.None; b.enabled = false;
            b.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer;
            return b;
        }).ToArray();

        var dustGo = new GameObject("ArtDust");
        dustGo.transform.SetParent(cam, false);
        var ps = dustGo.AddComponent<ParticleSystem>();
        ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        var main = ps.main;
        main.loop = true; main.prewarm = true; main.playOnAwake = true;
        main.startLifetime = 9f; main.startSpeed = 0.03f; main.maxParticles = 600;
        main.startSize = new ParticleSystem.MinMaxCurve(0.006f, 0.016f);
        main.startColor = new Color(0.75f, 0.7f, 0.62f, 0.55f);
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        var em = ps.emission; em.rateOverTime = 60f;
        var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(7f, 3f, 7f); sh.position = new Vector3(0f, 0f, 2.5f);
        var nz = ps.noise; nz.enabled = true; nz.strength = 0.05f; nz.frequency = 0.3f;
        var pr = dustGo.GetComponent<ParticleSystemRenderer>();
        pr.sharedMaterial = dustMat; pr.shadowCastingMode = ShadowCastingMode.Off; pr.receiveShadows = false;
        art.dust = ps;

        // 화면 설정은 바꿔 끼우지 않고 두 번째 볼륨(우선순위 1)을 겹친다 — DevHud · M1Check 가 첫 볼륨의 사본(안개)을 잡고 있다
        AssetDatabase.DeleteAsset(ArtProfilePath);
        var np = ScriptableObject.CreateInstance<VolumeProfile>();
        AssetDatabase.CreateAsset(np, ArtProfilePath);
        np.Add<ColorAdjustments>(true).contrast.Override(Tuning.ART_CONTRAST);
        var fg = np.Add<FilmGrain>(true); fg.type.Override(FilmGrainLookup.Medium1); fg.intensity.Override(Tuning.ART_GRAIN);
        var bl = np.Add<Bloom>(true); bl.intensity.Override(Tuning.ART_BLOOM); bl.threshold.Override(1.0f); bl.scatter.Override(0.6f);
        foreach (var c in np.components)
        {
            c.hideFlags = HideFlags.HideInInspector | HideFlags.HideInHierarchy;
            AssetDatabase.AddObjectToAsset(c, np);
        }
        EditorUtility.SetDirty(np);
        var av = new GameObject("ArtVolume").AddComponent<Volume>();
        av.isGlobal = true; av.priority = 1f; av.sharedProfile = np;
        art.artVolume = av;
        Debug.Log($"BOOTH art: rock renderers {rs.Length} (material slots {art.oldMats.Length}) · bounce lights {art.bounces.Length} · art volume {string.Join(" ", np.components.Select(c => c.GetType().Name))}");
    }

    // 켜진 전등 = 따뜻한 점광원 + 빛나는 전구, 꺼진 전등 = 어두운 전구만
    static void PlaceBoothLights(Transform map, DevHud hud)
    {
        Material Mat(string path, string name, Color c)
        {
            AssetDatabase.DeleteAsset(path);
            var m = new Material(Shader.Find("Universal Render Pipeline/Unlit")) { name = name, color = c };
            AssetDatabase.CreateAsset(m, path);
            return m;
        }
        var on = Mat(BulbOnMatPath, "M9_BulbOn", Tuning.BOOTH_LIGHT_COLOR * 1.4f);
        var off = Mat(BulbOffMatPath, "M9_BulbOff", new Color(0.05f, 0.045f, 0.04f));
        var root = new GameObject("BoothLights").transform;
        var lights = new System.Collections.Generic.List<Light>();
        foreach (var slot in map.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("SLOT_Light_") || t.name.StartsWith("SLOT_DeadLight_")).OrderBy(t => t.name))
        {
            bool lit = slot.name.StartsWith("SLOT_Light_");
            var go = new GameObject(lit ? "Lamp" : "DeadLamp");
            go.transform.SetParent(root);
            go.transform.position = slot.position;
            var bulb = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            UnityEngine.Object.DestroyImmediate(bulb.GetComponent<Collider>());
            bulb.transform.SetParent(go.transform, false);
            bulb.transform.localScale = Vector3.one * 0.12f;
            var br = bulb.GetComponent<MeshRenderer>();
            br.sharedMaterial = lit ? on : off;
            br.shadowCastingMode = ShadowCastingMode.Off;
            if (!lit) continue;
            var l = go.AddComponent<Light>();
            l.type = LightType.Point;
            l.color = Tuning.BOOTH_LIGHT_COLOR;
            l.intensity = Tuning.BOOTH_LIGHT_ENERGY;
            l.range = Tuning.BOOTH_LIGHT_RANGE;
            l.shadows = LightShadows.Soft;                                   // 없으면 바위를 뚫고 옆 갱도까지 비춘다
            l.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer;
            lights.Add(l);
        }
        hud.boothLights = lights.ToArray();
    }

    public static void BuildWindows()
    {
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { IntroScenePath, ScenePath, BoothScenePath },   // 0 = 인트로(UI-2), 1 = 42 m 복도(검사용), 2 = 부스 맵(MAP1, 인트로 "시작")
            locationPathName = ExePath,
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None,
        });
        Debug.Log($"BUILD {report.summary.result} errors={report.summary.totalErrors} size={report.summary.totalSize / 1048576} MB");
        EditorApplication.Exit(report.summary.result == BuildResult.Succeeded ? 0 : 1);
    }

    // UI-2 인트로 씬 (지침 1-1 · 4-1, 제안서 UI-2). 검은 카메라 + Canvas(1920×1080 기준) — 로고 패널(로고 2 · 팀명 · 게임명) / 메뉴 패널(시작 · 소리 크기 · 끝내기).
    // 값·글자는 Tuning.INTRO_*. 기본 해상도도 여기서 1920×1080 으로 (지침 하드웨어 사양서 16:9)
    public static void MakeIntro()
    {
        var font = AssetDatabase.LoadAssetAtPath<Font>(FontPath);
        var univ = LoadSprite(LogoUnivPath);
        var center = LoadSprite(LogoCenterPath);
        if (font == null || univ == null || center == null)
        {
            Debug.LogError($"{FontPath} / {LogoUnivPath} / {LogoCenterPath} 를 못 읽었다 (font {font != null}, univ {univ != null}, center {center != null})");
            EditorApplication.Exit(9);
            return;
        }
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var camGo = new GameObject("Camera") { tag = "MainCamera" };
        var cam = camGo.AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.black;
        cam.cullingMask = 0;
        camGo.AddComponent<UniversalAdditionalCameraData>().renderPostProcessing = false;
        camGo.AddComponent<AudioListener>();

        var canvasGo = new GameObject("Canvas");
        var canvas = canvasGo.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        var scaler = canvasGo.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920f, 1080f);
        scaler.matchWidthOrHeight = 0.5f;

        // 로고 패널: 로고 높이 = 화면의 18 % (제안값), 가로로 둘, 아래 팀명 · 게임명 · 영문 부제
        var logo = Panel(canvasGo.transform, "LogoPanel");
        float logoH = 1080f * 0.18f;
        Image(logo, "LogoUniversity", univ, new Vector2(-300f, 200f), logoH);
        Image(logo, "LogoCenter", center, new Vector2(300f, 200f), logoH);
        Label(logo, "Team", Tuning.INTRO_TEAM, 40, new Vector2(0f, -40f), font);
        Label(logo, "Title", Tuning.INTRO_TITLE, 96, new Vector2(0f, -160f), font);
        Label(logo, "Subtitle", Tuning.INTRO_SUBTITLE, 44, new Vector2(0f, -250f), font).color = new Color(0.75f, 0.75f, 0.75f);

        // 메뉴 패널: 글자 3줄, 화면 높이의 5 %
        var menu = Panel(canvasGo.transform, "MenuPanel");
        var items = new[]
        {
            Label(menu, "Start", "시작", 54, new Vector2(0f, 70f), font),
            Label(menu, "Volume", "소리 크기", 54, new Vector2(0f, 0f), font),
            Label(menu, "Quit", "끝내기", 54, new Vector2(0f, -70f), font),
        };
        menu.gameObject.SetActive(false);

        var intro = new GameObject("Intro").AddComponent<Intro>();
        intro.logoPanel = logo.gameObject;
        intro.menuPanel = menu.gameObject;
        intro.items = items;

        EditorSceneManager.SaveScene(scene, IntroScenePath);
        EditorBuildSettings.scenes = new[] { IntroScenePath, ScenePath, BoothScenePath }.Where(File.Exists).Select(sp => new EditorBuildSettingsScene(sp, true)).ToArray();
        PlayerSettings.defaultScreenWidth = 1920;
        PlayerSettings.defaultScreenHeight = 1080;
        AssetDatabase.SaveAssets();
        Debug.Log($"Intro scene saved: {IntroScenePath}");
    }

    static Sprite LoadSprite(string path)
    {
        var imp = AssetImporter.GetAtPath(path) as TextureImporter;
        if (imp == null) return null;
        if (imp.textureType != TextureImporterType.Sprite || imp.spriteImportMode != SpriteImportMode.Single)
        {
            imp.textureType = TextureImporterType.Sprite;
            imp.spriteImportMode = SpriteImportMode.Single;
            imp.SaveAndReimport();
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
        }
        return AssetDatabase.LoadAssetAtPath<Sprite>(path);
    }

    static RectTransform Rect(Transform parent, string name, Vector2 pos, Vector2 size)
    {
        var rt = new GameObject(name, typeof(RectTransform)).GetComponent<RectTransform>();
        rt.SetParent(parent, false);
        rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
        rt.anchoredPosition = pos;
        rt.sizeDelta = size;
        return rt;
    }

    static RectTransform Panel(Transform parent, string name)
    {
        var rt = Rect(parent, name, Vector2.zero, Vector2.zero);
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.offsetMin = rt.offsetMax = Vector2.zero;
        return rt;
    }

    static Image Image(Transform parent, string name, Sprite sprite, Vector2 pos, float height)
    {
        float w = height * sprite.rect.width / sprite.rect.height;
        var img = Rect(parent, name, pos, new Vector2(w, height)).gameObject.AddComponent<Image>();
        img.sprite = sprite;
        img.preserveAspect = true;
        return img;
    }

    static Text Label(Transform parent, string name, string text, int size, Vector2 pos, Font font)
    {
        var t = Rect(parent, name, pos, new Vector2(1800f, size * 1.6f)).gameObject.AddComponent<Text>();
        t.font = font;
        t.fontSize = size;
        t.text = text;
        t.alignment = TextAnchor.MiddleCenter;
        t.color = Color.white;
        t.horizontalOverflow = HorizontalWrapMode.Overflow;
        t.verticalOverflow = VerticalWrapMode.Overflow;
        return t;
    }

    static GameObject Instance(GameObject prefab, Transform parent)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
        PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        return go;
    }

    // 3D-①: 괴물 동작 상태기. GLB 의 클립 14개를 상태 하나씩으로, 기본 상태 = STALKER_MODEL_IDLE 반복 (glTFast 가 loopTime 을 켠다).
    // 상태 사이 전이는 3D-③ 에서 (지금은 기본 상태만 돈다)
    static RuntimeAnimatorController MakeStalkerAnimator()
    {
        var clips = AssetDatabase.LoadAllAssetsAtPath(MonsterPath).OfType<AnimationClip>().OrderBy(c => c.name).ToArray();
        if (clips.Length != Tuning.STALKER_CLIP_COUNT || clips.All(c => c.name != Tuning.STALKER_MODEL_IDLE))
        {
            Debug.LogError($"{MonsterPath} 클립이 {Tuning.STALKER_CLIP_COUNT}개가 아니거나 {Tuning.STALKER_MODEL_IDLE} 이 없다: {string.Join(", ", clips.Select(c => c.name))}");
            EditorApplication.Exit(6);
        }
        AssetDatabase.DeleteAsset(StalkerAnimPath);
        var ctrl = UnityEditor.Animations.AnimatorController.CreateAnimatorControllerAtPath(StalkerAnimPath);
        var sm = ctrl.layers[0].stateMachine;
        foreach (var clip in clips)
        {
            var state = sm.AddState(clip.name);
            state.motion = clip;
            if (clip.name == Tuning.STALKER_MODEL_IDLE) sm.defaultState = state;
        }
        Debug.Log($"STALKER_ANIM clips {clips.Length}: {string.Join(", ", clips.Select(c => $"{c.name} {c.length:F2}s"))}");
        return ctrl;
    }

    // 먼지 재질: URP 기본 파티클 재질(반투명)을 복사해 조명을 받는 Simple Lit 으로 — 램프 밖 먼지가 어둠에서 빛나지 않게
    static Material MakeDustMaterial()
    {
        AssetDatabase.DeleteAsset(DustMatPath);
        var urp = (UniversalRenderPipelineAsset)(QualitySettings.renderPipeline ?? GraphicsSettings.defaultRenderPipeline);
        var mat = new Material(urp.defaultParticleMaterial) { name = "M2_Dust" };
        mat.shader = Shader.Find("Universal Render Pipeline/Particles/Simple Lit");
        BaseShaderGUI.SetupMaterialBlendMode(mat);
        AssetDatabase.CreateAsset(mat, DustMatPath);
        return mat;
    }

    static void EndWall(Transform parent, string name, float z)
    {
        var w = new GameObject(name);
        w.transform.SetParent(parent);
        w.transform.position = new Vector3(0f, 2.8f, z);
        w.AddComponent<BoxCollider>().size = new Vector3(Tuning.GRID_CELL, 5.6f, 0.3f);
    }

    static void AddFogFeature()
    {
        var data = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(RendererPath);
        if (data.rendererFeatures.Any(f => f is VolumetricFogRendererFeature))
            return;
        var feature = ScriptableObject.CreateInstance<VolumetricFogRendererFeature>();
        feature.name = "VolumetricFog";
        AssetDatabase.AddObjectToAsset(feature, data);
        var fso = new SerializedObject(feature);
        fso.FindProperty("downsampleDepthShader").objectReferenceValue = Shader.Find("Hidden/DownsampleDepth");
        fso.FindProperty("volumetricFogShader").objectReferenceValue = Shader.Find("Hidden/VolumetricFog");
        fso.ApplyModifiedPropertiesWithoutUndo();
        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(feature, out string _, out long id);
        var so = new SerializedObject(data);
        var list = so.FindProperty("m_RendererFeatures");
        var map = so.FindProperty("m_RendererFeatureMap");
        list.arraySize++;
        list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = feature;
        map.arraySize++;
        map.GetArrayElementAtIndex(map.arraySize - 1).longValue = id;
        so.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(data);
        AssetDatabase.SaveAssets();
    }

    static VolumeProfile MakeProfile()
    {
        AssetDatabase.DeleteAsset(ProfilePath);
        var profile = ScriptableObject.CreateInstance<VolumeProfile>();
        AssetDatabase.CreateAsset(profile, ProfilePath);

        profile.Add<Tonemapping>(true).mode.Override(TonemappingMode.ACES);   // Godot Filmic 에 가장 가까운 URP 모드
        profile.Add<ColorAdjustments>(true).saturation.Override((Tuning.ADJ_SATURATION - 1f) * 100f);
        profile.Add<Vignette>(true).intensity.Override(Tuning.VIGNETTE);
        var fog = profile.Add<VolumetricFogVolumeComponent>(true);
        fog.enabled.Override(true);
        fog.density.Override(Tuning.VOLFOG_DENSITY);
        fog.distance.Override(Tuning.VOLFOG_DISTANCE);
        fog.baseHeight.Override(10f);           // 갱도 천장(5.6) 위까지 밀도 그대로
        fog.maximumHeight.Override(20f);
        fog.enableMainLightContribution.Override(false);
        fog.enableAdditionalLightsContribution.Override(true);

        foreach (var c in profile.components)
        {
            c.hideFlags = HideFlags.HideInInspector | HideFlags.HideInHierarchy;
            AssetDatabase.AddObjectToAsset(c, profile);
        }
        EditorUtility.SetDirty(profile);
        AssetDatabase.SaveAssets();
        return profile;
    }
}
