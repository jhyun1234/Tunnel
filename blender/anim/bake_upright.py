"""서서 오는 괴물 클립 셋을 굽는다 — up_walk · up_stand · up_run (제안서 3D-④ 5b, 영상 UP_U4 통과 2026-09-19).
혼자 돌지 않는다: walk_knuckle.py 가 걸음들을 구운 뒤 exec 로 부른다(그쪽의 pb·M·upd·rotate_world·reset_pose·check·acts·fb·FINGERS·curl_sign 을 쓴다).
빨리 이것만: QUICK=1 ONLY=none blender -b --factory-startup -P blender/anim/walk_knuckle.py
밑그림 = Mixamo "Mutant Walking"·"Mutant Run"(원본 FBX 는 저장소 밖 Documents/MineTunnel/blender/mixamo — GLB 에는 구운 클립만 든다).
얹는 값은 영상 스크립트 preview_upright.py 의 통과값과 같다(그쪽을 바꾸면 여기도). 머리 돌리기·상체 따라가기·손가락·턱·굳음은 클립이 아니라 Unity 가 얹는다.
사보타주: SABOTAGE=nolayer -> 덧칠 없이 원래 모션캡처를 굽는다 (검사 "엉덩이 낮춤"·"팔 흔들림 죽임"·"손이 앞에" FAIL) — U2 영상 버그의 클립판"""
UP_MIX = os.path.join(MT, "blender", "mixamo")
UP_HUNCH, UP_CROUCH, UP_ARM_STILL, UP_DIP = 42.0, 0.16, 0.85, 0.05
UP_LAYER = SABOTAGE != "nolayer"
UP_ARMS = [s + b for s in ("Left", "Right") for b in ("Shoulder", "Arm", "ForeArm", "Hand")]

def up_fcurves(act):
    return [fc for layer in act.layers for strip in layer.strips for cb in strip.channelbags for fc in cb.fcurves]
def up_use(act, f):
    ad.action = act
    if hasattr(ad, "action_slot") and act.slots:
        ad.action_slot = act.slots[0]
    scene.frame_set(int(f), subframe=f - int(f)); upd()
def up_load(stem):
    """FBX 의 동작만, 제자리 걸음으로(엉덩이의 곧은 흐름을 뺀다). 돌려주는 것: 동작 · 원래 빠르기(모델 m/s) · 팔 뼈의 평균 자세"""
    before_o, before_a = set(bpy.data.objects), set(bpy.data.actions)
    bpy.context.view_layer.objects.active = arm             # 걸음 그림을 찍고 나면 활성 물체가 비어 있다
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.import_scene.fbx(filepath=os.path.join(UP_MIX, stem + ".fbx"))
    act = next(a for a in bpy.data.actions if a not in before_a)
    for o in [o for o in bpy.data.objects if o not in before_o]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True); bpy.ops.object.mode_set(mode="POSE")
    f0, f1 = act.frame_range
    up_use(act, f0); p0 = whead("Hips").copy()
    up_use(act, f1); p1 = whead("Hips").copy()
    for fc in up_fcurves(act):
        if fc.data_path.endswith('["%sHips"].location' % P) and len(fc.keyframe_points) > 1:
            k0, k1 = fc.keyframe_points[0], fc.keyframe_points[-1]
            slope = (k1.co.y - k0.co.y) / max(k1.co.x - k0.co.x, 1e-6)
            for k in fc.keyframe_points:
                k.co.y -= slope * (k.co.x - k0.co.x)
            fc.update()
    mean = {}
    for f in range(int(f0), int(f1)):
        up_use(act, f)
        for n in UP_ARMS:
            q = pb(n).rotation_quaternion.copy()
            if n in mean and mean[n].dot(q) < 0: q.negate()
            mean[n] = q if n not in mean else Quaternion([a + b for a, b in zip(mean[n], q)])
    for n in mean: mean[n].normalize()
    return act, math.hypot(p1.x - p0.x, p1.y - p0.y) / ((f1 - f0) / FPS), mean

