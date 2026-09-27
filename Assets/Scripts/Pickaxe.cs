using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

// 화면에 들린 곡괭이(뷰모델)와 채굴. Godot Pickaxe.gd + Miner.gd.
// MINE-1 (제안서 docs/제안서_MINE1_캐기_연출.md, 승인 09-27): 광석(포켓)을 보고 좌클릭을 누르고 있으면 "한 묶음"(Mine) —
//   콱 여럿(서서 셋 · 쪼그려 다섯, 박자는 실제 영상에서 잰 값) → 박힌 채 당겨 비틀기(광석이 기운다) → 덩이 빠짐 → 날 눕혀 긁기.
//   포켓 체력이 곧 진행이라 손을 떼도 남는다. 평소 콱은 MINE_NOISE_SOFT(6 m). 묶음마다 MINE_SLIP_CHANCE 로 미끄러질 조짐(꼭대기에서 떨림) —
//   MINE_SLIP_WARN_S 안에 좌클릭을 떼었다 다시 누르면 고쳐 잡기(조용), 계속 누르면 '쨍' NOISE_PICK 한 번(괴물 한 칸 — 사용자 09-27 "약하게").
//   캐는 동안 몸은 멈추고 고개만 MINE_LOOK_* 안에서 돈다(Player.BeginMine). 고개를 돌려도 곡괭이는 광석을 친다(시작 카메라 기준으로 되돌려 둔다).
// 괴물을 겨냥하면 옛 빠른 휘두르기(Swing): 뒤로 들기 → 내려치기 → 끝나는 순간 다시 쏴서 맞은 것을 친다 → 박힌 채 잠깐 멈춤 → 되돌리기.
// 곡괭이는 ViewModel 레이어라 오버레이 카메라가 그린다(벽 속으로 들어가도 벽 위에 보인다). 헤드램프는 안 비추고 PickLight 만 비춘다.
// 우클릭 = 던지기 (M6). 곡괭이는 하나뿐 — 던지면 hasPick 이 false 라 못 캐고, ThrownPick 옆에서 E 로 주워야(Return) 다시 캔다.
// 내구도 (UI-1a): 콱마다 MINE_WEAR_BUNDLE ÷ 콱 수(한 묶음 = 2, 캐기 30 번 = 60), 미끄러지면 MINE_WEAR_SLIP, 괴물 타격 −1, 던지기 −5.
// PICK_SHAKY_BELOW 이하면 닿은 타격 뒤 뷰모델이 떨린다. 0 이 되는 순간 Break — 손에서 조각나 바닥에 떨어졌다 사라지고 빈손. 42 m 판은 DevHud 3/4 키(Adjust)
// 손 잡는 자리 GRIP_Rear · GRIP_Front (3D-P 의 팔이 따라간다) — 곡괭이 그물 밑 빈 점.
public class Pickaxe : MonoBehaviour
{
    public const int ViewModelLayer = 8;                 // ProjectSettings/TagManager "ViewModel"
    public const uint DefaultRenderingLayer = 1u;        // 조명 레이어: 갱도·헤드램프
    public const uint ViewModelRenderingLayer = 2u;      // 조명 레이어: 곡괭이·PickLight

