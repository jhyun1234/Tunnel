using UnityEngine;

// 벽에서 튀어나온 광석 한 덩이. Godot Ore.gd.
// 시간이 지나도 사라지지 않는다 — 주우러 갈지 말지를 고르는 것이 긴장이라, 시간이 대신 지워주면 안 된다.
// 튀어나온 뒤 ORE_MAGNET_DELAY 동안은 안 빨려온다(구르는 것을 볼 새). 그 뒤 플레이어가 ORE_MAGNET_RANGE 안이면 가슴께로 날아와 줍힌다.
public class Ore : MonoBehaviour
{
    public static float MagnetRange = Tuning.ORE_MAGNET_RANGE;   // 검사 사보타주가 바꾼다

    [System.NonSerialized] public Player player;
    [System.NonSerialized] public Vector3 spawnPos;

    public float Age { get; private set; }
    public bool Pulled { get; private set; }

    void Update()
    {
        Age += Time.deltaTime;
        if (!Pulled)
        {
            // 거리로 직접 판정한다 — 트리거 신호는 순간이동(검사)에서 안 온다
            if (Age < Tuning.ORE_MAGNET_DELAY || Vector3.Distance(transform.position, player.transform.position) > MagnetRange)
                return;
            Pulled = true;
            Destroy(GetComponent<Rigidbody>());             // 물리를 끄고 직접 옮긴다. 안 그러면 날아오는 내내 중력과 싸운다
            GetComponent<Collider>().enabled = false;
        }
        Vector3 goal = player.transform.position + Vector3.up * Tuning.EYE_HEIGHT * 0.5f;   // 발밑이 아니라 가슴께로 — 화면에 보이게
        transform.position = Vector3.MoveTowards(transform.position, goal, Tuning.ORE_PULL_SPEED * Time.deltaTime);
        if (Vector3.Distance(transform.position, goal) <= Tuning.ORE_COLLECT_DIST)
        {
            player.AddOre(1);
            Destroy(gameObject);
        }
    }
}
