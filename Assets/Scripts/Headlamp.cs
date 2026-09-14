using UnityEngine;
using UnityEngine.InputSystem;

// 헤드램프. 카메라를 LAMP_FOLLOW_TIME 만큼 늦게 쫓아간다 — 카메라 축에 딱 붙으면 빛에 방향이 없다(Godot #17).
// 가까운 면을 비추면 세기를 낮춘다(LAMP_NEAR_*) — URP 거리 제곱 감쇠로 벽 앞이 하얗게 타지 않게.
// F 로 끄고 켠다. 소리·눈 적응(DARK_ADAPT_*)은 아직 없다.
[RequireComponent(typeof(Light))]
public class Headlamp : MonoBehaviour
{
    public Transform cam;
    public bool lampOn = true;
    // 씬에 굽지 않는다 — 값은 Tuning 한 곳. DevHud·검사가 실행 중에 조정한다
    [System.NonSerialized] public float energy = Tuning.LAMP_ENERGY;
    [System.NonSerialized] public float nearRef = Tuning.LAMP_NEAR_REF;
    [System.NonSerialized] public float nearPow = Tuning.LAMP_NEAR_POW;
    [System.NonSerialized] public float nearDim = 1f;

    static readonly Vector3[] RayDirs = BuildRays();
    Light lamp;

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
        transform.SetPositionAndRotation(cam.TransformPoint(Tuning.LAMP_OFFSET), cam.rotation);
    }

    void LateUpdate()
    {
        var kb = Keyboard.current;
        if (kb != null && kb.fKey.wasPressedThisFrame)
            lampOn = !lampOn;

        float k = Tuning.LAMP_FOLLOW_TIME <= 0f ? 1f : 1f - Mathf.Exp(-Time.deltaTime / Tuning.LAMP_FOLLOW_TIME);
        transform.SetPositionAndRotation(cam.TransformPoint(Tuning.LAMP_OFFSET), Quaternion.Slerp(transform.rotation, cam.rotation, k));

        float kDim = 1f - Mathf.Exp(-Time.deltaTime / Tuning.LAMP_NEAR_TIME);
        nearDim = Mathf.Lerp(nearDim, NearDim(), kDim);
        lamp.intensity = Mathf.MoveTowards(lamp.intensity, lampOn ? energy * nearDim : 0f, energy / Tuning.LAMP_TOGGLE_TIME * Time.deltaTime);
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
