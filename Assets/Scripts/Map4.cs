using System.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;

// MAP4 1편 전체 (사용자 10-01 "전체 맵을 끝까지 만들어라. 그 뒤에 텍스처 · 구조를 말하겠다").
// exe 를 -map4 로 띄우면 인트로 → 시작 → 부스 맵 아래(Offset) 새 맵 승강장에서 시작한다 (괴물 없음 — 구조 · 텍스처 판정용).
// Assets/Fab/Resources/Map4.glb 는 git 에 없다(Fab 재배포 금지). 만드는 법: SCENE=m EXPORT_GLB=Assets/Fab/Resources/Map4.glb blender -b --factory-startup -P blender/map/scene_mock.py
// 빛 · 화각 = 영상 재현 판정값 Tuning.FAB_* (전등 세기 · 반경 · 주황 · 화각 85 · 은은한 빛 · 색보정). ZL_<rrggbb>_<i> = 구역 입구 색 등(카드 15).
// 판정 키: ] 다음 · [ 앞 장면 자리 (CAM_<구역>_<그림> = Blender 시안과 같은 자리, 처음은 CAM_start 승강장)
// 밝기 판정 키(10-01 v2 "전체가 많이 어둡다" — 전등을 101개로 늘리고 줄에 매달아 내려도 바닥은 어둡다 → 세기 · 거리는 사용자가 고른다, -fabvideo 와 같은 키):
// 1 2 전등 세기 · 3 4 빛이 닿는 거리 · 9 0 은은한 빛 · B 판정값(Tuning.FAB_*)으로. 값은 화면 왼쪽 아래. 이 모드에선 DevHud 를 끈다(같은 키).
public class Map4 : MonoBehaviour
{
    public static readonly Vector3 Offset = new Vector3(0f, -200f, 0f);
    public static bool Requested => System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-map4") >= 0;
    public Player player; public Camera cam;
    public Transform[] spots; int spot;
    [System.NonSerialized] public float power = Tuning.FAB_LIGHT_ENERGY, range = Tuning.FAB_LIGHT_RANGE, fill = Tuning.FAB_AMBIENT_FILL;
    Light[] lamps; (Light l, float mul)[] zone;                  // LAMP_ = 판정값 그대로 · ZL_ = 세기 × mul, 거리 + 1 m

