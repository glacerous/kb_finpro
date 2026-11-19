"""Stage 5: ROI & BEP Simulation (24 core scenarios + land/fuel/efficiency sensitivity).

Loads `fact_roi_simulation` and `fact_ml_predictions` into PostgreSQL for Power BI.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd

from etl_load_pg import SCHEMA_PATH, copy_upsert, get_conn

OUT_DIR = Path("data/processed")
YEARS = 15.0  # 2011-2025

# Grounded Indonesian marketplace CAPEX ranges (Tokopedia/Shopee, Nov 2026):
# Panel 550Wp Mono: Rp 1.75M-3.50M/unit; Submersible DC+MPPT: 750W (3.43M-6.35M),
# 2200W (6.5M-12M), 3700W (13M-22M); +15% mounting/cables/installation.
# shortcut: store direct product screenshots in docs/bukti_harga/ for final report appendix.
CAPEX_TABLE = {
    1.0: (8_500_000, 15_500_000),
    3.0: (20_000_000, 38_000_000),
    5.0: (35_000_000, 65_000_000),
}

FUEL_SCENARIOS = [
    ("Biosolar (Rp 6.800)", 6_800),
    ("Dexlite (Rp 23.700)", 23_700),
]

# Diesel consumption per m3 pumped: 0.04 L/m3 (~1 L/hr @ 25 m3/hr, 5.5HP) vs 0.06 L/m3 (higher head/older pump)
DIESEL_RATES = [0.04, 0.06]
ANNUAL_OPEX_PCT = 0.02  # 2% of CAPEX/year for routine maintenance

# Land preparation: 250 mm per planting season spread over first 15 days of MT1 (Nov 1-15) & MT2 (Mar 1-15)
LAND_PREP_MM_PER_DAY = 250.0 / 15.0


def load_base_data(conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT f.region_id, r.kabupaten, d.month, d.day, d.planting_season,
                   f.nfr_mm, f.solar_water_1kwp_m3
            FROM fact_irrigation_daily f
            JOIN dim_region r ON r.region_id = f.region_id
            JOIN dim_date d   ON d.date_id   = f.date_id
            WHERE d.planting_season IN ('MT1', 'MT2')
            """
        )
        daily = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])

        cur.execute("SELECT scenario_id, capacity_kwp, capex_low_idr, capex_high_idr FROM dim_scenario ORDER BY capacity_kwp")
        scenarios = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])
    return daily, scenarios


