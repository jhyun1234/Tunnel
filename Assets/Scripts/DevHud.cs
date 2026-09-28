using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

// 판정용 화면 표시와 손잡이. 사람이 실행 파일에서 안개·램프 값을 고를 때 쓴다.
// 시작할 때 꺼져 있다(UI-1d) — F1 로 켠다. 손잡이 키는 꺼져 있어도 먹는다.
// V 부피 안개 켜기/끄기 · [ ] 안개 밀도 ÷1.5 ×1.5 · - = 램프 세기 ÷1.25 ×1.25 · 1 2 어둠 적응 환경광 ÷1.25 ×1.25 · 3 4 곡괭이 내구도 −10/+10 · 5 6 스태미나 −20/+20 · 0 괴물 끄기/켜기 (Godot DebugHud 의 0) · 9 괴물을 내 앞에 세움 · N 선 괴물의 동작 차례로 · U 배회 걸음 A/B/C (3D-③) · I M 목 붉기 −/+ · Q R 목 밝기 ÷× 1.15 · Z X 세운 괴물 목 길이 −/+ · C B 목 빼는 시간 −/+ (3D-③b M1e) · F1 표시 끄기
// 부스 맵: 숫자패드 − + 켜진 전등 밝기 ÷×1.25 · F5 F6 막힘 묶음 서쪽·동쪽 켜기/끄기 · F7 F8 바위 틈 비집는 시간 −/+ 0.25 s · F9 F10 틈 속 몸 돌리는 각 −/+ 10° (누르면 표시가 켜진다)
// REP-1 고칠 곳: F2 가장 가까운 멀쩡한 고칠 곳을 망가뜨림 · F3 F4 고치는 시간 ÷×1.25 (모든 종류) · F11 F12 판 중 망가지는 간격 −/+ 30 s
// ART-1 현실감: Insert 옛/새 · Home/End 젖음 · PageDown/PageUp 튀는 빛 · 숫자패드 4/6 바위 밝기 — 키는 ArtLook 이 받는다 (여기는 줄만)
public class DevHud : MonoBehaviour
{
    public Headlamp lamp;
    public Light[] boothLights = new Light[0];             // MAP1: 켜진 전등 (BuildM1.PlaceBoothLights)
    public GameObject[] boothBlocks = new GameObject[0];   // MAP2: 막힘 돌무더기 BLK_<묶음>_<i> (묶음 1 서쪽 · 2 동쪽)
    public static int BlockGroup(GameObject b) => b.name[4] - '0';   // "BLK_2_11" → 2
    bool GroupOn(int g) => System.Array.Exists(boothBlocks, b => BlockGroup(b) == g && b.activeSelf);
    public Player player;
    public Volume volume;
    public Stalker stalker;
    public Pickaxe pickaxe;
    public RepairDirector repairs;                         // REP-1 (부스 맵만)

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
        if (!started) { show = startVisible; started = true; if (!Mathf.Approximately(Tuning.ORE_SHINE, 1f)) ApplyOreShine(); }   // ORE-1: 판정에서 받은 반짝임
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
        if (kb.rightBracketKey.wasPressedThisFrame && !kb.shiftKey.isPressed) fog.density.value *= 1.5f;   // Shift+[ ] 는 콱 크기 (SND-P)
        if (kb.leftBracketKey.wasPressedThisFrame && !kb.shiftKey.isPressed) fog.density.value /= 1.5f;
        if (kb.equalsKey.wasPressedThisFrame) lamp.energy *= 1.25f;
        if (kb.minusKey.wasPressedThisFrame) lamp.energy /= 1.25f;
        if (kb.f1Key.wasPressedThisFrame) show = !show;
        BoothKeys(kb);
        if ((kb.digit0Key.wasPressedThisFrame || kb.numpad0Key.wasPressedThisFrame) && stalker != null) stalker.enabled = !stalker.enabled;
        // 9 = 판정용: 괴물 행동을 끄고 내 앞 2.5 m 에 나를 보게 세운다 (사용자 09-17 "계속 접근해서 확인할 수 없다"). 0 으로 다시 켠다
        if ((kb.digit9Key.wasPressedThisFrame || kb.numpad9Key.wasPressedThisFrame) && stalker != null)
        {
            stalker.enabled = false;
            PlaceAhead(2.5f);
        }
        MineKeys(kb);
        OreKeys(kb);
        HitKeys(kb);
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
            if (kb.zKey.wasPressedThisFrame) sa.neckWant = Mathf.Max(0f, sa.neckWant - 0.05f);      // 3D-③b M1e: 목 길게 빼기 — 사용자가 길이·빠르기를 찾는다 (모델 m)
            if (kb.xKey.wasPressedThisFrame) sa.neckWant = Mathf.Min(Tuning.STALKER_NECK_OUT_MAX_M, sa.neckWant + 0.05f);
            if (kb.cKey.wasPressedThisFrame) sa.neckOutS = Mathf.Max(0.05f, sa.neckOutS / 1.25f);
            if (kb.bKey.wasPressedThisFrame) sa.neckOutS = Mathf.Min(5f, sa.neckOutS * 1.25f);
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
                stalker.GetComponent<CharacterController>().Move((to.normalized * Tuning.STALKER_PREVIEW_SPEED + Vector3.down) * Time.deltaTime);
        }
        var look = stalker != null ? stalker.GetComponentInChildren<StalkerLook>() : null;   // 3D-②b: 살 요철·거칠기·눈 발광 — 사용자가 값을 찾는다
        if (look != null)
        {
            bool changed = true;
            if (kb.digit7Key.wasPressedThisFrame) look.normalScale /= 1.25f;
            else if (kb.digit8Key.wasPressedThisFrame) look.normalScale *= 1.25f;
            else if (kb.commaKey.wasPressedThisFrame && !kb.shiftKey.isPressed) look.roughMul *= 0.9f;      // Shift+, . 는 광석 반짝임 (ORE-1)
            else if (kb.periodKey.wasPressedThisFrame && !kb.shiftKey.isPressed) look.roughMul /= 0.9f;
            else if (kb.iKey.wasPressedThisFrame) look.neckRed = Mathf.Max(0f, look.neckRed - 0.1f);   // 3D-③b M1e: 목 붉기 (0 = 몸 살 색)
            else if (kb.mKey.wasPressedThisFrame) look.neckRed = Mathf.Min(1f, look.neckRed + 0.1f);
            else if (kb.qKey.wasPressedThisFrame) look.neckBright = Mathf.Max(0.2f, look.neckBright / 1.15f);   // 목 밝기
            else if (kb.rKey.wasPressedThisFrame) look.neckBright = Mathf.Min(4f, look.neckBright * 1.15f);
            else if (kb.semicolonKey.wasPressedThisFrame) look.lureOffM = Mathf.Max(4f, look.lureOffM - 1f);   // m3-③ M1 램프 미끼: 램프가 꺼지는 거리
            else if (kb.quoteKey.wasPressedThisFrame) look.lureOffM = Mathf.Min(40f, look.lureOffM + 1f);
            else if (kb.slashKey.wasPressedThisFrame) look.lampEmission /= 1.25f;                               // 램프 유리 밝기
            else if (kb.backslashKey.wasPressedThisFrame) look.lampEmission *= 1.25f;
            else if (kb.kKey.wasPressedThisFrame) look.eyeEmission *= 0.8f;
            else if (kb.lKey.wasPressedThisFrame) look.eyeEmission /= 0.8f;
            else changed = false;
            if (changed) look.Apply();
        }
    }

    // MAP1 판정 손잡이: 받은 숫자를 Tuning.BOOTH_LIGHT_ENERGY · BOOTH_BLOCKS 에
    void BoothKeys(Keyboard kb)
    {
        if (boothLights.Length > 0 && (kb.scrollLockKey.wasPressedThisFrame || kb.pauseKey.wasPressedThisFrame))   // 숫자패드 − + 였다 → 텐키리스(CLAUDE.md)
        {
            float m = kb.pauseKey.wasPressedThisFrame ? 1.25f : 1f / 1.25f;
            foreach (var l in boothLights) l.intensity *= m;
            show = true;
        }
        var fk = new[] { kb.f5Key, kb.f6Key };
        for (int g = 1; g <= fk.Length; g++)
            if (fk[g - 1].wasPressedThisFrame)
            {
                bool on = !GroupOn(g);
                foreach (var b in boothBlocks) if (BlockGroup(b) == g) b.SetActive(on);
                show = true;
            }
        if (repairs != null)                                       // REP-1 판정 손잡이: 받은 숫자를 Tuning.RepairTime · REP_BREAK_EVERY 에
        {
            bool any = true;
            if (kb.f2Key.wasPressedThisFrame)
            {
                var r = Repairable.All.Where(x => !x.broken).OrderBy(x => Vector3.Distance(x.focus, player.transform.position)).FirstOrDefault();
                if (r != null) r.Break();
            }
            else if (kb.f3Key.wasPressedThisFrame) Repairable.timeMul /= 1.25f;
            else if (kb.f4Key.wasPressedThisFrame) Repairable.timeMul *= 1.25f;
            else if (kb.f11Key.wasPressedThisFrame) repairs.breakEvery = Mathf.Max(10f, repairs.breakEvery - 30f);
            else if (kb.f12Key.wasPressedThisFrame) repairs.breakEvery += 30f;
            else any = false;
            if (any) show = true;
        }
        if (Crevice.All.Count > 0)                                 // R2b 판정 손잡이: 받은 숫자를 Tuning.SQUEEZE_S · SQUEEZE_TURN_DEG 에
        {
            float ds = kb.f8Key.wasPressedThisFrame ? 0.25f : kb.f7Key.wasPressedThisFrame ? -0.25f : 0f;
            float dt = kb.f10Key.wasPressedThisFrame ? 10f : kb.f9Key.wasPressedThisFrame ? -10f : 0f;
            player.squeezeS = Mathf.Clamp(player.squeezeS + ds, 0.5f, 8f);
            player.squeezeTurnDeg = Mathf.Clamp(player.squeezeTurnDeg + dt, 0f, 90f);
            if (ds != 0f || dt != 0f) show = true;
        }
    }

    string CreviceLine() => Crevice.All.Count == 0 ? "" :
        $"\nsqueeze into a closed crevice {player.squeezeS:0.00} s (SQUEEZE_S {Tuning.SQUEEZE_S:0.00}) [F7 F8] · through crevices {player.SqueezeTime(Crevice.All.Where(c => c.through).Min(c => c.Length)):0.0}~{player.SqueezeTime(Crevice.All.Where(c => c.through).Max(c => c.Length)):0.0} s · side turn {player.squeezeTurnDeg:0}° (SQUEEZE_TURN_DEG {Tuning.SQUEEZE_TURN_DEG:0}) [F9 F10] · E {(player.Squeezing ? "SQUEEZING" : Crevice.Find(player.transform.position, player.transform.forward, out _, out _) ? "READY" : "-")}";

    // MINE-1 판정 손잡이: 받은 숫자를 Tuning.MINE_TEMPO · MINE_SLIP_CHANCE · MINE_LOOK_YAW_DEG 에. 숫자패드였다 → 텐키리스라 비어 있는 키로(CLAUDE.md)
    void MineKeys(Keyboard kb)
    {
        if (pickaxe == null) return;
        bool shift = kb.shiftKey.isPressed;                         // Shift+↓ ↑ 는 캐기 동작의 머리 흔들림 (MINE-2)
        if (kb.downArrowKey.wasPressedThisFrame && !shift) { pickaxe.tempo = Mathf.Max(0.3f, pickaxe.tempo * 0.9f); show = true; }
        if (kb.upArrowKey.wasPressedThisFrame && !shift) { pickaxe.tempo = Mathf.Min(3f, pickaxe.tempo * 1.1f); show = true; }
        if (kb.downArrowKey.wasPressedThisFrame && shift) { pickaxe.bobMul = Mathf.Max(0f, Mathf.Round(pickaxe.bobMul * 10f - 1f) / 10f); show = true; }
        if (kb.upArrowKey.wasPressedThisFrame && shift) { pickaxe.bobMul = Mathf.Min(1f, Mathf.Round(pickaxe.bobMul * 10f + 1f) / 10f); show = true; }
        if (kb.deleteKey.wasPressedThisFrame) { pickaxe.slipChance = Mathf.Max(0f, Mathf.Round((pickaxe.slipChance - 0.1f) * 100f) / 100f); show = true; }
        if (kb.backspaceKey.wasPressedThisFrame) { pickaxe.slipChance = Mathf.Min(1f, Mathf.Round((pickaxe.slipChance + 0.1f) * 100f) / 100f); show = true; }
        if (kb.backquoteKey.wasPressedThisFrame) { pickaxe.lookYaw = Mathf.Max(0f, pickaxe.lookYaw - 10f); show = true; }
        if (kb.tabKey.wasPressedThisFrame) { pickaxe.lookYaw = Mathf.Min(180f, pickaxe.lookYaw + 10f); show = true; }
    }

    // ORE-1 판정 손잡이: 광석(결 덩이 coal_lump · 캘 덩이 coal_fresh) 반짝임 = 거칠기 ÷ oreShine. 받은 숫자를 Tuning.ORE_SHINE 에
    [System.NonSerialized] public float oreShine = Tuning.ORE_SHINE;
    System.Collections.Generic.List<(Material m, float rough0)> oreMats;
    void OreKeys(Keyboard kb)
    {
        if (!kb.shiftKey.isPressed || !(kb.commaKey.wasPressedThisFrame || kb.periodKey.wasPressedThisFrame)) return;
        oreShine = Mathf.Clamp(oreShine * (kb.periodKey.wasPressedThisFrame ? 1.25f : 1f / 1.25f), 0.2f, 5f);
        ApplyOreShine();
        show = true;
    }
    public void ApplyOreShine()                                  // 광석 조각 · 포켓 재질을 한 번 복제해(에셋을 안 바꾸게) 거칠기만 바꾼다
    {
        if (oreMats == null)
        {
            oreMats = new System.Collections.Generic.List<(Material, float)>();
            var map = new System.Collections.Generic.Dictionary<Material, Material>();
            var faces = GameObject.Find("OreFaces");
            var rs = FindObjectsByType<OrePocket>(FindObjectsInactive.Exclude).SelectMany(p => p.GetComponentsInChildren<Renderer>())
                .Concat(faces != null ? faces.GetComponentsInChildren<Renderer>() : new Renderer[0]);
            foreach (var r in rs)
            {
                var ms = r.sharedMaterials;
                for (int i = 0; i < ms.Length; i++)
                {
                    if (ms[i] == null || !(ms[i].name.Contains("coal_lump") || ms[i].name.Contains("coal_fresh"))) continue;
                    if (!map.TryGetValue(ms[i], out var c)) { c = new Material(ms[i]); map[ms[i]] = c; oreMats.Add((c, c.GetFloat("roughnessFactor"))); }
                    ms[i] = c;
                }
                r.sharedMaterials = ms;
            }
        }
        foreach (var (m, r0) in oreMats) m.SetFloat("roughnessFactor", Mathf.Clamp(r0 / oreShine, 0.05f, 1f));
    }

    // SND-P 판정 손잡이: 평소 콱 크기. 받은 숫자를 Tuning.HIT_VOLUME 에 — 너무 키우면 검사 pick_soft_like_walk(걷기의 ½~2 배)가 FAIL
    void HitKeys(Keyboard kb)
    {
        var fx = MiningFx.I;
        if (fx == null || !kb.shiftKey.isPressed || !(kb.leftBracketKey.wasPressedThisFrame || kb.rightBracketKey.wasPressedThisFrame)) return;
        fx.hitVolume = Mathf.Clamp(Mathf.Round(fx.hitVolume * (kb.rightBracketKey.wasPressedThisFrame ? 1.1f : 0.9f) * 1000f) / 1000f, 0.02f, 1f);
        show = true;
    }

    static string HitLine() => MiningFx.I == null ? "" :
        $"\nhit vol {MiningFx.I.hitVolume:0.000} (HIT_VOLUME {Tuning.HIT_VOLUME:0.000}) [Shift+[ Shift+]]  heard to: strike {Tuning.MINE_NOISE_SOFT:0} m, slip {Tuning.NOISE_PICK:0} m";

    string OreLine() => oreMats == null && GameObject.Find("OreFaces") == null ? "" :
        $"\nore shine x{oreShine:0.00} (ORE_SHINE {Tuning.ORE_SHINE:0.00}) [Shift+, Shift+.]";

    string MineLine() => pickaxe == null ? "" :
        $"\nmine {(pickaxe.Mining ? $"{pickaxe.minePhase.ToUpper()} {(pickaxe.mineCrouch ? "crouch" : "stand")}" : "-")}  tempo x{pickaxe.tempo:0.00} (stand bundle {StandBundle(pickaxe.tempo):0.0} s) [↓ ↑]  slip {pickaxe.slipChance * 100f:0}% [Del Bksp]  look ±{pickaxe.lookYaw:0}° [` Tab]  strike {pickaxe.softNoise:0} m · slip {Tuning.NOISE_PICK:0} m  bundles {pickaxe.bundles} slips {pickaxe.slips} regrips {pickaxe.regrips}" +
        $"\nmine motion {(pickaxe.MotionOn ? pickaxe.motion.clipName : "none (code poses)")}  head bob {pickaxe.bobMul * 100f:0}% (MINE_MOTION_BOB {Tuning.MINE_MOTION_BOB * 100f:0}%) [Shift+↓ Shift+↑]";

    static float StandBundle(float tempo)
    {
        float s = 0f;
        foreach (float x in Tuning.MINE_STRIKE_STAND) s += x;
        return tempo * (s * Tuning.MINE_STRIKES_STAND + Tuning.MINE_PRY_STAND + Tuning.MINE_FALL_S + Tuning.MINE_SCRAPE_STAND);
    }

    string RepairLine() => repairs == null ? "" :
        $"\nrepair broken {Repairable.All.Count(r => r.broken)}/{Repairable.All.Count} fixed {Repairable.FixedCount}  {(player.Repairing ? $"FIXING {player.repairing.kind} {player.repairing.progress * 100f:0}%" : "")}  time x{Repairable.timeMul:0.00} [F3 F4] (timber {Tuning.RepairTime("timber") * Repairable.timeMul:0.0} s)  break every {repairs.breakEvery:0} s [F11 F12]  break nearest [F2]   money ore {Economy.Ore:0} + repair {Economy.Repair:0} = {Economy.Total:0}";

    string BoothLine() => boothLights.Length == 0 ? "" :
        $"\nbooth lights {boothLights[0].intensity:0.00} (BOOTH_LIGHT_ENERGY {Tuning.BOOTH_LIGHT_ENERGY:0.00}) [ScrLk Pause]   blocks west {(GroupOn(1) ? "X" : "o")} east {(GroupOn(2) ? "X" : "o")} [F5 F6] (X = 막힘: 서쪽 ① 채탄장·바깥 고리 · 동쪽 ③ 노보리·바깥 고리 — 둘 다 X = 가운데만)";

    [System.NonSerialized] public bool walkPreview;        // U: 세운 괴물이 걸어오기를 되풀이 (검사도 본다)
    [System.NonSerialized] public bool previewOn = true;   // 사보타주 nopreview 가 끈다 (고치기 전: U 가 세운 괴물에 안 먹던 상태)

    // 괴물을 내 앞 m 에 나를 보게 세운다
    void PlaceAhead(float m)
    {
        Vector3 f = player.transform.forward; f.y = 0f; f.Normalize();
        stalker.Teleport(player.transform.position + f * m, player.transform.eulerAngles.y + 180f);
    }

    static string LureLine(StalkerLook lk) =>        // m3-③ M1 램프 미끼
        lk.HasLamp ? $"lure lamp {lk.LampNow:0.0} eyes {lk.EyeNow:0.0}  lamp goes out under {lk.lureOffM:0} m [; ']  lamp glow x{lk.lampEmission:0.00} [/ \\]" : "lure: no lamp glass on this body";

    void OnGUI()
    {
        if (!show || fog == null)
            return;
        string monster = stalker == null ? "" :
            $"\nstalker {(stalker.enabled ? stalker.state.ToString() : "OFF [0]")}  sense {stalker.sense}  heard {stalker.lastHeard}  dist {stalker.DistToPlayer:0.0} m  spots {stalker.spotsVisited}  caught {stalker.catches}  hp {stalker.hp:0} hits {stalker.hitsTaken} hidden {stalker.hiddenLeft:0} s   EAR x{stalker.earMul:0.0} (NOISE_PICK {Tuning.NOISE_PICK:0} m) · EYE {Tuning.STALKER_EYE_M:0} m {Tuning.STALKER_EYE_DEG:0}° · LIGHT {Tuning.STALKER_LIGHT_M:0} m" +
            (stalker.GetComponentInChildren<StalkerAnim>() is StalkerAnim an ? $"\nanim {an.Current} x{an.Rate:0.00} at {an.Speed:0.0} m/s{(stalker.enabled ? "" : "   [N] next clip")}   wander gait {StalkerAnim.GaitName(an.gait)} [U]   jaw {an.JawDeg:0}° (roar/catch {an.jawWideDeg:0}° [H J])\nhead test {StalkerAnim.HeadTestName(an.headTest)} [G]  face {an.HeadYaw:0}° (max {an.headYawMax:0}° [T Y])  tilt {an.HeadTiltNow:0}° (listen {an.headTilt:0}° [O P])\nneck out {an.NeckOutNow * 100f * Tuning.STALKER_MODEL_SCALE:0} cm in game (model {an.NeckOutNow * 100f:0} of {an.neckWant * 100f:0} cm [Z X], max {Tuning.STALKER_NECK_OUT_MAX_M * 100f:0})  full out in {an.neckOutS:0.00} s [C B]{(walkPreview ? "  WALK-IN PREVIEW ([9] stop)" : "")}" : "") +
            (stalker.GetComponentInChildren<StalkerLook>() is StalkerLook lk ? $"\nskin relief x{lk.normalScale:0.00} [7 8]   rough x{lk.roughMul:0.00} [, .]   eye glow {lk.eyeEmission:0.00} [k l]   neck red {lk.neckRed:0.0} [I M] bright x{lk.neckBright:0.00} [Q R]\n{LureLine(lk)}   [9] freeze monster in front of me · [0] on/off" : "");
        GUI.Label(new Rect(10, 10, 1100, 330),
            $"{fps:0} fps  {Screen.width}x{Screen.height}\n" +
            $"volumetric fog {(fog.enabled.value ? "ON" : "OFF")}  density {fog.density.value:0.#####}   [V] [ [ ] ]\n" +
            $"lamp {(lamp.lampOn ? "ON" : "OFF")}  intensity {lamp.energy:0.#}   [F] [ - = ]   dark adapt {lamp.adapt:0.00}  DARK_ADAPT_AMBIENT {lamp.darkAdaptAmbient:0.##}   [ 1 2 ]\n" +
            $"{player.stance}  stamina {player.stamina:0}{(player.exhausted ? " EXHAUSTED" : "")}  nod x{(player.stamina <= Tuning.STAMINA_SOON ? Tuning.LAMP_BOB_SOON_MUL : 1f):0}   [ 5 6 ]   ore {player.ore}  noise {(miningHud == null ? "-" : $"{miningHud.LastKind} {miningHud.LastRadius:0} m {miningHud.Left:0.0} s")}   pick {(pickaxe == null ? "-" : $"{pickaxe.durability:0}/{Tuning.PICK_DURABILITY_MAX:0} {(pickaxe.hasPick ? "held" : pickaxe.Broken ? "BROKEN" : "thrown [E]")}")}   [ 3 4 ]   [F1] hide" + MineLine() + HitLine() + OreLine() + BoothLine() + RepairLine() + ArtLook.Line() + CreviceLine() + monster);
    }
}
