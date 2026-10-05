using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.InputSystem;

// GAME-1 감독 (제안서 docs/제안서_GAME1_MAP4에서_놀기.md 3절, 사용자 승인 10-03 "출발값으로" · 10-05 판정 3 ㉠ ㉡ ㉢). 괴물(그것)을 일하는 소리에 맞춰 숨은 굴로 데려온다.
//   단계 게이지 = 일하며 낸 소리 (팀에 하나 — 사람이 아니라 자리 · 몫 기준): 콱 · '쨍' = 덩이 값 × 반경 ÷ 18 · 던진 곡괭이 착지 = 덩이 반 개 · 발소리 0.
//   깔끔하게 몫을 다 채우면 100, 25 마다 한 단계 (덩이 값 = 100 ÷ BOOTH_QUOTA). 콱 한 번마다 조금씩 오른다.
//   부르기 ㉢: 게이지가 25 를 넘을 때마다(단계 5 뒤에도) 부를 일이 생긴다. 괴물이 어슬렁거리는 중(배회)이고 지난번 벽 속에 들어간 뒤 STAGE_EVERY_S(단계별 쉬는 최소 시간)만큼
//     어슬렁거렸으면 바로 부른다. 첫 곡괭이질 전에는 안 부른다(Alt+0 만 누른 판).
//   어디서든 ㉡: 괴물이 집에 있든 밖에 있든 아무도 못 볼 때 그 자리에서 벽 속으로 들어간다. 나온 뒤 집으로 돌아가지 않고 일한 자리 둘레를 돈다.
//   숨은 굴 ㉠: 거리와 상관없이 TUNNEL_S. 나오기 직전에 '지금' 마지막으로 일한 자리에서 굴 길이로 가장 가까운 출구를 고른다 — 사람 바로 옆이어도(10-05 판정 10: 단계 거리 상한 · 사람 8 m 규칙 뺌, 돌가루 소리 4 s 가 경고).
//   EMERGE_WARN_S 동안 그 출구에서 돌가루가 떨어진 뒤 나온다. 보고 있어도 나온다(10-04 판정 1). 나와서는 그 자리를 소리 들었을 때 걸음(STALKER_SPEED_INVESTIGATE)으로 보러 간다.
//   철수(곡괭이 열네 대)는 괴물 스스로 — 90 초 뒤 사람에게서 가장 먼 집에서 나온다(Stalker.cracks = 집 셋).
// 판정 키 (숫자패드 안 씀 · F1 줄에 값): Alt+1 2 쉬는 최소 시간 배율 · Alt+5 6 소리 배율 · Alt+7 8 숨은 굴 시간 −1 +1 s · Alt+9 지금 내 자리로 부르기 · Alt+0 한 단계 올리기
public class Director : MonoBehaviour
{
    public enum Phase { Free, Hiding, Tunnel, Warn }
    public class Exit { public string name; public Vector3 mouth, stand, face; public bool ceiling; }

