using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.AI;

// MAP2 부스 맵 구조 재기 — 검사 M1Check.BoothStage 가 쓴다. 제안서 docs/제안서_MAP2_맵_5배.md 의 잰 값을 평면도(blender/map/map2_plan.py)
// 대신 실제 길찾기 바닥(NavMesh, 괴물 반지름 0.6 m 를 뺀 바닥)으로 다시 잰다. 바닥을 위에서 본 칸(0.25 m)으로 그린다.
//   Loops  : 바닥에 둘러싸인 바위 기둥마다 한 바퀴 길이 (map2_plan.py measure 와 같은 방법)
//   Wander : 바닥 칸을 가는 선(뼈대)으로 깎아 갈림·막다른 점 그래프 → 되돌아서지 않고 갈림마다 아무 쪽이나 골라 걸어 정거장까지 (map2_plan.py wander)
public static class BoothMeasure
{
    public const float Cell = 0.25f;

    public class Grid
    {
        public bool[,] w;
        public float x0, z0;
        public int nx, nz;
        public Vector2 Pos(int i, int j) => new Vector2(x0 + (i + 0.5f) * Cell, z0 + (j + 0.5f) * Cell);
        public bool In(int i, int j) => i >= 0 && j >= 0 && i < nx && j < nz;
    }

    // 길찾기 바닥 삼각형을 칸에 칠한다. extra = 더 칠할 선(개구멍: 사람만 지나가는 길) — 굵기 0.5 m
    public static Grid Raster(NavMeshTriangulation tri, IEnumerable<(Vector3 a, Vector3 b)> extra = null)
    {
        var v = tri.vertices;
        float minX = v.Min(p => p.x) - 2f, minZ = v.Min(p => p.z) - 2f, maxX = v.Max(p => p.x) + 2f, maxZ = v.Max(p => p.z) + 2f;
        var g = new Grid { x0 = minX, z0 = minZ, nx = Mathf.CeilToInt((maxX - minX) / Cell), nz = Mathf.CeilToInt((maxZ - minZ) / Cell) };
        g.w = new bool[g.nx, g.nz];
        for (int k = 0; k < tri.indices.Length; k += 3)
        {
            Vector2 a = XZ(v[tri.indices[k]]), b = XZ(v[tri.indices[k + 1]]), c = XZ(v[tri.indices[k + 2]]);
            float area = Cross(b - a, c - a);
            if (Mathf.Abs(area) < 1e-6f) continue;
            int i0 = Idx(Mathf.Min(a.x, b.x, c.x) - g.x0), i1 = Idx(Mathf.Max(a.x, b.x, c.x) - g.x0), j0 = Idx(Mathf.Min(a.y, b.y, c.y) - g.z0), j1 = Idx(Mathf.Max(a.y, b.y, c.y) - g.z0);
            for (int i = i0; i <= i1; i++)
                for (int j = j0; j <= j1; j++)
                {
                    Vector2 p = g.Pos(i, j);
                    float u = Cross(b - a, p - a) / area, s = Cross(c - b, p - b) / area, t = Cross(a - c, p - c) / area;
                    if (u >= 0f && s >= 0f && t >= 0f && g.In(i, j)) g.w[i, j] = true;
                }
        }
        if (extra != null)
            foreach (var (a3, b3) in extra)
            {
                Vector2 a = XZ(a3), b = XZ(b3);
                int n = Mathf.CeilToInt((b - a).magnitude / (Cell * 0.5f));
                for (int k = 0; k <= n; k++)
                {
                    Vector2 p = Vector2.Lerp(a, b, k / (float)n);
                    for (int di = -1; di <= 1; di++)
                        for (int dj = -1; dj <= 1; dj++)
                        {
                            int i = Idx(p.x - g.x0) + di, j = Idx(p.y - g.z0) + dj;
                            if (g.In(i, j)) g.w[i, j] = true;
                        }
                }
            }
        return g;
    }

