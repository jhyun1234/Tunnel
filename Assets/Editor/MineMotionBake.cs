using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// MINE-2 (승인 09-28): Kevin Iglesias 캐기 동작 → 곡괭이 자리 표(MineMotion). 09-27 시험 MineAnimTest 와 같은 방법 —
// 사람 모형에 동작을 AnimationMode 로 입히고, 오른손 소품 뼈에 곡괭이를 쥐인 자리(쥐는 점 자루 끝에서 7 cm, 날이 벽 쪽)를 60 번/s 씩 잰다.
// 묶음(Assets/Kevin Iglesias/)이 없으면 아무것도 안 한다 — 있던 표는 그대로 둔다. BuildM1.BuildWindows 가 빌드 전에 부른다.
// 따로 부르기: Unity -batchmode -quit -executeMethod MineMotionBake.BakeCli
public static class MineMotionBake
{
    const string KI = "Assets/Kevin Iglesias/Human Animations/";
    const string MODEL = KI + "Models/HumanM_Model.fbx";
    public const string CLIP = KI + "Animations/Male/Work/Mining/HumanM@MiningOneHand01_R - Wall.fbx";
    public const string IDLE = KI + "Animations/Male/Idles/HumanM@Idle01.fbx";   // 3D-P 플레이어 몸 서 있기 (BuildM1.MakePlayerAnimator)
    public const string AssetPath = "Assets/Resources/Generated/MineMotion.asset";   // .gitignore — 에셋 스토어 약관(원본 재배포 금지), 저장소가 공개
    static readonly Vector3 GRIP = new Vector3(0f, -0.08f, 0f);   // 곡괭이 모델에서 손이 쥐는 점 (자루 끝 −0.15 에서 7 cm, 09-27 시험 값)
    const float RATE = 60f;

    public static void BakeCli() => EditorApplication.Exit(Bake() == null ? 1 : 0);

    public static string Bake()
    {
        if (AssetDatabase.LoadAssetAtPath<GameObject>(MODEL) == null) { Debug.Log($"MINEMOTION skip: {MODEL} 없음 (다른 컴퓨터) — 있던 표 그대로"); return "skip"; }
        AnimationClip clip = null;
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath(CLIP))
            if (o is AnimationClip c && !c.name.StartsWith("__preview")) clip = c;
        if (clip == null) { Debug.LogError($"MINEMOTION 동작 없음: {CLIP}"); return null; }

