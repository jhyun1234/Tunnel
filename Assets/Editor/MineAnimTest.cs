using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

// 시험(09-27, 사용자 "Human Crafting Animations FREE 받아서 해봐라"): 에셋 스토어 캐기 동작 하나로
// 1인칭(눈 자리 카메라, 머리 숨김)과 3인칭(몸 전체)을 같은 순간에 찍어 build/mineanim/ 에 그림 줄을 남긴다.
// 게임 코드는 건드리지 않는다. 묶음(Assets/Kevin Iglesias/, git 에서 뺌)이 없으면 아무것도 안 한다.
// 부르기: 열린 에디터에서 unity command eval --code "MineAnimTest.Capture(); return 0;"
public static class MineAnimTest
{
    const string KI = "Assets/Kevin Iglesias/Human Animations/";
    const string MODEL = KI + "Models/HumanM_Model.fbx";
    const string CLIP = KI + "Animations/Male/Work/Mining/HumanM@MiningOneHand01_R - Wall.fbx";
    const int W = 960, H = 540, FPS = 30;
    const float LOOPS = 1f;
    static readonly Vector3 GRIP = new Vector3(0f, -0.08f, 0f);          // 우리 곡괭이에서 손이 쥐는 점 (자루 끝 -0.15 에서 7 cm)
    static readonly Vector3 BLADE_TIP = new Vector3(-0.252f, 0.47f, 0f); // 뾰족한 날 끝 (pick_meshy.glb, -X 쪽)

    public static string Capture(bool kevinPick = false)
    {
        if (AssetDatabase.LoadAssetAtPath<GameObject>(MODEL) == null) return "묶음 없음: " + MODEL;
        var clip = LoadClip(CLIP);
        string outDir = Path.GetFullPath("build/mineanim");
        Directory.CreateDirectory(outDir);
        foreach (var f in Directory.GetFiles(outDir, "*.png")) File.Delete(f);

        var prev = SceneManager_GetActive();
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
        UnityEngine.SceneManagement.SceneManager.SetActiveScene(scene);
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.10f, 0.10f, 0.11f);
        RenderSettings.fog = false;
        string log;
        try
        {
            var man = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(MODEL), scene);
            man.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            var anim = man.GetComponent<Animator>();
            anim.applyRootMotion = false;
            var head = anim.GetBoneTransform(HumanBodyBones.Head);
            var hand = FindDeep(man.transform, "B-handProp.R") ?? anim.GetBoneTransform(HumanBodyBones.RightHand);
            var headToBody = Quaternion.Inverse(head.rotation) * man.transform.rotation;   // 쉬는 자세에서 머리 → 몸 앞

            // 에디터(재생 아님)에서 사람형 동작을 입히는 길 = 애니메이션 창과 같은 AnimationMode 샘플링
            AnimationMode.StartAnimationMode();
            void Pose(float t) { AnimationMode.BeginSampling(); AnimationMode.SampleAnimationClip(man, clip, t); AnimationMode.EndSampling(); }
            foreach (var smr in man.GetComponentsInChildren<SkinnedMeshRenderer>()) smr.forceMatrixRecalculationPerRender = true;   // 한 번에 두 카메라로 찍어도 살이 뼈를 따라가게

