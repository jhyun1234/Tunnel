using System.Collections.Generic;
using UnityEngine;

// 괴물 (M3 귀·배회·조사·수색 + M4 눈·빛·alert·chase·catch + M5 체력·스턴·철수). Godot Stalker.gd 에서 옮겼다.
// 천장 이동은 모델 뒤. 던진 곡괭이(M6)는 ThrownPick 이 Hit 을 부른다 — 휘두른 한 대와 같다. 길찾기 없음 — 직선 갱도라 목적지로 곧장 간다.
// 귀: 1타 = 소리 쪽으로 한 칸만, STALKER_HEAR_CONFIRM_S 안에 같은 자리에서 한 번 더 = 그 자리까지 (설계서 v2 Step 5).
// 눈: 램프 켜진 몸이 앞 원뿔 STALKER_EYE_DEG 안 STALKER_EYE_M 안, 시선이 안 가려야. 빛: 켜진 램프가 STALKER_LIGHT_M 안에 보이면 배회 속도로 다가간다.
// 체력(설계서 v2 Step 6, 교차 검토): 곡괭이 한 대 25 + 스턴 1.5 s(포효 0.7 + 뒷걸음 0.8). 철수선 30 이하가 되는 순간 철수 —
// 플레이어 램프 원뿔 안 8~14 m 벽으로 가서 벽을 타고 사라진다. 철수 중에는 못 친다(체력 0 경로 없음). STALKER_REGEN_S 뒤 틈에서 체력 100 으로.
public class Stalker : MonoBehaviour
{
    public enum State { Wander, Investigate, Search, Alert, Chase, Catch, Stun, Retreat, Climb, Hidden }

    [System.NonSerialized] public State state = State.Wander;
    public Transform player;
    public Transform playerHead;
    public Player playerBody;
    public Headlamp lamp;
    public float zMin, zMax;                       // 갱도 축 범위 — 씬 생성기가 넣는다
    public Vector3 restartPos;                     // 잡힌 뒤 플레이어가 서는 자리 (복도 시작점)
    public Vector3 homePos;                        // 잡힌 뒤 괴물이 돌아가는 자리 (북쪽 끝)
    public Vector3[] cracks = new Vector3[0];      // 갈라진 틈 — 철수 뒤 재등장 자리

    // 실행 중 조정·검사용 (씬에 안 굽는다)
    [System.NonSerialized] public float earMul = Tuning.STALKER_EAR_MUL;
    [System.NonSerialized] public float eyeM = Tuning.STALKER_EYE_M;
    [System.NonSerialized] public float chaseSpeed = Tuning.STALKER_SPEED_CHASE;
    [System.NonSerialized] public float loseS = Tuning.STALKER_LOSE_S;
    [System.NonSerialized] public float hp = Tuning.STALKER_HP;
    [System.NonSerialized] public float dmgMul = 1f;
    [System.NonSerialized] public float retreatHp = Tuning.STALKER_RETREAT_HP;
    [System.NonSerialized] public bool retreatArmor = true;      // 철수 중 무적 (사보타주 softretreat 가 끈다 — 연타로 벽에 못 가던 상태)
    [System.NonSerialized] public bool stunImmune = Tuning.STALKER_STUN_IMMUNE;   // 스턴 중 피격 무효
    [System.NonSerialized] public bool lureInChase;             // 사보타주 lurechase: 추격 중에도 소리를 듣는다 (M6 유인 검사가 잡는지)
    [System.NonSerialized] public float hiddenLeft;             // s, 숨어 있는 남은 시간
    [System.NonSerialized] public string lastHeard = "-";
    [System.NonSerialized] public string sense = "-";   // 이번 프레임 감각: eye / found / light / -
    [System.NonSerialized] public int hits;          // 같은 자리에서 연속으로 들은 횟수
    [System.NonSerialized] public int hitsTaken;     // 곡괭이에 맞은 횟수 (먹힌 것)
    [System.NonSerialized] public int hitsSeen;      // 곡괭이가 닿은 횟수 (스턴 중 무효 포함)
    [System.NonSerialized] public int spotsVisited;  // 이번 수색에서 들여다본 곳 수
    [System.NonSerialized] public int catches, restarts;
    [System.NonSerialized] public Vector3 noisePos, lastSeen;
    [System.NonSerialized] public Vector3 retreatSpot, retreatFrom, retreatFwd;   // 철수 자리, 그때 플레이어 자리·방향 (검사용)
    [System.NonSerialized] public bool retreatInCone;
    [System.NonSerialized] public float black;      // 잡힘 화면 검은 정도 0~1