    public static Director I;
    public Map4 map; public Stalker s; public Player player; public Camera cam;
    public readonly List<Exit> exits = new List<Exit>();
    public Vector3[] homes = new Vector3[0];
    [System.NonSerialized] public float gauge, everyMul = 1f, noiseMul = 1f, tunnelS = Tuning.TUNNEL_S;
    [System.NonSerialized] public Phase phase = Phase.Free;
    [System.NonSerialized] public Vector3 lastWork;
    [System.NonSerialized] public Exit target;
    [System.NonSerialized] public float targetPath, rest = 1e6f, warnFor;   // rest = 지난번 벽 속에 들어간 뒤 괴물이 어슬렁거린 시간 (첫 부름은 바로)
    [System.NonSerialized] public bool pending, worked;                     // pending = 25 를 넘었는데 아직 못 불렀다 · worked = 곡괭이질을 한 번이라도 했다
    [System.NonSerialized] public int approaches, calls, emergedSeen, warnBursts;   // 검사가 본다 (calls = 벽 속으로 들어간 수 · approaches = 나온 수)
    static bool SabFlatNoise => Map4.Sab("flatnoise"); static bool SabStepPile => Map4.Sab("steppile"); static bool SabJumpGauge => Map4.Sab("jumpgauge"); static bool SabNoStage => Map4.Sab("nostage");   // 검사 사보타주
    static bool SabHideExit => Map4.Sab("hideexit"); static bool SabSlowSend => Map4.Sab("slowsend"); static bool SabNoShake => Map4.Sab("noshake"); static bool SabChasePlayer => Map4.Sab("chaseplayer"); static bool SabFarExit => Map4.Sab("farexit"); static bool SabHomeExit => Map4.Sab("homeexit");
    static bool SabClockCall => Map4.Sab("clockcall"); static bool SabSlowTunnel => Map4.Sab("slowtunnel"); static bool SabHomeOnly => Map4.Sab("homeonly"); static bool SabNoRest => Map4.Sab("norest"); static bool SabNoWork => Map4.Sab("nowork");   // 10-05 판정 3 의 옛 규칙들
    static bool SabMuteEmerge => Map4.Sab("muteemerge");   // 검사: 나오는 소리 없음 (10-05 판정 7 전)
    static bool SabFarHere => Map4.Sab("farhere");         // 검사: 옛 Alt+9 (마지막 곡괭이 자리 기준)
    static bool SabKeep8m => Map4.Sab("keep8m"); static bool SabStageCap => Map4.Sab("stagecap");   // 검사: 판정 10 의 옛 규칙 (사람 8 m 안 틈 안 씀 · 단계 거리 안의 가장 먼 틈)
    static readonly float[] OldExitM = { 0f, 60f, 40f, 25f, 0f, 0f };   // stagecap 만 쓴다
    public static float Lump => 100f / Tuning.BOOTH_QUOTA;
    public int Stage => SabNoStage ? 0 : Mathf.Min(Tuning.STAGE_EVERY_S.Length - 1, Steps);
    public int Steps => Mathf.FloorToInt(gauge / Tuning.GAUGE_STEP + 1e-4f);   // 25 마다 하나 — 단계(최대 5)와 달리 끝이 없다
    public float Every => Tuning.STAGE_EVERY_S[Stage] * everyMul;

