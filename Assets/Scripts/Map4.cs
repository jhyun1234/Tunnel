using System.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;

// MAP4 1편 전체 (사용자 10-01 "전체 맵을 끝까지 만들어라. 그 뒤에 텍스처 · 구조를 말하겠다").
// exe 를 -map4 로 띄우면 인트로 → 시작 → 부스 맵 아래(Offset) 새 맵 승강장에서 시작한다 (괴물 없음 — 구조 · 텍스처 판정용).
// Assets/Fab/Resources/Map4.glb 는 git 에 없다(Fab 재배포 금지). 만드는 법: SCENE=m EXPORT_GLB=Assets/Fab/Resources/Map4.glb blender -b --factory-startup -P blender/map/scene_mock.py
// 빛 · 화각 = 영상 재현 판정값 Tuning.FAB_* (전등 세기 · 반경 · 주황 · 화각 85 · 은은한 빛 · 색보정). ZL_<rrggbb>_<i> = 구역 입구 색 등(카드 15).
// 판정 키: ] 다음 · [ 앞 장면 자리 (CAM_<구역>_<그림> = Blender 시안과 같은 자리, 처음은 CAM_start 승강장)
public class Map4 : MonoBehaviour
{
    public static readonly Vector3 Offset = new Vector3(0f, -200f, 0f);
    public static bool Requested => System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-map4") >= 0;
    public Player player; public Camera cam;
    public Transform[] spots; int spot;

    public static Map4 Spawn(Player player, Camera cam)
    {
        var go = FabTest.Spawn("Map4", Offset);
        if (go == null) return null;
        var warm = Color.Lerp(FabTest.White, Tuning.BOOTH_LIGHT_COLOR, Tuning.FAB_LIGHT_ORANGE);
        foreach (var l in go.GetComponentsInChildren<Light>().Where(l => l.name.StartsWith("LAMP_")))
        { l.intensity = Tuning.FAB_LIGHT_ENERGY; l.range = Tuning.FAB_LIGHT_RANGE; l.color = warm; }
        foreach (var t in go.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("ZL_")))
        {
            var l = t.gameObject.AddComponent<Light>();
            l.type = LightType.Point; ColorUtility.TryParseHtmlString("#" + t.name.Substring(3, 6), out var c); l.color = c;
            bool warmWhite = c.r > 0.9f && c.g > 0.4f && c.b < 0.5f;   // 작업등 · 주황 = 따뜻한 흰빛 계열
            l.intensity = Tuning.FAB_LIGHT_ENERGY * (warmWhite ? 0.8f : 0.4f); l.range = Tuning.FAB_LIGHT_RANGE + 1f; l.shadows = LightShadows.None;   // 구역 색 등(파랑 · 초록 · 빨강 · 흰색)은 약하게 (검수 10-01: 방 전체가 파랗게 번지고 판자 문이 새빨갛게 물들었다)
            l.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer;
        }
        if (Tuning.FAB_COLOR_GRADE) FabTest.Grade();
        var m = go.AddComponent<Map4>(); m.player = player; m.cam = cam;
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

    void Update()
    {
        // 머리 위가 선 몸(BODY_HEIGHT + 15 cm)보다 낮으면 저절로 숙인다 — Ctrl 을 떼도 천장 속으로 서지 않게 (공은 내 몸 캡슐 안 0.5 m 에서 출발해 제 몸은 안 맞는다, 공 꼭대기 0.75 m → 1.95 m)
        player.forceCrouch = Physics.SphereCast(player.transform.position + Vector3.up * 0.5f, 0.25f, Vector3.up, out _, Tuning.BODY_HEIGHT + 0.15f - 0.75f, ~0, QueryTriggerInteraction.Ignore);
        var k = UnityEngine.InputSystem.Keyboard.current; if (k == null || k.shiftKey.isPressed) return;
        if (k.rightBracketKey.wasPressedThisFrame) Go(spot + 1);
        else if (k.leftBracketKey.wasPressedThisFrame) Go(spot - 1);
    }

    void LateUpdate()
    {
        RenderSettings.ambientLight += FabTest.FillColor * Tuning.FAB_AMBIENT_FILL;   // Headlamp 가 매 프레임 환경광(어둠 적응 포함)을 새로 쓴 뒤에 더한다
        if (cam != null) cam.fieldOfView = Tuning.FAB_CAMERA_FOV;
    }

    void OnGUI()
    {
        if (spots.Length > 0) GUI.Label(new Rect(10, Screen.height - 28, 900, 24), $"MAP4  spot {spot + 1}/{spots.Length} {spots[spot].name.Substring(4)}   [ ] = prev / next spot");
    }
}
