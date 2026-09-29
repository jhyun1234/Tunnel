using System.IO;
using UnityEditor;
using UnityEngine;

// 3D-P2 (제안서 docs/제안서_3DP2_플레이어_재질_현실감.md, 승인 09-30): 플레이어 재질을 그림들로 — blender/rig/player_look.py 가 만든 그림을 쓴다.
// PlayerSkin.mat = 때 판(Tuning.PLAYER_DIRT_LEVEL) · 쇠·매끈함(부위별 윤기) · 가림 · 세부(천 결, 옷 · 흰 면만) · 노멀. 옛 값은 PlayerSkin_Clay.mat 사본(처음 한 번 — Shift+6 · 사보타주 claybody).
// 소품 재질 13 → Materials/<이름>.mat (되풀이 질감 · 쇠·매끈함 · 노멀), player.fbx 재질 자리에 끼운다(.meta 에 남음).
// 부르기(에디터 닫고): Unity.exe -batchmode -quit -projectPath . -executeMethod PlayerLookSetup.Run -logFile build/playerlook.log
public static class PlayerLookSetup
{
    const string DIR = "Assets/Tunnel/Player/", TEX = DIR + "Textures/", PROPS = TEX + "props/", MATS = DIR + "Materials/";
    public const string SKIN = DIR + "PlayerSkin.mat", CLAY = DIR + "PlayerSkin_Clay.mat";
    public static string Dirt(int level) => TEX + $"player_base_dirt{level + 1}.jpg";
    static readonly string[] PropMats = { "PlayerHelmet", "PlayerBattery", "PlayerOlive", "PlayerMetal", "PlayerAlu", "PlayerBezel", "PM_lens_rim", "PM_canister",
                                          "PlayerLampBody", "PlayerCord", "PM_rubber_black", "PM_strap_black", "PB_towel_dirty" };

    public static void Run()
    {
        int code = 0;
        try { Debug.Log("[PlayerLookSetup] " + Setup()); }
        catch (System.Exception e) { Debug.LogError("[PlayerLookSetup] ERROR " + e); code = 1; }
        EditorApplication.Exit(code);
    }

    static T Load<T>(string p) where T : Object => AssetDatabase.LoadAssetAtPath<T>(p) ?? throw new System.Exception("없음: " + p);

    static void Linear(string path)                                // 데이터 그림(쇠·매끈함 · 가림 · 가림판)은 선형
    {
        var ti = (TextureImporter)AssetImporter.GetAtPath(path) ?? throw new System.Exception("없음: " + path);
        if (!ti.sRGBTexture) return;
        ti.sRGBTexture = false;
        ti.SaveAndReimport();
    }

    static string Setup()
    {
        AssetDatabase.Refresh();
        foreach (var n in new[] { "player_ms.png", "player_ao.png", "player_detail_mask.png" }) Linear(TEX + n);
        foreach (var n in PropMats) Linear(PROPS + n + "_ms.png");
        if (AssetDatabase.LoadAssetAtPath<Material>(CLAY) == null)   // 찰흙 재질(3D-P 차례 3 값) 사본 — 처음 한 번만
            AssetDatabase.CopyAsset(SKIN, CLAY);

        var skin = Load<Material>(SKIN);
        float mPerUv = float.Parse(File.ReadAllText(TEX + "look.txt").Split(' ')[1], System.Globalization.CultureInfo.InvariantCulture);
        float tile = mPerUv / Tuning.PLAYER_CLOTH_TILE_M;          // 세부 되풀이 = 1 UV(m) ÷ 무늬 한 장(m)
        skin.SetTexture("_BaseMap", Load<Texture2D>(Dirt(Tuning.PLAYER_DIRT_LEVEL)));
        skin.SetTexture("_MetallicGlossMap", Load<Texture2D>(TEX + "player_ms.png"));
        skin.SetFloat("_SmoothnessTextureChannel", 0f);            // 매끈함 = 쇠 그림의 알파
        skin.SetFloat("_Smoothness", Tuning.PLAYER_SMOOTH_MUL);    // 그림이 있으면 배율
        skin.EnableKeyword("_METALLICSPECGLOSSMAP");
        skin.SetTexture("_OcclusionMap", Load<Texture2D>(TEX + "player_ao.png"));
        skin.SetFloat("_OcclusionStrength", 1f);
        skin.EnableKeyword("_OCCLUSIONMAP");
        skin.SetTexture("_DetailMask", Load<Texture2D>(TEX + "player_detail_mask.png"));
        skin.SetTexture("_DetailAlbedoMap", Load<Texture2D>(TEX + "cloth_detail_albedo.png"));
        skin.SetTexture("_DetailNormalMap", Load<Texture2D>(TEX + "cloth_detail_nor_gl.png"));
        skin.SetTextureScale("_DetailAlbedoMap", new Vector2(tile, tile));   // 세부 두 그림은 _DetailAlbedoMap_ST 하나를 같이 쓴다
        skin.SetFloat("_DetailAlbedoMapScale", 1f);
        skin.SetFloat("_DetailNormalMapScale", Tuning.PLAYER_CLOTH_DETAIL);
        skin.EnableKeyword("_DETAIL_MULX2");
        EditorUtility.SetDirty(skin);

        Directory.CreateDirectory(MATS);
        var fbx = (ModelImporter)AssetImporter.GetAtPath(DIR + "player.fbx");
        var lit = Shader.Find("Universal Render Pipeline/Lit");
        foreach (var n in PropMats)
        {
            string path = MATS + n + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(lit) { name = n }; AssetDatabase.CreateAsset(m, path); }
            m.SetTexture("_BaseMap", Load<Texture2D>(PROPS + n + "_Diffuse.jpg"));
            m.SetColor("_BaseColor", Color.white);
            m.SetTexture("_MetallicGlossMap", Load<Texture2D>(PROPS + n + "_ms.png"));
            m.SetFloat("_SmoothnessTextureChannel", 0f);
            m.SetFloat("_Smoothness", 1f);
            m.EnableKeyword("_METALLICSPECGLOSSMAP");
            m.SetTexture("_BumpMap", Load<Texture2D>(PROPS + n + "_nor_gl.jpg"));
            m.SetFloat("_BumpScale", 1f);
            m.EnableKeyword("_NORMALMAP");
            EditorUtility.SetDirty(m);
            fbx.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), n), m);
        }
        AssetDatabase.SaveAssets();
        fbx.SaveAndReimport();
        return $"skin: dirt level {Tuning.PLAYER_DIRT_LEVEL} · detail tile {tile:F2} (1 UV = {mPerUv:F3} m, pattern {Tuning.PLAYER_CLOTH_TILE_M} m) · props {PropMats.Length} remapped · clay copy {AssetDatabase.LoadAssetAtPath<Material>(CLAY) != null}";
    }
}
