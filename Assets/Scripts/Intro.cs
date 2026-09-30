using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

// UI-2 인트로 (지스타 2026 운영지침 1-1 · 4-1, 제안서 UI-2). 검은 바탕에 대학·사업단 로고 + 팀명 + 게임명을 INTRO_LOGO_MIN_S 이상 보여 준 뒤
// (그 뒤 아무 키, 또는 INTRO_LOGO_AUTO_S 에 저절로) 시작 메뉴 — 시작 · 소리 크기 · 끝내기. 위아래(또는 W/S)로 고르고 Enter·Space·클릭, 소리 크기는 좌우(A/D).
// 소리 크기는 AudioListener.volume(전역)에 바로 넣고 PlayerPrefs 에 남긴다 — 세이브가 아니라 부스 설정. 잡히면 Stalker 가 이 씬을 다시 불러 처음으로 돌아온다.
// UI-2d(제안서 docs/제안서_UI2d_인트로_간판.md, 09-29): 갱도 속 흰 함석 간판이 흔들리고, 머리 램프가 숨쉬듯 끄덕이고, 먼 램프가 조금 떨린다. 메뉴에선 로고 숨김.
// 판정 키: F1 값 한 줄 · [ ] 간판 밝기 · ; ' 흔들림 크기 — "아무 키"로 세지 않는다.
// -check: 이 씬의 검사(로고 최소 시간 · 스킵 · 소리 크기)를 먼저 하고 "시작"으로 갱도 검사(M1Check)로 넘어간다. 잡힘 뒤 두 번째로 오면 마지막 검사를 적고 끝낸다.
public class Intro : MonoBehaviour
{
    public GameObject logoPanel, menuPanel;
    public Text[] items;                                       // 시작 · 소리 크기 · 끝내기
    public RectTransform underline;                            // 고른 메뉴 줄 밑 빨간 줄
    public Text prompt, tuneLine;                              // "아무 키나 누르세요" · 판정 키 값 (F1)
    public Image[] logos;                                      // 대학 · 사업단 로고 (검사 intro_logos_keep_aspect)
    public Transform sign;                                     // 간판 윗변 가운데 — 여기서 흔들린다
    public Renderer signRenderer;
    public Light lamp, farLamp;                                // 간판 비추는 머리 램프 · 갱도 끝 먼 램프
    public static bool expectReturn;                           // M1Check 가 잡힘을 일으키기 전에 켠다 — 다시 이 씬에 오면 통과
    public static float minLogoS = Tuning.INTRO_LOGO_MIN_S;    // 사보타주 skipearly 가 0 으로
    const string VolumeKey = "volume";
    const int VolumeItem = 1;
    float t;
    int sel;
    bool menu;
    string only = "";
    float swayDeg = Tuning.INTRO_SIGN_SWAY_DEG, signBright = Tuning.INTRO_SIGN_BRIGHT;
    Quaternion signRest;                                       // 흔들림 없는 간판 방향 (카메라를 마주 본다)

    int Volume => Mathf.RoundToInt(AudioListener.volume * 100f);

    void Awake()
    {
        AudioListener.volume = PlayerPrefs.GetFloat(VolumeKey, 1f);
        Cursor.lockState = CursorLockMode.Locked;
        Cursor.visible = false;
        signRest = sign.localRotation;
        Shader.SetGlobalFloat("_ArtWet", Tuning.ART_WET);      // 부스 바위 재질(MineRock)의 젖음 · 밝기 — 게임에선 ArtLook 이 넣는다 (0 이면 바위가 검다)
        Shader.SetGlobalFloat("_ArtBright", Tuning.ART_BRIGHT);
        logoPanel.SetActive(true);
        menuPanel.SetActive(false);
        Refresh();
    }