    public Transform cam;
    public Player player;
    public Transform mesh;
    public ThrownPick thrown;                            // 씬에 하나. 던지면 켜고 주우면 끈다
    // 검사가 실행 중에 바꾼다. 값은 Tuning 한 곳
    [System.NonSerialized] public float damage = Tuning.MINE_DAMAGE;   // 괴물 · 사보타주 minefast. 묶음의 콱 하나 = POCKET_HEALTH ÷ 콱 수 × (damage ÷ MINE_DAMAGE) — 0 이면 안 캐진다(검사)
    [System.NonSerialized] public float cooldownTime = Tuning.MINE_COOLDOWN;
    [System.NonSerialized] public float swingTimeMul = 1f;
    [System.NonSerialized] public float aimRadius = Tuning.PICK_AIM_RADIUS;
    [System.NonSerialized] public bool oneOnly = true;   // 사보타주 twopicks 가 끈다 — 던져도 손에 남는 상태
    [System.NonSerialized] public bool hasPick = true;
    [System.NonSerialized] public float durability = Tuning.PICK_DURABILITY_MAX;
    [System.NonSerialized] public int hitsLanded;        // 검사용: 포켓·괴물에 닿은 타격 수 (미끄러짐은 안 센다)
    [System.NonSerialized] public bool dulls = true;     // 사보타주 nodull 이 끈다 — 안 닳는 상태
    [System.NonSerialized] public bool shaky = true;     // 사보타주 steadyhands 가 끈다 — 떨림 없는 상태
    [System.NonSerialized] public bool breaks = true;    // 사보타주 everlasting 이 끈다 — 0 이어도 손에 남고 캐지는 상태
    // MINE-1 판정 키(DevHud 숫자패드 7 8 · 1 2 · / *)와 사보타주
    [System.NonSerialized] public float tempo = Tuning.MINE_TEMPO;
    [System.NonSerialized] public float slipChance = Tuning.MINE_SLIP_CHANCE;
    [System.NonSerialized] public float softNoise = Tuning.MINE_NOISE_SOFT;    // 사보타주 loudsoft 가 NOISE_PICK 으로
    [System.NonSerialized] public float lookYaw = Tuning.MINE_LOOK_YAW_DEG;    // 사보타주 lookfree 가 180 으로
    [System.NonSerialized] public bool oldMining;        // 사보타주 minefast — 옛 두 번 치기(휘두를 때마다 25 m)
    [System.NonSerialized] public bool resetOnRelease;   // 사보타주 resetprogress — 떼면 진행 0
    [System.NonSerialized] public bool slipsOn = true;   // 사보타주 noslip 이 끈다 — 조짐이 안 오는 상태
    // 검사가 읽는다
    [System.NonSerialized] public int bundles, slips, regrips;
    [System.NonSerialized] public string minePhase = "";   // lift top warn down stuck out slip pry fall scrape lower
    [System.NonSerialized] public bool mineCrouch;
    [System.NonSerialized] public float lastShake;       // 이번 프레임 손 떨림 크기 (m)
    public readonly List<float> strikeTimes = new List<float>();   // 콱 시각 (Time.time)
    [System.NonSerialized] public Transform gripRear, gripFront;
    public bool Mining => mining != null;

    public bool Broken => !hasPick && (thrown == null || !thrown.gameObject.activeSelf);   // 빈손인데 주울 곡괭이도 없다

    static readonly RaycastHit[] Hits = new RaycastHit[16];
    float cooldown;
    bool swinging;
    Vector3 basePos = Tuning.PICK_POS;                   // 흔들림(걷기)까지 더한 자리. 떨림은 이 위에 얹는다
    float shakeLeft;
    Coroutine mining;
    Quaternion mineCamRot;                               // 묶음 시작 때 카메라 방향 — 곡괭이 자세는 이 기준
    Vector3 posePos;
    float poseTilt, poseYaw, poseWobble;

    void Awake()
    {
        transform.localPosition = Tuning.PICK_POS;
        SetTilt(Tuning.PICK_TILT_DEG);
        // "드는 자세"는 mesh 에, "휘두르기"는 이 노드에 — 한 곳에 섞으면 자세를 만질 때 스윙 축이 같이 틀어진다
        mesh.localScale = Vector3.one * Tuning.PICK_SCALE;
        mesh.localRotation = Quaternion.AngleAxis(Tuning.PICK_ROLL_DEG, Vector3.right) * Quaternion.AngleAxis(Tuning.PICK_YAW_DEG, Vector3.up);
        foreach (var r in mesh.GetComponentsInChildren<Renderer>())
            r.shadowCastingMode = ShadowCastingMode.Off;   // 등과 같은 자리라 그림자가 화면을 덮는다
        gripRear = Grip("GRIP_Rear", Tuning.GRIP_REAR);
        gripFront = Grip("GRIP_Front", Tuning.GRIP_FRONT);
    }

    Transform Grip(string name, Vector3 at)
    {
        var t = new GameObject(name).transform;
        t.SetParent(mesh, false);
        t.localPosition = at;
        t.gameObject.layer = ViewModelLayer;
        return t;
    }

