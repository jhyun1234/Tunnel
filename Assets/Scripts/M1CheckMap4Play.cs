using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;

// GAME-1 검사 (-only map4play, 제안서 docs/제안서_GAME1_MAP4에서_놀기.md 5절). 사람 길(인트로 → 아무 키 → "시작")로 들어와 DevHud 가 놓은 MAP4 게임을 그대로 탄다 — 맵 · 괴물 · 감독을 검사가 따로 놓지 않는다.
//   map4play_start   플래그 없이 MAP4 승강장 · 감독 · 괴물 (옛 부스 맵은 켜 둔다 — 판정 받은 -map4 모습과 같게)                                 (사보타주 startbooth)
//   map4play_nav     괴물 바닥(Map4_NavMesh) 넓이 · 승강장에서 석탄 28 · 출구 · 집 셋까지 길                    (nonav)
//   map4play_ore     씨앗 12 개: 좋은 광맥 5 + 나머지 1 씩 = 8 · 좋은 구역이 바뀐다 · 지금 판 8 곳 · 닫힌 조각 숨김 · 28 곳 모두 앞 바닥에서 곡괭이가 닿는다 · 하나 캐면 덩이   (noore · sameseed)
//   map4play_exits   석탄 자리마다 굴 길이 25 m 안 출구 · 불 켜진 방 안 출구 0                                      (farexit · homeexit)
//   map4play_gauge   같은 덩이를 서서 깔끔 < 숙여서 < '쨍' 섞임 · 발소리 0 · 콱 하나에 조금씩                          (flatnoise · steppile · jumpgauge)
//   map4play_stage   깔끔한 몫(콱 3 × BOOTH_QUOTA) = 4 단계 · 단계마다 간격 · 출구 거리가 표대로                               (nostage)
//   map4play_emerge  나온 출구 = 마지막 일한 자리 기준(사람 아님) · 돌가루 4 초 · 보고 있으면 안 나옴 · 보일 때 나온 수 0   (chaseplayer · noshake · seenexit)
//   map4play_move    이동 셋(걷기 · Shift 짧게 끊어 달리기 · 끝까지 달리기) 실제 키로 승강장 ↔ 가까운/먼 구역 왕복 → 몫 시간 어림 ≥ QUOTA_FLOOR_S   (fastrun)
// -only map4meet [-rounds N]: 첫 마주침 — 판마다 씬을 다시 불러 N 판(기본 6), Shift 끊어 달리기로 좋은 광맥을 캐다 괴물이 알아챌 때까지. 오래 걸려 따로 (중앙값 90~150 s)
public partial class M1Check
{
    static string AreaOf(string slotName) => slotName.Split('_')[2];
    static Vector3 SpotStand(Map4.Spot c) => OnNav(c.outT != null ? c.outT.position : c.slot.position, 2f);

