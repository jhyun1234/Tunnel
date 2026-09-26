using System.Collections.Generic;
using UnityEngine;

// REP-1 고칠 곳 하나 (제안서 docs/제안서_REP1_고칠_곳.md, 승인 09-26). 자리는 씬 생성기(BuildM1)가 부스 맵의 SLOT_Repair_<종류>_<i> 에 놓는다.
// 망가진 곳 앞에서 E 를 누르고 있으면 고친다(Player) — 손을 떼도 진행이 남는다. 고치는 동안 REP_NOISE_EVERY 마다 종류 반경으로 소음.
// 모습: Broken / Fixed 두 무리를 켜고 끈다 (자리표시 모양 — 모델·손 동작은 3D-P 뒤). 전등은 전구 재질 + 빛.
public class Repairable : MonoBehaviour
{
    public static readonly List<Repairable> All = new List<Repairable>();
    public static float timeMul = 1f;          // DevHud F3 F4 · 사보타주 instantfix(0)
    public static float noiseMul = 1f;         // 사보타주 silentfix(0)
    public static int FixedCount;              // 검사

    public string kind;                        // timber rail drain vent panel hose lamp
    public Vector3 focus;                      // 고칠 물건 자리 (바라보고 다가가는 곳)
    public Vector3 standAt;                    // 검사: 이 앞에 서는 자리 (바닥)
    public GameObject brokenLook, fixedLook;
    public Transform flap;                     // 망가진 동안 흔들리는 조각 (풍관 찢어진 천 · 풀린 호스 끝)
    public Renderer bulb;                      // 전등
    public Material bulbOn, bulbOff;
    public Light lampLight;

    [System.NonSerialized] public bool broken;
    [System.NonSerialized] public float progress;      // 0~1 — 떼도 남는다
    float noiseT;

    public float FixTime => Tuning.RepairTime(kind) * timeMul;
    public float Radius => Tuning.RepairNoise(kind) * noiseMul;
    public float Value => Tuning.ORE_VALUE * Tuning.RepairTime(kind) / Tuning.MINE_TIME_REF / Tuning.ORE_OVER_REPAIR;

    void OnEnable() => All.Add(this);
    void OnDisable() => All.Remove(this);

    public void Break() { broken = true; progress = 0f; noiseT = 0f; Apply(); }
    public void SetFixed() { broken = false; progress = 0f; Apply(); }

    // 한 프레임 고친다 (Player 가 E 를 누르고 있는 동안). 다 고친 프레임에 true
    public bool Work(float dt, object who)
    {
        if (!broken) return false;
        float t = FixTime;
        progress = t <= 0f ? 1f : Mathf.Min(1f, progress + dt / t);
        noiseT -= dt;
        if (noiseT <= 0f)
        {
            noiseT = Tuning.REP_NOISE_EVERY;
            NoiseBus.Make(focus, (kind == "panel" ? Tuning.REP_NOISE_PANEL_WORK : Tuning.RepairNoise(kind)) * noiseMul, "repair", who);
        }
        if (progress < 1f) return false;
        broken = false;
        progress = 0f;
        FixedCount++;
        Economy.AddRepair(Value);
        if (kind == "panel") NoiseBus.Make(focus, Radius, "repair", who);   // 기계가 한꺼번에 켜지는 순간
        Apply();
        return true;
    }

    void Apply()
    {
        if (brokenLook != null) brokenLook.SetActive(broken);
        if (fixedLook != null) fixedLook.SetActive(!broken);
        if (bulb != null) bulb.sharedMaterial = broken ? bulbOff : bulbOn;
        if (lampLight != null) lampLight.enabled = !broken;
    }

    void Update()
    {
        if (broken && flap != null)
            flap.localRotation = Quaternion.Euler(Mathf.Sin(Time.time * 9f + focus.x) * 28f, 0f, Mathf.Sin(Time.time * 5.3f) * 10f);
    }

    // 바라보는 망가진 고칠 곳 (수평 거리 REP_REACH_M 안 · 방향 REP_LOOK_DEG 안 — 가장 가까운 것)
    public static Repairable Nearest(Vector3 body, Vector3 forward)
    {
        Vector3 f = new Vector3(forward.x, 0f, forward.z).normalized;
        Repairable best = null;
        float bestD = Tuning.REP_REACH_M;
        foreach (var r in All)
        {
            if (!r.broken) continue;
            Vector3 d = r.focus - body; d.y = 0f;
            float m = d.magnitude;
            if (m > bestD) continue;
            if (m > 0.3f && Vector3.Angle(f, d) > Tuning.REP_LOOK_DEG) continue;
            best = r; bestD = m;
        }
        return best;
    }
}
