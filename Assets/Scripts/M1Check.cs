using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.Rendering;

// 배포물 검사. exe 를 -check 로 띄우면 돌고, 로그에 "CHECK PASS|FAIL 이름 값" 을 쓰고 종료 코드로 알린다.
// 입력은 가상 키보드 장치로 넣는다 — Player 는 사람 키보드와 같은 길(Keyboard.current)로 읽는다.
// -sabotage floor|lamp|fog|thickfog 는 검사가 FAIL 을 내는지 확인하는 용도다.
// -sweep 은 검사 대신 램프 세기·안개 밀도·안개 품질을 바꿔 가며 밝기·구조·fps 를 "SWEEP" 줄로 남긴다.
public class M1Check : MonoBehaviour
{
    public Player player;
    public Headlamp lamp;
    public Volume volume;
    public Transform pieces;

    const float MinFps = 60f;
    // Godot 골든 캡처 play_09_lamp.png(직선 갱도, 램프 켬) 화면 평균 밝기. 같은 계산(sRGB 휘도 평균)으로 잰 참고값
    const float GodotLum = 0.063f;
    readonly List<string> fails = new List<string>();
    string outDir;

    void Start()
    {
        string[] args = Environment.GetCommandLineArgs();
        bool sweep = Array.IndexOf(args, "-sweep") >= 0;
        if (!sweep && Array.IndexOf(args, "-check") < 0)
        {
            enabled = false;
            return;
        }
        int s = Array.IndexOf(args, "-sabotage");
        string sabotage = s >= 0 && s + 1 < args.Length ? args[s + 1] : "";
        outDir = Path.Combine(Path.GetDirectoryName(Application.dataPath), "check");
        Directory.CreateDirectory(outDir);
        Application.runInBackground = true;     // 창이 포커스를 잃어도 멈추지 않게
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
        Debug.Log($"CHECK start sabotage='{sabotage}' sweep={sweep} screen {Screen.width}x{Screen.height}");
        StartCoroutine(sweep ? Sweep(fog) : Run(fog));
    }

    IEnumerator Run(VolumetricFogVolumeComponent fog)
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
        yield return new WaitForSeconds(1.5f);
        var cc = player.GetComponent<CharacterController>();
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
        // 사용자 지적(09-14 "+Z 쪽으로 램프 빛이 안 보인다") — 실측 +Z 0.022 / -Z 0.130
        Vector3 back = player.transform.position;
        Vector2 plusZ = default, minusZ = default;
        Teleport(cc, new Vector3(0f, 0.1f, 17.5f), 0f);
        yield return Capture("4_mid_plusZ", v => plusZ = v);
        Teleport(cc, new Vector3(0f, 0.1f, 17.5f), 180f);
        yield return Capture("5_mid_minusZ", v => minusZ = v);
        float sym = Mathf.Min(plusZ.x, minusZ.x) / Mathf.Max(Mathf.Max(plusZ.x, minusZ.x), 1e-5f);
        Check("lamp_symmetric_z", sym > 0.67f, $"+Z {plusZ.x:F4} -Z {minusZ.x:F4} (min/max {sym:F2})");
        Teleport(cc, back, 0f);

        // 6. 화면: 램프+안개 / 램프만 / 램프 끔. 밝기(lum)·구조(grad, 이웃 픽셀 차)·fps 는 사람이 보는 화면에서 잰다
        Vector2 fogShot = default, noFogShot = default, darkShot = default;
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

        Check("lamp_lights_screen", fogShot.x > 0.01f && fogShot.x > darkShot.x * 3f, $"on {fogShot.x:F4} off {darkShot.x:F4}");
        // 기준 화면이 거의 검으면 아래 안개 구조 비교가 뜻이 없다 — 첫 빌드(램프 35, 밝기 0.003)에서 망가진 안개가 PASS 했다.
        // 하한 0.008 = 사용자 판정 램프 146.8 의 실측(약 0.017)의 절반. Godot 비율은 참고로만 남긴다
        Check("lamp_not_black", noFogShot.x > 0.008f, $"nofog lum {noFogShot.x:F4} (Godot {GodotLum} 의 x{noFogShot.x / GodotLum:F2})");
        // 안개가 보여야 하고(밝기 +2 % 이상), 갱도 형태를 지우면 안 된다(구조 85 % 이상 남음 — 실측 0.012 는 70 % 로 끝이 흰 막이었다)
        Check("volfog_visible", fogShot.x > noFogShot.x * 1.02f, $"lum fog {fogShot.x:F4} nofog {noFogShot.x:F4}");
        Check("volfog_keeps_structure", fogShot.y >= noFogShot.y * 0.85f, $"grad fog {fogShot.y:F2} nofog {noFogShot.y:F2} ({fogShot.y / noFogShot.y * 100f:F0} %)");
        Check("fps_fog_min60", fpsFog >= MinFps, $"fog {fpsFog:F0} fps ({1000f / fpsFog:F2} ms) · nofog {fpsNoFog:F0} fps ({1000f / fpsNoFog:F2} ms) · {SystemInfo.graphicsDeviceName}");

