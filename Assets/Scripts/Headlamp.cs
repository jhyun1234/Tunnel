using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering.Universal;

// 헤드램프. 카메라를 LAMP_FOLLOW_TIME 만큼 늦게 쫓아간다 — 카메라 축에 딱 붙으면 빛에 방향이 없다(Godot #17).
// 가까운 면을 비추면 세기를 낮춘다(LAMP_NEAR_*) — URP 거리 제곱 감쇠로 벽 앞이 하얗게 타지 않게.
// 곡괭이는 비추지 않는다(조명 레이어). 곡괭이 전용 약한 등(pickLight)이 램프와 같이 켜지고 꺼진다.
// F 로 끄고 켠다. 끄면 눈이 어둠에 적응한다(DARK_ADAPT_*: 환경광이 오르고 거리 안개가 짙어진다). 소리는 아직 없다.
// 몸 상태(UI-1b): 걸으면 Player.gait 박자로 끄덕인다(발 닿는 순간 맨 아래), 스태미나 곧 단계면 폭 3배. 탈진 자세는 Player 가 카메라를 숙이니 램프는 따라만 간다.
[RequireComponent(typeof(Light))]
public class Headlamp : MonoBehaviour
{
    public Transform cam;
    // 3D-②: 등 하나만 그림자 편차를 따로 (URP 파이프라인 값 대신). 검사 스윕·사보타주 acne 가 바꾼 뒤 ApplyShadowBias()
    [System.NonSerialized] public float shadowDepthBias = Tuning.LAMP_SHADOW_DEPTH_BIAS;
    [System.NonSerialized] public float shadowNormalBias = Tuning.LAMP_SHADOW_NORMAL_BIAS;
    public Light pickLight;
    public bool lampOn = true;
    // 씬에 굽지 않는다 — 값은 Tuning 한 곳. DevHud·검사가 실행 중에 조정한다
    [System.NonSerialized] public float energy = Tuning.LAMP_ENERGY;
    [System.NonSerialized] public float nearRef = Tuning.LAMP_NEAR_REF;
    [System.NonSerialized] public float nearPow = Tuning.LAMP_NEAR_POW;
    [System.NonSerialized] public float nearDim = 1f;
    [System.NonSerialized] public float darkAdaptAmbient = Tuning.DARK_ADAPT_AMBIENT;
    [System.NonSerialized] public float adapt;     // 0 = 평소, 1 = 어둠에 다 적응
    [System.NonSerialized] public float bobDeg = Tuning.LAMP_BOB_DEG;   // 검사가 읽는다 (사용자 판정값 0.6, 09-16)
    [System.NonSerialized] public bool soonNod = true;  // 사보타주 flatnod 가 끈다 — 곧 단계에도 폭 그대로
    [System.NonSerialized] public float nodDeg;    // 지금 더해진 끄덕임 (검사가 읽는다)
    [System.NonSerialized] public float pulseEnergy; // 탈진 박동이 적용된 세기(감광·페이드 전). 탈진 아니면 energy (검사가 읽는다)
    float pulsePhase;

    static readonly Vector3[] RayDirs = BuildRays();
    Light lamp;
    Player player;
    Quaternion follow;                             // 카메라를 늦게 쫓는 회전. 끄덕임은 이 위에 얹는다
    float fade = 1f;

    public static void Apply(Light light)
    {
        light.type = LightType.Spot;
        light.spotAngle = Tuning.LAMP_ANGLE_DEG * 2f;
        light.innerSpotAngle = light.spotAngle * Tuning.LAMP_INNER_FRAC;
        light.range = Tuning.LAMP_RANGE;
        light.color = Tuning.LAMP_COLOR;
        light.intensity = Tuning.LAMP_ENERGY;
        light.shadows = Tuning.LAMP_SHADOW ? LightShadows.Soft : LightShadows.None;
    }

    public void ApplyShadowBias()
    {
        var data = lamp.GetUniversalAdditionalLightData();
        data.usePipelineSettings = false;
        lamp.shadowBias = shadowDepthBias;
        lamp.shadowNormalBias = shadowNormalBias;
    }

    // 가운데 하나 + 원뿔 반각의 절반 기울기로 8방향
    static Vector3[] BuildRays()
    {
        var dirs = new Vector3[9];
        dirs[0] = Vector3.forward;
        for (int i = 0; i < 8; i++)
            dirs[i + 1] = Quaternion.Euler(0f, 0f, i * 45f) * Quaternion.Euler(Tuning.LAMP_ANGLE_DEG * 0.5f, 0f, 0f) * Vector3.forward;
        return dirs;
    }

