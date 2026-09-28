using UnityEngine;

// MINE-2 (제안서 docs/제안서_MINE2_캐기_동작.md, 승인 09-28): 캐기 동작에서 잰 곡괭이 자리 표.
// 에디터 MineMotionBake 가 Kevin Iglesias 캐기 동작(에셋 스토어 — git 에서 뺌)을 사람 모형에 입혀 60 번/s 씩 재어
// Assets/Resources/Generated/MineMotion.asset 에 쓴다(이 파일도 git 에서 뺌 — 이 컴퓨터 빌드에만 들어간다). 없으면 Pickaxe 는 MINE-1 코드 동작.
// 좌표 = "몸 틀": 원점 = 내려친 순간의 눈, +Z = 몸 앞, +Y = 위. 곡괭이 자리·방향은 곡괭이 모델(pick_meshy.glb) 뿌리의 것.
public class MineMotion : ScriptableObject
{
    public string clipName;
    public float length;          // s, 동작 한 번 (되풀이)
    public float strikeT;         // s, 내려친 순간 (곡괭이 머리가 가장 앞)
    public float releaseT;        // s, 박힌 채 버티다 빼기 시작하는 순간 (Kevin 동작에도 0.3 s 버팀이 있다)
    public float topT;            // s, 뒤로 가장 크게 든 순간 (곡괭이 머리가 가장 뒤) — 여기서 내려치기가 시작된다
    public float rate = 60f;      // 샘플/s
    public Vector3[] pickPos;
    public Quaternion[] pickRot;
    public Vector3[] eyePos;      // 눈 자리 (내려친 순간 눈 기준) — 머리 흔들림
    public float[] headPitch;     // 머리 숙임 ° (내려친 순간 기준, + = 아래)

    public int Samples => pickPos == null ? 0 : pickPos.Length;

    public float Wrap(float t) => Mathf.Repeat(t, length);

    // 동작 시각 t 의 곡괭이 자리·방향, 눈 자리, 머리 숙임 (샘플 사이는 이어서)
    public void Eval(float t, out Vector3 pos, out Quaternion rot, out Vector3 eye, out float pitch)
    {
        float f = Wrap(t) * rate;
        int n = Samples, i = Mathf.Min(Mathf.FloorToInt(f), n - 1), j = Mathf.Min(i + 1, n - 1);
        float u = Mathf.Clamp01(f - i);
        pos = Vector3.LerpUnclamped(pickPos[i], pickPos[j], u);
        rot = Quaternion.Slerp(pickRot[i], pickRot[j], u);
        eye = Vector3.LerpUnclamped(eyePos[i], eyePos[j], u);
        pitch = Mathf.Lerp(headPitch[i], headPitch[j], u);
    }

    // from 에서 앞으로 to 까지 걸리는 동작 시간 (되풀이라 끝을 넘으면 처음으로)
    public float Span(float from, float to) { float d = Wrap(to) - Wrap(from); return d < 0f ? d + length : d; }
}
