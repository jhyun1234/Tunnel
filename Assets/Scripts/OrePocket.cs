using System.Collections;
using UnityEngine;

// 갱도 옆벽에 반쯤 박힌 광석 덩이 — 광맥 포켓. Godot OrePocket.gd.
// 곡괭이로 두 번 친다. 첫 타에 밀렸다 돌아오며 자갈이 튀고, 둘째 타에 덩이가 벽에서 빠져나와 통로 쪽으로 구른다(Ore).
// 자리는 씬 생성기(BuildM1)가 조각의 SLOT_Pocket_* 에 놓는다.
public class OrePocket : MonoBehaviour
{
    public Transform mesh;
    public Vector3 outDir;                                  // 자리에서 통로 쪽 (수평 단위 벡터)
    [System.NonSerialized] public float health = Tuning.POCKET_HEALTH;

    public bool Breaking { get; private set; }

    Vector3 rest;
    Coroutine recoil;

    void Awake() => rest = mesh.localPosition;

    // hitDir: 때린 쪽에서 포켓을 향하는 방향. hitPoint: 곡괭이가 닿은 점
    public void TakeHit(float damage, Vector3 hitDir, Vector3 hitPoint)
    {
        if (Breaking)
            return;
        health -= damage;
        if (health <= 0f)
        {
            Pop(hitDir);
            return;
        }
        MiningFx.I.Dust(hitPoint, -hitDir, Tuning.HIT_DUST);
        MiningFx.I.Chips(hitPoint, -hitDir);
        if (recoil != null)
            StopCoroutine(recoil);
        recoil = StartCoroutine(Recoil(transform.InverseTransformDirection(hitDir).normalized));
    }

    IEnumerator Recoil(Vector3 localDir)
    {
        Vector3 back = rest + localDir * Tuning.HIT_RECOIL;
        yield return Move(rest, back, Tuning.HIT_RECOIL_TIME * 0.4f);
        yield return Move(back, rest, Tuning.HIT_RECOIL_TIME * 0.6f);
    }

    IEnumerator Move(Vector3 from, Vector3 to, float time)
    {
        for (float t = 0f; t < time; t += Time.deltaTime)
        {
            mesh.localPosition = Vector3.Lerp(from, to, t / time);
            yield return null;
        }
        mesh.localPosition = to;
    }

    // 덩이가 벽에서 빠져나온다. 통로 쪽(때린 사람 쪽)으로 튀고, 위로 떠서 바닥에 구른다
    void Pop(Vector3 hitDir)
    {
        Breaking = true;
        GetComponent<Collider>().enabled = false;           // 광석이 생기기 전에 판정부터 뺀다
        Vector3 o = new Vector3(-hitDir.x, 0f, -hitDir.z).normalized;
        if (o == Vector3.zero)
            o = outDir;
        MiningFx.I.Dust(transform.position, o, Tuning.BREAK_DUST);
        Vector3 side = Vector3.Cross(o, Vector3.up) * Random.Range(-1f, 1f) * Tuning.ORE_POP_SIDE;
        MiningFx.I.SpawnOre(transform.position + o * 0.3f, o * Tuning.POCKET_POP_OUT + side + Vector3.up * Tuning.ORE_POP_UP);
        Destroy(gameObject);
    }
}
