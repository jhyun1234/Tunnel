using System.Linq;
using UnityEngine;
using UnityEngine.AI;

// REP-1: 판이 시작될 때 REP_BROKEN_START 만큼 망가뜨리고, 판 중에는 REP_BREAK_EVERY 마다 하나씩 더 — 플레이어에게서 REP_BREAK_MIN_M 넘게 떨어진,
// 걸어서 갈 수 있는(막힘 돌무더기 너머가 아닌) 곳 중에서. 부스 판마다 돈을 0 으로.
public class RepairDirector : MonoBehaviour
{
    public Player player;
    [System.NonSerialized] public float breakEvery = Tuning.REP_BREAK_EVERY;   // DevHud F11 F12 · 검사가 줄인다
    [System.NonSerialized] public int startBroken, brokeLater, lampsStart;       // 검사 (startBroken = 전등 뺀 나머지에서 망가뜨린 수)
    [System.NonSerialized] public Repairable lastBroke;
    [System.NonSerialized] public float timer, minBreakDist = 999f;             // 검사: 타이머를 당기고, 판 중에 망가진 곳의 가장 가까운 거리를 본다

    void Start()
    {
        Economy.Reset();
        // 전등(= MAP2 의 꺼진 전등 자리)은 처음부터 다 꺼져 있다 — 판정 받은 "꺼진 전등 구역"의 어둠을 지킨다(검사 booth_light_zones). 30 % 는 나머지 종류에서
        var all = Repairable.All.ToList();
        var rest = all.Where(r => r.kind != "lamp").ToList();
        int n = Mathf.RoundToInt(rest.Count * Tuning.REP_BROKEN_START);
        foreach (var r in all) r.SetFixed();
        foreach (var r in all.Where(r => r.kind == "lamp")) r.Break();
        foreach (var r in rest.OrderBy(_ => Random.value).Take(n)) r.Break();
        startBroken = n;
        lampsStart = all.Count(r => r.kind == "lamp" && r.broken);
        timer = breakEvery;
    }

    void Update()
    {
        timer -= Time.deltaTime;
        if (timer > 0f) return;
        timer = breakEvery;
        Vector3 me = player.transform.position;
        var path = new NavMeshPath();
        bool Reach(Repairable r) => NavMesh.SamplePosition(r.standAt, out NavMeshHit h, 3f, NavMesh.AllAreas)
            && NavMesh.SamplePosition(me, out NavMeshHit hm, 3f, NavMesh.AllAreas)
            && NavMesh.CalculatePath(hm.position, h.position, NavMesh.AllAreas, path) && path.status == NavMeshPathStatus.PathComplete;
        var pick = Repairable.All.Where(r => !r.broken && Vector3.Distance(r.focus, me) > Tuning.REP_BREAK_MIN_M).OrderBy(_ => Random.value).FirstOrDefault(Reach);
        if (pick == null) return;
        pick.Break();
        lastBroke = pick;
        minBreakDist = Mathf.Min(minBreakDist, Vector3.Distance(pick.focus, me));
        brokeLater++;
    }
}
