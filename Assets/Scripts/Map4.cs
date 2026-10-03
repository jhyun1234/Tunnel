using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Rendering.Universal;

// MAP4 1편 전체 (사용자 10-01 "전체 맵을 끝까지 만들어라. 그 뒤에 텍스처 · 구조를 말하겠다").
// exe 를 -map4 로 띄우면 인트로 → 시작 → 부스 맵 아래(Offset) 새 맵 승강장에서 시작한다 (괴물 없음 — 구조 · 텍스처 판정용).
// Assets/Fab/Resources/Map4.glb 는 git 에 없다(Fab 재배포 금지). 만드는 법: SCENE=m EXPORT_GLB=Assets/Fab/Resources/Map4.glb blender -b --factory-startup -P blender/map/scene_mock.py
// 빛 · 화각 = 영상 재현 판정값 Tuning.FAB_* (전등 세기 · 반경 · 주황 · 화각 85 · 은은한 빛 · 색보정). ZL_<rrggbb>_<i> = 구역 입구 색 등(카드 15).
// 판정 키: ] 다음 · [ 앞 장면 자리 (CAM_<구역>_<그림> = Blender 시안과 같은 자리, 처음은 CAM_start 승강장)
// 밝기 판정 키(10-01 v2 "전체가 많이 어둡다" — 전등을 101개로 늘리고 줄에 매달아 내려도 바닥은 어둡다 → 세기 · 거리는 사용자가 고른다, -fabvideo 와 같은 키):
// 1 2 전등 세기 · 3 4 빛이 닿는 거리 · 9 0 은은한 빛 · B 판정값(Tuning.FAB_*)으로. 값은 화면 왼쪽 아래. 이 모드에선 DevHud 를 끈다(같은 키).
// TEX-1 (제안서 docs/제안서_TEX1_층과_환경에_따라_잇는_벽과_바닥.md, 사용자 10-01 승인): 굴 그물의 재질 칸 이름 RK_<벽A>_<벽B>_<바닥A>_<바닥B>(번호 = 비교 그림 번호)를 읽어
// 부스에서 통과한 바위 재질 MineRock 의 사본에 사진(Assets/Fab/Resources/Rock/ — git 에 없다, python tools/pack_rock_tex.py 로 만든다)을 끼운다. 섞는 양은 Blender 가 점마다 적어 두었다(scene_mock.py tex1_paint — 첫 UV = 벽 · 바닥 이음 자리, 셋째 UV = 젖음 · 큰 길).
// 벽 ② 는 따로 된 사진이 아니라 "큰 길에서 ③ 을 더 어둡게" 다 — 재질 칸에는 ③ 으로 적히고 어둡기만 점마다(전역 _Map4RoadDim = ② 어둡기 ÷ ③ 어둡기).
// 판정 키: T 구역 켬 · 끔(끄면 벽 전부 ③ · 바닥 전부 ②) · G 사진 대신 번호 색 · Tab 사진 고르기 → 5 6 그 사진 어둡기 ∓ · 7 8 이음 길이 ∓ 1 m(최대 20) · − = 얼룩 정도 · ← → 바위 밝기 · Home End 젖음 · B 전부 판정값(Tuning.MAP4_*)으로
public class Map4 : MonoBehaviour
{
    public static readonly Vector3 Offset = new Vector3(0f, -200f, 0f);
    public static bool HumanCheck => System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "map4human") >= 0;   // 검사 -only map4human: 사람 길(인트로 → 시작 → DevHud 가 놓는다)을 봇이 그대로 지난다
    public static bool Requested => System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-map4") >= 0 || HumanCheck;
    // GAME-1 (제안서 docs/제안서_GAME1_MAP4에서_놀기.md, 사용자 승인 10-03): 플래그 없이 "시작" = MAP4 에서 놀기 (괴물 · 석탄 · 감독). 검사 -only map4play 는 사람 길로 들어와 같은 것을 탄다
    static bool Arg(string a) => System.Array.IndexOf(System.Environment.GetCommandLineArgs(), a) >= 0;
    public static bool PlayCheck => Arg("map4play") || Arg("map4meet");
    public static bool Game => Tuning.MAP4_GAME && !Requested && !FabTest.Requested && !Arg("-fabvideo") && (!Arg("-check") || PlayCheck) && !Arg("startbooth");   // 사보타주 startbooth = 옛 부스 맵 그대로
    public static int Seed() { var a = System.Environment.GetCommandLineArgs(); int i = System.Array.IndexOf(a, "-seed"); return i >= 0 && i + 1 < a.Length && int.TryParse(a[i + 1], out int s) ? s : System.Environment.TickCount; }
    public static bool Sab(string name) { var a = System.Environment.GetCommandLineArgs(); int i = System.Array.IndexOf(a, "-sabotage"); return i >= 0 && i + 1 < a.Length && a[i + 1] == name; }   // 검사 사보타주 — 인자에서 바로 (DevHud.Start 가 M1Check.Start 보다 먼저 돌 수 있다)
    public static bool SabNoOre => Sab("noore"); public static bool SabSameSeed => Sab("sameseed"); public static bool SabNoNav => Sab("nonav");
    // 방 가운데 · 넓이: 굽기가 넣은 빈 노드 AREA_<방>_<가로 × 10>_<세로 × 10> (map4geo 와 같은 것). 없으면 설계 파일 좌표로
    public Transform Area(string id) => GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith("AREA_" + id + "_") && t.name.Split('_').Length == 4);
    public bool InArea(string id, Vector3 p, float margin)
    {
        var a = Area(id); if (a == null) return false; var q = a.name.Split('_'); float w = int.Parse(q[2]) / 10f, d = int.Parse(q[3]) / 10f; Vector3 v = p - a.position;
        return Mathf.Abs(Vector3.Dot(v, a.right)) <= w / 2 + margin && Mathf.Abs(Vector3.Dot(v, a.forward)) <= d / 2 + margin && Mathf.Abs(v.y) < 6f;
    }
    public static readonly string[] LitRooms = { "P", "R0", "L", "S1", "H", "z6" };   // 불 켜진 방(집) — 괴물 출구를 안 뚫는다 (사용자 10-03 "안 뚫는다")
    [System.NonSerialized] public bool judge;                    // 판정 모드(-map4 · 검사가 놓은 맵): 장면 자리 · 밝기 · 재질 키와 왼쪽 아래 글. 게임(StartGame)에선 끈다 (DevHud · 감독 키와 부딪힌다)
    public Player player; public Camera cam;
    public Transform[] spots; int spot;
    [System.NonSerialized] public float power = Tuning.FAB_LIGHT_ENERGY, range = Tuning.FAB_LIGHT_RANGE, fill = Tuning.FAB_AMBIENT_FILL;
    Light[] lamps; (Light l, float mul)[] zone;                  // LAMP_ = 판정값 그대로 · ZL_ = 세기 × mul, 거리 + 1 m

    // ---- TEX-1
    public class Rock { public Material mat; public int wa, wb, fa, fb; }   // 재질 칸 하나 = 사진 짝 (구운 번호)
    public static bool SabOneFace, SabNoTint, SabSeamShift;      // 검사용 사보타주: oneface(구역 끔 = 전부 ③ + ②) · notint(어둡게 물들이지 않음) · seamshift(둘째 사진 자리 어긋남 되살림)
    [System.NonSerialized] public List<Rock> rocks = new List<Rock>();
    [System.NonSerialized] public bool zones = true, numbers, sameBoth;   // sameBoth = 검사: 두 칸에 같은 사진을 끼우고 그래도 섞는다 (map4_seam_no_shift)
    [System.NonSerialized] public float seam = Tuning.MAP4_SEAM_M, blotch = Tuning.MAP4_BLOTCH, bright = Tuning.MAP4_ROCK_BRIGHT, wet = Tuning.MAP4_WET;
    [System.NonSerialized] public float[] wallDark = (float[])Tuning.MAP4_WALL_DARK.Clone(), floorDark = (float[])Tuning.MAP4_FLOOR_DARK.Clone();
    (bool floor, int n)[] picks = new (bool, int)[0]; int pick;  // Tab 으로 도는 사진 목록 (맵에 실제로 쓰인 것)
    readonly Dictionary<Material, Rock> byMat = new Dictionary<Material, Rock>();
    static readonly Dictionary<string, Texture> tex = new Dictionary<string, Texture>();
    static readonly int SeamId = Shader.PropertyToID("_Map4Seam"), BlotchId = Shader.PropertyToID("_Map4Blotch"), DebugId = Shader.PropertyToID("_Map4Debug"), ShiftId = Shader.PropertyToID("_Map4Shift"),
        BrightId = Shader.PropertyToID("_Map4Bright"), WetId = Shader.PropertyToID("_Map4Wet"), RoadId = Shader.PropertyToID("_Map4RoadDim"), ZonesId = Shader.PropertyToID("_Map4Zones"), Dbg2Id = Shader.PropertyToID("_Map4Dbg2");

    public static Map4 Spawn(Player player, Camera cam)
    {
        var go = FabTest.Spawn("Map4", Offset);
        if (go == null) return null;
        var warm = Color.Lerp(FabTest.White, Tuning.BOOTH_LIGHT_COLOR, Tuning.FAB_LIGHT_ORANGE);
        var lamps = go.GetComponentsInChildren<Light>().Where(l => l.name.StartsWith("LAMP_")).ToArray();
        foreach (var l in lamps) l.color = warm;
        var zone = new List<(Light, float)>();
        foreach (var t in go.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("ZL_")))
        {
            var l = t.gameObject.AddComponent<Light>();
            l.type = LightType.Point; ColorUtility.TryParseHtmlString("#" + t.name.Substring(3, 6), out var c); l.color = c;
            bool warmWhite = c.r > 0.9f && c.g > 0.4f && c.b < 0.5f;   // 작업등 · 주황 = 따뜻한 흰빛 계열
            l.shadows = LightShadows.None; zone.Add((l, warmWhite ? 0.8f : 0.4f));   // 구역 색 등(파랑 · 초록 · 빨강 · 흰색)은 약하게 (검수 10-01: 방 전체가 파랗게 번지고 판자 문이 새빨갛게 물들었다)
            l.GetUniversalAdditionalLightData().renderingLayers = Pickaxe.DefaultRenderingLayer;
        }
        // 전등 갓 · 줄은 그림자를 안 만든다 — 줄에 매달아 내린 전등의 갓이 제 빛을 가려 천장에 큰 검은 얼룩을 만들었다 (검수 10-01)
        foreach (var r in go.GetComponentsInChildren<Renderer>().Where(r => r.name.Contains("vgyidfpaw") || r.name.StartsWith("NOCOL_LAMPCORD")))
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        if (Tuning.FAB_COLOR_GRADE) FabTest.Grade();
        var m = go.AddComponent<Map4>(); m.player = player; m.cam = cam; m.lamps = lamps; m.zone = zone.ToArray(); m.judge = true;
        m.Axes(); m.Rocks(go); m.Apply();
        m.spots = go.GetComponentsInChildren<Transform>().Where(t => t.name.StartsWith("CAM_")).OrderBy(t => t.name == "CAM_start" ? "" : t.name).ToArray();
        m.Go(0);
        return m;
    }

    // Blender(설계 파일 · scene_mock.py) 좌표 → 게임 자리. glTF 를 읽는 쪽이 x 나 z 를 뒤집는다 — 아는 빈 노드 둘(펌프실 TEX_P_ = (-14, -3) · CAM_start = (0, 2))로 부호를 맞춘다 (Map4ShotsStage 와 같은 법)
    float sx = -1f, sz = 1f;
    void Axes()
    {
        var tp = GetComponentsInChildren<Transform>().FirstOrDefault(t => t.name.StartsWith("TEX_P_")); var cs = FabTest.Node(gameObject, "CAM_start");
        if (tp == null || cs == null) { Debug.Log("MAP4 no TEX_P_ / CAM_start node — plan axes guessed"); return; }
        sx = -Mathf.Sign(transform.InverseTransformPoint(tp.position).x); sz = Mathf.Sign(transform.InverseTransformPoint(cs.position).z);
    }
    public Vector3 Plan(float x, float y, float z = 0f) => transform.TransformPoint(new Vector3(sx * x, z, sz * y));

    // ---- GAME-1 석탄: 구역 넷(북 N · 서 W · 남 S · 동 E)의 후보 SLOT_Pocket_<구역>_<번호> (벽 겉) · SLOTOUT_<구역>_<번호> (0.8 m 바깥) · 탄층 조각 NOCOL_ORE_<구역>_<번호>_Face · _Loose · _Gap (scene_mock.py)
    public class Spot { public string name, area; public int index; public Transform slot, outT, face, loose, gap; public OrePocket pocket; public bool open; }
    [System.NonSerialized] public List<Spot> coal = new List<Spot>();
    [System.NonSerialized] public string rich = "";
    [System.NonSerialized] public int seed;
    UnityEngine.AI.NavMeshDataInstance nav;

    // 판마다 열 자리: 좋은 광맥 구역 하나(COAL_OPEN_RICH 곳) + 나머지 구역은 COAL_OPEN_POOR 곳씩. 씨앗이 같으면 같은 판
    public static (string rich, HashSet<string> open) PickOpen(IEnumerable<string> names, int seed)
    {
        var rnd = new System.Random(SabSameSeed ? 1 : seed);
        string rich = Tuning.COAL_AREAS[rnd.Next(Tuning.COAL_AREAS.Length)];
        var open = new HashSet<string>();
        foreach (var a in Tuning.COAL_AREAS)
        {
            var list = names.Where(n => n.Split('_')[2] == a).OrderBy(n => n).ToList();
            foreach (var n in list.OrderBy(_ => rnd.Next()).Take(a == rich ? Tuning.COAL_OPEN_RICH : Tuning.COAL_OPEN_POOR)) open.Add(n);
        }
        return (rich, open);
    }

    // 게임 시작: 괴물이 걸을 바닥(Map4_NavMesh — Assets/Editor/BuildMap4.cs 가 굽는다) · 석탄 열기 · 감독
    public Director StartGame(Stalker s, int seed)
    {
        judge = false;
        var nd = Resources.Load<UnityEngine.AI.NavMeshData>("Map4_NavMesh");
        if (nd != null && !SabNoNav) nav = UnityEngine.AI.NavMesh.AddNavMeshData(nd);
        else Debug.Log("MAP4 no Map4_NavMesh in Resources — the monster has no floor (bake: Unity -executeMethod BuildMap4.Bake)");
        var all = GetComponentsInChildren<Transform>(true); var by = all.GroupBy(t => t.name).ToDictionary(g => g.Key, g => g.First());
        coal.Clear();
        foreach (var t in all.Where(t => t.name.StartsWith("SLOT_Pocket_")))
        {
            var p = t.name.Split('_'); if (p.Length < 4) continue;
            var c = new Spot { name = t.name, area = p[2], index = int.Parse(p[3]), slot = t }; string k = "NOCOL_ORE_" + p[2] + "_" + p[3] + "_";
            by.TryGetValue("SLOTOUT_" + p[2] + "_" + p[3], out c.outT); by.TryGetValue(k + "Face", out c.face); by.TryGetValue(k + "Loose", out c.loose); by.TryGetValue(k + "Gap", out c.gap);
            coal.Add(c);
        }
        OpenCoal(seed);
        var d = gameObject.AddComponent<Director>(); d.Begin(this, s, player, cam);
        return d;
    }

    void OpenCoal(int sd)
    {
        var (r, open) = PickOpen(coal.Select(c => c.name), sd); rich = r; seed = sd;
        foreach (var c in coal)
        {
            c.open = open.Contains(c.name) && !SabNoOre;
            foreach (var t in new[] { c.face, c.loose, c.gap }) if (t != null) t.gameObject.SetActive(c.open);   // 닫힌 자리 = 띠만 칠한 벽
            if (!c.open || c.loose == null) continue;
            Vector3 o = c.outT != null ? c.outT.position - c.slot.position : Vector3.zero; o.y = 0f;
            if (o.sqrMagnitude < 1e-4f && UnityEngine.AI.NavMesh.SamplePosition(c.slot.position, out var h, 4f, UnityEngine.AI.NavMesh.AllAreas)) { o = h.position - c.slot.position; o.y = 0f; }
            o.Normalize();
            var go = new GameObject("OrePocket_" + c.area + "_" + c.index); go.SetActive(false);   // 꺼 둔 채 붙여 Awake 가 mesh 를 받은 뒤 돈다
            go.transform.SetParent(transform, true);
            go.transform.SetPositionAndRotation(c.slot.position + o * Tuning.POCKET_WALL_OUT, Quaternion.LookRotation(o.sqrMagnitude > 0f ? o : Vector3.forward));
            go.AddComponent<SphereCollider>().radius = Tuning.POCKET_RADIUS;
            var pk = go.AddComponent<OrePocket>(); c.loose.SetParent(go.transform, true); pk.mesh = c.loose; pk.outDir = o; c.pocket = pk;
            go.SetActive(true);
        }
        Debug.Log($"MAP4 coal: seed {sd} · good seam {rich} · open {coal.Count(c => c.open)} of {coal.Count} ({string.Join(" ", coal.Where(c => c.open).Select(c => c.area + c.index))})");
    }

    void OnDestroy() { if (nav.valid) UnityEngine.AI.NavMesh.RemoveNavMeshData(nav); }

    // RK_ 재질 칸 → 부스 바위 재질(MineRock) 사본. 같은 이름은 사본 하나를 같이 쓴다. 부스 재질 자체는 안 건드린다
    void Rocks(GameObject go)
    {
        var src = ArtLook.Instance != null ? ArtLook.Instance.newMat : null;
        if (src == null) { Debug.Log("MAP4 no booth rock material (ArtLook) in this scene — rock stays untextured"); return; }
        var by = new Dictionary<string, Rock>();
        foreach (var r in go.GetComponentsInChildren<MeshRenderer>())
        {
            var ms = r.sharedMaterials; bool changed = false;
            for (int i = 0; i < ms.Length; i++)
            {
                if (ms[i] == null || !ms[i].name.StartsWith("RK_")) continue;
                if (!by.TryGetValue(ms[i].name, out var k))
                {
                    var p = ms[i].name.Split('_');
                    k = new Rock { mat = new Material(src) { name = ms[i].name }, wa = int.Parse(p[1]), wb = int.Parse(p[2]), fa = int.Parse(p[3]), fb = int.Parse(p[4]) };
                    k.mat.EnableKeyword("_MAP4"); by[ms[i].name] = k; rocks.Add(k); byMat[k.mat] = k;
                }
                ms[i] = k.mat; changed = true;
            }
            if (changed) r.sharedMaterials = ms;
        }
        picks = new[] { (false, 2) }.Concat(rocks.SelectMany(k => new[] { k.wa, k.wb }).Distinct().OrderBy(n => n).Select(n => (false, n)))
            .Concat(rocks.SelectMany(k => new[] { k.fa, k.fb }).Distinct().OrderBy(n => n).Select(n => (true, n))).ToArray();
        if (SabOneFace) zones = false;
        if (SabNoTint) { for (int i = 0; i < wallDark.Length; i++) wallDark[i] = 1f; for (int i = 0; i < floorDark.Length; i++) floorDark[i] = 1f; }
        Paint();
    }

    // 바닥 ② = 벽 ⑦(석탄)과 같은 사진
    static string WallKey(int n) => "w" + n;
    static string FloorKey(int n) => n == 2 ? "w7" : "f" + n;
    static Texture Tex(string key, bool normal)
    {
        string path = "Rock/" + key + (normal ? "_nor_gl" : "_DiffRough");
        if (!tex.TryGetValue(path, out var t) || t == null) { t = Resources.Load<Texture2D>(path); tex[path] = t; if (t == null) Debug.Log("MAP4 missing rock photo " + path); }
        return t;
    }
    Vector4 Dark(float k) => SabNoTint ? new Vector4(1f, 1f, 1f, 0f) : new Vector4(k * Tuning.MAP4_WARM.r, k * Tuning.MAP4_WARM.g, k * Tuning.MAP4_WARM.b, 0f);   // 어둡기 = 빛 계산 눈금(선형) 곱 × 따뜻한 색조
    public static Color NumberColor(bool floor, int n) => Color.HSVToRGB((n * 0.137f + (floor ? 0.5f : 0f)) % 1f, floor ? 0.45f : 0.9f, floor ? 0.55f : 1f);
    public (int wa, int wb, int fa, int fb) Ids(Rock k) => zones ? (k.wa, sameBoth ? k.wa : k.wb, k.fa, sameBoth ? k.fa : k.fb) : (3, 3, 2, 2);

    public void Paint()
    {
        foreach (var k in rocks)
        {
            var (wa, wb, fa, fb) = Ids(k); var m = k.mat;
            m.SetTexture("_BaseMap", Tex(WallKey(wa), false)); m.SetTexture("_BumpMap", Tex(WallKey(wa), true));
            m.SetTexture("_BaseMapB", Tex(WallKey(wb), false)); m.SetTexture("_BumpMapB", Tex(WallKey(wb), true));
            m.SetTexture("_MudMap", Tex(FloorKey(fa), false)); m.SetTexture("_MudNormal", Tex(FloorKey(fa), true));
            m.SetTexture("_MudMapB", Tex(FloorKey(fb), false)); m.SetTexture("_MudNormalB", Tex(FloorKey(fb), true));
            m.SetTexture("_CoalMap", Tex("w7", false)); m.SetTexture("_CoalNormal", Tex("w7", true));                 // 탄층 띠 = 석탄 ⑦
            float ck = SabNoTint ? 1f : wallDark[7]; m.SetColor("_CoalTint", new Color(ck, ck, ck).gamma);
            m.SetVector("_TintA", Dark(wallDark[wa])); m.SetVector("_TintB", Dark(wallDark[wb]));
            m.SetVector("_FTintA", Dark(floorDark[fa])); m.SetVector("_FTintB", Dark(floorDark[fb]));
            m.SetVector("_Tile", new Vector4(2.4f / Tuning.MAP4_WALL_TILE_M[wa], 2.4f / Tuning.MAP4_WALL_TILE_M[7], 2.4f / Tuning.MAP4_FLOOR_TILE_M[fa], 1f));   // 셰이더 기준 = 한 장 2.4 m
            m.SetVector("_TileB", new Vector4(2.4f / Tuning.MAP4_WALL_TILE_M[wb], 1f, 2.4f / Tuning.MAP4_FLOOR_TILE_M[fb], 1f));
            m.SetVector("_Same", new Vector4(!sameBoth && WallKey(wa) == WallKey(wb) ? 1f : 0f, !sameBoth && FloorKey(fa) == FloorKey(fb) ? 1f : 0f, wa == 7 ? 1f : 0f, wb == 7 ? 1f : 0f));
            m.SetVector("_DbgA", NumberColor(false, wa).linear); m.SetVector("_DbgB", NumberColor(false, wb).linear);   // 벡터 칸은 색 변환이 없다 — 화면 색이 보기표(OnGUI)와 같게 .linear
            m.SetVector("_DbgFA", NumberColor(true, fa).linear); m.SetVector("_DbgFB", NumberColor(true, fb).linear);
        }
    }

    // 광선이 맞은 굴 면의 사진 번호 (이음 구간이면 그 점에서 더 많이 보이는 쪽) — 재질에 실제로 끼워진 그림 이름에서 읽는다. more = 그 점의 셋째 UV (젖음 ÷ 2, 큰 길). 검사 map4_room_photos · map4_photo_extras · map4_no_burn 가 쓴다
    public bool PhotoAt(RaycastHit hit, out int wall, out int floor) => PhotoAt(hit, out wall, out floor, out _);
    public bool PhotoAt(RaycastHit hit, out int wall, out int floor, out Vector2 more)
    {
        wall = floor = 0; more = default;
        var mc = hit.collider as MeshCollider; var r = hit.collider.GetComponent<MeshRenderer>();
        if (mc == null || r == null || mc.sharedMesh == null || !mc.sharedMesh.isReadable) return false;
        var mesh = mc.sharedMesh; int ti = hit.triangleIndex * 3, sub = -1;
        for (int i = 0; i < mesh.subMeshCount; i++) { var d = mesh.GetSubMesh(i); if (ti >= d.indexStart && ti < d.indexStart + d.indexCount) sub = i; }
        var ms = r.sharedMaterials;
        if (sub < 0 || sub >= ms.Length || !byMat.TryGetValue(ms[sub], out var k)) return false;
        var tr = mesh.triangles; var uv = mesh.uv; var b = hit.barycentricCoordinate;
        Vector2 u = uv[tr[ti]] * b.x + uv[tr[ti + 1]] * b.y + uv[tr[ti + 2]] * b.z;                     // x = 벽 · y = 바닥 이음 자리 (0.5 가 경계 — 이음 길이와 상관없다)
        var u3 = mesh.uv3; if (u3.Length == uv.Length) more = u3[tr[ti]] * b.x + u3[tr[ti + 1]] * b.y + u3[tr[ti + 2]] * b.z;
        int Num(string prop)                                                                        // "w3_DiffRough" → 3 · "f6_…" → 6 · 바닥 칸의 "w7_…" → 2
        {
            var t = k.mat.GetTexture(prop); if (t == null) return 0;
            int n = int.Parse(t.name.Substring(1, t.name.IndexOf('_') - 1)); return prop.StartsWith("_Mud") && t.name[0] == 'w' ? 2 : n;
        }
        wall = Num(u.x > 0.5f ? "_BaseMapB" : "_BaseMap"); floor = Num(u.y > 0.5f ? "_MudMapB" : "_MudMap");
        return true;
    }

    public void Go(int i)
    {
        if (spots.Length == 0) return;
        spot = (i % spots.Length + spots.Length) % spots.Length;
        FabTest.StandAt(player, spots[spot], FabTest.Node(gameObject, "AT_" + spots[spot].name.Substring(4)));
    }

    public void Apply()
    {
        foreach (var l in lamps) { l.intensity = power; l.range = range; }
        foreach (var (l, mul) in zone) { l.intensity = power * mul; l.range = range + 1f; }
        Shader.SetGlobalFloat(SeamId, seam); Shader.SetGlobalFloat(BlotchId, blotch); Shader.SetGlobalFloat(DebugId, numbers ? 1f : 0f);
        Shader.SetGlobalFloat(ShiftId, SabSeamShift ? 0.37f : 0f); Shader.SetGlobalFloat(BrightId, bright); Shader.SetGlobalFloat(WetId, wet);
        Shader.SetGlobalFloat(RoadId, zones && !SabNoTint ? wallDark[2] / wallDark[3] : 1f);
        Shader.SetGlobalFloat(ZonesId, zones ? 1f : 0f);
        Color d2 = NumberColor(false, 2).linear; Shader.SetGlobalVector(Dbg2Id, new Vector4(d2.r, d2.g, d2.b, zones ? 1f : 0f));
    }

    // 발 자리에서 머리 위 1.95 m 안에 무엇이 있나 (저절로 숙이는 조건). 검사 map4_no_auto_crouch 가 맵 전체 바닥에서 같은 것을 잰다
    // 여유는 몸 키 + 5 cm (10-02 까지 + 15 cm = 1.95 m: 선 몸 1.8 m 가 들어가는 1.8~1.95 m 틈 — 2.0 m 문틀 밑 침목 위, 아치 굴 벽 발치 — 에서 걷다가 저절로 숙여졌다. 사용자 10-02 "풍문으로 들어갈 때 자동 숙임이 생김")
    public const float LowAboveM = Tuning.BODY_HEIGHT + 0.05f;
    public static bool LowAbove(Vector3 feet, out RaycastHit hit) => Physics.SphereCast(feet + Vector3.up * 0.5f, 0.25f, Vector3.up, out hit, LowAboveM - 0.75f, ~0, QueryTriggerInteraction.Ignore);

    void Update()
    {
        // 머리 위가 선 몸(BODY_HEIGHT + 15 cm)보다 낮으면 저절로 숙인다 — Ctrl 을 떼도 천장 속으로 서지 않게 (공은 내 몸 캡슐 안 0.5 m 에서 출발해 제 몸은 안 맞는다, 공 꼭대기 0.75 m → 1.95 m)
        player.forceCrouch = LowAbove(player.transform.position, out _);
        if (!judge) return;                                                   // 게임(GAME-1): 판정 키 없음 — DevHud · 감독 키와 부딪힌다
        var k = UnityEngine.InputSystem.Keyboard.current; if (k == null || k.shiftKey.isPressed) return;
        bool paint = false;
        if (k.rightBracketKey.wasPressedThisFrame) Go(spot + 1);
        else if (k.leftBracketKey.wasPressedThisFrame) Go(spot - 1);
        else if (k.digit1Key.wasPressedThisFrame) power = Mathf.Max(0f, power - 4f);
        else if (k.digit2Key.wasPressedThisFrame) power += 4f;
        else if (k.digit3Key.wasPressedThisFrame) range = Mathf.Max(1f, range - 1f);
        else if (k.digit4Key.wasPressedThisFrame) range += 1f;
        else if (k.digit9Key.wasPressedThisFrame) fill = Mathf.Max(0f, fill - 0.02f);
        else if (k.digit0Key.wasPressedThisFrame) fill += 0.02f;
        else if (k.tKey.wasPressedThisFrame) { zones = !zones; paint = true; }
        else if (k.gKey.wasPressedThisFrame) numbers = !numbers;
        else if (k.tabKey.wasPressedThisFrame && picks.Length > 0) pick = (pick + 1) % picks.Length;
        else if ((k.digit5Key.wasPressedThisFrame || k.digit6Key.wasPressedThisFrame) && picks.Length > 0)
        {
            var (fl, n) = picks[pick]; var a = fl ? floorDark : wallDark;
            a[n] = Mathf.Clamp(Mathf.Round((a[n] + (k.digit6Key.wasPressedThisFrame ? 0.05f : -0.05f)) * 100f) / 100f, 0.05f, 2f); paint = true;
        }
        else if (k.digit7Key.wasPressedThisFrame) seam = Mathf.Max(1f, seam - 1f);
        else if (k.digit8Key.wasPressedThisFrame) seam = Mathf.Min(20f, seam + 1f);
        else if (k.minusKey.wasPressedThisFrame) blotch = Mathf.Max(0f, Mathf.Round((blotch - 0.1f) * 10f) / 10f);
        else if (k.equalsKey.wasPressedThisFrame) blotch = Mathf.Min(1f, Mathf.Round((blotch + 0.1f) * 10f) / 10f);
        else if (k.leftArrowKey.wasPressedThisFrame) bright /= 1.1f;
        else if (k.rightArrowKey.wasPressedThisFrame) bright *= 1.1f;
        else if (k.homeKey.wasPressedThisFrame) wet = Mathf.Max(0f, wet - 0.25f);
        else if (k.endKey.wasPressedThisFrame) wet += 0.25f;
        else if (k.bKey.wasPressedThisFrame)
        {
            power = Tuning.FAB_LIGHT_ENERGY; range = Tuning.FAB_LIGHT_RANGE; fill = Tuning.FAB_AMBIENT_FILL;
            zones = true; numbers = false; seam = Tuning.MAP4_SEAM_M; blotch = Tuning.MAP4_BLOTCH; bright = Tuning.MAP4_ROCK_BRIGHT; wet = Tuning.MAP4_WET;
            wallDark = (float[])Tuning.MAP4_WALL_DARK.Clone(); floorDark = (float[])Tuning.MAP4_FLOOR_DARK.Clone(); paint = true;
        }
        else return;
        if (paint) Paint();
        Apply();
    }

    void LateUpdate()
    {
        RenderSettings.ambientLight += FabTest.FillColor * fill;   // Headlamp 가 매 프레임 환경광(어둠 적응 포함)을 새로 쓴 뒤에 더한다
        if (cam != null) cam.fieldOfView = Tuning.FAB_CAMERA_FOV;
    }

    void OnGUI()
    {
        if (!judge) return;
        if (spots.Length > 0) GUI.Label(new Rect(10, Screen.height - 28, 900, 24), $"MAP4  spot {spot + 1}/{spots.Length} {spots[spot].name.Substring(4)}   [ ] = prev / next spot");
        GUI.Label(new Rect(10, Screen.height - 52, 1100, 24), $"lamp power {power:0} [1 2]   reach {range:0} m [3 4]   soft fill {fill:0.00} [9 0]   B = judged values ({Tuning.FAB_LIGHT_ENERGY:0} / {Tuning.FAB_LIGHT_RANGE:0} m / {Tuning.FAB_AMBIENT_FILL:0.00})   lamps {lamps.Length + zone.Length}");
        if (picks.Length == 0) return;
        var (fl, n) = picks[pick];
        GUI.Label(new Rect(10, Screen.height - 76, 1500, 24), $"rock  zones {(zones ? "ON" : "off = all wall 3 + floor 2")} [T]   number colours {(numbers ? "ON" : "off")} [G]   photo {(fl ? "floor" : "wall")} {n} dark {(fl ? floorDark : wallDark)[n]:0.00} [Tab = next photo, 5 6]   " +
            $"join {seam:0} m (max 20) [7 8]   blotch {blotch:0.0} [- =]   bright {bright:0.00} [Left Right]   wet {wet:0.00} [Home End]");
        if (!numbers) return;
        for (int i = 0; i < picks.Length; i++)                                // G: 번호 색 보기표 (화면 왼쪽 아래, 값 줄 위)
        {
            var old = GUI.color; GUI.color = NumberColor(picks[i].floor, picks[i].n);
            GUI.DrawTexture(new Rect(10 + i * 74, Screen.height - 102, 20, 18), Texture2D.whiteTexture); GUI.color = old;
            GUI.Label(new Rect(33 + i * 74, Screen.height - 104, 52, 22), (picks[i].floor ? "fl " : "wall ") + picks[i].n);
        }
    }
}
