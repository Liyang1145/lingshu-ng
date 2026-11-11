"""大整数 float() 溢出须归为 ValueError / 默认值（对照上游 4e3e045）。"""
import pytest
from lingshu_ng import numeric, activation


def test_require_finite_huge_int_is_valueerror():
    with pytest.raises(ValueError):
        numeric.require_finite(10 ** 400, "x")


def test_clamp_conf_huge_int_default():
    assert activation._clamp_conf(10 ** 400) == activation.DEFAULT_CONFIDENCE
