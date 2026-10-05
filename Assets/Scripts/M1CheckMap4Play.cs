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
//   map4play_ore     씨앗 12 개: 좋은 광맥 5 + 나머지 1 씩 = 8 · 좋은 구역이 바뀐다 · 지금 판 8 곳 · 닫힌 조각 숨김 · 28 곳 모두 앞 바닥에서 곡괭이가 닿고 눈에서 안 가린다 · 하나 캐면 덩이   (noore · sameseed · propblock)
//   map4play_exits   석탄 자리마다 굴 길이 25 m 안 출구 · 불 켜진 방 안 출구 0 · 벽 틈이 그 방 가운데서 보인다        (farexit · homeexit · propblock)
//   map4play_gauge   같은 덩이를 서서 깔끔 < 숙여서 < '쨍' 섞임 · 발소리 0 · 콱 하나에 조금씩                          (flatnoise · steppile · jumpgauge)
//   map4play_stage   깔끔한 몫(콱 3 × BOOTH_QUOTA) = 4 단계 · 단계마다 간격 · 출구 거리가 표대로                               (nostage)
//   map4play_emerge  나온 출구 = 마지막 일한 자리 기준(사람 아님) · 돌가루 4 초 · 보고 있어도 그 출구에서 돌가루 뒤 나옴 · 나와서 머리는 일한 자리를 보고 소리 들었을 때 걸음으로 · 입에서 돌가루 · 긁힘 · 와르르 소리   (chaseplayer · noshake · hideexit · stalehead · slowsend · muteemerge)
//   map4play_call    첫 곡괭이질 전엔 안 부름 · 25 를 넘긴 콱에 바로 부름 · 숨은 굴 TUNNEL_S · 25 를 안 넘으면 안 부름 · 쉬는 최소 시간 · 집에서 먼 밖에서 바로 벽 속으로   (nowork · slowtunnel · clockcall · norest · homeonly)
//   map4play_move    이동 셋(걷기 · Shift 짧게 끊어 달리기 · 끝까지 달리기) 실제 키로 승강장 → 가까운 구역(셋) · 먼 구역(끊어 달리기) 가는 길 → 몫 시간 어림 ≥ QUOTA_FLOOR_S   (fastrun)
// -only map4meet [-rounds N]: 첫 마주침 — 판마다 씬을 다시 불러 N 판(기본 6), Shift 끊어 달리기로 좋은 광맥을 캐다 괴물이 알아챌 때까지. 오래 걸려 따로 (중앙값 90~150 s)
public partial class M1Check
{
    static string AreaOf(string slotName) => slotName.Split('_')[2];
    static Vector3 SpotStand(Map4.Spot c) => OnNav(c.outT != null ? c.outT.position : c.slot.position, 2f);
    // 그 자리 1.5 m 안에서 지금 나는 나오는 소리(3D, 들리는 거리 EMERGE_SOUND_M) 이름들
    static string EmergeSounds(Vector3 p) => string.Join(" ", FindObjectsByType<AudioSource>(FindObjectsSortMode.None)
        .Where(a => a.isPlaying && a.clip != null && a.clip.name.StartsWith("emerge_") && a.spatialBlend > 0.99f && Mathf.Approximately(a.maxDistance, Tuning.EMERGE_SOUND_M) && Vector3.Distance(a.transform.position, p) < 1.5f)
        .Select(a => a.clip.name).Distinct().OrderBy(n => n));

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
        if (sabotageName == "propblock")                                                      // 사보타주: 석탄 하나 앞 · 벽 틈 하나 앞에 판 하나씩 (동발 기둥 · 칸막이가 가린 것처럼)
        {
            var c0 = m.coal[0]; Vector3 o0 = c0.outT.position - c0.slot.position; o0.y = 0f; o0.Normalize();
            var e0 = d.exits.First(e => e.name.StartsWith("MGAP_") && m.Area(e.name.Substring(5)) != null); Vector3 oe = OnNav(m.Area(e0.name.Substring(5)).position, 3f) + Vector3.up * 1.6f - e0.mouth; oe.Normalize();   // 그 방 가운데에서 틈을 보는 줄 위
            foreach (var (at, f) in new[] { (c0.slot.position + o0 * 0.9f + Vector3.up * 0.3f, o0), (e0.mouth + oe * 1.5f, oe) })
            { var b = GameObject.CreatePrimitive(PrimitiveType.Cube); b.transform.SetPositionAndRotation(at, Quaternion.LookRotation(f)); b.transform.localScale = new Vector3(1.4f, 1.6f, 0.15f); }
            Physics.SyncTransforms();
        }

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
        var reachRows = new List<string>(); var cantMine = new List<string>(); var hiddenCoal = new List<string>();
        foreach (var c in m.coal.Where(c => c.outT != null))
        {
            Vector3 o = c.outT.position - c.slot.position; o.y = 0f; o.Normalize();
            bool onFloor = NavMesh.SamplePosition(c.slot.position + o * 1.6f, out var sh, 1.5f, NavMesh.AllAreas);
            float reach = onFloor ? Vector3.Distance(sh.position + Vector3.up * 1.6f, c.slot.position) : 99f;
            float nav = NavMesh.SamplePosition(c.slot.position, out var nh, 6f, NavMesh.AllAreas) ? Vector3.Distance(nh.position, c.slot.position) : 99f;
            reachRows.Add($"{c.name.Replace("SLOT_Pocket_", "")} {reach:0.0} (floor {nav:0.0})");
            if (onFloor)                                                                       // 눈 셋(가운데 · 옆으로 0.5 m 씩) 다 보여야 — 가운데만 보면 기둥 사이로 석탄 한가운데가 보여 통과했다(10-03 W5)
                foreach (float k in new[] { -0.5f, 0f, 0.5f })
                    if (Hidden(sh.position + Vector3.up * 1.6f + Vector3.Cross(Vector3.up, o) * k, c.slot.position, 0.4f, out string by)) { hiddenCoal.Add($"{c.name} by {by}"); break; }
            if (reach > Tuning.MINE_RANGE - 0.5f)                                                 // 앞에 선 몸 자리를 무엇이 차지했나
            {
                Vector3 b0 = c.slot.position + o * 1.6f; b0.y = c.slot.position.y - 0.7f;
                var blk = Physics.OverlapCapsule(b0, b0 + Vector3.up * 1.2f, Tuning.BODY_RADIUS, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore).Select(x => x.name).Distinct().Take(4);
                cantMine.Add($"{c.name} {(onFloor ? reach.ToString("0.0") + " m" : "no floor")} (in the way: {string.Join(" ", blk)})");
            }
        }
        Debug.Log("MAP4PLAY coal reach (eye → coal from 1.6 m in front): " + string.Join(", ", reachRows));
        int offNav = cantMine.Count + hiddenCoal.Count;
        int noParts = m.coal.Count(c => c.face == null || c.loose == null || c.gap == null || c.outT == null);
        var kb = InputSystem.AddDevice<Keyboard>("Map4PlayKeyboard"); var mouse = InputSystem.AddDevice<Mouse>("Map4PlayMouse");
        if (!pickaxe.hasPick) pickaxe.Return();
        pickaxe.durability = Tuning.PICK_DURABILITY_MAX;
        var first = live.OrderBy(c => PathLen(spawn, stand[c.name]) is float L && L >= 0f ? L : 1e6f).FirstOrDefault();
        int ore0 = player.ore; bool popped = false; float mineT = 0f;
        if (first != null) yield return MineOne(cc, kb, mouse, first.pocket, false, (p, t) => { popped = p; mineT = t; });
        yield return new WaitForSeconds(1.5f);
        Check("map4play_ore", counts && riches.Count >= 3 && sets.Count >= 6 && live.Count == 8 && closedShown == 0 && offNav == 0 && noParts == 0 && popped && player.ore > ore0,
            $"12 seeds: 8 open each with 5 in the good seam {counts} · good seams seen {string.Join("", riches.OrderBy(x => x))} ({riches.Count}, want ≥ 3) · different sets {sets.Count} · this round: seed {m.seed} good {m.rich} open {live.Count} (want 8) closed chunks shown {closedShown} · of 28 spots can't be mined from the floor in front (reach {Tuning.MINE_RANGE - 0.5f:0.0} m) {cantMine.Count} {string.Join(", ", cantMine)} · hidden from the eye 1.6 m in front {hiddenCoal.Count} {string.Join(", ", hiddenCoal)} · spots missing face/loose/gap/out {noParts} · mined {(first != null ? first.name : "-")} popped {popped} in {mineT:0.0} s · ore {ore0} → {player.ore}");

