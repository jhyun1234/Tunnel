using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

// 마일스톤 1 씬 만들기와 Windows 빌드. 배치 모드에서 부른다 (명령은 docs/HANDOFF.md, tools/build.sh).
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
        if (piece == null)
        {
            Debug.LogError($"{PiecePath} 를 못 읽었다 (glTFast 임포트 확인)");
            EditorApplication.Exit(3);
            return;
        }

        var pick = AssetDatabase.LoadAssetAtPath<GameObject>(PickPath);
        var ore = AssetDatabase.LoadAssetAtPath<GameObject>(OrePath);
        var chips = AssetDatabase.LoadAssetAtPath<GameObject>(ChipsPath);
        if (pick == null || ore == null || chips == null)
        {
            Debug.LogError("pick / ore / mine_chips glTF 를 못 읽었다 (glTFast 임포트 확인)");
            EditorApplication.Exit(3);
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
            var go = (GameObject)PrefabUtility.InstantiatePrefab(piece, pieces);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
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
        camGo.AddComponent<UniversalAdditionalCameraData>().renderPostProcessing = true;
        camGo.AddComponent<AudioListener>();

        // 곡괭이 뷰모델 (카메라 밑). 자세·배율은 Pickaxe.Awake 가 Tuning 에서 넣는다
        var pickGo = new GameObject("Pickaxe");
        pickGo.transform.SetParent(camGo.transform, false);
        var pickaxe = pickGo.AddComponent<Pickaxe>();
        pickaxe.cam = camGo.transform;
        pickaxe.player = p;
        pickaxe.mesh = Instance(pick, pickGo.transform).transform;

        var lampGo = new GameObject("Headlamp");
        Headlamp.Apply(lampGo.AddComponent<Light>());
        lampGo.transform.SetPositionAndRotation(camGo.transform.TransformPoint(Tuning.LAMP_OFFSET), camGo.transform.rotation);
        var lamp = lampGo.AddComponent<Headlamp>();
        lamp.cam = camGo.transform;
        var vol = lampGo.AddComponent<VolumetricAdditionalLight>();
        vol.Anisotropy = Tuning.VOLFOG_ANISOTROPY;
        vol.Scattering = Tuning.VOLFOG_SCATTERING;

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

        var mining = new GameObject("Mining");
        var fx = mining.AddComponent<MiningFx>();
        fx.player = p;
        fx.orePrefab = ore;
        fx.chipMeshes = chips.GetComponentsInChildren<MeshFilter>().Select(f => f.sharedMesh).ToArray();
        fx.chipMaterial = chips.GetComponentInChildren<MeshRenderer>().sharedMaterial;
        fx.dustMaterial = MakeDustMaterial();
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