    public static Map4 Spawn(Player player, Camera cam)
    {
        var go = FabTest.Spawn("Map4", Offset);
        if (go == null) return null;
        var warm = Color.Lerp(FabTest.White, Tuning.BOOTH_LIGHT_COLOR, Tuning.FAB_LIGHT_ORANGE);
        var lamps = go.GetComponentsInChildren<Light>().Where(l => l.name.StartsWith("LAMP_")).ToArray();
        foreach (var l in lamps) l.color = warm;
        var zone = new System.Collections.Generic.List<(Light, float)>();
        foreach (var t in go.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("ZL_")))
        {
            var l = t.gameObject.AddComponent<Light>();
            l.type = LightType.Point; ColorUtility.TryParseHtmlString("#" + t.name.Substring(3, 6), out var c); l.color = c;
            bool warmWhite = c.r > 0.9f && c.g > 0.4f && c.b < 0.5f;   // 작업등 · 주황 = 따뜻한 흰빛 계열
            l.shadows = LightShadows.None; zone.Add((l, warmWhite ? 0.8f : 0.4f));   // 구역 색 등(파랑 · 초록 · 빨강 · 흰색)은 약하게 (검수 10-01: 방 전체가 파랗게 번지고 판자 문이 새빨갛게 물들었다)
            l.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer;
        }
        // 전등 갓 · 줄은 그림자를 안 만든다 — 줄에 매달아 내린 전등의 갓이 제 빛을 가려 천장에 큰 검은 얼룩을 만들었다 (검수 10-01)
        foreach (var r in go.GetComponentsInChildren<Renderer>().Where(r => r.name.Contains("vgyidfpaw") || r.name.StartsWith("NOCOL_LAMPCORD")))
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        if (Tuning.FAB_COLOR_GRADE) FabTest.Grade();
        var m = go.AddComponent<Map4>(); m.player = player; m.cam = cam; m.lamps = lamps; m.zone = zone.ToArray(); m.Apply();
        m.spots = go.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("CAM_")).OrderBy(t => t.name == "CAM_start" ? "" : t.name).ToArray();
        m.Go(0);
        return m;
    }

    public void Go(int i)
    {
        if (spots.Length == 0) return;
        spot = (i % spots.Length + spots.Length) % spots.Length;
        FabTest.StandAt(player, spots[spot], FabTest.Node(gameObject, "AT_" + spots[spot].name.Substring(4)));
    }

    void Apply()
    {
        foreach (var l in lamps) { l.intensity = power; l.range = range; }
        foreach (var (l, mul) in zone) { l.intensity = power * mul; l.range = range + 1f; }
    }

    void Update()
    {
        // 머리 위가 선 몸(BODY_HEIGHT + 15 cm)보다 낮으면 저절로 숙인다 — Ctrl 을 떼도 천장 속으로 서지 않게 (공은 내 몸 캡슐 안 0.5 m 에서 출발해 제 몸은 안 맞는다, 공 꼭대기 0.75 m → 1.95 m)
        player.forceCrouch = Physics.SphereCast(player.transform.position + Vector3.up * 0.5f, 0.25f, Vector3.up, out _, Tuning.BODY_HEIGHT + 0.15f - 0.75f, ~0, QueryTriggerInteraction.Ignore);
        var k = UnityEngine.InputSystem.Keyboard.current; if (k == null || k.shiftKey.isPressed) return;
        if (k.rightBracketKey.wasPressedThisFrame) Go(spot + 1);
        else if (k.leftBracketKey.wasPressedThisFrame) Go(spot - 1);
        else if (k.digit1Key.wasPressedThisFrame) power = Mathf.Max(0f, power - 4f);
        else if (k.digit2Key.wasPressedThisFrame) power += 4f;
        else if (k.digit3Key.wasPressedThisFrame) range = Mathf.Max(1f, range - 1f);
        else if (k.digit4Key.wasPressedThisFrame) range += 1f;
        else if (k.digit9Key.wasPressedThisFrame) fill = Mathf.Max(0f, fill - 0.02f);
        else if (k.digit0Key.wasPressedThisFrame) fill += 0.02f;
        else if (k.bKey.wasPressedThisFrame) { power = Tuning.FAB_LIGHT_ENERGY; range = Tuning.FAB_LIGHT_RANGE; fill = Tuning.FAB_AMBIENT_FILL; }
        else return;
        Apply();
    }

    void LateUpdate()
    {
        RenderSettings.ambientLight += FabTest.FillColor * fill;   // Headlamp 가 매 프레임 환경광(어둠 적응 포함)을 새로 쓴 뒤에 더한다
        if (cam != null) cam.fieldOfView = Tuning.FAB_CAMERA_FOV;
    }

    void OnGUI()
    {
        if (spots.Length > 0) GUI.Label(new Rect(10, Screen.height - 28, 900, 24), $"MAP4  spot {spot + 1}/{spots.Length} {spots[spot].name.Substring(4)}   [ ] = prev / next spot");
        GUI.Label(new Rect(10, Screen.height - 52, 1100, 24), $"lamp power {power:0} [1 2]   reach {range:0} m [3 4]   soft fill {fill:0.00} [9 0]   B = judged values ({Tuning.FAB_LIGHT_ENERGY:0} / {Tuning.FAB_LIGHT_RANGE:0} m / {Tuning.FAB_AMBIENT_FILL:0.00})   lamps {lamps.Length + zone.Length}");
    }
}