    void Start()
    {
        string[] args = Environment.GetCommandLineArgs();
        if (Array.IndexOf(args, "-check") < 0)
            return;
        int o = Array.IndexOf(args, "-only");
        if (o >= 0 && o + 1 < args.Length) only = args[o + 1];
        int s = Array.IndexOf(args, "-sabotage");
        string sab = s >= 0 && s + 1 < args.Length ? args[s + 1] : "";
        if (sab == "skipearly") minLogoS = 0f;
        if (sab == "nosignlight") lamp.enabled = false;        // intro_sign_lit 가 FAIL 해야 한다
        if (sab == "logostretch")                              // intro_logos_keep_aspect 가 FAIL 해야 한다
            foreach (var l in logos)
            {
                l.preserveAspect = false;
                l.rectTransform.sizeDelta = new Vector2(l.rectTransform.sizeDelta.x * 2f, l.rectTransform.sizeDelta.y);
            }
        if (expectReturn)
        {
            M1Check.Check("intro_returns_after_catch", true, $"scene {SceneManager.GetActiveScene().name} loaded after catch");
            M1Check.Finish();
            return;
        }
        SetVolume(100);                                        // 검사는 늘 100 에서 — 사람이 남긴 설정이 소리 검사(RMS)에 섞이지 않게
        if (only == "" || only == "intro")
            StartCoroutine(CheckIntro());
        else
            SceneManager.LoadScene(only == "booth" || only == "repair" || only == "art" || only == "ore" || only == "hudfit" || only == "sizes" || only == "glare" || only == "tour" || only == "fabtest" || only == "fabvideo" || only == "fabtuner" || only == "map4" ? Tuning.BOOTH_SCENE : "M1_Tunnel");   // 한 구간만: 부스 검사는 부스 맵, 나머지는 복도
    }

    void Update()
    {
        t += Time.deltaTime;
        Animate();
        var kb = Keyboard.current;
        var mouse = Mouse.current;
        bool click = mouse != null && mouse.leftButton.wasPressedThisFrame;
        bool tuned = kb != null && Tune(kb);
        bool any = ((kb != null && kb.anyKey.wasPressedThisFrame) || click) && !tuned;
        if (!menu)
        {
            if (t >= minLogoS && (any || t >= Tuning.INTRO_LOGO_AUTO_S))
                ShowMenu();
            return;
        }
        if (kb == null)
            return;
        if (kb.downArrowKey.wasPressedThisFrame || kb.sKey.wasPressedThisFrame) { sel = (sel + 1) % items.Length; Refresh(); }
        if (kb.upArrowKey.wasPressedThisFrame || kb.wKey.wasPressedThisFrame) { sel = (sel + items.Length - 1) % items.Length; Refresh(); }
        if (sel == VolumeItem)
        {
            int d = (kb.rightArrowKey.wasPressedThisFrame || kb.dKey.wasPressedThisFrame ? 1 : 0) - (kb.leftArrowKey.wasPressedThisFrame || kb.aKey.wasPressedThisFrame ? 1 : 0);
            if (d != 0) SetVolume(Volume + d * Tuning.INTRO_VOLUME_STEP);
        }
        if (!(kb.enterKey.wasPressedThisFrame || kb.spaceKey.wasPressedThisFrame || click))
            return;
        if (sel == 0) StartGame();
        else if (sel == 2) Application.Quit();
    }

    // 간판 흔들림(윗변에서 좌우로 비틀림 + 앞뒤로 절반, 주기를 어긋나게) · 머리 램프 끄덕임 · 먼 램프 떨림 · "아무 키나" 숨쉬기
    void Animate()
    {
        const float Tau = Mathf.PI * 2f;
        sign.localRotation = signRest * Quaternion.Euler(swayDeg * 0.5f * Mathf.Sin(Tau * t / (Tuning.INTRO_SIGN_SWAY_S * 1.4f)), swayDeg * Mathf.Sin(Tau * t / Tuning.INTRO_SIGN_SWAY_S), 0f);
        lamp.transform.localRotation = Quaternion.Euler(Tuning.INTRO_LAMP_NOD_DEG * Mathf.Sin(Tau * t / Tuning.INTRO_LAMP_NOD_S), 0f, 0f);
        farLamp.intensity = Tuning.INTRO_FAR_LAMP_ENERGY * (1f + Tuning.INTRO_FAR_LAMP_FLICKER * (Mathf.PerlinNoise(t * 1.7f, 0.3f) * 2f - 1f));
        var c = prompt.color;
        c.a = 0.45f + 0.55f * (0.5f + 0.5f * Mathf.Cos(Tau * t / Tuning.INTRO_PROMPT_PULSE_S));
        prompt.color = c;
    }

