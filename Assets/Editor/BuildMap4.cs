using System.Diagnostics;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.AI;
using Debug = UnityEngine.Debug;

// GAME-1 (제안서 docs/제안서_GAME1_MAP4에서_놀기.md): MAP4 괴물이 걸을 바닥(길찾기)을 굽는다. Map4.glb 를 다시 구우면 이것도 다시.
//   "C:/Program Files/Unity/Hub/Editor/6000.4.7f1/Editor/Unity.exe" -batchmode -nographics -projectPath . -executeMethod BuildMap4.Bake -logFile build/map4nav.log -quit
// 부딪힘 규칙은 게임이 맵을 놓을 때(FabTest.Spawn)와 같다: NOCOL_ 빼고 · 매단 전등(vgyidfpaw) 빼고 · COLONLY_ 는 부딪힘만. 괴물 크기 = 프로젝트 길찾기 설정(키 2.0 · 디딤 0.75)에 반지름만 Tuning.MAP4_STALKER_R (게임에서 괴물 부딪힘 둘레도 같은 값 — Director.Begin).
// 저장 = Assets/Fab/Resources/Map4_NavMesh.asset (Map4.glb 처럼 git 에 안 들어간다 — Fab 모양을 그대로 담는다). 지스타 제출 세션이 고쳐 둔 BuildM1.cs 를 건드리지 않으려고 따로 둔다
public static class BuildMap4
{
    const string MapPath = "Assets/Fab/Resources/Map4.glb";
    const string NavPath = "Assets/Fab/Resources/Map4_NavMesh.asset";

    public static void Bake()
    {
        var sw = Stopwatch.StartNew();
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(MapPath);
        if (prefab == null) { Debug.LogError($"MAP4NAV no {MapPath} (SCENE=m EXPORT_GLB=... blender/map/scene_mock.py)"); EditorApplication.Exit(2); return; }
        var go = (GameObject)Object.Instantiate(prefab, Map4.Offset, Quaternion.identity);
        int cols = 0;
        foreach (var mf in go.GetComponentsInChildren<MeshFilter>().Where(m => m.sharedMesh != null && !m.name.StartsWith("NOCOL_") && !m.name.Contains("vgyidfpaw")))
        { mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh; cols++; }
        // 괴물 몸 크기 = 프로젝트 길찾기 설정(0 번) 사본에 반지름 MAP4_STALKER_R. -navRadius · -navHeight · -navClimb 로 바꿔 굽기 (진단용)
        var settings = NavMesh.GetSettingsByID(0);
        var args = System.Environment.GetCommandLineArgs();
        float Arg(string k, float d) { int i = System.Array.IndexOf(args, k); return i >= 0 && i + 1 < args.Length && float.TryParse(args[i + 1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float v) ? v : d; }
        settings.agentRadius = Arg("-navRadius", Tuning.MAP4_STALKER_R); settings.agentHeight = Arg("-navHeight", settings.agentHeight); settings.agentClimb = Arg("-navClimb", settings.agentClimb);
        var sources = new System.Collections.Generic.List<NavMeshBuildSource>();
        NavMeshBuilder.CollectSources(go.transform, ~0, NavMeshCollectGeometry.PhysicsColliders, 0, new System.Collections.Generic.List<NavMeshBuildMarkup>(), sources);
        var bounds = new Bounds(Map4.Offset, new Vector3(800f, 200f, 800f));
        var data = NavMeshBuilder.BuildNavMeshData(settings, sources, bounds, Vector3.zero, Quaternion.identity);
        NavMesh.AddNavMeshData(data);
        Debug.Log($"MAP4NAV monster body radius {settings.agentRadius:0.00} m · height {settings.agentHeight:0.00} m · step {settings.agentClimb:0.00} m · slope {settings.agentSlope:0}° · sources {sources.Count}");
        AssetDatabase.DeleteAsset(NavPath);
        AssetDatabase.CreateAsset(data, NavPath);
        AssetDatabase.SaveAssets();
        var tri = NavMesh.CalculateTriangulation();
        double area = 0;
        for (int i = 0; i + 2 < tri.indices.Length; i += 3)
            area += Vector3.Cross(tri.vertices[tri.indices[i + 1]] - tri.vertices[tri.indices[i]], tri.vertices[tri.indices[i + 2]] - tri.vertices[tri.indices[i]]).magnitude * 0.5;
        Debug.Log($"MAP4NAV baked {NavPath}: colliders {cols} · navmesh {tri.vertices.Length} verts {tri.indices.Length / 3} tris · area {area:0} m2 · {sw.Elapsed.TotalSeconds:0} s");
        // 방마다 승강장(z6)에서 괴물 길이 이어지나 — 끊긴 곳은 길이 멈춘 자리를 적는다 (바람문 · 계단 · 낮은 곳)
        var areas = go.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("AREA_") && t.name.Split('_').Length == 4).ToArray();
        var z6 = areas.FirstOrDefault(t => t.name.StartsWith("AREA_z6_"));
        if (z6 != null && NavMesh.SamplePosition(z6.position, out var h0, 6f, NavMesh.AllAreas))
            foreach (var a in areas.OrderBy(t => t.name))
            {
                var path = new NavMeshPath(); string st;
                if (!NavMesh.SamplePosition(a.position, out var h1, 6f, NavMesh.AllAreas)) st = "NO FLOOR within 6 m";
                else { NavMesh.CalculatePath(h0.position, h1.position, NavMesh.AllAreas, path); var end = path.corners.Length > 0 ? path.corners[path.corners.Length - 1] : h0.position; st = path.status == NavMeshPathStatus.PathComplete ? "ok" : $"{path.status} — stops at ({end.x:0.0}, {end.y - Map4.Offset.y:0.0}, {end.z:0.0}), {Vector3.Distance(end, h1.position):0} m short"; }
                Debug.Log($"MAP4NAV from z6 to {a.name.Split('_')[1]}: {st}");
            }
        EditorApplication.Exit(tri.indices.Length > 0 ? 0 : 3);
    }
}
