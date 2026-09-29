using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

// 3D-P 차례 3 판정 ③(뼈대): 플레이어 몸(Assets/Tunnel/Player/player.fbx, Mixamo 뼈대 + 우리 그림 · 소품)에
// Kevin 사람형 동작(서 있기 → 서서 캐기 → 한 바퀴 돌기)을 입혀 3인칭으로 찍는다 → build/playerrig/f_###.png (+ log.txt).
// 게임 코드는 건드리지 않는다. Kevin 묶음(Assets/Kevin Iglesias/, git 에서 뺌)이 없으면 아무것도 안 한다.
// 부르기: 에디터가 닫혀 있을 때
//   Unity.exe -batchmode -quit -projectPath . -executeMethod PlayerRigTest.CaptureBatch -logFile build/playerrig/unity.log
public static class PlayerRigTest
{
    const string PLAYER = "Assets/Tunnel/Player/player.fbx";
    const string KI = "Assets/Kevin Iglesias/Human Animations/Animations/Male/";
    const string IDLE = KI + "Idles/HumanM@Idle01.fbx";
    const string MINE = KI + "Work/Mining/HumanM@MiningOneHand01_R - Wall.fbx";
    const int W = 960, H = 540, FPS = 30;

    public static void CaptureBatch()
    {
        string log;
        try { log = Capture(); }
        catch (System.Exception e) { log = "ERROR " + e; }
        Debug.Log("[PlayerRigTest] " + log);
        EditorApplication.Exit(log.StartsWith("ERROR") ? 1 : 0);
    }

    const string SKIN_MAT = "Assets/Tunnel/Player/PlayerSkin.mat";

