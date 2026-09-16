using UnityEngine;
using UnityEngine.InputSystem;

// 던져진 곡괭이 (M6, Godot ThrownPick.gd). 씬에 하나만 있고 Pickaxe.Throw 가 켜고 Return 이 끈다 — 곡괭이는 하나뿐.
// 첫 충돌에서 큰 소음(NOISE_PICK_LAND) 한 번 = 유인 (소리도 그 소음에서 난다, NoiseSound). 착지 뒤 THROW_STUCK_S 지나면 얼린다(틈에 끼지 않게).
// 괴물에 닿으면 휘두른 한 대와 같다(Stalker.Hit) 하고 그 자리에 떨어진다. CARRY_REACH 안에서 E → Pickaxe.Return.
// 레이어는 광석과 같은 Ignore Raycast — 시선·채굴 조준 구에 안 걸린다. 플레이어 몸과는 안 부딪힌다.
// 충돌체는 곡괭이 모양대로 상자 3개(자루·목·머리, BuildM1) — 공 하나였을 땐 공만 바닥에 닿아 머리가 바닥을 뚫었다(사용자 09-16).
// UI-1c: 착지 뒤 플레이어가 reach 안에 오면 머리(PICK_Head)가 Unlit 빛남 재질로 바뀐다 — "빛나면 주울 수 있다", 글자 대신.
[RequireComponent(typeof(Rigidbody))]
public class ThrownPick : MonoBehaviour
{
    public Pickaxe pickaxe;
    public Player player;
    public Renderer head;                                  // PICK_Head (BuildM1 이 넣는다)
    public Material glowMaterial;                          // M7_PickGlow.mat (Unlit)
    [System.NonSerialized] public float reach = Tuning.CARRY_REACH;   // 검사 사보타주가 바꾼다
    [System.NonSerialized] public bool glows = true;       // 사보타주 noglow 가 끈다
    [System.NonSerialized] public float glow = Tuning.PICK_GLOW;   // 빛 세기 — 사용자가 DevHud 7/8(임시) 로 찾는다
    public bool Glowing => head != null && head.sharedMaterial == glowMaterial;
    Material headMaterial;                                 // 원래 재질

    // 검사용: 메시 전체의 가장 낮은/높은 점 (바닥에 누웠는지)
    public Bounds MeshBounds
    {
        get
        {
            var rs = GetComponentsInChildren<Renderer>();
            Bounds b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            return b;
        }
    }
    [System.NonSerialized] public bool landed;
    [System.NonSerialized] public Vector3 landPos;
    [System.NonSerialized] public string landedOn = "-";   // 검사용: 처음 닿은 충돌체

    Rigidbody rb;
    float age, landAge;
    bool hitBody;                                          // 괴물 몸에 맞고 떨어졌다 — 착지음은 안 낸다(몸에 맞는 소리가 묻힌다, 사용자 09-16)

    public bool Frozen => rb.isKinematic;                   // 착지 뒤 THROW_STUCK_S 지나 멈췄다 (검사가 기다린다)

    void Awake()
    {
        rb = GetComponent<Rigidbody>();
        rb.mass = 2f;
        rb.linearDamping = 1f;
        rb.angularDamping = 4f;
        rb.collisionDetectionMode = CollisionDetectionMode.Continuous;
        rb.interpolation = RigidbodyInterpolation.None;      // Interpolate 면 첫 Launch 의 transform.position 을 이전(원점) 자세로 되돌려 원점 바닥에 '착지'했다 (09-15)
        if (head != null) headMaterial = head.sharedMaterial;
    }

    void OnDisable()
    {
        if (head != null && headMaterial != null) head.sharedMaterial = headMaterial;
    }

    public void Launch(Vector3 at, Vector3 velocity, Vector3 spin)
    {
        gameObject.SetActive(true);
        foreach (var col in GetComponentsInChildren<Collider>())
            Physics.IgnoreCollision(col, player.Controller);   // 끄면 풀린다 — 켤 때마다 다시
        rb.isKinematic = false;
        transform.position = at;
        rb.position = at;
        rb.linearVelocity = velocity;
        rb.angularVelocity = spin;
        landed = false;
        hitBody = false;
        landedOn = "-";
        age = landAge = 0f;
    }

    void OnCollisionEnter(Collision c)
    {
        if (landed)
            return;                                            // 바닥에 놓인 곡괭이를 괴물이 밟아도 맞은 게 아니다
        var stalker = c.collider.GetComponent<Stalker>();
        if (stalker != null)                                   // 날아가다 괴물에 닿음: 한 대와 같다. 튀지 않고 그 자리에 떨어진다
        {
            stalker.Hit(Tuning.STALKER_HIT_DMG, rb.linearVelocity.normalized);
            NoiseSound.I.Flesh(transform.position);
            hitBody = true;
            rb.linearVelocity = Vector3.zero;
            rb.angularVelocity = Vector3.zero;
        }
        landedOn = $"{c.collider.name} y{transform.position.y:F2} age{age:F2}";
        Land();                                                // 착지음은 NoiseSound 가 pick_land 소음에 붙여 튼다
    }

    void Land()
    {
        landed = true;
        landPos = transform.position;
        Debug.Log($"THROWN landed {landPos} on {landedOn}");
        NoiseBus.Make(landPos, Tuning.NOISE_PICK_LAND, hitBody ? "pick_land_body" : "pick_land", player);   // _body 는 NoiseSound 가 소리를 안 낸다 (괴물은 이미 맞아서 소음을 안 듣는다)
    }

    void Update()
    {
        float dt = Time.deltaTime;
        age += dt;
        if (landed)
        {
            landAge += dt;
            if (landAge >= Tuning.THROW_STUCK_S && !rb.isKinematic)
                rb.isKinematic = true;                         // 더 안 구른다
            if (transform.position.y < landPos.y - 2f)         // 바닥 아래로 빠졌다 — 착지점으로
            {
                rb.isKinematic = true;
                transform.position = landPos;
            }
        }
        else if (age > Tuning.THROW_STUCK_S * 2f)              // 아무 데도 안 닿았다(허공) — 그 자리에 세운다
        {
            Land();
            rb.isKinematic = true;
        }
        if (player == null)
            return;
        bool near = Vector3.Distance(transform.position, player.transform.position + Vector3.up * Tuning.EYE_HEIGHT * 0.5f) <= reach;
        if (head != null && headMaterial != null && glowMaterial != null)
        {
            head.sharedMaterial = landed && near && glows ? glowMaterial : headMaterial;
            glowMaterial.color = Tuning.PICK_GLOW_COLOR * glow;
        }
        var kb = Keyboard.current;
        if (kb == null || !kb.eKey.wasPressedThisFrame || player.frozen)
            return;
        if (near)
            pickaxe.Return();
    }
}