up_col = bpy.data.collections.new("up_rig"); scene.collection.children.link(up_col)
up_tg = {}
for s_ in ("Left", "Right"):                # 다리 IK: 발목은 원래 모션캡처 자리에 붙든 채 엉덩이만 낮춘다
    e = bpy.data.objects.new("up_tg_" + s_, None); e.rotation_mode = "QUATERNION"; up_col.objects.link(e); up_tg[s_] = e
    c = pb(s_ + "Leg").constraints.new("IK"); c.target = e; c.chain_count = 2; c.use_tail = True; c.name = "up_ik"
    c = pb(s_ + "Foot").constraints.new("COPY_ROTATION"); c.target = e; c.target_space = "WORLD"; c.owner_space = "WORLD"; c.name = "up_rot"
def up_legs(on):
    for s_ in ("Left", "Right"):
        pb(s_ + "Leg").constraints["up_ik"].influence = 1.0 if on else 0.0
        pb(s_ + "Foot").constraints["up_rot"].influence = 1.0 if on else 0.0
up_hips_axes = (M.to_3x3() @ pb("Hips").bone.matrix_local.to_3x3()).inverted()
up_order = [b for b in pbs if b.parent is None]
for b in up_order: up_order.extend(b.children)
def up_aim(bone, to, k):
    cur = wmat(bone).to_3x3().col[1].normalized()
    rotate_world(bone, Quaternion().slerp(cur.rotation_difference(Vector(to).normalized()), k).to_matrix().to_4x4())

def up_bake(name, src, mean, N, f_of, dip_of=None, life=0.0, run=False):
    """N 프레임 되풀이 클립. f_of(i) = 밑그림의 프레임, dip_of(i) = 발 디딤 내려앉음(m). 얹은 자세를 통째로 떠서 새 동작에 키로 박는다"""
    out = bpy.data.actions.new(name); out.use_fake_user = True
    for i in range(N + 1):
        k = i % N; t = k / FPS
        up_legs(False); up_use(src, f_of(k))
        for s_ in ("Left", "Right"):
            W = wmat(s_ + "Foot"); up_tg[s_].location = W.translation; up_tg[s_].rotation_quaternion = W.to_quaternion()
        if UP_LAYER:
            up_legs(True)
            w = 2 * math.pi / (N / FPS)                       # 되풀이가 이어지게 숨·무게·팔 박자는 클립 길이의 정수 배
            pb("Hips").location = pb("Hips").location + up_hips_axes @ Vector((0.015 * life * math.sin(2 * w * t), 0,
                                  -(UP_CROUCH + (dip_of(k) if dip_of else 0.0) + 0.010 * life * math.sin(3 * w * t))))
            for nm in UP_ARMS:
                pb(nm).rotation_quaternion = pb(nm).rotation_quaternion.slerp(mean[nm], UP_ARM_STILL)
            upd()
            for nm in ("Spine", "Spine1", "Spine2"):
                rotate_world(nm, Matrix.Rotation(math.radians(UP_HUNCH / 3), 4, "X"))
            rotate_world("Neck", Matrix.Rotation(math.radians(-UP_HUNCH * 0.45), 4, "X"))
            rotate_world("Head", Matrix.Rotation(math.radians(-UP_HUNCH * 0.45), 4, "X"))
            rotate_world("Spine1", Matrix.Rotation(math.radians(1.8 * life * math.sin(3 * w * t + 0.6)), 4, "X"))
            for j, s_ in enumerate(("Left", "Right")):
                if run:                                       # 두 팔로 잡겠다는 듯 앞으로 뻗고 벌림 — 모션캡처 펌프질은 20 % 만
                    sx = 1.0 if whead(s_ + "Arm").x > 0 else -1.0
                    up_aim(s_ + "Arm", (sx * 0.38, -1, -0.10), 0.8); up_aim(s_ + "ForeArm", (sx * 0.12, -1, 0.22), 0.8)
                    ax = wmat(s_ + "Hand").to_3x3().col[0]
                    for f_ in FINGERS:
                        for m_, a in enumerate((10, 28, 28)):
                            rotate_world(fb(s_, f_, m_ + 1), Matrix.Rotation(curl_sign[s_] * math.radians(a * (0.5 if f_ == "Thumb" else 1.0)), 4, ax))
                elif life:
                    rotate_world(s_ + "Arm", Matrix.Rotation(math.radians(7.0 * life * math.sin(3 * w * t + j * 2.1)), 4, "X"))
                    rotate_world(s_ + "ForeArm", Matrix.Rotation(math.radians(5.0 * life * math.sin(3 * w * t + j * 2.1 - 0.9)), 4, "X"))
        upd()
        mats = {b.name: b.matrix.copy() for b in up_order}     # IK 까지 계산된 결과
        ad.action = out
        if hasattr(ad, "action_slot") and out.slots:
            ad.action_slot = out.slots[0]
        up_legs(False)
        for b in up_order:
            rest = (mats[b.parent.name] @ b.parent.bone.matrix_local.inverted() @ b.bone.matrix_local) if b.parent else b.bone.matrix_local
            b.matrix_basis = rest.inverted() @ mats[b.name]
            if b.name != P + "Hips": b.location = (0, 0, 0)
            b.scale = (1, 1, 1)
            b.keyframe_insert("rotation_quaternion", frame=i)
        pb("Hips").keyframe_insert("location", frame=i)
    acts[name] = (out, N)
    print("baked", name, N)

