using System.Collections;
using System.Collections.Generic;
using UnityEngine;

// 채굴 연출 한 곳: 먼지(Godot Dust.gd), 자갈(WallChunk.gd), 광석 생성(Ore.spawn), 타격음, 부서진 곡괭이 조각(UI-1a).
// 에셋 참조는 씬 생성기(BuildM1)가 넣는다 — 실행 파일에 에셋이 따라 들어가게.
// 자갈과 광석은 Ignore Raycast 레이어(2)에 둔다 — 곡괭이 판정·램프 감광 광선을 막지 않게. 플레이어와는 안 부딪친다.
public class MiningFx : MonoBehaviour
{
    public static MiningFx I;

    public Player player;
    public GameObject orePrefab;
    public Mesh[] chipMeshes;                           // 옛 바위 조각 (사보타주 olddust)
    public Material chipMaterial;                       // 옛 바위 재질 — 석탄 앞에서 베이지 종잇조각처럼 보였다 (사보타주 olddust · whitechips)
    public Mesh coalMesh;                               // DUST-1: 광질 조각 = ORE-1 모난 탄 덩이(ore_lump) 그물을 줄여서
    public Material coalMaterial;
    public Material dustMaterial;
    public AudioClip[] hitClips;                        // 평소 콱 · 덩이 빠짐: 섞기 B pick_hit_* (SND-P, Assets/Audio/PickHit/SOURCES.txt)
    public AudioClip[] slipClips;                       // 미끄러질 조짐 딸각 · 미끄러짐 쨍: Kenney Impact Sounds impactMining_* (CC0, Assets/Audio/PickSlip)
    [System.NonSerialized] public float hitVolume = Tuning.HIT_VOLUME;   // 판정 키 Shift+[ Shift+] (DevHud)
    [System.NonSerialized] public float hitDistance = Tuning.MINE_NOISE_SOFT;   // 콱이 들리는 거리 · 사보타주 farhit (옛 25 m)

    [System.NonSerialized] public float dustMul = Tuning.DUST_MUL;   // 판정 키 Shift+9 Shift+0
    [System.NonSerialized] public bool oldDust;         // 사보타주 olddust — DUST-1 전 (빛나는 둥근 먼지 · 베이지 조각)
    [System.NonSerialized] public bool whiteChips;      // 사보타주 whitechips — 조각만 옛 재질
    [System.NonSerialized] public ParticleSystem lastPuff, lastStream, lastMotes;   // 검사가 읽는다
    public List<GameObject> LiveChips => chips;         // 검사가 읽는다

    public const int IgnoreRaycastLayer = 2;
    readonly List<GameObject> chips = new List<GameObject>();

    void Awake() => I = this;