    void Update()
    {
        cooldown = Mathf.Max(0f, cooldown - Time.deltaTime);
        shakeLeft = Mathf.Max(0f, shakeLeft - Time.deltaTime);
        var mouse = Mouse.current;
        if (Mining)
        {
            ApplyPose();
            return;
        }
        if (!swinging && hasPick && mouse != null && mouse.rightButton.wasPressedThisFrame && !player.Busy)
        {
            Throw();
            return;
        }
        if (cooldown <= 0f && !swinging && hasPick && !player.Squeezing && !player.Repairing && mouse != null && mouse.leftButton.isPressed && Target(out var pocket, out var stalker, out var hit))
        {
            if (stalker != null || oldMining)
            {
                cooldown = cooldownTime;
                StartCoroutine(Swing());
            }
            else
            {
                mining = StartCoroutine(Mine(pocket, hit.point));
                ApplyPose();
                return;
            }
        }
        if (!swinging && hasPick)
        {
            // 걸을 때만 흔들린다. 서 있으면 멎는다. 위상은 Player.gait — 발이 땅에 닿는 순간(π 마다) 곡괭이가 맨 아래를 지난다 = 발소리와 같은 때
            // 바위 틈을 비집는 동안은 곡괭이를 화면 밖으로 내린다 (Player.squeezeLower)
            if (player.gait <= 0f)
                basePos = Vector3.Lerp(basePos, Tuning.PICK_POS + Tuning.SQUEEZE_PICK_DROP * player.squeezeLower, Mathf.Min(Time.deltaTime * 8f, 1f));
            else
                basePos = Tuning.PICK_POS + new Vector3(Mathf.Cos(player.gait), Mathf.Abs(Mathf.Sin(player.gait)), 0f) * Tuning.PICK_BOB_AMOUNT;
        }
        // 손 떨림 (내구도 PICK_SHAKY_BELOW 이하, 닿은 타격 뒤 PICK_SHAKE_S). 곡괭이만 — 머리(Player.Shake)는 안 흔든다
        Vector3 shake = shakeLeft > 0f ? Random.insideUnitSphere * Tuning.PICK_SHAKE_AMOUNT : Vector3.zero;
        lastShake = shake.magnitude;
        transform.localPosition = basePos + shake;
    }

    // 캐는 동안: 자세는 묶음 시작 때 카메라 기준 — 고개를 돌린 만큼 되돌려 둔다(곡괭이는 광석을 계속 친다)
    void ApplyPose()
    {
        Quaternion back = Quaternion.Inverse(cam.rotation) * mineCamRot;
        Vector3 shake = shakeLeft > 0f ? Random.insideUnitSphere * Tuning.PICK_SHAKE_AMOUNT : Vector3.zero;
        lastShake = shake.magnitude;
        transform.localPosition = back * posePos + shake;
        transform.localRotation = back * Quaternion.Euler(poseTilt, poseYaw + poseWobble, poseWobble * 0.5f);
    }

    public bool HasTarget => Target(out _, out _, out _);   // 검사가 읽는다

    // 판정 구(aimRadius) 위 가장 가까운 포켓. 벽 충돌체는 무시한다 — Godot MineRay 가 포켓 레이어만 봤다(mask 4).
    // 포켓 앞면은 벽 충돌 상자보다 몇 cm 만 나와 있어서, 벽에 막히게 두면 포켓 아래를 조준했을 때 안 맞았다(09-14 검사)
    bool Target(out OrePocket pocket, out Stalker stalker, out RaycastHit hit)
    {
        pocket = null;
        stalker = null;
        hit = default;
        int n = aimRadius > 0f
            ? Physics.SphereCastNonAlloc(cam.position, aimRadius, cam.forward, Hits, Tuning.MINE_RANGE, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore)
            : Physics.RaycastNonAlloc(cam.position, cam.forward, Hits, Tuning.MINE_RANGE, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore);
        for (int i = 0; i < n; i++)
        {
            var candidate = Hits[i].collider.GetComponent<OrePocket>();
            if (candidate != null && !candidate.Breaking && (pocket == null || Hits[i].distance < hit.distance))
            {
                pocket = candidate;
                hit = Hits[i];
            }
            var monster = Hits[i].collider.GetComponent<Stalker>();       // 괴물 (M5). 포켓보다 가까우면 괴물을 친다
            if (monster != null && monster.CanBeHit && (stalker == null || Hits[i].distance < hit.distance))
            {
                stalker = monster;
                hit = Hits[i];
            }
        }
        if (stalker != null && pocket != null)
        {
            if (hit.collider.GetComponent<Stalker>() != null) pocket = null; else stalker = null;
        }
        if (hit.distance <= 0f)
            hit.point = pocket != null ? pocket.transform.position : stalker != null ? stalker.transform.position + Vector3.up * 1.4f : hit.point;  // 구가 처음부터 겹치면 닿은 점이 없다
        return pocket != null || stalker != null;
    }

