# -*- coding: utf-8 -*-
"""
moriyu_core.py
スタレゾ 森癒型（癒合流）回復計算コア
"""

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class MoriyuResult:
    fast_battle: float
    regen_count_10s: int
    total_ticks_10s: int
    int_conv: float
    ma_main: float
    magic_atk: float
    heal_tick: float
    heal_10s: float


def solve_moriyu(params: dict) -> MoriyuResult:
    int_stat = params["int_stat"]
    int_buff_total = params["int_buff_total"]
    weapon_ma = params["weapon_ma"]
    module_ma = params["module_ma"]
    ma_buff = params["ma_buff"]
    refine = params["refine"]
    elem = params["elem"]

    fast_display = params["fast_display"]
    heal_power_pct = params["heal_power_pct"]
    heal_effect_pct = params["heal_effect_pct"]
    omni_pct = params["omni_pct"]
    crit_pct = params["crit_pct"]

    fast_battle = fast_display + 0.10
    regen_count_10s = 10 + ceil(fast_battle / 0.10)
    total_ticks_10s = regen_count_10s * 5

    int_conv = int_stat * (1.0 + int_buff_total) * 0.6
    ma_main = (int_conv + weapon_ma + module_ma) * (1.0 + ma_buff)
    magic_atk = ma_main + refine + elem

    heal_tick = (0.35 * magic_atk + 100.0) * (1.0 + heal_power_pct + heal_effect_pct) * (1.0 + 0.35 * omni_pct) * (1.0 + 0.5 * crit_pct)
    heal_10s = heal_tick * total_ticks_10s

    return MoriyuResult(
        fast_battle=fast_battle,
        regen_count_10s=regen_count_10s,
        total_ticks_10s=total_ticks_10s,
        int_conv=int_conv,
        ma_main=ma_main,
        magic_atk=magic_atk,
        heal_tick=heal_tick,
        heal_10s=heal_10s,
    )