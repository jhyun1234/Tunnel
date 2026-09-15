using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

// 마일스톤 1·2 씬 만들기와 Windows 빌드. 배치 모드에서 부른다 (명령은 docs/HANDOFF.md, tools/build.sh).
public static class BuildM1
{
    const string ScenePath = "Assets/Scenes/M1_Tunnel.unity";
    const string PiecePath = "Assets/Tunnel/Pieces/piece_straight.gltf";
    const string ProfilePath = "Assets/Settings/M1_Volume.asset";
    const string RendererPath = "Assets/Settings/PC_Renderer.asset";
    const string ExePath = "build/Tunnel/Tunnel.exe";
    const string PickPath = "Assets/Tunnel/Pieces/pick.gltf";
    const string OrePath = "Assets/Tunnel/Pieces/ore.gltf";
    const string ChipsPath = "Assets/Tunnel/Pieces/mine_chips.gltf";
    const string DustMatPath = "Assets/Settings/M2_Dust.mat";
    const string StalkerMatPath = "Assets/Settings/M3_StalkerBody.mat";
    const string StalkerEyeMatPath = "Assets/Settings/M4_StalkerEye.mat";
    const string CrackMatPath = "Assets/Settings/M5_Crack.mat";
    const string HitSoundDir = "Assets/Audio/PickHit";   // Kenney Impact Sounds impactMining_* (CC0)
    const int PieceCount = 6;              // 직선 조각 한 종류를 줄지어 42 m — 달리기 판정 길이 + 이음새 확인