    // 바닥에 둘러싸인 바위 덩어리(칸 가장자리에 안 닿는 것) 마다 한 바퀴 길이 = 둘레에 붙은 바닥 칸 수 × 칸 × 0.9 (map2_plan.py 와 같다). 1 m² 밑 덩어리는 기둥이 아니다(바닥 그물의 틈)
    public static List<float> Loops(Grid g)
    {
        var lab = new int[g.nx, g.nz];
        var laps = new List<float>();
        int id = 0;
        var q = new Queue<(int, int)>();
        for (int si = 0; si < g.nx; si++)
            for (int sj = 0; sj < g.nz; sj++)
            {
                if (g.w[si, sj] || lab[si, sj] != 0) continue;
                id++;
                lab[si, sj] = id; q.Enqueue((si, sj));
                int cells = 0; bool border = false;
                var rim = new HashSet<int>();
                while (q.Count > 0)
                {
                    var (i, j) = q.Dequeue(); cells++;
                    if (i == 0 || j == 0 || i == g.nx - 1 || j == g.nz - 1) border = true;
                    foreach (var (di, dj) in Four)
                    {
                        int a = i + di, b = j + dj;
                        if (!g.In(a, b)) continue;
                        if (g.w[a, b]) rim.Add(a * g.nz + b);
                        else if (lab[a, b] == 0) { lab[a, b] = id; q.Enqueue((a, b)); }
                    }
                }
                if (!border && cells * Cell * Cell >= 1f) laps.Add(rim.Count * Cell * 0.9f);
            }
        return laps;
    }

    public struct WanderResult { public float within300, median; public int nodes, edges, deadEnds, homeNodes, runs; }

    // 길 잃은 사람 runs 번: 뼈대 그래프의 아무 굴 한가운데서 시작해 되돌아서지 않고(막다른 곳에서만 돌아선다) 갈림마다 아무 쪽이나 → 정거장 광장(home 네모)까지 걸은 거리
    public static WanderResult Wander(Grid g, Vector2 homeMin, Vector2 homeMax, int runs, int seed, float cap = 3000f)
    {
        var sk = Thin(g);
        var (nodePos, edges) = Graph(g, sk);
        // 막다른 짧은 가지(방 모서리로 뻗은 뼈대 · 4 m 밑)를 쳐 낸다 — 두 번
        for (int pass = 0; pass < 3; pass++)
        {
            var deg = new int[nodePos.Count];
            foreach (var e in edges) { deg[e.a]++; deg[e.b]++; }
            edges = edges.Where(e => !((deg[e.a] == 1 || deg[e.b] == 1) && e.a != e.b && e.len < 4f)).ToList();
        }
        var adj = new List<(int to, float len)>[nodePos.Count];
        for (int k = 0; k < adj.Length; k++) adj[k] = new List<(int, float)>();
        foreach (var e in edges) { adj[e.a].Add((e.b, e.len)); adj[e.b].Add((e.a, e.len)); }
        var home = new bool[nodePos.Count];
        for (int k = 0; k < nodePos.Count; k++)
        {
            Vector2 p = nodePos[k];
            home[k] = adj[k].Count > 0 && p.x >= homeMin.x - 0.5f && p.x <= homeMax.x + 0.5f && p.y >= homeMin.y - 0.5f && p.y <= homeMax.y + 0.5f;
        }
        var linked = new bool[nodePos.Count];                                   // 정거장에서 이어진 곳만 (막힘 돌무더기 너머 닫힌 구역에서는 출발하지 않는다)
        var q = new Queue<int>(Enumerable.Range(0, nodePos.Count).Where(k => home[k]));
        foreach (int k in q) linked[k] = true;
        while (q.Count > 0) foreach (var o in adj[q.Dequeue()]) if (!linked[o.to]) { linked[o.to] = true; q.Enqueue(o.to); }
        var start = edges.Where(e => !home[e.a] && !home[e.b] && linked[e.a]).ToList();
        var r = new WanderResult { nodes = adj.Count(l => l.Count > 0), edges = edges.Count, deadEnds = Enumerable.Range(0, adj.Length).Count(k => adj[k].Count == 1 && !home[k]), homeNodes = home.Count(h => h), runs = runs };
        if (start.Count == 0 || r.homeNodes == 0) return r;
        float total = start.Sum(e => e.len);
        var rng = new System.Random(seed);
        var dists = new List<float>();
        for (int n = 0; n < runs; n++)
        {
            float pick = (float)rng.NextDouble() * total; var st = start[start.Count - 1];
            foreach (var e in start) { if (pick < e.len) { st = e; break; } pick -= e.len; }
            int prev = st.a, cur = st.b; float d = st.len * (float)rng.NextDouble();
            while (d < cap && !home[cur])
            {
                var opts = adj[cur].Where(o => o.to != prev).ToList();
                if (opts.Count == 0) opts = adj[cur];
                var o = opts[rng.Next(opts.Count)];
                prev = cur; cur = o.to; d += o.len;
            }
            dists.Add(d);
        }
        dists.Sort();
        r.within300 = dists.Count(d => d <= 300f) * 100f / runs;
        r.median = dists[runs / 2];
        return r;
    }