        // ---- 출구
        var far = new List<string>(); float worst = 0f; string worstName = "-";
        foreach (var c in m.coal)
        {
            float best = d.exits.Select(e => PathLen(stand[c.name], e.stand)).Where(L => L >= 0f).DefaultIfEmpty(1e6f).Min();
            if (best > worst) { worst = best; worstName = c.name; }
            if (best > Tuning.EXIT_NEAR_SPOT_M) far.Add($"{c.name} {best:0}");
        }
        var inLit = d.exits.Where(e => Map4.LitRooms.Any(r => m.InArea(r, e.stand, 0.5f) || m.InArea(r, e.mouth, 0.5f))).Select(e => e.name).ToList();
        var hiddenExits = new List<string>();                                                 // 벽 틈은 그 방 가운데 눈높이에서 보여야 한다 (칸막이 · 쌓은 것 뒤 금지 — 사용자 "방마다 괴물 나올 자리가 보이게"). 틈 바로 앞에서 재면 칸막이 칸 안 틈이 '좁은 굴'로 빠졌다(10-03 V2)
        foreach (var e in d.exits.Where(e => !e.ceiling && e.name.StartsWith("MGAP_")))
        {
            string key = e.name.Substring(5); var room = m.Area(key) ?? (key.EndsWith("2") ? m.Area(key.Substring(0, key.Length - 1)) : null);
            if (room == null) { hiddenExits.Add($"{e.name} (no room node)"); continue; }
            Vector3 c0 = OnNav(room.position, 3f), half = OnNav(Vector3.Lerp(c0, e.mouth, 0.5f), 2f);   // 방 가운데가 물건 바로 옆이면(선로 끝 방: 덮개 천 0.6 m) 틈 쪽 반 거리에서 한 번 더
            string by = "";
            if (new[] { c0, half }.All(q => Hidden(q + Vector3.up * 1.6f, e.mouth, 0.5f, out by))) hiddenExits.Add($"{e.name} by {by}");
        }
        Check("map4play_exits", far.Count == 0 && inLit.Count == 0 && hiddenExits.Count == 0,
            $"exits {d.exits.Count} ({string.Join(" ", d.exits.Select(e => e.name))}) · coal spots farther than {Tuning.EXIT_NEAR_SPOT_M:0} m by path from any exit: {far.Count} {string.Join(", ", far.Take(6))} · worst {worstName} {worst:0} m · exits inside lit rooms {inLit.Count} {string.Join(" ", inLit)} · wall exits hidden from the middle of their room {hiddenExits.Count} {string.Join(", ", hiddenExits)}");

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

