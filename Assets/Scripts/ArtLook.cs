using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

// ART-1 현실감 시험 (docs/제안서_ART1_현실감_광장_시험.md): 부스 맵의 새 모습 ↔ 옛 모습.
// 새 모습 = 바위 재질 MineRock(무늬 되풀이 없음 · 석탄 띠 · 진흙 · 젖음) + 전등마다 튀는 빛 + 떠다니는 먼지 + 겹치는 화면 설정(필름 입자 · 빛 번짐 · 대비) + 광장 물건 · 굴 안 둥근 통나무 동발(차례 3).
// 판정 키: Insert 옛/새 · Home/End 젖음 −/+ · PageDown/PageUp 튀는 빛 −/+ · ← → (또는 숫자패드 4/6) 바위 밝기 ÷× 1.1 · Shift+Home/End 표지판 바탕 ÷× 1.25. 받은 숫자는 Tuning.ART_* · SIGN_BOARD_BRIGHT 에. 씬은 BuildM1.PlaceArt 가 만든다.
public class ArtLook : MonoBehaviour
{
    public Renderer[] renderers;                  // 부스 맵 바위 (SHL_Booth_* · PRP_Crevice_*)
    public Material[] oldMats;                    // renderers 의 재질 칸을 차례로 펼친 옛 재질
    public Material newMat;
    public Light[] mains, bounces;                // 같은 차례 — 튀는 빛은 그 전등이 켜져 있을 때만
    public ParticleSystem dust;
    public Volume artVolume;                      // 겹치는 화면 설정 (필름 입자 · 빛 번짐 · 대비) — 켜고 끈다
    public Renderer[] newOnly, oldOnly;           // 차례 3: 새 모습에만 = 광장 물건 · 둥근 통나무 동발 / 옛 모습에만 = 네모 갱목 · 광장 공 전구 (부딪힘 상자는 늘 남는다)

    public static ArtLook Instance;
    public static bool On = true;
    public static float Wet = Tuning.ART_WET, Bounce = Tuning.ART_BOUNCE, Bright = Tuning.ART_BRIGHT, SignBright = Tuning.SIGN_BOARD_BRIGHT;
    public static bool SabBrightBoard;                                   // 사보타주 brightboard: 표지판 바탕 옛 칠 그대로 (09-30 전)
    Renderer[] signs = new Renderer[0];                                  // 표지판 판 (SignBoard*, glTF 재질 사본) — 바탕 칠 × SignBright
    Color[] sign0;
    float signShown = -1f;
    public static bool SabDryWall, SabBounceDead, SabPropsStay;   // 검사용 사보타주: drywall(젖음 0) · bouncedead(튀는 빛이 꺼진 전등에서도) · propsstay(옛 모습에서도 물건이 남음)
    static readonly int WetId = Shader.PropertyToID("_ArtWet"), BrightId = Shader.PropertyToID("_ArtBright"), BaseColorId = Shader.PropertyToID("baseColorFactor");   // 소품은 glTF 재질

    void Awake()
    {
        Instance = this;
        Wet = Tuning.ART_WET; Bounce = Tuning.ART_BOUNCE; Bright = Tuning.ART_BRIGHT; SignBright = Tuning.SIGN_BOARD_BRIGHT;
        signs = System.Array.FindAll(FindObjectsByType<MeshRenderer>(FindObjectsInactive.Include, FindObjectsSortMode.None), r => r.name.StartsWith("SignBoard"));
        sign0 = System.Array.ConvertAll(signs, r => r.material.GetColor(BaseColorId));
        Headlamp.Probes.RemoveAll(r => r == null);                       // 지난 씬의 사라진 물체
        foreach (var r in signs) Headlamp.Probes.Add(r);                 // 기둥에 붙은 판은 뒤에 부딪힘 몸체가 없다 — 머리등이 판 자체를 가까운 면으로
        Set(true);
    }

    public void Set(bool on)
    {
        On = on;
        int k = 0;
        foreach (var r in renderers)
        {
            var m = r.sharedMaterials;
            for (int i = 0; i < m.Length; i++, k++) m[i] = on ? newMat : oldMats[k];
            r.sharedMaterials = m;
        }
        if (dust != null)
        {
            if (on) dust.Play();
            else dust.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        }
        if (artVolume != null) artVolume.enabled = on;
        foreach (var r in newOnly ?? new Renderer[0]) r.enabled = on || SabPropsStay;
        foreach (var r in oldOnly ?? new Renderer[0]) r.enabled = !on;
        LateUpdate();
    }

    void Update()
    {
        var kb = Keyboard.current;
        if (kb == null) return;
        if (kb.insertKey.wasPressedThisFrame) Set(!On);
        bool shift = kb.shiftKey.isPressed;                                                                  // Shift+← → 는 1인칭 팔 어깨 자리 (3D-P) · Shift+PgDn PgUp 은 머리등 (DevHud)
        if (kb.homeKey.wasPressedThisFrame && !shift) Wet = Mathf.Max(0f, Wet - 0.25f);
        if (kb.endKey.wasPressedThisFrame && !shift) Wet += 0.25f;
        if (kb.homeKey.wasPressedThisFrame && shift) SignBright = Mathf.Round(SignBright / 1.25f * 1000f) / 1000f;
        if (kb.endKey.wasPressedThisFrame && shift) SignBright = Mathf.Min(1f, Mathf.Round(SignBright * 1.25f * 1000f) / 1000f);
        if (kb.pageDownKey.wasPressedThisFrame && !shift) Bounce = Mathf.Max(0f, Bounce - 0.05f);
        if (kb.pageUpKey.wasPressedThisFrame && !shift) Bounce += 0.05f;
        if (kb.leftArrowKey.wasPressedThisFrame && !shift || kb.numpad4Key.wasPressedThisFrame) Bright /= 1.1f;    // ← → : 숫자패드 없는 키보드(사용자 09-27 텐키리스)
        if (kb.rightArrowKey.wasPressedThisFrame && !shift || kb.numpad6Key.wasPressedThisFrame) Bright *= 1.1f;
    }

    void LateUpdate()                               // 전등이 켜지고 꺼지는 것(고치기 · 검사)을 따라간다
    {
        Shader.SetGlobalFloat(WetId, SabDryWall ? 0f : Wet);
        Shader.SetGlobalFloat(BrightId, Bright);
        float sb = SabBrightBoard ? 1f : SignBright;
        if (signShown != sb)
        {
            signShown = sb;
            for (int i = 0; i < signs.Length; i++) signs[i].material.SetColor(BaseColorId, new Color(sign0[i].r * sb, sign0[i].g * sb, sign0[i].b * sb, sign0[i].a));
        }
        for (int i = 0; i < bounces.Length; i++)
        {
            bool lit = mains[i].enabled && mains[i].gameObject.activeInHierarchy;
            bounces[i].enabled = On && (lit || SabBounceDead) && Bounce > 0f;
            bounces[i].intensity = mains[i].intensity * Bounce;
        }
    }

    public static string Line() => Instance == null ? "" :
        $"\nlook {(On ? "NEW" : "OLD")} [Ins]  wet {Wet:0.00} [Home End]  bounce {Bounce:0.00} [PgDn PgUp]  bright {Bright:0.00} [Left Right arrow]  sign board x{SignBright:0.000} (SIGN_BOARD_BRIGHT {Tuning.SIGN_BOARD_BRIGHT:0.000}) [Shift+Home Shift+End]";
}
