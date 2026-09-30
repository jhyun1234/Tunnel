using System.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;

// 엔진 확인(사용자 09-30 "엔진의 한계인가? 게임은 찰흙처럼 보인다"): Blender 시안 ③ 광차 싣는 곳(Fab 강철 아치 갱도)을 그대로 게임에 넣는다.
// exe 를 -fabtest 로 띄우면 부스 맵 아래(Offset)에 Assets/Fab/Resources/FabTest.glb 를 놓고 그 안에서 시작한다 (괴물 없음).
// 파일은 git 에 없다(Fab 재배포 금지) — 없으면 아무것도 안 한다. 만드는 법: SCENE=3 EXPORT_GLB=... blender/map/scene_mock.py
// 빈 노드: CAM_<이름>(Blender 시안의 카메라 자리) · AT_<이름>(보는 곳) · LAMP_<i>(전등 — 부스 전등과 같은 빛)
public static class FabTest
{
    public static readonly Vector3 Offset = new Vector3(0f, -120f, 0f);
    public static bool Requested => System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-fabtest") >= 0;

    // res = Resources 이름(FabTest = 시안 ③ · FabVideo = Fab 소개 영상 재현), at = 놓을 자리 (기본 Offset)
    public static GameObject Spawn(string res = "FabTest", Vector3? at = null)
    {
        var src = Resources.Load<GameObject>(res);
        if (src == null) { Debug.Log($"FABTEST no Assets/Fab/Resources/{res}.glb in this build"); return null; }
        var go = Object.Instantiate(src, at ?? Offset, Quaternion.identity); go.name = res;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>())
            mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
        foreach (var t in go.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("LAMP_")))
        {
            var l = t.gameObject.AddComponent<Light>();
            l.type = LightType.Point; l.color = Tuning.BOOTH_LIGHT_COLOR; l.intensity = Tuning.BOOTH_LIGHT_ENERGY; l.range = Tuning.BOOTH_LIGHT_RANGE;
            l.shadows = LightShadows.Soft;
            l.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer;
        }
        foreach (var t in go.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("BLUE_")))   // 영상 재현: 먼 곳 차가운 빛 (처음엔 꺼 둔다)
        {
            var l = t.gameObject.AddComponent<Light>();
            l.type = LightType.Point; l.color = new Color(0.35f, 0.55f, 1f); l.intensity = 25f; l.range = 10f; l.shadows = LightShadows.Soft;
            l.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer; l.enabled = false;
        }
        return go;
    }

    public static Transform Node(GameObject go, string name) => go.GetComponentsInChildren<Transform>().FirstOrDefault(t => t.name == name);

    public static readonly Color White = new Color(1f, 0.93f, 0.85f), FillColor = new Color(1f, 0.85f, 0.72f);   // 흰 전등 · 은은한 빛 색 (영상 재현)

    // 색보정 (영상 재현 C 키 — 사용자 10-01 새 맵에 켬): 그늘은 푸르게 · 밝은 곳은 따뜻하게
    public static UnityEngine.Rendering.Volume Grade()
    {
        var g = new GameObject("VideoGrade"); var vol = g.AddComponent<UnityEngine.Rendering.Volume>(); vol.isGlobal = true; vol.priority = 100;
        vol.profile = ScriptableObject.CreateInstance<UnityEngine.Rendering.VolumeProfile>();
        var smh = vol.profile.Add<ShadowsMidtonesHighlights>(true);
        smh.shadows.Override(new Vector4(0.85f, 0.95f, 1.2f, 0f)); smh.highlights.Override(new Vector4(1.12f, 1.0f, 0.85f, 0f));
        return vol;
    }

    // 카메라 자리에 플레이어를 세운다: 발 = 카메라 밑 바닥 (숙인 눈 1.0 m 자리도 — 눈 − EYE_HEIGHT 면 바닥 밑으로 빠진다), 고개 = 보는 곳 쪽
    public static void StandAt(Player player, Transform cam, Transform at)
    {
        var cc = player.GetComponent<CharacterController>();
        Vector3 d = at.position - cam.position;
        cc.enabled = false;
        Physics.SyncTransforms();
        Vector3 feet = Physics.Raycast(cam.position + Vector3.up * 0.1f, Vector3.down, out var hit, 4f) ? hit.point : cam.position - Vector3.up * Tuning.EYE_HEIGHT;
        player.transform.SetPositionAndRotation(feet + Vector3.up * 0.05f,
            Quaternion.Euler(0f, Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg, 0f));
        cc.enabled = true;
        player.Pitch = -Mathf.Atan2(d.y, new Vector2(d.x, d.z).magnitude) * Mathf.Rad2Deg;
    }
}

