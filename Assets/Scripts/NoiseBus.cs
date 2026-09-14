using System;
using UnityEngine;

// 소음 이벤트 한 곳 (Godot NoiseBus.gd). 곡괭이 타격이 Make() 로 알린다.
// 아직 듣는 괴물은 없다 — MiningHud 가 원을 그리고, 검사가 Total·Last* 를 본다. 반경 0 은 소음이 아니다.
public static class NoiseBus
{
    public static event Action<Vector3, float, string, object> Made;

    public static int Total { get; private set; }
    public static float LastRadius { get; private set; }
    public static string LastKind { get; private set; }

    public static void Make(Vector3 pos, float radius, string kind, object who)
    {
        if (radius <= 0f)
            return;
        Total++;
        LastRadius = radius;
        LastKind = kind;
        Made?.Invoke(pos, radius, kind, who);
    }
}
