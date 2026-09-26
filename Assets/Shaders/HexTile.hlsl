// 헥스 타일링 — 한 장 질감을 육각 칸마다 다른 자리에서 가져와 섞어 무늬 되풀이를 없앤다 (ART-1).
// 방법: Morten S. Mikkelsen, "Practical Real-Time Hex-Tiling", JCGT 11(3) 2022 · https://github.com/mmikk/hextile-demo (MIT — 아래 알림).
// 돌리기는 뺐다(칸마다 옮기기만) — 노멀맵을 칸마다 돌릴 필요가 없다. 미분은 밖에서 받는다(분기 안에서 ddx 를 쓰면 안 된다).
//
// MIT License — Copyright (c) 2022 mmikk
// Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation
// files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy,
// modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
// is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be
// included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
// EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
// NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
// IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
// DEALINGS IN THE SOFTWARE.
#ifndef TUNNEL_HEXTILE_INCLUDED
#define TUNNEL_HEXTILE_INCLUDED

struct HexUV { float2 uv1, uv2, uv3; float3 w; float2 dx, dy; };

void HexTriangleGrid(float2 st, out float3 w, out int2 v1, out int2 v2, out int2 v3)
{
    st *= 2.0 * sqrt(3.0);
    const float2x2 gridToSkewed = float2x2(1.0, -0.57735027, 0.0, 1.15470054);
    float2 sk = mul(gridToSkewed, st);
    int2 baseId = int2(floor(sk));
    float3 t = float3(frac(sk), 0);
    t.z = 1.0 - t.x - t.y;
    float s = step(0.0, -t.z);
    float s2 = 2.0 * s - 1.0;
    w = float3(-t.z * s2, s - t.y * s2, s - t.x * s2);
    v1 = baseId + int2(s, s);
    v2 = baseId + int2(s, 1 - s);
    v3 = baseId + int2(1 - s, s);
}

float2 HexHash(float2 p)
{
    float2 r = mul(float2x2(127.1, 311.7, 269.5, 183.3), p);
    return frac(sin(r) * 43758.5453);
}

// st = 질감 좌표 · cell = 칸 크기 배율(1 = 질감 한 장에 칸 약 두 개) · dx dy = ddx(st) ddy(st)
HexUV HexSetup(float2 st, float cell, float2 dx, float2 dy)
{
    HexUV h;
    int2 v1, v2, v3;
    HexTriangleGrid(st / cell, h.w, v1, v2, v3);
    h.uv1 = st + HexHash(v1); h.uv2 = st + HexHash(v2); h.uv3 = st + HexHash(v3);
    h.dx = dx; h.dy = dy;
    return h;
}

// 색: 세 칸을 밝기로 날카롭게 섞는다(데모 값: 대비 0.6 · 지수 7). 같은 무게를 노멀·거칠기에도 쓴다.
half4 HexColor(TEXTURE2D_PARAM(tex, smp), HexUV h, out float3 W)
{
    half4 c1 = SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv1, h.dx, h.dy);
    half4 c2 = SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv2, h.dx, h.dy);
    half4 c3 = SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv3, h.dx, h.dy);
    const float3 lw = float3(0.299, 0.587, 0.114);
    float3 Dw = lerp(1.0, float3(dot(c1.rgb, lw), dot(c2.rgb, lw), dot(c3.rgb, lw)), 0.6);
    W = Dw * pow(max(h.w, 1e-4), 7.0);
    W /= (W.x + W.y + W.z);
    return W.x * c1 + W.y * c2 + W.z * c3;
}

half4 HexSample(TEXTURE2D_PARAM(tex, smp), HexUV h, float3 W)
{
    return W.x * SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv1, h.dx, h.dy)
         + W.y * SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv2, h.dx, h.dy)
         + W.z * SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv3, h.dx, h.dy);
}

half3 HexNormal(TEXTURE2D_PARAM(tex, smp), HexUV h, float3 W, half scale)
{
    half3 n = W.x * UnpackNormalScale(SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv1, h.dx, h.dy), scale)
            + W.y * UnpackNormalScale(SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv2, h.dx, h.dy), scale)
            + W.z * UnpackNormalScale(SAMPLE_TEXTURE2D_GRAD(tex, smp, h.uv3, h.dx, h.dy), scale);
    return normalize(n);
}
#endif
