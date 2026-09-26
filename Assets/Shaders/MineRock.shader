// ART-1 부스 맵 바위 · 바닥 (제안서 docs/제안서_ART1_현실감_광장_시험.md).
// 세 겹: 바위(Rock031) · 석탄(Rock035, 까만 띠) · 진흙(brown_mud_03, 바닥과 벽 아래) — 섞는 양은 Blender 가 적은 두 번째 UV(x = 석탄, y = 진흙).
// 무늬 되풀이: 헥스 타일링(HexTile.hlsl) + 몇 m 크기 밝기 얼룩. 젖음: 진흙 쪽 + 벽 흘러내린 자국 + 바닥 물웅덩이 — 세기는 전역 _ArtWet(ArtLook, Home/End).
// 질감은 세계 좌표 세 방향 투영(메시 UV · 탄젠트 불필요) — 맵의 상자 투영 UV 는 축이 바뀌는 곳에 X 자 이음새가 보였다.
Shader "Tunnel/MineRock"
{
    Properties
    {
        _BaseMap ("Rock (A = rough)", 2D) = "white" {}
        _BumpMap ("Rock normal", 2D) = "bump" {}
        _CoalMap ("Coal (A = rough)", 2D) = "white" {}
        _CoalNormal ("Coal normal", 2D) = "bump" {}
        _MudMap ("Mud (A = rough)", 2D) = "white" {}
        _MudNormal ("Mud normal", 2D) = "bump" {}
        _BaseColor ("Rock tint", Color) = (1, 1, 1, 1)
        _CoalTint ("Coal tint", Color) = (0.45, 0.45, 0.5, 1)
        _MudTint ("Mud tint", Color) = (0.55, 0.5, 0.46, 1)
        _Tile ("Tile per 2.4 m: rock, coal, mud, hex cell", Vector) = (1, 1.4, 1.6, 1)
        _NormalScale ("Normal strength", Float) = 1.2
        _CoalGloss ("Coal gloss", Range(0, 1)) = 0.35
        _Macro ("Big blotch amount", Range(0, 0.6)) = 0.3
        _Cutoff ("", Float) = 0.5
        _Surface ("", Float) = 0
    }

    HLSLINCLUDE
    #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
    #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/SurfaceInput.hlsl"
    CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST;
        float4 _BaseMap_TexelSize;
        half4 _BaseColor;
        half4 _SpecColor;
        half4 _EmissionColor;
        half _Cutoff;
        half _Surface;
        half4 _CoalTint;
        half4 _MudTint;
        float4 _Tile;
        half _NormalScale;
        half _CoalGloss;
        half _Macro;
        UNITY_TEXTURE_STREAMING_DEBUG_VARS;
    CBUFFER_END
    ENDHLSL

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            #pragma multi_compile _ _LIGHT_LAYERS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/RenderingLayers.hlsl"
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Fog.hlsl"
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "HexTile.hlsl"

            TEXTURE2D(_CoalMap); TEXTURE2D(_CoalNormal); TEXTURE2D(_MudMap); TEXTURE2D(_MudNormal);   // 색 그림 알파 = 거칠기 (읽는 횟수 1/3 덜기)
            float _ArtWet;                                   // 전역 (ArtLook) — 0 이면 마른 바위

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 art : TEXCOORD1; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float2 art : TEXCOORD3;
                half fogFactor : TEXCOORD4;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings vert(Attributes i)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(i); UNITY_TRANSFER_INSTANCE_ID(i, o);
                VertexPositionInputs p = GetVertexPositionInputs(i.positionOS.xyz);
                o.positionCS = p.positionCS; o.positionWS = p.positionWS;
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.art = i.art;
                o.fogFactor = ComputeFogFactor(p.positionCS.z);
                return o;
            }

            // 값 잡음 0..1
            float Hash3(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
            float VNoise(float3 x)
            {
                float3 i = floor(x), f = frac(x); f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(lerp(Hash3(i), Hash3(i + float3(1, 0, 0)), f.x), lerp(Hash3(i + float3(0, 1, 0)), Hash3(i + float3(1, 1, 0)), f.x), f.y),
                            lerp(lerp(Hash3(i + float3(0, 0, 1)), Hash3(i + float3(1, 0, 1)), f.x), lerp(Hash3(i + float3(0, 1, 1)), Hash3(i + float3(1, 1, 1)), f.x), f.y), f.z);
            }
            float Fbm2(float3 x) { return (VNoise(x) + 0.5 * VNoise(x * 2.03)) / 1.5; }

            // 한 겹 = 세 방향 투영(세계 좌표) × 헥스 타일링. 법선 쪽 무게가 0 이 아닌 투영만 읽는다(대부분 한 방향, 모서리만 둘).
            // 법선 섞기 = Ben Golus "Normal Mapping for a Triplanar Shader" 의 whiteout. 맵의 상자 투영 UV 는 안 쓴다 — 투영 축이 바뀌는 곳에 X 자 이음새가 보였다(09-27 캡처)
            void TriLayer(TEXTURE2D_PARAM(cT, s), TEXTURE2D(nT), float3 p, float3 dpx, float3 dpy, float3 bw, float3 N,
                          out half3 alb, out half3 nWS, out half rough)
            {
                alb = 0; rough = 0; half3 ns = 0; float3 W;
                UNITY_BRANCH if (bw.x > 0)
                {
                    HexUV h = HexSetup(p.zy, _Tile.w, dpx.zy, dpy.zy);
                    half4 c = HexColor(TEXTURE2D_ARGS(cT, s), h, W);
                    alb += bw.x * c.rgb; rough += bw.x * c.a;
                    half3 t = HexNormal(TEXTURE2D_ARGS(nT, s), h, W, _NormalScale);
                    t = half3(t.xy + N.zy, abs(t.z) * N.x); ns += bw.x * t.zyx;
                }
                UNITY_BRANCH if (bw.y > 0)
                {
                    HexUV h = HexSetup(p.xz, _Tile.w, dpx.xz, dpy.xz);
                    half4 c = HexColor(TEXTURE2D_ARGS(cT, s), h, W);
                    alb += bw.y * c.rgb; rough += bw.y * c.a;
                    half3 t = HexNormal(TEXTURE2D_ARGS(nT, s), h, W, _NormalScale);
                    t = half3(t.xy + N.xz, abs(t.z) * N.y); ns += bw.y * t.xzy;
                }
                UNITY_BRANCH if (bw.z > 0)
                {
                    HexUV h = HexSetup(p.xy, _Tile.w, dpx.xy, dpy.xy);
                    half4 c = HexColor(TEXTURE2D_ARGS(cT, s), h, W);
                    alb += bw.z * c.rgb; rough += bw.z * c.a;
                    half3 t = HexNormal(TEXTURE2D_ARGS(nT, s), h, W, _NormalScale);
                    t = half3(t.xy + N.xy, abs(t.z) * N.z); ns += bw.z * t.xyz;
                }
                nWS = normalize(ns);
            }

            half4 frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                float3 N = normalize(i.normalWS);
                float3 pw = i.positionWS;
                float3 dpx = ddx(pw), dpy = ddy(pw);
                float3 bw = pow(abs(N), 4.0); bw /= dot(bw, 1.0); bw = saturate(bw - 0.15); bw /= dot(bw, 1.0);   // 두 방향을 섞는 곳을 좁게 (09-27 fps 67 → 덜기)
                const float perM = 0.42;                          // 질감 한 장 = 2.4 m (옛 맵 UV 와 같은 촘촘함)

                // 바위 · 석탄 (진흙만 보이는 곳 = 바닥은 안 읽는다)
                half wc = smoothstep(0.1, 0.9, i.art.x), wm = smoothstep(0.1, 0.9, i.art.y);
                half3 alb = 0, nWS = N; half rough = 1;
                UNITY_BRANCH if (wm < 0.999)
                {
                    TriLayer(TEXTURE2D_ARGS(_BaseMap, sampler_BaseMap), _BumpMap, pw * perM * _Tile.x, dpx * perM * _Tile.x, dpy * perM * _Tile.x, bw, N, alb, nWS, rough);
                    alb *= _BaseColor.rgb;
                    UNITY_BRANCH if (wc > 0.001)
                    {
                        half3 a2, n2; half r2;
                        TriLayer(TEXTURE2D_ARGS(_CoalMap, sampler_BaseMap), _CoalNormal, pw * perM * _Tile.y + 0.37, dpx * perM * _Tile.y, dpy * perM * _Tile.y, bw, N, a2, n2, r2);
                        alb = lerp(alb, a2 * _CoalTint.rgb, wc); nWS = normalize(lerp(nWS, n2, wc)); rough = lerp(rough, min(r2, 1.0 - _CoalGloss), wc);
                    }
                }
                UNITY_BRANCH if (wm > 0.001)
                {
                    half3 a2, n2; half r2;
                    TriLayer(TEXTURE2D_ARGS(_MudMap, sampler_BaseMap), _MudNormal, pw * perM * _Tile.z + 0.71, dpx * perM * _Tile.z, dpy * perM * _Tile.z, bw, N, a2, n2, r2);
                    alb = lerp(alb, a2 * _MudTint.rgb, wm); nWS = normalize(lerp(nWS, n2, wm)); rough = lerp(rough, r2, wm);
                }

                // 몇 m 크기 밝기 얼룩 (같은 벽이 어디서나 같은 색이 아니게)
                alb *= lerp(1.0 - _Macro, 1.0 + _Macro, VNoise(pw * 0.22) * 0.67 + VNoise(pw * 0.45) * 0.33);

                // 젖음: 벽 아래 진흙 띠 · 벽 흘러내린 자국(세로로 긴 잡음) · 바닥 물웅덩이 — 바닥 전체는 조금만(다 적시면 기름처럼 번들거렸다, 09-27 첫 캡처)
                half up = saturate(N.y), streak = 0, puddle = 0;
                UNITY_BRANCH if (up < 0.9) streak = smoothstep(0.62, 0.74, Fbm2(float3(pw.x * 1.4, pw.y * 0.12, pw.z * 1.4))) * (1.0 - up);
                UNITY_BRANCH if (up > 0.75) puddle = smoothstep(0.58, 0.66, Fbm2(float3(pw.x, 0, pw.z) * 0.45)) * smoothstep(0.75, 0.9, up);
                half wet = saturate(max(max(max(i.art.y * (1.0 - up) * 0.6, streak), puddle), 0.12 * up) * _ArtWet);
                alb *= lerp(1.0, 0.5, wet);
                half smooth = lerp(1.0 - rough, 0.9, wet * 0.85);
                nWS = normalize(lerp(nWS, N, saturate(puddle * _ArtWet) * 0.9));

                InputData d = (InputData)0;
                d.positionWS = pw;
                d.positionCS = i.positionCS;
                d.normalWS = nWS;
                d.viewDirectionWS = GetWorldSpaceNormalizeViewDir(pw);
                d.shadowCoord = TransformWorldToShadowCoord(pw);
                d.fogCoord = i.fogFactor;
                d.bakedGI = EvaluateAmbientProbeSRGB(nWS);
                d.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS);
                d.shadowMask = half4(1, 1, 1, 1);

                SurfaceData sd = (SurfaceData)0;
                sd.albedo = alb;
                sd.smoothness = smooth;
                sd.normalTS = half3(0, 0, 1);
                sd.occlusion = 1;
                sd.alpha = 1;
                half4 col = UniversalFragmentPBR(d, sd);
                col.rgb = MixFog(col.rgb, i.fogFactor);
                return col;
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On ZTest LEqual ColorMask 0
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex ShadowPassVertex
            #pragma fragment ShadowPassFragment
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/Shaders/ShadowCasterPass.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex DepthOnlyVertex
            #pragma fragment DepthOnlyFragment
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/Shaders/DepthOnlyPass.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }
            ZWrite On
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex DepthNormalsVertex
            #pragma fragment DepthNormalsFragment
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/RenderingLayers.hlsl"
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/Shaders/DepthNormalsPass.hlsl"
            ENDHLSL
        }
    }
}
