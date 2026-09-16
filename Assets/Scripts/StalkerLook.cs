using UnityEngine;

// 3D-②b: 괴물 살·머리 재질에 요철 세기 · 거칠기 배율 · 눈구멍 발광을 넣는다 (glTFast 재질 속성 이름 그대로).
// 값은 Tuning 에서 시작하고, DevHud 키(7 8 · , . · k l)가 바꾼 뒤 Apply() 를 부른다 — 사용자가 실행 파일에서 직접 찾는다(판정값 규칙).
// 발광은 살 재질 전부에 넣는다 — 눈구멍 발광 그림이 어느 재질에 들었든(재질 나누기가 해골과 안 맞는다) 그림 없는 재질엔 효과가 없다.
// Stalker.cs 는 안 건드린다. 모델 뿌리(Stalker/Body/Model)에 붙는다.
public class StalkerLook : MonoBehaviour
{
    [System.NonSerialized] public float normalScale = Tuning.STALKER_SKIN_NORMAL_SCALE;
    [System.NonSerialized] public float roughMul = Tuning.STALKER_SKIN_ROUGH_MUL;
    [System.NonSerialized] public float eyeEmission = Tuning.STALKER_EYE_EMISSION;
    static readonly int NormalScaleId = Shader.PropertyToID("normalTexture_scale");
    static readonly int RoughId = Shader.PropertyToID("roughnessFactor");
    static readonly int EmissiveId = Shader.PropertyToID("emissiveFactor");
    Material[] skin = new Material[0];
    public Renderer[] Renderers { get; private set; } = new Renderer[0];

    void Awake()
    {
        var list = new System.Collections.Generic.List<Material>();
        Renderers = GetComponentsInChildren<Renderer>(true);
        foreach (var r in Renderers)
            foreach (var m in r.materials)                  // 사본 — 임포트된 재질 에셋은 안 바꾼다
                if (m.name.StartsWith("살")) list.Add(m);
        skin = list.ToArray();
        Apply();
    }

    public void Apply()
    {
        foreach (var m in skin)
        {
            m.SetFloat(NormalScaleId, normalScale);
            m.SetFloat(RoughId, roughMul);
            m.SetColor(EmissiveId, Tuning.STALKER_EYE_COLOR * eyeEmission);
        }
    }
}
