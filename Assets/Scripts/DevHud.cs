using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

// 판정용 화면 표시와 손잡이. 사람이 실행 파일에서 안개·램프 값을 고를 때 쓴다.
// V 부피 안개 켜기/끄기 · [ ] 안개 밀도 ÷1.5 ×1.5 · - = 램프 세기 ÷1.25 ×1.25 · 1 2 어둠 적응 환경광 ÷1.25 ×1.25 · 3 4 곡괭이 내구도 −10/+10 · 5 6 스태미나 −20/+20 · 0 괴물 끄기/켜기 (Godot DebugHud 의 0) · F1 표시 끄기
public class DevHud : MonoBehaviour
{
    public Headlamp lamp;
    public Player player;
    public Volume volume;
    public Stalker stalker;
    public Pickaxe pickaxe;

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
        if (kb.digit0Key.wasPressedThisFrame && stalker != null) stalker.enabled = !stalker.enabled;
        if (kb.digit1Key.wasPressedThisFrame) lamp.darkAdaptAmbient /= 1.25f;   // 어둠 적응 환경광 — 사용자가 직접 값을 찾는다 (09-15)
        if (kb.digit2Key.wasPressedThisFrame) lamp.darkAdaptAmbient *= 1.25f;
        if (kb.digit3Key.wasPressedThisFrame && pickaxe != null) pickaxe.Adjust(-10f);   // 곡괭이 내구도 (UI-1a, 설계서 Step 6)
        if (kb.digit4Key.wasPressedThisFrame && pickaxe != null) pickaxe.Adjust(10f);
        if (kb.digit5Key.wasPressedThisFrame) player.stamina = Mathf.Max(0f, player.stamina - 20f);      // 스태미나 (UI-1b, 설계서 Step 6)
        if (kb.digit6Key.wasPressedThisFrame) player.stamina = Mathf.Min(Tuning.STAMINA_MAX, player.stamina + 20f);
    }

    void OnGUI()
    {
        if (!show || fog == null)
            return;
        string monster = stalker == null ? "" :
            $"\nstalker {(stalker.enabled ? stalker.state.ToString() : "OFF [0]")}  sense {stalker.sense}  heard {stalker.lastHeard}  dist {stalker.DistToPlayer:0.0} m  spots {stalker.spotsVisited}  caught {stalker.catches}  hp {stalker.hp:0} hits {stalker.hitsTaken} hidden {stalker.hiddenLeft:0} s   EAR x{stalker.earMul:0.0} (NOISE_PICK {Tuning.NOISE_PICK:0} m) · EYE {Tuning.STALKER_EYE_M:0} m {Tuning.STALKER_EYE_DEG:0}° · LIGHT {Tuning.STALKER_LIGHT_M:0} m";
        GUI.Label(new Rect(10, 10, 900, 120),
            $"{fps:0} fps  {Screen.width}x{Screen.height}\n" +
            $"volumetric fog {(fog.enabled.value ? "ON" : "OFF")}  density {fog.density.value:0.#####}   [V] [ [ ] ]\n" +
            $"lamp {(lamp.lampOn ? "ON" : "OFF")}  intensity {lamp.energy:0.#}   [F] [ - = ]   dark adapt {lamp.adapt:0.00}  DARK_ADAPT_AMBIENT {lamp.darkAdaptAmbient:0.##}   [ 1 2 ]\n" +
            $"{player.stance}  stamina {player.stamina:0}{(player.exhausted ? " EXHAUSTED" : "")}  nod x{(player.stamina <= Tuning.STAMINA_SOON ? Tuning.LAMP_BOB_SOON_MUL : 1f):0}   [ 5 6 ]   pick {(pickaxe == null ? "-" : $"{pickaxe.durability:0}/{Tuning.PICK_DURABILITY_MAX:0} {(pickaxe.hasPick ? "held" : pickaxe.Broken ? "BROKEN" : "thrown [E]")}")}   [ 3 4 ]   [F1] hide" + monster);
    }
}
