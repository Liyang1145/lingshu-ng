# -*- coding: utf-8 -*-
"""sec-r1：四次方回溯正则（regexploit 检出、实测 400 个空白 ≈ 8.5 s）改占有量词后：
(1) 与旧式逐例结果完全相同（差分随机测试）；(2) 长空白输入线性完成。"""
import pathlib
import random
import re
import time

from lingshu_ng.chain import sav, v17

ROOT = pathlib.Path(__file__).resolve().parents[1]
OLD_SUFJ = (r"^\s*(?:的|之)?\s*(?:现在|当前|目前|如今|今天|最新|最近|这边|那边|这块儿?|这里|整个人|所在|所|的所在|现在的|当前所|"
            r"当前的|本人|自己|他|她|它)*\s*(?:的|之)?\s*$")
OLD_TAIL = r"\s*了?\s*(?:[（(][^（）()]*[）)])?\s*$"
OLD_GEN = r"\s*(area)?\s*,?\s*(plain)?\s*$"
NEW_GEN = r"\s*+(area)?\s*+,?\s*+(plain)?\s*+$"


def _rand(alpha, rng, n=12):
    return "".join(rng.choice(alpha) for _ in range(rng.randint(0, n)))


def test_sufj_equivalent_and_linear():
    rng = random.Random(7)
    alpha = [" ", "\t", "的", "之", "现在", "当前", "这块", "儿", "所在", "所", "他", "x", "0", "现在的"]
    old = re.compile(OLD_SUFJ)
    for _ in range(20000):
        s = _rand(alpha, rng)
        assert bool(old.match(s)) == bool(v17._SUFJ.match(s)), repr(s)
    t = time.perf_counter()
    assert v17._SUFJ.match(" " * 5000 + "0") is None
    assert time.perf_counter() - t < 0.5


def test_value_tail_equivalent_and_linear():
    rng = random.Random(11)
    alpha = [" ", "了", "(", ")", "（", "）", "a", "值", "0", "  "]
    for _ in range(20000):
        s = _rand(alpha, rng)
        assert re.sub(OLD_TAIL, "", s) == re.sub(sav._VALUE_TAIL, "", s), repr(s)
    t = time.perf_counter()
    re.sub(sav._VALUE_TAIL, "", " " * 5000 + "0")
    assert time.perf_counter() - t < 0.5


def test_gen_zone_tail_equivalent_and_linear():
    src = (ROOT / "plugins/lingshu-ng-gen/src/lingshu_ng_gen/multi_seed.py").read_text(encoding="utf-8")
    assert NEW_GEN in src and OLD_GEN not in src
    rng = random.Random(3)
    alpha = [" ", "area", "plain", ",", "a", "x", "  "]
    for _ in range(20000):
        s = _rand(alpha, rng, 8)
        assert re.sub(OLD_GEN, "", s) == re.sub(NEW_GEN, "", s), repr(s)
    t = time.perf_counter()
    re.sub(NEW_GEN, "", " " * 5000 + "0")
    assert time.perf_counter() - t < 0.5
