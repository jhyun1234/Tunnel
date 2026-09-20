using UnityEngine;

// 3D-②b: 괴물 살·머리 재질에 요철 세기 · 거칠기 배율 · 눈구멍 발광을 넣는다 (glTFast 재질 속성 이름 그대로).
// 값은 Tuning 에서 시작하고, DevHud 키(7 8 · , . · k l)가 바꾼 뒤 Apply() 를 부른다 — 사용자가 실행 파일에서 직접 찾는다(판정값 규칙).
// 발광은 살 재질 전부에 넣는다 — 눈구멍 발광 그림이 어느 재질에 들었든(재질 나누기가 해골과 안 맞는다) 그림 없는 재질엔 효과가 없다.
// 요철 세기: glTFast 6.14.1 의 normalTexture_scale 은 이 프로젝트(URP 셰이더 그래프)에서 안 먹는다 — Normal.cginc 가 세기를
// `#if (SHADER_TARGET >= 30)` 안에서만 곱하는데 그 조건이 꺼져 있다(09-18 실측: 4배로 해도 2 m 구조값 32.51 → 32.50).
// 그래서 세기를 곱한 요철 그림을 GPU 로 즉석에서 만들어(scaleShader) normalTexture 자리에 끼운다.
// Stalker.cs 는 안 건드린다. 모델 뿌리(Stalker/Body/Model)에 붙는다.
public class StalkerLook : MonoBehaviour
{
    public Shader glowShader;                      // Tunnel/LureGlow — 램프 미끼 빛무리 (씬 생성기가 넣는다)
    public Shader scaleShader;                     // Hidden/Tunnel/ScaleNormal — 씬 생성기가 넣는다 (빌드에 들어가게 참조로)
    [System.NonSerialized] public float normalScale = Tuning.STALKER_SKIN_NORMAL_SCALE;
    [System.NonSerialized] public float roughMul = Tuning.STALKER_SKIN_ROUGH_MUL;
    [System.NonSerialized] public float eyeEmission = Tuning.STALKER_EYE_EMISSION;
    [System.NonSerialized] public float neckBright = Tuning.STALKER_NECK_BRIGHT;   // DevHud Q/R
    [System.NonSerialized] public float neckRed = Tuning.STALKER_NECK_RED;   // 3D-③b M1e: 목 재질(목_근육) 붉기 — DevHud I/M
    // m3-③ M1 램프 미끼: 멀면 안전모 램프(재질 '램프_유리' + 약한 점광), 가까우면 램프가 떨다 꺼지고 → 어둠 → 눈. 거리·상태는 Stalker 에서 읽기만 한다
    [System.NonSerialized] public bool lure = true;                     // 검사 MonsterStage 가 끈다(살 모습만 재는 검사 — 미끼는 LureStage 가 잰다): 꺼지면 눈 켜짐 · 램프 꺼짐
    [System.NonSerialized] public float lureOffM = Tuning.STALKER_LURE_OFF_M;      // DevHud ; '
    [System.NonSerialized] public float lampEmission = Tuning.STALKER_LURE_EMISSION;   // DevHud / 와 역슬래시
    [System.NonSerialized] public bool sabAlwaysLamp, sabNoLamp, sabNoGap;   // 사보타주 alwayslamp · nolamp · nogap
    public float LampNow { get; private set; }                          // 0~1
    public float EyeNow { get; private set; } = 1f;
    public bool HasLamp => lampMats.Length > 0;
    Material[] lampMats = new Material[0];
    Light lampLight;
    Transform halo; Material haloMat;
    static readonly int ColorId = Shader.PropertyToID("_Color");
    Stalker st;
    bool lampWanted;
    float sinceToggle = 99f, lampShown = -1f, eyeShown = -1f;
    static readonly int BaseColorId = Shader.PropertyToID("baseColorFactor");
    Material[] neck = new Material[0];
    static readonly int NormalTexId = Shader.PropertyToID("normalTexture");
    static readonly int RoughId = Shader.PropertyToID("roughnessFactor");
    static readonly int EmissiveId = Shader.PropertyToID("emissiveFactor");
    static readonly int ScaleId = Shader.PropertyToID("_Scale");
    Material[] skin = new Material[0];
    Texture[] srcNormal = new Texture[0];
    RenderTexture[] scaled = new RenderTexture[0];
    Material blit;
    public Renderer[] Renderers { get; private set; } = new Renderer[0];

    void Awake()
    {
        var list = new System.Collections.Generic.List<Material>();
        Renderers = GetComponentsInChildren<Renderer>(true);
        foreach (var r in Renderers)
            foreach (var m in r.materials)                  // 사본 — 임포트된 재질 에셋은 안 바꾼다
                if (m.name.StartsWith("살")) list.Add(m);
        skin = list.ToArray();
        var nl = new System.Collections.Generic.List<Material>();
        foreach (var r in Renderers)
            foreach (var m in r.materials)
                if (m.name.StartsWith("목")) nl.Add(m);
        neck = nl.ToArray();
        var ll = new System.Collections.Generic.List<Material>();
        Renderer glass = null;
        foreach (var r in Renderers)
            foreach (var m in r.materials)
                if (m.name.StartsWith("램프")) { ll.Add(m); glass = r; }
        lampMats = ll.ToArray();
        st = GetComponentInParent<Stalker>();
        if (glass != null)
        {
            var headBone = System.Array.Find(GetComponentsInChildren<Transform>(), b => b.name == "mixamorig:Head");
            var go = new GameObject("StalkerLamp");
            go.transform.SetParent(headBone != null ? headBone : glass.transform, false);
            go.transform.position = glass.bounds.center + transform.forward * 0.12f;      // 유리 바로 앞 — 유리 속에 두면 제 그물에 가려 안전모만 비춘다
            lampLight = go.AddComponent<Light>();
            lampLight.type = LightType.Point; lampLight.color = Tuning.LAMP_COLOR; lampLight.range = Tuning.STALKER_LURE_LIGHT_RANGE;
            lampLight.shadows = LightShadows.None; lampLight.intensity = 0f;
            if (glowShader != null)
            {
                // 빛무리 판: 유리는 12 cm 라 15 m 밖에선 1~2 픽셀이고, 내 램프를 끄면 어둠 적응 안개(0.45)에 통째로 묻힌다(09-20 실측: 15~30 m 밝은 픽셀 0)
                var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
                Destroy(q.GetComponent<Collider>());
                q.name = "StalkerLampHalo"; q.transform.SetParent(go.transform, false);
                haloMat = new Material(glowShader);
                var mr = q.GetComponent<MeshRenderer>(); mr.sharedMaterial = haloMat;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;
                halo = q.transform;
            }
        }
        srcNormal = new Texture[skin.Length];
        scaled = new RenderTexture[skin.Length];
        for (int i = 0; i < skin.Length; i++) srcNormal[i] = skin[i].GetTexture(NormalTexId);
        if (scaleShader != null) blit = new Material(scaleShader);
        Apply();
    }