    CharacterController cc;
    Renderer[] renderers;
    Vector3 target, backDir;
    bool hasTarget, lightChase;
    float pause, dwell, vy, stuck, alertLeft, unseen, catchT, stunLeft, investigateSpeed, retreatSide, noiseTime = -99f;
    readonly List<Vector3> spots = new List<Vector3>();
    readonly System.Random rng = new System.Random(Tuning.MAP_SEED + 200);
    static Texture2D blackTex;
    const int RayMask = ~((1 << 2) | (1 << Pickaxe.ViewModelLayer));   // Ignore Raycast(자갈·광석)·곡괭이 뷰모델은 시선을 안 막는다

    public float DistToPlayer => player != null ? Flat(player.position - transform.position) : -1f;
    public bool CanBeHit => state != State.Catch && state != State.Climb && state != State.Hidden && !(state == State.Retreat && retreatArmor);

    void Awake()
    {
        cc = GetComponent<CharacterController>();
        renderers = GetComponentsInChildren<Renderer>();
    }

    void OnEnable() { NoiseBus.Made += OnNoise; }
    void OnDisable() { NoiseBus.Made -= OnNoise; }

    void OnNoise(Vector3 pos, float radius, string kind, object who)
    {
        if (state != State.Wander && state != State.Investigate && state != State.Search && !(lureInChase && state == State.Chase))
            return;                                // 이미 봤거나 맞았거나 숨었다 — 소리는 뒷전. 던진 곡괭이 유인도 추격 중엔 안 먹힌다 (설계서 Step 4)
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
        StartInvestigate(t, Tuning.STALKER_SPEED_INVESTIGATE, false);
    }

    // 곡괭이에 맞았다 (Pickaxe.Strike · ThrownPick). 스턴 중 피격은 무효(연타 방지). 철수 중은 CanBeHit 이 막는다 —
    // "철수 중 피격 = 스턴만"은 스턴마다 한 대씩 맞추면 벽에 영영 못 가서(사용자 09-15 F5) 무적으로 바꿨다.
    // 철수선 이하가 되는 순간은 스턴 없이 바로 철수 (사용자 09-15 "피가 없으면 곧바로 도망가는 연출")
    public void Hit(float dmg, Vector3 dir)
    {
        if (!CanBeHit)
            return;
        hitsSeen++;
        if (state == State.Stun && stunImmune)
            return;
        hitsTaken++;
        bool retreating = state == State.Retreat;              // 사보타주 softretreat 때만 온다
        hp = Mathf.Max(0f, hp - dmg * dmgMul);
        if (!retreating && hp <= retreatHp)
        {
            StartRetreat();
            return;
        }
        backDir = Flat3(transform.position - player.position).normalized;
        if (backDir.sqrMagnitude < 1e-4f) backDir = Flat3(dir).normalized;
        state = State.Stun;
        stunLeft = Tuning.STALKER_STUN_S;
        hasTarget = false;
        lightChase = false;
        spots.Clear();
    }

