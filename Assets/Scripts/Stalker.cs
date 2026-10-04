using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.SceneManagement;

// 괴물 (M3 귀·배회·조사·수색 + M4 눈·빛·alert·chase·catch + M5 체력·스턴·철수). Godot Stalker.gd 에서 옮겼다.
// 천장 이동은 모델 뒤. 던진 곡괭이(M6)는 ThrownPick 이 Hit 을 부른다 — 휘두른 한 대와 같다.
// 길: 부스 맵(MAP1, zMax ≤ zMin)은 길찾기 바닥(NavMesh)의 꺾는 점을 따라간다. 42 m 복도는 길찾기 바닥을 안 굽는다 — 길이 없으면 목적지로 곧장(옛 동작 그대로).
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
    public float zMin, zMax;                       // 갱도 축 범위 — 씬 생성기가 넣는다. 부스 맵은 0·0 (= 길찾기)
    public Vector3 restartPos;                     // 잡힌 뒤 플레이어가 서는 자리 (복도 시작점)
    public Vector3 homePos;                        // 잡힌 뒤 괴물이 돌아가는 자리 (북쪽 끝)
    public Vector3[] cracks = new Vector3[0];      // 갈라진 틈 — 철수 뒤 재등장 자리
    [System.NonSerialized] public bool hasAnchor;  // GAME-1: 배회 가운데를 감독이 정한다 (집 · 마지막으로 일한 자리). 없으면 제 자리 둘레 (옛 동작)
    [System.NonSerialized] public Vector3 anchor;
    [System.NonSerialized] public bool held;       // GAME-1: 감독이 숨은 굴에 넣어 둔 상태 — 꺼낼 때까지 안 나온다

    // 실행 중 조정·검사용 (씬에 안 굽는다)
    [System.NonSerialized] public float earMul = Tuning.STALKER_EAR_MUL;
    [System.NonSerialized] public float eyeM = Tuning.STALKER_EYE_M;
    [System.NonSerialized] public float lightM = Tuning.STALKER_LIGHT_M;   // 검사 사진: 램프를 켜고 찍으려고 잠시 0
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
    [System.NonSerialized] public bool returnToIntro = true;   // UI-2 (지침 4-1): 잡힌 뒤 Intro 씬으로 돌아간다. 검사는 옛 제자리 재시작으로 두고 intro 구간에서만 켠다
    [System.NonSerialized] public Vector3 noisePos, lastSeen;
    // 3D-④ MB 수색 더듬기 (영상 B4 통과 09-20): 첫 수색 자리(놓친 그 자리)에서만 STALKER_GROPE_S 동안 웅크려 가까운 면을 짚는다 — 몸짓은 StalkerAnim.
    // "들었나?": 더듬는 중 소리를 들으면(또는 heardChance 로 한 번) 몸이 굳고 머리만 그쪽을 딱 본 채 STALKER_HEARD_S — 그동안 자리 시간은 안 흐른다. 소리였으면 그 뒤에 조사하러 간다
    public bool Groping => state == State.Search && groping;
    public bool Heard => Groping && heardLeft > 0f;
    public Vector3 HeardPos { get; private set; }
    [System.NonSerialized] public bool grope = true;                       // 사보타주 nogrope
    [System.NonSerialized] public bool snapDown = true;                    // 사보타주 monsterfloat 가 끈다 — 비탈을 내려가며 떴다 붙었다 하던(옛) 상태
    [System.NonSerialized] public float heardChance = Tuning.STALKER_HEARD_CHANCE;
    [System.NonSerialized] public bool heardPause = true;                  // 사보타주 nohear: 더듬다 소리를 들어도 안 굳고 바로 간다
    [System.NonSerialized] public float foundM = Tuning.STALKER_FOUND_M;   // 사보타주 handfind 3.0 m(손보다 멀리) · shortfind 2.0 m(옛 값)
    [System.NonSerialized] public int heardCount;                          // 검사
    bool groping, heardPending;
    float heardLeft, heardAt;
    Vector3 heardGo;
    public bool LightChase => lightChase;          // 조사가 빛(플레이어 자리)을 따라가는 중 — 머리가 플레이어를 본다 (StalkerAnim)
    [System.NonSerialized] public Vector3 retreatSpot, retreatFrom, retreatFwd;   // 철수 자리, 그때 플레이어 자리·방향 (검사용)
    [System.NonSerialized] public bool retreatInCone;
    [System.NonSerialized] public float black;      // 잡힘 화면 검은 정도 0~1

    CharacterController cc;
    Renderer[] renderers;
    Vector3 target, backDir;
    bool hasTarget, lightChase;
    Vector3 gropeFace;                             // 첫 자리 더듬기 때 돌아설 쪽 (부스 맵)
    float pause, dwell, vy, stuck, alertLeft, unseen, catchT, stunLeft, investigateSpeed, retreatSide, noiseTime = -99f;
    readonly List<Vector3> spots = new List<Vector3>();
    readonly List<Vector3> corners = new List<Vector3>();   // 길찾기 꺾는 점 ([0] = 출발)
    NavMeshPath navPath;
    int corner;
    Vector3 climbDir;
    float climbTop;
    bool Nav => zMax <= zMin;
    static readonly RaycastHit[] rayBuf = new RaycastHit[16];
    // 제 몸(충돌 캡슐)을 빼고 가장 가까운 것. 캡슐 안에서 쏜 광선이 제 캡슐에 맞았다 (부스 첫 검사 09-24)
    public static bool RayIgnore(Vector3 o, Vector3 d, float max, int mask, Collider self, out RaycastHit best)
    {
        int n = Physics.RaycastNonAlloc(o, d, rayBuf, max, mask, QueryTriggerInteraction.Ignore);
        best = default; float bd = float.MaxValue; bool any = false;
        for (int i = 0; i < n; i++)
            if (rayBuf[i].collider != self && rayBuf[i].distance < bd) { bd = rayBuf[i].distance; best = rayBuf[i]; any = true; }
        return any;
    }
    public Vector3 ClimbFacing => Nav && climbDir != Vector3.zero ? climbDir : Vector3.right * (transform.position.x >= 0f ? 1f : -1f);   // StalkerAnim: 벽타기 때 몸을 벽 정면으로
    readonly System.Random rng = new System.Random(Tuning.MAP_SEED + 200);
    readonly System.Random heardRng = new System.Random(Tuning.MAP_SEED + 201);   // "들었나?"는 제 난수로 — rng 를 같이 쓰면 수색 자리 차례가 바뀐다 (09-20: 옛 수색 검사가 램프에 들켜 빠졌다)
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
        if (Time.time - noiseTime > Tuning.STALKER_HEAR_CONFIRM_S || Flat(pos - noisePos) > Tuning.STALKER_NOISE_SAME_M)
            hits = 0;
        hits++;
        noisePos = pos;
        noiseTime = Time.time;
        lastHeard = $"{kind} {d:F1} m x{hits}";
        Vector3 to = pos - transform.position;
        to.y = 0f;
        Vector3 t = hits >= 2 ? pos : transform.position + Vector3.ClampMagnitude(to, Tuning.STALKER_HEAR_SOFT_M);
        if (Groping && heardPause)                 // 더듬다 들었다: 바로 안 간다 — 굳어서 그쪽을 본 뒤에
        {
            if (heardLeft <= 0f) { heardLeft = Tuning.STALKER_HEARD_S; heardCount++; }
            HeardPos = pos; heardGo = t; heardPending = true;
            return;
        }
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
                    else SetTarget(RandomNear(hasAnchor ? anchor : transform.position, Tuning.STALKER_WANDER_CELLS * Tuning.GRID_CELL));
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
                if (Heard)
                {
                    heardLeft -= dt;
                    if (heardLeft <= 0f && heardPending) { heardPending = false; StartInvestigate(heardGo, Tuning.STALKER_SPEED_INVESTIGATE, false); }
                    break;
                }
                if (groping && heardAt > 0f && dwell <= heardAt)           // 조용히 있어도 가끔: 내 쪽(±25° 빗나가게)을 본다
                {
                    heardAt = 0f; heardLeft = Tuning.STALKER_HEARD_S; heardCount++;
                    HeardPos = transform.position + Quaternion.Euler(0f, ((float)heardRng.NextDouble() * 2f - 1f) * Tuning.STALKER_HEARD_MISS_DEG, 0f) * (player.position - transform.position);
                    break;
                }
                if (!hasTarget)
                {
                    if (groping && gropeFace != Vector3.zero) Face(transform.position + gropeFace, dt);
                    if (dwell > 0f) { dwell -= dt; if (dwell <= 0f) groping = false; }
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
        if (Nav)
        {
            if (NavMesh.SamplePosition(spot, out NavMeshHit h, Tuning.STALKER_RETREAT_MAX_M, NavMesh.AllAreas)) spot = h.position;
        }
        else
        {
            spot.x = retreatSide * Tuning.STALKER_LANE_X;
            spot.y = transform.position.y;
            spot.z = Mathf.Clamp(spot.z, zMin, zMax);
        }
        retreatSpot = spot;
        SetTarget(spot);
        state = State.Retreat;
    }

    // 벽에 붙어 오른다. TUNNEL_ARCH_Y 에 닿으면 사라진다. 부스 맵: 가장 가까운 벽으로, 그 자리 천장까지
    void UpdateClimb(float dt)
    {
        Vector3 p = transform.position;
        if (Nav)
        {
            if (climbDir == Vector3.zero) StartClimbNav();
            p += climbDir * Mathf.Min(Tuning.STALKER_WALL_SPEED * dt, Mathf.Max(0f, WallDist(p) - Tuning.STALKER_R));
            p.y += Tuning.STALKER_WALL_SPEED * dt;
            transform.position = p;
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(climbDir), 5f * dt);
            if (p.y < climbTop)
                return;
            climbDir = Vector3.zero;
            state = State.Hidden;
            hiddenLeft = Tuning.STALKER_REGEN_S;
            foreach (var r in renderers) r.enabled = false;
            return;
        }
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

    // 부스 맵 벽타기: 8 방향 중 가장 가까운 벽 쪽, 오를 높이 = 그 자리 천장 − 캡슐 반쯤 (못 재면 2 m)
    void StartClimbNav()
    {
        Vector3 at = transform.position + Vector3.up * 1.2f;
        float best = 99f;
        for (int i = 0; i < 8; i++)
        {
            Vector3 d = Quaternion.Euler(0f, i * 45f, 0f) * Vector3.forward;
            if (RayIgnore(at, d, 8f, RayMask, cc, out RaycastHit h) && h.distance < best) { best = h.distance; climbDir = d; }
        }
        if (climbDir == Vector3.zero) climbDir = transform.forward;
        climbTop = transform.position.y + (RayIgnore(at, Vector3.up, 6f, RayMask, cc, out RaycastHit up) ? up.distance + 1.2f - 0.4f : 2f);
    }

    float WallDist(Vector3 p) => RayIgnore(new Vector3(p.x, transform.position.y + 1.2f, p.z), climbDir, 8f, RayMask, cc, out RaycastHit h) ? h.distance : 0f;

    // 숨어서 회복. 끝나면 플레이어에서 먼 틈에서 체력 100 으로 배회
    void UpdateHidden(float dt)
    {
        if (held) return;                          // 감독이 꺼낸다 (Release)
        hiddenLeft -= dt;
        if (hiddenLeft > 0f)
            return;
        Vector3 at = homePos;
        float best = -1f;
        foreach (var c in cracks)
        {
            float d = Flat(c - player.position);
            if (d > best && Open(c)) { best = d; at = c; }
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
        else if (state == State.Search && d <= foundM)
            sense = "found";
        else if (lit && d <= lightM && Clear())
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
        Vector3 eye = transform.position + Vector3.up * EyeH();
        Vector3 to = playerHead.position - eye;
        if (!Physics.Raycast(eye, to.normalized, out RaycastHit hit, to.magnitude, RayMask, QueryTriggerInteraction.Ignore))
            return true;
        return hit.transform == player || hit.transform.IsChildOf(player);
    }

    // 눈 높이: 부스 맵은 천장이 2.2~2.7 m 라 STALKER_EYE_H(2.4)가 바위 속일 수 있다 — 그 자리 천장 밑 0.3 m 로 누른다
    float EyeH()
    {
        if (!Nav) return Tuning.STALKER_EYE_H;
        Vector3 at = transform.position + Vector3.up;
        return RayIgnore(at, Vector3.up, Tuning.STALKER_EYE_H, RayMask, cc, out RaycastHit h)
            ? Mathf.Min(Tuning.STALKER_EYE_H, 1f + h.distance - 0.3f) : Tuning.STALKER_EYE_H;
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
        SetTarget(Nav ? Centered(at) : at);
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
        groping = grope;                           // 첫 곳(놓친 그 자리)에서만 더듬는다 — 사용자 결정 09-20
        gropeFace = groping && Nav ? OpenFacing() : Vector3.zero;
        dwell = groping ? Tuning.STALKER_GROPE_S : Tuning.STALKER_DWELL_S;
        heardLeft = 0f; heardPending = false;
        heardAt = groping && heardRng.NextDouble() < heardChance ? dwell * Mathf.Lerp(0.35f, 0.6f, (float)heardRng.NextDouble()) : 0f;
        spotsVisited = 1;                          // 도착 자리가 첫 곳
        spots.Clear();
        int n = rng.Next(Tuning.STALKER_SPOTS_MIN, Tuning.STALKER_SPOTS_MAX + 1) - 1;
        for (int i = 0; i < n; i++)
            spots.Add(RandomNear(transform.position, Tuning.STALKER_SEARCH_CELLS * Tuning.GRID_CELL));
        state = State.Search;
    }

    // 잡힘: 플레이어 잠금 → 검은 화면 → CATCH_RESTART_S 에 복도 시작점에서 다시 (설계서 v2 Step 2, 교차 검토 반영)
    public void ForceCatch() => StartCatch();   // 검사(intro 구간)가 추격 없이 잡힘만 일으킨다

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
        if (returnToIntro)                       // UI-2: 씬을 다시 불러 처음(인트로)으로 — 광석·괴물·곡괭이 전부 새것
        {
            restarts++;
            enabled = false;
            SceneManager.LoadScene("Intro");
            return;
        }
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

    // GAME-1 감독: 아무도 못 볼 때 벽 속(숨은 굴)으로 들어간다 — 몸 · 충돌을 끄고 Release 까지 기다린다
    public void Hold()
    {
        state = State.Hidden; held = true; hasTarget = false; lightChase = false; spots.Clear();
        cc.enabled = false;
        foreach (var r in renderers) r.enabled = false;
    }

    // 감독이 출구 앞에 꺼낸다 (아무도 그 자리를 못 볼 때만 부른다) — 배회로 시작, 체력은 그대로
    public void Release(Vector3 pos, float yaw)
    {
        held = false;
        foreach (var r in renderers) r.enabled = true;
        Teleport(pos, yaw);
    }

    // 감독이 보낸 자리를 살피러 간다 — 소리를 들은 것과 같은 길 (조사 → 수색 → 배회)
    // 조사 중 머리는 noisePos 를 본다 — 안 넣으면 옛 소리 자리(못 들었으면 (0,0,0) = MAP4 200 m 위)를 보며 걷는다 (10-04 판정 1 "두리번")
    public void SendTo(Vector3 at, float speed) { if (!Map4.Sab("stalehead")) noisePos = at; StartInvestigate(at, speed, false); }

    void SetTarget(Vector3 t)
    {
        corners.Clear();
        corner = 1;
        if (Nav)
        {
            if (NavMesh.SamplePosition(t, out NavMeshHit h, 4f, NavMesh.AllAreas)) t = h.position;
            if (NavMesh.CalculatePath(transform.position, t, NavMesh.AllAreas, navPath ??= new NavMeshPath()) && navPath.corners.Length > 1)
            {
                corners.AddRange(navPath.corners);           // 길이 없으면(바닥 밖) 곧장 — 막히면 STALKER_STUCK_S 그물
                for (int i = 1; i < corners.Count - 1; i++)   // 꺾는 점은 바닥 끝(= 벽에서 0.6 m) 모서리에 붙어 있다 — 숙인 머리가 몸보다 1 m 앞이라 기둥 모서리를 돌 때 벽에 0.5 m 파고들었다 (MAP2 검사 09-25)
                    corners[i] = Inward(corners[i], Tuning.STALKER_CORNER_KEEP_M);
            }
        }
        else
        {
            t.x = Mathf.Clamp(t.x, -Tuning.STALKER_LANE_X, Tuning.STALKER_LANE_X);
            t.z = Mathf.Clamp(t.z, zMin, zMax);
        }
        t.y = transform.position.y;
        target = t;
        hasTarget = true;
    }

    // 소리 난 자리가 벽이면(광맥) 가장 가까운 괴물 바닥은 그 벽 쪽 끝 — 좁은 굴에서 거기 서서 더듬으면 손·머리가 벽 속으로. 끝에서 0.6 m 안으로 (2.4 m 굴이면 가운데)
    Vector3 Centered(Vector3 t) => NavMesh.SamplePosition(t, out NavMeshHit h0, 4f, NavMesh.AllAreas) ? Inward(h0.position, 0.6f) : t;

    // 바닥 끝(가장 가까운 괴물 바닥 가장자리)에서 keep 만큼 안쪽 자리. 굴이 좁으면 늘릴 수 있는 만큼만
    static Vector3 Inward(Vector3 p, float keep)
    {
        if (!NavMesh.FindClosestEdge(p, out NavMeshHit e, NavMesh.AllAreas) || e.distance >= keep) return p;
        foreach (float s in new[] { 1f, -1f })                                   // 가장자리 법선의 방향이 안쪽인지 몰라 둘 다 — 가장자리에서 멀어지는 쪽
            if (NavMesh.SamplePosition(p + e.normal * s * (keep - e.distance), out NavMeshHit h, 0.5f, NavMesh.AllAreas)
                && NavMesh.FindClosestEdge(h.position, out NavMeshHit e2, NavMesh.AllAreas) && e2.distance > e.distance + 0.1f) return h.position;
        return p;
    }

    // 더듬을 쪽: 지금 향한 쪽에서 가장 가까운, 앞 STALKER_WALL_STOP_M 이 트인 방향 — 옆벽 광맥 앞에서 벽을 본 채 웅크리면 머리가 벽 속으로 들어갔다 (MAP2 검사 09-25)
    Vector3 OpenFacing()
    {
        Vector3 f = Flat3(transform.forward).normalized;
        for (int k = 0; k <= 8; k++)
            foreach (int s in new[] { 1, -1 })
            {
                Vector3 d = Quaternion.Euler(0f, s * k * 22.5f, 0f) * f;
                if (!RayIgnore(transform.position + Vector3.up * 1.5f, d, Tuning.STALKER_WALL_STOP_M, RayMask, cc, out _)) return d;
            }
        return f;
    }

    // 집(시작 자리)에서 길이 이어지는가 — 부스판 막힘 돌무더기 너머의 틈에서 나오면 못 돌아온다 (MAP2: 먼 틈이 거의 다 닫힌 위 구역에 있다)
    bool Open(Vector3 p) => !Nav || NavMesh.SamplePosition(p, out NavMeshHit a, 2f, NavMesh.AllAreas) && NavMesh.SamplePosition(homePos, out NavMeshHit b, 2f, NavMesh.AllAreas)
        && NavMesh.CalculatePath(a.position, b.position, NavMesh.AllAreas, navPath ??= new NavMeshPath()) && navPath.status == NavMeshPathStatus.PathComplete;

    Vector3 RandomNear(Vector3 center, float range)
    {
        float u = (float)(rng.NextDouble() * 2.0 - 1.0), v = (float)(rng.NextDouble() * 2.0 - 1.0);
        if (!Nav)
            return new Vector3(u * Tuning.STALKER_LANE_X, center.y, center.z + v * range);
        // ponytail: 네모 안 무작위 점을 바닥에 붙인다 — 벽 너머 다른 갱도에 붙으면 길이가 range 보다 길다. 배회 범위를 덩어리 단위로 묶을 때 고친다
        return NavMesh.SamplePosition(center + new Vector3(u * range, 0f, v * range), out NavMeshHit h, range, NavMesh.AllAreas) ? h.position : center;
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
        if (Nav && state == State.Investigate && d < 3f && RayIgnore(transform.position + Vector3.up * 1.5f, to, Tuning.STALKER_WALL_STOP_M, RayMask, cc, out _))
            return true;                                       // 광맥은 벽에 있다 — 벽 앞에서 멈춰 벽 쪽으로 더듬는다
        while (corner < corners.Count - 1 && Flat(corners[corner] - transform.position) < 0.4f)
            corner++;                                          // 꺾는 점에 닿으면 다음 점으로
        if (corner < corners.Count - 1)
        {
            to = corners[corner] - transform.position;
            to.y = 0f;
            d = Mathf.Max(to.magnitude, speed * dt);           // 중간 점에서는 안 늦춘다
        }
        Vector3 dir = to / Mathf.Max(to.magnitude, 1e-4f);
        Vector3 face = corners.Count > 1 ? Flat3(LookAhead(1.6f) - transform.position) : dir;   // 몸은 꺾는 점으로, 얼굴은 길 1.6 m 앞 — 숙인 머리가 몸보다 1 m 앞이라 모퉁이 안쪽 벽을 스쳤다 (09-24)
        transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(face.sqrMagnitude > 1e-4f ? face.normalized : dir), 10f * dt);
        bool grounded = cc.isGrounded;
        float v = Mathf.Min(speed, d / Mathf.Max(dt, 1e-4f));
        vy = grounded ? -1f : vy - Tuning.GRAVITY * dt;
        cc.Move((dir * v + Vector3.up * vy) * dt);
        // 비탈 내려가기 (Player 와 같은 방법): 노보리 25° 를 조사 5 m/s 로 내려가면 1초에 2.3 m 떨어지는데 바닥 붙이기는 −1 m/s 라 프레임 75 % 가 떠 있었다 (MAP2 검사 09-25).
        // 걸을 수 있는 가장 가파른 비탈이 이번 이동만큼 떨어뜨리는 거리를 내려 본다 — 못 닿으면(턱 밖) 되돌린다
        if (grounded && !cc.isGrounded && snapDown)
        {
            float drop = v * dt * Mathf.Tan(cc.slopeLimit * Mathf.Deg2Rad) + 0.02f;
            cc.Move(Vector3.down * drop);
            if (!cc.isGrounded) cc.Move(Vector3.up * drop);
        }
        // 벽·플레이어에 막혀 STALKER_STUCK_S 동안 못 가면 도착으로 친다 (무한히 미는 것을 막는 그물)
        stuck = cc.velocity.sqrMagnitude < 0.01f ? stuck + dt : 0f;
        if (stuck < Tuning.STALKER_STUCK_S)
            return false;
        stuck = 0f;
        return true;
    }

    // 길을 따라 지금 자리에서 dist 만큼 앞의 점
    Vector3 LookAhead(float dist)
    {
        Vector3 at = transform.position;
        for (int i = corner; i < corners.Count; i++)
        {
            float seg = Flat(corners[i] - at);
            if (seg >= dist) return at + Flat3(corners[i] - at).normalized * dist;
            dist -= seg; at = corners[i];
        }
        return at;
    }

    void Fall(float dt)
    {
        vy = cc.isGrounded ? -1f : vy - Tuning.GRAVITY * dt;
        cc.Move(Vector3.up * vy * dt);
    }

    static float Flat(Vector3 v) => new Vector2(v.x, v.z).magnitude;
    static Vector3 Flat3(Vector3 v) => new Vector3(v.x, 0f, v.z);
}