    // ---- MINE-1 한 묶음 ----
    bool Held(OrePocket pocket)
    {
        var mouse = Mouse.current;
        return hasPick && !player.frozen && pocket != null && !pocket.Breaking && mouse != null && mouse.leftButton.isPressed;
    }

    // 자세를 time 동안 옮긴다. stopOn 이 있으면 손을 떼는 순간 멈춘다
    IEnumerator PoseTo(Vector3 pos, float tilt, float time, System.Func<float, float> ease, OrePocket stopOn = null, float yaw = Tuning.MINE_SWING_YAW)
    {
        Vector3 p0 = posePos;
        float t0 = poseTilt, y0 = poseYaw;
        for (float t = 0f; t < time; t += Time.deltaTime)
        {
            if (stopOn != null && !Held(stopOn)) yield break;
            float u = ease(t / time);
            posePos = Vector3.LerpUnclamped(p0, pos, u);
            poseTilt = Mathf.LerpUnclamped(t0, tilt, u);
            poseYaw = Mathf.LerpUnclamped(y0, yaw, u);
            yield return null;
        }
        posePos = pos;
        poseTilt = tilt;
        poseYaw = yaw;
    }

    static float EaseOut(float u) => Mathf.Sin(u * Mathf.PI * 0.5f);
    static float EaseIn(float u) => u * u;

