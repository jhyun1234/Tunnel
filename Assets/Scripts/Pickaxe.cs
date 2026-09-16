using System.Collections;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

// 화면에 들린 곡괭이(뷰모델)와 채굴. Godot Pickaxe.gd + Miner.gd.
// 좌클릭을 누르고 있는 동안, 카메라 정면 MINE_RANGE 안에 광맥 포켓이나 괴물이 있으면 휘두른다. 허공에는 안 휘두른다.
// 휘두르기: 뒤로 들기 → 내려치기 → 끝나는 순간 다시 쏴서 맞은 것을 친다(휘두르는 사이 시점이 돌았을 수 있다) → 박힌 채 잠깐 멈춤 → 되돌리기.
// 곡괭이는 ViewModel 레이어라 오버레이 카메라가 그린다(벽 속으로 들어가도 벽 위에 보인다). 헤드램프는 안 비추고 PickLight 만 비춘다.
// 우클릭 = 던지기 (M6). 곡괭이는 하나뿐 — 던지면 hasPick 이 false 라 못 캐고, ThrownPick 옆에서 E 로 주워야(Return) 다시 캔다.
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
    [System.NonSerialized] public float damage = Tuning.MINE_DAMAGE;
    [System.NonSerialized] public float cooldownTime = Tuning.MINE_COOLDOWN;
    [System.NonSerialized] public float swingTimeMul = 1f;
    [System.NonSerialized] public float aimRadius = Tuning.PICK_AIM_RADIUS;
    [System.NonSerialized] public bool oneOnly = true;   // 사보타주 twopicks 가 끈다 — 던져도 손에 남는 상태
    [System.NonSerialized] public bool hasPick = true;

    static readonly RaycastHit[] Hits = new RaycastHit[16];
    float cooldown;
    bool swinging;

    void Awake()
    {
        transform.localPosition = Tuning.PICK_POS;
        SetTilt(Tuning.PICK_TILT_DEG);
        // "드는 자세"는 mesh 에, "휘두르기"는 이 노드에 — 한 곳에 섞으면 자세를 만질 때 스윙 축이 같이 틀어진다
        mesh.localScale = Vector3.one * Tuning.PICK_SCALE;
        mesh.localRotation = Quaternion.AngleAxis(Tuning.PICK_ROLL_DEG, Vector3.right) * Quaternion.AngleAxis(Tuning.PICK_YAW_DEG, Vector3.up);
        foreach (var r in mesh.GetComponentsInChildren<Renderer>())
            r.shadowCastingMode = ShadowCastingMode.Off;   // 등과 같은 자리라 그림자가 화면을 덮는다
    }

    void Update()
    {
        cooldown = Mathf.Max(0f, cooldown - Time.deltaTime);
        var mouse = Mouse.current;
        if (!swinging && hasPick && mouse != null && mouse.rightButton.wasPressedThisFrame && !player.frozen)
        {
            Throw();
            return;
        }
        if (cooldown <= 0f && !swinging && hasPick && mouse != null && mouse.leftButton.isPressed && Target(out _, out _, out _))
        {
            cooldown = cooldownTime;
            StartCoroutine(Swing());
        }
        if (swinging || !hasPick)
            return;
        // 걸을 때만 흔들린다. 서 있으면 멎는다. 위상은 Player.gait — 발이 땅에 닿는 순간(π 마다) 곡괭이가 맨 아래를 지난다 = 발소리와 같은 때
        if (player.gait <= 0f)
            transform.localPosition = Vector3.Lerp(transform.localPosition, Tuning.PICK_POS, Mathf.Min(Time.deltaTime * 8f, 1f));
        else
            transform.localPosition = Tuning.PICK_POS + new Vector3(Mathf.Cos(player.gait), Mathf.Abs(Mathf.Sin(player.gait)), 0f) * Tuning.PICK_BOB_AMOUNT;
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
        if (stalker != null)
        {
            stalker.Hit(Tuning.STALKER_HIT_DMG, cam.forward);
            NoiseSound.I.Flesh(hit.point);                             // 몸에 맞는 소리 — 광물 소리와 다르다
            player.Shake(Tuning.PICK_HIT_SHAKE_AMOUNT, Tuning.PICK_HIT_SHAKE_TIME);
            return;
        }
        pocket.TakeHit(damage, cam.forward, hit.point);
        NoiseBus.Make(hit.point, Tuning.NOISE_PICK, "pick", player);   // 포켓에 닿은 타격만 소음. 허공은 위에서 걸러진다
        MiningFx.I.HitSound(hit.point, pocket.Breaking);
        if (pocket.Breaking)
            player.Shake(Tuning.SHAKE_AMOUNT, Tuning.SHAKE_TIME);      // 덩이가 빠질 때 크게
        else
            player.Shake(Tuning.PICK_HIT_SHAKE_AMOUNT, Tuning.PICK_HIT_SHAKE_TIME);
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
        Vector3 dir = Quaternion.AngleAxis(-Tuning.THROW_UP_DEG, cam.right) * cam.forward;
        thrown.Launch(cam.position + cam.forward * 0.6f, dir * Tuning.THROW_SPEED, cam.right * 8f);
    }

    // ThrownPick 이 E 로 주워졌다
    public void Return()
    {
        hasPick = true;
        mesh.gameObject.SetActive(true);
        thrown.gameObject.SetActive(false);
    }

    void SetTilt(float deg) => transform.localRotation = Quaternion.Euler(deg, 0f, 0f);
}
