// ART-1 부스 맵 바위 · 바닥 (제안서 docs/제안서_ART1_현실감_광장_시험.md).
// 세 겹: 바위(Rock031) · 석탄(Rock035, 까만 띠) · 진흙(brown_mud_03, 바닥과 벽 아래) — 섞는 양은 Blender 가 적은 두 번째 UV(x = 석탄, y = 진흙).
// 무늬 되풀이: 헥스 타일링(HexTile.hlsl) + 몇 m 크기 밝기 얼룩. 젖음: 진흙 쪽 + 벽 흘러내린 자국 + 바닥 물웅덩이 — 세기는 전역 _ArtWet(ArtLook, Home/End).
// 질감은 세계 좌표 세 방향 투영(메시 UV · 탄젠트 불필요) — 맵의 상자 투영 UV 는 축이 바뀌는 곳에 X 자 이음새가 보였다.
// TEX-1 새 맵(MAP4, 키워드 _MAP4 — Map4.cs 가 재질 사본에 켠다. 부스 재질은 키워드가 없어 아래 #else 쪽 = 옛 코드 그대로): 재질 칸 하나 = 사진 짝.
//   벽 A · B(_BaseMap · _BaseMapB)는 첫 UV 의 x, 바닥 A · B(_MudMap · _MudMapB)는 첫 UV 의 y 로 섞는다(이음 자리: 0.5 = 두 사진의 경계, ±0.5 = ±10 m) — 얼룩으로 번지게(_Map4Blotch), 이음 길이는 전역 _Map4Seam(m)으로 좁힌다.
//   둘째 UV 는 부스와 같다(x = 탄층 띠 → _CoalMap, y = 바닥). 셋째 UV = (그 자리 젖음 배율 ÷ 2, 큰 길 = 벽 ② 의 어둡기를 받는 정도). 밝기 · 젖음은 새 맵 값 _Map4Bright · _Map4Wet (부스 값 _ArtBright · _ArtWet 를 안 건드린다).
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
        _OreTint ("Ore band tint (art.x 1..2 = ORE-1 광석 자리 띠)", Color) = (0.14, 0.14, 0.15, 1)
        _Tile ("Tile per 2.4 m: rock, coal, mud, hex cell", Vector) = (1, 1.4, 1.6, 1)
        _NormalScale ("Normal strength", Float) = 1.2
        _CoalGloss ("Coal gloss", Range(0, 1)) = 0.35
        _Macro ("Big blotch amount", Range(0, 0.6)) = 0.3
        _BaseMapB ("MAP4 wall B (A = rough)", 2D) = "white" {}
        _BumpMapB ("MAP4 wall B normal", 2D) = "bump" {}
        _MudMapB ("MAP4 floor B (A = rough)", 2D) = "white" {}
        _MudNormalB ("MAP4 floor B normal", 2D) = "bump" {}
        _TintA ("MAP4 wall A darkness (linear)", Vector) = (1, 1, 1, 0)
        _TintB ("MAP4 wall B darkness (linear)", Vector) = (1, 1, 1, 0)
        _FTintA ("MAP4 floor A darkness (linear)", Vector) = (1, 1, 1, 0)
        _FTintB ("MAP4 floor B darkness (linear)", Vector) = (1, 1, 1, 0)
        _TileB ("MAP4 tile per 2.4 m: wall B, -, floor B, -", Vector) = (1, 1, 1, 1)
        _Same ("MAP4 same photo in A and B: x wall, y floor · coal photo: z wall A, w wall B", Vector) = (0, 0, 0, 0)
        _DbgA ("MAP4 number colour: wall A", Vector) = (1, 0, 1, 0)
        _DbgB ("MAP4 number colour: wall B", Vector) = (1, 0, 1, 0)
        _DbgFA ("MAP4 number colour: floor A", Vector) = (1, 0, 1, 0)
        _DbgFB ("MAP4 number colour: floor B", Vector) = (1, 0, 1, 0)
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
        half4 _OreTint;
        float4 _Tile;
        half _NormalScale;
        half _CoalGloss;
        half _Macro;
        float4 _TintA, _TintB, _FTintA, _FTintB, _TileB, _Same, _DbgA, _DbgB, _DbgFA, _DbgFB;   // TEX-1 (새 맵) — 부스 재질에선 안 읽는다
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
            #pragma multi_compile_local _ _MAP4              // shader_feature 면 실행 파일에서 벗겨진다 — 새 맵 재질은 실행 중에 만든 사본뿐이라 빌드에 든 재질 자산이 이 키워드를 안 켠다
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "HexTile.hlsl"

            TEXTURE2D(_CoalMap); TEXTURE2D(_CoalNormal); TEXTURE2D(_MudMap); TEXTURE2D(_MudNormal);   // 색 그림 알파 = 거칠기 (읽는 횟수 1/3 덜기)
            float _ArtWet;                                   // 전역 (ArtLook) — 0 이면 마른 바위
            float _ArtBright;                                // 전역 (ArtLook) — 바위·석탄·진흙 밝기 배율 (사용자 09-27 "조금 어둡다")

        #if defined(_MAP4)
            TEXTURE2D(_BaseMapB); TEXTURE2D(_BumpMapB); TEXTURE2D(_MudMapB); TEXTURE2D(_MudNormalB);
            float4 _Map4Dbg2;                                // 전역: 번호 색 보기에서 큰 길(벽 ②)의 색 · a = 구역 켬(1) 끔(0)
            float _Map4Zones;                                // 전역: 구역 켬 1 · 끔 0 (T 키 — 끄면 탄층 띠도 없다: "벽 전부 ③")
            float _Map4Seam, _Map4Blotch, _Map4Debug, _Map4Shift, _Map4Bright, _Map4Wet, _Map4RoadDim;   // 전역 (Map4.cs): 이음 길이 m · 얼룩 정도 0..1 · 번호 색 보기 · 둘째 사진 자리 어긋남(사보타주 seamshift 만 0 이 아님) · 새 맵 밝기 · 젖음 · 큰 길 벽(② = ③ 을 더 어둡게)의 곱
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 blend : TEXCOORD0; float2 art : TEXCOORD1; float2 more : TEXCOORD2; UNITY_VERTEX_INPUT_INSTANCE_ID };
        #else
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 art : TEXCOORD1; UNITY_VERTEX_INPUT_INSTANCE_ID };
        #endif
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float2 art : TEXCOORD3;
                half fogFactor : TEXCOORD4;
            #if defined(_MAP4)
                float4 blend : TEXCOORD5;                    // xy = 벽 · 바닥 이음 자리, zw = 젖음 ÷ 2 · 큰 길
            #endif
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
            #if defined(_MAP4)
                o.blend = float4(i.blend, i.more);
            #endif
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

                half wc = smoothstep(0.1, 0.9, i.art.x), wm = smoothstep(0.1, 0.9, i.art.y);
                half3 alb = 0, nWS = N; half rough = 1;
            #if defined(_MAP4)
                // 이음: t = 0 (사진 A) → 1 (사진 B). 구운 값은 ±10 m 이고 _Map4Seam 으로 좁힌다. 얼룩 = 옆으로 긴 잡음(가로 3 m × 세로 0.7 m)을 문턱으로 — 뿌옇게 반반 겹치지 않고 B 가 얼룩으로 나타나 넓어진다. t = 0 · 1 에서는 늘 한 사진 100 %
                half2 t = saturate((i.blend.xy - 0.5) * 20.0 / max(_Map4Seam, 0.25) + 0.5), ts = smoothstep(0.0, 1.0, t);   // x = 벽 · y = 바닥 (따로 잇는다)
                half bn = lerp(0.15, 0.85, VNoise(pw * float3(0.3333, 1.4286, 0.3333) + 5.3));
                half2 mB2 = lerp(ts, smoothstep(bn - 0.1, bn + 0.1, t * 1.2 - 0.1), _Map4Blotch); half mB = mB2.x, mF = mB2.y;
                half3 road = lerp(1.0, _Map4RoadDim, i.blend.w);                                         // 큰 길: 같은 사진 ③ 을 ② 의 어둡기로 (점마다 — 재질 칸을 안 가른다). ③ 은 늘 A 칸(가장 작은 번호)이라 A 에만 곱한다
                wc *= _Map4Zones;
                UNITY_BRANCH if (wm < 0.999)
                {
                    UNITY_BRANCH if (_Same.x > 0.5 || mB < 0.999)
                        TriLayer(TEXTURE2D_ARGS(_BaseMap, sampler_BaseMap), _BumpMap, pw * perM * _Tile.x, dpx * perM * _Tile.x, dpy * perM * _Tile.x, bw, N, alb, nWS, rough);
                    alb *= _TintA.rgb * road;
                    UNITY_BRANCH if (_Same.x < 0.5 && mB > 0.001)                                        // _Same.x = 벽은 한 장이고 바닥만 바뀌는 칸 — 두 번 읽지 않는다
                    {
                        half3 a2, n2; half r2;
                        TriLayer(TEXTURE2D_ARGS(_BaseMapB, sampler_BaseMap), _BumpMapB, pw * perM * _TileB.x + _Map4Shift, dpx * perM * _TileB.x, dpy * perM * _TileB.x, bw, N, a2, n2, r2);
                        alb = lerp(alb, a2 * _TintB.rgb, mB); nWS = normalize(lerp(nWS, n2, mB)); rough = lerp(rough, r2, mB);
                    }
                    rough = lerp(rough, min(rough, 1.0 - _CoalGloss), lerp(_Same.z, _Same.w, mB));       // 석탄 윤기는 ⑦ 이 든 칸에만 (_Same.z · w = A · B 가 석탄인가)
                    UNITY_BRANCH if (wc > 0.001)                                                         // 탄층 띠 — 석탄 사진의 울퉁불퉁함 · 윤기까지 (부스 쪽 아래 줄은 색만 섞인다)
                    {
                        half3 a2, n2; half r2;
                        TriLayer(TEXTURE2D_ARGS(_CoalMap, sampler_BaseMap), _CoalNormal, pw * perM * _Tile.y + 0.37, dpx * perM * _Tile.y, dpy * perM * _Tile.y, bw, N, a2, n2, r2);
                        alb = lerp(alb, a2 * _CoalTint.rgb, wc); nWS = normalize(lerp(nWS, n2, wc)); rough = lerp(rough, min(r2, 1.0 - _CoalGloss), wc);
                    }
                }
                UNITY_BRANCH if (wm > 0.001)
                {
                    half3 a1 = 0, n1 = N; half r1 = 1;
                    UNITY_BRANCH if (_Same.y > 0.5 || mF < 0.999)
                        TriLayer(TEXTURE2D_ARGS(_MudMap, sampler_BaseMap), _MudNormal, pw * perM * _Tile.z + 0.71, dpx * perM * _Tile.z, dpy * perM * _Tile.z, bw, N, a1, n1, r1);
                    UNITY_BRANCH if (_Same.y > 0.5) a1 *= _FTintA.rgb;
                    else
                    {
                        a1 *= _FTintA.rgb;
                        UNITY_BRANCH if (mF > 0.001)
                        {
                            half3 a2, n2; half r2;
                            TriLayer(TEXTURE2D_ARGS(_MudMapB, sampler_BaseMap), _MudNormalB, pw * perM * _TileB.z + 0.71 + _Map4Shift, dpx * perM * _TileB.z, dpy * perM * _TileB.z, bw, N, a2, n2, r2);
                            a1 = lerp(a1, a2 * _FTintB.rgb, mF); n1 = normalize(lerp(n1, n2, mF)); r1 = lerp(r1, r2, mF);
                        }
                    }
                    alb = lerp(alb, a1, wm); nWS = normalize(lerp(nWS, n1, wm)); rough = lerp(rough, r1, wm);
                }
                UNITY_BRANCH if (_Map4Debug > 0.5) alb = lerp(lerp(lerp(_DbgA.rgb, _Map4Dbg2.rgb, i.blend.w * _Map4Dbg2.a), _DbgB.rgb, mB), lerp(_DbgFA.rgb, _DbgFB.rgb, mF), wm);   // G 키: 사진 대신 번호 색
                float artBright = _Map4Bright, artWet = _Map4Wet * i.blend.z * 2.0;
            #else
                // 바위 · 석탄 (진흙만 보이는 곳 = 바닥은 안 읽는다)
                UNITY_BRANCH if (wm < 0.999)
                {
                    TriLayer(TEXTURE2D_ARGS(_BaseMap, sampler_BaseMap), _BumpMap, pw * perM * _Tile.x, dpx * perM * _Tile.x, dpy * perM * _Tile.x, bw, N, alb, nWS, rough);
                    alb *= _BaseColor.rgb;
                    UNITY_BRANCH if (wc > 0.001)
                    {
                        half3 a2, n2; half r2;
                        TriLayer(TEXTURE2D_ARGS(_CoalMap, sampler_BaseMap), _CoalNormal, pw * perM * _Tile.y + 0.37, dpx * perM * _Tile.y, dpy * perM * _Tile.y, bw, N, a2, n2, r2);
                        alb = lerp(alb, a2 * lerp(_CoalTint.rgb, _OreTint.rgb, saturate(i.art.x - 1.0)), wc);   // ORE-1: 광석 자리 띠(x 1..2)는 더 검게 — 사진의 막장 석탄 (조사 12). ART-1 무작위 띠(x ≤ 1)는 그대로 nWS = normalize(lerp(nWS, n2, wc)); rough = lerp(rough, min(r2, 1.0 - _CoalGloss), wc);
                    }
                }
                UNITY_BRANCH if (wm > 0.001)
                {
                    half3 a2, n2; half r2;
                    TriLayer(TEXTURE2D_ARGS(_MudMap, sampler_BaseMap), _MudNormal, pw * perM * _Tile.z + 0.71, dpx * perM * _Tile.z, dpy * perM * _Tile.z, bw, N, a2, n2, r2);
                    alb = lerp(alb, a2 * _MudTint.rgb, wm); nWS = normalize(lerp(nWS, n2, wm)); rough = lerp(rough, r2, wm);
                }
                float artBright = _ArtBright, artWet = _ArtWet;
            #endif

                // 몇 m 크기 밝기 얼룩 (같은 벽이 어디서나 같은 색이 아니게)
                alb *= lerp(1.0 - _Macro, 1.0 + _Macro, VNoise(pw * 0.22) * 0.67 + VNoise(pw * 0.45) * 0.33) * artBright;

                // 젖음: 벽 아래 진흙 띠 · 벽 흘러내린 자국(세로로 긴 잡음) · 바닥 물웅덩이 — 바닥 전체는 조금만(다 적시면 기름처럼 번들거렸다, 09-27 첫 캡처)
                half up = saturate(N.y), streak = 0, puddle = 0;
                UNITY_BRANCH if (up < 0.9) streak = smoothstep(0.62, 0.74, Fbm2(float3(pw.x * 1.4, pw.y * 0.12, pw.z * 1.4))) * (1.0 - up);
                UNITY_BRANCH if (up > 0.75) puddle = smoothstep(0.58, 0.66, Fbm2(float3(pw.x, 0, pw.z) * 0.45)) * smoothstep(0.75, 0.9, up);
                half wet = saturate(max(max(max(i.art.y * (1.0 - up) * 0.6, streak), puddle), 0.12 * up) * artWet);
                alb *= lerp(1.0, 0.5, wet);
                half smooth = lerp(1.0 - rough, 0.9, wet * 0.85);
                nWS = normalize(lerp(nWS, N, saturate(puddle * artWet) * 0.9));

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
