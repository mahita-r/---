# -*- coding: utf-8 -*-
"""
wisaki_core.py
スタレゾ 威咲（イサキ）インフュージョン
1キャストEV計算コア
"""

import heapq
import time
import concurrent.futures as cf
from dataclasses import dataclass
from itertools import combinations
from typing import List, Tuple, Dict


BASE = {"crit": 0.05, "luck": 0.05, "dex": 0.06, "omni": 0.04}
DEN_4457 = 4457.0
DEN_OMNI = 2500.0

DMG_UP_COMMON = 0.20 + 0.20

SLOTS_ARMOR = ["head", "body", "arm", "leg", "ear", "neck", "ring", "L", "R", "charm"]
SLOTS_RAID_ELIGIBLE = ["head", "body", "arm", "leg", "L", "R"]

EVO_MAIN = 200
EVO_SUB = 100
REFORGE = 60
GEM = 50
DUNGEON_SLOT_TOTAL = EVO_MAIN + EVO_SUB + REFORGE + GEM

STATS_EVO = ["crit", "luck", "dex", "omni"]
STATS_GEM = ["crit", "luck", "dex"]


@dataclass(frozen=True)
class Breakdown:
    case: str
    ev_heal: float
    dmg_normal: float
    dmg_luck: float
    dmg_pass: float
    dmg_total: float
    r: float
    crit: int
    luck: int
    dex: int
    omni: int
    crit_pct: float
    luck_pct: float
    dex_pct: float
    omni_pct: float
    dmg_up: float
    weapon_desc: str
    raid_armor_slots: Tuple[str, ...]


def pct_4457(x: float) -> float:
    return x / (x + DEN_4457) if x > 0 else 0.0


def pct_omni(x: float) -> float:
    return x / (x + DEN_OMNI) if x > 0 else 0.0


def stats_percent(c: int, l: int, d: int, o: int) -> Dict[str, float]:
    return {
        "crit": BASE["crit"] + pct_4457(c),
        "luck": BASE["luck"] + pct_4457(l),
        "dex": BASE["dex"] + pct_4457(d),
        "omni": BASE["omni"] + pct_omni(o),
    }


def convert_rate(dex_pct: float, has_raid_armor: bool, raid_armor_bonus_r: float) -> float:
    base = 0.47 + (raid_armor_bonus_r if has_raid_armor else 0.0)
    return base + dex_pct / 5.0


def calc_expected(
    case: str,
    ma_base: float,
    refine: float,
    elem: float,
    hits: int,
    mult: float,
    flat: float,
    def_coef: float,
    muksuka_atk_up: float,
    unity: float,
    crit_dmg: float,
    luck_a: float,
    luck_b: float,
    luck_mult: float,
    passive_mult: float,
    passive_has_dex_mult: bool,
    dmg_up: float,
    c: int,
    l: int,
    d: int,
    o: int,
    weapon_desc: str,
    raid_slots: Tuple[str, ...],
    raid_armor_bonus_r: float,
) -> Breakdown:
    p = stats_percent(c, l, d, o)
    pcrit, pluck, pdex, pomni = p["crit"], p["luck"], p["dex"], p["omni"]

    ma_used = ma_base * (1.0 + muksuka_atk_up)

    up = 1.0 + dmg_up
    unity_mult = 1.0 + unity
    dex_mult = 1.0 + 0.7 * pdex
    omni_mult = 1.0 + 0.35 * pomni

    ecrit = hits * pcrit
    eluck = hits * pluck
    eluckcrit = eluck * pcrit

    x = ma_used * def_coef + refine + elem

    base_normal = (x * mult + flat) * up * dex_mult * omni_mult * unity_mult
    dmg_normal = base_normal * (hits + crit_dmg * ecrit)

    base_luck = (ma_used + refine + elem) * (luck_a + luck_b * pluck) * luck_mult
    base_luck *= up * dex_mult * omni_mult * unity_mult
    dmg_luck = base_luck * (eluck + crit_dmg * eluckcrit)

    base_pass = (ma_used * def_coef + refine) * passive_mult
    base_pass *= up * omni_mult * unity_mult
    if passive_has_dex_mult:
        base_pass *= dex_mult
    dmg_pass = base_pass * (eluck + crit_dmg * eluckcrit)

    dmg_total = dmg_normal + dmg_luck + dmg_pass
    r = convert_rate(pdex, has_raid_armor=(len(raid_slots) > 0), raid_armor_bonus_r=raid_armor_bonus_r)
    ev = dmg_total * r

    return Breakdown(
        case=case,
        ev_heal=ev,
        dmg_normal=dmg_normal,
        dmg_luck=dmg_luck,
        dmg_pass=dmg_pass,
        dmg_total=dmg_total,
        r=r,
        crit=c,
        luck=l,
        dex=d,
        omni=o,
        crit_pct=pcrit,
        luck_pct=pluck,
        dex_pct=pdex,
        omni_pct=pomni,
        dmg_up=dmg_up,
        weapon_desc=weapon_desc,
        raid_armor_slots=raid_slots,
    )


def armor_total_pts(raid_slots: Tuple[str, ...], raid_fixed_dex: int, raid_fixed_luck: int) -> int:
    raid_count = len(raid_slots)
    return (len(SLOTS_ARMOR) - raid_count) * DUNGEON_SLOT_TOTAL + raid_count * (raid_fixed_dex + raid_fixed_luck + REFORGE + GEM)


def enumerate_armor_totals(total_pts: int, step: int = 50) -> List[Tuple[int, int, int]]:
    out = []
    for c in range(0, total_pts + 1, step):
        for l in range(0, total_pts - c + 1, step):
            for d in range(0, total_pts - c - l + 1, step):
                out.append((c, l, d))
    return out


