# -*- coding: utf-8 -*-
import time
import streamlit as st
from wisaki_core import solve_cases
from moriyu_core import solve_moriyu

st.set_page_config(page_title="スタレゾ ビルド計算ツール", layout="wide")

st.title("スタレゾ ビルド計算ツール")
st.caption("森癒型（癒合流） / 威咲型（イサキ） スイッチ対応")

with st.sidebar:
    st.header("ビルド切替")
    build = st.radio("ビルド", ["威咲型（イサキ）", "森癒型（癒合流）"])

# =========================
# 威咲UI
# =========================
if build == "威咲型（イサキ）":
    with st.sidebar:
        st.header("威咲 入力")
        cases = st.multiselect("ケース", ["1-1", "1-2", "1-3", "2-1", "2-2", "2-3"], default=["1-1", "1-2", "1-3"])
        k = st.number_input("上位K件", min_value=1, max_value=50, value=3, step=1)
        workers = st.number_input("並列ワーカー数", min_value=1, max_value=64, value=6, step=1)
        chunk = st.number_input("chunkサイズ", min_value=1000, max_value=200000, value=20000, step=1000)
        step = st.selectbox("pt刻み", [50, 25, 10], index=0)

        st.subheader("スキル・係数")
        ma_base = st.number_input("MA_BASE", value=2167.0, step=1.0)
        refine = st.number_input("製錬攻", value=360.0, step=1.0)
        elem = st.number_input("属性攻", value=45.0, step=1.0)
        hits = st.number_input("hit数", value=46, step=1)
        mult = st.number_input("スキル倍率", value=0.63, step=0.01, format="%.4f")
        flat = st.number_input("スキル固定値", value=272.0, step=1.0)
        def_coef = st.number_input("防御係数", value=0.9198, step=0.0001, format="%.4f")

        st.subheader("補正")
        muksuka_atk_up = st.number_input("ムクスカ魔法攻上昇", value=0.15, step=0.01, format="%.4f")
        unity = st.number_input("団結", value=0.25, step=0.01, format="%.4f")
        crit_dmg = st.number_input("会心ダメージ補正", value=0.50, step=0.01, format="%.4f")
        luck_a = st.number_input("幸運一撃係数A", value=0.45, step=0.01, format="%.4f")
        luck_b = st.number_input("幸運一撃係数B", value=1.25, step=0.01, format="%.4f")
        luck_mult = st.number_input("幸運一撃倍率", value=1.5, step=0.1, format="%.4f")
        passive_mult = st.number_input("ギルミーパッシブ倍率", value=0.28, step=0.01, format="%.4f")
        passive_has_dex_mult = st.checkbox("パッシブにDEX倍率を乗せる", value=False)

        st.subheader("レイド関連")
        raid_weapon_bonus = st.number_input("レイド武器ダメUP加算", value=0.08, step=0.01, format="%.4f")
        raid_armor_bonus_r = st.number_input("レイド防具時のr加算", value=0.04, step=0.01, format="%.4f")
        raid_fixed_dex = st.number_input("レイド防具固定DEX", value=200, step=10)
        raid_fixed_luck = st.number_input("レイド防具固定LUCK", value=200, step=10)

        run = st.button("威咲を計算", type="primary")

    if run:
        params = {
            "ma_base": float(ma_base),
            "refine": float(refine),
            "elem": float(elem),
            "hits": int(hits),
            "mult": float(mult),
            "flat": float(flat),
            "def_coef": float(def_coef),
            "muksuka_atk_up": float(muksuka_atk_up),
            "unity": float(unity),
            "crit_dmg": float(crit_dmg),
            "luck_a": float(luck_a),
            "luck_b": float(luck_b),
            "luck_mult": float(luck_mult),
            "passive_mult": float(passive_mult),
            "passive_has_dex_mult": bool(passive_has_dex_mult),
            "raid_weapon_bonus": float(raid_weapon_bonus),
            "raid_armor_bonus_r": float(raid_armor_bonus_r),
            "raid_fixed_dex": int(raid_fixed_dex),
            "raid_fixed_luck": int(raid_fixed_luck),
        }

        progress_area = st.empty()
        prog = {}
        start_all = time.time()

        def progress_cb(case, done, total, eta):
            prog[case] = (done, total, eta)
            lines = []
            for c in cases:
                if c in prog:
                    d, t, e = prog[c]
                    lines.append(f"{c}: tick {d}/{t} ({d/t*100:.2f}%) ETA {e:.1f}s")
                else:
                    lines.append(f"{c}: waiting...")
            progress_area.code("\n".join(lines))

        with st.spinner("威咲 計算中..."):
            results = solve_cases(
                cases=cases,
                params=params,
                k=int(k),
                workers=int(workers),
                chunk_size=int(chunk),
                step=int(step),
                progress_cb=progress_cb,
            )

        st.success(f"完了。所要時間: {time.time()-start_all:.2f}s")

        for case in cases:
            st.subheader(f"CASE {case}")
            top = results[case]

            for idx, bd in enumerate(top, 1):
                with st.expander(f"Rank {idx}  EV heal = {bd.ev_heal:,.3f}", expanded=(idx == 1)):
                    c1, c2, c3 = st.columns(3)

                    with c1:
                        st.markdown("**属性配分 % (実数)**")
                        st.text(f"CRIT {bd.crit_pct*100:.2f}% ({bd.crit:,})")
                        st.text(f"LUCK {bd.luck_pct*100:.2f}% ({bd.luck:,})")
                        st.text(f"DEX  {bd.dex_pct*100:.2f}% ({bd.dex:,})")
                        st.text(f"UTL  {bd.omni_pct*100:.2f}% ({bd.omni:,})")

                    with c2:
                        st.markdown("**ダメージ内訳（期待値）**")
                        st.text(f"通常         {bd.dmg_normal:,.3f}")
                        st.text(f"幸運一撃     {bd.dmg_luck:,.3f}")
                        st.text(f"幸運パッシブ {bd.dmg_pass:,.3f}")
                        st.text(f"合計         {bd.dmg_total:,.3f}")

                    with c3:
                        st.markdown("**共生の印**")
                        st.text(f"変換率 r     {bd.r:.6f}")
                        st.text(f"ヒールEV     {bd.ev_heal:,.3f}")
                        st.text(f"DMG_UP       {bd.dmg_up*100:.2f}%")
                        if case.startswith("2-"):
                            st.text(f"raid_armor_slots {bd.raid_armor_slots}")
                        st.text(f"weapon {bd.weapon_desc}")

