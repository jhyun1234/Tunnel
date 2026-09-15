using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

// 판정용 화면 표시와 손잡이. 사람이 실행 파일에서 안개·램프 값을 고를 때 쓴다.
// V 부피 안개 켜기/끄기 · [ ] 안개 밀도 ÷1.5 ×1.5 · - = 램프 세기 ÷1.25 ×1.25 · F1 표시 끄기
public class DevHud : MonoBehaviour
{
    public Headlamp lamp;
    public Player player;
    public Volume volume;
    public Stalker stalker;

    VolumetricFogVolumeComponent fog;
    float fps, acc;
    int frames;
    bool show = true;

    void Start()
    {
        volume.profile.TryGet(out fog);    // .profile 은 실행 중 사본 — 에셋을 안 바꾼다
    }

    void Update()
    {
        acc += Time.unscaledDeltaTime;
        frames++;
        if (acc >= 0.5f)
        {
            fps = frames / acc;
            acc = 0f;
            frames = 0;
        }
        var kb = Keyboard.current;
        if (kb == null || fog == null)
            return;
        if (kb.vKey.wasPressedThisFrame) fog.enabled.value = !fog.enabled.value;
        if (kb.rightBracketKey.wasPressedThisFrame) fog.density.value *= 1.5f;
        if (kb.leftBracketKey.wasPressedThisFrame) fog.density.value /= 1.5f;
        if (kb.equalsKey.wasPressedThisFrame) lamp.energy *= 1.25f;
        if (kb.minusKey.wasPressedThisFrame) lamp.energy /= 1.25f;
        if (kb.f1Key.wasPressedThisFrame) show = !show;
    }

    void OnGUI()
    {
        if (!show || fog == null)
            return;
        string monster = stalker == null ? "" :
            $"\nstalker {stalker.state}  heard {stalker.lastHeard}  dist {stalker.DistToPlayer:0.0} m  spots {stalker.spotsVisited}   STALKER_EAR_MUL x{stalker.earMul:0.0} (NOISE_PICK {Tuning.NOISE_PICK:0} m)";
        GUI.Label(new Rect(10, 10, 900, 120),
            $"{fps:0} fps  {Screen.width}x{Screen.height}\n" +
            $"volumetric fog {(fog.enabled.value ? "ON" : "OFF")}  density {fog.density.value:0.#####}   [V] [ [ ] ]\n" +
            $"lamp {(lamp.lampOn ? "ON" : "OFF")}  intensity {lamp.energy:0.#}   [F] [ - = ]\n" +
            $"{player.stance}  stamina {player.stamina:0}   [F1] hide" + monster);
    }
}
