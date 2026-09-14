using System.Collections;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering;

// 화면에 들린 곡괭이(뷰모델)와 채굴. Godot Pickaxe.gd + Miner.gd.
// 좌클릭을 누르고 있는 동안, 카메라 정면 MINE_RANGE 안에 광맥 포켓이 있으면 휘두른다. 허공에는 안 휘두른다.
// 내려치기가 끝나는 순간(곡괭이 머리가 벽에 닿을 때) 다시 쏴서 맞은 것을 친다 — 휘두르는 사이 시점이 돌았을 수 있다.
// 휘두르기는 코드로 각도를 흔든다(리깅 애니메이션 아님). 충돌 없는 그림이라 벽을 뚫고 보일 수 있다.
public class Pickaxe : MonoBehaviour
{
    public Transform cam;
    public Player player;
    public Transform mesh;
    // 검사가 실행 중에 바꾼다. 값은 Tuning 한 곳
    [System.NonSerialized] public float damage = Tuning.MINE_DAMAGE;
    [System.NonSerialized] public float cooldownTime = Tuning.MINE_COOLDOWN;
    [System.NonSerialized] public float swingTimeMul = 1f;

    float cooldown, bob;
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
        if (cooldown <= 0f && !swinging && mouse != null && mouse.leftButton.isPressed && Target(out _, out _))
        {
            cooldown = cooldownTime;
            StartCoroutine(Swing());
        }
        if (swinging)
            return;
        // 걸을 때만 흔들린다. 서 있으면 멎는다
        if (player.Speed < 0.2f)
        {
            bob = 0f;
            transform.localPosition = Vector3.Lerp(transform.localPosition, Tuning.PICK_POS, Mathf.Min(Time.deltaTime * 8f, 1f));
        }
        else
        {
            bob += Time.deltaTime * Tuning.PICK_BOB_SPEED;
            transform.localPosition = Tuning.PICK_POS + new Vector3(Mathf.Cos(bob), Mathf.Abs(Mathf.Sin(bob)), 0f) * Tuning.PICK_BOB_AMOUNT;
        }
    }

    public bool HasTarget => Target(out _, out _);   // 검사가 읽는다

    // 레이 위 가장 가까운 포켓. 벽 충돌체는 무시한다 — Godot MineRay 가 포켓 레이어만 봤다(mask 4).
    // 포켓 앞면은 벽 충돌 상자보다 몇 cm 만 나와 있어서, 벽에 막히게 두면 포켓 가운데 아래를 조준했을 때 안 맞았다(09-14 검사)
    static readonly RaycastHit[] Hits = new RaycastHit[16];

    bool Target(out OrePocket pocket, out RaycastHit hit)
    {
        pocket = null;
        hit = default;
        int n = Physics.RaycastNonAlloc(cam.position, cam.forward, Hits, Tuning.MINE_RANGE, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Ignore);
        for (int i = 0; i < n; i++)
        {
            var candidate = Hits[i].collider.GetComponent<OrePocket>();
            if (candidate != null && !candidate.Breaking && (pocket == null || Hits[i].distance < hit.distance))
            {
                pocket = candidate;
                hit = Hits[i];
            }
        }
        return pocket != null;
    }

    IEnumerator Swing()
    {
        swinging = true;
        float rest = Tuning.PICK_TILT_DEG, down = rest + Tuning.PICK_SWING_DEG;
        float time = Tuning.PICK_DOWN_TIME * swingTimeMul;
        for (float t = 0f; t < time; t += Time.deltaTime)
        {
            float u = t / time;
            SetTilt(Mathf.Lerp(rest, down, u * u));                          // 가속하며 내려친다
            yield return null;
        }
        SetTilt(down);
        Strike();
        time = Tuning.PICK_UP_TIME * swingTimeMul;
        for (float t = 0f; t < time; t += Time.deltaTime)
        {
            SetTilt(Mathf.Lerp(down, rest, Mathf.Sin(t / time * Mathf.PI * 0.5f)));   // 감속하며 되돌린다
            yield return null;
        }
        SetTilt(rest);
        swinging = false;
    }

    void Strike()
    {
        if (!Target(out var pocket, out var hit))
            return;
        pocket.TakeHit(damage, cam.forward, hit.point);
        NoiseBus.Make(hit.point, Tuning.NOISE_PICK, "pick", player);   // 포켓에 닿은 타격만 소음. 허공은 위에서 걸러진다
        if (pocket.Breaking)
            player.Shake(Tuning.SHAKE_AMOUNT, Tuning.SHAKE_TIME);      // 덩이가 빠질 때만 — 평타마다 흔들면 빠지는 순간이 안 특별해진다
    }

    void SetTilt(float deg) => transform.localRotation = Quaternion.Euler(deg, 0f, 0f);
}
