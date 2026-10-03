using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

// MAP4 모양 검사 (-only map4geo). 10-02 판정 ① (사용자: 떠 있음 · 찢어진 바위 · 풍문에서 저절로 숙임 · 광차와 레일 간격 · 홀로 선 문)의 흠을 "맵 전체에서" 찾는다.
// 그 전 검사는 [ ] 자리 65곳에 서서만 봐서 문 · 굴 속 · 소품은 못 잡았다. 걷는 길 · 훑을 넓이는 굽기가 빈 노드로 넣는다(scene_mock.py: WALK_<번호>_<반폭 × 10>_<점> · AREA_<이름>_<가로 × 10>_<세로 × 10>).
//   map4_shell_not_torn   바위 굴 그물(0.25 m 복셀)에 0.75 m 넘게 늘어난 변이 없다 = 겉면이 접힌(검은 틈 · 뾰족한 조각) 곳이 없다        (사보타주 tornshell)
//   map4_no_floating      모든 물체 · 덩어리가 바위나 바위에 닿은 다른 것에 5 cm 안으로 닿아 있다 (닿음을 번져 가며 센다)                 (사보타주 floatprop)
//   map4_heaps_solid      돌 · 석탄 더미마다 속 찬 둔덕이 있고, 덩이 가운데 바로 밑(덩이 키 안)에 둔덕이나 바위 바닥이 있다 — 덩이 위에 덩이를 얹은 탑이 없다   (사보타주 heaplift)
//   map4_monster_gaps     괴물 틈 여섯 넘게: 입 안은 사람이 서고 · 그 뒤는 선 몸이 못 들고 · 6 m 넘게 끝까지 뚫려 있다                              (사보타주 gapplug)
//   map4_ceiling_holes    천장 구멍 둘(K · M): 입 → 꺾는 점 둘 → 끝까지 뚫렸고 · 밑 8 m 안 선 자리 어디서도 끝이 안 보이고 · 긁힌 자국 16 줄 · 떨어진 돌 넷 넘게   (사보타주 chimplug · chimpeek · chimbare)
//   map4_fan_ducts        바람 관(E1 · z2): 선풍기 출구 1 m 안에서 시작 · 점 사이 3 m 안 · 바위를 안 뚫고 · 끝이 막장 면 7 m 안 · 선풍기는 막장 9 m 밖          (사보타주 ductcut · ductfar)
//   map4_air_lines        압축공기 관(E1 · z2 · N2): 점 사이 3.5 m 안 · 바위를 안 뚫고 · 두 끝은 밸브거나 벽 속으로 · 호스가 밸브와 착암기를 잇는다           (사보타주 pipeend · hoseloose)
//   map4_doors_in_wall    판자 문 칸의 문틀 양옆 0.25 m 밖, 0.3 m 안에 바위가 있다 = 문이 벽에 달려 있다                                   (사보타주 lonedoor)
//   map4_carts_on_rails   선 광차의 바퀴 넷 밑에 레일 머리가 3 cm 안으로 있다                                                              (사보타주 offrail)
//   map4_no_auto_crouch   방 · 굴 · 장면 바닥을 0.25~0.5 m 칸으로 훑어, 선 몸이 들어가는 자리에서 저절로 숙여지는 곳(Map4.LowAbove)이 없다   (사보타주 lowdoor)
//                         + 굴 가운데 줄 머리 위 가장 낮은 것이 2.1 m 넘는다 (사용자 10-01 "높낮이를 낮게 구성하지 말아라")
//   map4_walk_through     굴마다 몸 캡슐(CharacterController)을 10 cm 씩 밀어 끝까지 간다 — 막힘 · 떨어짐이 없다                            (사보타주 blockway)
// 옛 맵 파일(걷는 길 노드가 없다)에는 exe -walks <글 파일> (굽기가 맵 옆에 적는 Map4_walks.txt, Blender 좌표).
public partial class M1Check
{
    const float TornEdge = 0.75f, Touch = 0.05f;