    IEnumerator Mine(OrePocket pocket, Vector3 point)
    {
        mineCamRot = cam.rotation;
        posePos = transform.localPosition;
        poseTilt = Tuning.PICK_TILT_DEG;
        poseYaw = 0f;
        bool low = pocket.transform.position.y - player.transform.position.y < Tuning.MINE_LOW_M;
        mineCrouch = low || player.stance == "crouch";
        player.BeginMine(low, lookYaw);
        bundles++;
        float T = tempo * swingTimeMul;
        float[] st = mineCrouch ? Tuning.MINE_STRIKE_CROUCH : Tuning.MINE_STRIKE_STAND;
        int per = mineCrouch ? Tuning.MINE_STRIKES_CROUCH : Tuning.MINE_STRIKES_STAND;
        float dmg = Tuning.POCKET_HEALTH / per * damage / Tuning.MINE_DAMAGE;
        Vector3 raise = mineCrouch ? Tuning.MINE_RAISE_POS_LOW : Tuning.MINE_RAISE_POS;
        float raiseTilt = mineCrouch ? Tuning.MINE_RAISE_TILT_LOW : Tuning.MINE_RAISE_TILT;
        Vector3 hitDir = (pocket.transform.position - cam.position).normalized;
        int remaining = dmg > 0f ? Mathf.CeilToInt(pocket.health / dmg - 0.001f) : 1000;
        int slipAt = !slipsOn ? -1 : slipChance >= 1f ? 0 : Random.value < slipChance ? Random.Range(0, Mathf.Max(1, Mathf.Min(remaining, per))) : -1;
        bool held = true;
        for (int k = 0; held && pocket.health > 0f; k++)
        {
            minePhase = "lift";
            yield return PoseTo(raise, raiseTilt, st[0] * T, EaseOut, pocket);
            if (!(held = Held(pocket))) break;
            minePhase = "top";
            for (float t = 0f; t < st[1] * T && (held = Held(pocket)); t += Time.deltaTime) yield return null;
            if (!held) break;
            bool slip = false;
            if (k == slipAt)
            {
                // 미끄러질 조짐: 꼭대기에서 곡괭이가 떨리고 딸각거린다. 떼었다 다시 누르면 고쳐 잡기, 떼고 안 누르면 멈춤, 계속 누르면 미끄러진다
                minePhase = "warn";
                bool released = false, regrip = false;
                float next = 0f;
                for (float t = 0f; t < Tuning.MINE_SLIP_WARN_S; t += Time.deltaTime)
                {
                    poseWobble = Mathf.Sin(t * 45f) * Tuning.MINE_SLIP_WOBBLE_DEG;
                    if (t >= next) { MiningFx.I.PickSound(point, 0.3f, 1.9f); next += Tuning.MINE_SLIP_WARN_S / 3f; }
                    var mouse = Mouse.current;
                    bool down = mouse != null && mouse.leftButton.isPressed;
                    if (!hasPick || player.frozen) break;
                    if (!down) released = true;
                    else if (released) { regrip = true; break; }
                    yield return null;
                }
                poseWobble = 0f;
                if (!hasPick || player.frozen || (released && !regrip)) { held = false; break; }
                if (regrip) regrips++;
                else slip = true;
            }
            minePhase = "down";
            yield return PoseTo(Tuning.MINE_HIT_POS, Tuning.MINE_HIT_TILT, st[2] * T, EaseIn, slip ? null : pocket);
            if (!slip && !(held = Held(pocket))) break;
            if (slip)
            {
                Slip(point);                                        // 튕긴 채 잠깐 — 그 콱은 안 친 셈, 다음 콱으로
                for (float t = 0f; t < 0.25f * T && (held = Held(pocket)); t += Time.deltaTime) yield return null;
                if (!held) break;
                continue;
            }
            StrikeOre(pocket, point, hitDir, dmg);
            if (!hasPick) { held = false; break; }                 // 이 콱에 부서졌다
            minePhase = "stuck";
            float stuck = st[3] * T;
            for (float t = 0f; t < stuck && (held = Held(pocket)); t += Time.deltaTime)
            {
                posePos = Tuning.MINE_HIT_POS + Random.insideUnitSphere * 0.004f;   // 박힌 채 버팀 — 손이 조금 떨린다
                yield return null;
            }
            posePos = Tuning.MINE_HIT_POS;
            if (!held) break;
            minePhase = "out";
            yield return PoseTo(Tuning.MINE_HIT_POS + new Vector3(0f, 0.03f, -0.06f), Tuning.MINE_HIT_TILT - 12f, st[4] * T, EaseOut, pocket);
            if (!(held = Held(pocket))) break;
        }
        if (held && pocket != null && pocket.health <= 0f && !pocket.Breaking)
        {
            // 박힌 채 자루를 아래·몸 쪽으로 당겨 비튼다 — 덩이가 기운다, 머리가 조금 앞으로
            if (poseTilt < 0f) yield return PoseTo(Tuning.MINE_HIT_POS, Tuning.MINE_HIT_TILT, 0.15f * T, EaseIn, pocket);   // (진행이 다 찬 채로 다시 시작했을 때)
            minePhase = "pry";
            float pry = (mineCrouch ? Tuning.MINE_PRY_CROUCH : Tuning.MINE_PRY_STAND) * T;
            for (float t = 0f; t < pry && (held = Held(pocket)); t += Time.deltaTime)
            {
                float u = Mathf.SmoothStep(0f, 1f, t / pry);
                posePos = Vector3.Lerp(Tuning.MINE_HIT_POS, Tuning.MINE_PRY_POS, u);
                poseTilt = Mathf.Lerp(Tuning.MINE_HIT_TILT, Tuning.MINE_PRY_TILT, u);
                pocket.Pry(u);
                player.mineLean = Tuning.MINE_PRY_LEAN_DEG * u;
                yield return null;
            }
            if (held)
            {
                minePhase = "fall";
                pocket.Pop(hitDir);                                 // 광석이 빠진다 — 진행 끝
                MiningFx.I.HitSound(point, true);
                player.Shake(Tuning.SHAKE_AMOUNT, Tuning.SHAKE_TIME);
                for (float t = 0f; t < Tuning.MINE_FALL_S * T; t += Time.deltaTime)
                {
                    player.mineLean = Tuning.MINE_PRY_LEAN_DEG * (1f - t / (Tuning.MINE_FALL_S * T));
                    yield return null;
                }
                player.mineLean = 0f;
                // 날을 눕혀 몸 쪽으로 긁는다 — 떼면 바로 멈춘다(광석은 이미 빠졌다)
                minePhase = "scrape";
                float scrape = (mineCrouch ? Tuning.MINE_SCRAPE_CROUCH : Tuning.MINE_SCRAPE_STAND) * T;
                yield return ScrapeTo(Tuning.MINE_SCRAPE_POS, Tuning.MINE_SCRAPE_TILT, scrape * 0.3f);
                yield return ScrapeTo(Tuning.MINE_SCRAPE_END, Tuning.MINE_SCRAPE_TILT_END, scrape * 0.7f);
            }
        }
        if (!held && resetOnRelease && pocket != null && !pocket.Breaking) pocket.ResetProgress();
        player.mineLean = 0f;
        minePhase = "lower";
        yield return PoseTo(Tuning.PICK_POS, Tuning.PICK_TILT_DEG, Tuning.MINE_LOWER_S, EaseOut, null, 0f);
        minePhase = "";
        basePos = Tuning.PICK_POS;
        transform.localPosition = Tuning.PICK_POS;
        SetTilt(Tuning.PICK_TILT_DEG);
        player.EndMine();
        mining = null;
    }