        var prev = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        bool additive = !string.IsNullOrEmpty(prev.path);                    // 배치 모드는 저장 안 된 빈 씬 하나뿐 — 그땐 새 씬으로 바꾼다
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, additive ? NewSceneMode.Additive : NewSceneMode.Single);
        UnityEngine.SceneManagement.SceneManager.SetActiveScene(scene);
        try
        {
            var man = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(MODEL), scene);
            man.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            var anim = man.GetComponent<Animator>();
            anim.applyRootMotion = false;
            var head = anim.GetBoneTransform(HumanBodyBones.Head);
            var hand = FindDeep(man.transform, "B-handProp.R") ?? anim.GetBoneTransform(HumanBodyBones.RightHand);
            var headToBody = Quaternion.Inverse(head.rotation) * man.transform.rotation;   // 쉬는 자세에서 머리 → 몸 앞

            AnimationMode.StartAnimationMode();
            void Pose(float t) { AnimationMode.BeginSampling(); AnimationMode.SampleAnimationClip(man, clip, t); AnimationMode.EndSampling(); }

            var pick = new GameObject("PickRoot").transform;                  // 곡괭이 모델 뿌리 자리 (모델은 안 넣는다 — 자리만)
            pick.SetParent(hand, false);
            pick.localPosition = -GRIP;
            // 내려친 순간 = 곡괭이 머리(자루 위 0.55 m)가 가장 앞으로 나간 때 · 뒤로 가장 크게 든 순간 = 가장 뒤(09-28 표: 가장 높은 때는 내려치는 도중이었다)
            // 빼기 시작 = 내려친 뒤 머리가 5 cm 넘게 움직이기 시작한 때 (박힌 채 1~4 cm 흔들리는 것은 버팀 — 09-28 표)
            const int STEPS = 240;
            var head55 = new Vector3[STEPS + 1];
            float strikeT = 0f, topT = 0f, releaseT = 0f, bestZ = -9f, backZ = 9f;
            for (int i = 0; i <= STEPS; i++)
            {
                float t = clip.length * i / STEPS; Pose(t);
                var h = head55[i] = hand.TransformPoint(new Vector3(0f, 0.55f, 0f));
                if (h.z > bestZ) { bestZ = h.z; strikeT = t; }
                if (h.z < backZ) { backZ = h.z; topT = t; }
            }
            int si = Mathf.RoundToInt(strikeT / clip.length * STEPS);
            for (int k = Mathf.CeilToInt(0.1f / clip.length * STEPS); k <= STEPS; k++)   // 내려친 뒤 0.1 s 는 튕김(최대 약 3 cm) — 건너뛴다
            {
                int i = (si + k) % STEPS;
                if ((head55[i] - head55[si]).magnitude > 0.05f) { releaseT = clip.length * ((si + k - 1) % STEPS) / STEPS; break; }
            }
            Pose(strikeT);
            bool flip = Vector3.Dot(-hand.right, Vector3.forward) < 0f;       // 날(모델 −X)이 벽(+Z) 쪽을 보게
            if (flip) pick.localRotation = Quaternion.Euler(0f, 180f, 0f);
            Vector3 Eye() { var f = head.rotation * headToBody; return head.position + f * (Vector3.up * 0.08f + Vector3.forward * 0.10f); }
            float Pitch() { var f = head.rotation * headToBody * Vector3.forward; return -Mathf.Asin(Mathf.Clamp(f.y, -1f, 1f)) * Mathf.Rad2Deg; }
            Vector3 eye0 = Eye();
            float pitch0 = Pitch();

            int n = Mathf.FloorToInt(clip.length * RATE) + 1;
            var mm = AssetDatabase.LoadAssetAtPath<MineMotion>(AssetPath);
            bool fresh = mm == null;
            if (fresh) mm = ScriptableObject.CreateInstance<MineMotion>();
            mm.clipName = clip.name; mm.length = clip.length; mm.strikeT = strikeT; mm.releaseT = releaseT; mm.topT = topT; mm.rate = RATE;
            mm.pickPos = new Vector3[n]; mm.pickRot = new Quaternion[n]; mm.eyePos = new Vector3[n]; mm.headPitch = new float[n];
            for (int i = 0; i < n; i++)
            {
                Pose(Mathf.Min(i / RATE, clip.length));
                mm.pickPos[i] = pick.position - eye0;                          // 몸 틀 = 모형 틀(모형은 원점 · 앞 +Z)
                mm.pickRot[i] = pick.rotation;
                mm.eyePos[i] = Eye() - eye0;
                mm.headPitch[i] = Pitch() - pitch0;
            }
            AnimationMode.StopAnimationMode();
            if (fresh)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(AssetPath));
                AssetDatabase.CreateAsset(mm, AssetPath);
            }
            else EditorUtility.SetDirty(mm);
            AssetDatabase.SaveAssets();
            string log = $"MINEMOTION {clip.name} length {clip.length:F3} s · strike {strikeT:F3} s · release {releaseT:F3} s · top(back) {topT:F3} s · samples {n} · flip {flip} · " +
                         $"pick root at strike {mm.pickPos[Mathf.RoundToInt(strikeT * RATE)]} (from eye) · eye height {eye0.y:F2} m";
            Debug.Log(log);
            return log;
        }
        finally
        {
            if (AnimationMode.InAnimationMode()) AnimationMode.StopAnimationMode();
            if (additive) EditorSceneManager.CloseScene(scene, true);
            if (additive && prev.IsValid()) UnityEngine.SceneManagement.SceneManager.SetActiveScene(prev);
        }
    }

    static Transform FindDeep(Transform t, string name)
    {
        if (t.name == name) return t;
        foreach (Transform c in t) { var r = FindDeep(c, name); if (r != null) return r; }
        return null;
    }
}