    void Update()
    {
        float dt = Time.deltaTime;
        switch (state)
        {
            case State.Catch: UpdateCatch(dt); return;
            case State.Stun: UpdateStun(dt); return;
            case State.Climb: UpdateClimb(dt); return;
            case State.Hidden: UpdateHidden(dt); return;
        }
        black = Mathf.MoveTowards(black, 0f, dt / Tuning.CATCH_FADE_OUT_S);
        if (state != State.Retreat)
            Senses();
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
                if (lightChase && sense == "light")
                    SetTarget(player.position);     // 빛이 보이는 동안은 자리를 계속 고친다
                if (MoveTo(investigateSpeed, dt))
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
            case State.Alert:                      // 멈춰서 플레이어를 본다 — 빠져나갈 틈 (STALKER_ALERT_S)
                Face(player.position, dt);
                alertLeft -= dt;
                if (alertLeft <= 0f)
                {
                    state = State.Chase;
                    unseen = 0f;
                    lastSeen = player.position;
                }
                break;
            case State.Chase:
                if (sense == "eye") { lastSeen = player.position; unseen = 0f; }
                else unseen += dt;
                if (DistToPlayer <= Tuning.STALKER_CATCH_M)
                {
                    StartCatch();
                    break;
                }
                if (unseen >= loseS)               // 놓쳤다 — 마지막 본 자리로
                {
                    StartInvestigate(lastSeen, Tuning.STALKER_SPEED_INVESTIGATE, false);
                    break;
                }
                SetTarget(sense == "eye" ? player.position : lastSeen);
                MoveTo(chaseSpeed, dt);
                break;
            case State.Retreat:                    // 벽 자리로 달려가서 오른다
                if (MoveTo(Tuning.STALKER_SPEED_RETREAT, dt))
                {
                    state = State.Climb;
                    cc.enabled = false;
                    hasTarget = false;
                    return;                        // cc 를 껐다 — 아래 Fall 이 같은 프레임에 Move 를 부르면 "inactive controller" 경고
                }
                break;
        }
        if (!hasTarget || state == State.Alert)
            Fall(dt);
    }

    // 스턴: 맞는 순간 밀렸다가(STALKER_STUN_KNOCK_*) 남은 시간은 서서 플레이어를 본다. 끝나면 철수선 이하면 철수, 아니면 추격
    void UpdateStun(float dt)
    {
        stunLeft -= dt;
        vy = cc.isGrounded ? -1f : vy - Tuning.GRAVITY * dt;
        if (stunLeft > Tuning.STALKER_STUN_S - Tuning.STALKER_STUN_KNOCK_S)
            cc.Move((backDir * (Tuning.STALKER_STUN_KNOCK_M / Tuning.STALKER_STUN_KNOCK_S) + Vector3.up * vy) * dt);
        else
        {
            Face(player.position, dt);
            cc.Move(Vector3.up * vy * dt);
        }
        if (stunLeft > 0f)
            return;
        if (hp <= retreatHp)
            StartRetreat();
        else
        {
            state = State.Chase;                   // 맞았다 = 알아챘다
            unseen = 0f;
            lastSeen = player.position;
        }
    }

    // 철수 자리: 플레이어 앞(램프 원뿔) 8~14 m 의 가운데, 괴물이 선 쪽 벽. 괴물이 플레이어 뒤면 앞으로 못 지나가니(#16) 뒤쪽 벽
    void StartRetreat()
    {
        retreatFrom = player.position;
        retreatFwd = Flat3(player.forward).normalized;
        Vector3 toMe = Flat3(transform.position - player.position);
        retreatInCone = Vector3.Angle(retreatFwd, toMe) <= Tuning.LAMP_ANGLE_DEG;
        Vector3 dir = retreatInCone ? retreatFwd : -retreatFwd;
        float d = (Tuning.STALKER_RETREAT_MIN_M + Tuning.STALKER_RETREAT_MAX_M) * 0.5f;
        retreatSide = transform.position.x >= 0f ? 1f : -1f;
        Vector3 spot = player.position + dir * d;
        spot.x = retreatSide * Tuning.STALKER_LANE_X;
        spot.y = transform.position.y;
        spot.z = Mathf.Clamp(spot.z, zMin, zMax);
        retreatSpot = spot;
        SetTarget(spot);
        state = State.Retreat;
    }

    // 벽에 붙어 오른다. TUNNEL_ARCH_Y 에 닿으면 사라진다
    void UpdateClimb(float dt)
    {
        Vector3 p = transform.position;
        p.x = Mathf.MoveTowards(p.x, retreatSide * (Tuning.TUNNEL_WALL_X - Tuning.STALKER_R), Tuning.STALKER_WALL_SPEED * dt);
        p.y += Tuning.STALKER_WALL_SPEED * dt;
        transform.position = p;
        transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(Vector3.right * retreatSide), 5f * dt);
        if (p.y < Tuning.TUNNEL_ARCH_Y)
            return;
        state = State.Hidden;
        hiddenLeft = Tuning.STALKER_REGEN_S;
        foreach (var r in renderers) r.enabled = false;
    }

    // 숨어서 회복. 끝나면 플레이어에서 먼 틈에서 체력 100 으로 배회
    void UpdateHidden(float dt)
    {
        hiddenLeft -= dt;
        if (hiddenLeft > 0f)
            return;
        Vector3 at = homePos;
        float best = -1f;
        foreach (var c in cracks)
        {
            float d = Flat(c - player.position);
            if (d > best) { best = d; at = c; }
        }
        hp = Tuning.STALKER_HP;
        foreach (var r in renderers) r.enabled = true;
        Teleport(at);
    }

    // 감각. 우선순위: 눈 > 수색 중 2 m(found) > 빛
    void Senses()
    {
        sense = "-";
        if (player == null || lamp == null)
            return;
        float d = DistToPlayer;
        bool lit = lamp.lampOn;
        if (lit && d <= eyeM && Vector3.Angle(Flat3(transform.forward), Flat3(player.position - transform.position)) <= Tuning.STALKER_EYE_DEG && Clear())
            sense = "eye";
        else if (state == State.Search && d <= Tuning.STALKER_FOUND_M)
            sense = "found";
        else if (lit && d <= Tuning.STALKER_LIGHT_M && Clear())
            sense = "light";

        if (state == State.Alert || state == State.Chase)
            return;
        if (sense == "eye" || sense == "found")
            StartAlert();
        else if (sense == "light" && (state == State.Wander || state == State.Search || lightChase))
            StartInvestigate(player.position, Tuning.STALKER_SPEED_WANDER, true);
    }

    // 눈에서 플레이어 머리까지 시선이 안 가리는가
    bool Clear()
    {
        Vector3 eye = transform.position + Vector3.up * Tuning.STALKER_EYE_H;
        Vector3 to = playerHead.position - eye;
        if (!Physics.Raycast(eye, to.normalized, out RaycastHit hit, to.magnitude, RayMask, QueryTriggerInteraction.Ignore))
            return true;
        return hit.transform == player || hit.transform.IsChildOf(player);
    }

    void StartAlert()
    {
        state = State.Alert;
        alertLeft = Tuning.STALKER_ALERT_S;
        hasTarget = false;
        lightChase = false;
        spots.Clear();
    }

    void StartInvestigate(Vector3 at, float speed, bool byLight)
    {
        if (state == State.Investigate && !lightChase && byLight)
            return;                                // 소음 조사 중엔 빛이 끼어들지 않는다
        SetTarget(at);
        investigateSpeed = speed;
        lightChase = byLight;
        spots.Clear();
        spotsVisited = 0;
        state = State.Investigate;
    }

    void BeginSearch()
    {
        hasTarget = false;
        lightChase = false;
        dwell = Tuning.STALKER_DWELL_S;
        spotsVisited = 1;                          // 도착 자리가 첫 곳
        spots.Clear();
        int n = rng.Next(Tuning.STALKER_SPOTS_MIN, Tuning.STALKER_SPOTS_MAX + 1) - 1;
        for (int i = 0; i < n; i++)
            spots.Add(RandomNear(transform.position, Tuning.STALKER_SEARCH_CELLS * Tuning.GRID_CELL));
        state = State.Search;
    }

    // 잡힘: 플레이어 잠금 → 검은 화면 → CATCH_RESTART_S 에 복도 시작점에서 다시 (설계서 v2 Step 2, 교차 검토 반영)
    void StartCatch()
    {
        state = State.Catch;
        catchT = 0f;
        catches++;
        hasTarget = false;
        if (playerBody != null) playerBody.frozen = true;
    }

    void UpdateCatch(float dt)
    {
        catchT += dt;
        black = Mathf.Clamp01(catchT / Tuning.CATCH_FADE_S);
        if (catchT < Tuning.CATCH_RESTART_S)
            return;
        var pcc = player.GetComponent<CharacterController>();
        pcc.enabled = false;
        player.SetPositionAndRotation(restartPos, Quaternion.identity);
        pcc.enabled = true;
        if (playerBody != null)
        {
            playerBody.ore = 0;
            playerBody.frozen = false;
        }
        restarts++;
        Teleport(homePos);
    }

    void OnGUI()
    {
        if (black <= 0f)
            return;
        if (blackTex == null)
        {
            blackTex = new Texture2D(1, 1);
            blackTex.SetPixel(0, 0, Color.black);
            blackTex.Apply();
        }
        GUI.color = new Color(0f, 0f, 0f, black);
        GUI.DrawTexture(new Rect(0, 0, Screen.width, Screen.height), blackTex);
        GUI.color = Color.white;
    }

    // 검사·배치용. 상태도 배회로 되돌린다 (체력은 안 건드린다)
    public void Teleport(Vector3 pos, float yaw = float.NaN)
    {
        cc.enabled = false;
        transform.position = pos;
        if (!float.IsNaN(yaw)) transform.rotation = Quaternion.Euler(0f, yaw, 0f);
        cc.enabled = true;
        hasTarget = false;
        lightChase = false;
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

    void Face(Vector3 at, float dt)
    {
        Vector3 dir = Flat3(at - transform.position);
        if (dir.sqrMagnitude > 1e-4f)
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir.normalized), 10f * dt);
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
    static Vector3 Flat3(Vector3 v) => new Vector3(v.x, 0f, v.z);
}
