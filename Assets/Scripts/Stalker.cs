using System.Collections.Generic;
using UnityEngine;

// 소음을 듣는 괴물 최소판 (M3). Godot Stalker.gd 의 귀·배회·조사·수색만 옮겼다.
// 눈·빛·추격·잡기·체력·벽·천장은 다음 마일스톤. 길찾기 없음 — 직선 갱도라 목적지로 곧장 간다.
// 1타 = 소리 쪽으로 한 칸만 (방향만 안다), STALKER_HEAR_CONFIRM_S 안에 같은 자리에서 한 번 더 = 그 자리까지 (설계서 v2 Step 5).
public class Stalker : MonoBehaviour
{
    public enum State { Wander, Investigate, Search }

    [System.NonSerialized] public State state = State.Wander;
    public Transform player;
    public float zMin, zMax;                       // 갱도 축 범위 — 씬 생성기가 넣는다

    // 실행 중 조정·검사용 (씬에 안 굽는다)
    [System.NonSerialized] public float earMul = Tuning.STALKER_EAR_MUL;
    [System.NonSerialized] public string lastHeard = "-";
    [System.NonSerialized] public int hits;          // 같은 자리에서 연속으로 들은 횟수
    [System.NonSerialized] public int spotsVisited;  // 이번 수색에서 들여다본 곳 수
    [System.NonSerialized] public Vector3 noisePos;

    CharacterController cc;
    Vector3 target;
    bool hasTarget;
    float pause, dwell, vy, stuck, noiseTime = -99f;
    readonly List<Vector3> spots = new List<Vector3>();
    readonly System.Random rng = new System.Random(Tuning.MAP_SEED + 200);

    public float DistToPlayer => player != null ? Flat(player.position - transform.position) : -1f;

    void Awake()
    {
        cc = GetComponent<CharacterController>();
    }

    void OnEnable() { NoiseBus.Made += OnNoise; }
    void OnDisable() { NoiseBus.Made -= OnNoise; }

    void OnNoise(Vector3 pos, float radius, string kind, object who)
    {
        float d = Flat(pos - transform.position);
        if (d > radius * earMul)
            return;
        if (Time.time - noiseTime > Tuning.STALKER_HEAR_CONFIRM_S || Flat(pos - noisePos) > Tuning.STALKER_FOUND_M)
            hits = 0;
        hits++;
        noisePos = pos;
        noiseTime = Time.time;
        lastHeard = $"{kind} {d:F1} m x{hits}";
        Vector3 to = pos - transform.position;
        to.y = 0f;
        Vector3 t = hits >= 2 ? pos : transform.position + Vector3.ClampMagnitude(to, Tuning.STALKER_HEAR_SOFT_M);
        SetTarget(t);
        spots.Clear();
        spotsVisited = 0;
        state = State.Investigate;
    }

    void Update()
    {
        float dt = Time.deltaTime;
        switch (state)
        {
            case State.Wander:
                if (!hasTarget)
                {
                    if (pause > 0f) pause -= dt;
                    else SetTarget(RandomNear(transform.position, Tuning.STALKER_WANDER_CELLS * Tuning.GRID_CELL));
                }
                else if (MoveTo(Tuning.STALKER_SPEED_WANDER, dt))
                {
                    hasTarget = false;
                    pause = Tuning.STALKER_WANDER_PAUSE_S;
                }
                break;
            case State.Investigate:
                if (MoveTo(Tuning.STALKER_SPEED_INVESTIGATE, dt))
                    BeginSearch();
                break;
            case State.Search:
                if (!hasTarget)
                {
                    if (dwell > 0f) dwell -= dt;
                    else if (spots.Count > 0)
                    {
                        SetTarget(spots[0]);
                        spots.RemoveAt(0);
                    }
                    else
                    {
                        state = State.Wander;
                        pause = Tuning.STALKER_WANDER_PAUSE_S;
                    }
                }
                else if (MoveTo(Tuning.STALKER_SPEED_SEARCH, dt))
                {
                    hasTarget = false;
                    dwell = Tuning.STALKER_DWELL_S;
                    spotsVisited++;
                }
                break;
        }
        if (!hasTarget)
            Fall(dt);
    }

    void BeginSearch()
    {
        hasTarget = false;
        dwell = Tuning.STALKER_DWELL_S;
        spotsVisited = 1;                          // 도착 자리가 첫 곳
        spots.Clear();
        int n = rng.Next(Tuning.STALKER_SPOTS_MIN, Tuning.STALKER_SPOTS_MAX + 1) - 1;
        for (int i = 0; i < n; i++)
            spots.Add(RandomNear(transform.position, Tuning.STALKER_SEARCH_CELLS * Tuning.GRID_CELL));
        state = State.Search;
    }

    // 검사·배치용. 상태도 배회로 되돌린다
    public void Teleport(Vector3 pos)
    {
        cc.enabled = false;
        transform.position = pos;
        cc.enabled = true;
        hasTarget = false;
        pause = Tuning.STALKER_WANDER_PAUSE_S;      // 놓인 자리에서 한 번 멈춘다 (검사 캡처도 이 틈에 찍는다)
        hits = 0;
        noiseTime = -99f;
        spots.Clear();
        state = State.Wander;
    }

    void SetTarget(Vector3 t)
    {
        t.x = Mathf.Clamp(t.x, -Tuning.STALKER_LANE_X, Tuning.STALKER_LANE_X);
        t.z = Mathf.Clamp(t.z, zMin, zMax);
        t.y = transform.position.y;
        target = t;
        hasTarget = true;
    }

    Vector3 RandomNear(Vector3 center, float range)
    {
        float x = (float)(rng.NextDouble() * 2.0 - 1.0) * Tuning.STALKER_LANE_X;
        float z = center.z + (float)(rng.NextDouble() * 2.0 - 1.0) * range;
        return new Vector3(x, center.y, z);
    }

    // 목적지로 걷는다. 도착하면 true
    bool MoveTo(float speed, float dt)
    {
        Vector3 to = target - transform.position;
        to.y = 0f;
        float d = to.magnitude;
        if (d < Tuning.STALKER_ARRIVE_M)
            return true;
        Vector3 dir = to / d;
        transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir), 10f * dt);
        vy = cc.isGrounded ? -1f : vy - Tuning.GRAVITY * dt;
        cc.Move((dir * Mathf.Min(speed, d / Mathf.Max(dt, 1e-4f)) + Vector3.up * vy) * dt);
        // 벽·플레이어에 막혀 STALKER_STUCK_S 동안 못 가면 도착으로 친다 (무한히 미는 것을 막는 그물)
        stuck = cc.velocity.sqrMagnitude < 0.01f ? stuck + dt : 0f;
        if (stuck < Tuning.STALKER_STUCK_S)
            return false;
        stuck = 0f;
        return true;
    }

    void Fall(float dt)
    {
        vy = cc.isGrounded ? -1f : vy - Tuning.GRAVITY * dt;
        cc.Move(Vector3.up * vy * dt);
    }

    static float Flat(Vector3 v) => new Vector2(v.x, v.z).magnitude;
}