def up_measure(act, N):
    """엉덩이 평균 높이 · 손이 가슴에서 앞뒤로 오가는 폭 · 손이 가슴보다 앞선 평균 거리(-Y 가 앞) · 처음과 끝 자세 차이(도)"""
    hz, rel, first, last = [], [], None, None
    for i in range(N + 1):
        up_use(act, i)
        hz.append(whead("Hips").z)
        rel.append(sum((whead(s_ + "Hand").y - whead("Spine2").y) for s_ in ("Left", "Right")) / 2)
        q = {b.name: b.matrix.to_quaternion() for b in pbs}
        if i == 0: first = q
        last = q
    seam = max(math.degrees(first[n].rotation_difference(last[n]).angle) for n in first)
    return sum(hz) / len(hz), max(rel) - min(rel), -sum(rel) / len(rel), seam

up_walk_src, up_v_walk, up_mean_walk = up_load("Mutant Walking")
up_run_src, up_v_run, up_mean_run = up_load("Mutant Run")
wl = up_walk_src.frame_range[1] - up_walk_src.frame_range[0]; rl = up_run_src.frame_range[1] - up_run_src.frame_range[0]
UP_WALK_N, UP_RUN_N, UP_JOG_N = 60, 19, 24  # 걸음 0.72배 느리게(43 → 60 프레임) · 질주 1.39배 빠르게(26 → 19) · 달음질(조사 5.0 m/s)은 거의 그대로(26 → 24)
print("UPRIGHT clip speeds (game m/s): walk %.2f  run %.2f  jog %.2f" % (up_v_walk * wl / UP_WALK_N * 1.5, up_v_run * rl / UP_RUN_N * 1.5, up_v_run * rl / UP_JOG_N * 1.5))

# 발 디딤(발끝이 0.13 m 밑으로 내려오는 순간)마다 엉덩이가 두세 프레임에 걸쳐 내려앉는다 — 되풀이가 이어지게 두 바퀴 돌려 둘째 바퀴 값을 쓴다
dips, d, d_to, was = [0.0] * UP_WALK_N, 0.0, 0.0, [True, True]
for i in range(2 * UP_WALK_N):
    up_use(up_walk_src, up_walk_src.frame_range[0] + (i % UP_WALK_N) * wl / UP_WALK_N)
    for j, s_ in enumerate(("Left", "Right")):
        up = whead(s_ + "ToeBase").z > 0.13
        if was[j] and not up: d_to = UP_DIP
        was[j] = up
    d += (d_to - d) * 0.5; d_to *= 0.55; dips[i % UP_WALK_N] = d

