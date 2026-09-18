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
    public Shader scaleShader;                     // Hidden/Tunnel/ScaleNormal — 씬 생성기가 넣는다 (빌드에 들어가게 참조로)
    [System.NonSerialized] public float normalScale = Tuning.STALKER_SKIN_NORMAL_SCALE;
    [System.NonSerialized] public float roughMul = Tuning.STALKER_SKIN_ROUGH_MUL;
    [System.NonSerialized] public float eyeEmission = Tuning.STALKER_EYE_EMISSION;
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
        srcNormal = new Texture[skin.Length];
        scaled = new RenderTexture[skin.Length];
        for (int i = 0; i < skin.Length; i++) srcNormal[i] = skin[i].GetTexture(NormalTexId);
        if (scaleShader != null) blit = new Material(scaleShader);
        Apply();
    }

    public void Apply()
    {
        for (int i = 0; i < skin.Length; i++)
        {
            var m = skin[i];
            m.SetFloat(RoughId, roughMul);
            m.SetColor(EmissiveId, Tuning.STALKER_EYE_COLOR * eyeEmission);
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