    public static void MakeScene()
    {
        if (File.Exists(ScenePath) && !Environment.GetCommandLineArgs().Contains("-force"))
        {
            Debug.LogError($"{ScenePath} 가 이미 있다 — 덮어쓰려면 -force");
            EditorApplication.Exit(2);
            return;
        }
        var piece = AssetDatabase.LoadAssetAtPath<GameObject>(PiecePath);
        var pick = AssetDatabase.LoadAssetAtPath<GameObject>(PickPath);
        var ore = AssetDatabase.LoadAssetAtPath<GameObject>(OrePath);
        var chips = AssetDatabase.LoadAssetAtPath<GameObject>(ChipsPath);
        if (piece == null || pick == null || ore == null || chips == null)
        {
            Debug.LogError("piece_straight / pick / ore / mine_chips glTF 를 못 읽었다 (glTFast 임포트 확인)");
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

        AddFogFeature();
        var profile = MakeProfile();
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

        // 갱도: 조각의 COL_* 노드를 충돌로, 보이지 않게
        var pieces = new GameObject("Pieces").transform;
        for (int i = 0; i < PieceCount; i++)
        {
            var go = Instance(piece, pieces);
            go.name = $"piece_straight_{i}";
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

        // 광맥 포켓: 조각의 SLOT_Pocket_* 자리마다 POCKET_CHANCE 로 (Godot PocketSpawner.gd). 통로 쪽 = 자리에서 조각 원점 쪽
        var rng = new System.Random(Tuning.MAP_SEED + 100);
        var pocketsRoot = new GameObject("Pockets").transform;
        foreach (var slot in pieces.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("SLOT_Pocket_")).ToArray())
        {
            if (rng.NextDouble() >= Tuning.POCKET_CHANCE)
                continue;
            var pieceRoot = slot;
            while (pieceRoot.parent != pieces)
                pieceRoot = pieceRoot.parent;
            Vector3 outDir = pieceRoot.position - slot.position;
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

        // M3 괴물 — 캡슐 하나 (모델은 텍스처 확정 뒤). 북쪽 끝에서 시작
        var stalkerGo = new GameObject("Stalker");
        stalkerGo.transform.position = new Vector3(0f, 0.1f, (PieceCount - 1) * Tuning.GRID_CELL);
        var scc = stalkerGo.AddComponent<CharacterController>();
        scc.radius = Tuning.STALKER_R;
        scc.height = Tuning.STALKER_H;
        scc.center = new Vector3(0f, Tuning.STALKER_H * 0.5f, 0f);
        var body = GameObject.CreatePrimitive(PrimitiveType.Capsule);
        body.name = "Body";
        UnityEngine.Object.DestroyImmediate(body.GetComponent<Collider>());
        body.transform.SetParent(stalkerGo.transform);
        body.transform.localPosition = new Vector3(0f, Tuning.STALKER_H * 0.5f, 0f);
        body.transform.localScale = new Vector3(Tuning.STALKER_R * 2f, Tuning.STALKER_H * 0.5f, Tuning.STALKER_R * 2f);  // 기본 캡슐 = 반지름 0.5 · 높이 2
        // 자리표시 캡슐 색. 검정(0.12)은 램프 앞 7 m 에서 밝기 0.055 = 갱도 바탕 0.05 과 같아 "절대 보이지 않는다"(사용자 09-15) → 밝은 회갈색
        var bodyMat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "M3_StalkerBody", color = new Color(0.40f, 0.36f, 0.32f) };
        bodyMat.SetFloat("_Smoothness", 0.25f);
        AssetDatabase.DeleteAsset(StalkerMatPath);
        AssetDatabase.CreateAsset(bodyMat, StalkerMatPath);
        body.GetComponent<MeshRenderer>().sharedMaterial = bodyMat;
        // 앞 표시 — 눈 두 개 (사용자 09-15 "캡슐이라 플레이어를 보는지 배회인지 판정이 안 선다"). 눈높이 STALKER_EYE_H, 몸 앞면
        // Unlit — 빛과 무관하게 늘 같은 밝기로 보인다 (램프를 꺼도 눈은 보인다). Lit + _EMISSION 은 빌드에서 변형이 빠져 검게 나왔다(09-15)
        var eyeMat = new Material(Shader.Find("Universal Render Pipeline/Unlit")) { name = "M4_StalkerEye", color = Tuning.STALKER_EYE_COLOR * Tuning.STALKER_EYE_GLOW };
        AssetDatabase.DeleteAsset(StalkerEyeMatPath);
        AssetDatabase.CreateAsset(eyeMat, StalkerEyeMatPath);
        foreach (float sx in new[] { -0.16f, 0.16f })
        {
            var eye = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            eye.name = sx < 0 ? "EyeL" : "EyeR";
            UnityEngine.Object.DestroyImmediate(eye.GetComponent<Collider>());
            eye.transform.SetParent(stalkerGo.transform);
            eye.transform.localPosition = new Vector3(sx, Tuning.STALKER_EYE_H, Tuning.STALKER_R * 0.92f);
            eye.transform.localScale = Vector3.one * 0.2f;
            eye.GetComponent<MeshRenderer>().sharedMaterial = eyeMat;
        }
        var stalker = stalkerGo.AddComponent<Stalker>();
        stalker.player = player.transform;
        stalker.playerHead = head;
        stalker.playerBody = p;
        stalker.lamp = lamp;
        stalker.restartPos = player.transform.position;
        stalker.homePos = stalkerGo.transform.position;
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
        hud.stalker = stalker;
        check.stalker = stalker;

        var mining = new GameObject("Mining");
        var fx = mining.AddComponent<MiningFx>();
        fx.player = p;
        fx.orePrefab = ore;
        fx.chipMeshes = chips.GetComponentsInChildren<MeshFilter>().Select(f => f.sharedMesh).ToArray();
        fx.chipMaterial = chips.GetComponentInChildren<MeshRenderer>().sharedMaterial;
        fx.dustMaterial = MakeDustMaterial();
        fx.hitClips = hitClips;
        mining.AddComponent<MiningHud>().player = p;

        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        PlayerSettings.productName = "Tunnel";
        PlayerSettings.companyName = "jhyun1234";
        AssetDatabase.SaveAssets();
        Debug.Log($"M1 scene saved: {ScenePath}");
    }

    public static void BuildWindows()
    {
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = ExePath,
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None,
        });
        Debug.Log($"BUILD {report.summary.result} errors={report.summary.totalErrors} size={report.summary.totalSize / 1048576} MB");
        EditorApplication.Exit(report.summary.result == BuildResult.Succeeded ? 0 : 1);
    }

    static GameObject Instance(GameObject prefab, Transform parent)
    {
        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
        PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        return go;
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