def simulate_roi(daily: pd.DataFrame, scenarios: pd.DataFrame) -> pd.DataFrame:
    is_prep = ((daily["month"].isin([11, 3])) & (daily["day"] <= 15))
    daily = daily.assign(total_need_mm=daily["nfr_mm"] + np.where(is_prep, LAND_PREP_MM_PER_DAY, 0.0))

    rows = []
    for (rid, kab), grp in daily.groupby(["region_id", "kabupaten"]):
        need_mm = grp["total_need_mm"].to_numpy()
        solar_1kwp = grp["solar_water_1kwp_m3"].to_numpy()

        for _, sc in scenarios.iterrows():
            sid = int(sc["scenario_id"])
            cap = float(sc["capacity_kwp"])
            capex_lo = int(sc["capex_low_idr"])
            capex_hi = int(sc["capex_high_idr"])
            solar_cap = solar_1kwp * cap

            land_modes = [
                ("Individu (1 ha)", 1.0),
                ("Kelompok Tani (1 ha/kWp)", cap),
            ]
            for land_mode, ha in land_modes:
                # 1 mm on 1 ha = 10 m3
                demand_m3 = need_mm * 10.0 * ha
                solar_used = np.minimum(demand_m3, solar_cap)
                deficit_m3 = demand_m3 - solar_used

                ann_demand = float(demand_m3.sum() / YEARS)
                ann_solar = float(solar_used.sum() / YEARS)
                ann_deficit = float(deficit_m3.sum() / YEARS)
                cov_pct = (ann_solar / ann_demand * 100.0) if ann_demand > 0 else 0.0

                opex_lo = round(capex_lo * ANNUAL_OPEX_PCT)
                opex_hi = round(capex_hi * ANNUAL_OPEX_PCT)

                for fuel_name, fuel_price in FUEL_SCENARIOS:
                    for rate in DIESEL_RATES:
                        diesel_saved_l = ann_solar * rate
                        gross_saving = round(diesel_saved_l * fuel_price)
                        net_lo = gross_saving - opex_lo
                        net_hi = gross_saving - opex_hi

                        bep_lo = round(capex_lo / net_lo, 2) if net_lo > 0 else None
                        bep_hi = round(capex_hi / net_hi, 2) if net_hi > 0 else None
                        roi_10_lo = round(((net_lo * 10 - capex_lo) / capex_lo) * 100.0, 1)
                        roi_10_hi = round(((net_hi * 10 - capex_hi) / capex_hi) * 100.0, 1)

                        rows.append({
                            "region_id": int(rid),
                            "kabupaten": kab,
                            "scenario_id": sid,
                            "capacity_kwp": cap,
                            "land_mode": land_mode,
                            "land_area_ha": ha,
                            "fuel_scenario": fuel_name,
                            "fuel_price_idr": fuel_price,
                            "diesel_l_per_m3": rate,
                            "annual_demand_m3": round(ann_demand, 1),
                            "annual_solar_m3": round(ann_solar, 1),
                            "solar_coverage_pct": round(cov_pct, 2),
                            "annual_diesel_backup_m3": round(ann_deficit, 1),
                            "annual_diesel_saved_l": round(diesel_saved_l, 1),
                            "annual_gross_saving_idr": gross_saving,
                            "annual_opex_low_idr": opex_lo,
                            "annual_opex_high_idr": opex_hi,
                            "annual_net_saving_low": net_lo,
                            "annual_net_saving_high": net_hi,
                            "bep_low_years": bep_lo,
                            "bep_high_years": bep_hi,
                            "roi_10yr_low_pct": roi_10_lo,
                            "roi_10yr_high_pct": roi_10_hi,
                            "viable_under_5yr_low": int(bep_lo is not None and bep_lo <= 5.0),
                        })
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Apply updated schema (creates fact_roi_simulation & fact_ml_predictions if missing)
                cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

                # Update dim_scenario CAPEX ranges
                for cap, (lo, hi) in CAPEX_TABLE.items():
                    cur.execute(
                        "UPDATE dim_scenario SET capex_low_idr = %s, capex_high_idr = %s WHERE capacity_kwp = %s",
                        (lo, hi, cap),
                    )

                daily, scenarios = load_base_data(conn)
                roi_df = simulate_roi(daily, scenarios)

                pg_roi_cols = [
                    "region_id", "scenario_id", "land_mode", "land_area_ha",
                    "fuel_scenario", "fuel_price_idr", "diesel_l_per_m3",
                    "annual_demand_m3", "annual_solar_m3", "solar_coverage_pct",
                    "annual_diesel_backup_m3", "annual_diesel_saved_l",
                    "annual_gross_saving_idr", "annual_opex_low_idr", "annual_opex_high_idr",
                    "annual_net_saving_low", "annual_net_saving_high",
                    "bep_low_years", "bep_high_years", "roi_10yr_low_pct", "roi_10yr_high_pct",
                    "viable_under_5yr_low",
                ]
                copy_upsert(
                    cur,
                    roi_df,
                    "fact_roi_simulation",
                    pg_roi_cols,
                    ["region_id", "scenario_id", "land_mode", "fuel_scenario", "diesel_l_per_m3"],
                )

                # Load Stage 4 ML predictions into PostgreSQL for Power BI
                ml_csv = OUT_DIR / "ml_test_predictions_2023_2025.csv"
                assert ml_csv.exists(), f"Missing {ml_csv}; run stage4_stats_ml.py first."
                ml_df = pd.read_csv(ml_csv)
                pg_ml_cols = [
                    "region_id", "date_id", "next_date", "next_season", "target_next",
                    "prob_lr", "pred_lr_050", "pred_lr_fn3", "prob_rf", "pred_rf_050", "pred_rf_fn3",
                ]
                copy_upsert(cur, ml_df, "fact_ml_predictions", pg_ml_cols, ["region_id", "date_id"])

                cur.execute("SELECT COUNT(*) FROM fact_roi_simulation")
                n_roi = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM fact_ml_predictions")
                n_ml = cur.fetchone()[0]
    finally:
        conn.close()

    roi_df.to_csv(OUT_DIR / "roi_simulation_table.csv", index=False)

    # Print executive summary (baseline diesel rate 0.04 L/m3)
    base = roi_df[roi_df["diesel_l_per_m3"] == 0.04].copy()
    print(f"Loaded PostgreSQL: fact_roi_simulation={n_roi:,} rows | fact_ml_predictions={n_ml:,} rows\n")

    print("=== ROI SUMMARY: KELOMPOK TANI (1 ha/kWp, 0.04 L/m3, 1 vs 5 kWp) ===")
    view = base[(base["land_mode"] == "Kelompok Tani (1 ha/kWp)") & (base["capacity_kwp"].isin([1.0, 5.0]))]
    piv = view.pivot_table(
        index=["kabupaten", "capacity_kwp"],
        columns="fuel_scenario",
        values=["solar_coverage_pct", "bep_low_years", "bep_high_years"],
        aggfunc="first",
    ).round(2)
    print(piv.to_string())

    print("\n=== INDIVIDUAL (1 ha) OVERKILL CHECK (Gunungkidul, Dexlite, 0.04 L/m3) ===")
    ind = base[(base["kabupaten"] == "Gunungkidul") & (base["land_mode"] == "Individu (1 ha)") & (base["fuel_price_idr"] == 23700)]
    print(ind[["capacity_kwp", "solar_coverage_pct", "annual_diesel_saved_l", "bep_low_years", "bep_high_years"]].to_string(index=False))

    # Save compact JSON summary for reporting/git
    summary = {
        "rows_loaded": {"fact_roi_simulation": n_roi, "fact_ml_predictions": n_ml},
        "assumptions": {
            "capex_idr": CAPEX_TABLE,
            "annual_opex_pct": ANNUAL_OPEX_PCT,
            "land_prep_mm_per_season": 250.0,
            "diesel_rates_l_per_m3": DIESEL_RATES,
        },
        "best_5kwp_group_dexlite_004": (
            base[(base["land_mode"] == "Kelompok Tani (1 ha/kWp)") & (base["capacity_kwp"] == 5.0) & (base["fuel_price_idr"] == 23700)]
            .sort_values("bep_low_years")[["kabupaten", "solar_coverage_pct", "bep_low_years", "bep_high_years", "roi_10yr_low_pct"]]
            .to_dict(orient="records")
        ),
        "best_1kwp_indiv_biosolar_004": (
            base[(base["land_mode"] == "Individu (1 ha)") & (base["capacity_kwp"] == 1.0) & (base["fuel_price_idr"] == 6800)]
            .sort_values("bep_low_years")[["kabupaten", "solar_coverage_pct", "bep_low_years", "bep_high_years", "roi_10yr_low_pct"]]
            .to_dict(orient="records")
        ),
    }
    (OUT_DIR / "stage5_roi_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
