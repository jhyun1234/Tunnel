using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.InputSystem;

// GAME-1 감독 (제안서 docs/제안서_GAME1_MAP4에서_놀기.md 3절, 사용자 승인 10-03 "출발값으로"). 괴물(그것)을 판 진행에 맞춰 숨은 굴로 데려온다.
//   단계 게이지 = 일하며 낸 소리 (팀에 하나 — 사람이 아니라 자리 · 몫 기준): 콱 · '쨍' = 덩이 값 × 반경 ÷ 18 · 던진 곡괭이 착지 = 덩이 반 개 · 발소리 0.
//   깔끔하게 몫을 다 채우면 100, 25 마다 한 단계 (덩이 값 = 100 ÷ BOOTH_QUOTA). 콱 한 번마다 조금씩 오른다.
//   단계 ≥ 1: 간격(STAGE_EVERY_S)마다 마지막으로 게이지가 오른 자리에서 굴 길이로 단계 거리(STAGE_EXIT_M) 안의 출구 — 사람에게서 8 m 넘게 —
//   로 숨은 굴을 지나(초당 TUNNEL_SPEED) 와서, EMERGE_WARN_S 동안 그 출구에서 돌가루가 떨어진 뒤 나온다. 보고 있어도 나온다(10-04 판정 1 "나오는 게 보이게" — 그 전엔 안 보이는 출구만 · 눈을 뗄 때까지 기다림).
//   나와서는 그 자리를 소리 들었을 때 걸음(STALKER_SPEED_INVESTIGATE)으로 보러 가고(판정 통과 감각 그대로) LINGER_S 동안 못 찾으면 아무도 못 볼 때 숨은 굴로 들어가 가장 가까운 집(붕락 방 · 옛 채굴 빈터 · 괴물의 굴)으로.
//   철수(곡괭이 열네 대)는 괴물 스스로 — 90 초 뒤 사람에게서 가장 먼 집에서 나온다(Stalker.cracks = 집 셋).
// 판정 키 (숫자패드 안 씀 · F1 줄에 값): Alt+1 2 간격 배율 · Alt+3 4 출구 거리 배율 · Alt+5 6 소리 배율 · Alt+7 8 숨은 굴 빠르기 · Alt+9 지금 부르기 · Alt+0 한 단계 올리기
public class Director : MonoBehaviour
{
    public enum Phase { Home, Hiding, Tunnel, Warn, Out, Return, Back }
    public class Exit { public string name; public Vector3 mouth, stand, face; public bool ceiling; }

    public static Director I;
    public Map4 map; public Stalker s; public Player player; public Camera cam;
    public readonly List<Exit> exits = new List<Exit>();
    public Vector3[] homes = new Vector3[0];
    [System.NonSerialized] public float gauge, everyMul = 1f, exitMul = 1f, noiseMul = 1f, tunnelSpeed = Tuning.TUNNEL_SPEED;
    [System.NonSerialized] public Phase phase = Phase.Home;
    [System.NonSerialized] public Vector3 lastWork;
    [System.NonSerialized] public Exit target;
    [System.NonSerialized] public float targetPath, rest, warnFor, phaseT;
    [System.NonSerialized] public int approaches, emergedSeen, warnBursts;   // 검사가 본다
    static bool SabFlatNoise => Map4.Sab("flatnoise"); static bool SabStepPile => Map4.Sab("steppile"); static bool SabJumpGauge => Map4.Sab("jumpgauge"); static bool SabNoStage => Map4.Sab("nostage");   // 검사 사보타주
    static bool SabHideExit => Map4.Sab("hideexit"); static bool SabSlowSend => Map4.Sab("slowsend"); static bool SabNoShake => Map4.Sab("noshake"); static bool SabChasePlayer => Map4.Sab("chaseplayer"); static bool SabFarExit => Map4.Sab("farexit"); static bool SabHomeExit => Map4.Sab("homeexit");
    public static float Lump => 100f / Tuning.BOOTH_QUOTA;
    public int Stage => SabNoStage ? 0 : Mathf.Min(Tuning.STAGE_EVERY_S.Length - 1, Mathf.FloorToInt(gauge / Tuning.GAUGE_STEP + 1e-4f));
    public float Every => Tuning.STAGE_EVERY_S[Stage] * everyMul;
    public float ExitMax => Tuning.STAGE_EXIT_M[Stage] * exitMul;

