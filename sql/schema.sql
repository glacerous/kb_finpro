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

CREATE TABLE IF NOT EXISTS fact_roi_simulation (
    region_id               INTEGER NOT NULL REFERENCES dim_region(region_id),
    scenario_id             INTEGER NOT NULL REFERENCES dim_scenario(scenario_id),
    land_mode               TEXT NOT NULL,          -- 'Individu (1 ha)' | 'Kelompok Tani (1 ha/kWp)'
    land_area_ha            DOUBLE PRECISION NOT NULL,
    fuel_scenario           TEXT NOT NULL,          -- 'Biosolar (Rp 6.800)' | 'Dexlite (Rp 23.700)'
    fuel_price_idr          INTEGER NOT NULL,
    diesel_l_per_m3         DOUBLE PRECISION NOT NULL,
    annual_demand_m3        DOUBLE PRECISION NOT NULL,
    annual_solar_m3         DOUBLE PRECISION NOT NULL,
    solar_coverage_pct      DOUBLE PRECISION NOT NULL,
    annual_diesel_backup_m3 DOUBLE PRECISION NOT NULL,
    annual_diesel_saved_l   DOUBLE PRECISION NOT NULL,
    annual_gross_saving_idr BIGINT NOT NULL,
    annual_opex_low_idr     BIGINT NOT NULL,
    annual_opex_high_idr    BIGINT NOT NULL,
    annual_net_saving_low   BIGINT NOT NULL,
    annual_net_saving_high  BIGINT NOT NULL,
    bep_low_years           DOUBLE PRECISION,
    bep_high_years          DOUBLE PRECISION,
    roi_10yr_low_pct        DOUBLE PRECISION,
    roi_10yr_high_pct       DOUBLE PRECISION,
    viable_under_5yr_low    SMALLINT NOT NULL,
    PRIMARY KEY (region_id, scenario_id, land_mode, fuel_scenario, diesel_l_per_m3)
);

CREATE TABLE IF NOT EXISTS fact_ml_predictions (
    region_id       INTEGER NOT NULL REFERENCES dim_region(region_id),
    date_id         INTEGER NOT NULL REFERENCES dim_date(date_id),
    next_date       DATE NOT NULL,
    next_season     TEXT NOT NULL,
    target_next     SMALLINT NOT NULL,
    prob_lr         REAL NOT NULL,
    pred_lr_050     SMALLINT NOT NULL,
    pred_lr_fn3     SMALLINT NOT NULL,
    prob_rf         REAL NOT NULL,
    pred_rf_050     SMALLINT NOT NULL,
    pred_rf_fn3     SMALLINT NOT NULL,
    PRIMARY KEY (region_id, date_id)
);

CREATE INDEX IF NOT EXISTS idx_weather_hourly_date ON fact_weather_hourly(date_id);
CREATE INDEX IF NOT EXISTS idx_irrigation_daily_date ON fact_irrigation_daily(date_id);
CREATE INDEX IF NOT EXISTS idx_ml_pred_date ON fact_ml_predictions(date_id);