    // Zhang-Suen 가늘게 깎기 — 바닥 칸을 한 칸 굵기 뼈대로
    static bool[,] Thin(Grid g)
    {
        var s = (bool[,])g.w.Clone();
        var del = new List<(int, int)>();
        bool changed = true;
        while (changed)
        {
            changed = false;
            for (int pass = 0; pass < 2; pass++)
            {
                del.Clear();
                for (int i = 1; i < g.nx - 1; i++)
                    for (int j = 1; j < g.nz - 1; j++)
                    {
                        if (!s[i, j]) continue;
                        bool p2 = s[i, j + 1], p3 = s[i + 1, j + 1], p4 = s[i + 1, j], p5 = s[i + 1, j - 1], p6 = s[i, j - 1], p7 = s[i - 1, j - 1], p8 = s[i - 1, j], p9 = s[i - 1, j + 1];
                        int b = (p2 ? 1 : 0) + (p3 ? 1 : 0) + (p4 ? 1 : 0) + (p5 ? 1 : 0) + (p6 ? 1 : 0) + (p7 ? 1 : 0) + (p8 ? 1 : 0) + (p9 ? 1 : 0);
                        if (b < 2 || b > 6) continue;
                        int a = (!p2 && p3 ? 1 : 0) + (!p3 && p4 ? 1 : 0) + (!p4 && p5 ? 1 : 0) + (!p5 && p6 ? 1 : 0) + (!p6 && p7 ? 1 : 0) + (!p7 && p8 ? 1 : 0) + (!p8 && p9 ? 1 : 0) + (!p9 && p2 ? 1 : 0);
                        if (a != 1) continue;
                        if (pass == 0 ? (p2 && p4 && p6) || (p4 && p6 && p8) : (p2 && p4 && p8) || (p2 && p6 && p8)) continue;
                        del.Add((i, j));
                    }
                foreach (var (i, j) in del) s[i, j] = false;
                changed |= del.Count > 0;
            }
        }
        return s;
    }

    struct Edge { public int a, b; public float len; }

