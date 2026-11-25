"""Idempotent ETL loader: raw CSVs (8 kabupaten) -> PostgreSQL Kimball Star Schema.

Reads DB connection from environment variables or local `.env` file:
  PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
"""

import argparse
import io
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from etl_fetch import END_YEAR, OUT_DIR, REGIONS, START_YEAR

SCHEMA_PATH = Path("sql/schema.sql")
QUALITY_REPORT_PATH = Path("data/processed/etl_quality_report.json")
EXPECTED_HOURLY_ROWS = 131_496
EXPECTED_DAILY_ROWS = 5_479

# Piecewise Gowa debit curve for 1 kWp direct-driven DC pump (L/min vs W/m2)
# shortcut: cut-in at 30 W/m2 is an assumption; run sensitivity test in Tahap 5
GOWA_RAD_XP = [0.0, 30.0, 51.0, 276.0, 726.0, 1000.0]
GOWA_FLOW_FP = [0.0, 0.0, 15.6, 53.3, 84.1, 100.0]

# Paddy NFR assumptions (mm/day); shortcut: verify planting calendar against KATAM DIY/Jateng
PERCOLATION_MM = 2.0
WLR_MM = 1.0
REFF_COEF = 0.8
NEED_IRRIG_THRESHOLD_MM = 1.0

SCENARIOS = [
    (1.0, 100.0, None, None, "Acuan studi Gowa (900 Wp / pompa DC 750 W, direct-driven tanpa baterai)"),
    (3.0, 300.0, None, None, "Interpolasi direct-driven DC tanpa baterai (skala 3x)"),
    (5.0, 500.0, None, None, "Direct-driven DC tanpa baterai (skala 5x, bukan sistem komunitas baterai)"),
]


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_conn():
    load_dotenv()
    password = os.environ.get("PGPASSWORD")
    if not password:
        raise RuntimeError("PGPASSWORD belum diset. Buat file .env dari .env.example atau set env var PGPASSWORD.")
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "kb_solar_irrigation"),
        user=os.environ.get("PGUSER", "postgres"),
        password=password,
    )


def copy_upsert(cur, df: pd.DataFrame, target_table: str, cols: list[str], pk_cols: list[str]) -> None:
    stage = f"_stg_{target_table}"
    cur.execute(f"CREATE TEMP TABLE IF NOT EXISTS {stage} (LIKE {target_table} INCLUDING DEFAULTS) ON COMMIT DROP")
    cur.execute(f"TRUNCATE {stage}")
    buf = io.StringIO()
    df[cols].to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)
    col_list = ", ".join(cols)
    cur.copy_expert(f"COPY {stage} ({col_list}) FROM STDIN WITH (FORMAT csv, NULL '\\N')", buf)

    update_cols = [c for c in cols if c not in pk_cols]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    pk_list = ", ".join(pk_cols)
    cur.execute(
        f"INSERT INTO {target_table} ({col_list}) SELECT {col_list} FROM {stage} "
        f"ON CONFLICT ({pk_list}) DO UPDATE SET {set_clause}"
    )


def build_dim_date() -> pd.DataFrame:
    dates = pd.date_range(f"{START_YEAR}-01-01", f"{END_YEAR}-12-31", freq="D")
    df = pd.DataFrame({"full_date": dates})
    df["date_id"] = df["full_date"].dt.strftime("%Y%m%d").astype(int)
    df["year"] = df["full_date"].dt.year
    df["month"] = df["full_date"].dt.month
    df["day"] = df["full_date"].dt.day
    df["day_of_year"] = df["full_date"].dt.dayofyear
    df["climate_season"] = np.where(df["month"].isin([11, 12, 1, 2, 3, 4]), "Hujan", "Kemarau")
    df["planting_season"] = np.select(
        [df["month"].isin([11, 12, 1, 2]), df["month"].isin([3, 4, 5, 6])],
        ["MT1", "MT2"],
        default="Bera",
    )
    # FAO-56 paddy Kc approximation per month within MT1/MT2 (init 1.05, mid 1.20, late 0.90, bera 0.0)
    kc_map = {11: 1.05, 12: 1.20, 1: 1.20, 2: 0.90, 3: 1.05, 4: 1.20, 5: 1.20, 6: 0.90}
    df["kc_paddy"] = df["month"].map(kc_map).fillna(0.0)
    df["full_date"] = df["full_date"].dt.strftime("%Y-%m-%d")
    return df