    IEnumerator ScrapeTo(Vector3 pos, float tilt, float time)
    {
        Vector3 p0 = posePos;
        float t0 = poseTilt;
        for (float t = 0f; t < time; t += Time.deltaTime)
        {
            var mouse = Mouse.current;
            if (!hasPick || player.frozen || mouse == null || !mouse.leftButton.isPressed) yield break;
            float u = Mathf.SmoothStep(0f, 1f, t / time);
            posePos = Vector3.Lerp(p0, pos, u);
            poseTilt = Mathf.Lerp(t0, tilt, u);
            yield return null;
        }
    }

    // 콱: 광석이 깎여 조금 밀려 나오고 자갈·먼지, 소리는 작게(6 m)
    void StrikeOre(OrePocket pocket, Vector3 point, Vector3 hitDir, float dmg)
    {
        hitsLanded++;
        strikeTimes.Add(Time.time);
        pocket.TakeHit(dmg, hitDir, point);
        NoiseBus.Make(point, softNoise, "pick", player);
        MiningFx.I.HitSound(point, false);
        player.Shake(Tuning.PICK_HIT_SHAKE_AMOUNT, Tuning.PICK_HIT_SHAKE_TIME);
        Wear(Tuning.MineWearPerStrike(mineCrouch));
    }

    // 미끄러짐: 날이 벽을 긁고 튕겨 '쨍' — 진행 없음, NOISE_PICK 한 번(괴물 규칙: 한 번 = 한 칸 다가옴), 더 닳는다
    void Slip(Vector3 point)
    {
        slips++;
        minePhase = "slip";
        NoiseBus.Make(point, Tuning.NOISE_PICK, "pick_slip", player);
        MiningFx.I.PickSound(point, 1f, 1.5f);
        MiningFx.I.Chips(point, (cam.position - point).normalized);
        player.Shake(Tuning.SHAKE_AMOUNT, Tuning.SHAKE_TIME);
        posePos = Tuning.MINE_HIT_POS + new Vector3(0.10f, 0.04f, -0.05f);   // 옆으로 튕긴다
        poseTilt = Tuning.MINE_HIT_TILT - 20f;
        Wear(Tuning.MINE_WEAR_SLIP);
    }

    // ---- 괴물 (옛 빠른 휘두르기) ----
    IEnumerator Swing()
    {
        swinging = true;
        float rest = Tuning.PICK_TILT_DEG, up = rest - Tuning.PICK_WINDUP_DEG, down = rest + Tuning.PICK_SWING_DEG;
        yield return Tilt(rest, up, Tuning.PICK_WINDUP_TIME, u => Mathf.Sin(u * Mathf.PI * 0.5f));   // 뒤로 든다
        yield return Tilt(up, down, Tuning.PICK_DOWN_TIME, u => u * u);                              // 가속하며 내려친다
        Strike();
        yield return new WaitForSeconds(Tuning.PICK_HITSTOP_TIME * swingTimeMul);                  // 박힌 채 멈춤
        yield return Tilt(down, rest, Tuning.PICK_UP_TIME, u => Mathf.Sin(u * Mathf.PI * 0.5f));     // 감속하며 되돌린다
        swinging = false;
    }