NAME = "up_walk"
up_bake(NAME, up_walk_src, up_mean_walk, UP_WALK_N, lambda k: up_walk_src.frame_range[0] + k * wl / UP_WALK_N, dip_of=lambda k: dips[k])
raw = up_measure(up_walk_src, int(wl)); got = up_measure(acts[NAME][0], UP_WALK_N)
check(raw[0] - got[0] >= 0.12, "엉덩이 낮춤 %.3f m (원래 모션캡처보다 ≥ 0.12)" % (raw[0] - got[0]))
check(got[1] <= 0.5 * raw[1], "팔 흔들림 죽임: 손이 앞뒤로 오가는 폭 %.3f m ≤ 원래 %.3f 의 50 %% (09-19 실측 41 %% — 어깨·몸통 흔들림이 남는다)" % (got[1], raw[1]))
check(got[3] < 2.0, "되풀이 이음매 %.2f° (< 2)" % got[3])
NAME = "up_stand"                           # 걷다 만 자세(두 발이 다 땅에 있는 프레임)로 서서: 숨 · 무게 옮기기 · 팔 앞뒤. 10 s 되풀이
stand_f = up_walk_src.frame_range[0] + min(range(int(wl)), key=lambda k: (up_use(up_walk_src, up_walk_src.frame_range[0] + k), max(whead("LeftToeBase").z, whead("RightToeBase").z))[1])
up_bake(NAME, up_walk_src, up_mean_walk, 300, lambda k: stand_f, life=1.0)
got = up_measure(acts[NAME][0], 300)
check(0.02 <= got[1] <= 0.30, "서 있을 때 팔이 앞뒤로 움직임 %.3f m (0.02 ~ 0.30)" % got[1])
check(got[3] < 2.0, "되풀이 이음매 %.2f° (< 2)" % got[3])
NAME = "up_run"
up_bake(NAME, up_run_src, up_mean_run, UP_RUN_N, lambda k: up_run_src.frame_range[0] + k * rl / UP_RUN_N, run=True)
got = up_measure(acts[NAME][0], UP_RUN_N)
check(got[2] >= 0.27, "질주: 두 손이 가슴보다 앞 %.3f m (≥ 0.27 = 게임 0.4)" % got[2])
check(got[3] < 2.0, "되풀이 이음매 %.2f° (< 2)" % got[3])
NAME = "up_jog"                             # 팔을 안 뻗는 달리기: 소리 조사·철수 — 잡으러 오는 게 아닐 때 (철수 때 뻗은 팔이 벽을 뚫었다, 09-19 게임 검사)
up_bake(NAME, up_run_src, up_mean_run, UP_JOG_N, lambda k: up_run_src.frame_range[0] + k * rl / UP_JOG_N)
jog = up_measure(acts[NAME][0], UP_JOG_N)
check(jog[2] <= got[2] - 0.3, "달음질: 두 손이 가슴보다 앞 %.3f m — 질주 %.3f 보다 0.3 넘게 뒤" % (jog[2], got[2]))
check(jog[3] < 2.0, "되풀이 이음매 %.2f° (< 2)" % jog[3])
# ---- up_grope (3D-④ MB, 영상 B4 통과 2026-09-20): 수색 자리에서 깊이 웅크려 바닥·벽을 짚을 때의 몸. 다리 = 걷다 만 선 자세, 허리 위 = 모션캡처 "Creeping Zombie Walk"(두 팔을 앞으로 뻗고 더듬듯 걷는 연기)를
# 0.4배쯤으로·빠르기를 고르지 않게. 값은 preview_upright.py 의 통과값(LOW: 숙임 +52° · 웅크림 0.70 · 우리 숙임 35 % 덜기 · 고개 22°). 손 짚기·엉덩이 실기·"들었나?"는 클립이 아니라 Unity 가 얹는다.
NAME = "up_grope"
UP_GROPE_N, UP_G_LEAN, UP_G_SQUAT, UP_G_CUT, UP_G_PITCH = 300, 52.0, 0.70, 0.35, 22.0
up_grope_src, _, _ = up_load("Creeping Zombie Walk")
g0 = up_grope_src.frame_range[0]; gl = up_grope_src.frame_range[1] - g0
up_upper = set(pb("Spine").children_recursive) | {pb("Spine")}
def up_bake_grope(name, N):
    out = bpy.data.actions.new(name); out.use_fake_user = True
    hunch = (UP_HUNCH * (1 - UP_G_CUT) + UP_G_LEAN) if UP_LAYER else 0.0
    for i in range(N + 1):
        u = (i % N) / N; t = u * N / FPS; w = 2 * math.pi / (N / FPS)
        up_legs(False); up_use(up_walk_src, stand_f)
        A = {b.name: (b.rotation_quaternion.copy(), b.location.copy()) for b in up_order}
        for s_ in ("Left", "Right"):
            W = wmat(s_ + "Foot"); up_tg[s_].location = W.translation; up_tg[s_].rotation_quaternion = W.to_quaternion()
        up_use(up_grope_src, g0 + gl * (u + 0.55 * math.sin(6 * math.pi * u) / (6 * math.pi) + 0.25 * math.sin(14 * math.pi * u) / (14 * math.pi)))    # 빠르기 0.2~1.8배를 오가되 되풀이가 이어지게 (한 바퀴에 3번·7번)
        for b in up_order:
            if b not in up_upper: b.rotation_quaternion, b.location = A[b.name]
        upd()
        if UP_LAYER:
            up_legs(True)
            pb("Hips").location = pb("Hips").location + up_hips_axes @ Vector((0.015 * math.sin(2 * w * t), 0.35 * UP_G_SQUAT, -(UP_CROUCH + UP_G_SQUAT + 0.010 * math.sin(3 * w * t))))
            upd()
            for nm in ("Spine", "Spine1", "Spine2"):
                rotate_world(nm, Matrix.Rotation(math.radians(hunch / 3), 4, "X"))
            rotate_world("Neck", Matrix.Rotation(math.radians(-hunch * 0.45 + UP_G_PITCH * 0.4), 4, "X"))
            rotate_world("Head", Matrix.Rotation(math.radians(-hunch * 0.45 + UP_G_PITCH * 0.6), 4, "X"))
        upd()
        mats = {b.name: b.matrix.copy() for b in up_order}
        ad.action = out
        if hasattr(ad, "action_slot") and out.slots:
            ad.action_slot = out.slots[0]
        up_legs(False)
        for b in up_order:
            rest = (mats[b.parent.name] @ b.parent.bone.matrix_local.inverted() @ b.bone.matrix_local) if b.parent else b.bone.matrix_local
            b.matrix_basis = rest.inverted() @ mats[b.name]
            if b.name != P + "Hips": b.location = (0, 0, 0)
            b.scale = (1, 1, 1)
            b.keyframe_insert("rotation_quaternion", frame=i)
        pb("Hips").keyframe_insert("location", frame=i)
    acts[name] = (out, N)
    print("baked", name, N)