            // 우리 곡괭이를 오른손 소품 뼈에 — 자루 = 뼈 Y (Kevin 곡괭이와 같은 축), 쥐는 점 = 뼈 자리
            var pick = (GameObject)Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Tunnel/Props/pick_meshy.glb"));
            pick.name = "OurPick";
            pick.transform.SetParent(hand, false);
            pick.transform.localPosition = -GRIP;
            if (kevinPick)   // 비교용: 묶음에 든 Kevin 곡괭이를 데모 장면처럼 손 소품 뼈에 그대로
            {
                var kp = (GameObject)Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(KI + "Unity Demo Scenes/Human Crafting Animations/Prefabs/Tools/Human_Pickaxe.prefab"));
                kp.transform.SetParent(hand, false);
                pick.SetActive(false);
            }
            // 날이 벽 쪽을 보도록: 가장 앞으로 나간 순간에 날(-X)이 몸 앞(+Z)을 보는지 재고, 아니면 180° 돌린다
            float strikeT = 0f, bestZ = -9f;
            for (int i = 0; i <= 60; i++)
            {
                float t = clip.length * i / 60f; Pose(t);
                float z = hand.TransformPoint(new Vector3(0f, 0.55f, 0f)).z;
                if (z > bestZ) { bestZ = z; strikeT = t; }
            }
            Pose(strikeT);
            if (Vector3.Dot(-hand.right, Vector3.forward) < 0f) pick.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            var tipAtStrike = pick.transform.TransformPoint(BLADE_TIP);

            // 벽: 날 끝이 가장 앞으로 나간 자리에 벽면 (2 cm 박힘)
            float wallZ = tipAtStrike.z - 0.02f;
            var rock = AssetDatabase.LoadAssetAtPath<Material>("Assets/Tunnel/Art/M11_MineRock.mat");
            var wall = GameObject.CreatePrimitive(PrimitiveType.Cube);
            wall.name = "Wall"; wall.transform.position = new Vector3(0f, 1.5f, wallZ + 0.25f); wall.transform.localScale = new Vector3(14f, 3.2f, 0.5f);
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor"; floor.transform.position = new Vector3(0f, -0.05f, 0f); floor.transform.localScale = new Vector3(14f, 0.1f, 14f);
            var lit = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            lit.SetColor("_BaseColor", new Color(0.32f, 0.30f, 0.28f)); lit.SetFloat("_Smoothness", 0.15f);
            wall.GetComponent<Renderer>().sharedMaterial = lit;
            floor.GetComponent<Renderer>().sharedMaterial = lit;
            var orePrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Tunnel/Art/ore_lump.gltf");
            if (orePrefab != null) { var ore = Object.Instantiate(orePrefab); ore.name = "Ore"; ore.transform.position = new Vector3(tipAtStrike.x, tipAtStrike.y, wallZ + 0.02f); }

            // 머리등: 머리에 붙은 빛 하나(1인칭 · 3인칭 같은 빛) + 3인칭에서 몸을 알아보게 약한 채움 빛
            var lampGo = new GameObject("HeadLamp"); var lamp = lampGo.AddComponent<Light>();
            lamp.type = LightType.Spot; lamp.spotAngle = 60f; lamp.innerSpotAngle = 18f; lamp.range = 14f; lamp.intensity = 6f;
            lamp.color = new Color(1f, 0.93f, 0.8f); lamp.shadows = LightShadows.Soft;
            var fillGo = new GameObject("Fill"); var fill = fillGo.AddComponent<Light>();
            fill.type = LightType.Point; fill.range = 8f; fill.intensity = 1.2f; fillGo.transform.position = new Vector3(2.2f, 2.2f, -1.8f);

            var cam1 = NewCam("Cam1P", 80f, 0.03f);   // 게임과 같은 세로 80°
            var cam3 = NewCam("Cam3P", 50f, 0.1f);
            cam3.transform.position = new Vector3(2.0f, 1.75f, -1.7f);
            cam3.transform.LookAt(new Vector3(0f, 1.1f, wallZ * 0.5f));
            var rt = new RenderTexture(W, H, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
            var tex = new Texture2D(W, H, TextureFormat.RGB24, false);
            var aimPoint = new Vector3(tipAtStrike.x * 0.5f, tipAtStrike.y, wallZ);

            int n = Mathf.RoundToInt(clip.length * LOOPS * FPS);
            for (int i = 0; i < n; i++)
            {
                float t = (i / (float)FPS) % clip.length; Pose(t);
                // 1인칭: 눈 = 머리뼈에서 위 8 cm · 앞 10 cm. 방향은 광석을 보되 머리 흔들림을 20 % 만 따른다(멀미 방지)
                var headFwd = head.rotation * headToBody;
                var eye = head.position + headFwd * (Vector3.up * 0.08f + Vector3.forward * 0.10f);
                var look = Quaternion.LookRotation(aimPoint - eye, Vector3.up);
                cam1.transform.SetPositionAndRotation(eye, Quaternion.Slerp(look, headFwd * Quaternion.Euler(20f, 0f, 0f), 0.2f));
                lampGo.transform.SetPositionAndRotation(eye + headFwd * new Vector3(0f, 0.06f, 0f), cam1.transform.rotation);

                var s = head.localScale; head.localScale = Vector3.one * 0.001f;   // 머리 숨김(1인칭만)
                Shot(cam1, rt, tex, Path.Combine(outDir, $"fp_{i:000}.png"));
                head.localScale = s;
                Shot(cam3, rt, tex, Path.Combine(outDir, $"tp_{i:000}.png"));
            }
            log = $"clip {clip.name} {clip.length:F3}s · frames {n} · strike {strikeT:F2}s · blade tip {tipAtStrike} · wall z {wallZ:F2} · blade flipped {pick.transform.localRotation != Quaternion.identity}";
            Object.DestroyImmediate(rt); Object.DestroyImmediate(tex);
        }
        finally
        {
            if (AnimationMode.InAnimationMode()) AnimationMode.StopAnimationMode();
            EditorSceneManager.CloseScene(scene, true);
            if (prev.IsValid()) UnityEngine.SceneManagement.SceneManager.SetActiveScene(prev);
        }
        File.WriteAllText(Path.Combine(outDir, "log.txt"), log);
        return log;
    }

    static UnityEngine.SceneManagement.Scene SceneManager_GetActive() => UnityEngine.SceneManagement.SceneManager.GetActiveScene();

    static AnimationClip LoadClip(string path)
    {
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath(path))
            if (o is AnimationClip c && !c.name.StartsWith("__preview")) return c;
        return null;
    }

    static Transform FindDeep(Transform t, string name)
    {
        if (t.name == name) return t;
        foreach (Transform c in t) { var r = FindDeep(c, name); if (r != null) return r; }
        return null;
    }

    static Camera NewCam(string name, float fov, float near)
    {
        var c = new GameObject(name).AddComponent<Camera>();
        c.fieldOfView = fov; c.nearClipPlane = near; c.farClipPlane = 50f;
        c.clearFlags = CameraClearFlags.SolidColor; c.backgroundColor = Color.black;
        c.enabled = false;
        return c;
    }

    static void Shot(Camera cam, RenderTexture rt, Texture2D tex, string file)
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