    // 판정 키 (숫자패드 없음): F1 값 한 줄 · [ ] 간판 밝기 ÷×1.1 · ; ' 흔들림 ∓0.2°. 눌렀으면 true
    bool Tune(Keyboard kb)
    {
        bool f1 = kb.f1Key.wasPressedThisFrame, dn = kb.leftBracketKey.wasPressedThisFrame, up = kb.rightBracketKey.wasPressedThisFrame,
             less = kb.semicolonKey.wasPressedThisFrame, more = kb.quoteKey.wasPressedThisFrame;
        if (f1) tuneLine.gameObject.SetActive(!tuneLine.gameObject.activeSelf);
        if (dn || up)
        {
            signBright = Mathf.Clamp(signBright * (up ? 1.1f : 1f / 1.1f), 0.01f, 1f);
            signRenderer.material.SetColor("_BaseColor", new Color(signBright, signBright, signBright, 1f));
        }
        if (less) swayDeg = Mathf.Max(0f, swayDeg - 0.2f);
        if (more) swayDeg += 0.2f;
        tuneLine.text = $"[ ] sign {signBright:0.000} (INTRO_SIGN_BRIGHT {Tuning.INTRO_SIGN_BRIGHT:0.000})     ; ' sway {swayDeg:0.0}° (INTRO_SIGN_SWAY_DEG {Tuning.INTRO_SIGN_SWAY_DEG:0.0})     [F1] hide";
        return f1 || dn || up || less || more;
    }

    void ShowMenu()
    {
        menu = true;
        logoPanel.SetActive(false);
        menuPanel.SetActive(true);
        Refresh();
    }

    void SetVolume(int v)
    {
        AudioListener.volume = Mathf.Clamp(v, 0, 100) / 100f;
        PlayerPrefs.SetFloat(VolumeKey, AudioListener.volume);
        Refresh();
    }

    void Refresh()
    {
        if (items == null || items.Length < 3) return;
        items[VolumeItem].text = $"소리 크기   ◀ {Volume} ▶";
        for (int i = 0; i < items.Length; i++)
            items[i].color = i == sel ? new Color32(236, 229, 212, 255) : new Color32(125, 118, 106, 255);
        underline.anchoredPosition = items[sel].rectTransform.anchoredPosition + new Vector2(0f, -30f);
        underline.sizeDelta = new Vector2(items[sel].preferredWidth, underline.sizeDelta.y);
    }

    void StartGame() => SceneManager.LoadScene(Tuning.BOOTH_SCENE);   // MAP1: 사람은 부스 맵으로 (42 m 복도 M1_Tunnel 은 검사용)

    // 검사 (지침 1-1): ① 0.5 s 에 로고만 보이고, 키를 눌러도 INTRO_LOGO_MIN_S 전엔 안 넘어간다 ② 그 뒤 키 → 메뉴 ③ 소리 크기 좌우 5칸 = 0.5 → 다시 1.0 ④ 시작 → 갱도(M1Check 가 이어서)
    IEnumerator CheckIntro()
    {
        var kb = InputSystem.AddDevice<Keyboard>("IntroKeyboard");
        while (t < 0.5f) yield return null;
        Snap("intro_logo");                                    // 10/2 제출 캡처 — build/Tunnel/check/ 에 남는다
        bool logoFirst = logoPanel.activeSelf && !menuPanel.activeSelf && !menu;
        yield return new WaitForEndOfFrame();
        var shot = ScreenCapture.CaptureScreenshotAsTexture();
        float ratio = SignLitRatio(shot, out string litDetail);
        Destroy(shot);
        M1Check.Check("intro_sign_lit", ratio >= Tuning.INTRO_SIGN_LIT_MIN, litDetail);
        M1Check.Check("intro_logos_keep_aspect", LogosKeepAspect(out string logoDetail), logoDetail);
        yield return Press(kb, Key.Space);
        yield return new WaitForSeconds(0.2f);
        M1Check.Check("intro_logo_holds_min_time", logoFirst && !menu, $"logo only at 0.5 s {logoFirst}; key at 0.5 s → menu {menu} at {t:F2} s (min {minLogoS:F1} s)");
        if (!menu)
        {
            while (t < Tuning.INTRO_LOGO_MIN_S + 0.1f) yield return null;
            yield return Press(kb, Key.Space);
        }
        M1Check.Check("intro_key_after_min_time_opens_menu", menu && menuPanel.activeSelf && !logoPanel.activeSelf, $"menu {menu}, menu panel {menuPanel.activeSelf}, logo panel {logoPanel.activeSelf} at {t:F2} s");
        Snap("intro_menu");
        yield return null;
        yield return Press(kb, Key.DownArrow);
        for (int i = 0; i < 5; i++) yield return Press(kb, Key.LeftArrow);
        float half = AudioListener.volume;
        for (int i = 0; i < 5; i++) yield return Press(kb, Key.RightArrow);
        M1Check.Check("intro_volume_setting_applies", sel == VolumeItem && Mathf.Approximately(half, 0.5f) && Mathf.Approximately(AudioListener.volume, 1f),
            $"selected {sel} (want {VolumeItem}), after 5 left {half:F2} (want 0.50), after 5 right {AudioListener.volume:F2} (want 1.00)");
        yield return Press(kb, Key.UpArrow);
        yield return Press(kb, Key.Enter);                     // 시작 → 부스 맵 (사람 길). 부스 검사 뒤 복도로 넘어간다
    }

