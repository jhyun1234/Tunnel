using System.Collections;
using UnityEngine;

// 갱도 옆벽에 반쯤 박힌 광석 덩이 — 광맥 포켓. Godot OrePocket.gd.
// MINE-1(09-27): 곡괭이 한 묶음(Pickaxe.Mine)으로 캔다. 콱마다 체력이 깎이며 벽에서 조금씩 밀려 나오고(진행 — 되돌아가지 않는다),
// 체력이 다 되면 박힌 채 비트는 동안 기울다가(Pry) 빠져 통로 쪽으로 구른다(Pop → Ore). 손을 떼도 체력(진행)은 남는다.
// 자리는 씬 생성기(BuildM1)가 조각의 SLOT_Pocket_* 에 놓는다.
public class OrePocket : MonoBehaviour
{
    public Transform mesh;
    public Vector3 outDir;                                  // 자리에서 통로 쪽 (수평 단위 벡터)
    [System.NonSerialized] public float health = Tuning.POCKET_HEALTH;

    public bool Breaking { get; private set; }
    public float Loosened => 1f - Mathf.Clamp01(health / Tuning.POCKET_HEALTH);   // 0 → 1, 밀려 나온 정도

    Vector3 rest;
    Quaternion restRot;
    Coroutine recoil;

    void Awake() { rest = mesh.localPosition; restRot = mesh.localRotation; }

    Vector3 Slid => rest + transform.InverseTransformDirection(outDir).normalized * Tuning.MINE_POCKET_SLIDE_M * Loosened;

    // 콱 하나. hitDir: 때린 쪽에서 포켓을 향하는 방향. hitPoint: 곡괭이가 닿은 점. 빠지는 것은 Pry → Pop 이 한다
    public void TakeHit(float damage, Vector3 hitDir, Vector3 hitPoint)
    {
        if (Breaking)
            return;
        health = Mathf.Max(0f, health - damage);
        if (health < 1e-3f) health = 0f;                     // 50 ÷ 3 을 세 번 빼면 0.00001 이 남아 콱이 하나 더 들어갔다 (09-27 첫 검사)
        MiningFx.I.Dust(hitPoint, -hitDir, Tuning.HIT_DUST);
        MiningFx.I.Chips(hitPoint, -hitDir);
        if (recoil != null)
            StopCoroutine(recoil);
        recoil = StartCoroutine(Recoil(transform.InverseTransformDirection(hitDir).normalized));
    }

    IEnumerator Recoil(Vector3 localDir)
    {
        Vector3 to = Slid;                                   // 밀린 뒤 제자리가 아니라 조금 더 나온 자리로 돌아온다
        Vector3 back = to + localDir * Tuning.HIT_RECOIL;
        yield return Move(mesh.localPosition, back, Tuning.HIT_RECOIL_TIME * 0.4f);
        yield return Move(back, to, Tuning.HIT_RECOIL_TIME * 0.6f);
        recoil = null;
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

    // 박힌 채 비트는 동안 덩이가 통로 쪽으로 기운다. u = 0 → 1
    public void Pry(float u)
    {
        if (Breaking)
            return;
        Vector3 axis = transform.InverseTransformDirection(Vector3.Cross(Vector3.up, outDir)).normalized;
        mesh.localRotation = Quaternion.AngleAxis(Tuning.MINE_PRY_TILT_DEG * Mathf.SmoothStep(0f, 1f, u), axis) * restRot;
    }

    // 덩이가 벽에서 빠져나온다. 통로 쪽(때린 사람 쪽)으로 튀고, 위로 떠서 바닥에 구른다
    public void Pop(Vector3 hitDir)
    {
        if (Breaking)
            return;
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

    // 사보타주 resetprogress: 손을 떼면 진행이 0 으로 (Minecraft 식 — 우리 규칙이 아니다)
    public void ResetProgress()
    {
        health = Tuning.POCKET_HEALTH;
        mesh.localPosition = rest;
        mesh.localRotation = restRot;
    }
}
