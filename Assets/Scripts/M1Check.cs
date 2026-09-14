using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

// 배포물 검사. exe 를 -check 로 띄우면 돌고, 로그에 "CHECK PASS|FAIL 이름 값" 을 쓰고 종료 코드로 알린다.
// 입력은 가상 키보드·마우스 장치로 넣는다 — Player·Pickaxe 는 사람 장치와 같은 길(Keyboard.current / Mouse.current)로 읽는다.
// -only m1|mining 은 그 구간만 돈다 (고치는 중에는 바뀐 구간만, 커밋 전에는 전체).
// -sabotage floor|lamp|fog|thickfog|nodim|bury|onehit|spam|nomagnet|noassist|noviewmodel|picklamp|mute 는 검사가 FAIL 을 내는지 확인하는 용도다.
// -sweep 은 검사 대신 가까운 면 감광 값을 바꿔 가며 갱도·벽 앞 화면 값을 "SWEEP" 줄로 남긴다.
public class M1Check : MonoBehaviour
{
    public Player player;
    public Headlamp lamp;
    public Volume volume;
    public Transform pieces;
    public Pickaxe pickaxe;

    const float MinFps = 60f;
    // Godot 골든 캡처 play_09_lamp.png(직선 갱도, 램프 켬) 화면 평균 밝기. 같은 계산(sRGB 휘도 평균)으로 잰 참고값
    const float GodotLum = 0.063f;
    const float BurntLum = 0.85f;                 // 이 밝기 위 픽셀 = 하얗게 탄 픽셀
    // 벽 앞 화면에서 탄 픽셀 비율 상한. 실측(09-14 -sweep, 램프 75.2): 감광 없음 45 % · ref 2 = 9.4 % · pow 1.0 = 7.0 % · ref 3 = 2.8 % · ref 4 pow 1.4 = 1.3 %
    const float MaxBurntNearWall = 0.05f;
    const float MaxBurntPick = 0.05f;             // 곡괭이 화면 영역의 탄 픽셀 비율 상한
    static readonly Vector3 NearWallPos = new Vector3(2.75f, 0.1f, 15.75f);   // 오른쪽 벽에 몸이 닿는 자리, 기둥 사이
    static readonly Vector3 MidTunnel = new Vector3(0f, 1.9f, 17.5f);
    readonly List<string> fails = new List<string>();
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
        Debug.Log($"CHECK start sabotage='{sabotage}' only='{only}' sweep={sweep} screen {Screen.width}x{Screen.height}");
        StartCoroutine(sweep ? Sweep() : Run(fog));
    }

    IEnumerator Run(VolumetricFogVolumeComponent fog)
    {
        var cc = player.GetComponent<CharacterController>();
        yield return new WaitForSeconds(1.5f);   // 바닥에 내려앉는다
        if (only == "" || only == "m1")
            yield return M1(cc, fog);
        if (only == "" || only == "mining")
            yield return Mining(cc);
        Finish();
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

    void StandAt(CharacterController cc, OrePocket pk)
    {
        Vector3 at = pk.transform.position + pk.outDir * 1.8f;
        at.y = 0.1f;
        Teleport(cc, at, Quaternion.LookRotation(-pk.outDir).eulerAngles.y);
    }

    // 값 고르기용 측정: 가까운 면 감광(기준 거리·지수)마다 갱도(z 17.5, +Z)와 벽 앞 화면. 판정이 아니라 숫자 표를 남긴다
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

    void Finish()
    {
        string summary = fails.Count == 0 ? "CHECK ALL PASS" : "CHECK FAILED: " + string.Join(", ", fails);
        Debug.Log(summary);
        Application.Quit(fails.Count == 0 ? 0 : 1);
    }

    void Check(string name, bool ok, string value)
    {
        Debug.Log($"CHECK {(ok ? "PASS" : "FAIL")} {name} {value}");
        if (!ok) fails.Add(name);
    }

    static float Flat(Vector3 v) => new Vector2(v.x, v.z).magnitude;

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
    IEnumerator Capture(string name, Action<Vector3> result, Rect region = default)
    {
        yield return new WaitForSeconds(0.6f);        // 램프 페이드·안개 누적·램프 늦게 따라오기가 끝나게
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
        int n = 0, burnt = 0;
        for (int y = y0; y < y1; y += 3)
            for (int x = x0; x < x1; x += 3)
            {
                float l = Lum(px[y * w + x]);
                sum += l;
                n++;
                if (l > BurntLum) burnt++;
                grad += Mathf.Abs(Lum(px[y * w + x + 1]) - l) + Mathf.Abs(Lum(px[(y + 1) * w + x]) - l);
            }
        n = Mathf.Max(n, 1);
        result(new Vector3((float)(sum / n), (float)(grad / n * 1000.0), (float)burnt / n));
    }

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