    void Awake()
    {
        lamp = GetComponent<Light>();
        Apply(lamp);
        ApplyShadowBias();
        transform.SetPositionAndRotation(cam.TransformPoint(Tuning.LAMP_OFFSET), cam.rotation);
        follow = cam.rotation;
        player = cam.GetComponentInParent<Player>();
    }

    void LateUpdate()
    {
        var kb = Keyboard.current;
        if (kb != null && kb.fKey.wasPressedThisFrame)
            lampOn = !lampOn;
        fade = Mathf.MoveTowards(fade, lampOn ? 1f : 0f, Time.deltaTime / Tuning.LAMP_TOGGLE_TIME);

        float k = Tuning.LAMP_FOLLOW_TIME <= 0f ? 1f : 1f - Mathf.Exp(-Time.deltaTime / Tuning.LAMP_FOLLOW_TIME);
        follow = Quaternion.Slerp(follow, cam.rotation, k);
        nodDeg = 0f;
        if (player != null)
        {
            // 끄덕임: 걸음 위상 π 마다 발이 닿고 그때 맨 아래(cos 2·gait = 1). 속도에 비례, 서면 0. 곧 단계면 LAMP_BOB_SOON_MUL 배 — 바로 바뀐다("갑자기 심해진다"가 신호)
            float mul = player.stamina <= Tuning.STAMINA_SOON && soonNod ? Tuning.LAMP_BOB_SOON_MUL : 1f;
            nodDeg = Mathf.Cos(player.gait * 2f) * bobDeg * mul * Mathf.Clamp01(player.Speed / Tuning.WALK_SPEED * (player.gait > 0f ? 1f : 0f));
        }
        transform.SetPositionAndRotation(cam.TransformPoint(Tuning.LAMP_OFFSET), follow * Quaternion.Euler(nodDeg, 0f, 0f));

        float kDim = 1f - Mathf.Exp(-Time.deltaTime / Tuning.LAMP_NEAR_TIME);
        nearDim = Mathf.Lerp(nearDim, NearDim(), kDim);
        // 탈진(3차 판정 09-16): 세기가 LAMP_EXHAUST_MIN~MAX 사이를 빠른 심장 박동처럼 — 박동 순간 MAX 로 뛰고 지수로 MIN 까지 잦아든다. 탈진 정도(pant)로 섞는다
        pulseEnergy = energy;
        if (player != null && player.pant > 0f)
        {
            pulsePhase = (pulsePhase + Time.deltaTime / Tuning.EXHAUST_PULSE_S) % 1f;
            float beat = Mathf.Exp(-pulsePhase * 4f);                    // 1 → 0.02
            pulseEnergy = Mathf.Lerp(energy, Mathf.Lerp(Tuning.LAMP_EXHAUST_MIN, Tuning.LAMP_EXHAUST_MAX, beat), player.pant);
        }
        else
            pulsePhase = 0f;
        lamp.intensity = pulseEnergy * nearDim * fade;
        // 어둠 적응: 끄면 DARK_ADAPT_TIME 에 걸쳐 오르고, 켜면 즉시 평소 (Godot Atmosphere.gd 트윈과 같다)
        adapt = lampOn ? 0f : Mathf.MoveTowards(adapt, 1f, Time.deltaTime / Tuning.DARK_ADAPT_TIME);
        RenderSettings.ambientLight = Tuning.AMBIENT_COLOR * Mathf.Lerp(Tuning.AMBIENT_ENERGY, darkAdaptAmbient, adapt);
        RenderSettings.fogDensity = Mathf.Lerp(Tuning.FOG_DENSITY, Tuning.DARK_ADAPT_FOG, adapt);
        if (pickLight != null)
            pickLight.intensity = Tuning.PICK_LIGHT_ENERGY * fade;
    }

    float NearDim()
    {
        float sum = 0f;
        foreach (var dir in RayDirs)
        {
            float d = Physics.Raycast(transform.position, transform.rotation * dir, out RaycastHit hit, nearRef, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
                ? hit.distance : nearRef;
            sum += Mathf.Pow(Mathf.Max(d, 0.05f) / nearRef, nearPow);
        }
        return sum / RayDirs.Length;
    }
}
