using UnityEngine;

// 왼쪽 아래 소음 원 (Godot NoiseHud.gd). 내가 낸 마지막 소음 반경만큼 원이 뜨고 NOISE_HUD_FADE 동안 사라진다.
// UI-1c(09-16): 갱도 화면에 글자 0 — "철 N"·"곡괭이 없음" 글자는 지웠고(설계서 결정 변경 제안 1·3), 원은 판정용이라 DevHud 를 켰을 때만 그린다(제안 2).
public class MiningHud : MonoBehaviour
{
    public Player player;
    public Pickaxe pickaxe;

    static readonly Color NoiseColor = new Color(0.95f, 0.85f, 0.5f);
    static readonly Vector2 Center = new Vector2(110f, -110f);   // 왼쪽 아래 기준
    Texture2D disk, ring;
    GUIStyle label;
    float radius, left;
    [System.NonSerialized] public bool oreText;            // 사보타주 hudtext 가 켠다 — "철 N" 글자가 있던(옛) 상태
    public static int LabelsDrawn, CirclesDrawn;           // 검사용: 플레이어 화면에 그린 글자·원 수
    public string LastKind { get; private set; } = "-";
    public float LastRadius => radius;
    public float Left => left;

    void OnEnable() => NoiseBus.Made += OnNoise;
    void OnDisable() => NoiseBus.Made -= OnNoise;

    void OnNoise(Vector3 pos, float r, string kind, object who)
    {
        if (!ReferenceEquals(who, player))
            return;
        radius = r;
        left = Tuning.NOISE_HUD_FADE;
        LastKind = kind;
    }

    void Update() => left = Mathf.Max(0f, left - Time.deltaTime);

    void OnGUI()
    {
        if (label == null)
        {
            label = new GUIStyle(GUI.skin.label) { fontSize = 28 };
            label.normal.textColor = Color.white;
            disk = Circle(128, false);
            ring = Circle(128, true);
        }
        if (oreText)
        {
            GUI.Label(new Rect(24f, Screen.height - 64f, 236f, 40f), $"철 {player.ore}", label);
            LabelsDrawn++;
        }
        if (left <= 0f || !DevHud.Visible)                    // 원은 DevHud 를 켰을 때만
            return;
        CirclesDrawn++;
        float a = left / Tuning.NOISE_HUD_FADE;
        float r = radius * Tuning.NOISE_HUD_PX_PER_M * 0.5f;
        var c = new Vector2(Center.x, Screen.height + Center.y);
        var rect = new Rect(c.x - r, c.y - r, r * 2f, r * 2f);
        GUI.color = new Color(NoiseColor.r, NoiseColor.g, NoiseColor.b, 0.18f * a);
        GUI.DrawTexture(rect, disk);
        GUI.color = new Color(NoiseColor.r, NoiseColor.g, NoiseColor.b, 0.9f * a);
        GUI.DrawTexture(rect, ring);
        GUI.color = new Color(NoiseColor.r, NoiseColor.g, NoiseColor.b, a);
        GUI.DrawTexture(new Rect(c.x - 3f, c.y - 3f, 6f, 6f), disk);
        GUI.color = Color.white;
    }

    // 흰 원 텍스처. ringOnly 면 가장자리 띠만
    static Texture2D Circle(int size, bool ringOnly)
    {
        var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp };
        float h = size * 0.5f;
        for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                float d = new Vector2(x + 0.5f - h, y + 0.5f - h).magnitude;
                float alpha = ringOnly ? Mathf.Clamp01(1f - Mathf.Abs(d - (h - 3f)) / 2.5f) : Mathf.Clamp01(h - d);
                tex.SetPixel(x, y, new Color(1f, 1f, 1f, alpha));
            }
        tex.Apply();
        return tex;
    }
}