def build_irrigation_daily(om_df: pd.DataFrame, region_id: int, dim_date: pd.DataFrame) -> pd.DataFrame:
    flow_lpm = np.interp(om_df["shortwave_radiation"].to_numpy(), GOWA_RAD_XP, GOWA_FLOW_FP)
    work = om_df.assign(
        date_str=om_df["time"].str.slice(0, 10),
        water_m3_hr=flow_lpm * 60.0 / 1000.0,
        is_active=(flow_lpm > 0).astype(int),
    )
    daily = work.groupby("date_str", as_index=False).agg(
        et0_mm=("et0_fao_evapotranspiration", "sum"),
        rain_mm=("precipitation", "sum"),
        rad_wh=("shortwave_radiation", "sum"),
        temp_mean_c=("temperature_2m", "mean"),
        rh_mean_pct=("relative_humidity_2m", "mean"),
        cloud_mean_pct=("cloud_cover", "mean"),
        wind_mean_kmh=("wind_speed_10m", "mean"),
        solar_water_1kwp_m3=("water_m3_hr", "sum"),
        active_pump_hours=("is_active", "sum"),
    )
    daily["rad_mj_m2"] = daily["rad_wh"] * 0.0036
    daily = daily.merge(
        dim_date[["full_date", "date_id", "planting_season", "kc_paddy"]],
        left_on="date_str",
        right_on="full_date",
        how="inner",
    )
    in_season = daily["planting_season"] != "Bera"
    raw_nfr = daily["kc_paddy"] * daily["et0_mm"] + PERCOLATION_MM + WLR_MM - REFF_COEF * daily["rain_mm"]
    daily["nfr_mm"] = np.where(in_season, np.maximum(0.0, raw_nfr), 0.0)
    daily["need_irrigation"] = np.where(in_season & (daily["nfr_mm"] > NEED_IRRIG_THRESHOLD_MM), 1, 0)
    daily["region_id"] = region_id
    return daily[
        [
            "region_id",
            "date_id",
            "et0_mm",
            "rain_mm",
            "rad_mj_m2",
            "temp_mean_c",
            "rh_mean_pct",
            "cloud_mean_pct",
            "wind_mean_kmh",
            "solar_water_1kwp_m3",
            "active_pump_hours",
            "nfr_mm",
            "need_irrigation",
        ]
    ]


