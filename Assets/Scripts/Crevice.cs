using System.Collections.Generic;
using UnityEngine;

// R2b 바위 틈 하나 (제안서 docs/제안서_R2b_바위틈_비집기.md). BuildM1 이 맵의 SLOT_Crevice_<i>_P0..Pn 으로 만든다.
// path = 바위 밖 선 자리 → 틈 가운데 선 → 숨는 자리(막힌) / 반대편 바위 밖 선 자리(뚫린). 양 끝 어디서나 들어간다 — 막힌 틈은 숨는 자리에서 E 로 나온다.
public class Crevice : MonoBehaviour
{
    public Vector3[] path;
    public bool through;
    public float Length { get { float L = 0f; for (int i = 1; i < path.Length; i++) L += Vector3.Distance(path[i - 1], path[i]); return L; } }

    public static readonly List<Crevice> All = new List<Crevice>();
    void OnEnable() => All.Add(this);
    void OnDisable() => All.Remove(this);

    // 서 있는 자리(발)와 보는 방향으로 들어갈 수 있는 틈 → 옮겨 갈 길(첫 점 = 발), 끝나고 볼 방향. 막힌 틈에 들어가면 입구 쪽(밖)을 보게 돈다
    public static bool Find(Vector3 feet, Vector3 forward, out List<Vector3> route, out Vector3 endLook)
    {
        route = null; endLook = Vector3.zero;
        forward.y = 0f; forward.Normalize();
        float best = Tuning.SQUEEZE_REACH_M;
        foreach (var c in All)
            for (int e = 0; e < 2; e++)
            {
                var p = new List<Vector3>(c.path);
                if (e == 1) p.Reverse();
                Vector3 d = p[1] - p[0]; d.y = 0f;
                Vector3 off = p[0] - feet; off.y = 0f;
                if (off.magnitude > best || Mathf.Abs(p[0].y - feet.y) > 1f || Vector3.Angle(forward, d) > Tuning.SQUEEZE_FACE_DEG) continue;
                best = off.magnitude;
                p[0] = feet;
                route = p;
                bool intoHide = !c.through && e == 0;
                endLook = intoHide ? p[p.Count - 2] - p[p.Count - 1] : p[p.Count - 1] - p[p.Count - 2];
                endLook.y = 0f;
            }
        return route != null;
    }
}