        Finish();
    }

    // 값 고르기용 측정. 판정이 아니라 숫자 표를 남긴다
    IEnumerator Sweep(VolumetricFogVolumeComponent fog)
    {
        yield return new WaitForSeconds(1.5f);
        fog.enabled.value = false;
        float bestEnergy = lamp.energy, bestErr = float.MaxValue;
        foreach (float e in new[] { 35f, 70f, 140f, 280f, 560f, 1120f })
        {
            lamp.energy = e;
            Vector2 shot = default;
            yield return Capture($"sweep_lamp_{e:0}", v => shot = v);
            float err = Mathf.Abs(Mathf.Log(Mathf.Max(shot.x, 1e-5f) / GodotLum));
            if (err < bestErr) { bestErr = err; bestEnergy = e; }
            Debug.Log($"SWEEP lamp {e,6:0} nofog lum {shot.x:F4} grad {shot.y:F2}");
        }
        lamp.energy = bestEnergy;
        Vector2 baseShot = default;
        float baseFps = 0f;
        yield return Capture("sweep_base", v => baseShot = v);
        yield return MeasureFps(3f, v => baseFps = v);
        Debug.Log($"SWEEP base lamp {bestEnergy:0} nofog lum {baseShot.x:F4} grad {baseShot.y:F2} fps {baseFps:F0}");

        fog.enabled.value = true;
        foreach (float d in new[] { 0.012f, 0.006f, 0.003f, 0.0015f, 0.0007f, 0.0003f })
        {
            fog.density.value = d;
            Vector2 shot = default;
            float fps = 0f;
            yield return Capture($"sweep_fog_{d:0.0000}", v => shot = v);
            yield return MeasureFps(3f, v => fps = v);
            Debug.Log($"SWEEP fog {d:0.0000} lum {shot.x:F4} (x{shot.x / baseShot.x:F2}) grad {shot.y:F2} ({shot.y / baseShot.y * 100f:F0} %) fps {fps:F0} ({1000f / fps:F2} ms)");
        }
        fog.density.value = 0.0015f;
        foreach (int steps in new[] { 128, 64, 32, 16 })
            foreach (int blur in new[] { 2, 1 })
            {
                fog.maxSteps.value = steps;
                fog.blurIterations.value = blur;
                float fps = 0f;
                yield return new WaitForSeconds(0.3f);
                yield return MeasureFps(3f, v => fps = v);
                Debug.Log($"SWEEP quality steps {steps,3} blur {blur} fps {fps:F0} ({1000f / fps:F2} ms)");
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

    // x = 평균 밝기(sRGB 휘도 0~1), y = 구조(이웃 픽셀 밝기 차 평균 × 1000). 안개가 형태를 지우면 y 가 떨어진다
    IEnumerator Capture(string name, Action<Vector2> result)
    {
        yield return new WaitForSeconds(0.6f);        // 램프 페이드·안개 누적·램프 늦게 따라오기가 끝나게
        yield return new WaitForEndOfFrame();
        var tex = ScreenCapture.CaptureScreenshotAsTexture();
        File.WriteAllBytes(Path.Combine(outDir, name + ".png"), tex.EncodeToPNG());
        Color32[] px = tex.GetPixels32();
        int w = tex.width, h = tex.height;
        Destroy(tex);
        double sum = 0, grad = 0;
        int n = 0, g = 0;
        for (int y = 0; y < h - 1; y += 3)
            for (int x = 0; x < w - 1; x += 3)
            {
                float l = Lum(px[y * w + x]);
                sum += l;
                n++;
                grad += Mathf.Abs(Lum(px[y * w + x + 1]) - l) + Mathf.Abs(Lum(px[(y + 1) * w + x]) - l);
                g++;
            }
        result(new Vector2((float)(sum / n), (float)(grad / g * 1000.0)));
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
