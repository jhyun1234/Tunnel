using UnityEngine;
using UnityEngine.InputSystem;

// 헤드램프. 카메라를 LAMP_FOLLOW_TIME 만큼 늦게 쫓아간다 — 카메라 축에 딱 붙으면 빛에 방향이 없다(Godot #17).
// F 로 끄고 켠다. 소리·눈 적응(DARK_ADAPT_*)은 아직 없다.
[RequireComponent(typeof(Light))]
public class Headlamp : MonoBehaviour
{
    public Transform cam;
    public bool lampOn = true;
    public float energy = Tuning.LAMP_ENERGY;   // DevHud 가 조정한다

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
        lamp.intensity = Mathf.MoveTowards(lamp.intensity, lampOn ? energy : 0f, energy / Tuning.LAMP_TOGGLE_TIME * Time.deltaTime);

        float k = Tuning.LAMP_FOLLOW_TIME <= 0f ? 1f : 1f - Mathf.Exp(-Time.deltaTime / Tuning.LAMP_FOLLOW_TIME);
        transform.SetPositionAndRotation(cam.TransformPoint(Tuning.LAMP_OFFSET), Quaternion.Slerp(transform.rotation, cam.rotation, k));
    }
}
