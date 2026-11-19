"""Fetch 1-kabupaten sample (Gunungkidul, 2011-2025) from Open-Meteo & NASA POWER.

Attribution:
- Weather data by Open-Meteo.com (https://open-meteo.com/), licensed under CC BY 4.0.
- NASA POWER data from NASA Langley Research Center POWER Project (https://power.larc.nasa.gov/).
"""

from pathlib import Path
import time
import pandas as pd
import requests

REGION = "Gunungkidul"
LAT, LON = -7.9666, 110.6025
START_YEAR, END_YEAR = 2011, 2025
OUT_DIR = Path("data/raw")

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
    "et0_fao_evapotranspiration",
]

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_VARS = ["ALLSKY_SFC_SW_DWN", "T2M", "RH2M", "PRECTOTCORR", "WS2M"]


SESSION = requests.Session()


def get_json(url: str, params: dict, retries: int = 5) -> dict:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = SESSION.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 * attempt)
                continue
            resp.raise_for_status()
        except requests.exceptions.RequestException as err:
            last_err = err
            if attempt < retries:
                time.sleep(2 * attempt)
                continue
            raise
    raise RuntimeError(f"Failed after {retries} retries: {url}") from last_err


def fetch_open_meteo() -> tuple[pd.DataFrame, dict]:
    frames = []
    units = {}
    for year in range(START_YEAR, END_YEAR + 1):
        data = get_json(
            OPEN_METEO_URL,
            {
                "latitude": LAT,
                "longitude": LON,
                "start_date": f"{year}-01-01",
                "end_date": f"{year}-12-31",
                "hourly": ",".join(OPEN_METEO_VARS),
                "timezone": "Asia/Jakarta",
            },
        )
        units = data.get("hourly_units", units)
        df = pd.DataFrame(data["hourly"])
        df.insert(0, "kabupaten", REGION)
        frames.append(df)
        time.sleep(0.3)
    return pd.concat(frames, ignore_index=True), units


def fetch_nasa_power() -> tuple[pd.DataFrame, dict]:
    frames = []
    units = {}
    for year in range(START_YEAR, END_YEAR + 1):
        data = get_json(
            NASA_POWER_URL,
            {
                "parameters": ",".join(NASA_POWER_VARS),
                "community": "AG",
                "longitude": LON,
                "latitude": LAT,
                "start": f"{year}0101",
                "end": f"{year}1231",
                "format": "JSON",
            },
        )
        fill_val = data.get("header", {}).get("fill_value", -999.0)
        param_meta = data.get("parameters", {})
        units = {k: v.get("units", "") for k, v in param_meta.items()}
        param_data = data["properties"]["parameter"]
        df = pd.DataFrame(param_data)
        df.index.name = "date"
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
        for col in NASA_POWER_VARS:
            df[col] = pd.to_numeric(df[col], errors="coerce").replace(fill_val, pd.NA)
        df.insert(0, "kabupaten", REGION)
        frames.append(df)
        time.sleep(0.3)
    return pd.concat(frames, ignore_index=True), units


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching Open-Meteo hourly ({REGION}, {START_YEAR}-{END_YEAR})...")
    om_df, om_units = fetch_open_meteo()
    om_path = OUT_DIR / f"sample_openmeteo_{REGION.lower()}_{START_YEAR}_{END_YEAR}.csv"
    om_df.to_csv(om_path, index=False)

    print(f"Fetching NASA POWER daily ({REGION}, {START_YEAR}-{END_YEAR})...")
    np_df, np_units = fetch_nasa_power()
    np_path = OUT_DIR / f"sample_nasapower_{REGION.lower()}_{START_YEAR}_{END_YEAR}.csv"
    np_df.to_csv(np_path, index=False)

    # Sanity checks
    assert len(om_df) > 130_000, f"Unexpected Open-Meteo row count: {len(om_df)}"
    assert len(np_df) > 5_400, f"Unexpected NASA POWER row count: {len(np_df)}"

    print("\n=== Open-Meteo Summary ===")
    print(f"File: {om_path} ({om_path.stat().st_size / 1e6:.2f} MB)")
    print(f"Rows: {len(om_df):,} | Range: {om_df['time'].min()} -> {om_df['time'].max()}")
    print("Units:", om_units)
    print("Nulls:\n", om_df.isna().sum().to_dict())
    print("Min/Max shortwave_radiation:", om_df["shortwave_radiation"].min(), om_df["shortwave_radiation"].max())
    print("Min/Max et0:", om_df["et0_fao_evapotranspiration"].min(), om_df["et0_fao_evapotranspiration"].max())

    print("\n=== NASA POWER Summary ===")
    print(f"File: {np_path} ({np_path.stat().st_size / 1e6:.2f} MB)")
    print(f"Rows: {len(np_df):,} | Range: {np_df['date'].min()} -> {np_df['date'].max()}")
    print("Units:", np_units)
    print("Nulls:\n", np_df.isna().sum().to_dict())

    # Cross-check daily radiation correlation
    om_daily = (
        om_df.assign(date=om_df["time"].str.slice(0, 10))
        .groupby("date", as_index=False)["shortwave_radiation"]
        .sum()
    )
    # Open-Meteo sum of hourly W/m2 = Wh/m2/day; * 0.0036 = MJ/m2/day
    om_daily["om_rad_mj"] = om_daily["shortwave_radiation"] * 0.0036
    merged = om_daily.merge(np_df[["date", "ALLSKY_SFC_SW_DWN"]], on="date").dropna()
    corr = merged["om_rad_mj"].corr(merged["ALLSKY_SFC_SW_DWN"])
    diff = (merged["om_rad_mj"] - merged["ALLSKY_SFC_SW_DWN"]).mean()
    print("\n=== Cross-Validation (Daily Radiation: Open-Meteo vs NASA POWER) ===")
    print(f"Matched days: {len(merged):,} | Pearson r: {corr:.4f} | Mean diff (OM - NASA, MJ/m2/d): {diff:+.2f}")
    print(f"Mean OM: {merged['om_rad_mj'].mean():.2f} MJ/m2/d | Mean NASA: {merged['ALLSKY_SFC_SW_DWN'].mean():.2f} MJ/m2/d")


if __name__ == "__main__":
    main()
