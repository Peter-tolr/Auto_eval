# -*- coding: utf-8 -*-
"""评教打分策略：整体高分，但不全满分、不全相同。"""
from __future__ import annotations

import random

# 选项序号 -> 分值（选项 A 最高）
OPTION_SCORES = {0: 5.0, 1: 4.0, 2: 3.0, 3: 2.0, 4: 1.0}


def plan(count: int, rng: random.Random, min_avg: float = 0.9) -> list[int]:
    """为 count 道单选题生成选项下标。

    规则：
      * 绝大多数选 A（完全符合）
      * 随机 1~2 道降一档为 B（符合），少量情况下再降一道为 C
      * 保证：不是全部同一项、平均分 >= min_avg*5
    """
    if count <= 0:
        return []
    idx = [0] * count
    demote = 1 if count <= 8 else 2
    if count >= 12 and rng.random() < 0.35:
        demote = 2
    positions = rng.sample(range(count), k=min(demote, count))
    for p in positions:
        idx[p] = 1
    # 偶尔再降一档，增加差异（但保证均值）
    if count >= 10 and rng.random() < 0.25:
        rest = [i for i in range(count) if i not in positions]
        if rest:
            idx[rng.choice(rest)] = 2
    # 校验：不允许全部相同
    if all(i == idx[0] for i in idx) and count > 1:
        idx[rng.randrange(count)] = 1
    avg = sum(OPTION_SCORES[i] for i in idx) / count / 5.0
    if avg < min_avg:
        # 回退到最保守方案：仅一道降档
        idx = [0] * count
        idx[rng.randrange(count)] = 1
    return idx