        // ---- 나오기: ① 마지막 일한 자리 기준 · 돌가루 · 사람에서 8 m 밖 · 나와서 일한 자리를 보며 곧장  ② 보고 있어도 나온다 (10-04 판정 1)
        stalker.enabled = true; d.tunnelS = 1f;                                 // 숨은 굴 시간은 이 검사의 대상이 아니다 — 빨리 (map4play_call 이 잰다)
        var spotA = m.coal.OrderByDescending(c => PathLen(spawn, stand[c.name])).FirstOrDefault();   // 일한 자리 = 승강장에서 가장 먼 석탄 자리 · 사람은 승강장 (석탄 자리가 없는 옛 맵이면 옛 채굴 빈터)
        d.gauge = 3 * Tuning.GAUGE_STEP + 1f; d.lastWork = spotA != null ? stand[spotA.name] : d.homes[1];
        Teleport(cc, spawn + Vector3.up * 0.1f, 0f);
        d.ForceHome(); yield return null;
        int ap0 = d.approaches; bool called = d.Call(true); var tgt = d.target; int bursts0 = d.warnBursts;
        float tw = 0f; for (; tw < 60f && d.approaches == ap0; tw += Time.deltaTime) yield return null;
        float fromWork = tgt != null ? PathLen(d.lastWork, tgt.stand) : -1f, toPlayer = tgt != null ? Flat(tgt.stand - player.transform.position) : -1f;
        float nearestFromWork = d.exits.Select(e => PathLen(d.lastWork, e.stand)).Where(L => L >= 0f).DefaultIfEmpty(-1f).Min();
        bool rule1 = called && d.approaches > ap0 && fromWork >= 0f && (fromWork <= Tuning.STAGE_EXIT_M[3] + 0.5f || Mathf.Abs(fromWork - nearestFromWork) < 0.5f) && toPlayer >= Tuning.EXIT_MIN_PLAYER_M;
        float warn1 = d.warnFor; int b1 = d.warnBursts - bursts0;
        // 나와서: 조사 머리(mode 4)가 보는 자리 = 일한 자리 · 걸음 = 소리 들었을 때 (2.5 살피는 걸음 + 옛 소리 자리 머리 = 사용자 "두리번")
        var sa = stalker.GetComponentInChildren<StalkerAnim>();
        float headOff = Flat(stalker.noisePos - d.lastWork), walked = 0f, el = 0f; Vector3 prev = stalker.transform.position; int fr = 0, fr4 = 0;
        for (; el < 2f && stalker.state == Stalker.State.Investigate; el += Time.deltaTime)
        { yield return null; walked += Flat(stalker.transform.position - prev); prev = stalker.transform.position; fr++; if (sa != null && sa.HeadMode == 4) fr4++; }
        float walkV = el > 0.3f ? walked / el : -1f;
        bool goes = headOff < 1f && fr > 0 && fr4 == fr && walkV >= 0.8f * Tuning.STALKER_SPEED_INVESTIGATE;
        stalker.enabled = false; yield return null;
        // ② 출구 하나 앞 10~14 m(그 입이 보이는 자리)에 서서 그 입을 본다 — 보고 있어도 그 출구를 고르고, 돌가루 뒤 보는 앞에서 나온다
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
            Vector3 look = stareAt.mouth - (stareFrom + Vector3.up * Tuning.EYE_HEIGHT);
            Teleport(cc, stareFrom + Vector3.up * 0.1f, Quaternion.LookRotation(Flat3(look)).eulerAngles.y);   // 그 입을 본다
            player.Pitch = -Mathf.Atan2(look.y, Flat(look)) * Mathf.Rad2Deg;
            yield return null; stalker.enabled = true;
            d.ForceHome(); yield return null;
            int seen0 = d.emergedSeen, ap1 = d.approaches; bool seenAtCall = d.Seen(stareAt.mouth); d.Call(true);
            bool same = d.target == stareAt;
            for (float w = 0f; w < 60f && d.phase != Director.Phase.Warn && d.approaches == ap1; w += Time.deltaTime) yield return null;
            string warnSnd = EmergeSounds(stareAt.mouth);                                            // 돌가루가 떨어지기 시작한 때 그 입에서 나는 소리 (10-05 판정 7 · 8)
            float tOut = 0f; for (; tOut < Tuning.EMERGE_WARN_S + 3f && d.phase == Director.Phase.Warn; tOut += Time.deltaTime) yield return null;
            string outSnd = EmergeSounds(stareAt.mouth);
            bool outSeen = d.approaches > ap1 && d.target == stareAt && d.emergedSeen == seen0 + 1;
            bool sounds = warnSnd.Contains("emerge_dust_000") && warnSnd.Contains("emerge_scrape_000") && outSnd.Contains("emerge_burst_000");
            stareOk = seenAtCall && same && outSeen && tOut <= Tuning.EMERGE_WARN_S + 0.5f && sounds;
            stareNote = $"looked at {stareAt.name} from {Flat(stareFrom - stareAt.stand):0} m (in view {seenAtCall}): chosen {same} · came out {tOut:0.0} s after the dust began (want ≤ {Tuning.EMERGE_WARN_S + 0.5f:0.0}) at {(d.target != null ? d.target.name : "-")} · came out in view {d.emergedSeen - seen0} (want 1) · 3D sounds at the mouth ({Tuning.EMERGE_SOUND_M:0} m) when the dust began [{warnSnd}] (want dust + scrape) · when it came out [{outSnd}] (want burst)";
            stalker.enabled = false;
        }
        Check("map4play_emerge", rule1 && warn1 >= Tuning.EMERGE_WARN_S - 0.05f && b1 >= 6 && goes && stareOk,
            $"① worked at {(spotA != null ? spotA.name : "M (no coal spots)")}, player at the cage: came out at {(tgt != null ? tgt.name : "-")} {fromWork:0} m from the work spot by path (stage 3 max {Tuning.STAGE_EXIT_M[3]:0}, nearest {nearestFromWork:0}) · {toPlayer:0} m from the player (want ≥ {Tuning.EXIT_MIN_PLAYER_M:0}) · dust {warn1:0.0} s in {b1} bursts · then head looks {headOff:0.0} m from the work spot (want < 1) in head mode 4 {fr4}/{fr} frames · walks {walkV:0.0} m/s over {el:0.0} s (want ≥ {0.8f * Tuning.STALKER_SPEED_INVESTIGATE:0.0}) · ② {stareNote}");
        d.tunnelS = Tuning.TUNNEL_S;

        // ---- 부르기 (10-05 판정 3): ㉮ 첫 곡괭이질 전엔 안 부름 · ㉢ 25 를 넘긴 콱에 바로 부름 · ㉠ 숨은 굴 TUNNEL_S(괴물의 굴에서 멀어도) · 25 를 안 넘으면 다 쉬었어도 안 부름
        //   · 쉬는 최소 시간 전엔 안 부름 · ㉡ 집에서 먼 밖에서 바로 그 자리 벽 속으로 → 새 일한 자리 둘레로 나옴. 사람은 승강장 (괴물이 못 보고 못 듣는 곳)
        var farHome = m.coal.Select(c => (c, h: d.homes.Min(hm => Flat(hm - stand[c.name])))).OrderByDescending(x => x.h).Select(x => x.c).ToList();
        var workA = farHome.FirstOrDefault(); var workB = farHome.FirstOrDefault(c => workA != null && Flat(stand[c.name] - stand[workA.name]) > 80f);
        bool callOk = false; string callNote = "no two coal spots 80 m apart";
        if (workA != null && workB != null)
        {
            Teleport(cc, spawn + Vector3.up * 0.1f, 0f); player.Pitch = 0f;
            d.gauge = 0f; stalker.enabled = true; d.ForceHome(); d.worked = false; d.gauge = Tuning.GAUGE_STEP + 1f;   // Alt+0 처럼 곡괭이질 없이 1 단계
            int calls0 = d.calls;
            yield return new WaitForSeconds(1.5f);
            bool noWork = d.pending && d.calls == calls0;                                                      // ㉮ 부를 일은 있지만 첫 곡괭이질 전
            NoiseBus.Make(workA.slot.position, Tuning.MINE_NOISE_SOFT, "pick", player);                       // 첫 콱 → 바로 부른다
            float tCall = 0f; for (; tCall < 1f && d.calls == calls0; tCall += Time.deltaTime) yield return null;
            bool calledA = d.calls == calls0 + 1;
            float tTun = 0f; for (; tTun < 30f && d.phase == Director.Phase.Tunnel; tTun += Time.deltaTime) yield return null;
            bool tunnelOk = calledA && Mathf.Abs(tTun - Tuning.TUNNEL_S) < 0.5f;
            for (float w = 0f; w < 10f && d.phase != Director.Phase.Free; w += Time.deltaTime) yield return null;
            stalker.Teleport(stand[workA.name], 0f); d.rest = 1e6f; int calls1 = d.calls;                     // 밖(집에서 먼 일한 자리)에서 어슬렁거리고 다 쉬었다
            yield return new WaitForSeconds(1.5f);
            bool noStepNoCall = d.calls == calls1;                                                             // 25 를 안 넘었다 — 안 부른다 (옛 시계라면 부른다)
            d.rest = 0f; d.gauge = (d.Steps + 1) * Tuning.GAUGE_STEP - 0.5f;
            NoiseBus.Make(workB.slot.position, Tuning.MINE_NOISE_SOFT, "pick", player);                       // 다른 구역 콱이 25 를 넘긴다
            yield return new WaitForSeconds(1.5f);
            bool restHolds = d.pending && d.calls == calls1;                                                   // 쉬는 최소 시간 전 — 안 부른다
            d.rest = 1e6f;
            float tC2 = 0f; for (; tC2 < 1f && d.calls == calls1; tC2 += Time.deltaTime) yield return null;
            float heldHome = d.homes.Min(hm => Flat(hm - stalker.transform.position));
            bool fromOut = d.calls == calls1 + 1 && heldHome > Tuning.STALKER_WANDER_CELLS * Tuning.GRID_CELL + 3f;
            int ap2 = d.approaches; for (float w = 0f; w < 20f && d.approaches == ap2; w += Time.deltaTime) yield return null;
            float fromB = d.target != null && d.approaches > ap2 ? PathLen(workB.slot.position, d.target.stand) : -1f;
            bool nearB = fromB >= 0f && fromB <= Mathf.Max(d.ExitMax, Tuning.EXIT_NEAR_SPOT_M) + 0.5f;
            callOk = noWork && calledA && tunnelOk && noStepNoCall && restHolds && fromOut && nearB;
            callNote = $"㉮ past 25 with no strike yet: waiting {noWork} · ㉢ first strike at {workA.name}: into the wall after {tCall:0.0} s (want < 1) · ㉠ tunnel {tTun:0.0} s from the lair (want {Tuning.TUNNEL_S:0} ± 0.5) · out and rested, no new 25: called {!noStepNoCall} (want no) · new 25 at {workB.name} just after a call: called {!restHolds} (want no, rest {d.Every:0} s) · rested: into the wall {tC2:0.0} s later, {heldHome:0} m from the nearest home (want > {Tuning.STALKER_WANDER_CELLS * Tuning.GRID_CELL + 3f:0} — out, not home) · came out at {(d.target != null ? d.target.name : "-")} {fromB:0} m from {workB.name}";
            stalker.enabled = false; yield return null;
        }
        Check("map4play_call", callOk, callNote);

        // ---- 이동: 실제 W · Shift 로 승강장 ↔ 가까운 구역 · 먼 구역의 가장 가까운 석탄 자리 (괴물 끔)
        if (m.coal.Count == 0) { Check("map4play_move", false, "no coal spots in this map file"); InputSystem.RemoveDevice(kb); InputSystem.RemoveDevice(mouse); yield break; }
        var areaNear = Tuning.COAL_AREAS.Select(a => (a, c: m.coal.Where(c => c.area == a).OrderBy(c => PathLen(spawn, stand[c.name])).First())).Select(x => (x.a, x.c, L: PathLen(spawn, stand[x.c.name]))).OrderBy(x => x.L).ToList();
        var legs = new[] { areaNear.First(), areaNear.Last() };
        var rows = new List<string>(); float fastest = 1e6f; string fastestNote = "";
        // 가는 길만 잰다: 돌아오는 길은 같은 길 · 같은 시간(10-03 왕복 여섯 번: 15.2/15.0 · 12.3/12.2 · 42.6/42.1 · 35.4/35.1 s) — 왕복이 검사 시간의 85 % 였다.
        //   먼 구역은 Shift 끊어 달리기만 (사용자 방식 · 그 판 몫 길이를 적으려고). 가장 빠른 어림(몫 기준)은 가까운 구역 세 방식에서 나온다
        foreach (var (a, c, L) in legs)
            foreach (var style in a == legs[0].a ? new[] { "walk", "burst", "sprint" } : new[] { "burst" })
            {
                Teleport(cc, spawn + Vector3.up * 0.1f, 0f); player.stamina = Tuning.STAMINA_MAX; player.exhausted = false; yield return new WaitForSeconds(0.3f);
                float go = -1f, gl = 0f;
                yield return BotWalk(kb, stand[c.name], style, (t, len) => { go = t; gl = len; });
                bool there = Flat(player.transform.position - stand[c.name]) < 1.5f;
                int trips = Mathf.CeilToInt(Tuning.BOOTH_QUOTA / 2f);
                float quota = there ? trips * (go + go / 0.9f + 2f * Tuning.MINE_TIME_REF + 2f) : -1f;   // 돌아올 땐 같은 길을 들고 0.9 배 (BOOTH-2) · 덩이 둘 캐기 · 싣기 2 s
                rows.Add($"{a} {style}: go {go:0.0} s over {gl:0} m{(there ? "" : " (DID NOT ARRIVE)")} → quota ≈ {quota:0} s");
                if (quota > 0f && quota < fastest) { fastest = quota; fastestNote = $"{a} {style}"; }
            }
        Check("map4play_move", fastest < 1e5f && fastest >= Tuning.QUOTA_FLOOR_S,
            $"fastest quota estimate {fastest:0} s ({fastestNote}) — want ≥ {Tuning.QUOTA_FLOOR_S:0} s, else raise BOOTH_QUOTA (now {Tuning.BOOTH_QUOTA}) · {string.Join(" | ", rows)}");
        InputSystem.RemoveDevice(kb); InputSystem.RemoveDevice(mouse);
        player.runMul = 1f;
    }

    // eye → target 사이에 다른 것이 먼저 걸리나 (target 앞 tol m 안은 벽 자체). 석탄 덩이 구 · 내 몸 · 괴물은 건너뛴다
    bool Hidden(Vector3 eye, Vector3 target, float tol, out string by)
    {
        Vector3 v = target - eye; by = "";
        foreach (var h in Physics.RaycastAll(eye, v.normalized, v.magnitude + 0.3f, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance))
        {
            if (h.collider.GetComponent<OrePocket>() != null || h.collider.transform.IsChildOf(player.transform) || h.collider.GetComponentInParent<Stalker>() != null) continue;
            if (h.distance < v.magnitude - tol) { by = $"{h.collider.name} {h.distance:0.0} m"; return true; }
            return false;
        }
        return false;
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
        for (; pk != null && t < 15f; t += Time.deltaTime) { kb.MakeCurrent(); mouse.MakeCurrent(); yield return null; }   // 검사 중 진짜 마우스 · 키보드가 움직이면 Mouse.current 가 그쪽으로 넘어가 누르기가 끊긴다(10-04: 두 번 치고 멈춤)
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
        // 길 = 괴물 바닥(턱 0.75 m 까지)이라 사람(턱 0.3 m)이 못 넘는 곳이 있다(10-04: 무너진 돌무더기 앞에서 매판 멈춤). 사람처럼: 2 초 동안 0.5 m 도 못 가면
        //   그 자리를 길에서 지우고(NavMeshObstacle 깎기 — 이 구간 동안 괴물 길에서도 빠진다) 다른 길로 다시 찾는다. 네 번까지
        var pts = new List<Vector3>(); float len = 0f, len0 = -1f, limit = 0f, t = 0f, bt = 0f, still = 0f; bool shift = false; int ci = 0, reroutes = 0;
        Vector3 lastP = player.transform.position;
        void Plan()
        {
            var path = new NavMeshPath();
            bool has = NavMesh.CalculatePath(OnNav(player.transform.position), OnNav(goal), NavMesh.AllAreas, path) && path.status == NavMeshPathStatus.PathComplete;
            pts = has ? path.corners.ToList() : new List<Vector3> { goal };
            len = 0f; for (int i = 1; i < pts.Count; i++) len += Vector3.Distance(pts[i - 1], pts[i]);
            if (len0 < 0f) len0 = len;
            limit = t + len / Tuning.CROUCH_SPEED + 15f; ci = Mathf.Min(1, pts.Count - 1);
        }
        Plan();
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
            InputSystem.QueueStateEvent(kb, shift ? new KeyboardState(Key.W, Key.LeftShift) : new KeyboardState(Key.W)); kb.MakeCurrent();
            yield return null; t += Time.deltaTime;
            if (Flat(player.transform.position - lastP) > 0.5f) { lastP = player.transform.position; still = 0f; } else still += Time.deltaTime;
            if (still > 2f && reroutes < 4 && !player.frozen)                               // 잡혀 얼어 있을 때는 아니다
            {
                Vector3 at = player.transform.position + player.transform.forward * 1.0f, pp = at - Map4.Offset;
                var ob = new GameObject("botwalk_blocked").AddComponent<NavMeshObstacle>(); ob.transform.position = at; ob.shape = NavMeshObstacleShape.Capsule; ob.radius = 1.2f; ob.height = 3f; ob.carving = true; ob.carveOnlyStationary = false;
                reroutes++; Debug.Log($"BOTWALK a person can't get past plan ({-pp.x:0.0}, {-pp.z:0.0}, {pp.y:0.0}) — trying another way ({reroutes})");
                InputSystem.QueueStateEvent(kb, new KeyboardState()); yield return null; yield return null; t += 2f * Time.deltaTime;
                Plan(); still = 0f; lastP = player.transform.position;
            }
        }
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        yield return null;
        done(t, len0);
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
        stalker.enabled = true;                                                               // 검사 틀(Run)이 구간마다 괴물 두뇌를 끈다 — 끄인 채면 감독이 쉬어 6 판 내내 안 나왔다(10-04)
        var kb = InputSystem.AddDevice<Keyboard>("Map4MeetKeyboard"); var mouse = InputSystem.AddDevice<Mouse>("Map4MeetMouse");
        Vector3 spawn = OnNav(player.transform.position); float t0 = Time.time; float met = -1f; int mined = 0;
        bool Met() => stalker.state == Stalker.State.Alert || stalker.state == Stalker.State.Chase || stalker.state == Stalker.State.Catch;
        IEnumerator Watch() { while (met < 0f) { if (Met()) met = Time.time - t0; yield return null; } }
        StartCoroutine(Watch());
        var order = m.coal.Where(c => c.open).OrderBy(c => c.area == m.rich ? 0 : 1).ThenBy(c => PathLen(spawn, SpotStand(c))).ToList();
        foreach (var c in order)
        {
            if (met >= 0f || Time.time - t0 > 240f) break;
            float wt = 0f; yield return BotWalk(kb, SpotStand(c), "burst", (t, len) => wt = t);
            bool there = Flat(player.transform.position - SpotStand(c)) < 1.5f; Vector3 pp = player.transform.position - Map4.Offset;
            Debug.Log($"MAP4MEET {Time.time - t0:0} s: walked to {c.name} in {wt:0.0} s · {(there ? "there" : $"NOT there — stopped at plan ({-pp.x:0.0}, {-pp.z:0.0}, {pp.y:0.0}) {Flat(player.transform.position - SpotStand(c)):0} m short · stance {player.stance}")} · stage {d.Stage} · {d.phase}");
            if (!there) yield return Capture($"69_meet_stuck_{meetTimes.Count + 1}_{c.name.Replace("SLOT_Pocket_", "")}", _ => { });
            if (met >= 0f || c.pocket == null) continue;
            Vector3 aim = c.pocket.transform.position - pickaxe.cam.position;
            player.transform.rotation = Quaternion.LookRotation(Flat3(aim)); player.Pitch = -Mathf.Atan2(aim.y, Flat(aim)) * Mathf.Rad2Deg;
            InputSystem.QueueStateEvent(mouse, new MouseState().WithButton(MouseButton.Left));
            for (float t = 0f; c.pocket != null && t < 15f && met < 0f; t += Time.deltaTime) { kb.MakeCurrent(); mouse.MakeCurrent(); yield return null; }
            InputSystem.QueueStateEvent(mouse, new MouseState()); player.Pitch = 0f;
            if (c.pocket == null) mined++; else Debug.Log($"MAP4MEET {c.name} not mined in 15 s");
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
