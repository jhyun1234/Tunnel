using UnityEditor;

// Poly Haven 텍스처 파일 이름으로 임포트 설정을 정한다. glTFast 는 프로젝트 안 외부 텍스처의 설정을 고치지 않는다.
// 노멀맵이 sRGB 일반 텍스처로 읽히면 노멀이 한쪽으로 기울어, 대칭 갱도에서 +Z / -Z 화면 밝기가 0.022 / 0.129 로
// 6배 갈렸다 (09-14 사용자 지적 "+Z 쪽으로 램프 빛이 안 보인다", 검사 lamp_symmetric_z).
public class TextureImportRules : AssetPostprocessor
{
    public override uint GetVersion() => 3;

    void OnPreprocessTexture()
    {
        var importer = (TextureImporter)assetImporter;
        string path = assetPath.ToLowerInvariant();
        if (path.Contains("_nor_gl"))
            importer.textureType = TextureImporterType.NormalMap;     // OpenGL(Y+) 노멀 = Unity 규약
        else if (path.Contains("_rough") || path.Contains("_arm"))
            importer.sRGBTexture = false;                              // 데이터 텍스처는 선형
        if (path.Contains("/tunnel/art/") || path.Contains("/fab/resources/rock/"))   // + TEX-1 새 맵 바위 사진 (tools/pack_rock_tex.py — 같은 재질 MineRock 이 읽는다)
            importer.anisoLevel = 4;                                   // ART-1 바위·바닥: 비스듬히 보는 바닥이 뭉개지지 않게 (8 은 fps 가 무거웠다)
    }
}
