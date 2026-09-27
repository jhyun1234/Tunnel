using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

// UI-2 인트로 (지스타 2026 운영지침 1-1 · 4-1, 제안서 UI-2). 검은 바탕에 대학·사업단 로고 + 팀명 + 게임명을 INTRO_LOGO_MIN_S 이상 보여 준 뒤
// (그 뒤 아무 키, 또는 INTRO_LOGO_AUTO_S 에 저절로) 시작 메뉴 — 시작 · 소리 크기 · 끝내기. 위아래(또는 W/S)로 고르고 Enter·Space·클릭, 소리 크기는 좌우(A/D).
// 소리 크기는 AudioListener.volume(전역)에 바로 넣고 PlayerPrefs 에 남긴다 — 세이브가 아니라 부스 설정. 잡히면 Stalker 가 이 씬을 다시 불러 처음으로 돌아온다.
// -check: 이 씬의 검사(로고 최소 시간 · 스킵 · 소리 크기)를 먼저 하고 "시작"으로 갱도 검사(M1Check)로 넘어간다. 잡힘 뒤 두 번째로 오면 마지막 검사를 적고 끝낸다.
public class Intro : MonoBehaviour
{
    public GameObject logoPanel, menuPanel;
    public Text[] items;                                       // 시작 · 소리 크기 · 끝내기
    public static bool expectReturn;                           // M1Check 가 잡힘을 일으키기 전에 켠다 — 다시 이 씬에 오면 통과
    public static float minLogoS = Tuning.INTRO_LOGO_MIN_S;    // 사보타주 skipearly 가 0 으로
    const string VolumeKey = "volume";
    const int VolumeItem = 1;
    float t;
    int sel;
    bool menu;
    string only = "";

    int Volume => Mathf.RoundToInt(AudioListener.volume * 100f);

    void Awake()
    {
        AudioListener.volume = PlayerPrefs.GetFloat(VolumeKey, 1f);
        Cursor.lockState = CursorLockMode.Locked;
        Cursor.visible = false;
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
        if (s >= 0 && s + 1 < args.Length && args[s + 1] == "skipearly") minLogoS = 0f;
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
            SceneManager.LoadScene(only == "booth" || only == "repair" || only == "art" || only == "ore" ? Tuning.BOOTH_SCENE : "M1_Tunnel");   // 한 구간만: 부스 검사는 부스 맵, 나머지는 복도
    }

    void Update()
    {
        t += Time.deltaTime;
        var kb = Keyboard.current;
        var mouse = Mouse.current;
        bool click = mouse != null && mouse.leftButton.wasPressedThisFrame;
        bool any = (kb != null && kb.anyKey.wasPressedThisFrame) || click;
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
            items[i].color = i == sel ? Color.white : new Color(0.45f, 0.45f, 0.45f);
    }

    void StartGame() => SceneManager.LoadScene(Tuning.BOOTH_SCENE);   // MAP1: 사람은 부스 맵으로 (42 m 복도 M1_Tunnel 은 검사용)

    // 검사 (지침 1-1): ① 0.5 s 에 로고만 보이고, 키를 눌러도 INTRO_LOGO_MIN_S 전엔 안 넘어간다 ② 그 뒤 키 → 메뉴 ③ 소리 크기 좌우 5칸 = 0.5 → 다시 1.0 ④ 시작 → 갱도(M1Check 가 이어서)
    IEnumerator CheckIntro()
    {
        var kb = InputSystem.AddDevice<Keyboard>("IntroKeyboard");
        while (t < 0.5f) yield return null;
        Snap("intro_logo");                                    // 10/2 제출 캡처 — build/Tunnel/check/ 에 남는다
        bool logoFirst = logoPanel.activeSelf && !menuPanel.activeSelf && !menu;
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
