using System.Collections;
using System.Collections.Generic;
using UnityEngine;

// 채굴 연출 한 곳: 먼지(Godot Dust.gd), 자갈(WallChunk.gd), 광석 생성(Ore.spawn), 타격음.
// 에셋 참조는 씬 생성기(BuildM1)가 넣는다 — 실행 파일에 에셋이 따라 들어가게.
// 자갈과 광석은 Ignore Raycast 레이어(2)에 둔다 — 곡괭이 판정·램프 감광 광선을 막지 않게. 플레이어와는 안 부딪친다.
public class MiningFx : MonoBehaviour
{
    public static MiningFx I;

    public Player player;
    public GameObject orePrefab;
    public Mesh[] chipMeshes;
    public Material chipMaterial;
    public Material dustMaterial;
    public AudioClip[] hitClips;                        // Kenney Impact Sounds impactMining_* (CC0)

    public const int IgnoreRaycastLayer = 2;
    readonly List<GameObject> chips = new List<GameObject>();

    void Awake() => I = this;

    // 한 번 터지고 스스로 사라지는 먼지 뭉게. 벽에서 플레이어 쪽(facing)으로 퍼져 나와 떠 있다가 커지며 옅어진다
    public void Dust(Vector3 at, Vector3 facing, int count)
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

    // 평타에 튀는 자갈. 짧게 살고 줄어들며 사라진다. 상한을 넘으면 오래된 것부터 지운다
    public void Chips(Vector3 hitPoint, Vector3 outDir)
    {
        for (int i = 0; i < Tuning.CHIP_PER_HIT; i++)
        {
            var go = new GameObject("Chip", typeof(MeshFilter), typeof(MeshRenderer)) { layer = IgnoreRaycastLayer };
            go.GetComponent<MeshFilter>().sharedMesh = chipMeshes[Random.Range(0, chipMeshes.Length)];
            go.GetComponent<MeshRenderer>().sharedMaterial = chipMaterial;
            go.transform.position = hitPoint + outDir * 0.1f;
            Physics.IgnoreCollision(go.AddComponent<BoxCollider>(), player.Controller);
            var rb = go.AddComponent<Rigidbody>();
            Vector3 spread = new Vector3(Random.Range(-1f, 1f), Random.Range(-0.2f, 1f), Random.Range(-1f, 1f)).normalized;
            rb.linearVelocity = (outDir + spread * 0.7f).normalized * Tuning.CHIP_POP;
            rb.angularVelocity = RandomBox() * Tuning.CHUNK_SPIN;
            chips.Add(go);
            while (chips.Count > Tuning.CHUNK_LIMIT)
            {
                if (chips[0] != null) Destroy(chips[0]);
                chips.RemoveAt(0);
            }
            StartCoroutine(FadeOut(go, Tuning.CHIP_LIFE));
        }
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

    // 곡괭이 타격음. 맞은 자리에서 나는 3D 소리 — 소음 반경(NOISE_PICK)에서 0 이 된다
    public void HitSound(Vector3 at, bool breaking)
    {
        if (hitClips == null || hitClips.Length == 0)
            return;
        var go = new GameObject("HitSound");
        go.transform.position = at;
        var src = go.AddComponent<AudioSource>();
        src.clip = hitClips[Random.Range(0, hitClips.Length)];
        src.spatialBlend = 1f;
        src.rolloffMode = AudioRolloffMode.Linear;
        src.minDistance = Tuning.HIT_MIN_DISTANCE;
        src.maxDistance = Tuning.NOISE_PICK;
        src.volume = breaking ? 1f : Tuning.HIT_VOLUME;
        src.pitch = breaking ? Tuning.HIT_BREAK_PITCH : 1f + Random.Range(-Tuning.HIT_PITCH_JITTER, Tuning.HIT_PITCH_JITTER);
        src.Play();
        Destroy(go, src.clip.length / src.pitch + 0.1f);
    }

    IEnumerator FadeOut(GameObject go, float life)
    {
        yield return new WaitForSeconds(life);
        for (float t = 0f; go != null && t < Tuning.CHUNK_FADE; t += Time.deltaTime)
        {
            go.transform.localScale = Vector3.one * (1f - t / Tuning.CHUNK_FADE);
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