    // 간판 자리(화면에 비친 판 네 귀퉁이의 안쪽 80 %) 평균 밝기 ÷ 그 밖 화면 평균 밝기 — 간판이 읽히게 비춰졌나
    float SignLitRatio(Texture2D shot, out string detail)
    {
        var cam = Camera.main;
        Vector2 lo = new Vector2(float.MaxValue, float.MaxValue), hi = -lo;
        foreach (var corner in new[] { new Vector3(-0.5f, -0.5f), new Vector3(0.5f, -0.5f), new Vector3(-0.5f, 0.5f), new Vector3(0.5f, 0.5f) })
        {
            Vector2 p = cam.WorldToScreenPoint(signRenderer.transform.TransformPoint(corner));
            lo = Vector2.Min(lo, p);
            hi = Vector2.Max(hi, p);
        }
        Vector2 pad = (hi - lo) * 0.1f;
        lo += pad;
        hi -= pad;
        float sx = shot.width / (float)Screen.width, sy = shot.height / (float)Screen.height;
        var px = shot.GetPixels32();
        double inSum = 0, outSum = 0;
        int inN = 0, outN = 0;
        for (int y = 0; y < shot.height; y += 2)
            for (int x = 0; x < shot.width; x += 2)
            {
                var c = px[y * shot.width + x];
                double l = (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255.0;
                if (x >= lo.x * sx && x <= hi.x * sx && y >= lo.y * sy && y <= hi.y * sy) { inSum += l; inN++; }
                else { outSum += l; outN++; }
            }
        float inMean = inN > 0 ? (float)(inSum / inN) : 0f, outMean = outN > 0 ? (float)(outSum / outN) : 0f;
        float ratio = inN == 0 ? 0f : inMean / Mathf.Max(outMean, 1e-4f);
        detail = $"sign mean {inMean:F3} (screen {lo.x:0}..{hi.x:0} x {lo.y:0}..{hi.y:0}, {inN} px) / rest {outMean:F3} = {ratio:F2} (want >= {Tuning.INTRO_SIGN_LIT_MIN:F2}), lamp {(lamp.enabled ? "on" : "off")}, sign bright {signBright:0.000}";
        return ratio;
    }

    // 로고 둘이 켜져 있고, 화면 안에 있고, 그려진 가로:세로가 그림 원본과 같다 (지침 1-1 "임의 변형 금지")
    bool LogosKeepAspect(out string detail)
    {
        bool ok = logos != null && logos.Length == 2;
        detail = "";
        var wc = new Vector3[4];
        foreach (var l in logos ?? new Image[0])
        {
            var rt = l.rectTransform;
            rt.GetWorldCorners(wc);                            // 화면 겹침 Canvas — 월드 좌표 = 화면 픽셀
            bool onScreen = wc.All(p => p.x >= 0f && p.y >= 0f && p.x <= Screen.width && p.y <= Screen.height);
            float original = l.sprite.rect.width / l.sprite.rect.height, box = rt.rect.width / rt.rect.height;
            float drawn = l.preserveAspect ? original : box;   // preserveAspect 면 칸 안에 원본 비율로 그린다
            bool keep = Mathf.Abs(drawn / original - 1f) < 0.01f;
            ok &= l.isActiveAndEnabled && onScreen && keep;
            detail += $"{l.name}: shown {l.isActiveAndEnabled}, on screen {onScreen}, drawn {drawn:F2} vs original {original:F2}; ";
        }
        return ok;
    }

    static void Snap(string name)
    {
        string dir = Path.Combine(Path.GetDirectoryName(Application.dataPath), "check");
        Directory.CreateDirectory(dir);
        ScreenCapture.CaptureScreenshot(Path.Combine(dir, name + ".png"));
    }

    static IEnumerator Press(Keyboard kb, Key key)
    {
        InputSystem.QueueStateEvent(kb, new KeyboardState(key));
        yield return new WaitForSeconds(0.05f);
        InputSystem.QueueStateEvent(kb, new KeyboardState());
        yield return null;
    }
}