// 영상 재현 판정 모드 (사용자 09-30 "판정 키 넣은 실행 파일"): exe 를 -fabvideo 로 띄우면 FabVideo.glb(영상 5 초 컷 재현)에서 시작하고 키로 빛 · 화각을 바꾼다.
// 이 모드에선 DevHud 를 끈다(키가 거의 다 판정 키로 쓰여 부딪힌다). 값은 왼쪽 위에 영어로 (기본 글꼴에 한글이 없다) — 고른 숫자를 받아 Tuning 에 넣는다.
// 1 2 전등 세기 · 3 4 전등 반경 · 5 6 주황 정도(0 흰빛 ~ 1 지금 주황) · 7 8 화각 · 9 0 은은한 빛(튀는 빛 흉내 = 환경광에 더함)
// Z 채움 · X 먼 곳 차가운 빛 · C 색보정 · V 추천값(재현 v9) · B 옛 부스 게임 값 · R 처음 자리 · F 머리등(원래 키). 처음 값 = Tuning.FAB_*(사용자 판정 10-01)
public class FabVideoTuner : MonoBehaviour
{
    public Player player; public Camera cam;
    float power = Tuning.FAB_LIGHT_ENERGY, range = Tuning.FAB_LIGHT_RANGE, orange = Tuning.FAB_LIGHT_ORANGE, fov = Tuning.FAB_CAMERA_FOV, fill = Tuning.FAB_AMBIENT_FILL;   // 처음 = 사용자 판정값(10-01)
    bool dress = true, blue = Tuning.FAB_BLUE_FAR, grade = Tuning.FAB_COLOR_GRADE;   // 처음 = 사용자 판정(10-01): 채움 넣음 · 먼 빛은 구역 입구 등으로만 · 색보정 켬
    Light[] lamps, blues; GameObject[] dressing; UnityEngine.Rendering.Volume vol; Transform start, look;
    static Color White => FabTest.White; static Color FillColor => FabTest.FillColor;

    void Start()
    {
        lamps = GetComponentsInChildren<Light>(true).Where(l => l.name.StartsWith("LAMP_")).ToArray();
        blues = GetComponentsInChildren<Light>(true).Where(l => l.name.StartsWith("BLUE_")).ToArray();
        dressing = GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("DRESS_")).Select(t => t.gameObject).ToArray();
        var cams = GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("CAM_")).OrderBy(t => t.name).ToArray();
        start = cams.FirstOrDefault(); look = start ? FabTest.Node(gameObject, "AT_" + start.name.Substring(4)) : null;
        vol = FabTest.Grade();
        if (start) FabTest.StandAt(player, start, look);
        Apply();
    }

    void Update()
    {
        var k = UnityEngine.InputSystem.Keyboard.current; if (k == null) return;
        bool changed = true;
        if (k.digit1Key.wasPressedThisFrame) power = Mathf.Max(0f, power - 4f);
        else if (k.digit2Key.wasPressedThisFrame) power += 4f;
        else if (k.digit3Key.wasPressedThisFrame) range = Mathf.Max(1f, range - 1f);
        else if (k.digit4Key.wasPressedThisFrame) range += 1f;
        else if (k.digit5Key.wasPressedThisFrame) orange = Mathf.Max(0f, orange - 0.1f);
        else if (k.digit6Key.wasPressedThisFrame) orange = Mathf.Min(1f, orange + 0.1f);
        else if (k.digit7Key.wasPressedThisFrame) fov = Mathf.Max(30f, fov - 5f);
        else if (k.digit8Key.wasPressedThisFrame) fov = Mathf.Min(100f, fov + 5f);
        else if (k.digit9Key.wasPressedThisFrame) fill = Mathf.Max(0f, fill - 0.02f);
        else if (k.digit0Key.wasPressedThisFrame) fill += 0.02f;
        else if (k.zKey.wasPressedThisFrame) dress = !dress;
        else if (k.xKey.wasPressedThisFrame) blue = !blue;
        else if (k.cKey.wasPressedThisFrame) grade = !grade;
        else if (k.vKey.wasPressedThisFrame) { power = 28f; range = 9f; orange = 0.5f; fov = 50f; fill = 0.16f; dress = blue = grade = true; }
        else if (k.bKey.wasPressedThisFrame) { power = Tuning.BOOTH_LIGHT_ENERGY; range = Tuning.BOOTH_LIGHT_RANGE; orange = 1f; fov = Tuning.CAMERA_FOV; fill = 0f; grade = false; }
        else if (k.rKey.wasPressedThisFrame && start) FabTest.StandAt(player, start, look);
        else changed = false;
        if (changed) Apply();
    }

    void Apply()
    {
        foreach (var l in lamps) { l.intensity = power; l.range = range; l.color = Color.Lerp(White, Tuning.BOOTH_LIGHT_COLOR, orange); }
        foreach (var l in blues) l.enabled = blue;
        foreach (var d in dressing) d.SetActive(dress);
        vol.enabled = grade; cam.fieldOfView = fov;
    }

    void LateUpdate() => RenderSettings.ambientLight += FillColor * fill;   // Headlamp 가 매 프레임 환경광(어둠 적응 포함)을 새로 쓴 뒤에 더한다

    void OnGUI()
    {
        GUI.Box(new Rect(10, 10, 900, 64), "");
        GUI.Label(new Rect(20, 16, 880, 60),
            $"FAB VIDEO TEST   lamp power {power:0} [1 2]   range {range:0} m [3 4]   orange {orange:0.0} [5 6]   fov {fov:0} [7 8]   fill {fill:0.00} [9 0]\n" +
            $"dress {(dress ? "ON" : "off")} [Z]   blue far {(blue ? "ON" : "off")} [X]   grade {(grade ? "ON" : "off")} [C]   V = recommended (v9)   B = game values now   R = start   F = headlamp");
    }
}