    float t, dustT, jumpAcc; int lastStage, lastSteps, lastOre, sentFrame = -9; Stalker.State lastSt;
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
        if (s != null)
        {
            s.zMin = s.zMax = 0f; s.cracks = homes; s.homePos = homes[2]; s.restartPos = p.transform.position;
            s.GetComponent<CharacterController>().radius = Tuning.MAP4_STALKER_R;   // 길찾기 바닥과 같은 몸 (BuildMap4)
            s.Teleport(homes[2], 0f); s.hasAnchor = true; s.anchor = homes[2];      // 판 시작 = 괴물의 굴 둘레
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
        if (Steps > lastSteps) pending = true;                                                                       // ㉢ 25 를 넘었다 — 부를 일
        lastSteps = Steps;
        if (player.ore != lastOre) { Debug.Log($"DIRECTOR {T} · ore {player.ore}/{Tuning.BOOTH_QUOTA} near {Near(player.transform.position)}"); lastOre = player.ore; }   // 판정 로그(-logFile): 언제 · 어디서 캤나
        if (s.state != lastSt)                                                                                        // 판정 로그: 괴물이 듣고 · 보고 · 쫓고 · 잡은 때
        {
            string why = s.state == Stalker.State.Investigate ? (Time.frameCount - sentFrame <= 1 ? " (sent)" : s.LightChase ? " (saw the lamp)" : $" (heard {s.lastHeard})") : s.state == Stalker.State.Alert ? $" (sense {s.sense})" : "";
            Debug.Log($"DIRECTOR {T} · monster {lastSt} -> {s.state}{why} · {Vector3.Distance(s.transform.position, player.transform.position):0} m from the player");
            if (lastSt == Stalker.State.Hidden && s.state == Stalker.State.Wander) s.anchor = s.transform.position;   // 철수 뒤 먼 집에서 다시 나왔다 — 그 둘레를 돈다
            lastSt = s.state;
        }
        if (s.state == Stalker.State.Hidden && !s.held) { phase = Phase.Free; rest = 0f; return; }   // 철수 중 — 괴물 스스로 90 초 뒤 먼 집에서
        bool idle = s.state == Stalker.State.Wander;
        if (idle) rest += dt;                                                                                         // 쫓기 · 살피기 중엔 안 센다
        switch (phase)
        {
            case Phase.Free:                                     // 집이든 밖이든 어슬렁거리는 중 — 부를 일이 있고 다 쉬었으면 부른다
                if (idle && (SabClockCall ? st >= 1 : pending) && (worked || SabNoWork) && (rest >= Every || SabNoRest)) Call(false);
                break;
            case Phase.Hiding:                                   // 아무도 못 볼 때 그 자리 벽 속으로
                if (!idle) { phase = Phase.Free; Debug.Log($"DIRECTOR {T} · call put off — the monster is busy ({s.state})"); break; }   // 기다리는 사이 무엇을 듣거나 봤다 — 부를 일은 남는다
                if (SeenBody()) break;
                s.Hold(); t = SabSlowTunnel ? Mathf.Max(1.5f, Vector3.Distance(s.transform.position, target.mouth) / 5f) : tunnelS;   // 검사 slowtunnel: 옛 5 m/s
                phase = Phase.Tunnel; rest = 0f; pending = false; calls++;
                Debug.Log($"DIRECTOR {T} · into the wall -> {target.name}, tunnel {t:0} s");
                break;
            case Phase.Tunnel:
                t -= dt;
                if (t <= 0f)
                {
                    var again = Choose(out float len2);                                           // 나오기 직전에 '지금' 마지막으로 일한 자리로 다시 고른다
                    if (again != null && again != target) Debug.Log($"DIRECTOR {T} · re-pick {target.name} -> {again.name} (last work {WorkAt})");
                    if (again != null) { target = again; targetPath = len2; }
                    phase = Phase.Warn; t = SabNoShake ? 0f : Tuning.EMERGE_WARN_S; warnFor = 0f; dustT = 0f;
                    Sound("emerge_dust_000", ref dustClip, Tuning.EMERGE_DUST_VOLUME); Sound("emerge_scrape_000", ref scrapeClip, Tuning.EMERGE_SCRAPE_VOLUME);   // 10-05 판정 7 · 8 (사용자 "B A A")
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
                Sound("emerge_burst_000", ref burstClip, Tuning.EMERGE_BURST_VOLUME);
                s.hasAnchor = true; s.anchor = lastWork; s.SendTo(lastWork, SabSlowSend ? Tuning.STALKER_SPEED_SEARCH : Tuning.STALKER_SPEED_INVESTIGATE);   // 소리 들었을 때와 같은 걸음 (10-04 판정 1: 살피는 걸음 2.5 는 "두리번")
                phase = Phase.Free; approaches++; sentFrame = Time.frameCount;
                Debug.Log($"DIRECTOR {T} · out #{approaches} at {target.name} · stage {st} · last work {WorkAt} · path from last work {targetPath:0} m · to player {Vector3.Distance(target.stand, player.transform.position):0} m · warned {warnFor:0.0} s · in view {seen}");
                break;
        }
    }

    // 검사: 괴물을 괴물의 굴에 다 쉰 상태로 되돌린다 (부를 일 없음 · 아무 단계 · 아무 자리에서)
    public void ForceHome()
    {
        if (s == null) return;
        s.Hold(); s.Release(homes[2], 0f); s.hasAnchor = true; s.anchor = homes[2];
        phase = Phase.Free; rest = 1e6f; pending = false; lastSteps = Steps; target = null;
    }

    // 지금 부른다 (부를 일이 있고 다 쉬었다 · Alt+9 · 검사). 출구가 없으면 쉬는 시간 반 뒤 다시
    public bool Call(bool force)
    {
        if (phase != Phase.Free || s == null || s.state != Stalker.State.Wander) return false;
        if (SabHomeOnly && !homes.Any(h => Flat(h - s.transform.position).magnitude < Tuning.STALKER_WANDER_CELLS * Tuning.GRID_CELL + 3f)) return false;   // 검사: 옛 규칙 (집에서 쉴 때만)
        target = Choose(out targetPath);
        if (target == null) { if (!force) rest = Every * 0.5f; Debug.Log($"DIRECTOR {T} · no exit to use (none reachable)"); return false; }
        phase = Phase.Hiding;
        Debug.Log($"DIRECTOR {T} · call{(force ? " (forced)" : "")} · stage {Stage} · exit {target.name} {targetPath:0} m from last work ({WorkAt}) · player {Vector3.Distance(player.transform.position, lastWork):0} m from last work · monster {Vector3.Distance(s.transform.position, player.transform.position):0} m from the player");
        return true;
    }

    // 판정 키 Alt+9: 지금 내가 선 자리에서 곡괭이질한 것처럼 부른다 — 나에게서 가장 가까운 틈, 나와서 내 자리로
    //   (10-05 판정 9 "괴물의 굴 앞에서 Alt+9 를 눌렀는데 곧바로 나오지 않는다" — 옛 Alt+9 는 마지막 곡괭이 자리 = 시작 자리 기준이었다)
    public bool CallHere()
    {
        if (phase != Phase.Free) return false;
        Vector3 keep = lastWork;
        if (!SabFarHere) lastWork = player.transform.position;
        if (Call(true)) return true;
        lastWork = keep;
        return false;
    }

    // 마지막으로 일한 자리에서 굴 길이로 가장 가까운 출구 — 사람 바로 옆이어도 (10-05 판정 10 "석탄을 캐고 난 뒤에 곧바로 괴물의 틈에서 크게 소리가 나면서")
    public Exit Choose(out float len)
    {
        Vector3 from = SabChasePlayer ? player.transform.position : lastWork;
        len = -1f;
        var c = exits.Where(e => (!SabHideExit || !Seen(e.mouth) && !Seen(e.stand + Vector3.up * 1.2f)) && (!SabKeep8m || Flat(e.stand - player.transform.position).magnitude >= 8f))
            .Select(e => (e, d: PathLen(from, e.stand))).Where(x => x.d >= 0f).OrderBy(x => x.d).ToList();
        if (c.Count == 0) return null;
        float cap = SabStageCap ? OldExitM[Stage] : 0f;                                  // 검사: 옛 규칙 (단계 거리 안의 가장 먼 것)
        var pick = cap > 0f && c.Any(x => x.d <= cap) ? c.Last(x => x.d <= cap) : c[0];
        len = pick.d;
        return pick.e;
    }

    void Dust(float dt)
    {
        if (SabNoShake || MiningFx.I == null) return;
        dustT -= dt;
        if (dustT > 0f) return;
        dustT = 0.5f; warnBursts++;
        MiningFx.I.Dust(MouthFx, target.ceiling ? Vector3.down : target.face, 1.5f);
        MiningFx.I.Chips(MouthFx, target.ceiling ? Vector3.down : target.face, 3);
    }
    Vector3 MouthFx => target.ceiling ? target.mouth + Vector3.down * 0.3f : target.mouth + target.face * 0.2f;   // 돌가루 · 소리가 나는 자리 (입 바로 앞)

    // 나오는 소리 — 출구 자리 3D, EMERGE_SOUND_M 안에서 들린다. 파일은 Assets/Audio/Emerge/Resources (SOURCES.txt)
    static AudioClip dustClip, scrapeClip, burstClip;
    void Sound(string name, ref AudioClip clip, float volume)
    {
        if (SabMuteEmerge) return;
        if (clip == null) { clip = Resources.Load<AudioClip>(name); if (clip == null) Debug.LogWarning($"DIRECTOR sound {name} is not in Resources"); }
        NoiseSound.Play3D(MouthFx, clip, volume, Tuning.EMERGE_SOUND_M);
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

    // 판정 로그(-logFile) 글: 판 시작부터 초 · 가장 가까운 석탄 자리
    static string T => $"t {Time.timeSinceLevelLoad:0}s";
    string WorkAt => worked ? Near(lastWork) : "start, no work yet";
    string Near(Vector3 p) { var c = map.coal.OrderBy(k => (k.slot.position - p).sqrMagnitude).FirstOrDefault(); return c == null ? "-" : $"{c.name.Replace("SLOT_Pocket_", "")} {Vector3.Distance(c.slot.position, p):0} m"; }

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
        else if (kb.digit5Key.wasPressedThisFrame) noiseMul = R(noiseMul / 1.25f);
        else if (kb.digit6Key.wasPressedThisFrame) noiseMul = R(noiseMul * 1.25f);
        else if (kb.digit7Key.wasPressedThisFrame) tunnelS = Mathf.Max(1f, tunnelS - 1f);
        else if (kb.digit8Key.wasPressedThisFrame) tunnelS += 1f;
        else if (kb.digit9Key.wasPressedThisFrame) CallHere();
        else if (kb.digit0Key.wasPressedThisFrame) gauge = (Stage + 1) * Tuning.GAUGE_STEP;
    }

    string CallState => phase != Phase.Free ? "on the way" : !pending ? $"at gauge {(Steps + 1) * Tuning.GAUGE_STEP:0}" : !worked ? "after the first strike" : rest < Every ? $"after {Every - rest:0} s more wandering" : "when it wanders";
    public string Line() =>
        $"\ndirector stage {Stage} (gauge {gauge:0}, {Tuning.GAUGE_STEP:0} a stage) · {phase} · next call {CallState} · came {approaches} · good seam {map.rich} · ore {player.ore}/{Tuning.BOOTH_QUOTA}" +
        $"\n  [Alt+1 2] rest x{everyMul:0.00} ({Every:0} s)  [Alt+5 6] noise x{noiseMul:0.00}  [Alt+7 8] tunnel {tunnelS:0} s  [Alt+9] call now  [Alt+0] +1 stage";
}
