-- Kimball Star Schema: Solar Irrigation BI (DIY & Sekitarnya, 8 Kabupaten)
-- Attribution: Weather data by Open-Meteo.com (CC BY 4.0); validation by NASA POWER.

CREATE TABLE IF NOT EXISTS dim_region (
    region_id   SERIAL PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    kabupaten   TEXT NOT NULL UNIQUE,
    provinsi    TEXT NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id         INTEGER PRIMARY KEY, -- YYYYMMDD
    full_date       DATE NOT NULL UNIQUE,
    year            SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    day             SMALLINT NOT NULL,
    day_of_year     SMALLINT NOT NULL,
    climate_season  TEXT NOT NULL,       -- Hujan (Nov-Apr) / Kemarau (Mei-Okt)
    planting_season TEXT NOT NULL,       -- MT1 (Nov-Feb) / MT2 (Mar-Jun) / Bera (Jul-Okt)
    kc_paddy        DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_scenario (
    scenario_id     SERIAL PRIMARY KEY,
    capacity_kwp    DOUBLE PRECISION NOT NULL UNIQUE,
    max_flow_lpm    DOUBLE PRECISION NOT NULL,
    capex_low_idr   BIGINT,
    capex_high_idr  BIGINT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS fact_weather_hourly (
    region_id                   INTEGER NOT NULL REFERENCES dim_region(region_id),
    ts                          TIMESTAMP NOT NULL,
    date_id                     INTEGER NOT NULL REFERENCES dim_date(date_id),
    temperature_2m              REAL,
    relative_humidity_2m        REAL,
    precipitation               REAL,
    cloud_cover                 REAL,
    wind_speed_10m              REAL,
    shortwave_radiation         REAL,
    et0_fao_evapotranspiration  REAL,
    PRIMARY KEY (region_id, ts)
);

CREATE TABLE IF NOT EXISTS fact_nasa_daily (
    region_id           INTEGER NOT NULL REFERENCES dim_region(region_id),
    date_id             INTEGER NOT NULL REFERENCES dim_date(date_id),
    allsky_sfc_sw_dwn   REAL,
    t2m                 REAL,
    rh2m                REAL,
    prectotcorr         REAL,
    ws2m                REAL,
    PRIMARY KEY (region_id, date_id)
);

CREATE TABLE IF NOT EXISTS fact_irrigation_daily (
    region_id           INTEGER NOT NULL REFERENCES dim_region(region_id),
    date_id             INTEGER NOT NULL REFERENCES dim_date(date_id),
    et0_mm              REAL NOT NULL,
    rain_mm             REAL NOT NULL,
    rad_mj_m2           REAL NOT NULL,
    temp_mean_c         REAL NOT NULL,
    rh_mean_pct         REAL NOT NULL,
    cloud_mean_pct      REAL NOT NULL,
    wind_mean_kmh       REAL NOT NULL,
    solar_water_1kwp_m3 REAL NOT NULL,
    active_pump_hours   SMALLINT NOT NULL,
    nfr_mm              REAL NOT NULL,
    need_irrigation     SMALLINT NOT NULL,
    PRIMARY KEY (region_id, date_id)
);

CREATE INDEX IF NOT EXISTS idx_weather_hourly_date ON fact_weather_hourly(date_id);
CREATE INDEX IF NOT EXISTS idx_irrigation_daily_date ON fact_irrigation_daily(date_id);
