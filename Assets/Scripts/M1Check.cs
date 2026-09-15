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
// -only m1|mining|stalker|chase|retreat 은 그 구간만 돈다 (고치는 중에는 바뀐 구간만, 커밋 전에는 전체).
// -sabotage floor|lamp|fog|thickfog|nodim|bury|onehit|spam|nomagnet|noassist|noviewmodel|picklamp|mute|deaf|bigears|ghost|blind|slowchase|nolose|noadapt|dimeyes|tank|noretreat|softretreat 는 검사가 FAIL 을 내는지 확인하는 용도다.
// -sweep 은 검사 대신 가까운 면 감광 값을 바꿔 가며 갱도·벽 앞 화면 값을 "SWEEP" 줄로 남긴다.
public class M1Check : MonoBehaviour
{
    public Player player;
    public Headlamp lamp;
    public Volume volume;
    public Transform pieces;
    public Pickaxe pickaxe;
    public Stalker stalker;

    const float MinFps = 60f;
    // Godot 골든 캡처 play_09_lamp.png(직선 갱도, 램프 켬) 화면 평균 밝기. 같은 계산(sRGB 휘도 평균)으로 잰 참고값
    const float GodotLum = 0.063f;
    const float BurntLum = 0.85f;                 // 이 밝기 위 픽셀 = 하얗게 탄 픽셀
    // 벽 앞 화면에서 탄 픽셀 비율 상한. 실측(09-14 -sweep, 램프 75.2): 감광 없음 45 % · ref 2 = 9.4 % · pow 1.0 = 7.0 % · ref 3 = 2.8 % · ref 4 pow 1.4 = 1.3 %
    const float MaxBurntNearWall = 0.05f;
    const float MaxBurntPick = 0.05f;             // 곡괭이 화면 영역의 탄 픽셀 비율 상한
    // 램프 안 괴물 캡슐 영역의 평균 밝기 하한 (사용자 09-15 "절대 보이지 않는다"). 갱도 바탕 0.05. 램프 사거리 14 m 라 13 m 는 0.01 이 맞다.
    // 실측(09-15): 검정 재질(0.12) 3 m 0.159 · 7 m 0.055 = 바탕과 같음 → 회갈색(0.40) 3 m 0.303 · 7 m 0.127. 안 그리면(ghost) 0.077 · 0.009
    const float MinStalkerLum3m = 0.20f;
    const float MinStalkerLum7m = 0.09f;
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
        if (sabotage == "deaf")                 // 귀 ×0.4 = 곡괭이 소음 10 m — 20 m 에서 못 듣는다
            stalker.earMul = 0.4f;
        if (sabotage == "bigears")              // 귀 ×2 = 50 m — 30 m 밖에서도 온다
            stalker.earMul = 2f;
        if (sabotage == "ghost")                // 괴물 몸을 안 그린다 — 보임 검사가 잡는지
            foreach (var r in stalker.GetComponentsInChildren<Renderer>()) r.enabled = false;
        if (sabotage == "blind")                // 눈 0 m — 램프를 봐도 모른다
            stalker.eyeM = 0f;
        if (sabotage == "slowchase")            // 추격 3.0 m/s — 걷는 사람도 못 잡는다
            stalker.chaseSpeed = 3f;
        if (sabotage == "nolose")               // 못 봐도 안 놓는다
            stalker.loseS = 99f;
        if (sabotage == "tank")                 // 곡괭이가 안 먹힌다
            stalker.dmgMul = 0f;
        if (sabotage == "noretreat")            // 철수선 없음 — 체력이 0 까지 간다
            stalker.retreatHp = -1f;
        if (sabotage == "softretreat")          // 철수 중에도 깎인다
            stalker.retreatArmor = false;
        if (sabotage == "noadapt")              // 눈 적응 없음 — 램프 끄면 검은 화면 그대로
            lamp.darkAdaptAmbient = Tuning.AMBIENT_ENERGY;
        if (sabotage == "dimeyes")              // 괴물 눈 발광 끔
            foreach (var r in stalker.GetComponentsInChildren<Renderer>())
                if (r.name.StartsWith("Eye")) r.material.color = Color.black;
        Debug.Log($"CHECK start sabotage='{sabotage}' only='{only}' sweep={sweep} screen {Screen.width}x{Screen.height}");
        StartCoroutine(sweep ? Sweep() : Run(fog));
    }

    IEnumerator Run(VolumetricFogVolumeComponent fog)
    {
        var cc = player.GetComponent<CharacterController>();
        stalker.enabled = false;                 // 괴물 무관 구간은 괴물을 끈다 (DevHud 0 키와 같다) — 켜 두면 램프 빛을 보고 와서 잡는다
        yield return new WaitForSeconds(1.5f);   // 바닥에 내려앉는다
        if (only == "" || only == "m1")
            yield return M1(cc, fog);
        if (only == "" || only == "mining")
            yield return Mining(cc);
        stalker.enabled = true;
        if (only == "" || only == "stalker")
            yield return StalkerStage(cc);
        if (only == "" || only == "chase")
            yield return ChaseStage(cc);
        if (only == "" || only == "retreat")
            yield return RetreatStage(cc);
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

    // M5: 체력·스턴·철수. 플레이어를 괴물 앞 2.2 m(사거리 3 m 안)에 세우고 한 번 클릭 = 한 대. 괴물은 매번 z 20 에 북쪽을 보고 선다
    IEnumerator RetreatStage(CharacterController cc)
    {
        var st = stalker;
        var mouse = InputSystem.AddDevice<Mouse>("RetreatMouse");
        lamp.lampOn = true;
        Vector3 S = new Vector3(0f, 0.1f, 20f);
        Vector3 fwd = Vector3.forward;
        Vector3 P = S - fwd * 2.2f;                                   // 남쪽 2.2 m 에서 북쪽(괴물)을 본다
        var bodyT = st.transform.Find("Body");
        float t;

        // ① 1대: 체력 75, 1.5 s 멈춤(0.7 서서 + 0.8 뒷걸음 1.6 m), 끝나면 추격
        st.Teleport(S, 180f);
        st.hp = Tuning.STALKER_HP;
        Teleport(cc, P, 0f);
        player.frozen = false;
        yield return null;
        float hp0 = st.hp;
        yield return Click(mouse);
        t = 0f;
        while (st.state != Stalker.State.Stun && t < 1f) { t += Time.deltaTime; yield return null; }
        yield return null;                                             // 납작해진 몸이 한 프레임 뒤에 보인다
        float hp1 = st.hp;
        float squash = bodyT != null ? bodyT.localScale.y : -1f;
        Vector3 at = st.transform.position;
        float stunT = 0f;
        while (st.state == Stalker.State.Stun && stunT < 3f) { stunT += Time.deltaTime; yield return null; }
        float back = Flat(st.transform.position - at);
        Check("hit_damages_and_stuns", hp0 == Tuning.STALKER_HP && hp1 == hp0 - Tuning.STALKER_HIT_DMG && stunT > 1.3f && stunT < 1.8f && back > 1.0f && back < 2.2f && st.state == Stalker.State.Chase && squash < bodyT.localScale.y,
            $"hp {hp0:0} → {hp1:0}, stun {stunT:F2} s, backed {back:F2} m, then {st.state}, squash y {squash:F2}→{bodyT.localScale.y:F2}");

        // ② 2대째·3대째: 체력 50 → 25, 세 번째 멈춤이 끝나면 즉시 철수
        for (int i = 0; i < 2; i++)
        {
            st.Teleport(S, 180f);                                        // 자리만 되돌린다 — 체력은 그대로 (Teleport 는 hp 를 안 건드린다)
            Teleport(cc, P, 0f);
            player.frozen = false;                                       // 스턴 끝에 추격 → 잡힘이 한 프레임에 끼어들 수 있다
            yield return null;
            yield return Click(mouse);
            t = 0f;
            while (st.state != Stalker.State.Stun && t < 1f) { t += Time.deltaTime; yield return null; }
            if (i == 0) { while (st.state == Stalker.State.Stun) yield return null; }
        }
        float hp3 = st.hp;
        Vector3 retreatFrom = player.transform.position;
        while (st.state == Stalker.State.Stun) yield return null;
        yield return null;
        Check("third_hit_retreats_at_once", hp3 == Tuning.STALKER_HP - 3f * Tuning.STALKER_HIT_DMG && hp3 <= Tuning.STALKER_RETREAT_HP && st.state == Stalker.State.Retreat,
            $"hp after 3 hits {hp3:0} (retreat line {Tuning.STALKER_RETREAT_HP}), state {st.state}");

        // ③ 철수 중 1대: 체력 그대로, 1.5 s 멈춘 뒤 철수 계속. 길 앞 1.5 m 에 서서 치고 바로 비킨다
        Vector3 dir = Flat3(st.retreatSpot - st.transform.position).normalized;
        Teleport(cc, st.transform.position + dir * 1.5f, Quaternion.LookRotation(-dir).eulerAngles.y);
        yield return null;
        yield return Click(mouse);
        t = 0f;
        while (st.state != Stalker.State.Stun && t < 1f) { t += Time.deltaTime; yield return null; }
        bool stunned = st.state == Stalker.State.Stun;
        Teleport(cc, retreatFrom, 0f);
        while (st.state == Stalker.State.Stun) yield return null;
        yield return null;
        Check("retreat_hits_only_stun", stunned && st.hp == hp3 && st.state == Stalker.State.Retreat, $"stunned {stunned}, hp {st.hp:0} (was {hp3:0}), then {st.state}");

        // ④ 철수 자리: 플레이어에서 8~14 m, 램프 원뿔(60°) 안. 7 m 를 벗어난 뒤 다시 안 들어온다 (#16)
        float minAfter = 99f;
        bool left = false;
        t = 0f;
        while (st.state == Stalker.State.Retreat && t < 10f)
        {
            float d = Flat(st.transform.position - retreatFrom);
            if (d > Tuning.GRID_CELL) left = true;
            else if (left) minAfter = Mathf.Min(minAfter, d);
            t += Time.deltaTime;
            yield return null;
        }
        float spotD = Flat(st.retreatSpot - st.retreatFrom);
        float spotAng = Vector3.Angle(Flat3(st.retreatFwd), Flat3(st.retreatSpot - st.retreatFrom));
        Check("retreat_spot_in_lamp_cone_8_14m", st.state == Stalker.State.Climb && spotD >= Tuning.STALKER_RETREAT_MIN_M - 0.5f && spotD <= Tuning.STALKER_RETREAT_MAX_M + 0.5f && spotAng <= Tuning.LAMP_ANGLE_DEG && st.retreatInCone && minAfter > Tuning.GRID_CELL,
            $"spot {spotD:F1} m at {spotAng:F0}° (cone ±{Tuning.LAMP_ANGLE_DEG}), inCone {st.retreatInCone}, re-entered 7 m: {(minAfter <= Tuning.GRID_CELL ? "yes " + minAfter.ToString("F1") : "no")}, state {st.state} after {t:F1} s");

        // ⑤ 벽타기 3~5 s 뒤 사라진다, 숨은 시간은 90 s 로 시작
        float y0 = st.transform.position.y;
        t = 0f;
        while (st.state == Stalker.State.Climb && t < 8f) { t += Time.deltaTime; yield return null; }
        bool shown = false;
        foreach (var r in st.GetComponentsInChildren<Renderer>()) shown |= r.enabled;
        Check("climbs_wall_then_vanishes", st.state == Stalker.State.Hidden && t > 3f && t < 5f && !shown && Mathf.Abs(st.hiddenLeft - Tuning.STALKER_REGEN_S) < 1f,
            $"climb {t:F1} s from y {y0:F1}, state {st.state}, visible {shown}, hidden {st.hiddenLeft:0} s (STALKER_REGEN_S {Tuning.STALKER_REGEN_S})");

        // ⑥ 재등장: 숨은 시간만 2 s 로 줄인다(값만 바꿈). 체력 100, 플레이어에서 먼 틈, 배회. 램프는 꺼서 나오자마자 빛을 보고 움직이지 않게
        lamp.lampOn = false;
        st.hiddenLeft = 2f;
        t = 0f;
        while (st.state == Stalker.State.Hidden && t < 5f) { t += Time.deltaTime; yield return null; }
        shown = true;
        foreach (var r in st.GetComponentsInChildren<Renderer>()) shown &= r.enabled;
        float far = 0f;
        foreach (var c in st.cracks) far = Mathf.Max(far, Flat(c - player.transform.position));
        float d2 = Flat(st.transform.position - player.transform.position);
        Check("reappears_at_far_crack_full_hp", st.state == Stalker.State.Wander && st.hp == Tuning.STALKER_HP && shown && d2 > 15f && Mathf.Abs(d2 - far) < 1.5f,
            $"state {st.state}, hp {st.hp:0}, visible {shown}, {d2:F1} m from player (far crack {far:F1} m)");
        lamp.lampOn = true;
    }

    // M4: 눈·빛·추격·잡기. 플레이어는 z 10 에서 +Z 를 본다. 괴물은 앞(+Z)이나 뒤(-Z)에 놓고 플레이어 쪽을 보게 한다
    IEnumerator ChaseStage(CharacterController cc)
    {
        var st = stalker;
        var kb = InputSystem.AddDevice<Keyboard>("ChaseKeyboard");
        Vector3 P = new Vector3(0f, 0.1f, 10f);
        Vector3 fwd = Vector3.forward;
        float t;

        // ① 램프 켜고 8 m 앞 → alert. ② alert → chase 1.0 s
        lamp.lampOn = true;
        Teleport(cc, P, 0f);
        st.Teleport(P + fwd * 8f, 180f);
        t = 0f;
        while (st.state != Stalker.State.Alert && t < 2f) { t += Time.deltaTime; yield return null; }
        float tAlert = t;
        Check("stalker_sees_lamp_in_12m", st.state == Stalker.State.Alert && tAlert < 1f, $"alert after {tAlert:F2} s, sense {st.sense}, state {st.state}");
        t = 0f;
        while (st.state == Stalker.State.Alert && t < 3f) { t += Time.deltaTime; yield return null; }
        Check("alert_1s_before_chase", st.state == Stalker.State.Chase && t > 0.9f && t < 1.3f, $"chase after {t:F2} s (STALKER_ALERT_S {Tuning.STALKER_ALERT_S})");
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));

        // ③ 램프 끄고 같은 자리 → 모른다
        lamp.lampOn = false;
        yield return new WaitForSeconds(Tuning.LAMP_TOGGLE_TIME + 0.1f);
        st.Teleport(P + fwd * 8f, 180f);
        yield return new WaitForSeconds(2f);
        Check("stalker_blind_when_lamp_off", st.state != Stalker.State.Alert && st.state != Stalker.State.Chase && st.sense == "-", $"state {st.state}, sense {st.sense}");

        // ④ 램프 켜고 20 m → 빛. 2 s 에 배회 속도(2.5)로 4~6 m 다가온다
        lamp.lampOn = true;
        Vector3 from = P + fwd * 20f;
        st.Teleport(from, 180f);
        yield return new WaitForSeconds(2f);
        float moved = Flat(from - st.transform.position);
        Check("stalker_light_30m_slow_approach", st.state == Stalker.State.Investigate && moved > 3.5f && moved < 6.5f, $"moved {moved:F1} m in 2 s, state {st.state}, sense {st.sense}");
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));

        // ⑤ 5 m 뒤에서 걷는 플레이어를 7 s 안에 잡는다. ⑥ 검은 화면 → 3.0 s 뒤 복도 시작점 · 광석 0 · 괴물 북쪽 끝
        Teleport(cc, P, 0f);
        player.ore = 3;
        st.Teleport(P - fwd * 5f, 0f);
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W));
        int c0 = st.catches;
        t = 0f;
        while (st.catches == c0 && t < 8f) { t += Time.deltaTime; yield return null; }
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        float tCatch = t;
        Check("chase_catches_walker", st.catches == c0 + 1 && tCatch < 7f, $"caught after {tCatch:F1} s, state {st.state}");
        Vector3 blackV = default;
        yield return Capture("13_caught_black", v => blackV = v);      // 0.6 s 뒤 = 검은 화면 안
        int r0 = st.restarts;
        t = 0.6f;
        while (st.restarts == r0 && t < 5f) { t += Time.deltaTime; yield return null; }
        yield return null;
        float toStart = Flat(player.transform.position - st.restartPos);
        Check("catch_black_then_restart_3s", blackV.x < 0.02f && st.restarts == r0 + 1 && t > 2.7f && t < 3.4f && toStart < 0.5f && player.ore == 0 && !player.frozen && st.transform.position.z > st.zMax - 5f,
            $"black lum {blackV.x:F3}, restart at {t:F1} s, {toStart:F2} m from start, ore {player.ore}, frozen {player.frozen}, stalker z {st.transform.position.z:F1}");
        yield return new WaitForSeconds(Tuning.CATCH_FADE_OUT_S);

        // ⑦ 5 m 뒤에서 달리는 플레이어는 4 s 동안 안 잡힌다
        Teleport(cc, new Vector3(0f, 0.1f, 4f), 0f);
        player.stamina = Tuning.STAMINA_MAX;
        st.Teleport(new Vector3(0f, 0.1f, -1f), 0f);
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W, Key.LeftShift));
        c0 = st.catches;
        bool chased = false;
        for (t = 0f; t < 4f && st.catches == c0; t += Time.deltaTime) { chased |= st.state == Stalker.State.Chase; yield return null; }
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        Check("runner_escapes_4s", st.catches == c0 && chased, $"caught {st.catches != c0}, chased {chased}, gap {st.DistToPlayer:F1} m at 4 s");
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));

        // ⑧ 추격 중 램프 끄고 뒤로 빠지면 3.0 s 에 놓고, 마지막 본 자리로 가서 수색
        Teleport(cc, P, 0f);
        st.Teleport(P + fwd * 8f, 180f);
        t = 0f;
        while (st.state != Stalker.State.Chase && t < 3f) { t += Time.deltaTime; yield return null; }
        lamp.lampOn = false;
        Teleport(cc, P - fwd * 12f, 0f);
        t = 0f;
        while (st.state == Stalker.State.Chase && t < 5f) { t += Time.deltaTime; yield return null; }
        float tLose = t;
        while (st.state != Stalker.State.Search && t < 10f) { t += Time.deltaTime; yield return null; }
        float toLast = Flat(st.transform.position - P);
        Check("stalker_loses_after_3s", tLose > 2.7f && tLose < 3.6f && st.state == Stalker.State.Search && toLast < 3f, $"left chase at {tLose:F1} s, searching {toLast:F1} m from last seen, state {st.state}");
        lamp.lampOn = true;

        // ⑨ 어둠 적응 (사용자 09-15 "램프를 끄면 아무것도 안 보인다" → A, 값 6.4 는 사용자가 1/2 키로 찾음). 괴물은 끄고 북쪽 끝에 세운다 — 배회하며 화면에 들어오면 밝기가 2.5배 흔들렸다.
        // 램프는 0.2 s 켜서 적응을 풀고 끈다 (한 프레임만 켜면 안 풀렸다, 09-15)
        st.enabled = false;
        st.Teleport(st.homePos);
        Teleport(cc, P, 0f);
        lamp.lampOn = true;
        yield return new WaitForSeconds(0.2f);
        lamp.lampOn = false;
        Vector3 dark0 = default, adapted = default;
        yield return Capture("15_dark_0s", x => dark0 = x);
        float adapt0 = lamp.adapt;
        yield return new WaitForSeconds(Tuning.DARK_ADAPT_TIME);
        yield return Capture("15_dark_adapted", x => adapted = x);
        float fogNow = RenderSettings.fogDensity;
        Check("dark_adapt_shapes_visible", adapt0 < 0.3f && lamp.adapt >= 1f && adapted.x > dark0.x * 3f && adapted.x > 0.006f && adapted.x < 0.05f && Mathf.Abs(fogNow - Tuning.DARK_ADAPT_FOG) < 0.01f,
            $"lum off 0.6 s {dark0.x:F4} (adapt {adapt0:F2}) → adapted {adapted.x:F4} (6.4 → 0.012, allow 0.006~0.05; noadapt 0.0002), fog {fogNow:F2} (DARK_ADAPT_FOG {Tuning.DARK_ADAPT_FOG})");
        lamp.lampOn = true;
        yield return null;
        yield return null;
        Check("lamp_on_resets_adapt", lamp.adapt == 0f && Mathf.Abs(RenderSettings.fogDensity - Tuning.FOG_DENSITY) < 1e-4f, $"adapt {lamp.adapt:F2}, fog {RenderSettings.fogDensity:F3}");

        // ⑩ 괴물 눈 발광 (C): 램프 끄고 5 m 앞에 세운(꺼 둔) 괴물의 눈 영역 밝기
        yield return new WaitForSeconds(0.2f);
        lamp.lampOn = false;
        st.Teleport(P + fwd * 5f, 180f);
        var eyeR = new List<Renderer>();
        foreach (var r in st.GetComponentsInChildren<Renderer>()) if (r.name.StartsWith("Eye")) eyeR.Add(r);
        var camMain = pickaxe.cam.GetComponent<Camera>();
        Vector3 eyes = default;
        Rect eyeRect = ScreenRect(camMain, eyeR.ToArray());
        yield return Capture("16_eyes_in_dark", x => eyes = x, eyeRect);
        Check("stalker_eyes_glow_in_dark", eyeRect.width > 0f && eyes.x > 0.05f, $"eye region lum {eyes.x:F3} in {eyeRect.width:F0}x{eyeRect.height:F0} px at 5 m, lamp off, adapt {lamp.adapt:F2}");
        lamp.lampOn = true;
        st.enabled = true;
    }

    // M3: 소음을 듣는 괴물. 포켓은 안 캐지게(health 1e6) 두고 소음만 낸다. 괴물 자리는 소리를 내기 직전에 놓는다 — 그 순간의 거리가 기준이다
    IEnumerator StalkerStage(CharacterController cc)
    {
        var st = stalker;
        var pockets = new List<OrePocket>(FindObjectsByType<OrePocket>(FindObjectsSortMode.None));
        pockets.Sort((a, b) => a.transform.position.z.CompareTo(b.transform.position.z));
        OrePocket south = pockets[0];
        OrePocket mid = pockets.Find(pk => pk.transform.position.z > 12f && pk.transform.position.z < 20f) ?? pockets[pockets.Count / 2];
        foreach (var pk in pockets) pk.health = 1e6f;
        var mouse = InputSystem.AddDevice<Mouse>("StalkerMouse");
        lamp.lampOn = true;

        // 0. 보이는가 (사용자 09-15 "절대 보이지 않는다"). 갱도 가운데서 앞 3·7·13 m 에 세우고 캡슐 화면 영역 밝기를 잰다
        var mainCam = pickaxe.cam.GetComponent<Camera>();
        var bodyR = st.GetComponentsInChildren<Renderer>();
        Teleport(cc, new Vector3(0f, 0.1f, 3.5f), 0f);
        var vis = new Dictionary<float, Vector3>();
        float minRect = 1e9f;
        foreach (float dist in new[] { 3f, 7f, 13f })
        {
            st.Teleport(new Vector3(0f, 0.1f, 3.5f + dist));   // 놓인 뒤 1 s 는 서 있다 (STALKER_WANDER_PAUSE_S)
            Rect r = default;
            Vector3 v = default;
            yield return Capture($"12_stalker_at_{dist:0}m", x => v = x, default, () => r = ScreenRect(mainCam, bodyR));
            vis[dist] = v;
            minRect = Mathf.Min(minRect, r.width);
            Debug.Log($"STALKER_VIS {dist:0} m lum {v.x:F4} burnt {v.z * 100f:F1} % rect {r.width:F0}x{r.height:F0}");
        }
        Check("stalker_visible_in_lamp", minRect > 0f && vis[3f].x > MinStalkerLum3m && vis[7f].x > MinStalkerLum7m, $"lum 3 m {vis[3f].x:F3} (min {MinStalkerLum3m}) · 7 m {vis[7f].x:F3} (min {MinStalkerLum7m}) · 13 m {vis[13f].x:F3} (램프 14 m 밖은 안 보이는 게 맞다)");
        lamp.lampOn = false;                       // 귀 검사는 램프를 끄고 — M4 눈·빛이 끼어들지 않게 (램프 끄면 소리만 남는 것이 규칙이다)
        yield return new WaitForSeconds(Tuning.LAMP_TOGGLE_TIME + 0.1f);

        // 1. 30 m 밖 1타 → 안 듣는다
        StandAt(cc, south);
        st.Teleport(new Vector3(0f, 0.1f, st.zMax));
        yield return null;
        float d0 = Flat(south.transform.position - st.transform.position);
        yield return Click(mouse);
        yield return new WaitForSeconds(2f);
        Check("stalker_ignores_beyond_25m", d0 > 30f && st.hits == 0 && st.state == Stalker.State.Wander, $"noise at {d0:F1} m, hits {st.hits}, state {st.state}");

        // 2. 20 m 안 1타 → 소리 쪽으로 한 칸(7 m)만 다가와 멈춘다
        StandAt(cc, mid);
        Vector3 from = new Vector3(0f, 0.1f, Mathf.Min(mid.transform.position.z + 20f, st.zMax));
        st.Teleport(from);
        yield return null;
        yield return Click(mouse);
        yield return new WaitForSeconds(3f);      // 7 m ÷ 4.0 = 1.75 s
        float moved = Flat(st.transform.position - from);
        float toPocket = Flat(mid.transform.position - st.transform.position);
        Check("stalker_one_hit_approaches_7m", st.hits == 1 && moved > 5f && moved < 9f && toPocket > 5f && st.state == Stalker.State.Search,
            $"moved {moved:F1} m, {toPocket:F1} m from pocket, state {st.state}");

        // 3. 20 m 안 2타 연속 → 그 자리(2 m 안)까지 온다
        yield return new WaitForSeconds(Tuning.STALKER_HEAR_CONFIRM_S);   // 앞 소리와 이어지지 않게
        st.Teleport(from);
        yield return null;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(Tuning.MINE_COOLDOWN * 1.6f);      // 2타
        InputSystem.QueueStateEvent(mouse, new MouseState());
        // 길을 비켜 남쪽 4 m 에서 포켓 쪽을 본다 — 괴물이 플레이어 몸에 막히지 않게, 오는 장면을 찍는다
        Teleport(cc, new Vector3(-Mathf.Sign(mid.transform.position.x) * 1.0f, 0.1f, mid.transform.position.z - 4f), 0f);
        float t = 0f;
        while (st.state != Stalker.State.Search && t < 8f) { t += Time.deltaTime; yield return null; }
        toPocket = Flat(mid.transform.position - st.transform.position);
        Check("stalker_two_hits_arrives_2m", st.hits == 2 && st.state == Stalker.State.Search && toPocket < Tuning.STALKER_FOUND_M && t < 6f,
            $"hits {st.hits}, {toPocket:F2} m from pocket after {t:F1} s, state {st.state}");
        Teleport(cc, new Vector3(0f, 0.1f, st.zMin + 1f), 0f);    // 수색 길에서 비킨다

        // 4. 2~3곳을 2 s 씩 들여다본 뒤 배회로 돌아간다. 수색 곳이 우연히 플레이어 2 m 안이면 들키는 게(found) 규칙이라 그것도 통과로 친다
        t = 0f;
        bool found = false;
        while (st.state == Stalker.State.Search && t < 40f) { t += Time.deltaTime; found |= st.sense == "found"; yield return null; }
        Check("stalker_searches_2to3_spots_then_wanders", found || (st.state == Stalker.State.Wander && st.spotsVisited >= Tuning.STALKER_SPOTS_MIN && st.spotsVisited <= Tuning.STALKER_SPOTS_MAX),
            $"spots {st.spotsVisited}, state {st.state} after {t:F1} s{(found ? ", found player within 2 m" : "")}");

        // 5. 도착 장면 캡처 (램프 켜고) — 2타로 다시 부른 뒤 4 m 남쪽에서 본다
        StandAt(cc, mid);
        st.Teleport(from);
        yield return null;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(Tuning.MINE_COOLDOWN * 1.6f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
        Teleport(cc, new Vector3(-Mathf.Sign(mid.transform.position.x) * 1.0f, 0.1f, mid.transform.position.z - 4f), 0f);
        t = 0f;
        while (st.state != Stalker.State.Search && t < 8f) { t += Time.deltaTime; yield return null; }
        lamp.lampOn = true;
        yield return Capture("11_stalker_arrived", v => { });
    }

    IEnumerator Click(Mouse mouse)
    {
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        yield return new WaitForSeconds(0.05f);
        InputSystem.QueueStateEvent(mouse, new MouseState());
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
    static Vector3 Flat3(Vector3 v) => new Vector3(v.x, 0f, v.z);

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
    // regionAt 은 찍는 순간에 영역을 다시 잰다 — 움직이는 것(괴물)은 0.6 s 기다리는 동안 자리가 바뀐다
    IEnumerator Capture(string name, Action<Vector3> result, Rect region = default, Func<Rect> regionAt = null)
    {
        yield return new WaitForSeconds(0.6f);        // 램프 페이드·안개 누적·램프 늦게 따라오기가 끝나게
        if (regionAt != null) region = regionAt();
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