# =========================
# 森癒UI
# =========================
else:
    with st.sidebar:
        st.header("森癒 入力")
        int_stat = st.number_input("知力", value=3000.0, step=10.0)
        int_buff_total = st.number_input("知力バフ合計", value=0.00, step=0.01, format="%.4f")
        weapon_ma = st.number_input("武器魔法攻", value=114.0, step=1.0)
        module_ma = st.number_input("モジュ魔法攻", value=0.0, step=1.0)
        ma_buff = st.number_input("魔法攻バフ", value=0.03, step=0.01, format="%.4f")
        refine = st.number_input("製錬攻", value=307.0, step=1.0)
        elem = st.number_input("属性攻", value=45.0, step=1.0)

        fast_display = st.number_input("ファスト表示値（小数）", value=0.00, step=0.01, format="%.4f")
        heal_power_pct = st.number_input("回復力系合計", value=0.015, step=0.01, format="%.4f")
        heal_effect_pct = st.number_input("回復効果系合計", value=0.00, step=0.01, format="%.4f")
        omni_pct = st.number_input("万能％（小数）", value=0.04, step=0.01, format="%.4f")
        crit_pct = st.number_input("会心％（小数）", value=0.05, step=0.01, format="%.4f")

        run_m = st.button("森癒を計算", type="primary")

    if run_m:
        params = {
            "int_stat": float(int_stat),
            "int_buff_total": float(int_buff_total),
            "weapon_ma": float(weapon_ma),
            "module_ma": float(module_ma),
            "ma_buff": float(ma_buff),
            "refine": float(refine),
            "elem": float(elem),
            "fast_display": float(fast_display),
            "heal_power_pct": float(heal_power_pct),
            "heal_effect_pct": float(heal_effect_pct),
            "omni_pct": float(omni_pct),
            "crit_pct": float(crit_pct),
        }

        res = solve_moriyu(params)

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("森癒 計算結果")
            st.text(f"Fast_battle     {res.fast_battle:.4f}")
            st.text(f"RegenCount_10s  {res.regen_count_10s}")
            st.text(f"TotalTicks_10s  {res.total_ticks_10s}")

            st.text(f"INTconv         {res.int_conv:,.3f}")
            st.text(f"MA_main         {res.ma_main:,.3f}")
            st.text(f"MagicAtk        {res.magic_atk:,.3f}")

        with c2:
            st.subheader("回復")
            st.text(f"Heal_tick       {res.heal_tick:,.3f}")
            st.text(f"Heal_10s        {res.heal_10s:,.3f}")