def validate_data_quality() -> dict:
    """Fail-fast 4-dimension Data Quality check (Uniqueness, Completeness, Accuracy, Validity)."""
    report = {"regions": {}, "total_hourly_rows": 0, "total_daily_rows": 0, "status": "PASS"}
    for reg in REGIONS:
        slug = reg["slug"]
        om_path = OUT_DIR / f"openmeteo_{slug}_{START_YEAR}_{END_YEAR}.csv"
        np_path = OUT_DIR / f"nasapower_{slug}_{START_YEAR}_{END_YEAR}.csv"
        assert om_path.exists(), f"Missing {om_path}"
        assert np_path.exists(), f"Missing {np_path}"

        om = pd.read_csv(om_path)
        np_df = pd.read_csv(np_path)

        # 1. Validity: exact row counts & ISO date parsing
        assert len(om) == EXPECTED_HOURLY_ROWS, f"{slug} OM rows {len(om)} != {EXPECTED_HOURLY_ROWS}"
        assert len(np_df) == EXPECTED_DAILY_ROWS, f"{slug} NASA rows {len(np_df)} != {EXPECTED_DAILY_ROWS}"
        assert pd.to_datetime(om["time"], format="%Y-%m-%dT%H:%M", errors="coerce").notna().all(), f"{slug} invalid OM time"
        assert pd.to_datetime(np_df["date"], format="%Y-%m-%d", errors="coerce").notna().all(), f"{slug} invalid NASA date"

        # 2. Uniqueness: 0 duplicate timestamps/dates
        assert om["time"].duplicated().sum() == 0, f"{slug} duplicate OM timestamps"
        assert np_df["date"].duplicated().sum() == 0, f"{slug} duplicate NASA dates"

        # 3. Completeness: 0 NULL/NaN
        assert int(om.isna().sum().sum()) == 0, f"{slug} OM contains NaN"
        assert int(np_df.isna().sum().sum()) == 0, f"{slug} NASA contains NaN"

        # 4. Accuracy: physical bounds
        assert om["relative_humidity_2m"].between(0, 100).all(), f"{slug} OM RH out of [0,100]"
        assert (om["shortwave_radiation"] >= 0).all(), f"{slug} OM negative radiation"
        assert (om["precipitation"] >= 0).all(), f"{slug} OM negative rain"
        assert om["temperature_2m"].between(5, 50).all(), f"{slug} OM temp out of [5,50]"
        assert np_df["RH2M"].between(0, 100).all(), f"{slug} NASA RH out of [0,100]"
        assert (np_df["ALLSKY_SFC_SW_DWN"] >= 0).all(), f"{slug} NASA negative radiation"
        assert (np_df["PRECTOTCORR"] >= 0).all(), f"{slug} NASA negative rain"
        assert np_df["T2M"].between(5, 50).all(), f"{slug} NASA temp out of [5,50]"

        report["regions"][slug] = {
            "kabupaten": reg["kabupaten"],
            "om_rows": len(om),
            "nasa_rows": len(np_df),
            "duplicates": 0,
            "nulls": 0,
            "physical_bounds_ok": True,
        }
        report["total_hourly_rows"] += len(om)
        report["total_daily_rows"] += len(np_df)

    QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"[DQ PASS] 8 kabupaten verified | OM={report['total_hourly_rows']:,} | "
        f"NASA={report['total_daily_rows']:,} | 0 dup | 0 null -> {QUALITY_REPORT_PATH}"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL Quality Check & PostgreSQL Kimball Loader")
    parser.add_argument("--quality-only", action="store_true", help="Run 4-dimension DQ checks on raw CSVs without PostgreSQL")
    args = parser.parse_args()

    validate_data_quality()
    if args.quality_only:
        return

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

                # 1. Upsert dim_region
                execute_values(
                    cur,
                    """
                    INSERT INTO dim_region (slug, kabupaten, provinsi, latitude, longitude)
                    VALUES %s
                    ON CONFLICT (slug) DO UPDATE SET
                        kabupaten = EXCLUDED.kabupaten,
                        provinsi = EXCLUDED.provinsi,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude
                    """,
                    [(r["slug"], r["kabupaten"], r["provinsi"], r["lat"], r["lon"]) for r in REGIONS],
                )
                cur.execute("SELECT slug, region_id FROM dim_region")
                region_map = dict(cur.fetchall())

                # 2. Upsert dim_scenario
                execute_values(
                    cur,
                    """
                    INSERT INTO dim_scenario (capacity_kwp, max_flow_lpm, capex_low_idr, capex_high_idr, notes)
                    VALUES %s
                    ON CONFLICT (capacity_kwp) DO UPDATE SET
                        max_flow_lpm = EXCLUDED.max_flow_lpm,
                        notes = EXCLUDED.notes
                    """,
                    SCENARIOS,
                )

                # 3. Upsert dim_date
                dim_date = build_dim_date()
                copy_upsert(
                    cur,
                    dim_date,
                    "dim_date",
                    ["date_id", "full_date", "year", "month", "day", "day_of_year", "climate_season", "planting_season", "kc_paddy"],
                    ["date_id"],
                )

                # 4. Load fact tables per kabupaten
                for reg in REGIONS:
                    slug = reg["slug"]
                    rid = region_map[slug]
                    om_path = OUT_DIR / f"openmeteo_{slug}_{START_YEAR}_{END_YEAR}.csv"
                    np_path = OUT_DIR / f"nasapower_{slug}_{START_YEAR}_{END_YEAR}.csv"

                    print(f"[LOAD] {reg['kabupaten']}...", flush=True)
                    om_df = pd.read_csv(om_path)
                    om_fact = om_df.assign(
                        region_id=rid,
                        ts=om_df["time"].str.replace("T", " ", regex=False),
                        date_id=om_df["time"].str.slice(0, 10).str.replace("-", "", regex=False).astype(int),
                    )
                    copy_upsert(
                        cur,
                        om_fact,
                        "fact_weather_hourly",
                        [
                            "region_id",
                            "ts",
                            "date_id",
                            "temperature_2m",
                            "relative_humidity_2m",
                            "precipitation",
                            "cloud_cover",
                            "wind_speed_10m",
                            "shortwave_radiation",
                            "et0_fao_evapotranspiration",
                        ],
                        ["region_id", "ts"],
                    )

                    np_df = pd.read_csv(np_path)
                    np_fact = np_df.assign(
                        region_id=rid,
                        date_id=np_df["date"].str.replace("-", "", regex=False).astype(int),
                    ).rename(
                        columns={
                            "ALLSKY_SFC_SW_DWN": "allsky_sfc_sw_dwn",
                            "T2M": "t2m",
                            "RH2M": "rh2m",
                            "PRECTOTCORR": "prectotcorr",
                            "WS2M": "ws2m",
                        }
                    )
                    copy_upsert(
                        cur,
                        np_fact,
                        "fact_nasa_daily",
                        ["region_id", "date_id", "allsky_sfc_sw_dwn", "t2m", "rh2m", "prectotcorr", "ws2m"],
                        ["region_id", "date_id"],
                    )

                    irrig_df = build_irrigation_daily(om_df, rid, dim_date)
                    copy_upsert(
                        cur,
                        irrig_df,
                        "fact_irrigation_daily",
                        list(irrig_df.columns),
                        ["region_id", "date_id"],
                    )

                # Verify counts
                print("\n=== POSTGRESQL ROW COUNTS ===")
                for tbl in ["dim_region", "dim_date", "dim_scenario", "fact_weather_hourly", "fact_nasa_daily", "fact_irrigation_daily"]:
                    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                    print(f"  {tbl:24s}: {cur.fetchone()[0]:,}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