    Vector3 home; float t, dustT, jumpAcc; int lastStage, lastOre, sentFrame = -9; bool worked; Stalker.State lastSt;
    static readonly RaycastHit[] buf = new RaycastHit[16];
    const int SeeMask = ~((1 << 2) | (1 << Pickaxe.ViewModelLayer));   // 자갈 · 광석(Ignore Raycast) · 곡괭이 뷰모델은 시선을 안 막는다

    public void Begin(Map4 m, Stalker st, Player p, Camera c)
    {
        I = this; map = m; s = st; player = p; cam = c; lastWork = p.transform.position;
        homes = new[] { ("K", -56f, -30f), ("M", -78f, -64f), ("z9", 125f, -66f) }.Select(h => OnNav(m.Area(h.Item1) is Transform a ? a.position : m.Plan(h.Item2, h.Item3), 8f)).ToArray();   // 집 = 붕락 방 · 옛 채굴 빈터 · 괴물의 굴 (방 가운데)
        foreach (var tr in m.GetComponentsInChildren<Transform>(true))
        {
            bool wall = tr.name.StartsWith("MGAP_"), ceil = tr.name.StartsWith("CHIM_");
            if (!wall && !ceil) continue;
            var e = new Exit { name = tr.name, mouth = tr.position, ceiling = ceil };
            if (wall)
            {
                var inT = FabTest.Node(m.gameObject, "MGAPIN_" + tr.name.Substring(5));       // 입 안 1 m — 바깥 = 입 − 안
                e.face = inT != null ? Flat(tr.position - inT.position).normalized : Vector3.forward;
                e.stand = OnNav(tr.position + e.face * 1.2f - Vector3.up * 1.2f, 3f);
            }
            else { e.face = Vector3.down; e.stand = OnNav(tr.position + Vector3.down * 3f, 8f); }   // 천장 구멍: 밑 바닥
            if (NavMesh.SamplePosition(e.stand, out _, 0.5f, NavMesh.AllAreas)) exits.Add(e);
            else Debug.Log($"DIRECTOR exit {tr.name} has no monster floor in front — skipped");
        }
        if (SabFarExit) exits.RemoveAll(e => !e.name.EndsWith("_K") && !e.name.EndsWith("_M"));   // 검사: 집 둘레 출구만 (석탄 자리에서 멀다)
        if (SabHomeExit) { var z6 = m.Area("z6"); Vector3 c0 = z6 != null ? z6.position : p.transform.position; exits.Add(new Exit { name = "MGAP_SABHOME", mouth = c0 + Vector3.up * 1.2f, stand = OnNav(c0, 3f), face = Vector3.forward }); }   // 검사: 승강장 안 출구
        home = homes[2];
        if (s != null)
        {
            s.zMin = s.zMax = 0f; s.cracks = homes; s.homePos = home; s.restartPos = p.transform.position;
            s.GetComponent<CharacterController>().radius = Tuning.MAP4_STALKER_R;   // 길찾기 바닥과 같은 몸 (BuildMap4)
            s.Teleport(home, 0f); s.hasAnchor = true; s.anchor = home;
        }
        Debug.Log($"DIRECTOR begin · exits {exits.Count} ({string.Join(" ", exits.Select(e => e.name))}) · homes {string.Join(" ", homes.Select(h => h.ToString("F0")))} · lump {Lump:0.0} · seed {m.seed} rich {m.rich}");
    }

    void OnEnable() => NoiseBus.Made += OnNoise;
    void OnDisable() { NoiseBus.Made -= OnNoise; if (I == this) I = null; }

    // 일하며 낸 소리만 쌓는다. 자리는 사람이 아니라 소리 난 곳
    void OnNoise(Vector3 pos, float r, string kind, object who)
    {
        float lumps;
        if (kind == "pick" || kind == "pick_slip") lumps = (SabFlatNoise ? Tuning.MINE_NOISE_SOFT : r) / Tuning.GAUGE_STRIKE_REF_M;
        else if (kind.StartsWith("pick_land")) lumps = Tuning.GAUGE_LAND_LUMPS;
        else if (kind == "step" && SabStepPile) lumps = r / Tuning.GAUGE_STRIKE_REF_M;
        else return;
        lastWork = pos; worked = true;
        if (SabJumpGauge) { jumpAcc += lumps; if (jumpAcc < 1f - 1e-3f) return; lumps = jumpAcc; jumpAcc = 0f; }   // 검사: 덩이마다 한 번에 뛴다 (옛 안)
        gauge += lumps * Lump * noiseMul;
    }

