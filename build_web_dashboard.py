"""Build standalone Foundry IDN-GRID style interactive web dashboard from real data.

Uses real ADM2 GeoJSON polygons (`data/processed/diy_jateng_adm2.geojson`) rendered
as a crisp, 100% offline vector SVG choropleth — zero tile servers or API keys.

Outputs: `docs/dashboard_interaktif.html`
"""

import json
from pathlib import Path
import pandas as pd

from etl_fetch import REGIONS
from etl_load_pg import get_conn
from stage5_roi_sim import CAPEX_TABLE

OUT_HTML = Path("docs/dashboard_interaktif.html")
GEOJSON_PATH = Path("data/processed/diy_jateng_adm2.geojson")

# Map geoBoundaries shapeName -> our canonical kabupaten name
SHAPE_TO_KAB = {
    "Kulon Progo": "Kulon Progo",
    "Bantul": "Bantul",
    "Gunung Kidul": "Gunungkidul",
    "Sleman": "Sleman",
    "Purworejo": "Purworejo",
    "Magelang": "Kab. Magelang",
    "Klaten": "Klaten",
    "Wonogiri": "Wonogiri",
}


def extract_real_payload() -> dict:
    roi_df = pd.read_csv("data/processed/roi_simulation_table.csv")
    ml_df = pd.read_csv("data/processed/ml_test_predictions_2023_2025.csv")
    stage4 = json.loads(Path("data/processed/stage4_results.json").read_text(encoding="utf-8"))
    geojson = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))

    # Tag study polygons vs context neighbor polygons
    for feat in geojson["features"]:
        raw_name = feat["properties"]["name"]
        feat["properties"]["kab"] = SHAPE_TO_KAB.get(raw_name)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.kabupaten, d.month,
                       ROUND(AVG(f.nfr_mm)::numeric, 2) AS avg_nfr,
                       ROUND(AVG(f.rad_mj_m2)::numeric, 2) AS avg_rad,
                       ROUND(AVG(f.rain_mm)::numeric, 2) AS avg_rain
                FROM fact_irrigation_daily f
                JOIN dim_region r ON r.region_id = f.region_id
                JOIN dim_date d   ON d.date_id   = f.date_id
                GROUP BY r.kabupaten, d.month
                ORDER BY r.kabupaten, d.month
                """
            )
            monthly_rows = cur.fetchall()

            cur.execute(
                """
                SELECT r.kabupaten, d.year, SUM(f.need_irrigation) AS irrig_days
                FROM fact_irrigation_daily f
                JOIN dim_region r ON r.region_id = f.region_id
                JOIN dim_date d   ON d.date_id   = f.date_id
                GROUP BY r.kabupaten, d.year
                ORDER BY r.kabupaten, d.year
                """
            )
            yearly_rows = cur.fetchall()
    finally:
        conn.close()

    monthly_by_kab: dict[str, list[dict]] = {}
    for kab, m, nfr, rad, rain in monthly_rows:
        monthly_by_kab.setdefault(kab, []).append(
            {"month": int(m), "nfr": float(nfr), "rad": float(rad), "rain": float(rain)}
        )

    yearly_by_kab: dict[str, list[dict]] = {}
    for kab, yr, days in yearly_rows:
        yearly_by_kab.setdefault(kab, []).append({"year": int(yr), "days": int(days)})

    ml_df["month"] = pd.to_datetime(ml_df["full_date"]).dt.month
    ml_cal = (
        ml_df.groupby("month", as_index=False)
        .agg(prob_lr=("prob_lr", "mean"), actual=("target_next", "mean"))
        .sort_values("month")
    )

    base_roi = roi_df[roi_df["fuel_price_idr"] == 23700][
        [
            "kabupaten", "capacity_kwp", "land_mode", "land_area_ha", "diesel_l_per_m3",
            "annual_demand_m3", "annual_solar_m3", "solar_coverage_pct",
            "annual_diesel_saved_l", "annual_opex_low_idr", "annual_opex_high_idr",
        ]
    ].copy()
    base_roi["capex_low"] = base_roi["capacity_kwp"].map(lambda c: CAPEX_TABLE[float(c)][0])
    base_roi["capex_high"] = base_roi["capacity_kwp"].map(lambda c: CAPEX_TABLE[float(c)][1])

    matched_kabs = {f["properties"]["kab"] for f in geojson["features"] if f["properties"]["kab"]}
    assert len(matched_kabs) == 8, f"Missing kabupaten polygons: {matched_kabs}"
    assert len(base_roi) == 96

    reg_stats = {r["kabupaten"]: r for r in stage4["stats"]["regional_summary"]}
    regions_out = [
        {
            "kabupaten": r["kabupaten"],
            "provinsi": r["provinsi"],
            "lat": r["lat"],
            "lon": r["lon"],
            "mean_nfr": reg_stats[r["kabupaten"]]["mean_nfr_mm"],
            "pct_irrig": reg_stats[r["kabupaten"]]["pct_need_irrig"],
            "mean_rad": reg_stats[r["kabupaten"]]["mean_rad_mj"],
            "solar_m3_1kwp": reg_stats[r["kabupaten"]]["mean_solar_m3_1kwp"],
        }
        for r in REGIONS
    ]

    return {
        "geojson": geojson,
        "regions": regions_out,
        "roi": base_roi.to_dict(orient="records"),
        "monthly": monthly_by_kab,
        "yearly": yearly_by_kab,
        "stats": {
            "anova_F": round(stage4["stats"]["anova_nfr_F"], 2),
            "ttest_season_t": round(stage4["stats"]["ttest_nfr_kemarau_vs_hujan_t"], 2),
        },
        "ml": {
            "models": stage4["ml"]["models"],
            "calibration": ml_cal.round(4).to_dict(orient="records"),
        },
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>SOLAR-GRID · DIY &amp; Jateng Selatan</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  :root {
    --canvas: #F3F3F0;
    --panel: rgba(34, 35, 39, 0.94);
    --panel-soft: rgba(46, 48, 54, 0.92);
    --border: rgba(255, 255, 255, 0.09);
    --ink-light: #F3F4F6;
    --ink-muted: #9CA3AF;
    --ink-dark: #18181B;
    --teal: #38A89D;
    --teal-soft: #66C2B5;
    --lavender: #9B8EDB;
    --lavender-deep: #7B6CC4;
    --gold: #E5B94C;
    --font: "Segoe UI", -apple-system, BlinkMacSystemFont, Inter, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--font);
    background: var(--canvas);
    color: var(--ink-light);
    height: 100vh;
    width: 100vw;
    overflow: hidden;
    user-select: none;
  }

  /* Full-bleed crisp SVG vector map stage */
  #map-stage {
    position: fixed;
    inset: 0;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: radial-gradient(circle at 62% 52%, #FAF9F6 0%, #EFEFE9 100%);
  }
  #map-svg {
    width: 100%;
    height: 100%;
    display: block;
  }
  .poly-neighbor {
    fill: #E3E2DC;
    stroke: #F4F4F0;
    stroke-width: 0.9;
    transition: fill 0.2s;
  }
  .poly-study {
    stroke: #FFFFFF;
    stroke-width: 1.4;
    cursor: pointer;
    transition: fill 0.25s ease, stroke 0.15s ease, filter 0.15s ease;
  }
  .poly-study:hover {
    filter: brightness(0.95);
    stroke: #18181B;
    stroke-width: 1.8;
  }
  .poly-study.selected {
    stroke: #18181B;
    stroke-width: 2.3;
  }
  .ctx-label {
    font-family: var(--font);
    font-size: 9.5px;
    fill: #8E8E93;
    font-weight: 500;
    pointer-events: none;
    text-anchor: middle;
  }
  .kab-title {
    font-family: var(--font);
    font-size: 11.5px;
    font-weight: 700;
    fill: #18181B;
    pointer-events: none;
    text-anchor: middle;
  }
  .kab-sub {
    font-family: var(--font);
    font-size: 9.5px;
    font-weight: 600;
    pointer-events: none;
    text-anchor: middle;
  }
  .pill-rect {
    fill: #1C1D21;
    rx: 5;
    ry: 5;
    pointer-events: none;
  }
  .pill-txt {
    font-family: var(--font);
    font-size: 10px;
    font-weight: 700;
    fill: #FFFFFF;
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: central;
  }

  /* Hover tooltip */
  #tooltip {
    position: fixed;
    z-index: 30;
    pointer-events: none;
    display: none;
    background: rgba(24, 25, 29, 0.95);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 10px;
    padding: 9px 12px;
    font-size: 11.5px;
    line-height: 1.45;
    color: #F4F4F5;
    box-shadow: 0 10px 26px rgba(0,0,0,0.22);
    min-width: 195px;
  }
  #tooltip .tt-h { font-weight: 700; font-size: 12.5px; margin-bottom: 3px; color: #FFFFFF; }
  #tooltip .tt-r { display: flex; justify-content: space-between; gap: 14px; color: #D4D4D8; }
  #tooltip .tt-r b { color: #FFFFFF; font-variant-numeric: tabular-nums; }

  /* Top Floating Chrome (Foundry IDN-GRID faithful) */
  .top-bar {
    position: fixed; top: 14px; left: 16px; right: 16px; z-index: 20;
    display: flex; align-items: center; justify-content: space-between; pointer-events: none;
  }
  .top-bar > * { pointer-events: auto; }
  .brand-row { display: flex; align-items: center; gap: 8px; }
  .brand-mark {
    display: flex; align-items: center; gap: 7px; color: var(--ink-dark);
    font-weight: 800; font-size: 15px; letter-spacing: -0.3px;
  }
  .brand-icon {
    width: 22px; height: 22px; border-radius: 5px; background: #18181B; color: #FFFFFF;
    display: grid; place-items: center; font-size: 11px; font-weight: 800;
  }
  .chip-dark {
    background: var(--panel); color: #FFFFFF; font-size: 11.5px; font-weight: 700;
    padding: 5px 11px; border-radius: 999px; border: 1px solid var(--border);
    display: flex; align-items: center; gap: 6px;
  }
  .chip-dark span.sub { color: var(--ink-muted); font-weight: 500; }

  .nav-pills {
    display: flex; gap: 2px; background: var(--panel);
    border: 1px solid var(--border); border-radius: 999px; padding: 3px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
  }
  .nav-btn {
    border: none; background: transparent; color: var(--ink-muted); font-family: var(--font);
    font-size: 12px; font-weight: 600; padding: 6px 14px; border-radius: 999px; cursor: pointer;
    transition: all 0.15s;
  }
  .nav-btn:hover { color: #FFFFFF; }
  .nav-btn.active { background: rgba(255,255,255,0.14); color: #FFFFFF; }

  .status-pill {
    background: var(--panel); color: var(--gold); font-size: 11.5px; font-weight: 600;
    padding: 6px 13px; border-radius: 999px; border: 1px solid var(--border);
  }

  /* Left Matte Dark Panel (Foundry left card) */
  .sidebar {
    position: fixed; top: 58px; left: 16px; bottom: 16px; width: 315px; z-index: 15;
    background: var(--panel); backdrop-filter: blur(12px);
    border: 1px solid var(--border); border-radius: 16px;
    padding: 15px 15px 12px; display: flex; flex-direction: column; gap: 11px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.16); overflow-y: auto;
  }
  .sidebar::-webkit-scrollbar { width: 4px; }
  .sidebar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.16); border-radius: 4px; }
  .sb-title { font-size: 13px; font-weight: 700; color: #FFFFFF; }
  .sb-copy { font-size: 11.5px; color: var(--ink-muted); line-height: 1.45; }

  .seg-wrap { display: flex; flex-direction: column; gap: 6px; }
  .seg-row { display: flex; gap: 3px; background: rgba(255,255,255,0.06); padding: 3px; border-radius: 8px; }
  .seg-btn {
    flex: 1; border: none; background: transparent; color: var(--ink-muted);
    font-family: var(--font); font-size: 11px; font-weight: 600; padding: 5px 6px;
    border-radius: 6px; cursor: pointer; transition: all 0.14s;
  }
  .seg-btn.active { background: #F4F4F5; color: #18181B; }

  .sec-head {
    font-size: 11px; font-weight: 700; color: #E4E4E7;
    padding-top: 6px; border-top: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: center;
  }
  .sec-head span.muted { font-weight: 500; color: var(--ink-muted); font-size: 10.5px; }

  /* Foundry-style minimal stacked rows (no heavy boxes!) */
  .reg-list { display: flex; flex-direction: column; gap: 8px; }
  .reg-row { cursor: pointer; padding: 4px 6px; margin: 0 -6px; border-radius: 8px; transition: background 0.14s; }
  .reg-row:hover { background: rgba(255,255,255,0.06); }
  .reg-row.selected { background: rgba(255,255,255,0.10); }
  .rr-top { display: flex; justify-content: space-between; font-size: 12px; }
  .rr-name { font-weight: 600; color: #F4F4F5; }
  .rr-val { font-weight: 700; font-variant-numeric: tabular-nums; }
  .rr-sub { font-size: 10px; color: var(--ink-muted); margin: 1px 0 4px; display: flex; justify-content: space-between; }
  .rr-bar { height: 5px; background: rgba(255,255,255,0.09); border-radius: 2px; overflow: hidden; display: flex; }
  .rr-fill { height: 100%; transition: width 0.25s ease, background 0.25s ease; }

  .sb-footer {
    margin-top: auto; padding-top: 8px; border-top: 1px solid var(--border);
    font-size: 10.5px; color: var(--ink-muted); display: flex; flex-direction: column; gap: 5px;
  }
  .ramp-bar {
    height: 6px; border-radius: 999px;
    background: linear-gradient(90deg, #2A9D8F 0%, #66C2B5 35%, #B7B0DC 70%, #7B6CC4 100%);
  }
  .ramp-lbls { display: flex; justify-content: space-between; font-size: 10px; }

  /* Bottom Foundry Control Dock */
  .bottom-dock {
    position: fixed; bottom: 16px; left: 348px; right: 16px; z-index: 15;
    display: flex; flex-direction: column; gap: 7px; align-items: flex-start; pointer-events: none;
  }
  .bottom-dock > * { pointer-events: auto; }
  .mode-bar {
    display: flex; align-items: center; gap: 8px;
    background: var(--panel); border: 1px solid var(--border); border-radius: 999px; padding: 3px 10px 3px 4px;
  }
  .preset-btn {
    border: none; background: transparent; color: var(--ink-muted); font-family: var(--font);
    font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 999px; cursor: pointer;
  }
  .preset-btn.active { background: #F4F4F5; color: #18181B; }

  .scrubber {
    width: 100%; background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    padding: 9px 14px; display: flex; align-items: center; gap: 12px;
    box-shadow: 0 8px 22px rgba(0,0,0,0.16);
  }
  .play-btn {
    width: 28px; height: 28px; border-radius: 50%; border: none; background: #F4F4F5; color: #18181B;
    font-size: 10px; font-weight: 800; cursor: pointer; flex-shrink: 0; display: grid; place-items: center;
  }
  .slider-col { flex: 1; display: flex; flex-direction: column; gap: 2px; }
  .slider-meta { display: flex; justify-content: space-between; font-size: 11px; color: var(--ink-muted); }
  .slider-meta strong { color: #FFFFFF; font-size: 12px; font-variant-numeric: tabular-nums; }
  input[type="range"] { width: 100%; accent-color: #E5B94C; cursor: pointer; height: 4px; }

  /* Overlay Tabs (Iklim / ML / Ringkasan) */
  .overlay-view {
    position: fixed; top: 58px; left: 348px; right: 16px; bottom: 16px; z-index: 16;
    background: var(--panel); backdrop-filter: blur(14px);
    border: 1px solid var(--border); border-radius: 16px;
    padding: 20px 22px; overflow-y: auto; display: none;
    box-shadow: 0 14px 34px rgba(0,0,0,0.22);
  }
  .overlay-view.open { display: block; }
  .ov-h { font-size: 17px; font-weight: 700; color: #FFFFFF; }
  .ov-s { font-size: 11.5px; color: var(--ink-muted); margin: 3px 0 16px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: rgba(255,255,255,0.035); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
  .card h4 { font-size: 12.5px; color: #FFFFFF; margin-bottom: 3px; }
  .card .sub { font-size: 11px; color: var(--ink-muted); margin-bottom: 10px; }
  .ch-box { position: relative; height: 245px; }
  .tbl { width: 100%; border-collapse: collapse; font-size: 11.5px; margin-top: 6px; }
  .tbl th { text-align: left; padding: 7px 8px; color: var(--ink-muted); border-bottom: 1px solid var(--border); font-weight: 600; }
  .tbl td { padding: 7px 8px; border-bottom: 1px solid rgba(255,255,255,0.05); font-variant-numeric: tabular-nums; }
  .tbl tr.hi td { color: var(--teal-soft); font-weight: 700; background: rgba(56,168,157,0.10); }
  .cm-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
  .cm-box { background: rgba(255,255,255,0.04); border-radius: 9px; padding: 14px; text-align: center; }
  .cm-box .num { font-size: 24px; font-weight: 800; }
  .cm-box .lbl { font-size: 10.5px; color: var(--ink-muted); margin-top: 2px; }
</style>
</head>
<body>

<div id="map-stage">
  <svg id="map-svg" viewBox="0 0 1200 720" preserveAspectRatio="xMidYMid meet"></svg>
</div>
<div id="tooltip"></div>

<!-- Top Floating Bar -->
<div class="top-bar">
  <div class="brand-row">
    <div class="brand-mark"><div class="brand-icon">S</div>SOLAR-GRID</div>
    <div class="chip-dark">DIY-JATENG <span class="sub">Data riil</span></div>
  </div>

  <div class="nav-pills">
    <button class="nav-btn active" data-tab="map">Peta ROI</button>
    <button class="nav-btn" data-tab="climate">Iklim &amp; Sinergi</button>
    <button class="nav-btn" data-tab="ml">Prediksi ML</button>
    <button class="nav-btn" data-tab="summary">Sumber</button>
  </div>

  <div class="status-pill" id="top-status">15 Tahun · 1,05 Juta Baris</div>
</div>

<!-- Left Dark Panel -->
<aside class="sidebar">
  <div>
    <div class="sb-title">Kelayakan Pompa Irigasi Surya</div>
    <p class="sb-copy" style="margin-top:4px;">
      Simulasi neraca air padi &amp; titik impas (BEP) di 8 kabupaten DIY-Jateng (2011–2025). Klik wilayah di peta atau geser harga solar di bawah.
    </p>
  </div>

  <div class="seg-wrap">
    <div class="seg-row" id="ctrl-land">
      <button class="seg-btn active" data-val="Kelompok Tani (1 ha/kWp)">Kelompok Tani</button>
      <button class="seg-btn" data-val="Individu (1 ha)">Individu (1 ha)</button>
    </div>
    <div style="display:grid; grid-template-columns: 1.35fr 1fr; gap: 6px;">
      <div class="seg-row" id="ctrl-cap">
        <button class="seg-btn" data-val="1">1 kWp</button>
        <button class="seg-btn" data-val="3">3</button>
        <button class="seg-btn active" data-val="5">5 kWp</button>
      </div>
      <div class="seg-row" id="ctrl-rate">
        <button class="seg-btn active" data-val="0.04">0,04 L/m³</button>
        <button class="seg-btn" data-val="0.06">0,06</button>
      </div>
    </div>
  </div>

  <div class="sec-head">
    <span>Peringkat 8 Kabupaten</span>
    <span class="muted" id="sb-summary">-</span>
  </div>

  <div class="reg-list" id="reg-list"></div>

  <div class="sb-footer">
    <div class="ramp-bar"></div>
    <div class="ramp-lbls">
      <span style="color:#66C2B5">Cepat (&lt; 2,5 thn)</span>
      <span>Sedang (4–5 thn)</span>
      <span style="color:#B7B0DC">Lama (&gt; 8 thn)</span>
    </div>
    <div>Open-Meteo (CC BY 4.0) · NASA POWER · Tokopedia Nov 2026</div>
  </div>
</aside>

<!-- Bottom Fuel Price Scrubber -->
<div class="bottom-dock" id="bottom-dock">
  <div class="mode-bar">
    <button class="preset-btn" data-price="6800">Biosolar Rp 6.800</button>
    <button class="preset-btn" data-price="15000">Transisi Rp 15.000</button>
    <button class="preset-btn active" data-price="23700">Dexlite Rp 23.700</button>
  </div>
  <div class="scrubber">
    <button class="play-btn" id="play-btn" title="Animasi kenaikan harga solar">▶</button>
    <div class="slider-col">
      <div class="slider-meta">
        <span>Sensitivitas Harga Solar (Rp 6.800 – Rp 30.000/L)</span>
        <strong id="price-display">Rp 23.700 / L</strong>
      </div>
      <input type="range" id="price-slider" min="6800" max="30000" step="100" value="23700" />
    </div>
  </div>
</div>

<!-- Overlay: Climate & Synergy -->
<section class="overlay-view" id="view-climate">
  <div class="ov-h" id="clim-title">Iklim &amp; Sinergi Agroklimat — Gunungkidul</div>
  <div class="ov-s">ANOVA 8 Kabupaten: F = <span id="st-f"></span> (p &lt; 0,001) · Welch t-test Kemarau vs Hujan: t = <span id="st-t"></span> (klik kabupaten di panel kiri untuk ganti wilayah)</div>
  <div class="grid-2">
    <div class="card">
      <h4>Sinergi Bulanan: Kebutuhan Air (NFR) vs Radiasi Surya</h4>
      <div class="sub">Kebutuhan air memuncak di Apr–Jun bersamaan radiasi matahari tinggi (Jul–Okt masa Bera).</div>
      <div class="ch-box"><canvas id="chart-monthly"></canvas></div>
    </div>
    <div class="card">
      <h4>Tren Hari Butuh Irigasi Per Tahun (2011–2025)</h4>
      <div class="sub">Lonjakan merah menandai tahun kering El Niño (2018, 2019, 2023).</div>
      <div class="ch-box"><canvas id="chart-yearly"></canvas></div>
    </div>
  </div>
</section>

<!-- Overlay: ML H+1 -->
<section class="overlay-view" id="view-ml">
  <div class="ov-h">Prediksi Kebutuhan Irigasi H+1 (Test Out-of-Sample 2023–2025 · 5.808 Hari)</div>
  <div class="ov-s">Logistic Regression unggul (ROC-AUC 0,794); penalaan biaya FN:FP = 3:1 (t = 0,21) memangkas gagal siram 90%</div>
  <div class="grid-2">
    <div class="card">
      <h4>Kalibrasi Probabilitas Bulanan (Prediksi vs Aktual)</h4>
      <div class="sub">Kurva probabilitas Logistic Regression mengikuti kejadian aktual sepanjang tahun.</div>
      <div class="ch-box"><canvas id="chart-ml-cal"></canvas></div>
    </div>
    <div class="card">
      <h4>Confusion Matrix — Logistic Regression (t = 0,21)</h4>
      <div class="sub">Recall 97,33% · Gagal irigasi (FN) turun dari 849 ke 88 hari.</div>
      <div class="cm-grid">
        <div class="cm-box"><div class="num" style="color:var(--teal-soft)">3.209</div><div class="lbl">True Positive (Tepat Siram)</div></div>
        <div class="cm-box"><div class="num" style="color:#F87171">88</div><div class="lbl">False Negative (Gagal Siram · -90%)</div></div>
        <div class="cm-box"><div class="num" style="color:var(--gold)">2.227</div><div class="lbl">False Positive (Siaga Berlebih)</div></div>
        <div class="cm-box"><div class="num" style="color:#E4E4E7">284</div><div class="lbl">True Negative (Tepat Tidak Siram)</div></div>
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:14px;">
    <h4>Perbandingan Seluruh Model (Temporal Split Anti-Leakage)</h4>
    <table class="tbl" id="ml-table"></table>
  </div>
</section>

<!-- Overlay: Summary & Sources -->
<section class="overlay-view" id="view-summary">
  <div class="ov-h">Ringkasan Keputusan &amp; Sumber Data</div>
  <div class="ov-s">Tugas Besar Kecerdasan Bisnis — Kelas SI-C, UPN "Veteran" Yogyakarta (2026)</div>
  <div class="grid-2">
    <div class="card">
      <h4>Dua Tuas Keputusan Bisnis</h4>
      <p style="font-size:12px; color:#D4D4D8; line-height:1.65; margin-top:6px;">
        <strong>1. Skala Kelompok Tani (5 kWp / 5 ha):</strong> Hindari <em>over-sizing</em> pada petani individu 1 ha (1 kWp paling rasional). Pada skema komunal 5 ha, <strong>4 kabupaten</strong> (Gunungkidul, Klaten, Bantul, Wonogiri) sudah tembus BEP <strong>&lt; 5 tahun</strong> bahkan dengan Biosolar subsidi.<br/><br/>
        <strong>2. Sensitivitas Subsidi BBM:</strong> Jika subsidi Biosolar dibatasi pasca-2026 (Dexlite Rp 23.700/L), <strong>seluruh 8 kabupaten</strong> balik modal dalam <strong>1,20–2,77 tahun</strong>. Prioritas #1 Gunungkidul, #2 Klaten.
      </p>
    </div>
    <div class="card">
      <h4>Sumber Data Riil &amp; Atribusi</h4>
      <p style="font-size:11.5px; color:#D4D4D8; line-height:1.65; margin-top:6px;">
        • <strong>Open-Meteo Archive API (CC BY 4.0):</strong> 1.051.968 baris/jam (2011–2025, 0 null).<br/>
        • <strong>NASA POWER Project:</strong> 43.832 baris validasi silang radiasi (r = 0,74–0,78).<br/>
        • <strong>Batas Wilayah:</strong> geoBoundaries IDN ADM2 (30 poligon DIY–Jateng).<br/>
        • <strong>CAPEX Marketplace (Tokopedia Nov 2026):</strong> 1 kWp Rp 8,5–15,5 jt | 3 kWp Rp 20–38 jt | 5 kWp Rp 35–65 jt (+15% pasang, OPEX 2%/thn).
      </p>
    </div>
  </div>
</section>

<script>
const DATA = __PAYLOAD_JSON__;

const state = {
  tab: "map",
  land: "Kelompok Tani (1 ha/kWp)",
  cap: 5.0,
  rate: 0.04,
  price: 23700,
  selectedKab: "Gunungkidul",
  playing: false,
  timer: null,
};

const fmtRp = (n) => "Rp " + Math.round(n).toLocaleString("id-ID");

// Foundry-inspired continuous teal -> lavender color scale based on BEP years
function bepFill(bep) {
  if (bep === null || bep >= 9) return "#8B7EC8";     // deep lavender (slow)
  if (bep >= 6.5) return "#A79CD9";                   // medium lavender
  if (bep >= 5.0) return "#C6C0E4";                   // pale lavender (borderline)
  if (bep >= 3.5) return "#9AD4CB";                   // soft mint
  if (bep >= 2.2) return "#5BB8AC";                   // Foundry teal
  return "#2D9A8E";                                   // rich Foundry emerald-teal (very fast)
}
function bepTextCol(bep) {
  if (bep === null || bep > 5) return "#B8B0E6";
  if (bep <= 2.5) return "#5EEAD4";
  return "#99E2D8";
}

function computeScenario(kab) {
  const rec = DATA.roi.find(
    (r) => r.kabupaten === kab && r.land_mode === state.land && r.capacity_kwp === state.cap && r.diesel_l_per_m3 === state.rate
  );
  const gross = rec.annual_diesel_saved_l * state.price;
  const netLow = gross - rec.annual_opex_low_idr;
  const netHigh = gross - rec.annual_opex_high_idr;
  const bepLow = netLow > 0 ? rec.capex_low / netLow : null;
  const bepHigh = netHigh > 0 ? rec.capex_high / netHigh : null;
  return { ...rec, gross, netLow, netHigh, bepLow, bepHigh };
}

// ---------- Pure Vector SVG Projection (Equirectangular centered on DIY-Jateng) ----------
// Shift map cleanly to the right of the 315px sidebar
const LON_MIN = 109.72, LON_MAX = 111.35;
const LAT_MIN = -8.28,  LAT_MAX = -7.32;
const SVG_W = 1200, SVG_H = 720;
const PAD_L = 335, PAD_R = 45, PAD_T = 55, PAD_B = 90;

function project(lon, lat) {
  const x = PAD_L + ((lon - LON_MIN) / (LON_MAX - LON_MIN)) * (SVG_W - PAD_L - PAD_R);
  const y = PAD_T + ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * (SVG_H - PAD_T - PAD_B);
  return [x, y];
}

function ringToPath(ring) {
  return ring.map((pt, idx) => {
    const [x, y] = project(pt[0], pt[1]);
    return (idx === 0 ? "M" : "L") + x.toFixed(1) + "," + y.toFixed(1);
  }).join(" ") + " Z";
}

function geomToPath(geom) {
  if (geom.type === "Polygon") return geom.coordinates.map(ringToPath).join(" ");
  if (geom.type === "MultiPolygon") return geom.coordinates.map((p) => p.map(ringToPath).join(" ")).join(" ");
  return "";
}

// Clean hand-tuned label anchor coords (lon, lat) so all 8 study badges sit cleanly inside their polygon
const LABEL_POS = {
  "Kulon Progo":   [110.16, -7.83],
  "Bantul":        [110.35, -7.91],
  "Gunungkidul":   [110.63, -8.00],
  "Sleman":        [110.38, -7.72],
  "Purworejo":     [109.99, -7.72],
  "Kab. Magelang": [110.22, -7.53],
  "Klaten":        [110.62, -7.70],
  "Wonogiri":      [110.95, -7.89],
};
const NEIGHBOR_LABELS = [
  ["Kota Yogyakarta", 110.37, -7.80],
  ["Boyolali", 110.62, -7.48],
  ["Sukoharjo", 110.83, -7.68],
  ["Kebumen", 109.78, -7.68],
  ["Pacitan", 111.16, -8.12],
  ["Wonosobo", 109.92, -7.42],
];

const svg = document.getElementById("map-svg");
const SVG_NS = "http://www.w3.org/2000/svg";
const el = (tag, attrs = {}) => {
  const n = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
};

const gNeighbors = el("g");
const gStudy = el("g");
const gLabels = el("g");
svg.append(gNeighbors, gStudy, gLabels);

const studyPaths = {};
const labelPills = {};
const labelSubs = {};
const tooltip = document.getElementById("tooltip");

function initMap() {
  DATA.geojson.features.forEach((feat) => {
    const kab = feat.properties.kab;
    const d = geomToPath(feat.geometry);
    if (!kab) {
      gNeighbors.appendChild(el("path", { d, class: "poly-neighbor" }));
    } else {
      const path = el("path", { d, class: "poly-study" });
      path.addEventListener("mouseenter", (e) => showTooltip(kab, e));
      path.addEventListener("mousemove", (e) => moveTooltip(e));
      path.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
      path.addEventListener("click", () => selectKab(kab));
      gStudy.appendChild(path);
      studyPaths[kab] = path;
    }
  });

  // Subtle neighbor names for geographic context
  NEIGHBOR_LABELS.forEach(([name, lon, lat]) => {
    const [x, y] = project(lon, lat);
    const t = el("text", { x, y, class: "ctx-label" });
    t.textContent = name;
    gLabels.appendChild(t);
  });

  // Crisp Foundry-style kabupaten labels + compact black metric pills
  Object.entries(LABEL_POS).forEach(([kab, [lon, lat]]) => {
    const [x, y] = project(lon, lat);
    const g = el("g");

    const title = el("text", { x, y: y - 10, class: "kab-title" });
    title.textContent = kab;
    g.appendChild(title);

    const pillW = 66, pillH = 19;
    const rect = el("rect", { x: x - pillW / 2, y: y - 4, width: pillW, height: pillH, class: "pill-rect" });
    const txt = el("text", { x, y: y + 5.5, class: "pill-txt" });
    g.append(rect, txt);

    const sub = el("text", { x, y: y + 26, class: "kab-sub", fill: "#3F3F46" });
    g.appendChild(sub);

    gLabels.appendChild(g);
    labelPills[kab] = txt;
    labelSubs[kab] = sub;
  });
}

function showTooltip(kab, e) {
  const reg = DATA.regions.find((r) => r.kabupaten === kab);
  const sc = computeScenario(kab);
  tooltip.innerHTML = `
    <div class="tt-h">${kab} <span style="font-weight:500;color:#9CA3AF">(${reg.provinsi})</span></div>
    <div class="tt-r"><span>BEP (Low – High)</span><b>${sc.bepLow ? sc.bepLow.toFixed(2) : "N/A"} – ${sc.bepHigh ? sc.bepHigh.toFixed(2) : "N/A"} thn</b></div>
    <div class="tt-r"><span>Hemat Bersih/thn</span><b>${(sc.netLow / 1e6).toFixed(1)} jt</b></div>
    <div class="tt-r"><span>Solar Coverage</span><b>${sc.solar_coverage_pct.toFixed(1)}%</b></div>
    <div class="tt-r"><span>NFR / Radiasi</span><b>${reg.mean_nfr} mm · ${reg.mean_rad} MJ/m²</b></div>
  `;
  tooltip.style.display = "block";
  moveTooltip(e);
}
function moveTooltip(e) {
  tooltip.style.left = Math.min(window.innerWidth - 220, e.clientX + 14) + "px";
  tooltip.style.top = Math.min(window.innerHeight - 130, e.clientY + 14) + "px";
}

function selectKab(kab) {
  state.selectedKab = kab;
  renderAll();
  if (state.tab === "climate") renderClimateCharts();
}

function renderAll() {
  const computed = DATA.regions.map((reg) => ({ ...reg, ...computeScenario(reg.kabupaten) }));
  computed.sort((a, b) => (a.bepLow ?? 99) - (b.bepLow ?? 99));

  const viable = computed.filter((x) => x.bepLow !== null && x.bepLow <= 5).length;
  const avgBep = computed.reduce((s, x) => s + (x.bepLow ?? 0), 0) / computed.length;
  document.getElementById("sb-summary").textContent = `${viable}/8 layak · avg ${avgBep.toFixed(2)} thn`;
  document.getElementById("top-status").textContent = `${state.cap} kWp · ${viable}/8 Kab Layak (< 5 thn)`;

  // Update polygons & map pills
  computed.forEach((item) => {
    const p = studyPaths[item.kabupaten];
    if (p) {
      p.style.fill = bepFill(item.bepLow);
      p.classList.toggle("selected", item.kabupaten === state.selectedKab);
    }
    labelPills[item.kabupaten].textContent = item.bepLow ? `${item.bepLow.toFixed(2)} thn` : ">25 thn";
    labelSubs[item.kabupaten].textContent = `hemat ${(item.netLow / 1e6).toFixed(1)} jt/thn`;
  });

  // Update left panel ranked bars (Foundry minimal style)
  const listEl = document.getElementById("reg-list");
  listEl.innerHTML = "";
  const maxNet = Math.max(...computed.map((x) => Math.max(1, x.netLow)));

  computed.forEach((item) => {
    const fillCol = bepFill(item.bepLow);
    const txtCol = bepTextCol(item.bepLow);
    const wPct = Math.max(10, Math.min(100, (item.netLow / maxNet) * 100));
    const row = document.createElement("div");
    row.className = "reg-row" + (item.kabupaten === state.selectedKab ? " selected" : "");
    row.innerHTML = `
      <div class="rr-top">
        <span class="rr-name">${item.kabupaten}</span>
        <span class="rr-val" style="color:${txtCol}">${item.bepLow ? item.bepLow.toFixed(2) + " thn" : ">25 thn"}</span>
      </div>
      <div class="rr-sub">
        <span>Hemat ${(item.netLow / 1e6).toFixed(1)} jt/thn · Cov ${item.solar_coverage_pct.toFixed(0)}%</span>
        <span>${item.bepLow?.toFixed(1)}–${item.bepHigh?.toFixed(1)} thn</span>
      </div>
      <div class="rr-bar"><div class="rr-fill" style="width:${wPct}%; background:${fillCol}"></div></div>
    `;
    row.onclick = () => selectKab(item.kabupaten);
    listEl.appendChild(row);
  });
}

// Charts (Iklim & ML)
let chMonthly = null, chYearly = null, chMlCal = null;
const MONTHS = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agt","Sep","Okt","Nov","Des"];

function renderClimateCharts() {
  const kab = state.selectedKab;
  document.getElementById("clim-title").textContent = `Iklim & Sinergi Agroklimat — ${kab}`;
  document.getElementById("st-f").textContent = DATA.stats.anova_F;
  document.getElementById("st-t").textContent = DATA.stats.ttest_season_t;

  const mData = DATA.monthly[kab];
  if (chMonthly) chMonthly.destroy();
  chMonthly = new Chart(document.getElementById("chart-monthly"), {
    data: {
      labels: MONTHS,
      datasets: [
        { type: "bar", label: "NFR (mm/hr)", data: mData.map(x => x.nfr), backgroundColor: "rgba(91,184,172,0.75)", borderRadius: 3, yAxisID: "y" },
        { type: "line", label: "Radiasi (MJ/m²/hr)", data: mData.map(x => x.rad), borderColor: "#E5B94C", backgroundColor: "#E5B94C", tension: 0.35, yAxisID: "y1" },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#9CA3AF" }, grid: { color: "rgba(255,255,255,0.04)" } },
        y: { position: "left", ticks: { color: "#66C2B5" }, grid: { color: "rgba(255,255,255,0.05)" } },
        y1: { position: "right", min: 14, max: 22, ticks: { color: "#E5B94C" }, grid: { drawOnChartArea: false } },
      },
    },
  });

  const yData = DATA.yearly[kab];
  if (chYearly) chYearly.destroy();
  chYearly = new Chart(document.getElementById("chart-yearly"), {
    type: "bar",
    data: {
      labels: yData.map(x => x.year),
      datasets: [{
        label: "Hari Butuh Irigasi",
        data: yData.map(x => x.days),
        backgroundColor: yData.map(x => [2018, 2019, 2023].includes(x.year) ? "#E5B94C" : "rgba(155,142,219,0.68)"),
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#9CA3AF" }, grid: { display: false } },
        y: { ticks: { color: "#9CA3AF" }, grid: { color: "rgba(255,255,255,0.05)" } },
      },
    },
  });
}

function renderMlView() {
  if (!chMlCal) {
    const cal = DATA.ml.calibration;
    chMlCal = new Chart(document.getElementById("chart-ml-cal"), {
      type: "line",
      data: {
        labels: cal.map(x => MONTHS[x.month - 1]),
        datasets: [
          { label: "Prediksi (prob_lr)", data: cal.map(x => x.prob_lr), borderColor: "#66C2B5", tension: 0.35, borderWidth: 2.5 },
          { label: "Aktual (target_next)", data: cal.map(x => x.actual), borderColor: "#9B8EDB", borderDash: [5, 4], tension: 0.35, borderWidth: 2.5 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
        scales: {
          x: { ticks: { color: "#9CA3AF" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { min: 0.2, max: 1.0, ticks: { color: "#9CA3AF" }, grid: { color: "rgba(255,255,255,0.05)" } },
        },
      },
    });
  }
  const tbl = document.getElementById("ml-table");
  if (!tbl.innerHTML) {
    let html = "<thead><tr><th>Model</th><th>Acc</th><th>Recall</th><th>F1</th><th>AUC</th><th>FN (Gagal)</th><th>FP</th></tr></thead><tbody>";
    for (const [name, m] of Object.entries(DATA.ml.models)) {
      const hi = name.includes("Logistic Regression (FN:FP=3:1") ? ' class="hi"' : "";
      html += `<tr${hi}><td>${name}</td><td>${m.accuracy.toFixed(3)}</td><td>${m.recall.toFixed(3)}</td><td>${m.f1.toFixed(3)}</td><td>${m.roc_auc ? m.roc_auc.toFixed(3) : "-"}</td><td>${m.fn}</td><td>${m.fp}</td></tr>`;
    }
    tbl.innerHTML = html + "</tbody>";
  }
}

function bindSeg(id, key, isNum = false) {
  document.querySelectorAll(`#${id} .seg-btn`).forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll(`#${id} .seg-btn`).forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state[key] = isNum ? parseFloat(btn.dataset.val) : btn.dataset.val;
      renderAll();
    };
  });
}
bindSeg("ctrl-land", "land");
bindSeg("ctrl-cap", "cap", true);
bindSeg("ctrl-rate", "rate", true);

const slider = document.getElementById("price-slider");
const priceDisp = document.getElementById("price-display");
function setPrice(val) {
  state.price = Number(val);
  slider.value = state.price;
  priceDisp.textContent = fmtRp(state.price) + " / L";
  document.querySelectorAll(".preset-btn").forEach((p) => p.classList.toggle("active", Number(p.dataset.price) === state.price));
  renderAll();
}
slider.oninput = (e) => setPrice(e.target.value);
document.querySelectorAll(".preset-btn").forEach((btn) => { btn.onclick = () => setPrice(btn.dataset.price); });

document.getElementById("play-btn").onclick = () => {
  const btn = document.getElementById("play-btn");
  if (state.playing) {
    clearInterval(state.timer);
    state.playing = false;
    btn.textContent = "▶";
  } else {
    if (state.price >= 24000) setPrice(6800);
    state.playing = true;
    btn.textContent = "❚❚";
    state.timer = setInterval(() => {
      if (state.price >= 23700) {
        setPrice(23700);
        clearInterval(state.timer);
        state.playing = false;
        btn.textContent = "▶";
        return;
      }
      setPrice(state.price + 400);
    }, 110);
  }
};

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.tab = btn.dataset.tab;
    document.querySelectorAll(".overlay-view").forEach((v) => v.classList.remove("open"));
    document.getElementById("bottom-dock").style.display = state.tab === "map" ? "flex" : "none";
    if (state.tab !== "map") {
      document.getElementById(`view-${state.tab}`).classList.add("open");
      if (state.tab === "climate") renderClimateCharts();
      if (state.tab === "ml") renderMlView();
    }
  };
});

initMap();
renderAll();
</script>
</body>
</html>
"""


def main() -> None:
    payload = extract_real_payload()
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    html = HTML_TEMPLATE.replace("__PAYLOAD_JSON__", json.dumps(payload, ensure_ascii=False))
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Generated {OUT_HTML} ({OUT_HTML.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
