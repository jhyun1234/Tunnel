using System.Collections;
using System.Collections.Generic;
using UnityEngine;

// 채굴 연출 한 곳: 먼지(Godot Dust.gd), 자갈(WallChunk.gd), 광석 생성(Ore.spawn).
// 에셋 참조는 씬 생성기(BuildM1)가 넣는다 — 실행 파일에 에셋이 따라 들어가게.
// 자갈과 광석은 Ignore Raycast 레이어(2)에 둔다 — 곡괭이 레이·램프 감광 레이를 막지 않게. 플레이어와는 안 부딪친다.
public class MiningFx : MonoBehaviour
{
    public static MiningFx I;

    public Player player;
    public GameObject orePrefab;
    public Mesh[] chipMeshes;
    public Material chipMaterial;
    public Material dustMaterial;

    const int IgnoreRaycastLayer = 2;
    readonly List<GameObject> chips = new List<GameObject>();

    void Awake() => I = this;

    // 한 번 터지고 스스로 사라지는 먼지. 벽에서 플레이어 쪽(facing)으로 뿜는다
    public void Dust(Vector3 at, Vector3 facing, int count)
    {
        var go = new GameObject("Dust");
        go.transform.SetPositionAndRotation(at, Quaternion.LookRotation(facing.sqrMagnitude > 0.001f ? facing : Vector3.up));
        var ps = go.AddComponent<ParticleSystem>();
        ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        var main = ps.main;
        main.duration = 0.1f;
        main.loop = false;
        main.startLifetime = 1.2f;
        main.startSpeed = new ParticleSystem.MinMaxCurve(0.8f, 2.6f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.22f * 0.4f, 0.22f);
        main.startColor = new Color(0.58f, 0.55f, 0.5f, 0.75f);
        main.gravityModifier = 2.5f / 9.81f;
        main.stopAction = ParticleSystemStopAction.Destroy;
        var emission = ps.emission;
        emission.rateOverTime = 0f;
        emission.SetBursts(new[] { new ParticleSystem.Burst(0f, (short)count) });
        var shape = ps.shape;
        shape.shapeType = ParticleSystemShapeType.Cone;
        shape.angle = 60f;
        shape.radius = 0.25f;
        var drag = ps.limitVelocityOverLifetime;
        drag.enabled = true;
        drag.drag = 2.25f;                                  // Godot damping 1.5~3
        var size = ps.sizeOverLifetime;
        size.enabled = true;
        size.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.35f), new Keyframe(0.3f, 1f), new Keyframe(1f, 0f)));
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
