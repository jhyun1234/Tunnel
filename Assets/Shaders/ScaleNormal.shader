// 탄젠트 노멀맵(RGB = xyz, glTF 방식)의 기울기(xy)에 _Scale 을 곱해 다시 정규화한다. StalkerLook.cs 가 Graphics.Blit 으로 쓴다.
// glTFast 6.14.1 의 normalTexture_scale 이 URP 셰이더 그래프에서 안 먹어서(Normal.cginc 의 SHADER_TARGET 조건) 그림 쪽에서 세기를 준다.
Shader "Hidden/Tunnel/ScaleNormal"
{
    Properties
    {
        _MainTex ("", 2D) = "bump" {}
        _Scale ("", Float) = 1
    }
    SubShader
    {
        Cull Off ZWrite Off ZTest Always
        Pass
        {
            CGPROGRAM
            #pragma vertex vert_img
            #pragma fragment frag
            #include "UnityCG.cginc"
            sampler2D _MainTex;
            float _Scale;
            fixed4 frag(v2f_img i) : SV_Target
            {
                float4 p = tex2D(_MainTex, i.uv);
                float2 xy = (p.xy * 2.0 - 1.0) * _Scale;
                float l = length(xy);
                if (l > 0.99) xy *= 0.99 / l;          // 너무 누우면 z 가 0 이 된다
                float z = sqrt(1.0 - dot(xy, xy));
                return float4(xy * 0.5 + 0.5, z * 0.5 + 0.5, 1.0);
            }
            ENDCG
        }
    }
}
