// m3-③ M1 램프 미끼의 빛무리: 괴물 안전모 램프 앞에 세우는 판(늘 카메라를 본다, StalkerLook.cs). 더하기 섞기, 벽에는 가린다(ZTest LEqual).
// 장면 안개를 일부러 안 탄다 — 내 램프를 끄면 거리 안개가 0.45(어둠 적응)가 되어 5 m 밖은 아무것도 안 보이는데, 어둠 속 먼 불빛은 보여야 미끼가 된다.
// 거리 감쇠는 StalkerLook 이 평소 안개 밀도(FOG_DENSITY)로 셈해 _Color 에 곱해 준다.
Shader "Tunnel/LureGlow"
{
    Properties
    {
        _Color ("", Color) = (1, 1, 1, 1)
    }
    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent" }
        Blend One One Cull Off ZWrite Off ZTest LEqual
        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            float4 _Color;
            struct v2f { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };
            v2f vert(appdata_base v) { v2f o; o.pos = UnityObjectToClipPos(v.vertex); o.uv = v.texcoord.xy; return o; }
            fixed4 frag(v2f i) : SV_Target
            {
                float r = length(i.uv * 2.0 - 1.0);             // 가운데 0 → 가장자리 1
                float core = saturate(1.0 - r * 4.0);           // 밝은 속
                float halo = pow(saturate(1.0 - r), 3.0);       // 번지는 빛무리
                return float4(_Color.rgb * (core + halo * 0.35), 1.0);
            }
            ENDCG
        }
    }
}