def weapon_list(case: str, raid_weapon_bonus: int) -> List[Tuple[int, int, int, int, float, str]]:
    out = []

    def add(c, l, d, o, up, desc):
        out.append((c, l, d, o, up, desc))

    if case in ("1-1", "2-1"):
        up = DMG_UP_COMMON + raid_weapon_bonus
        base_dex, base_luck = 306, 306
        for gem in STATS_GEM:
            c = 50 if gem == "crit" else 0
            l = base_luck + (50 if gem == "luck" else 0)
            d = base_dex + (50 if gem == "dex" else 0)
            add(c, l, d, 0, up, f"raid70 fixed(DEX306/LUCK306) gem={gem}50")

    elif case in ("1-3", "2-3"):
        up = DMG_UP_COMMON + raid_weapon_bonus
        base_dex, base_luck = 384, 384
        for gem in STATS_GEM:
            c = 50 if gem == "crit" else 0
            l = base_luck + (50 if gem == "luck" else 0)
            d = base_dex + (50 if gem == "dex" else 0)
            add(c, l, d, 0, up, f"raid90 fixed(DEX384/LUCK384) gem={gem}50")

    elif case in ("1-2", "2-2"):
        up = DMG_UP_COMMON
        for main in STATS_EVO:
            for sub in STATS_EVO:
                if sub == main:
                    continue
                for ref in STATS_EVO:
                    for gem in STATS_GEM:
                        c = l = d = 0
                        total = 400 + 200 + 120 + 50
                        for st, amt in [(main, 400), (sub, 200), (ref, 120), (gem, 50)]:
                            if st == "crit":
                                c += amt
                            elif st == "luck":
                                l += amt
                            elif st == "dex":
                                d += amt
                        o = total - (c + l + d)
                        add(c, l, d, o, up, f"gold80 {main}400/{sub}200 ref={ref}120 gem={gem}50")
    else:
        raise ValueError(case)

    return out


def _worker(payload):
    (
        case,
        raid_slots,
        chunk,
        params,
        k,
    ) = payload

    heap = []
    tie = 0

    weapons = weapon_list(case, params["raid_weapon_bonus"])
    total_pts = armor_total_pts(raid_slots, params["raid_fixed_dex"], params["raid_fixed_luck"])

    for ac, al, ad in chunk:
        ao = total_pts - (ac + al + ad)
        for wc, wl, wd, wo, dmg, desc in weapons:
            c = ac + wc
            l = al + wl
            d = ad + wd
            o = ao + wo

            bd = calc_expected(
                case=case,
                ma_base=params["ma_base"],
                refine=params["refine"],
                elem=params["elem"],
                hits=params["hits"],
                mult=params["mult"],
                flat=params["flat"],
                def_coef=params["def_coef"],
                muksuka_atk_up=params["muksuka_atk_up"],
                unity=params["unity"],
                crit_dmg=params["crit_dmg"],
                luck_a=params["luck_a"],
                luck_b=params["luck_b"],
                luck_mult=params["luck_mult"],
                passive_mult=params["passive_mult"],
                passive_has_dex_mult=params["passive_has_dex_mult"],
                dmg_up=dmg,
                c=c,
                l=l,
                d=d,
                o=o,
                weapon_desc=desc,
                raid_slots=raid_slots,
                raid_armor_bonus_r=params["raid_armor_bonus_r"],
            )

            tie += 1
            item = (bd.ev_heal, tie, bd)
            if len(heap) < k:
                heapq.heappush(heap, item)
            else:
                if item[0] > heap[0][0]:
                    heapq.heapreplace(heap, item)

    return heap


def solve_cases(
    cases: List[str],
    params: Dict,
    k: int = 3,
    workers: int = 6,
    chunk_size: int = 20000,
    step: int = 50,
    progress_cb=None,
) -> Dict[str, List[Breakdown]]:
    raid_combos = list(combinations(SLOTS_RAID_ELIGIBLE, 4))
    results: Dict[str, List[Breakdown]] = {}

    for case in cases:
        merged = []
        merged_tie = 0
        start = time.time()

        if case.startswith("1-"):
            raid_slots_list = [tuple()]
        else:
            raid_slots_list = [tuple(c) for c in raid_combos]

        for raid_slots in raid_slots_list:
            total_pts = armor_total_pts(raid_slots, params["raid_fixed_dex"], params["raid_fixed_luck"])
            armor = enumerate_armor_totals(total_pts, step=step)
            total = len(armor)
            chunks = [armor[i:i + chunk_size] for i in range(0, total, chunk_size)]
            done = 0

            with cf.ProcessPoolExecutor(max_workers=workers) as ex:
                future_to_len = {}
                for ch in chunks:
                    fut = ex.submit(_worker, (case, raid_slots, ch, params, k))
                    future_to_len[fut] = len(ch)

                for fut in cf.as_completed(future_to_len):
                    part = fut.result()
                    for ev, _, bd in part:
                        merged_tie += 1
                        item = (ev, merged_tie, bd)
                        if len(merged) < k:
                            heapq.heappush(merged, item)
                        else:
                            if item[0] > merged[0][0]:
                                heapq.heapreplace(merged, item)

                    done += future_to_len[fut]
                    elapsed = time.time() - start
                    rate = done / elapsed if elapsed > 0 else 0.0
                    eta = (total - done) / rate if rate > 0 else 0.0
                    if progress_cb:
                        progress_cb(case, done, total, eta)

        merged.sort(key=lambda x: x[0], reverse=True)
        results[case] = [bd for _, __, bd in merged]

    return results