    IEnumerator Map4PlayStage()
    {
        Map4 m = null; Director d = null;
        for (float w = 0f; w < 8f && (m == null || d == null); w += Time.deltaTime) { m = FindFirstObjectByType<Map4>(); d = Director.I; yield return null; }
        var cc = player.GetComponent<CharacterController>(); var hud = GetComponent<DevHud>();
        var startT = m != null ? FabTest.Node(m.gameObject, "CAM_start") : null;
        float fromStart = startT != null ? Flat(player.transform.position - startT.position) : 99f;
        bool monsterHere = m != null && stalker.transform.position.y < Map4.Offset.y + 60f;
        Check("map4play_start", m != null && d != null && !m.judge && fromStart < 4f && stalker.gameObject.activeSelf && d.s == stalker && monsterHere && hud != null && hud.enabled && m.coal.Count == 28,
            $"intro → start (no -map4): map {m != null} · judge mode {(m != null && m.judge)} · director {d != null} · player {fromStart:0.0} m from CAM_start · monster given to the director {(d != null && d.s == stalker)} in the new map {monsterHere} (BoothRun switches its brain off for checks) · DevHud on {hud != null && hud.enabled} · coal spots {(m != null ? m.coal.Count : 0)} (want 28)");
        if (m == null || d == null) yield break;
        stalker.returnToIntro = false; stalker.enabled = false;               // 괴물은 나오기 검사에서만 켠다 (감독은 괴물이 꺼져 있으면 쉰다)
        if (sabotageName == "fastrun") player.runMul = 2f;
        Vector3 spawn = OnNav(player.transform.position);

        // ---- 바닥
        var tri = NavMesh.CalculateTriangulation(); double area = 0; int n4 = 0;
        for (int i = 0; i + 2 < tri.indices.Length; i += 3)
        {
            Vector3 a = tri.vertices[tri.indices[i]], b = tri.vertices[tri.indices[i + 1]], c3 = tri.vertices[tri.indices[i + 2]];
            if (a.y > Map4.Offset.y + 60f) continue;
            n4++; area += Vector3.Cross(b - a, c3 - a).magnitude * 0.5;
        }
        var stand = m.coal.ToDictionary(c => c.name, SpotStand);
        int badSpots = stand.Count(kv => PathLen(spawn, kv.Value) < 0f), badExits = d.exits.Count(e => PathLen(spawn, e.stand) < 0f), badHomes = d.homes.Count(h => PathLen(spawn, h) < 0f);
        Check("map4play_nav", n4 > 0 && area > 4000 && badSpots == 0 && badExits == 0 && badHomes == 0 && d.exits.Count >= 9,
            $"monster floor {area:0} m2 ({n4} tris) · from the cage: coal spots unreachable {badSpots}/{stand.Count} · exits {d.exits.Count} unreachable {badExits} · homes unreachable {badHomes}/{d.homes.Length}");

        // ---- 석탄
        var names = m.coal.Select(c => c.name).ToList(); var riches = new HashSet<string>(); var sets = new HashSet<string>(); bool counts = true;
        for (int sd = 1; sd <= 12; sd++)
        {
            var (r, open) = Map4.PickOpen(names, sd); riches.Add(r); sets.Add(string.Join(",", open.OrderBy(x => x)));
            counts &= open.Count == Tuning.COAL_OPEN_RICH + (Tuning.COAL_AREAS.Length - 1) * Tuning.COAL_OPEN_POOR && open.Count(n => AreaOf(n) == r) == Tuning.COAL_OPEN_RICH;
        }
        var live = m.coal.Where(c => c.open && c.pocket != null).ToList();
        int closedShown = m.coal.Count(c => !c.open && ((c.loose != null && c.loose.gameObject.activeInHierarchy) || (c.face != null && c.face.gameObject.activeInHierarchy)));
        // 28 곳 전부(이번 판에 닫힌 곳도): 석탄 앞 1.6 m 바닥(1.5 m 안)에 선 눈(1.6 m)에서 곡괭이가 닿나 — 판마다 8 곳만 보면 운으로 갈린다
        var reachRows = new List<string>(); var cantMine = new List<string>();
        foreach (var c in m.coal.Where(c => c.outT != null))
        {
            Vector3 o = c.outT.position - c.slot.position; o.y = 0f; o.Normalize();
            bool onFloor = NavMesh.SamplePosition(c.slot.position + o * 1.6f, out var sh, 1.5f, NavMesh.AllAreas);
            float reach = onFloor ? Vector3.Distance(sh.position + Vector3.up * 1.6f, c.slot.position) : 99f;
            float nav = NavMesh.SamplePosition(c.slot.position, out var nh, 6f, NavMesh.AllAreas) ? Vector3.Distance(nh.position, c.slot.position) : 99f;
            reachRows.Add($"{c.name.Replace("SLOT_Pocket_", "")} {reach:0.0} (floor {nav:0.0})");
            if (reach > Tuning.MINE_RANGE - 0.5f)                                                 // 앞에 선 몸 자리를 무엇이 차지했나
            {
                Vector3 b0 = c.slot.position + o * 1.6f; b0.y = c.slot.position.y - 0.7f;
                var blk = Physics.OverlapCapsule(b0, b0 + Vector3.up * 1.2f, Tuning.BODY_RADIUS, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore).Select(x => x.name).Distinct().Take(4);
                cantMine.Add($"{c.name} {(onFloor ? reach.ToString("0.0") + " m" : "no floor")} (in the way: {string.Join(" ", blk)})");
            }
        }
        Debug.Log("MAP4PLAY coal reach (eye → coal from 1.6 m in front): " + string.Join(", ", reachRows));
        int offNav = cantMine.Count;
        int noParts = m.coal.Count(c => c.face == null || c.loose == null || c.gap == null || c.outT == null);
        var kb = InputSystem.AddDevice<Keyboard>("Map4PlayKeyboard"); var mouse = InputSystem.AddDevice<Mouse>("Map4PlayMouse");
        if (!pickaxe.hasPick) pickaxe.Return();
        pickaxe.durability = Tuning.PICK_DURABILITY_MAX;
        var first = live.OrderBy(c => PathLen(spawn, stand[c.name]) is float L && L >= 0f ? L : 1e6f).FirstOrDefault();
        int ore0 = player.ore; bool popped = false; float mineT = 0f;
        if (first != null) yield return MineOne(cc, kb, mouse, first.pocket, false, (p, t) => { popped = p; mineT = t; });
        yield return new WaitForSeconds(1.5f);
        Check("map4play_ore", counts && riches.Count >= 3 && sets.Count >= 6 && live.Count == 8 && closedShown == 0 && offNav == 0 && noParts == 0 && popped && player.ore > ore0,
            $"12 seeds: 8 open each with 5 in the good seam {counts} · good seams seen {string.Join("", riches.OrderBy(x => x))} ({riches.Count}, want ≥ 3) · different sets {sets.Count} · this round: seed {m.seed} good {m.rich} open {live.Count} (want 8) closed chunks shown {closedShown} · of 28 spots can't be mined from the floor in front (reach {Tuning.MINE_RANGE - 0.5f:0.0} m) {offNav} {string.Join(", ", cantMine)} · spots missing face/loose/gap/out {noParts} · mined {(first != null ? first.name : "-")} popped {popped} in {mineT:0.0} s · ore {ore0} → {player.ore}");

        // ---- 출구
        var far = new List<string>(); float worst = 0f; string worstName = "-";
        foreach (var c in m.coal)
        {
            float best = d.exits.Select(e => PathLen(stand[c.name], e.stand)).Where(L => L >= 0f).DefaultIfEmpty(1e6f).Min();
            if (best > worst) { worst = best; worstName = c.name; }
            if (best > Tuning.EXIT_NEAR_SPOT_M) far.Add($"{c.name} {best:0}");
        }
        var inLit = d.exits.Where(e => Map4.LitRooms.Any(r => m.InArea(r, e.stand, 0.5f) || m.InArea(r, e.mouth, 0.5f))).Select(e => e.name).ToList();
        Check("map4play_exits", far.Count == 0 && inLit.Count == 0,
            $"exits {d.exits.Count} ({string.Join(" ", d.exits.Select(e => e.name))}) · coal spots farther than {Tuning.EXIT_NEAR_SPOT_M:0} m by path from any exit: {far.Count} {string.Join(", ", far.Take(6))} · worst {worstName} {worst:0} m · exits inside lit rooms {inLit.Count} {string.Join(" ", inLit)}");

        // ---- 게이지: 같은 덩이를 세 방식으로 (실제 곡괭이 · 실제 소리)
        var pk = live.Where(c => c != first && c.pocket != null).Select(c => c.pocket).Where(p => p.transform.position.y - OnNav(p.transform.position + p.outDir * 1.6f, 1.5f).y >= Tuning.MINE_LOW_M + 0.1f).Take(3).ToList();
        float[] dg = new float[3]; float firstStrike = -1f; var how = new List<string>();
        for (int k = 0; k < pk.Count; k++)
        {
            pickaxe.slipChance = k == 2 ? 1f : 0f;
            float g0 = d.gauge; int strikes0 = pickaxe.hitsLanded;
            bool watch = k == 0;
            IEnumerator Watch() { while (watch) { if (firstStrike < 0f && pickaxe.hitsLanded > strikes0) firstStrike = d.gauge - g0; yield return null; } }
            if (watch) StartCoroutine(Watch());
            bool got = false; float mt = 0f; string nm = pk[k].name; yield return MineOne(cc, kb, mouse, pk[k], k == 1, (p, t) => { got = p; mt = t; });
            watch = false; yield return null;
            how.Add($"{nm.Replace("OrePocket_", "")} {(got ? "out" : "STUCK")} {mt:0.0}s {pickaxe.hitsLanded - strikes0} hits");
            dg[k] = got ? (d.gauge - g0) / Director.Lump : -1f;
        }
        pickaxe.slipChance = 0f;
        float gw = d.gauge; Teleport(cc, spawn + Vector3.up * 0.1f, 0f);
        InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W)); yield return new WaitForSeconds(2.5f); InputSystem.QueueStateEvent(kb, new KeyboardState(Key.W, Key.LeftShift)); yield return new WaitForSeconds(1.5f); InputSystem.QueueStateEvent(kb, new KeyboardState());
        float stepG = d.gauge - gw;
        bool order = pk.Count == 3 && dg[0] > 0f && dg[0] < dg[1] && dg[1] < dg[2];
        Check("map4play_gauge", order && Mathf.Abs(dg[0] - 1f) < 0.15f && dg[1] > 1.4f && dg[1] < 1.95f && dg[2] > 2.0f && dg[2] < 2.8f && Mathf.Abs(stepG) < 1e-4f && firstStrike > 0f && firstStrike <= 0.5f * Director.Lump,
            $"one lump in lump units: stand clean {dg[0]:0.00} (want 1) · crouched {(pk.Count > 1 ? dg[1] : -1f):0.00} (want ~1.67) · with a slip {(pk.Count > 2 ? dg[2] : -1f):0.00} (want ~2.39) · walking + running 4 s {stepG:0.00} (want 0) · first strike {firstStrike:0.0} of a {Director.Lump:0.0} lump (want a third) · pockets used {pk.Count}: {string.Join(", ", how)}");

        // ---- 단계 (깔끔한 몫 = 콱 3 × BOOTH_QUOTA)
        d.gauge = 0f; var stages = new List<int>();
        for (int k = 0; k < Tuning.BOOTH_QUOTA; k++)
        {
            for (int s3 = 0; s3 < 3; s3++) NoiseBus.Make(spawn, Tuning.MINE_NOISE_SOFT, "pick", player);
            stages.Add(d.Stage);
        }
        var table = new List<string>(); bool tableOk = true; float keep = d.gauge;
        for (int st = 0; st < Tuning.STAGE_EVERY_S.Length; st++)
        {
            d.gauge = st * Tuning.GAUGE_STEP; table.Add($"{d.Stage}:{d.Every:0}s/{(d.ExitMax > 0f ? d.ExitMax.ToString("0") + "m" : "near")}");
            tableOk &= d.Stage == st && Mathf.Approximately(d.Every, Tuning.STAGE_EVERY_S[st]) && Mathf.Approximately(d.ExitMax, Tuning.STAGE_EXIT_M[st]);
        }
        d.gauge = keep;
        Check("map4play_stage", stages.Last() == 4 && tableOk && stages.Zip(stages.Skip(1), (a, b) => b >= a).All(x => x),
            $"clean quota {Tuning.BOOTH_QUOTA} lumps → stage after each lump {string.Join(" ", stages)} (want ends at 4) · gauge {keep:0.0} · table {string.Join(" ", table)} {(tableOk ? "as Tuning" : "NOT as Tuning")}");

        // ---- 나오기: ① 마지막 일한 자리 기준 · 돌가루 · 사람에서 8 m 밖  ② 보고 있으면 안 나온다
        stalker.enabled = true; d.tunnelSpeed = 60f;                            // 숨은 굴 시간은 이 검사의 대상이 아니다 — 빨리
        var spotA = m.coal.OrderByDescending(c => PathLen(spawn, stand[c.name])).FirstOrDefault();   // 일한 자리 = 승강장에서 가장 먼 석탄 자리 · 사람은 승강장 (석탄 자리가 없는 옛 맵이면 옛 채굴 빈터)
        d.gauge = 3 * Tuning.GAUGE_STEP + 1f; d.lastWork = spotA != null ? stand[spotA.name] : d.homes[1];
        Teleport(cc, spawn + Vector3.up * 0.1f, 0f);
        d.ForceHome(); yield return null;
        bool called = d.Call(true); var tgt = d.target; int bursts0 = d.warnBursts;
        float tw = 0f; for (; tw < 40f && d.phase != Director.Phase.Out; tw += Time.deltaTime) yield return null;
        float fromWork = tgt != null ? PathLen(d.lastWork, tgt.stand) : -1f, toPlayer = tgt != null ? Flat(tgt.stand - player.transform.position) : -1f;
        float nearestFromWork = d.exits.Select(e => PathLen(d.lastWork, e.stand)).Where(L => L >= 0f).DefaultIfEmpty(-1f).Min();
        bool rule1 = called && d.phase == Director.Phase.Out && fromWork >= 0f && (fromWork <= Tuning.STAGE_EXIT_M[3] + 0.5f || Mathf.Abs(fromWork - nearestFromWork) < 0.5f) && toPlayer >= Tuning.EXIT_MIN_PLAYER_M;
        float warn1 = d.warnFor; int b1 = d.warnBursts - bursts0;
        stalker.enabled = false; yield return null;
        // ② 출구 하나 앞 10~14 m(그 입이 보이는 자리)에 서서 등을 돌리고, 돌가루가 나는 동안 돌아서서 본다
        Director.Exit stareAt = null; Vector3 stareFrom = default;
        foreach (var e in d.exits.Where(e => !e.ceiling))
            for (float L = 10f; L <= 14f && stareAt == null; L += 2f)
            {
                Vector3 p = OnNav(e.stand + e.face * L, 1.5f); Vector3 eye = p + Vector3.up * Tuning.EYE_HEIGHT;
                if (Flat(p - e.stand) < 9f || Physics.Linecast(eye, e.mouth + e.face * 0.3f, ~((1 << 2) | (1 << Pickaxe.ViewModelLayer)), QueryTriggerInteraction.Ignore)) continue;
                stareAt = e; stareFrom = p;
            }
        bool stareOk = false; string stareNote = "no exit with a clear view from 10-14 m";
        if (stareAt != null)
        {
            d.gauge = 4 * Tuning.GAUGE_STEP + 1f; d.lastWork = stareAt.stand;                       // 4 단계 = 가장 가까운 출구 = 그 출구
            Teleport(cc, stareFrom + Vector3.up * 0.1f, Quaternion.LookRotation(stareAt.face).eulerAngles.y);   // 등을 돌림 (출구가 뒤)
            player.Pitch = 0f;
            yield return null; stalker.enabled = true;
            d.ForceHome(); yield return null;
            int seen0 = d.emergedSeen; d.Call(true);
            for (float w = 0f; w < 20f && d.phase != Director.Phase.Warn; w += Time.deltaTime) yield return null;
            bool same = d.target == stareAt;
            Vector3 look = stareAt.mouth - pickaxe.cam.position;
            player.transform.rotation = Quaternion.LookRotation(Flat3(look)); player.Pitch = -Mathf.Atan2(look.y, Flat(look)) * Mathf.Rad2Deg;
            yield return new WaitForSeconds(Tuning.EMERGE_WARN_S + 3f);
            bool held = d.phase == Director.Phase.Warn && d.Seen(stareAt.mouth);
            player.transform.rotation = Quaternion.LookRotation(Flat3(-look)); player.Pitch = 0f;
            float tOut = 0f; for (; tOut < 5f && d.phase == Director.Phase.Warn; tOut += Time.deltaTime) yield return null;
            stareOk = same && held && d.phase == Director.Phase.Out && d.emergedSeen == seen0;
            stareNote = $"stared at {stareAt.name} from {Flat(stareFrom - stareAt.stand):0} m: chosen {same} · still in the wall {Tuning.EMERGE_WARN_S + 3f:0} s while looked at {held} · came out {tOut:0.0} s after looking away · came out while seen {d.emergedSeen - seen0}";
            stalker.enabled = false;
        }
        Check("map4play_emerge", rule1 && warn1 >= Tuning.EMERGE_WARN_S - 0.05f && b1 >= 6 && stareOk && d.emergedSeen == 0,
            $"① worked at {(spotA != null ? spotA.name : "M (no coal spots)")}, player at the cage: came out at {(tgt != null ? tgt.name : "-")} {fromWork:0} m from the work spot by path (stage 3 max {Tuning.STAGE_EXIT_M[3]:0}, nearest {nearestFromWork:0}) · {toPlayer:0} m from the player (want ≥ {Tuning.EXIT_MIN_PLAYER_M:0}) · dust {warn1:0.0} s in {b1} bursts · ② {stareNote}");
        d.tunnelSpeed = Tuning.TUNNEL_SPEED;

        // ---- 이동: 실제 W · Shift 로 승강장 ↔ 가까운 구역 · 먼 구역의 가장 가까운 석탄 자리 (괴물 끔)
        if (m.coal.Count == 0) { Check("map4play_move", false, "no coal spots in this map file"); InputSystem.RemoveDevice(kb); InputSystem.RemoveDevice(mouse); yield break; }
        var areaNear = Tuning.COAL_AREAS.Select(a => (a, c: m.coal.Where(c => c.area == a).OrderBy(c => PathLen(spawn, stand[c.name])).First())).Select(x => (x.a, x.c, L: PathLen(spawn, stand[x.c.name]))).OrderBy(x => x.L).ToList();
        var legs = new[] { areaNear.First(), areaNear.Last() };
        var rows = new List<string>(); float fastest = 1e6f; string fastestNote = "";
        foreach (var (a, c, L) in legs)
            foreach (var style in new[] { "walk", "burst", "sprint" })
            {
                Teleport(cc, spawn + Vector3.up * 0.1f, 0f); player.stamina = Tuning.STAMINA_MAX; player.exhausted = false; yield return new WaitForSeconds(0.3f);
                float go = -1f, back = -1f, gl = 0f;
                yield return BotWalk(kb, stand[c.name], style, (t, len) => { go = t; gl = len; });
                bool there = Flat(player.transform.position - stand[c.name]) < 1.5f;
                yield return new WaitForSeconds(0.5f);                              // 캐는 시간은 어림에 숫자로 더한다 (아래)
                player.stamina = Mathf.Min(Tuning.STAMINA_MAX, player.stamina + Tuning.STAMINA_IDLE * 2f * Tuning.MINE_TIME_REF);   // 두 덩이 캐는 동안 쉬며 찬 기력
                yield return BotWalk(kb, spawn, style, (t, len) => back = t);
                bool home = Flat(player.transform.position - spawn) < 1.5f;
                int trips = Mathf.CeilToInt(Tuning.BOOTH_QUOTA / 2f);
                float quota = there && home ? trips * (go + back / 0.9f + 2f * Tuning.MINE_TIME_REF + 2f) : -1f;   // 돌아올 땐 들고 0.9 배 (BOOTH-2) · 덩이 둘 캐기 · 싣기 2 s
                rows.Add($"{a} {style}: go {go:0.0} s back {back:0.0} s over {gl:0} m{(there && home ? "" : " (DID NOT ARRIVE)")} → quota ≈ {quota:0} s");
                if (quota > 0f && quota < fastest) { fastest = quota; fastestNote = $"{a} {style}"; }
            }
        Check("map4play_move", fastest < 1e5f && fastest >= Tuning.QUOTA_FLOOR_S,
            $"fastest quota estimate {fastest:0} s ({fastestNote}) — want ≥ {Tuning.QUOTA_FLOOR_S:0} s, else raise BOOTH_QUOTA (now {Tuning.BOOTH_QUOTA}) · {string.Join(" | ", rows)}");
        InputSystem.RemoveDevice(kb); InputSystem.RemoveDevice(mouse);
        player.runMul = 1f;
    }

    // 석탄 하나: 1.6 m 앞에 서서 겨누고 좌클릭을 누르고 있다 (crouch = Ctrl 을 누른 채). 빠지면 true
    IEnumerator MineOne(CharacterController cc, Keyboard kb, Mouse mouse, OrePocket pk, bool crouch, Action<bool, float> done)
    {
        if (!pickaxe.hasPick) pickaxe.Return();
        float w0 = Time.time; while (player.mineLock && Time.time - w0 < 5f) yield return null;   // 앞 덩이의 내리기 동작이 끝날 때까지 (사람은 다음 자리까지 걷는 동안 끝난다 — 묶인 채 옮기면 고개가 앞 방향에 묶인다)
        if (Time.time - w0 > 0.05f) Debug.Log($"MINEONE waited {Time.time - w0:0.00} s for the last swing to end before {pk.name}");
        Vector3 at = OnNav(pk.transform.position + pk.outDir * 1.6f, 1.5f);
        Teleport(cc, at + Vector3.up * 0.1f, Quaternion.LookRotation(-pk.outDir).eulerAngles.y);
        InputSystem.QueueStateEvent(kb, crouch ? new KeyboardState(Key.LeftCtrl) : new KeyboardState());
        yield return new WaitForSeconds(0.6f);
        Vector3 aim = pk.transform.position - pickaxe.cam.position;
        player.Pitch = -Mathf.Atan2(aim.y, Flat(aim)) * Mathf.Rad2Deg;
        yield return null;
        InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
        float t = 0f;
        for (; pk != null && t < 15f; t += Time.deltaTime) yield return null;
        if (pk != null)                                                                       // 안 빠졌다: 어디에 섰고 겨눈 줄에 무엇이 걸렸나
        {
            var want = pk.transform.position + pk.outDir * 1.6f; var hits = Physics.RaycastAll(pickaxe.cam.position, pickaxe.cam.forward, 6f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance).Take(5);
            Debug.Log($"MINEONE stuck {pk.name}: eye→coal {Vector3.Distance(pickaxe.cam.position, pk.transform.position):0.00} m (reach {Tuning.MINE_RANGE}) · stood {Flat(player.transform.position - want):0.00} m off the 1.6 m spot · eye {pickaxe.cam.position.y - player.transform.position.y:0.00} m · facing off {Mathf.DeltaAngle(player.transform.eulerAngles.y, Quaternion.LookRotation(-pk.outDir).eulerAngles.y):0}° · pitch {player.Pitch:0} · mine lock {player.mineLock} · ray: {string.Join(", ", hits.Select(h => $"{h.collider.name} {h.distance:0.00}"))}");
        }
        InputSystem.QueueStateEvent(mouse, new MouseState()); InputSystem.QueueStateEvent(kb, new KeyboardState());
        player.Pitch = 0f;
        yield return new WaitForSeconds(0.6f);
        done(pk == null, t);
    }

    // 봇 걷기: 길찾기 꺾는 점을 따라 방향만 돌리고 W(+ Shift)를 누른다 (실제 키). walk · burst(Shift 를 짧게 — 2 s 달리고 1.5 s 걷기, 기력 40 밑이면 놓는다) · sprint(끝까지 — 탈진까지)
    IEnumerator BotWalk(Keyboard kb, Vector3 goal, string style, Action<float, float> done)
    {
        var path = new NavMeshPath();
        bool has = NavMesh.CalculatePath(OnNav(player.transform.position), OnNav(goal), NavMesh.AllAreas, path) && path.status == NavMeshPathStatus.PathComplete;
        var pts = has ? path.corners.ToList() : new List<Vector3> { goal };
        float len = 0f; for (int i = 1; i < pts.Count; i++) len += Vector3.Distance(pts[i - 1], pts[i]);
        float limit = len / Tuning.CROUCH_SPEED + 15f, t = 0f, bt = 0f; bool shift = false; int ci = Mathf.Min(1, pts.Count - 1);
        while (t < limit && Flat(goal - player.transform.position) > 1.0f)
        {
            while (ci < pts.Count - 1 && Flat(pts[ci] - player.transform.position) < 0.6f) ci++;
            Vector3 to = Flat3(pts[ci] - player.transform.position);
            if (to.sqrMagnitude > 1e-4f) player.transform.rotation = Quaternion.LookRotation(to);
            bt += Time.deltaTime;
            if (style == "sprint") shift = true;
            else if (style == "burst")
            {
                if (shift && (bt > 2f || player.stamina < 40f)) { shift = false; bt = 0f; }
                else if (!shift && bt > 1.5f && player.stamina >= 60f) { shift = true; bt = 0f; }
            }
            InputSystem.QueueStateEvent(kb, shift ? new KeyboardState(Key.W, Key.LeftShift) : new KeyboardState(Key.W));
            yield return null; t += Time.deltaTime;
        }
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        yield return null;
        done(t, len);
    }

    // ================= 첫 마주침 (-only map4meet [-rounds N]). 판마다 씬을 다시 불러 새 씨앗 — 결과는 static 에 모은다
    static readonly List<float> meetTimes = new List<float>(); static readonly List<string> meetRows = new List<string>();
    IEnumerator Map4MeetStage()
    {
        Map4 m = null; Director d = null;
        for (float w = 0f; w < 8f && (m == null || d == null); w += Time.deltaTime) { m = FindFirstObjectByType<Map4>(); d = Director.I; yield return null; }
        if (m == null || d == null) { Check("map4meet_first", false, "no MAP4 game"); yield break; }
        var a = Environment.GetCommandLineArgs(); int ri = Array.IndexOf(a, "-rounds"); int rounds = ri >= 0 && ri + 1 < a.Length && int.TryParse(a[ri + 1], out int rr) ? rr : 6;
        var cc = player.GetComponent<CharacterController>(); stalker.returnToIntro = false;
        var kb = InputSystem.AddDevice<Keyboard>("Map4MeetKeyboard"); var mouse = InputSystem.AddDevice<Mouse>("Map4MeetMouse");
        Vector3 spawn = OnNav(player.transform.position); float t0 = Time.time; float met = -1f; int mined = 0;
        bool Met() => stalker.state == Stalker.State.Alert || stalker.state == Stalker.State.Chase || stalker.state == Stalker.State.Catch;
        IEnumerator Watch() { while (met < 0f) { if (Met()) met = Time.time - t0; yield return null; } }
        StartCoroutine(Watch());
        var order = m.coal.Where(c => c.open).OrderBy(c => c.area == m.rich ? 0 : 1).ThenBy(c => PathLen(spawn, SpotStand(c))).ToList();
        foreach (var c in order)
        {
            if (met >= 0f || Time.time - t0 > 240f) break;
            yield return BotWalk(kb, SpotStand(c), "burst", (t, len) => { });
            if (met >= 0f || c.pocket == null) continue;
            Vector3 aim = c.pocket.transform.position - pickaxe.cam.position;
            player.transform.rotation = Quaternion.LookRotation(Flat3(aim)); player.Pitch = -Mathf.Atan2(aim.y, Flat(aim)) * Mathf.Rad2Deg;
            InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
            for (float t = 0f; c.pocket != null && t < 15f && met < 0f; t += Time.deltaTime) yield return null;
            InputSystem.QueueStateEvent(mouse, new MouseState()); player.Pitch = 0f;
            if (c.pocket == null) mined++;
            yield return new WaitForSeconds(0.8f);
        }
        while (met < 0f && Time.time - t0 < 240f) yield return null;             // 다 캤으면 그 자리에서 기다린다
        InputSystem.RemoveDevice(kb); InputSystem.RemoveDevice(mouse);
        meetTimes.Add(met); meetRows.Add($"seed {m.seed} good {m.rich}: met {(met >= 0f ? met.ToString("0") + " s" : "NOT in 240 s")} · mined {mined} · stage {d.Stage} · came {d.approaches}");
        Debug.Log("MAP4MEET round " + meetTimes.Count + " " + meetRows.Last());
        if (meetTimes.Count < rounds) { SceneManager.LoadScene(Tuning.BOOTH_SCENE); yield return new WaitForSeconds(999f); }
        var got = meetTimes.Where(x => x >= 0f).OrderBy(x => x).ToList(); float med = got.Count > 0 ? got[got.Count / 2] : -1f;
        Check("map4meet_first", got.Count == meetTimes.Count && med >= 90f && med <= 150f && got.Count(x => x > 180f) <= meetTimes.Count / 10,
            $"rounds {meetTimes.Count} · first meeting median {med:0} s (want 90~150) · over 180 s {got.Count(x => x > 180f)} · never {meetTimes.Count(x => x < 0f)} · {string.Join(" | ", meetRows)}");
    }
}