    // 뼈대 → 그래프. 이웃이 둘이 아닌 칸 = 점(붙어 있는 것끼리 하나), 점 사이를 따라가며 길이를 잰다
    static (List<Vector2>, List<Edge>) Graph(Grid g, bool[,] sk)
    {
        int Deg(int i, int j) { int n = 0; foreach (var (di, dj) in Eight) if (g.In(i + di, j + dj) && sk[i + di, j + dj]) n++; return n; }
        var node = new int[g.nx, g.nz];
        var pos = new List<Vector2>();
        var q = new Queue<(int, int)>();
        for (int si = 0; si < g.nx; si++)
            for (int sj = 0; sj < g.nz; sj++)
            {
                if (!sk[si, sj] || node[si, sj] != 0 || Deg(si, sj) == 2) continue;
                int id = pos.Count + 1; Vector2 sum = Vector2.zero; int cnt = 0;
                node[si, sj] = id; q.Enqueue((si, sj));
                while (q.Count > 0)
                {
                    var (i, j) = q.Dequeue(); sum += g.Pos(i, j); cnt++;
                    foreach (var (di, dj) in Eight)
                    {
                        int a = i + di, b = j + dj;
                        if (g.In(a, b) && sk[a, b] && node[a, b] == 0 && Deg(a, b) != 2) { node[a, b] = id; q.Enqueue((a, b)); }
                    }
                }
                pos.Add(sum / cnt);
            }
        var edges = new List<Edge>();
        var seen = new bool[g.nx, g.nz];
        for (int si = 0; si < g.nx; si++)
            for (int sj = 0; sj < g.nz; sj++)
            {
                if (node[si, sj] == 0) continue;
                foreach (var (di, dj) in Eight)
                {
                    int ci = si + di, cj = sj + dj;
                    if (!g.In(ci, cj) || !sk[ci, cj]) continue;
                    if (node[ci, cj] != 0)
                    {
                        if (node[ci, cj] > node[si, sj]) edges.Add(new Edge { a = node[si, sj] - 1, b = node[ci, cj] - 1, len = Cell * Mathf.Sqrt(di * di + dj * dj) });
                        continue;
                    }
                    if (seen[ci, cj]) continue;
                    int pi = si, pj = sj; float len = Cell * Mathf.Sqrt(di * di + dj * dj);
                    int end = -1;
                    while (true)
                    {
                        seen[ci, cj] = true;
                        int ni = -1, nj = -1;
                        foreach (var (ei, ej) in Eight)
                        {
                            int a = ci + ei, b = cj + ej;
                            if (!g.In(a, b) || !sk[a, b] || (a == pi && b == pj)) continue;
                            if (node[a, b] != 0)
                            {
                                if (node[a, b] == node[si, sj] && len < Cell * 3f) continue;   // 막 떠난 점의 다른 칸
                                ni = a; nj = b; break;                                          // 점에 닿으면 끝
                            }
                            if (!seen[a, b] && ni < 0) { ni = a; nj = b; }
                        }
                        if (ni < 0) break;                                      // 뼈대가 끊겼다(닫힌 고리 끝) — 버린다
                        len += Cell * Mathf.Sqrt((ni - ci) * (ni - ci) + (nj - cj) * (nj - cj));
                        pi = ci; pj = cj; ci = ni; cj = nj;
                        if (node[ci, cj] != 0) { end = node[ci, cj] - 1; break; }
                    }
                    if (end >= 0) edges.Add(new Edge { a = node[si, sj] - 1, b = end, len = len });
                }
            }
        return (pos, edges);
    }

    // 시작 자리에서 길찾기로 닿는 바닥 넓이 (삼각형 가운데마다 길을 찾는다 — 막힘 돌무더기가 파낸 너머는 안 센다)
    public static float ReachArea(Vector3 from)
    {
        var tri = NavMesh.CalculateTriangulation();
        var path = new NavMeshPath();
        float area = 0f;
        for (int k = 0; k < tri.indices.Length; k += 3)
        {
            Vector3 a = tri.vertices[tri.indices[k]], b = tri.vertices[tri.indices[k + 1]], c = tri.vertices[tri.indices[k + 2]];
            if (NavMesh.CalculatePath(from, (a + b + c) / 3f, NavMesh.AllAreas, path) && path.status == NavMeshPathStatus.PathComplete)
                area += Vector3.Cross(b - a, c - a).magnitude * 0.5f;
        }
        return area;
    }

    static readonly (int, int)[] Four = { (1, 0), (-1, 0), (0, 1), (0, -1) };
    static readonly (int, int)[] Eight = { (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1) };
    static Vector2 XZ(Vector3 p) => new Vector2(p.x, p.z);
    static float Cross(Vector2 a, Vector2 b) => a.x * b.y - a.y * b.x;
    static int Idx(float d) => Mathf.FloorToInt(d / Cell);
}
