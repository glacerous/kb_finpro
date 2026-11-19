"""Fetch 8 kabupaten (DIY & Sekitarnya, 2011-2025) from Open-Meteo & NASA POWER.

Idempotent: skips any kabupaten whose raw CSV already exists.

Attribution:
- Weather data by Open-Meteo.com (https://open-meteo.com/), licensed under CC BY 4.0.
- NASA POWER data from NASA Langley Research Center POWER Project (https://power.larc.nasa.gov/).
"""

from pathlib import Path
import time
import pandas as pd
import requests

START_YEAR, END_YEAR = 2011, 2025
OUT_DIR = Path("data/raw")

REGIONS = [
    {"slug": "kulon_progo", "kabupaten": "Kulon Progo", "provinsi": "DI Yogyakarta", "lat": -7.8568, "lon": 110.1604},
    {"slug": "bantul", "kabupaten": "Bantul", "provinsi": "DI Yogyakarta", "lat": -7.8881, "lon": 110.3288},
    {"slug": "gunungkidul", "kabupaten": "Gunungkidul", "provinsi": "DI Yogyakarta", "lat": -7.9666, "lon": 110.6025},
    {"slug": "sleman", "kabupaten": "Sleman", "provinsi": "DI Yogyakarta", "lat": -7.7160, "lon": 110.3556},
    {"slug": "purworejo", "kabupaten": "Purworejo", "provinsi": "Jawa Tengah", "lat": -7.7131, "lon": 110.0086},
    {"slug": "kab_magelang", "kabupaten": "Kab. Magelang", "provinsi": "Jawa Tengah", "lat": -7.5994, "lon": 110.2206},
    {"slug": "klaten", "kabupaten": "Klaten", "provinsi": "Jawa Tengah", "lat": -7.7058, "lon": 110.6015},
    {"slug": "wonogiri", "kabupaten": "Wonogiri", "provinsi": "Jawa Tengah", "lat": -7.8139, "lon": 110.9234},
]

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


def fetch_open_meteo_region(reg: dict) -> pd.DataFrame:
    frames = []
    for year in range(START_YEAR, END_YEAR + 1):
        data = get_json(
            OPEN_METEO_URL,
            {
                "latitude": reg["lat"],
                "longitude": reg["lon"],
                "start_date": f"{year}-01-01",
                "end_date": f"{year}-12-31",
                "hourly": ",".join(OPEN_METEO_VARS),
                "timezone": "Asia/Jakarta",
            },
        )
        df = pd.DataFrame(data["hourly"])
        df.insert(0, "kabupaten", reg["kabupaten"])
        frames.append(df)
        time.sleep(0.25)
    return pd.concat(frames, ignore_index=True)


def fetch_nasa_power_region(reg: dict) -> pd.DataFrame:
    frames = []
    for year in range(START_YEAR, END_YEAR + 1):
        data = get_json(
            NASA_POWER_URL,
            {
                "parameters": ",".join(NASA_POWER_VARS),
                "community": "AG",
                "longitude": reg["lon"],
                "latitude": reg["lat"],
                "start": f"{year}0101",
                "end": f"{year}1231",
                "format": "JSON",
            },
        )
        fill_val = data.get("header", {}).get("fill_value", -999.0)
        df = pd.DataFrame(data["properties"]["parameter"])
        df.index.name = "date"
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
        for col in NASA_POWER_VARS:
            df[col] = pd.to_numeric(df[col], errors="coerce").replace(fill_val, pd.NA)
        df.insert(0, "kabupaten", reg["kabupaten"])
        frames.append(df)
        time.sleep(0.25)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []

    for reg in REGIONS:
        slug = reg["slug"]
        om_path = OUT_DIR / f"openmeteo_{slug}_{START_YEAR}_{END_YEAR}.csv"
        np_path = OUT_DIR / f"nasapower_{slug}_{START_YEAR}_{END_YEAR}.csv"

        # Reuse earlier sample file for Gunungkidul if present
        old_om = OUT_DIR / f"sample_openmeteo_{slug}_{START_YEAR}_{END_YEAR}.csv"
        old_np = OUT_DIR / f"sample_nasapower_{slug}_{START_YEAR}_{END_YEAR}.csv"
        if not om_path.exists() and old_om.exists():
            old_om.rename(om_path)
        if not np_path.exists() and old_np.exists():
            old_np.rename(np_path)

        if om_path.exists():
            print(f"[SKIP] {reg['kabupaten']} Open-Meteo already exists.")
            om_df = pd.read_csv(om_path)
        else:
            print(f"[FETCH] {reg['kabupaten']} Open-Meteo ({START_YEAR}-{END_YEAR})...", flush=True)
            om_df = fetch_open_meteo_region(reg)
            om_df.to_csv(om_path, index=False)

        if np_path.exists():
            print(f"[SKIP] {reg['kabupaten']} NASA POWER already exists.")
            np_df = pd.read_csv(np_path)
        else:
            print(f"[FETCH] {reg['kabupaten']} NASA POWER ({START_YEAR}-{END_YEAR})...", flush=True)
            np_df = fetch_nasa_power_region(reg)
            np_df.to_csv(np_path, index=False)

        assert len(om_df) == 131_496, f"{reg['kabupaten']} OM rows={len(om_df)}"
        assert len(np_df) == 5_479, f"{reg['kabupaten']} NASA rows={len(np_df)}"

        om_daily = (
            om_df.assign(date=om_df["time"].str.slice(0, 10))
            .groupby("date", as_index=False)["shortwave_radiation"]
            .sum()
        )
        om_daily["om_rad_mj"] = om_daily["shortwave_radiation"] * 0.0036
        merged = om_daily.merge(np_df[["date", "ALLSKY_SFC_SW_DWN"]], on="date").dropna()
        summary.append(
            {
                "kabupaten": reg["kabupaten"],
                "om_nulls": int(om_df.isna().sum().sum()),
                "np_nulls": int(np_df.isna().sum().sum()),
                "om_rad_mean": round(merged["om_rad_mj"].mean(), 2),
                "np_rad_mean": round(merged["ALLSKY_SFC_SW_DWN"].mean(), 2),
                "pearson_r": round(merged["om_rad_mj"].corr(merged["ALLSKY_SFC_SW_DWN"]), 4),
            }
        )

    print("\n=== 8-KABUPATEN FETCH & CROSS-VALIDATION SUMMARY ===")
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
