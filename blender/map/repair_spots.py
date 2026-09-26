"""고칠 곳 자리 규칙 (REP-1, 제안서 docs/제안서_REP1_고칠_곳.md, 승인 09-26). 표(굴 목록)를 받아 자리를 낸다.
Blender 안(make_booth.py — 부스 맵에 SLOT_Repair_<종류>_<번호>)과 평면도(map3_levels.py)가 같이 쓴다 — numpy · booth_table 만 (Blender 파이썬에 scipy·PIL 이 없다).
규칙(제안, 간격은 판정 뒤 조정): 전등 = 꺼진 전등(D) 굴 15 m 마다 · 배수관 30 m · 레일 40 m(운반갱도) · 갱목 40 m(그 밖의 갱목 굴) ·
  환기 = 막장 끝(face = 시작점, spur = 끝에서 3 m) · 공기 호스 = 비탈 막장 세로 굴 가운데 · 배전반 = hubs. 4 m 안에 겹치면 하나만."""
import math
import numpy as np
import booth_table as bt

KINDS = {"갱목": "timber", "레일": "rail", "배수관": "drain", "환기": "vent", "배전반": "panel", "공기 호스": "hose", "전등": "lamp"}   # Unity 노드 이름 (ASCII)
LETTER = {"갱목": "갱", "전등": "등", "배수관": "수", "환기": "환", "공기 호스": "공", "레일": "레", "배전반": "배"}              # 평면도 동그라미 글자
HAUL = ("main", "w_main", "e_main", "m2_hw", "m2_he", "w2_h", "e2_h", "uw_adit", "ue_adit", "ue_main")                     # 운반갱도 (배수관 · 레일)


def spots(T, hubs=(), lamps=True):
    """T = 표의 굴 목록, hubs = [((x, y), 바닥)] 배전반 자리. → [(종류, (x, y), 바닥)]"""
    out = []
    def add(kind, q, z):
        if all(math.dist(q, p) > 4.0 for _, p, _ in out): out.append((kind, (float(q[0]), float(q[1])), float(z)))
    for t in T:
        if t[6] != "tunnel" or not t[4] or t[1][0][3] > 10: continue       # 걷는 굴만 (큰 굴 = 폭 10 m 넘는 트인 곳은 뺀다)
        n, pts, lz, timber = t[0], t[1], t[5], t[3]; L = bt.seg_len(pts)
        def at(sp):
            q = tuple(bt.point_at(pts, sp)); return q, bt.proj(pts, q)[2]
        haul = n in HAUL or n.startswith(("w2_h", "m2_h"))
        if "face" in n:
            add("환기", *at(0.0)); continue
        if "spur" in n: add("환기", *at(max(L - 3.0, 0.0)))
        if lamps and lz == "D":
            for sp in np.arange(7.5, L, 15.0): add("전등", *at(sp))
        if haul:
            for sp in np.arange(12.0, L, 30.0): add("배수관", *at(sp))
            for sp in np.arange(27.0, L, 40.0): add("레일", *at(sp))
        elif timber and lz == "K":
            if any(k in n for k in ("_nb_c", "_ch_c", "_col")): add("공기 호스", *at(L / 2))
            for sp in np.arange(20.0, L, 40.0): add("갱목", *at(sp))
    for q, z in hubs: add("배전반", q, z)
    return out