    // DUST-1 광질 가루 — 날 끝 뿜기 · 벽 타고 흘러내림 · 램프 빛 속 알갱이. amount: 콱 1 · 덩이 빠짐 DUST_BREAK · 미끄러짐 DUST_SLIP
    public void Dust(Vector3 at, Vector3 facing, float amount)
    {
        if (oldDust) { OldDust(at, facing, amount >= 1.5f ? Tuning.BREAK_DUST : Tuning.HIT_DUST); return; }
        float k = amount * dustMul, s = Mathf.Clamp(Mathf.Sqrt(amount), 0.6f, 1.6f);
        Vector3 f = facing.sqrMagnitude > 0.001f ? facing.normalized : Vector3.up;

        // 날 끝 뿜기: 10~25 cm 회색 가루가 벽에서 튀어나와 금방 멎고, 가라앉으며 0.3~0.6 s 에 옅어진다
        var puff = NewBurst("DustPuff", at, Quaternion.LookRotation(f), Mathf.RoundToInt(Tuning.PUFF_COUNT * k));
        var pm = puff.main;
        pm.startLifetime = new ParticleSystem.MinMaxCurve(Tuning.PUFF_LIFE_MIN * s, Tuning.PUFF_LIFE_MAX * s);
        pm.startSpeed = new ParticleSystem.MinMaxCurve(Tuning.PUFF_SPEED_MIN, Tuning.PUFF_SPEED_MAX);
        pm.startSize = new ParticleSystem.MinMaxCurve(Tuning.PUFF_SIZE_MIN * s, Tuning.PUFF_SIZE_MAX * s);
        pm.startColor = Tuning.PUFF_COLOR;
        pm.gravityModifier = Tuning.PUFF_GRAVITY;
        var ps = puff.shape; ps.shapeType = ParticleSystemShapeType.Cone; ps.angle = 50f; ps.radius = 0.03f;
        var pd = puff.limitVelocityOverLifetime; pd.enabled = true; pd.drag = Tuning.PUFF_DRAG;
        var pz = puff.sizeOverLifetime; pz.enabled = true; pz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, 1f / Tuning.PUFF_GROW, 1f, 1f));
        Fade(puff, 0.1f);
        puff.Play();
        lastPuff = puff;
        var haze = NewBurst("DustHaze", at + f * 0.08f, Quaternion.LookRotation(f), Mathf.RoundToInt(Tuning.HAZE_COUNT * Mathf.Max(1f, k)));   // 아주 옅은 막
        var hm = haze.main;
        hm.startLifetime = new ParticleSystem.MinMaxCurve(Tuning.PUFF_LIFE_MIN * s * 1.2f, Tuning.PUFF_LIFE_MAX * s * 1.2f);
        hm.startSpeed = new ParticleSystem.MinMaxCurve(0.2f, 0.5f);
        hm.startSize = new ParticleSystem.MinMaxCurve(Tuning.HAZE_SIZE_MIN * s, Tuning.HAZE_SIZE_MAX * s);
        hm.startColor = Tuning.HAZE_COLOR;
        hm.gravityModifier = Tuning.PUFF_GRAVITY;
        var hs = haze.shape; hs.shapeType = ParticleSystemShapeType.Cone; hs.angle = 30f; hs.radius = 0.03f;
        var hd = haze.limitVelocityOverLifetime; hd.enabled = true; hd.drag = Tuning.PUFF_DRAG;
        Fade(haze, 0.15f);
        haze.Play();

        // 흘러내림: 가는 줄 알갱이가 벽을 타고 아래로 (늘인 입자)
        var stream = NewBurst("DustStream", at + f * 0.03f, Quaternion.identity, Mathf.RoundToInt(Tuning.STREAM_COUNT * k));
        var sm = stream.main;
        sm.startLifetime = new ParticleSystem.MinMaxCurve(Tuning.STREAM_LIFE_MIN, Tuning.STREAM_LIFE_MAX);
        sm.startSpeed = 0f;
        sm.startSize = new ParticleSystem.MinMaxCurve(Tuning.STREAM_SIZE_MIN, Tuning.STREAM_SIZE_MAX);
        sm.startColor = Tuning.STREAM_COLOR;
        sm.gravityModifier = Tuning.STREAM_GRAVITY;
        var ss = stream.shape; ss.shapeType = ParticleSystemShapeType.Sphere; ss.radius = 0.06f * s;
        var sv = stream.velocityOverLifetime; sv.enabled = true; sv.space = ParticleSystemSimulationSpace.World;
        sv.x = new ParticleSystem.MinMaxCurve(f.x * 0.05f, f.x * 0.15f); sv.z = new ParticleSystem.MinMaxCurve(f.z * 0.05f, f.z * 0.15f);
        sv.y = new ParticleSystem.MinMaxCurve(-Tuning.STREAM_SPEED_MAX, -Tuning.STREAM_SPEED_MIN);
        var sr = stream.GetComponent<ParticleSystemRenderer>(); sr.renderMode = ParticleSystemRenderMode.Stretch; sr.velocityScale = 0f; sr.lengthScale = Tuning.STREAM_LENGTH;
        Fade(stream, 0.05f);
        stream.Play();
        lastStream = stream;

        // 램프 빛 속 알갱이: 친 자리 둘레에 가는 점이 천천히 떨어진다 (여러 번 치면 모인다)
        var motes = NewBurst("DustMotes", at + f * 0.15f, Quaternion.identity, Mathf.RoundToInt(Tuning.MOTE_COUNT * k));
        var mm = motes.main;
        mm.startLifetime = new ParticleSystem.MinMaxCurve(Tuning.MOTE_LIFE_MIN, Tuning.MOTE_LIFE_MAX);
        mm.startSpeed = new ParticleSystem.MinMaxCurve(Tuning.MOTE_SPEED_MIN, Tuning.MOTE_SPEED_MAX);
        mm.startSize = new ParticleSystem.MinMaxCurve(Tuning.MOTE_SIZE_MIN, Tuning.MOTE_SIZE_MAX);
        mm.startColor = Tuning.MOTE_COLOR;
        mm.gravityModifier = Tuning.MOTE_GRAVITY;
        var ms = motes.shape; ms.shapeType = ParticleSystemShapeType.Sphere; ms.radius = Tuning.MOTE_RADIUS * s;
        var md = motes.limitVelocityOverLifetime; md.enabled = true; md.drag = 1.0f;
        Fade(motes, 0.2f);
        motes.Play();
        lastMotes = motes;
    }

    // 한 번 터지고 스스로 사라지는 입자 (가루 셋이 같이 쓴다)
    ParticleSystem NewBurst(string name, Vector3 at, Quaternion rot, int count)
    {
        var go = new GameObject(name);
        go.transform.SetPositionAndRotation(at, rot);
        var ps = go.AddComponent<ParticleSystem>();
        ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        var main = ps.main;
        main.duration = 0.1f;
        main.loop = false;
        main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
        main.stopAction = ParticleSystemStopAction.Destroy;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        var emission = ps.emission;
        emission.rateOverTime = 0f;
        emission.SetBursts(new[] { new ParticleSystem.Burst(0f, (short)Mathf.Max(1, count)) });
        go.GetComponent<ParticleSystemRenderer>().sharedMaterial = dustMaterial;
        return ps;
    }

    // 금방 짙어졌다가(fadeIn, 수명 비율) 끝까지 옅어진다
    static void Fade(ParticleSystem ps, float fadeIn)
    {
        var color = ps.colorOverLifetime;
        color.enabled = true;
        var gradient = new Gradient();
        gradient.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                         new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, fadeIn), new GradientAlphaKey(0f, 1f) });
        color.color = gradient;
    }

    // (옛 — DUST-1 전, 사보타주 olddust) 한 번 터지고 스스로 사라지는 먼지 뭉게. 벽에서 플레이어 쪽(facing)으로 퍼져 나와 떠 있다가 커지며 옅어진다
    void OldDust(Vector3 at, Vector3 facing, int count)
    {
        var go = new GameObject("Dust");
        go.transform.SetPositionAndRotation(at, Quaternion.LookRotation(facing.sqrMagnitude > 0.001f ? facing : Vector3.up));
        var ps = go.AddComponent<ParticleSystem>();
        ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        var main = ps.main;
        main.duration = 0.1f;
        main.loop = false;
        main.startLifetime = new ParticleSystem.MinMaxCurve(Tuning.DUST_LIFE_MIN, Tuning.DUST_LIFE_MAX);
        main.startSpeed = new ParticleSystem.MinMaxCurve(Tuning.DUST_SPEED_MIN, Tuning.DUST_SPEED_MAX);
        main.startSize = new ParticleSystem.MinMaxCurve(Tuning.DUST_SIZE_MIN, Tuning.DUST_SIZE_MAX);
        main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
        main.startColor = Tuning.DUST_COLOR;
        main.gravityModifier = Tuning.DUST_GRAVITY;
        main.stopAction = ParticleSystemStopAction.Destroy;
        var emission = ps.emission;
        emission.rateOverTime = 0f;
        emission.SetBursts(new[] { new ParticleSystem.Burst(0f, (short)count) });
        var shape = ps.shape;
        shape.shapeType = ParticleSystemShapeType.Cone;
        shape.angle = 45f;
        shape.radius = 0.15f;
        var drag = ps.limitVelocityOverLifetime;
        drag.enabled = true;
        drag.drag = Tuning.DUST_DRAG;
        var size = ps.sizeOverLifetime;
        size.enabled = true;
        size.size = new ParticleSystem.MinMaxCurve(Tuning.DUST_GROW, AnimationCurve.EaseInOut(0f, 1f / Tuning.DUST_GROW, 1f, 1f));
        var color = ps.colorOverLifetime;                  // 금방 짙어졌다가 천천히 옅어진다
        color.enabled = true;
        var gradient = new Gradient();
        gradient.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                         new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.15f), new GradientAlphaKey(0f, 1f) });
        color.color = gradient;
        go.GetComponent<ParticleSystemRenderer>().sharedMaterial = dustMaterial;
        ps.Play();
    }

    // DUST-1 석탄 조각: 모난 탄 덩이를 2~6 cm 로 줄여 여럿(가끔 주먹만 한 것 하나) — 밖으로 조금 튀었다 곧 떨어져 바닥에 누워 있다 DEBRIS_LIFE 뒤 줄어들며 사라진다.
    // 상한(CHUNK_LIMIT)을 넘으면 오래된 것부터 지운다
    public void Chips(Vector3 hitPoint, Vector3 outDir, int count)
    {
        if (oldDust)
        {
            for (int i = 0; i < Tuning.CHIP_PER_HIT; i++)
            {
                Vector3 spread = new Vector3(Random.Range(-1f, 1f), Random.Range(-0.2f, 1f), Random.Range(-1f, 1f)).normalized;
                Chip("Chip", hitPoint + outDir * 0.1f, (outDir + spread * 0.7f).normalized * Tuning.CHIP_POP, chipMaterial, Tuning.CHIP_LIFE, Vector3.one);
            }
            return;
        }
        float meshSize = coalMesh != null ? coalMesh.bounds.size.magnitude / 1.732f : 0.2f;   // 그물의 평균 폭 (ore_lump ≈ 0.18 m)
        for (int i = 0; i < count; i++)
        {
            float size = i == 0 && Random.value < Tuning.DEBRIS_BIG_CHANCE ? Tuning.DEBRIS_BIG : Random.Range(Tuning.DEBRIS_SIZE_MIN, Tuning.DEBRIS_SIZE_MAX);
            Vector3 scale = new Vector3(Random.Range(0.7f, 1.3f), Random.Range(0.7f, 1.3f), Random.Range(0.7f, 1.3f)) * (size / meshSize);
            Vector3 v = outDir * Random.Range(Tuning.DEBRIS_POP_MIN, Tuning.DEBRIS_POP_MAX) + Random.insideUnitSphere * 0.4f + Vector3.up * Random.Range(0f, 0.4f);
            Chip("Chip", hitPoint + outDir * 0.05f + Random.insideUnitSphere * 0.03f, v, whiteChips ? chipMaterial : coalMaterial, Tuning.DEBRIS_LIFE, scale, coalMesh);
        }
    }

    // 곡괭이가 부서진다 (UI-1a): 손 자리에서 곡괭이 재질 조각이 튀어 바닥에 떨어지고 PICK_BREAK_LIFE 뒤 줄어들며 사라진다. 자갈과 같은 물체
    public void Shatter(Vector3 at, Material[] materials)
    {
        for (int i = 0; i < Tuning.PICK_BREAK_PIECES; i++)
            Chip("PickPiece", at, (RandomBox() + Vector3.up * 0.5f).normalized * Tuning.PICK_BREAK_POP, materials[Random.Range(0, materials.Length)], Tuning.PICK_BREAK_LIFE, Vector3.one * Tuning.PICK_BREAK_SCALE);
    }

    public int PiecesAlive => chips.FindAll(g => g != null && g.name == "PickPiece").Count;   // 검사가 센다

    void Chip(string name, Vector3 at, Vector3 velocity, Material material, float life, Vector3 scale, Mesh mesh = null)
    {
        var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer)) { layer = IgnoreRaycastLayer };
        go.transform.localScale = scale;
        go.transform.rotation = Random.rotation;
        go.GetComponent<MeshFilter>().sharedMesh = mesh != null ? mesh : chipMeshes[Random.Range(0, chipMeshes.Length)];
        go.GetComponent<MeshRenderer>().sharedMaterial = material;
        go.transform.position = at;
        Physics.IgnoreCollision(go.AddComponent<BoxCollider>(), player.Controller);
        var rb = go.AddComponent<Rigidbody>();
        rb.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;   // 2 cm 조각이 바닥을 뚫지 않게
        rb.linearVelocity = velocity;
        rb.angularVelocity = RandomBox() * Tuning.CHUNK_SPIN;
        chips.Add(go);
        while (chips.Count > Tuning.CHUNK_LIMIT)
        {
            if (chips[0] != null) Destroy(chips[0]);
            chips.RemoveAt(0);
        }
        StartCoroutine(FadeOut(go, life));
    }

    public void SpawnOre(Vector3 at, Vector3 velocity)
    {
        var go = Instantiate(orePrefab, at, Random.rotation);
        go.name = "Ore";
        go.layer = IgnoreRaycastLayer;
        var col = go.AddComponent<SphereCollider>();
        col.radius = Tuning.ORE_RADIUS;
        Physics.IgnoreCollision(col, player.Controller);
        var rb = go.AddComponent<Rigidbody>();
        rb.interpolation = RigidbodyInterpolation.Interpolate;
        rb.linearVelocity = velocity;
        rb.angularDamping = Tuning.ORE_ROLL_DAMP;
        rb.linearDamping = Tuning.ORE_ROLL_DAMP * 0.25f;
        rb.angularVelocity = RandomBox() * Tuning.ORE_SPIN;
        var ore = go.AddComponent<Ore>();
        ore.player = player;
        ore.spawnPos = at;
    }

    // 곡괭이 타격음(평소 콱 · 덩이 빠짐). 맞은 자리에서 나는 3D 소리 — 괴물이 듣는 거리(MINE_NOISE_SOFT 6 m)에서 0 이 된다
    public void HitSound(Vector3 at, bool breaking) =>
        Play(hitClips, at, breaking ? 1f : hitVolume, breaking ? Tuning.HIT_BREAK_PITCH : 1f + Random.Range(-Tuning.HIT_PITCH_JITTER, Tuning.HIT_PITCH_JITTER), hitDistance);

    // MINE-1 미끄러질 조짐(작고 높게 딸각) · 미끄러짐 '쨍'(크고 높게) — Kenney 소리를 크기·높이만 바꿔 튼다. NOISE_PICK(25 m)에서 0
    public void SlipSound(Vector3 at, float volume, float pitch) => Play(slipClips, at, volume, pitch, Tuning.NOISE_PICK);

    void Play(AudioClip[] clips, Vector3 at, float volume, float pitch, float maxDistance)
    {
        if (clips == null || clips.Length == 0)
            return;
        var go = new GameObject("HitSound");
        go.transform.position = at;
        var src = go.AddComponent<AudioSource>();
        src.clip = clips[Random.Range(0, clips.Length)];
        src.spatialBlend = 1f;
        src.rolloffMode = AudioRolloffMode.Linear;
        src.minDistance = Tuning.HIT_MIN_DISTANCE;
        src.maxDistance = maxDistance;
        src.volume = volume;
        src.pitch = pitch;
        src.Play();
        Destroy(go, src.clip.length / src.pitch + 0.1f);
    }

    IEnumerator FadeOut(GameObject go, float life)
    {
        yield return new WaitForSeconds(life);
        Vector3 full = go != null ? go.transform.localScale : Vector3.one;
        for (float t = 0f; go != null && t < Tuning.CHUNK_FADE; t += Time.deltaTime)
        {
            go.transform.localScale = full * (1f - t / Tuning.CHUNK_FADE);
            yield return null;
        }
        if (go != null)
        {
            chips.Remove(go);
            Destroy(go);
        }
    }

    static Vector3 RandomBox() => new Vector3(Random.Range(-1f, 1f), Random.Range(-1f, 1f), Random.Range(-1f, 1f));
}
