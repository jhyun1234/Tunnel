using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

// 판정용 화면 표시와 손잡이. 사람이 실행 파일에서 안개·램프 값을 고를 때 쓴다.
// 시작할 때 꺼져 있다(UI-1d) — F1 로 켠다. 손잡이 키는 꺼져 있어도 먹는다.
// V 부피 안개 켜기/끄기 · [ ] 안개 밀도 ÷1.5 ×1.5 · - = 램프 세기 ÷1.25 ×1.25 · 1 2 어둠 적응 환경광 ÷1.25 ×1.25 · 3 4 곡괭이 내구도 −10/+10 · 5 6 스태미나 −20/+20 · 0 괴물 끄기/켜기 (Godot DebugHud 의 0) · 9 괴물을 내 앞에 세움 · N 선 괴물의 동작 차례로 · U 배회 걸음 A/B/C (3D-③) · F1 표시 끄기
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
    bool show, started;
    [System.NonSerialized] public bool startVisible = Tuning.DEVHUD_START_VISIBLE;   // 첫 Update 에서 한 번 적용 (UI-1d: 꺼진 채 시작). 사보타주 hudon 이 켠다
    public MiningHud miningHud;                            // 소음 원·마지막 소음 (UI-1c: 원은 DevHud 켰을 때만)
    public static bool Visible { get; private set; }       // F1 상태 — MiningHud 가 본다. 컴포넌트가 꺼지면(검사) false

    void Start()
    {
        volume.profile.TryGet(out fog);    // .profile 은 실행 중 사본 — 에셋을 안 바꾼다
    }

    void OnDisable() => Visible = false;

    void Update()
    {
        if (!started) { show = startVisible; started = true; }
        Visible = show;
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
        if ((kb.digit0Key.wasPressedThisFrame || kb.numpad0Key.wasPressedThisFrame) && stalker != null) stalker.enabled = !stalker.enabled;
        // 9 = 판정용: 괴물 행동을 끄고 내 앞 2.5 m 에 나를 보게 세운다 (사용자 09-17 "계속 접근해서 확인할 수 없다"). 0 으로 다시 켠다
        if ((kb.digit9Key.wasPressedThisFrame || kb.numpad9Key.wasPressedThisFrame) && stalker != null)
        {
            stalker.enabled = false;
            PlaceAhead(2.5f);
        }
        if (kb.digit1Key.wasPressedThisFrame) lamp.darkAdaptAmbient /= 1.25f;   // 어둠 적응 환경광 — 사용자가 직접 값을 찾는다 (09-15)
        if (kb.digit2Key.wasPressedThisFrame) lamp.darkAdaptAmbient *= 1.25f;
        if (kb.digit3Key.wasPressedThisFrame && pickaxe != null) pickaxe.Adjust(-10f);   // 곡괭이 내구도 (UI-1a, 설계서 Step 6)
        if (kb.digit4Key.wasPressedThisFrame && pickaxe != null) pickaxe.Adjust(10f);
        if (kb.digit5Key.wasPressedThisFrame) player.stamina = Mathf.Max(0f, player.stamina - 20f);      // 스태미나 (UI-1b, 설계서 Step 6)
        if (kb.digit6Key.wasPressedThisFrame) player.stamina = Mathf.Min(Tuning.STAMINA_MAX, player.stamina + 20f);
        var sa = stalker != null ? stalker.GetComponentInChildren<StalkerAnim>() : null;   // 3D-③: 동작 판정 — 선 괴물의 동작을 차례로, 배회 걸음 안을 바꾼다
        if (sa != null)
        {
            if (kb.gKey.wasPressedThisFrame) sa.headTest = (sa.headTest + 1) % 4;                   // 3D-③b M1d: 세운 괴물(9)의 머리 시험
            if (kb.tKey.wasPressedThisFrame) sa.headYawMax = Mathf.Max(15f, sa.headYawMax - 15f);
            if (kb.yKey.wasPressedThisFrame) sa.headYawMax = Mathf.Min(180f, sa.headYawMax + 15f);
            if (kb.oKey.wasPressedThisFrame) sa.headTilt = Mathf.Max(0f, sa.headTilt - 10f);
            if (kb.pKey.wasPressedThisFrame) sa.headTilt = Mathf.Min(180f, sa.headTilt + 10f);
            if (kb.hKey.wasPressedThisFrame) sa.jawWideDeg = Mathf.Max(5f, sa.jawWideDeg - 5f);    // 3D-③b M1c: 포효·잡기 턱 벌림 — 사용자가 값을 찾는다
            if (kb.jKey.wasPressedThisFrame) sa.jawWideDeg = Mathf.Min(90f, sa.jawWideDeg + 5f);
            if (kb.nKey.wasPressedThisFrame && !stalker.enabled) { sa.manual = (sa.manual + 1) % StalkerAnim.ManualClips.Length; walkPreview = false; }
            // U = 배회 걸음 A/B/C/D. 세운 괴물(9)이면 8 m 앞에서 배회 빠르기로 걸어오기를 되풀이한다 — 행동을 켜면 12 m 에서 나를 보고
            // 바로 포효·추격이라 가까이서 배회 걸음을 볼 틈이 없다 (사용자 09-18 "U 를 눌렀을 때 적용이 안 된다")
            if (kb.uKey.wasPressedThisFrame)
            {
                sa.gait = (sa.gait + 1) % Tuning.STALKER_GAIT_COUNT;
                if (!stalker.enabled && !walkPreview && previewOn) { walkPreview = true; PlaceAhead(Tuning.STALKER_PREVIEW_FROM_M); }
            }
        }
        if (walkPreview && (stalker == null || stalker.enabled || kb.digit9Key.wasPressedThisFrame || kb.numpad9Key.wasPressedThisFrame))
            walkPreview = false;
        if (walkPreview)
        {
            Vector3 to = player.transform.position - stalker.transform.position;
            to.y = 0f;
            if (to.magnitude <= Tuning.STALKER_PREVIEW_TO_M)
                PlaceAhead(Tuning.STALKER_PREVIEW_FROM_M);
            else
                stalker.GetComponent<CharacterController>().Move((to.normalized * Tuning.STALKER_SPEED_WANDER + Vector3.down) * Time.deltaTime);
        }
        var look = stalker != null ? stalker.GetComponentInChildren<StalkerLook>() : null;   // 3D-②b: 살 요철·거칠기·눈 발광 — 사용자가 값을 찾는다
        if (look != null)
        {
            bool changed = true;
            if (kb.digit7Key.wasPressedThisFrame) look.normalScale /= 1.25f;
            else if (kb.digit8Key.wasPressedThisFrame) look.normalScale *= 1.25f;
            else if (kb.commaKey.wasPressedThisFrame) look.roughMul *= 0.9f;
            else if (kb.periodKey.wasPressedThisFrame) look.roughMul /= 0.9f;
            else if (kb.kKey.wasPressedThisFrame) look.eyeEmission *= 0.8f;
            else if (kb.lKey.wasPressedThisFrame) look.eyeEmission /= 0.8f;
            else changed = false;
            if (changed) look.Apply();
        }
    }

    [System.NonSerialized] public bool walkPreview;        // U: 세운 괴물이 걸어오기를 되풀이 (검사도 본다)
    [System.NonSerialized] public bool previewOn = true;   // 사보타주 nopreview 가 끈다 (고치기 전: U 가 세운 괴물에 안 먹던 상태)

    // 괴물을 내 앞 m 에 나를 보게 세운다
    void PlaceAhead(float m)
    {
        Vector3 f = player.transform.forward; f.y = 0f; f.Normalize();
        stalker.Teleport(player.transform.position + f * m, player.transform.eulerAngles.y + 180f);
    }

    void OnGUI()
    {
        if (!show || fog == null)
            return;
        string monster = stalker == null ? "" :
            $"\nstalker {(stalker.enabled ? stalker.state.ToString() : "OFF [0]")}  sense {stalker.sense}  heard {stalker.lastHeard}  dist {stalker.DistToPlayer:0.0} m  spots {stalker.spotsVisited}  caught {stalker.catches}  hp {stalker.hp:0} hits {stalker.hitsTaken} hidden {stalker.hiddenLeft:0} s   EAR x{stalker.earMul:0.0} (NOISE_PICK {Tuning.NOISE_PICK:0} m) · EYE {Tuning.STALKER_EYE_M:0} m {Tuning.STALKER_EYE_DEG:0}° · LIGHT {Tuning.STALKER_LIGHT_M:0} m" +
            (stalker.GetComponentInChildren<StalkerAnim>() is StalkerAnim an ? $"\nanim {an.Current} x{an.Rate:0.00} at {an.Speed:0.0} m/s{(stalker.enabled ? "" : "   [N] next clip")}   wander gait {StalkerAnim.GaitName(an.gait)} [U]   jaw {an.JawDeg:0}° (roar/catch {an.jawWideDeg:0}° [H J])\nhead test {StalkerAnim.HeadTestName(an.headTest)} [G]  face {an.HeadYaw:0}° (max {an.headYawMax:0}° [T Y])  tilt {an.HeadTiltNow:0}° (listen {an.headTilt:0}° [O P]){(walkPreview ? "  WALK-IN PREVIEW ([9] stop)" : "")}" : "") +
            (stalker.GetComponentInChildren<StalkerLook>() is StalkerLook lk ? $"\nskin relief x{lk.normalScale:0.00} [7 8]   rough x{lk.roughMul:0.00} [, .]   eye glow {lk.eyeEmission:0.00} [k l]   [9] freeze monster in front of me · [0] on/off" : "");
        GUI.Label(new Rect(10, 10, 900, 140),
            $"{fps:0} fps  {Screen.width}x{Screen.height}\n" +
            $"volumetric fog {(fog.enabled.value ? "ON" : "OFF")}  density {fog.density.value:0.#####}   [V] [ [ ] ]\n" +
            $"lamp {(lamp.lampOn ? "ON" : "OFF")}  intensity {lamp.energy:0.#}   [F] [ - = ]   dark adapt {lamp.adapt:0.00}  DARK_ADAPT_AMBIENT {lamp.darkAdaptAmbient:0.##}   [ 1 2 ]\n" +
            $"{player.stance}  stamina {player.stamina:0}{(player.exhausted ? " EXHAUSTED" : "")}  nod x{(player.stamina <= Tuning.STAMINA_SOON ? Tuning.LAMP_BOB_SOON_MUL : 1f):0}   [ 5 6 ]   ore {player.ore}  noise {(miningHud == null ? "-" : $"{miningHud.LastKind} {miningHud.LastRadius:0} m {miningHud.Left:0.0} s")}   pick {(pickaxe == null ? "-" : $"{pickaxe.durability:0}/{Tuning.PICK_DURABILITY_MAX:0} {(pickaxe.hasPick ? "held" : pickaxe.Broken ? "BROKEN" : "thrown [E]")}")}   [ 3 4 ]   [F1] hide" + monster);
    }
}