up_bake_grope(NAME, UP_GROPE_N)
got = up_measure(acts[NAME][0], UP_GROPE_N)
sh_z = []
for i in range(0, UP_GROPE_N, 10):
    up_use(acts[NAME][0], i); sh_z.append(max(whead("LeftArm").z, whead("RightArm").z))
check(max(sh_z) <= 0.80, "웅크림: 높은 쪽 어깨 %.3f m ≤ 0.80 (팔 0.86 m 로 바닥에 닿으려면 — 서 있을 땐 1.5 쯤)" % max(sh_z))
check(got[2] >= 0.05, "웅크림: 두 손이 가슴보다 앞 %.3f m (≥ 0.05 — 가슴이 깊이 숙어 앞에 있다, 09-20 실측 0.115)" % got[2])
check(got[3] < 2.0, "되풀이 이음매 %.2f° (< 2)" % got[3])
bpy.data.actions.remove(up_grope_src)
NAME = ""

for s_ in ("Left", "Right"):
    pb(s_ + "Leg").constraints.remove(pb(s_ + "Leg").constraints["up_ik"]); pb(s_ + "Foot").constraints.remove(pb(s_ + "Foot").constraints["up_rot"])
for o in list(up_col.objects): bpy.data.objects.remove(o, do_unlink=True)
bpy.data.collections.remove(up_col)
bpy.data.actions.remove(up_walk_src); bpy.data.actions.remove(up_run_src)
ad.action = None; reset_pose()
bpy.ops.object.mode_set(mode="OBJECT")        # 내보내기(object.select_all)는 물체 모드에서 돈다