    void Update()
    {
        Keys();
        if (s == null || !s.isActiveAndEnabled) return;
        float dt = Time.deltaTime; int st = Stage;
        if (st != lastStage) { Debug.Log($"DIRECTOR {T} · stage {lastStage} -> {st} (gauge {gauge:0.0})"); lastStage = st; }
        if (player.ore != lastOre) { Debug.Log($"DIRECTOR {T} · ore {player.ore}/{Tuning.BOOTH_QUOTA} near {Near(player.transform.position)}"); lastOre = player.ore; }   // 판정 로그(-logFile): 언제 · 어디서 캤나
        if (s.state != lastSt)                                                                                        // 판정 로그: 괴물이 듣고 · 보고 · 쫓고 · 잡은 때
        {
            string why = s.state == Stalker.State.Investigate ? (Time.frameCount - sentFrame <= 1 ? " (sent)" : s.LightChase ? " (saw the lamp)" : $" (heard {s.lastHeard})") : s.state == Stalker.State.Alert ? $" (sense {s.sense})" : "";
            Debug.Log($"DIRECTOR {T} · monster {lastSt} -> {s.state}{why} · {Vector3.Distance(s.transform.position, player.transform.position):0} m from the player");
            lastSt = s.state;
        }
        if (s.state == Stalker.State.Hidden && !s.held) { phase = Phase.Home; rest = 0f; return; }   // 철수 중 — 괴물 스스로 90 초 뒤 먼 집에서
        bool idle = s.state == Stalker.State.Wander;
        switch (phase)
        {
            case Phase.Home:
                if (idle) { rest += dt; s.hasAnchor = true; s.anchor = NearestHome(s.transform.position); }   // 쫓기 · 살피기 중엔 안 센다
                if (st >= 1 && rest >= Every) Call(false);
                break;
            case Phase.Hiding:                                   // 아무도 못 볼 때 벽 속으로
                if (!idle) { phase = Phase.Out; phaseT = 0f; break; }   // 기다리는 사이 무엇을 듣거나 봤다 — 그대로 둔다
                if (!SeenBody()) { s.Hold(); t = Mathf.Max(1.5f, Vector3.Distance(s.transform.position, target.mouth) / tunnelSpeed); phase = Phase.Tunnel; Debug.Log($"DIRECTOR {T} · into the wall -> {target.name}, tunnel {t:0} s"); }
                break;
            case Phase.Tunnel:
                t -= dt;
                if (t <= 0f)
                {
                    var again = Choose(out float len2);                                           // 굴을 지나는 20~40 초 사이 사람은 다른 구역으로 간다 — 나오기 직전에 '지금' 마지막으로 일한 자리로 다시 고른다 (10-04 map4meet: 나왔을 때 사람과 71~181 m)
                    if (again != null && again != target) Debug.Log($"DIRECTOR {T} · re-pick {target.name} -> {again.name} (last work {WorkAt})");
                    if (again != null) { target = again; targetPath = len2; }
                    phase = Phase.Warn; t = SabNoShake ? 0f : Tuning.EMERGE_WARN_S; warnFor = 0f; dustT = 0f;
                }
                break;
            case Phase.Warn:                                     // 돌가루 → 나온다 (보고 있어도)
                t -= dt; warnFor += dt; Dust(dt);
                if (t > 0f) break;
                bool seen = Seen(target.stand + Vector3.up * 1.2f) || Seen(target.mouth);
                if (seen && SabHideExit) break;                  // 검사: 옛 규칙 (보고 있으면 눈을 뗄 때까지 안 나옴)
                if (seen) emergedSeen++;
                Vector3 look = target.ceiling ? Flat(lastWork - target.stand) : target.face;
                s.Release(target.stand, look.sqrMagnitude > 1e-4f ? Quaternion.LookRotation(look).eulerAngles.y : 0f);
                s.hasAnchor = true; s.anchor = lastWork; s.SendTo(lastWork, SabSlowSend ? Tuning.STALKER_SPEED_SEARCH : Tuning.STALKER_SPEED_INVESTIGATE);   // 소리 들었을 때와 같은 걸음 (10-04 판정 1: 살피는 걸음 2.5 는 "두리번")
                phase = Phase.Out; phaseT = 0f; approaches++; sentFrame = Time.frameCount;
                Debug.Log($"DIRECTOR {T} · out #{approaches} at {target.name} · stage {st} · last work {WorkAt} · path from last work {targetPath:0} m (max {(ExitMax > 0f ? ExitMax.ToString("0") : "nearest")}) · to player {Vector3.Distance(target.stand, player.transform.position):0} m · warned {warnFor:0.0} s · in view {seen}");
                break;
            case Phase.Out:                                      // 판정 통과 감각으로 찾는다 — 놓치고 배회로 LINGER_S 지나면 돌아간다
                phaseT = idle ? phaseT + dt : 0f;
                if (phaseT >= Tuning.LINGER_S) phase = Phase.Return;
                break;
            case Phase.Return:
                if (!idle) { phase = Phase.Out; phaseT = 0f; break; }
                if (SeenBody()) break;
                home = NearestHome(s.transform.position); t = Mathf.Max(1.5f, Vector3.Distance(s.transform.position, home) / tunnelSpeed);
                s.Hold(); phase = Phase.Back;
                Debug.Log($"DIRECTOR {T} · found nobody for {Tuning.LINGER_S:0} s -> into the wall, home {HomeName(home)}");
                break;
            case Phase.Back:
                t -= dt;
                if (t > 0f || Seen(home + Vector3.up * 1.2f)) break;
                s.Release(home, 0f); s.hasAnchor = true; s.anchor = home;
                phase = Phase.Home; rest = 0f;
                Debug.Log($"DIRECTOR {T} · back home {HomeName(home)} · next call in {(Stage >= 1 ? Every.ToString("0") + " s" : "- (stage 0)")}");
                break;
        }
    }