    void Update()
    {
        float d = st != null ? st.DistToPlayer : -1f;
        bool calm = st == null || st.state == Stalker.State.Wander || st.state == Stalker.State.Investigate || st.state == Stalker.State.Search;
        bool want = lure && HasLamp && !sabNoLamp && calm && d >= 0f && d > (lampWanted ? lureOffM : lureOffM + (Tuning.STALKER_LURE_ON_M - Tuning.STALKER_LURE_OFF_M));
        if (sabAlwaysLamp && HasLamp) want = true;
        if (want != lampWanted) { lampWanted = want; sinceToggle = 0f; }
        sinceToggle += Time.deltaTime;
        float t = sinceToggle, fl = Tuning.STALKER_LURE_FLICKER_S, gap = sabNoGap ? 0f : Tuning.STALKER_LURE_GAP_S, fade = Tuning.STALKER_LURE_FADE_S;
        if (lampWanted)
        {
            EyeNow = 1f - Mathf.Clamp01(t / fade);
            LampNow = Mathf.Clamp01((t - fade) / fade);
        }
        else
        {
            LampNow = t >= fl ? 0f : ((t > fl * 0.2f && t < fl * 0.4f) || (t > fl * 0.6f && t < fl * 0.8f) ? 0.15f : 1f);   // 두 번 떨다 꺼진다
            EyeNow = Mathf.Clamp01((t - fl - gap) / fade);
        }
        if (!Mathf.Approximately(LampNow, lampShown) || !Mathf.Approximately(EyeNow, eyeShown))
            ApplyGlow();
    }

    void LateUpdate()
    {
        if (halo == null) return;
        var cam = Camera.main;
        bool on = LampNow > 0f && cam != null;
        if (halo.gameObject.activeSelf != on) halo.gameObject.SetActive(on);
        if (!on) return;
        float d = Vector3.Distance(cam.transform.position, halo.position);
        halo.rotation = cam.transform.rotation;                                        // 늘 카메라를 본다
        float size = Mathf.Max(Tuning.STALKER_LURE_HALO_M, d * Tuning.STALKER_LURE_HALO_ANGLE);   // 멀어도 화면에서 일정 크기 아래로 안 줄어든다 (먼 불빛의 번짐)
        halo.localScale = Vector3.one * (size / Mathf.Max(halo.parent.lossyScale.x, 1e-4f));
        haloMat.SetColor(ColorId, Tuning.LAMP_COLOR * (lampEmission * LampNow * Mathf.Exp(-Tuning.FOG_DENSITY * d)));
    }

    void ApplyGlow()
    {
        lampShown = LampNow; eyeShown = EyeNow;
        foreach (var m in skin)
            m.SetColor(EmissiveId, Tuning.STALKER_EYE_COLOR * (eyeEmission * EyeNow));
        foreach (var m in lampMats)
            m.SetColor(EmissiveId, Tuning.LAMP_COLOR * (lampEmission * LampNow));
        if (lampLight != null)
            lampLight.intensity = Tuning.STALKER_LURE_LIGHT * LampNow;
    }

    public void Apply()
    {
        ApplyGlow();
        foreach (var m in neck)
            m.SetColor(BaseColorId, Color.Lerp(Color.white, Tuning.STALKER_NECK_RED_TINT, neckRed) * neckBright);
        for (int i = 0; i < skin.Length; i++)
        {
            var m = skin[i];
            m.SetFloat(RoughId, roughMul);
            if (srcNormal[i] == null || blit == null || m.GetTexture(NormalTexId) == null) continue;   // 노멀이 없거나 검사가 뺐으면(flatskin) 그대로
            if (Mathf.Approximately(normalScale, 1f)) { m.SetTexture(NormalTexId, srcNormal[i]); continue; }
            if (scaled[i] == null)
            {
                scaled[i] = new RenderTexture(srcNormal[i].width, srcNormal[i].height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear)
                    { useMipMap = true, autoGenerateMips = true, wrapMode = srcNormal[i].wrapMode, filterMode = FilterMode.Trilinear, anisoLevel = srcNormal[i].anisoLevel };
            }
            blit.SetFloat(ScaleId, normalScale);
            Graphics.Blit(srcNormal[i], scaled[i], blit);
            m.SetTexture(NormalTexId, scaled[i]);
        }
    }

    void OnDestroy()
    {
        foreach (var rt in scaled) if (rt != null) rt.Release();
    }
}
