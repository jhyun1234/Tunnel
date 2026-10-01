"""도구 시험용 본보기 (맵에는 안 쓴다): 받침 위 통 + 관 + 손잡이 바퀴 + 글자 판."""
import math
import bmesh
from _util import box, cyl, tube, torus, sweep, obj, text_mesh

def build(mats, label="시험"):
    out = []
    bm = bmesh.new(); box(bm, (0, 0, 0.1), (1.2, 0.6, 0.2)); out.append(obj("DEMO_BASE", bm, mats["concrete"]))
    bm = bmesh.new(); tube(bm, (-0.4, 0, 0.5), (0.4, 0, 0.5), 0.3, 0.27); box(bm, (0, 0, 0.21), (0.5, 0.3, 0.05)); out.append(obj("DEMO_DRUM", bm, mats["steel_paint"], smooth=True))
    bm = bmesh.new(); sweep(bm, [(0.4, 0, 0.5), (0.7, 0, 0.5), (0.8, 0, 0.6), (0.8, 0, 1.4)], 0.05); torus(bm, (0.8, -0.12, 1.0), (0, 1, 0), 0.12, 0.012); cyl(bm, (0.8, 0, 1.0), (0.8, -0.12, 1.0), 0.015)
    out.append(obj("DEMO_PIPE", bm, mats["rust"], smooth=True))
    bm = bmesh.new(); box(bm, (-0.3, -0.31, 0.5), (0.3, 0.01, 0.2)); out.append(obj("DEMO_PLATE", bm, mats["white"]))
    out.append(text_mesh("DEMO_TEXT", label, (-0.3, -0.318, 0.46), 0.09, mats["red"]))
    return out
