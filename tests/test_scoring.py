# -*- coding: utf-8 -*-
"""打分策略单元测试：python -m unittest discover -s tests -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hlju import scoring


class TestPlan(unittest.TestCase):
    def test_length(self):
        for n in (0, 1, 5, 9, 11, 15, 17):
            self.assertEqual(len(scoring.plan(n, random.Random(1))), n)

    def test_not_all_same(self):
        for seed in range(200):
            idx = scoring.plan(15, random.Random(seed))
            self.assertGreater(len(set(idx)), 1, "seed=%d 全部选项相同" % seed)

    def test_not_all_max(self):
        for seed in range(200):
            idx = scoring.plan(11, random.Random(seed))
            self.assertTrue(any(i > 0 for i in idx), "seed=%d 全部满分" % seed)

    def test_never_lowest_options(self):
        for seed in range(200):
            idx = scoring.plan(17, random.Random(seed))
            self.assertLessEqual(max(idx), 2, "seed=%d 出现最低两档" % seed)

    def test_average_high(self):
        for seed in range(200):
            idx = scoring.plan(15, random.Random(seed))
            avg = sum(scoring.OPTION_SCORES[i] for i in idx) / len(idx) / 5.0
            self.assertGreaterEqual(avg, 0.9, "seed=%d 平均分过低" % seed)

    def test_variety_between_forms(self):
        plans = {tuple(scoring.plan(15, random.Random(s))) for s in range(30)}
        self.assertGreater(len(plans), 10, "不同问卷的打分过于雷同")


if __name__ == "__main__":
    unittest.main()