    IEnumerator Map4GeoStage()
    {
        var m = Map4.Spawn(player, Camera.main);
        if (m == null) { Check("map4geo_loaded", false, "no Map4.glb in Resources"); yield break; }
        stalker.gameObject.SetActive(false); lamp.lampOn = true;
        var cc = player.GetComponent<CharacterController>();
        yield return new WaitForSeconds(0.5f);
        player.enabled = false; cc.enabled = false; Physics.SyncTransforms();
        // Blender 좌표 ↔ 게임 (Map4ShotsStage 와 같은 법)
        var tp = m.GetComponentsInChildren<Transform>().FirstOrDefault(t => t.name.StartsWith("TEX_P_")); var cs = FabTest.Node(m.gameObject, "CAM_start");
        if (tp == null || cs == null) { Check("map4geo_loaded", false, "no TEX_P_ / CAM_start node to fix the axes"); yield break; }
        float sx = -Mathf.Sign(m.transform.InverseTransformPoint(tp.position).x), sz = Mathf.Sign(m.transform.InverseTransformPoint(cs.position).z);
        Vector3 W(float x, float y, float z) => m.transform.TransformPoint(new Vector3(sx * x, z, sz * y));
        Vector3 B(Vector3 w) { var l = m.transform.InverseTransformPoint(w); return new Vector3(sx * l.x, sz * l.z, l.y); }
        string At(Vector3 w) { var b = B(w); return $"({b.x:0.0}, {b.y:0.0}, {b.z:0.0})"; }

        // ---- 걷는 길 · 훑을 넓이
        var walks = new List<(string name, float hw, List<Vector3> pts)>(); var areas = new List<(string name, Vector3 c, Vector3 ax, Vector3 az, float w, float d)>();
        var ci = System.Globalization.CultureInfo.InvariantCulture; string[] args = Environment.GetCommandLineArgs(); int wi = Array.IndexOf(args, "-walks");
        if (wi >= 0 && wi + 1 < args.Length && File.Exists(args[wi + 1]))
            foreach (var raw in File.ReadAllLines(args[wi + 1]))
            {
                var p = raw.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                Vector3 V(string s) { var f = s.Split(',').Select(x => float.Parse(x, ci)).ToArray(); return W(f[0], f[1], f[2]); }
                if (p.Length > 4 && p[0] == "WALK") walks.Add((p[1] + " " + p[2], float.Parse(p[3], ci), p.Skip(4).Select(V).ToList()));
                if (p.Length > 5 && p[0] == "AREA")
                {
                    float yaw = float.Parse(p[5], ci) * Mathf.Deg2Rad; Vector3 c = V(p[2]);
                    areas.Add((p[1], c, (W(Mathf.Cos(yaw), Mathf.Sin(yaw), 0f) - W(0f, 0f, 0f)).normalized, (W(-Mathf.Sin(yaw), Mathf.Cos(yaw), 0f) - W(0f, 0f, 0f)).normalized, float.Parse(p[3], ci), float.Parse(p[4], ci)));
                }
            }
        else
        {
            foreach (var g in m.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("WALK_")).GroupBy(t => t.name.Split('_')[1]).OrderBy(g => g.Key))
                walks.Add((g.Key, int.Parse(g.First().name.Split('_')[2]) / 10f, g.OrderBy(t => t.name).Select(t => t.position).ToList()));
            foreach (var t in m.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("AREA_")))
            { var p = t.name.Split('_'); areas.Add((p[1], t.position, t.right, t.forward, int.Parse(p[2]) / 10f, int.Parse(p[3]) / 10f)); }
        }
        Check("map4geo_loaded", walks.Count > 20 && areas.Count > 20, $"{walks.Count} walk lines ({walks.Sum(w => Len(w.pts)):0} m) · {areas.Count} areas to scan · {m.GetComponentsInChildren<MeshFilter>().Length} meshes");
        if (walks.Count == 0) yield break;

        var filters = m.GetComponentsInChildren<MeshFilter>().Where(f => f.sharedMesh != null).ToArray();
        var shells = filters.Where(f => f.name.StartsWith("SHELL_")).ToArray();
        bool IsShell(Collider c) => c != null && c.name.StartsWith("SHELL_");
        bool IsCart(string n) => n.Contains("ueujednfa") || n.Contains("ufmodhpfa") || n.Contains("ujzhahdfa");

        // ---- 사보타주 (검사보다 먼저 맵을 망가뜨린다)
        if (sabotageName == "tornshell")
        { var f = shells[0]; var me = Instantiate(f.sharedMesh); var v = me.vertices; v[v.Length / 2] += Vector3.up * 2f; me.vertices = v; f.sharedMesh = me; }
        if (sabotageName == "floatprop") filters.First(x => x.name.StartsWith("BENCH")).transform.position += Vector3.up * 1.0f;   // 긴 의자 하나를 1 m 띄운다 (벽에서 1 m 떨어져 있어 아무 데도 안 닿는다)
        if (sabotageName == "lonedoor")
        {
            var f = filters.First(x => x.name.StartsWith("TIMBER_C")); var d = filters.FirstOrDefault(x => x.name == "DOOR_" + f.name.Substring(7));
            FrameAxes(f, out Vector3 c, out Vector3 u, out Vector3 n);
            Vector3 mv = n * 1.8f; if (Physics.CheckSphere(c + mv + Vector3.up, 0.6f)) mv = -mv;      // 바위가 없는 쪽(방 안)으로
            f.transform.position += mv; if (d != null) d.transform.position += mv;
        }
        if (sabotageName == "offrail")
        { var f = filters.First(x => IsCart(x.name) && Vector3.Dot(x.transform.up, Vector3.up) > 0.9f && UnderRail(x)); CartAxes(f, out _, out _, out Vector3 lat); f.transform.position += lat * 0.2f; }
        GameObject sabPlate = null;
        if (sabotageName == "lowdoor" || sabotageName == "blockway")
        {
            var w = walks.OrderByDescending(x => Len(x.pts)).First(); Vector3 mid = (w.pts[0] + w.pts[1]) * 0.5f;
            Physics.Raycast(mid + Vector3.up * 1.0f, Vector3.down, out var fl, 3f);
            sabPlate = GameObject.CreatePrimitive(PrimitiveType.Cube);
            if (sabotageName == "lowdoor") { sabPlate.transform.localScale = new Vector3(3f, 0.2f, 3f); sabPlate.transform.position = fl.point + Vector3.up * (Map4.LowAboveM + 0.08f); }   // 밑면 = 숙이는 선 − 2 cm — 선 몸(1.8 m)은 들어가고 선에는 걸린다
            else { sabPlate.transform.localScale = new Vector3(8f, 3f, 0.6f); sabPlate.transform.SetPositionAndRotation(fl.point + Vector3.up * 1.5f, Quaternion.LookRotation(Flat3(w.pts[1] - w.pts[0]))); }
        }
        Physics.SyncTransforms(); yield return null;

        // ---- 1. 찢어진 바위
        {
            var bad = new List<string>(); float worst = 0f; long tris = 0;
            foreach (var f in shells)
            {
                var me = f.sharedMesh; if (!me.isReadable) { bad.Add(f.name + " not readable"); continue; }
                var v = me.vertices; var t = me.triangles; int n = 0; float mx = 0f; tris += t.Length / 3;
                for (int i = 0; i < t.Length; i += 3)
                    for (int k = 0; k < 3; k++) { float e = (v[t[i + k]] - v[t[i + (k + 1) % 3]]).sqrMagnitude; if (e > mx) mx = e; if (e > TornEdge * TornEdge * 2f) n++; }   // 삼각형 빗변 = 칸 √2 배 → 0.75 × √2
                mx = Mathf.Sqrt(mx); worst = Mathf.Max(worst, mx);
                if (n > 0) bad.Add($"{f.name} {n} ({mx:0.00} m)");
            }
            Check("map4_shell_not_torn", shells.Length > 20 && bad.Count == 0, $"{shells.Length} rock tiles, {tris} triangles · tiles with edges stretched past {TornEdge * 1.414f:0.00} m (folded surface): {bad.Count}{(bad.Count > 0 ? " — " + string.Join("; ", bad.Take(10)) : "")} · longest edge {worst:0.00} m");
        }
        yield return null;

        // ---- 2. 떠 있는 물체
        {
            var added = new List<Collider>(); var nodes = new List<FloatNode>(); var byCol = new Dictionary<Collider, List<int>>(); int unreadable = 0;
            foreach (var f in filters)
            {
                if (f.name.StartsWith("SHELL_")) continue;
                var col = f.GetComponent<Collider>();
                if (col == null) { var mc = f.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = f.sharedMesh; col = mc; added.Add(mc); }   // NOCOL_ (표지 · 줄 · 물 · 전등): 검사 동안만 부딪힘을 단다
                var list = new List<int>(); byCol[col] = list; var me = f.sharedMesh; var l2w = f.transform.localToWorldMatrix;
                if (!me.isReadable) { unreadable++; continue; }
                var v = me.vertices;
                if (v.Length > 2500 || f.name.Contains("_LOD0"))                                   // Fab · 받아 온 모델 = 통째로 한 덩어리
                {
                    int step = Mathf.Max(1, v.Length / 250); var s = new List<Vector3>(); for (int i = 0; i < v.Length; i += step) s.Add(l2w.MultiplyPoint3x4(v[i]));
                    list.Add(nodes.Count); nodes.Add(new FloatNode { f = f, col = col, island = 0, b = f.GetComponent<Renderer>().bounds, samples = s.ToArray(), whole = true });
                    continue;
                }
                // 손으로 지은 물체 = 이어진 면끼리 덩어리로 (같은 자리 점은 하나로 — 가져올 때 면마다 점이 갈라진다)
                var weld = new Dictionary<Vector3Int, int>(); var id = new int[v.Length]; int nw = 0;
                for (int i = 0; i < v.Length; i++) { var k = Vector3Int.RoundToInt(v[i] * 1000f); if (!weld.TryGetValue(k, out id[i])) { id[i] = nw; weld[k] = nw++; } }
                var par = Enumerable.Range(0, nw).ToArray();
                int Find(int a) { while (par[a] != a) { par[a] = par[par[a]]; a = par[a]; } return a; }
                var t = me.triangles; for (int i = 0; i < t.Length; i += 3) { int a = Find(id[t[i]]), b = Find(id[t[i + 1]]), c = Find(id[t[i + 2]]); par[b] = a; par[Find(c)] = a; }
                var groups = new Dictionary<int, List<Vector3>>();
                for (int i = 0; i < v.Length; i++) { int r = Find(id[i]); if (!groups.TryGetValue(r, out var g)) groups[r] = g = new List<Vector3>(); g.Add(l2w.MultiplyPoint3x4(v[i])); }
                int isl = 0;
                foreach (var g in groups.Values)
                {
                    var b = new Bounds(g[0], Vector3.zero); foreach (var q in g) b.Encapsulate(q);
                    int step = Mathf.Max(1, g.Count / 60); var s = new List<Vector3>(); for (int i = 0; i < g.Count; i += step) s.Add(g[i]);
                    list.Add(nodes.Count); nodes.Add(new FloatNode { f = f, col = col, island = isl++, b = b, samples = s.ToArray() });
                }
            }
            Physics.SyncTransforms(); yield return null;
            var buf = new Collider[256]; var adj = new List<int>[nodes.Count]; for (int i = 0; i < nodes.Count; i++) adj[i] = new List<int>();
            for (int i = 0; i < nodes.Count; i++)
            {
                var nd = nodes[i]; var grown = nd.b; grown.Expand(Touch * 2f);
                void Touching(int k, Vector3 at, bool point)
                {
                    for (int j = 0; j < k; j++)
                    {
                        var c = buf[j]; if (c == nd.col) continue;
                        if (IsShell(c)) { nd.grounded = true; continue; }
                        if ((sabPlate != null && c.gameObject == sabPlate) || !byCol.TryGetValue(c, out var others)) continue;
                        foreach (int o in others) { var ob = nodes[o].b; ob.Expand(Touch * 2f + 0.02f); if (point ? ob.Contains(at) : ob.Intersects(grown)) { adj[i].Add(o); adj[o].Add(i); } }
                    }
                }
                // 작은 덩어리(끝이 바위 속에 묻힌 쇠줄 · 글자 · 통나무 끝면)는 상자로, 큰 것(굴 조각 · 긴 판)은 점마다 5 cm 공으로 — 상자가 실제로 다른 물체의 면과 겹쳐야 닿은 것
                if (!nd.whole || nd.b.size.magnitude <= 3f) Touching(Physics.OverlapBoxNonAlloc(nd.b.center, nd.b.extents + Vector3.one * Touch, buf, Quaternion.identity, ~0, QueryTriggerInteraction.Ignore), nd.b.center, false);
                else foreach (var sp in nd.samples) Touching(Physics.OverlapSphereNonAlloc(sp, Touch, buf, ~0, QueryTriggerInteraction.Ignore), sp, true);
                foreach (int o in byCol[nd.col])                                                   // 같은 물체의 다른 덩어리: 상자끼리 3 cm 안으로 겹치면 닿은 것
                    if (o > i) { var a = nd.b; a.Expand(0.06f); if (a.Intersects(nodes[o].b)) { adj[i].Add(o); adj[o].Add(i); } }
                if (i % 400 == 399) yield return null;
            }
            var q2 = new Queue<int>(Enumerable.Range(0, nodes.Count).Where(i => nodes[i].grounded));
            while (q2.Count > 0) { int i = q2.Dequeue(); foreach (int o in adj[i]) if (!nodes[o].grounded) { nodes[o].grounded = true; q2.Enqueue(o); } }
            var fl = nodes.Where(n => !n.grounded).OrderByDescending(n => n.b.size.magnitude).ToList();
            foreach (var n in fl.Take(60)) Debug.Log($"MAP4GEO floating {n.f.name}#{n.island} at {At(n.b.center)} size {n.b.size.x:0.00} x {n.b.size.z:0.00} x {n.b.size.y:0.00}");
            Check("map4_no_floating", nodes.Count > 500 && fl.Count == 0, $"{nodes.Count} pieces (objects and loose parts) · not touching rock or anything that touches rock within {Touch * 100f:0} cm: {fl.Count}" +
                (fl.Count > 0 ? " — " + string.Join("; ", fl.GroupBy(n => n.f.name.Split('.')[0]).OrderByDescending(g => g.Count()).Take(12).Select(g => $"{g.Key} ×{g.Count()} {At(g.First().b.center)}")) : "") + $" · unreadable meshes skipped {unreadable}");
            foreach (var c in added) Destroy(c);
            yield return null; Physics.SyncTransforms();
        }

        // ---- 2b. 돌 · 석탄 더미 = 속 찬 둔덕 + 그 겉에 묻힌 덩이 (사용자 10-03 "돌 무더기를 일부러 이렇게 띄워 놓았나": 덩이 위에 덩이를 얹어 가운데에 한 줄 탑이 섰고 모서리만 닿아 떠 보였다 —
        //      위 검사는 상자가 5 cm 안이면 닿은 것으로 쳐서 통과했다). 더미마다(HEAPC_<종류>_<번호>_<반지름 x × 10>_<y × 10>_<높이 × 10>): 덩이 가운데 바로 밑, 덩이 반 높이 안에 둔덕이나 바위 바닥이 있어야 한다
        {
            var heaps = m.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("HEAPC_")).ToArray();
            var lumps = filters.Where(f => f.name.Contains("wd3efb0")).ToArray(); var bad = new List<string>(); int inHeaps = 0, noMound = 0, thin = 0;
            if (sabotageName == "heaplift" && heaps.Length > 0)                                    // 사보타주: 가장 큰 더미의 덩이 열둘을 1.2 m 띄운다 (옛 탑처럼 덩이가 덩이 위에)
            {
                var hc = heaps.OrderByDescending(t => int.Parse(t.name.Split('_')[5])).First(); Vector3 c0 = B(hc.position);
                foreach (var f in lumps.Where(f => { var d = B(f.GetComponent<Renderer>().bounds.center) - c0; return d.x * d.x + d.y * d.y < 9f; }).Take(12)) f.transform.position += Vector3.up * 1.2f;
                Physics.SyncTransforms(); yield return null;
            }
            foreach (var hc in heaps)
            {
                var p = hc.name.Split('_'); float rx = int.Parse(p[3]) / 10f, ry = int.Parse(p[4]) / 10f, hh = int.Parse(p[5]) / 10f; Vector3 c = B(hc.position);
                if (!filters.Any(f => f.name.StartsWith("HEAP_") && f.GetComponent<Renderer>().bounds.Contains(hc.position + Vector3.up * 0.1f))) { noMound++; bad.Add($"{hc.name} {At(hc.position)} has no mound"); continue; }
                int n = 0;
                foreach (var f in lumps)
                {
                    var b = f.GetComponent<Renderer>().bounds; Vector3 lc = B(b.center); float ex = (lc.x - c.x) / (rx * 1.45f), ey = (lc.y - c.y) / (ry * 1.45f);
                    if (ex * ex + ey * ey > 1f || Mathf.Abs(lc.z - c.z) > hh + 2.5f) continue;
                    n++; inHeaps++;
                    bool held = Physics.RaycastAll(b.center + Vector3.up * b.extents.y, Vector3.down, b.size.y + 0.05f, ~0, QueryTriggerInteraction.Ignore).Any(h => h.collider.name.StartsWith("HEAP_") || IsShell(h.collider) || h.collider.name.StartsWith("FLOOR"));   // 덩이 꼭대기에서 밑동 5 cm 아래까지
                    if (!held) bad.Add($"{hc.name} lump {At(b.center)} {b.size.y:0.00} m tall: no mound or floor under its centre");
                }
                if (n < 5) { thin++; bad.Add($"{hc.name} {At(hc.position)} only {n} lumps"); }
            }
            foreach (var s in bad.Take(40)) Debug.Log("MAP4GEO heap " + s);
            Check("map4_heaps_solid", heaps.Length >= 6 && bad.Count == 0, $"{heaps.Length} rock and coal heaps, {inHeaps} lumps on them · heaps without a solid mound {noMound} · with fewer than 5 lumps {thin} · lumps with nothing solid under their centre (stacked lump on lump) {bad.Count - noMound - thin}" +
                (bad.Count > 0 ? " — " + string.Join("; ", bad.Take(6)) : ""));
        }
        yield return null;

        // ---- 2c. 괴물 틈 (사용자 10-03 "괴물이 튀어나올 만한 위험이 인지되는 곳이 없다 — 괴물 전용 틈이 없다"): 설계가 약속한 방마다 벽에 깊은 틈이 실제로 뚫려 있나.
        //      점 넷(굽기가 넣는 빈 노드 MGAP · MGAPIN · MGAPMID · MGAPEND _<방>): 입 안 1 m 는 사람이 설 수 있고 · 좁은 데는 선 몸이 못 들고 · 맨 끝까지 바위에 안 묻혔다 (머리등이 끝에 안 닿는 깊이 6 m 넘게)
        {
            var all = m.GetComponentsInChildren<Transform>(); var mouths = all.Where(t => t.name.StartsWith("MGAP_")).ToArray(); var bad = new List<string>(); float shallow = 99f;
            Transform Nd(string pre, string room) => all.FirstOrDefault(t => t.name == pre + "_" + room);
            if (sabotageName == "gapplug" && mouths.Length > 0)                                    // 사보타주: 첫 틈의 맨 끝을 바위(상자)로 메운다
            { var e = Nd("MGAPEND", mouths[0].name.Substring(5)); var c = GameObject.CreatePrimitive(PrimitiveType.Cube); c.transform.position = e.position; c.transform.localScale = Vector3.one * 1.2f; Physics.SyncTransforms(); yield return null; }
            foreach (var g in mouths)
            {
                string room = g.name.Substring(5); Transform gi = Nd("MGAPIN", room), gm = Nd("MGAPMID", room), ge = Nd("MGAPEND", room);
                if (gi == null || gm == null || ge == null) { bad.Add(room + " nodes missing"); continue; }
                Vector3 Feet(Vector3 p) => Physics.Raycast(p, Vector3.down, out var fh, 3f, ~0, QueryTriggerInteraction.Ignore) ? fh.point : p + Vector3.down * 1.2f;
                bool Body(Vector3 feet) => !Physics.CheckCapsule(feet + Vector3.up * 0.72f, feet + Vector3.up * (Tuning.BODY_HEIGHT - 0.4f), 0.38f, ~0, QueryTriggerInteraction.Ignore);
                bool open = Body(Feet(gi.position)), narrow = !Body(Feet(gm.position)), deep = !Physics.CheckSphere(ge.position, 0.1f, ~0, QueryTriggerInteraction.Ignore) && !Physics.CheckSphere(gm.position, 0.1f, ~0, QueryTriggerInteraction.Ignore);
                float len = Vector3.Distance(g.position, gm.position) + Vector3.Distance(gm.position, ge.position); shallow = Mathf.Min(shallow, len);
                if (!open || !narrow || !deep) bad.Add($"{room} {At(g.position)} mouth a body can stand in {open} · too narrow for a body further in {narrow} · open to the far end {deep}");
            }
            foreach (var s2 in bad) Debug.Log("MAP4GEO gap " + s2);
            Check("map4_monster_gaps", mouths.Length >= 6 && bad.Count == 0 && shallow > 5f, $"{mouths.Length} monster cracks in room walls (plan promised them; none were built before 10-03) · bad {bad.Count}{(bad.Count > 0 ? " — " + string.Join("; ", bad.Take(5)) : "")} · shortest run from mouth to far end {shallow:0.0} m");
        }
        yield return null;

        // ---- 2d. 천장 구멍 (사용자 10-03 판정 ③ ⓑ "천장 구멍은 저기서 갑자기 나오는 듯"): 굴뚝 꼴 구멍 둘(K · M)이 벽 틈처럼 꺾여 끝이 안 보이고 · 긁힌 자국 · 떨어진 돌이 있나.
        //      빈 노드 CHIM(입 가운데, 천장 높이) · CHIMP1 · CHIMP2(꺾는 점) · CHIMEND(끝 0.4 m 앞) _<방> · 자국 = NOCOL_CHGOUGE_<방> · 돌 = put("stone") 의 Fab 돌(이름에 wd3efb0, 재질 stone_lump)
        {
            var all = m.GetComponentsInChildren<Transform>(); var rows = new List<string>(); int nbad = 0; GameObject plug = null;
            Transform Nd(string pre, string room) => all.FirstOrDefault(t => t.name == pre + "_" + room);
            var stones = filters.Where(f => f.name.Contains("wd3efb0") && f.GetComponent<Renderer>().sharedMaterials.Any(x => x != null && x.name.StartsWith("stone"))).Select(f => f.GetComponent<Renderer>().bounds.center).ToArray();
            var e0 = new[] { "K", "M" }.Select(r => Nd("CHIMEND", r)).FirstOrDefault(t => t != null);
            if (sabotageName == "chimplug" && e0 != null)                                          // 사보타주: 첫 구멍의 끝을 바위(상자)로 메운다
            { plug = GameObject.CreatePrimitive(PrimitiveType.Cube); plug.transform.position = e0.position; plug.transform.localScale = Vector3.one * 1.2f; }
            if (sabotageName == "chimbare") foreach (var f in filters.Where(f => f.name.StartsWith("NOCOL_CHGOUGE_"))) f.gameObject.SetActive(false);   // 사보타주: 긁힌 자국을 지운다 (끈 것은 아래에서 안 센다)
            Physics.SyncTransforms(); yield return null;
            var gouge = m.GetComponentsInChildren<MeshFilter>().Where(f => f.name.StartsWith("NOCOL_CHGOUGE_") && f.sharedMesh != null).ToArray();
            foreach (var room in new[] { "K", "M" })
            {
                Transform c0 = Nd("CHIM", room), c1 = Nd("CHIMP1", room), c2 = Nd("CHIMP2", room), ce = Nd("CHIMEND", room);
                if (c0 == null || c1 == null || c2 == null || ce == null) { rows.Add(room + " nodes missing (CHIM · CHIMP1 · CHIMP2 · CHIMEND)"); nbad++; continue; }
                var path = new[] { c0.position, c1.position, c2.position, ce.position }; string blocked = "";       // (a) 입 → 꺾는 점 → 끝 사이에 아무것도 없다
                for (int i = 1; i < path.Length; i++) if (Physics.Linecast(path[i - 1], path[i], out var lh, ~0, QueryTriggerInteraction.Ignore)) blocked += $" leg {i} hits {lh.collider.name}";
                Vector3 aim = sabotageName == "chimpeek" ? c0.position + Vector3.up : ce.position; int st = 0, vis = 0; string visAt = "";   // (b) 밑 8 m 안 선 자리(돌 더미 위 포함)의 눈 1.7 m 에서 끝이 안 보인다 (사보타주 chimpeek: 과녁 = 입 위 1 m)
                Vector3 under = Physics.Raycast(c0.position, Vector3.down, out var uh, 15f, ~0, QueryTriggerInteraction.Ignore) ? uh.point : c0.position + Vector3.down * 4f;
                for (float x = -8f; x <= 8f; x += 0.5f)
                    for (float z = -8f; z <= 8f; z += 0.5f)
                    {
                        if (x * x + z * z > 64f || !Physics.Raycast(new Vector3(c0.position.x + x, c0.position.y - 0.2f, c0.position.z + z), Vector3.down, out var fh, 12f, ~0, QueryTriggerInteraction.Ignore)) continue;
                        if (fh.point.y > under.y + 2.5f) continue;   // 사람이 못 오르는 턱은 뺀다: K 는 무너져 올라간 구멍 안쪽 판(발 7.1 m)까지 셌다 — 입 밑 바닥(돌 더미 꼭대기 2.0 m) + 2.5 m 위로는 오를 길이 없다
                        if (Physics.CheckCapsule(fh.point + Vector3.up * 0.72f, fh.point + Vector3.up * (Tuning.BODY_HEIGHT - 0.4f), 0.38f, ~0, QueryTriggerInteraction.Ignore)) continue;   // 선 몸이 안 들어가는 자리는 뺀다
                        st++;
                        if (!Physics.Linecast(fh.point + Vector3.up * 1.7f, aim, ~0, QueryTriggerInteraction.Ignore)) { vis++; if (visAt == "") visAt = At(fh.point); }
                    }
                long gt = gouge.Where(f => f.name.StartsWith("NOCOL_CHGOUGE_" + room)).Sum(f => Enumerable.Range(0, f.sharedMesh.subMeshCount).Sum(s => (long)f.sharedMesh.GetIndexCount(s))) / 3;   // (c) 자국 상자 하나 = 삼각형 12
                int nst =stones.Count(p => (p - under).magnitude <= 1.6f);
                bool ok = blocked == "" && st >= 40 && vis == 0 && gt / 12 >= 16 && nst >= 4; if (!ok) nbad++;
                rows.Add($"{room} {At(c0.position)} open to the end {blocked == ""}{blocked} · {st} standing spots within 8 m below, {vis} see the far end{(visAt != "" ? " (first " + visAt + ")" : "")} · gouge strips {gt / 12} · fallen stones within 1.6 m of the floor below {nst}{(ok ? "" : " BAD")}");
            }
            foreach (var s2 in rows) Debug.Log("MAP4GEO chimney " + s2);
            Check("map4_ceiling_holes", nbad == 0, $"ceiling chimneys K · M · bad {nbad} — " + string.Join("; ", rows) + " (want: open from mouth to end · 40+ standing spots, none sees the end · 16+ gouge strips · 4+ fallen stones)");
            if (plug != null) Destroy(plug);
        }
        yield return null;

        // ---- 2e. 바람 관 (국부 선풍기 → 막장): 빈 노드 FAN_<id>(선풍기 출구) · DUCTP_<id>_<00..>(관 가운데 줄, 00 = 출구 쪽) · DFACE_<id>(바람 받는 막장 면 가운데, 바닥 위 1.5 m).
        //      출구에 붙고 · 벽을 안 뚫고 · 끝이 막장에서 7 m 안(법: 풍관 끝은 막장에서 7 m 안) · 선풍기는 막장에서 9 m 밖(막다른 굴 입구에서 5 m 밖을 곧은 거리로 대신)
        {
            var all = m.GetComponentsInChildren<Transform>(); var rows = new List<string>(); int nbad = 0, nfan = 0;
            foreach (var id in new[] { "E1", "z2" })                                               // z2 는 못 지을 수도 있다 — FAN_ 이 있는 것만 (E1 은 꼭)
            {
                var fan = all.FirstOrDefault(t => t.name == "FAN_" + id); var face = all.FirstOrDefault(t => t.name == "DFACE_" + id);
                if (fan == null) { if (id == "E1") { rows.Add("E1 no FAN_E1 node"); nbad++; } continue; }
                nfan++;
                var pts = all.Where(t => t.name.StartsWith("DUCTP_" + id + "_")).OrderBy(t => t.name).Select(t => t.position).ToList();
                if (pts.Count < 2 || face == null) { rows.Add($"{id} duct points {pts.Count} · DFACE node {face != null}"); nbad++; continue; }
                Vector3 fp = face.position;
                if (sabotageName == "ductcut" && nfan == 1 && pts.Count > 2) pts.RemoveAt(pts.Count / 2);   // 사보타주: 가운데 점 하나를 지운다 → 이웃 사이가 3 m 넘는다
                if (sabotageName == "ductfar" && nfan == 1) { var d0 = fp - pts[pts.Count - 1]; fp += (d0.sqrMagnitude > 1e-4f ? d0.normalized : (fp - fan.position).normalized) * 10f; }   // 사보타주: 막장 면을 관 끝에서 10 m 민다
                float start = Vector3.Distance(fan.position, pts[0]), gap = 0f; string through = "";
                for (int i = 1; i < pts.Count; i++)
                {
                    Vector3 a = pts[i - 1], d = pts[i] - a; gap = Mathf.Max(gap, d.magnitude);
                    var hr = Physics.RaycastAll(a, d.normalized, d.magnitude, ~0, QueryTriggerInteraction.Ignore).FirstOrDefault(h => IsShell(h.collider));
                    if (hr.collider != null && through == "") through = $" through rock between {i - 1:00} and {i:00} at {At(hr.point)}";
                }
                float endGap = Vector3.Distance(pts[pts.Count - 1], fp), fanFace = Vector3.Distance(fan.position, fp);
                bool ok = start <= 1.0f && gap <= 3.0f && through == "" && endGap <= 7.0f && fanFace >= 9.0f; if (!ok) nbad++;
                rows.Add($"{id} {At(fan.position)} first point {start:0.00} m from the outlet · {pts.Count} points, widest gap {gap:0.00} m{through} · duct end {endGap:0.0} m from the face · fan {fanFace:0.0} m from the face{(ok ? "" : " BAD")}");
            }
            foreach (var s2 in rows) Debug.Log("MAP4GEO duct " + s2);
            Check("map4_fan_ducts", nfan > 0 && nbad == 0, $"{nfan} fans with ducts · bad {nbad} — " + string.Join("; ", rows) + " (want: first point ≤ 1.0 m · gaps ≤ 3.0 m, none through rock · end ≤ 7 m from the face · fan ≥ 9 m from the face)");
        }
        yield return null;

        // ---- 2f. 압축공기 관 · 호스 · 착암기: 빈 노드 AIRP_<id>_<00..>(관 가운데 줄) · VALVE_<id>_<k>(밸브 꼭지) · HOSEP_<id>_<00..>(호스 줄, 00 = 밸브 쪽) · JACKLEG_<id>(착암기 호스 나오는 점).
        //      관이 바위를 안 뚫고 · 두 끝은 밸브가 아니면 벽 속으로 들어가고(사용자 10-03 "관이 양 끝에서 뚝 끊김") · 호스가 밸브와 착암기를 잇는다
        {
            var all = m.GetComponentsInChildren<Transform>(); var rows = new List<string>(); int nbad = 0, nline = 0; bool sabDone = false;
            foreach (var id in new[] { "E1", "z2", "N2" })
            {
                List<Vector3> Line(string pre) => all.Where(t => t.name.StartsWith(pre + "_" + id + "_")).OrderBy(t => t.name).Select(t => t.position).ToList();
                var pipe = Line("AIRP"); var valves = Line("VALVE"); var hose = Line("HOSEP"); var jack = all.FirstOrDefault(t => t.name == "JACKLEG_" + id);
                if (pipe.Count < 2) { rows.Add($"{id} pipe points {pipe.Count}"); nbad++; continue; }
                nline++;
                bool Valve(Vector3 p) => valves.Any(v => (v - p).sqrMagnitude < 0.25f);                     // 밸브 꼭지에서 0.5 m 안 = 밸브로 끝나는 끝
                if (sabotageName == "pipeend" && !sabDone)                                         // 사보타주: 벽 속으로 들어간 끝 하나를 1 m 떼어 낸다 (관이 굴 한가운데서 뚝 끊긴다)
                    foreach (int e in new[] { 0, pipe.Count - 1 })
                        if (!sabDone && !Valve(pipe[e])) { int nb = e == 0 ? 1 : pipe.Count - 2; pipe[e] -= (pipe[e] - pipe[nb]).normalized * 1.0f; sabDone = true; }
                if (sabotageName == "hoseloose" && !sabDone && hose.Count > 0) { hose[hose.Count - 1] += Vector3.right * 1.0f; sabDone = true; }   // 사보타주: 호스 끝을 착암기에서 1 m 옮긴다
                float gap = 0f; string through = "", loose = "";
                for (int i = 1; i < pipe.Count; i++)                                              // (a) 점 사이 3.5 m 안 · 바위를 안 뚫는다 (두 끝 0.35 m 안은 벽 속으로 들어가는 자리라 뺀다)
                {
                    Vector3 a = pipe[i - 1], d = pipe[i] - a; gap = Mathf.Max(gap, d.magnitude);
                    foreach (var h in Physics.RaycastAll(a, d.normalized, d.magnitude, ~0, QueryTriggerInteraction.Ignore))
                        if (through == "" && IsShell(h.collider) && (h.point - pipe[0]).magnitude > 0.35f && (h.point - pipe[pipe.Count - 1]).magnitude > 0.35f) through = $" through rock between {i - 1:00} and {i:00} at {At(h.point)}";
                }
                foreach (int e in new[] { 0, pipe.Count - 1 })                                    // (b) 밸브가 아닌 끝: 관 방향으로 끝점 앞뒤 0.35 m 안에 바위 겉면 (벽을 따라 걸린 관은 옆 벽이 늘 0.35 m 안이라 여섯 방향으로 재면 굴 한가운데서 끊긴 끝도 통과한다)
                {
                    if (Valve(pipe[e])) continue;
                    Vector3 nb = pipe[e == 0 ? 1 : pipe.Count - 2], d = pipe[e] - nb; float L = d.magnitude;
                    if (!Physics.RaycastAll(nb, d.normalized, L + 0.35f, ~0, QueryTriggerInteraction.Ignore).Any(h => IsShell(h.collider) && h.distance >= L - 0.35f)) loose += $" end {e:00} {At(pipe[e])} stops in the air";
                }
                float hv = hose.Count > 0 && valves.Count > 0 ? valves.Min(v => Vector3.Distance(v, hose[0])) : 99f, hj = hose.Count > 0 && jack != null ? Vector3.Distance(hose[hose.Count - 1], jack.position) : 99f;   // (c) 호스 = 밸브 → 착암기
                bool ok = gap <= 3.5f && through == "" && loose == "" && hv <= 0.35f && hj <= 0.4f; if (!ok) nbad++;
                rows.Add($"{id} {pipe.Count} pipe points, widest gap {gap:0.00} m{through}{loose} · {valves.Count} valves · hose {hose.Count} points: start {hv:0.00} m from a valve, end {hj:0.00} m from the drill{(jack == null ? " (no JACKLEG node)" : "")}{(ok ? "" : " BAD")}");
            }
            foreach (var s2 in rows) Debug.Log("MAP4GEO air " + s2);
            Check("map4_air_lines", nline > 0 && nbad == 0, $"{nline}/3 compressed-air lines · bad {nbad} — " + string.Join("; ", rows) + " (want: gaps ≤ 3.5 m, none through rock · each end at a valve or into rock within 0.35 m along the pipe · hose start ≤ 0.35 m from a valve, end ≤ 0.4 m from the drill)");
        }
        yield return null;

        // ---- 3. 판자 문 칸의 문이 벽에 달려 있나
        {
            var frames = filters.Where(f => f.name.StartsWith("TIMBER_C") || f.name.StartsWith("TIMBER_MAG")).ToArray(); var lone = new List<string>();
            foreach (var f in frames)
            {
                FrameAxes(f, out Vector3 c, out Vector3 u, out _); float floor = f.GetComponent<Renderer>().bounds.min.y; var gaps = new List<string>(); bool ok = true;
                foreach (int sd in new[] { -1, 1 })
                {
                    int hit = 0;
                    foreach (float h in new[] { 0.5f, 1.2f, 2.0f })
                        if (Physics.OverlapSphere(new Vector3(c.x, floor + h, c.z) + u * sd * 0.91f, 0.3f, ~0, QueryTriggerInteraction.Ignore).Any(IsShell)) hit++;
                    if (hit < 2) ok = false; gaps.Add(hit + "/3");
                }
                if (!ok) lone.Add($"{f.name.Substring(7)} {At(c)} rock beside the frame {string.Join(" · ", gaps)}");
            }
            Check("map4_doors_in_wall", frames.Length >= 10 && lone.Count == 0, $"{frames.Length} closet door frames · rock within 0.3 m beside both jambs (at 2 of 3 heights): missing at {lone.Count}{(lone.Count > 0 ? " — " + string.Join("; ", lone) : "")}");
        }

        // ---- 4. 광차 바퀴가 레일 머리 위에 있나
        {
            var carts = filters.Where(f => IsCart(f.name) && f.sharedMesh.isReadable).ToArray(); var off = new List<string>(); int upright = 0;
            foreach (var f in carts)
            {
                if (Vector3.Dot(f.transform.up, Vector3.up) < 0.9f) continue;                      // 넘어진 광차는 뺀다
                upright++; CartAxes(f, out Vector3 c, out Vector3 along, out Vector3 lat);
                var wv = f.sharedMesh.vertices.Select(v => f.transform.TransformPoint(v)).ToArray(); float minY = wv.Min(v => v.y);
                float halfL = wv.Max(v => Mathf.Abs(Vector3.Dot(v - c, along)));
                var low = wv.Where(v => v.y < minY + 0.14f && Mathf.Abs(Vector3.Dot(v - c, lat)) > 0.12f && Mathf.Abs(Vector3.Dot(v - c, along)) < halfL * 0.75f).ToArray();   // 바퀴 밑동 (가운데 고리 · 끝 연결쇠는 뺀다)
                int good = 0; float worstGap = 0f; string what = "";
                foreach (int sa in new[] { -1, 1 })
                    foreach (int sl in new[] { -1, 1 })
                    {
                        var qv = low.Where(v => Mathf.Sign(Vector3.Dot(v - c, along)) == sa && Mathf.Sign(Vector3.Dot(v - c, lat)) == sl).ToArray();
                        if (qv.Length == 0) { what = "no wheel found"; continue; }
                        float a0 = qv.Average(v => Vector3.Dot(v - c, along)), l0 = qv.Min(v => Mathf.Abs(Vector3.Dot(v - c, lat))), l1 = qv.Max(v => Mathf.Abs(Vector3.Dot(v - c, lat))); bool on = false; float best = 9f;
                        for (int k = 0; k <= 8; k++)
                        {
                            float l = Mathf.Lerp(l0, l1, k / 8f); Vector3 o = c + along * a0 + lat * (sl * l); o.y = minY + 0.3f;
                            float wheelY = qv.Where(v => Mathf.Abs(Mathf.Abs(Vector3.Dot(v - c, lat)) - l) < 0.02f).Select(v => v.y).DefaultIfEmpty(99f).Min();
                            foreach (var h in Physics.RaycastAll(o, Vector3.down, 0.9f, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance))
                            {
                                if (h.collider.gameObject == f.gameObject) continue;
                                bool railHead = h.collider.name.Contains("ufekae") && h.point.y > h.collider.bounds.max.y - 0.03f;
                                float gap = wheelY - h.point.y; if (railHead && Mathf.Abs(gap) < Mathf.Abs(best)) best = gap;
                                if (railHead && Mathf.Abs(gap) <= 0.03f) on = true;
                                break;
                            }
                        }
                        if (on) good++; else { worstGap = best; what = best > 8f ? "no rail head under the wheel" : $"wheel {best * 100f:+0;-0} cm from the rail head"; }
                        if (!on) Debug.Log($"MAP4GEO wheel {f.name} along {a0:0.00} side {sl} lateral {l0:0.000}..{l1:0.000} lowest {qv.Min(v => v.y) - minY:0.000} best gap {best:0.000} · under it: " + string.Join(", ", Physics.RaycastAll(c + along * a0 + lat * (sl * (l0 + l1) * 0.5f) + Vector3.up * 0.5f, Vector3.down, 1.5f).OrderBy(h => h.distance).Select(h => $"{h.collider.name}@{h.point.y - minY:0.000} [bounds y {h.collider.bounds.min.y - minY:0.000}..{h.collider.bounds.max.y - minY:0.000} rot {h.collider.transform.eulerAngles} scale {h.collider.transform.lossyScale} lat {Vector3.Dot(h.collider.bounds.center - c, lat):0.000}]")));
                    }
                if (good < 4) off.Add($"{f.name.Substring(0, 9)} {At(c)} wheels on rail {good}/4 ({what})");
            }
            foreach (var s in off.Take(40)) Debug.Log("MAP4GEO cart " + s);
            Check("map4_carts_on_rails", upright >= 10 && off.Count == 0, $"{upright} upright carts ({carts.Length - upright} tipped ones skipped) · all four wheels within 3 cm above a rail head: off at {off.Count}{(off.Count > 0 ? " — " + string.Join("; ", off.Take(6)) : "")}");
        }
        yield return null;

        // ---- 5. 저절로 숙여지는 곳 (선 몸이 들어가는 자리에서 머리 위 1.95 m 안에 무엇이 있다)
        {
            var low = new List<(Vector3 p, string what, float clear)>(); int samples = 0, standable = 0; float lowestCentre = 99f; string lowestAt = "";
            bool Stands(Vector3 feet) => !Physics.CheckCapsule(feet + Vector3.up * 0.72f, feet + Vector3.up * (Tuning.BODY_HEIGHT - 0.4f), 0.38f, ~0, QueryTriggerInteraction.Ignore);   // 선 몸(반지름 0.4 · 키 1.8). 발목 0.32 m 까지는 넘어 오른다(침목 · 레일)
            void Probe(Vector3 at, bool centre)
            {
                samples++;
                var mound = Physics.RaycastAll(at + Vector3.up * 4f, Vector3.down, 4f, ~0, QueryTriggerInteraction.Ignore).Where(h => h.collider.name.StartsWith("HEAP_")).OrderBy(h => h.distance).FirstOrDefault();
                if (mound.collider != null) at = mound.point;                                      // 돌 · 석탄 둔덕 위: 둔덕 겉에 선다 (속 빈 그물이라 바닥에서 재면 둔덕 속에 서서 덩이 밑에서 숙이는 것으로 잘못 셌다 — 10-03)
                if (!Physics.Raycast(at + Vector3.up * 1.0f, Vector3.down, out var fl, 2.6f, ~0, QueryTriggerInteraction.Ignore)) return;
                if (!Stands(fl.point)) return;
                standable++;
                if (centre && Physics.Raycast(fl.point + Vector3.up * 0.5f, Vector3.up, out var up, 20f, ~0, QueryTriggerInteraction.Ignore) && up.distance + 0.5f < lowestCentre) { lowestCentre = up.distance + 0.5f; lowestAt = $"{At(fl.point)} under {up.collider.name}"; }
                if (Map4.LowAbove(fl.point, out var h) && !low.Any(x => (x.p - fl.point).sqrMagnitude < 1f)) low.Add((fl.point, h.collider.name, h.point.y - fl.point.y));
            }
            foreach (var a in areas)
            {
                for (float x = -a.w / 2 + 0.3f; x <= a.w / 2 - 0.3f; x += 0.5f)
                    for (float z = -a.d / 2 + 0.3f; z <= a.d / 2 - 0.3f; z += 0.5f) Probe(a.c + a.ax * x + a.az * z, false);
                yield return null;
            }
            foreach (var w in walks)
            {
                for (int i = 1; i < w.pts.Count; i++)
                {
                    Vector3 p0 = w.pts[i - 1], p1 = w.pts[i]; float L = Flat(p1 - p0); if (L < 0.1f) continue;
                    Vector3 side = Vector3.Cross(Vector3.up, Flat3(p1 - p0).normalized);
                    for (float t = 0f; t <= L; t += 0.25f)
                        for (float s = -w.hw + 0.3f; s <= w.hw - 0.3f + 1e-3f; s += 0.3f) Probe(Vector3.Lerp(p0, p1, t / L) + side * s, Mathf.Abs(s) < 0.16f);
                }
                yield return null;
            }
            foreach (var x in low.Take(60)) Debug.Log($"MAP4GEO auto-crouch at {At(x.p)} under {x.what} ({x.clear:0.00} m above the feet)");
            Check("map4_no_auto_crouch", standable > 20000 && low.Count == 0 && lowestCentre >= 2.1f, $"{samples} floor samples in rooms, scenes and tunnels, {standable} where a standing body fits · places that force a crouch (something lower than {Map4.LowAboveM:0.00} m above the feet): {low.Count}" +
                (low.Count > 0 ? " — " + string.Join("; ", low.Take(10).Select(x => $"{At(x.p)} {x.what} {x.clear:0.00} m")) : "") + $" · lowest thing above a tunnel centre line {lowestCentre:0.00} m at {lowestAt}");
        }

        // ---- 6. 굴마다 몸을 밀어 끝까지 (막힘 · 떨어짐)
        {
            var stuck = new List<string>(); var fell = new List<string>(); float walked = 0f; int reached = 0, legs = 0;
            cc.enabled = true;
            foreach (var w in walks)
            {
                Seat(cc, w.pts[0]);
                for (int i = 1; i < w.pts.Count; i++)
                {
                    Vector3 target = w.pts[i], from = w.pts[i - 1]; float legLen = Flat(target - from); if (legLen < 0.3f) continue;
                    legs++; float best = Flat(target - cc.transform.position); int stall = 0, guard = (int)(best / 0.1f * 3f) + 80; bool dropped = false;
                    while (Flat(target - cc.transform.position) > 0.4f && guard-- > 0)
                    {
                        Vector3 pos = cc.transform.position, dir = Flat3(target - pos).normalized;
                        cc.Move(dir * 0.1f); cc.Move(Vector3.down * 0.25f);
                        Vector3 np = cc.transform.position; walked += Flat(np - pos);
                        float dn = Flat(target - np); if (dn < best - 0.02f) { best = dn; stall = 0; } else if (++stall > 30) break;
                        float pathY = Mathf.Lerp(from.y, target.y, 1f - Mathf.Clamp01(dn / legLen));
                        if (np.y < pathY - 1.3f && !dropped) { dropped = true; fell.Add($"{w.name} at {At(np)} ({pathY - np.y:0.0} m below the path)"); }
                    }
                    if (Flat(target - cc.transform.position) <= 0.4f) reached++;
                    else
                    {
                        Vector3 pos = cc.transform.position, dir = Flat3(target - pos).normalized; cc.enabled = false;
                        string what = Physics.SphereCast(pos + Vector3.up * 0.9f - dir * 0.3f, 0.35f, dir, out var fh, 1.2f, ~0, QueryTriggerInteraction.Ignore) ? fh.collider.name : "?";
                        cc.enabled = true; stuck.Add($"{w.name} at {At(pos)} {Flat(target - pos):0.0} m short, against {what}");
                        Seat(cc, target);
                    }
                }
                yield return null;
            }
            cc.enabled = false;
            foreach (var s in stuck.Take(60)) Debug.Log("MAP4GEO stuck " + s);
            Check("map4_walk_through", legs > 40 && stuck.Count == 0 && fell.Count == 0, $"pushed the body along {walks.Count} lines, {legs} legs, {walked:0} m · reached {reached}/{legs} · stuck {stuck.Count}{(stuck.Count > 0 ? " — " + string.Join("; ", stuck.Take(8)) : "")} · fell {fell.Count}{(fell.Count > 0 ? " — " + string.Join("; ", fell.Take(5)) : "")}");
        }
        cc.enabled = true; player.enabled = true;
    }

    class FloatNode { public MeshFilter f; public Collider col; public int island; public Bounds b; public Vector3[] samples; public bool grounded, whole; }

    static float Len(List<Vector3> p) { float l = 0f; for (int i = 1; i < p.Count; i++) l += Vector3.Distance(p[i - 1], p[i]); return l; }

    // 몸을 그 점 밑 바닥에 세운다 (CharacterController 를 껐다 켠다)
    static void Seat(CharacterController cc, Vector3 at)
    {
        cc.enabled = false;
        Vector3 p = Physics.Raycast(at + Vector3.up * 1.0f, Vector3.down, out var h, 3f, ~0, QueryTriggerInteraction.Ignore) ? h.point : at;
        cc.transform.position = p + Vector3.up * 0.08f; Physics.SyncTransforms(); cc.enabled = true;
    }

    // 문틀의 가운데 · 폭 방향(u) · 두께 방향(n) — 수평면에서 점들이 가장 길게 퍼진 쪽이 폭
    static void FrameAxes(MeshFilter f, out Vector3 c, out Vector3 u, out Vector3 n) { Spread(f, out c, out u, out n); }
    // 광차의 가운데 · 긴 쪽(along) · 옆(lat)
    static void CartAxes(MeshFilter f, out Vector3 c, out Vector3 along, out Vector3 lat) { Spread(f, out c, out along, out lat); }
    static void Spread(MeshFilter f, out Vector3 c, out Vector3 major, out Vector3 minor)
    {
        var v = f.sharedMesh.vertices; var l2w = f.transform.localToWorldMatrix; var b = new Bounds(l2w.MultiplyPoint3x4(v[0]), Vector3.zero);
        double sxx = 0, sxz = 0, szz = 0, mx = 0, mz = 0; var w = new Vector3[v.Length];
        for (int i = 0; i < v.Length; i++) { w[i] = l2w.MultiplyPoint3x4(v[i]); b.Encapsulate(w[i]); mx += w[i].x; mz += w[i].z; }
        mx /= v.Length; mz /= v.Length;
        foreach (var p in w) { double dx = p.x - mx, dz = p.z - mz; sxx += dx * dx; sxz += dx * dz; szz += dz * dz; }
        float ang = 0.5f * Mathf.Atan2((float)(2 * sxz), (float)(sxx - szz));
        major = new Vector3(Mathf.Cos(ang), 0f, Mathf.Sin(ang)); minor = new Vector3(-major.z, 0f, major.x); c = b.center;
    }

    static bool UnderRail(MeshFilter cart) => Physics.RaycastAll(cart.GetComponent<Renderer>().bounds.center, Vector3.down, 2f).Any(h => h.collider.name.Contains("ufekae"));
}
