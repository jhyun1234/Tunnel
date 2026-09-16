using UnityEngine;

// 소음 → 소리 한 곳 (설계서 sound_design.md "한 곳에서 튼다": 괴물 귀의 반경과 플레이어 귀의 음량이 같은 이벤트에서 나온다).
// NoiseBus.Made 의 종류 이름으로 파일·음량을 고른다.
// step = 2D(머리 안 — 발이 어디 있는지가 아니라 얼마나 시끄러운지만), 반경으로 자세를 안다. pick_land = 착지 자리 3D.
// pick(곡괭이 타격)은 MiningFx.HitSound 가 튼다(M2 판정 통과 코드) — 여기 표에 없다.
public class NoiseSound : MonoBehaviour
{
    public static NoiseSound I;

    public Player player;
    public AudioClip[] stepClips;      // 걷기·달리기: 흙 발소리 4변주
    public AudioClip[] crouchClips;    // 숙이기: 발 끄는 소리
    public AudioClip[] landClips;      // 던진 곡괭이 착지: 쇠붙이가 바닥에

    [System.NonSerialized] public bool flat;          // 사보타주 flatsteps: 자세 무관 같은 음량
    [System.NonSerialized] public int maxRepeat;      // 검사: 같은 발소리 파일이 연달아 난 최대 횟수 (0 = 한 번도 안 겹침)
    [System.NonSerialized] public string lastClip = "-";

    AudioSource self;                  // 2D, 자기 소리
    int lastIdx = -1, repeat;

    void Awake()
    {
        I = this;
        self = gameObject.AddComponent<AudioSource>();
        self.spatialBlend = 0f;
        self.playOnAwake = false;
    }

    void OnEnable() => NoiseBus.Made += OnNoise;
    void OnDisable() => NoiseBus.Made -= OnNoise;

    void OnNoise(Vector3 pos, float radius, string kind, object who)
    {
        if (!ReferenceEquals(who, player))
            return;
        if (kind == "step")
        {
            bool crouch = radius <= Tuning.NOISE_STEP_CROUCH;
            float vol = flat ? Tuning.STEP_VOLUME_RUN
                      : crouch ? Tuning.STEP_VOLUME_CROUCH
                      : radius <= Tuning.NOISE_STEP ? Tuning.STEP_VOLUME_WALK : Tuning.STEP_VOLUME_RUN;
            var clip = Pick(crouch ? crouchClips : stepClips);
            if (clip == null)
                return;
            self.pitch = 1f + Random.Range(-Tuning.STEP_PITCH_JITTER, Tuning.STEP_PITCH_JITTER);
            self.PlayOneShot(clip, vol);
        }
        else if (kind == "pick_land")
            Play3D(pos, Pick(landClips), Tuning.LAND_VOLUME, radius);
    }

    // 직전과 다른 변주를 고른다 — 같은 파일이 연달아 나면 기계 소리로 들린다
    AudioClip Pick(AudioClip[] clips)
    {
        if (clips == null || clips.Length == 0)
            return null;
        int i = Random.Range(0, clips.Length);
        if (clips.Length > 1 && i == lastIdx)
            i = (i + 1) % clips.Length;
        repeat = clips.Length > 1 && i == lastIdx ? repeat + 1 : 0;   // 변주가 하나뿐인 갈래(숙이기)는 겹침으로 안 센다
        maxRepeat = Mathf.Max(maxRepeat, repeat);
        lastIdx = i;
        lastClip = clips[i].name;
        return clips[i];
    }

    // 그 자리에서 나는 3D 소리. 반경 = 들리는 거리 (MiningFx.HitSound 와 같은 감쇠)
    public static void Play3D(Vector3 at, AudioClip clip, float volume, float radius)
    {
        if (clip == null)
            return;
        var go = new GameObject("NoiseSound3D");
        go.transform.position = at;
        var src = go.AddComponent<AudioSource>();
        src.clip = clip;
        src.spatialBlend = 1f;
        src.rolloffMode = AudioRolloffMode.Linear;
        src.minDistance = Tuning.HIT_MIN_DISTANCE;
        src.maxDistance = radius;
        src.volume = volume;
        src.Play();
        Destroy(go, clip.length + 0.1f);
    }
}