    // 검사: 괴물을 집(괴물의 굴)에 쉬는 상태로 되돌린다 (아무 단계 · 아무 자리에서)
    public void ForceHome()
    {
        if (s == null) return;
        s.Hold(); home = homes[2]; s.Release(home, 0f); s.hasAnchor = true; s.anchor = home;
        phase = Phase.Home; rest = 0f; target = null;
    }

    // 지금 부른다 (간격이 됐다 · Alt+9 · 검사). 출구가 없으면 반 간격 뒤 다시
    public bool Call(bool force)
    {
        if (phase != Phase.Home || s == null || s.state != Stalker.State.Wander) return false;
        target = Choose(out targetPath);
        if (target == null) { rest = force ? 0f : Every * 0.5f; Debug.Log($"DIRECTOR {T} · no exit to use (all unreachable or within 8 m)"); return false; }
        phase = Phase.Hiding; rest = 0f;
        Debug.Log($"DIRECTOR {T} · call{(force ? " (forced)" : "")} · stage {Stage} · exit {target.name} {targetPath:0} m from last work ({WorkAt}) · player {Vector3.Distance(player.transform.position, lastWork):0} m from last work");
        return true;
    }

    // 마지막으로 일한 자리에서 굴 길이로 단계 거리 안의 출구 가운데 가장 먼 것(단계가 오를수록 가까워진다) — 없으면 가장 가까운 것
    public Exit Choose(out float len)
    {
        Vector3 from = SabChasePlayer ? player.transform.position : lastWork;
        float max = ExitMax; len = -1f;
        var c = exits.Where(e => (!SabHideExit || !Seen(e.mouth) && !Seen(e.stand + Vector3.up * 1.2f)) && Flat(e.stand - player.transform.position).magnitude >= Tuning.EXIT_MIN_PLAYER_M)
            .Select(e => (e, d: PathLen(from, e.stand))).Where(x => x.d >= 0f).OrderBy(x => x.d).ToList();
        if (c.Count == 0) return null;
        var pick = max > 0f && c.Any(x => x.d <= max) ? c.Last(x => x.d <= max) : c[0];
        len = pick.d;
        return pick.e;
    }

    void Dust(float dt)
    {
        if (SabNoShake || MiningFx.I == null) return;
        dustT -= dt;
        if (dustT > 0f) return;
        dustT = 0.5f; warnBursts++;
        Vector3 at = target.ceiling ? target.mouth + Vector3.down * 0.3f : target.mouth + target.face * 0.2f;
        MiningFx.I.Dust(at, target.ceiling ? Vector3.down : target.face, 1.5f);
        MiningFx.I.Chips(at, target.ceiling ? Vector3.down : target.face, 3);
    }