    // player.fbx 를 사람형(Humanoid)으로 읽고, 몸 재질 자리(PlayerSkin)에 우리 그림 재질을 끼운다 — .meta 에 남는다
    // (FBX 안에 그림을 넣어 보냈더니 Unity 가 그림을 꺼내지 않아 몸이 하얗게 나왔다, 09-29)
    static void EnsureImport()
    {
        var mi = (ModelImporter)AssetImporter.GetAtPath(PLAYER);
        if (mi == null) throw new System.Exception("없음: " + PLAYER);
        var skin = AssetDatabase.LoadAssetAtPath<Material>(SKIN_MAT);
        if (skin == null)
        {
            skin = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "PlayerSkin" };
            skin.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Tunnel/Player/Textures/player_base.png"));
            skin.SetColor("_BaseColor", Color.white);
            skin.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Tunnel/Player/Textures/player_nor_gl.png"));
            skin.EnableKeyword("_NORMALMAP");
            skin.SetFloat("_Smoothness", 0.25f);                                 // ※ 천 · 고무 · 살 한 값(어림) — Meshy 거칠기 그림은 URP 와 채널이 달라 안 씀
            AssetDatabase.CreateAsset(skin, SKIN_MAT);
        }
        var id = new AssetImporter.SourceAssetIdentifier(typeof(Material), "PlayerSkin");
        bool remapped = mi.GetExternalObjectMap().TryGetValue(id, out var cur) && cur == skin;
        if (mi.animationType == ModelImporterAnimationType.Human && mi.avatarSetup == ModelImporterAvatarSetup.CreateFromThisModel && remapped) return;
        mi.animationType = ModelImporterAnimationType.Human;
        mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
        mi.importAnimation = false; mi.importCameras = false; mi.importLights = false;
        mi.AddRemap(id, skin);
        mi.SaveAndReimport();
    }

    public static string Capture()
    {
        if (AssetDatabase.LoadAssetAtPath<GameObject>(IDLE) == null) return "Kevin 묶음 없음: " + IDLE;
        EnsureImport();
        var model = AssetDatabase.LoadAssetAtPath<GameObject>(PLAYER);
        var idle = LoadClip(IDLE); var mine = LoadClip(MINE);
        string outDir = Path.GetFullPath("build/playerrig");
        Directory.CreateDirectory(outDir);
        foreach (var f in Directory.GetFiles(outDir, "*.png")) File.Delete(f);

        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.22f, 0.22f, 0.24f);
        RenderSettings.fog = false;

        var man = (GameObject)PrefabUtility.InstantiatePrefab(model, scene);
        man.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);   // 모델 앞 = +Z = 카메라 쪽(180° 로 돌렸더니 등을 보였다)
        var anim = man.GetComponent<Animator>();
        if (anim == null || anim.avatar == null || !anim.avatar.isHuman) return "ERROR 사람형 아바타 없음 — " + (anim == null ? "Animator 없음" : anim.avatar == null ? "avatar 없음" : "isHuman=false");
        anim.applyRootMotion = false;
        foreach (var smr in man.GetComponentsInChildren<SkinnedMeshRenderer>()) smr.forceMatrixRecalculationPerRender = true;

        var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
        floor.transform.position = new Vector3(0f, -0.05f, 0f); floor.transform.localScale = new Vector3(10f, 0.1f, 10f);
        var lit = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        lit.SetColor("_BaseColor", new Color(0.30f, 0.29f, 0.28f)); lit.SetFloat("_Smoothness", 0.1f);
        floor.GetComponent<Renderer>().sharedMaterial = lit;
        var key = new GameObject("Key").AddComponent<Light>(); key.type = LightType.Directional; key.intensity = 1.3f; key.shadows = LightShadows.Soft;
        key.transform.rotation = Quaternion.Euler(40f, 150f, 0f);
        var fill = new GameObject("Fill").AddComponent<Light>(); fill.type = LightType.Directional; fill.intensity = 0.45f; fill.transform.rotation = Quaternion.Euler(20f, -30f, 0f);

        var cam = new GameObject("Cam").AddComponent<Camera>();
        cam.fieldOfView = 35f; cam.nearClipPlane = 0.1f; cam.farClipPlane = 50f; cam.enabled = false;
        cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0.30f, 0.30f, 0.31f);
        cam.transform.position = new Vector3(0.7f, 1.25f, 3.0f); cam.transform.LookAt(new Vector3(0f, 0.92f, 0f));   // 온몸이 화면 높이를 거의 채우게(4.2 m 는 작았다)
        var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
        var tex = new Texture2D(W, H, TextureFormat.RGB24, false);

        AnimationMode.StartAnimationMode();
        int frame = 0;
        void Pose(AnimationClip c, float t) { AnimationMode.BeginSampling(); AnimationMode.SampleAnimationClip(man, c, t); AnimationMode.EndSampling(); }
        void Shot() => ShotTo(cam, rt, tex, Path.Combine(outDir, $"f_{frame++:000}.png"));
        string log;
        try
        {
            Pose(idle, 0f); ShotTo(cam, rt, tex, Path.Combine(outDir, "warmup.png"));                                 // 첫 장은 빛 · 그림자가 덜 차서 어둡다 — 버린다
            for (int i = 0; i < FPS * 2; i++) { Pose(idle, (i / (float)FPS) % idle.length); Shot(); }                // 서 있기 2 초
            int nm = Mathf.RoundToInt(mine.length * 3 * FPS);
            for (int i = 0; i < nm; i++) { Pose(mine, (i / (float)FPS) % mine.length); Shot(); }                      // 서서 캐기 세 번
            for (int i = 0; i < FPS * 5; i++)                                                                        // 한 바퀴(5 초) — 등 · 배터리 · 줄 · 번호
            {
                man.transform.rotation = Quaternion.Euler(0f, 360f * i / (FPS * 5), 0f);
                Pose(idle, (i / (float)FPS) % idle.length); Shot();
            }
            var hand = anim.GetBoneTransform(HumanBodyBones.RightHand);
            log = $"frames {frame} · idle {idle.length:F2}s · mine {mine.length:F2}s · avatar {anim.avatar.name} human={anim.avatar.isHuman} · right hand {hand.position}";
        }
        finally { if (AnimationMode.InAnimationMode()) AnimationMode.StopAnimationMode(); Object.DestroyImmediate(rt); Object.DestroyImmediate(tex); }
        File.WriteAllText(Path.Combine(outDir, "log.txt"), log);
        return log;
    }

    public static void InspectBatch()
    {
        var sb = new System.Text.StringBuilder();
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath(PLAYER))
        {
            if (o is Material m) sb.Append($"\nMAT {m.name} shader={m.shader.name} base={(m.HasProperty("_BaseMap") ? m.GetTexture("_BaseMap")?.name : "-")} color={(m.HasProperty("_BaseColor") ? m.GetColor("_BaseColor").ToString() : "-")} normal={(m.HasProperty("_BumpMap") ? m.GetTexture("_BumpMap")?.name : "-")}");
            else if (o is Texture2D t) sb.Append($"\nTEX {t.name} {t.width}x{t.height}");
        }
        Debug.Log("[PlayerRigTest] inspect" + sb);
        EditorApplication.Exit(0);
    }

    static AnimationClip LoadClip(string path)
    {
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath(path))
            if (o is AnimationClip c && !c.name.StartsWith("__preview")) return c;
        return null;
    }

    static void ShotTo(Camera cam, RenderTexture rt, Texture2D tex, string file)
    {
        var req = new RenderPipeline.StandardRequest { destination = rt };
        if (RenderPipeline.SupportsRenderRequest(cam, req)) RenderPipeline.SubmitRenderRequest(cam, req);
        else { cam.targetTexture = rt; cam.Render(); cam.targetTexture = null; }
        var old = RenderTexture.active; RenderTexture.active = rt;
        tex.ReadPixels(new Rect(0, 0, W, H), 0, 0); tex.Apply();
        RenderTexture.active = old;
        File.WriteAllBytes(file, tex.EncodeToPNG());
    }
}