    IEnumerator Tilt(float from, float to, float time, System.Func<float, float> ease)
    {
        time *= swingTimeMul;
        for (float t = 0f; t < time; t += Time.deltaTime)
        {
            SetTilt(Mathf.Lerp(from, to, ease(t / time)));
            yield return null;
        }
        SetTilt(to);
    }

    void Strike()
    {
        if (!Target(out var pocket, out var stalker, out var hit))
            return;
        if (stalker == null && !oldMining)
            return;                                                    // 광석은 묶음(Mine)으로만
        hitsLanded++;
        Wear(Tuning.PICK_WEAR_HIT);
        if (stalker != null)
        {
            stalker.Hit(Tuning.STALKER_HIT_DMG, cam.forward);
            NoiseSound.I.Flesh(hit.point);                             // 몸에 맞는 소리 — 광물 소리와 다르다
            player.Shake(Tuning.PICK_HIT_SHAKE_AMOUNT, Tuning.PICK_HIT_SHAKE_TIME);
            return;
        }
        // 사보타주 minefast: 옛 두 번 치기 (MINE-1 전)
        pocket.TakeHit(damage, cam.forward, hit.point);
        if (pocket.health <= 0f) pocket.Pop(cam.forward);
        NoiseBus.Make(hit.point, Tuning.NOISE_PICK, "pick", player);
        MiningFx.I.HitSound(hit.point, pocket.Breaking);
    }

    // 던지기: 뷰모델을 숨기고 ThrownPick 을 카메라 앞에서 던진다. 방향은 카메라 앞을 오른쪽 축으로 THROW_UP_DEG 올린 것
    void Throw()
    {
        if (thrown == null)
            return;
        if (oneOnly)
        {
            hasPick = false;
            mesh.gameObject.SetActive(false);
        }
        Wear(Tuning.PICK_WEAR_THROW);                    // 던져서 0 이 되면 주워 드는 순간(Return) 깨진다
        Vector3 dir = Quaternion.AngleAxis(-Tuning.THROW_UP_DEG, cam.right) * cam.forward;
        thrown.Launch(cam.position + cam.forward * 0.6f, dir * Tuning.THROW_SPEED, cam.right * 8f);
    }

    // ThrownPick 이 E 로 주워졌다
    public void Return()
    {
        hasPick = true;
        mesh.gameObject.SetActive(true);
        thrown.gameObject.SetActive(false);
        if (durability <= 0f) Break();
    }

    void Wear(float amount)
    {
        if (!dulls)
            return;
        durability = Mathf.Max(0f, durability - amount);
        if (durability <= Tuning.PICK_SHAKY_BELOW && shaky && hasPick)
            shakeLeft = Tuning.PICK_SHAKE_S;
        if (durability <= 1e-4f && hasPick)
        {
            durability = 0f;
            Break();
        }
    }

    // 부서진다: 뷰모델이 사라지고 그 자리에서 곡괭이 재질 조각이 튀어 바닥에 떨어졌다 사라진다. 빈손 — 주울 것 없음
    void Break()
    {
        if (!breaks)
            return;
        hasPick = false;
        shakeLeft = 0f;
        mesh.gameObject.SetActive(false);
        var renderers = mesh.GetComponentsInChildren<Renderer>(true);
        var materials = new Material[renderers.Length];
        for (int i = 0; i < renderers.Length; i++) materials[i] = renderers[i].sharedMaterial;
        MiningFx.I.Shatter(mesh.position, materials);
    }

    // DevHud 3/4 키 (상점이 생기기 전 판정용). 0 이 되면 손에서 깨지고, 깨진 뒤 올리면 손에 다시 난다
    public void Adjust(float delta)
    {
        durability = Mathf.Clamp(durability + delta, 0f, Tuning.PICK_DURABILITY_MAX);
        if (durability <= 0f && hasPick)
            Break();
        else if (durability > 0f && Broken)
        {
            hasPick = true;
            mesh.gameObject.SetActive(true);
        }
    }

    void SetTilt(float deg) => transform.localRotation = Quaternion.Euler(deg, 0f, 0f);
}