    // 사람(카메라) 화면에 들고, EXIT_SEEN_M 안이고, 가리는 것이 없으면 보인다
    public bool Seen(Vector3 p)
    {
        if (cam == null) return false;
        var v = cam.WorldToViewportPoint(p);
        if (v.z <= 0.05f || v.z > Tuning.EXIT_SEEN_M || v.x < -0.1f || v.x > 1.1f || v.y < -0.1f || v.y > 1.1f) return false;
        Vector3 o = cam.transform.position, d = p - o; float L = d.magnitude;
        int n = Physics.RaycastNonAlloc(o, d / L, buf, Mathf.Max(0f, L - 0.3f), SeeMask, QueryTriggerInteraction.Ignore);
        for (int i = 0; i < n; i++)
        {
            var tr = buf[i].collider.transform;
            if (!tr.IsChildOf(player.transform) && !(s != null && tr.IsChildOf(s.transform))) return false;   // 가렸다
        }
        return true;
    }
    bool SeenBody() => Seen(s.transform.position + Vector3.up) || Seen(s.transform.position + Vector3.up * 2f);

    Vector3 NearestHome(Vector3 p) => homes.OrderBy(h => (h - p).sqrMagnitude).First();

    // 판정 로그(-logFile) 글: 판 시작부터 초 · 가장 가까운 석탄 자리 · 집 이름
    static string T => $"t {Time.timeSinceLevelLoad:0}s";
    string WorkAt => worked ? Near(lastWork) : "start, no work yet";
    string Near(Vector3 p) { var c = map.coal.OrderBy(k => (k.slot.position - p).sqrMagnitude).FirstOrDefault(); return c == null ? "-" : $"{c.name.Replace("SLOT_Pocket_", "")} {Vector3.Distance(c.slot.position, p):0} m"; }
    string HomeName(Vector3 h) { int i = System.Array.IndexOf(homes, h); return i == 0 ? "K" : i == 1 ? "M" : i == 2 ? "z9" : "?"; }

    public static float PathLen(Vector3 a, Vector3 b)
    {
        var path = new NavMeshPath();
        if (!NavMesh.CalculatePath(OnNav(a, 4f), OnNav(b, 4f), NavMesh.AllAreas, path) || path.status != NavMeshPathStatus.PathComplete) return -1f;
        float L = 0f; for (int i = 1; i < path.corners.Length; i++) L += Vector3.Distance(path.corners[i - 1], path.corners[i]);
        return L;
    }
    public static Vector3 OnNav(Vector3 p, float r) => NavMesh.SamplePosition(p, out NavMeshHit h, r, NavMesh.AllAreas) ? h.position : p;
    static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0f, v.z);

    void Keys()
    {
        var kb = Keyboard.current;
        if (kb == null || !kb.altKey.isPressed) return;
        float R(float v) => Mathf.Round(v * 100f) / 100f;
        if (kb.digit1Key.wasPressedThisFrame) everyMul = R(everyMul / 1.25f);
        else if (kb.digit2Key.wasPressedThisFrame) everyMul = R(everyMul * 1.25f);
        else if (kb.digit3Key.wasPressedThisFrame) exitMul = R(exitMul / 1.25f);
        else if (kb.digit4Key.wasPressedThisFrame) exitMul = R(exitMul * 1.25f);
        else if (kb.digit5Key.wasPressedThisFrame) noiseMul = R(noiseMul / 1.25f);
        else if (kb.digit6Key.wasPressedThisFrame) noiseMul = R(noiseMul * 1.25f);
        else if (kb.digit7Key.wasPressedThisFrame) tunnelSpeed = Mathf.Max(1f, tunnelSpeed - 1f);
        else if (kb.digit8Key.wasPressedThisFrame) tunnelSpeed += 1f;
        else if (kb.digit9Key.wasPressedThisFrame) Call(true);
        else if (kb.digit0Key.wasPressedThisFrame) gauge = (Stage + 1) * Tuning.GAUGE_STEP;
    }

    public string Line() =>
        $"\ndirector stage {Stage} (gauge {gauge:0}, {Tuning.GAUGE_STEP:0} a stage) · {phase} · next in {(Stage >= 1 && phase == Phase.Home ? Mathf.Max(0f, Every - rest).ToString("0") + " s" : "-")} (every {Every:0} s) · exit {(ExitMax > 0f ? "<= " + ExitMax.ToString("0") + " m" : "nearest")} · came {approaches} · good seam {map.rich} · ore {player.ore}/{Tuning.BOOTH_QUOTA}" +
        $"\n  [Alt+1 2] every x{everyMul:0.00}  [Alt+3 4] exit x{exitMul:0.00}  [Alt+5 6] noise x{noiseMul:0.00}  [Alt+7 8] tunnel {tunnelSpeed:0} m/s  [Alt+9] call now  [Alt+0] +1 stage";
}
