"""Build standalone Foundry IDN-GRID style interactive web dashboard from real data.

Uses real ADM2 GeoJSON polygons (`data/processed/diy_jateng_adm2.geojson`) rendered
as a crisp, 100% offline vector SVG choropleth — zero tile servers or API keys.

Outputs: `docs/dashboard_interaktif.html`
"""

import base64
import json
from pathlib import Path
import pandas as pd

from etl_fetch import REGIONS
from etl_load_pg import get_conn
from stage5_roi_sim import CAPEX_TABLE

OUT_HTML = Path("docs/dashboard_interaktif.html")
GEOJSON_PATH = Path("data/processed/diy_jateng_adm2.geojson")
HILLSHADE_PATH = Path("data/processed/java_hillshade.jpg")

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

    hillshade_b64 = ""
    if HILLSHADE_PATH.exists():
        hillshade_b64 = "data:image/jpeg;base64," + base64.b64encode(HILLSHADE_PATH.read_bytes()).decode("ascii")

    return {
        "geojson": geojson,
        "hillshade": hillshade_b64,
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
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  :root {
    --ocean: #FFFFFF;
    --land: #EBEBE8;
    --panel: rgba(52, 54, 59, 0.93);
    --panel-deep: rgba(38, 40, 44, 0.96);
    --border: rgba(255, 255, 255, 0.10);
    --ink-light: #F4F4F5;
    --ink-muted: #A6A9B0;
    --ink-dark: #18181B;
    --teal-txt: #1A7A6E;
    --lav-txt: #6453B4;
    --gold: #E8C05A;
    --font: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
    --mono: "Inter", -apple-system, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--font);
    font-weight: 400;
    background: var(--ocean);
    color: var(--ink-light);
    height: 100vh;
    width: 100vw;
    overflow: hidden;
    user-select: none;
    -webkit-font-smoothing: antialiased;
  }

  /* Subtle coastal ocean gradient + high-precision SVG cartography */
  #map-stage {
    position: fixed;
    inset: 0;
    z-index: 1;
    background: linear-gradient(180deg, #F6F8FA 0%, #EDF2F7 100%);
    cursor: grab;
  }
  #map-stage:active { cursor: grabbing; }
  #map-svg {
    width: 100%;
    height: 100%;
    display: block;
    shape-rendering: geometricPrecision;
  }

  .grat-line {
    stroke: rgba(100, 116, 139, 0.14);
    stroke-width: 0.6;
    stroke-dasharray: 2 3;
    vector-effect: non-scaling-stroke;
    pointer-events: none;
  }
  .grat-lbl {
    font-family: var(--font); font-size: 8.5px; fill: #94A3B8; font-weight: 400;
    pointer-events: none;
  }
  .ocean-lbl {
    font-family: var(--font); font-size: 11px; fill: #94A3B8; font-weight: 500;
    letter-spacing: 5px; opacity: 0.65; pointer-events: none; text-anchor: middle;
  }
  .peak-lbl {
    font-family: var(--font); font-size: 8.5px; fill: #64748B; font-weight: 500;
    pointer-events: none;
  }

  .poly-neighbor {
    fill: #EAEAE6;
    stroke: #F8FAFC;
    stroke-width: 0.7;
    vector-effect: non-scaling-stroke;
  }
  .poly-study {
    stroke: #FFFFFF;
    stroke-width: 1.1;
    vector-effect: non-scaling-stroke;
    cursor: pointer;
    transition: fill 0.22s ease, opacity 0.2s ease, filter 0.2s ease;
  }
  .poly-study.dimmed { opacity: 0.90; }
  .poly-study:hover { opacity: 1; }
  .poly-study.selected {
    opacity: 1;
    stroke: #FFFFFF;
    stroke-width: 2.0;
    filter: drop-shadow(0 3px 8px rgba(15, 23, 42, 0.22));
  }

  .ctx-label {
    font-family: var(--font); font-size: 9.5px; fill: #9CA0A8; font-weight: 400;
    pointer-events: none; text-anchor: middle;
  }
  .leader-line {
    stroke: #6B7280; stroke-width: 0.85; fill: none; pointer-events: none;
  }
  .anchor-dot {
    fill: #374151; stroke: #FFFFFF; stroke-width: 1.3; pointer-events: none;
  }
  .kab-name {
    font-family: var(--font); font-size: 11px; font-weight: 600; fill: #1F2937;
    pointer-events: none; text-anchor: middle; letter-spacing: -0.15px;
  }
  .kab-status {
    font-family: var(--font); font-size: 9.5px; font-weight: 500;
    pointer-events: none; text-anchor: middle;
  }
  .pill-bg {
    fill: #1F2024; rx: 9; ry: 9; pointer-events: none;
  }
  .pill-txt {
    font-family: var(--font); font-size: 9.2px; font-weight: 500; fill: #F9FAFB;
    font-variant-numeric: tabular-nums;
    pointer-events: none; text-anchor: middle; dominant-baseline: central;
  }

  /* Hover tooltip */
  #tooltip {
    position: fixed; z-index: 30; pointer-events: none; display: none;
    background: var(--panel-deep); border: 1px solid var(--border);
    border-radius: 10px; padding: 9px 12px; font-size: 11.5px; line-height: 1.45;
    color: #F4F4F5; box-shadow: 0 10px 26px rgba(0,0,0,0.18); min-width: 195px;
  }
  #tooltip .tt-h { font-weight: 700; font-size: 12px; margin-bottom: 3px; color: #FFFFFF; }
  #tooltip .tt-r { display: flex; justify-content: space-between; gap: 14px; color: #D4D4D8; }
  #tooltip .tt-r b { color: #FFFFFF; font-variant-numeric: tabular-nums; }

  /* Top Floating Chrome (Foundry matte slate pills) */
  .top-bar {
    position: fixed; top: 12px; left: 14px; right: 14px; z-index: 20;
    display: flex; align-items: center; justify-content: space-between; pointer-events: none;
  }
  .top-bar > * { pointer-events: auto; }
  .brand-row { display: flex; align-items: center; gap: 9px; }
  .brand-mark {
    display: flex; align-items: center; gap: 6px; color: var(--ink-dark);
    font-weight: 600; font-size: 14.5px; letter-spacing: -0.3px;
  }
  .chip-dark {
    background: var(--panel); color: #FFFFFF; font-size: 11.5px; font-weight: 700;
    padding: 6px 12px; border-radius: 999px; border: 1px solid var(--border);
    display: flex; align-items: center; gap: 7px; box-shadow: 0 4px 14px rgba(0,0,0,0.10);
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
    transition: all 0.14s;
  }
  .nav-btn:hover { color: #FFFFFF; }
  .nav-btn.active { background: rgba(255,255,255,0.18); color: #FFFFFF; }

  .status-pill {
    background: var(--panel); color: var(--gold); font-size: 11.5px; font-weight: 600;
    padding: 6px 14px; border-radius: 999px; border: 1px solid var(--border);
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
  }

  /* Left Matte Slate Panel (Foundry exact proportion & calm grey) */
  .sidebar {
    position: fixed; top: 56px; left: 14px; bottom: 14px; width: 300px; z-index: 15;
    background: var(--panel); backdrop-filter: blur(14px);
    border: 1px solid var(--border); border-radius: 16px;
    padding: 14px 15px 12px; display: flex; flex-direction: column; gap: 10px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.14); overflow-y: auto;
  }
  .sidebar::-webkit-scrollbar { width: 4px; }
  .sidebar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.18); border-radius: 4px; }
  .sb-title { font-size: 12.5px; font-weight: 600; color: #D4D6DC; }
  .sb-copy { font-size: 11.5px; color: var(--ink-muted); line-height: 1.48; }

  .seg-wrap { display: flex; flex-direction: column; gap: 5px; }
  .seg-row { display: flex; gap: 3px; background: rgba(0,0,0,0.18); padding: 3px; border-radius: 999px; }
  .seg-btn {
    flex: 1; border: none; background: transparent; color: var(--ink-muted);
    font-family: var(--font); font-size: 11px; font-weight: 600; padding: 5px 6px;
    border-radius: 999px; cursor: pointer; transition: all 0.14s;
  }
  .seg-btn.active { background: #F4F4F5; color: #1F2024; }

  .sec-head {
    font-size: 11.5px; font-weight: 700; color: #F4F4F5;
    padding-top: 8px; border-top: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: center;
  }
  .sec-head span.muted { font-weight: 500; color: var(--ink-muted); font-size: 10.5px; }

  /* Foundry-exact clean flat bar rows */
  .reg-list { display: flex; flex-direction: column; gap: 7px; }
  .reg-row { cursor: pointer; padding: 3px 6px; margin: 0 -6px; border-radius: 8px; transition: background 0.14s; }
  .reg-row:hover { background: rgba(255,255,255,0.07); }
  .reg-row.selected { background: rgba(255,255,255,0.12); }
  .rr-top { display: flex; justify-content: space-between; font-size: 12px; }
  .rr-name { font-weight: 600; color: #FFFFFF; }
  .rr-val { font-weight: 700; color: #FFFFFF; font-variant-numeric: tabular-nums; }
  .rr-sub { font-size: 10px; color: var(--ink-muted); margin: 1px 0 4px; display: flex; justify-content: space-between; }
  .rr-bar { height: 5px; background: rgba(255,255,255,0.14); border-radius: 2px; overflow: hidden; }
  .rr-fill { height: 100%; transition: width 0.25s ease, background 0.25s ease; }

  .sb-footer {
    margin-top: auto; padding-top: 8px; border-top: 1px solid var(--border);
    font-size: 10px; color: var(--ink-muted); display: flex; flex-direction: column; gap: 4px;
  }
  .leg-row { display: flex; gap: 12px; align-items: center; }
  .sq { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }

  /* Bottom Foundry Dock (2 stacked pills + dotted amber timeline scrubber) */
  .bottom-dock {
    position: fixed; bottom: 14px; left: 328px; right: 14px; z-index: 15;
    display: flex; flex-direction: column; gap: 6px; align-items: flex-start; pointer-events: none;
  }
  .bottom-dock > * { pointer-events: auto; }
  .dock-pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: var(--panel); border: 1px solid var(--border); border-radius: 999px;
    padding: 4px 12px; font-size: 11px; color: var(--ink-muted);
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
  }
  .preset-btn {
    border: none; background: transparent; color: var(--ink-muted); font-family: var(--font);
    font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 999px; cursor: pointer;
  }
  .preset-btn.active { background: #FFFFFF; color: #1F2024; }
  .mini-ramp {
    width: 82px; height: 6px; border-radius: 999px;
    background: linear-gradient(90deg, #9E93D3 0%, #DCD7EE 45%, #8AD5CB 75%, #4DB5A7 100%);
  }

  .scrubber {
    width: 100%; background: var(--panel); border: 1px solid var(--border); border-radius: 999px;
    padding: 7px 14px; display: flex; align-items: center; gap: 12px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.14);
  }
  .play-btn {
    width: 28px; height: 28px; border-radius: 50%; border: none; background: #FFFFFF; color: #1F2024;
    font-size: 10px; font-weight: 800; cursor: pointer; flex-shrink: 0; display: grid; place-items: center;
  }
  .slider-col { flex: 1; display: flex; flex-direction: column; gap: 2px; }
  .slider-ticks {
    display: flex; justify-content: space-between; font-size: 10px; color: var(--ink-muted); padding: 0 2px;
  }
  input[type="range"] {
    width: 100%; accent-color: #FFFFFF; cursor: pointer; height: 4px;
    background: repeating-linear-gradient(90deg, #E8C05A 0px, #E8C05A 4px, transparent 4px, transparent 8px);
    border-radius: 999px; appearance: none;
  }
  input[type="range"]::-webkit-slider-thumb {
    appearance: none; width: 14px; height: 14px; border-radius: 50%;
    background: #FFFFFF; box-shadow: 0 1px 5px rgba(0,0,0,0.4); cursor: pointer;
  }
  .price-readout { text-align: right; min-width: 112px; }
  .price-readout strong { display: block; font-size: 12px; color: #FFFFFF; font-variant-numeric: tabular-nums; }
  .price-readout span { font-size: 10px; color: var(--gold); }

  /* Overlay Tabs (Iklim / ML / Ringkasan) */
  .overlay-view {
    position: fixed; top: 56px; left: 328px; right: 14px; bottom: 14px; z-index: 16;
    background: var(--panel); backdrop-filter: blur(16px);
    border: 1px solid var(--border); border-radius: 16px;
    padding: 20px 22px; overflow-y: auto; display: none;
    box-shadow: 0 14px 34px rgba(0,0,0,0.18);
  }
  .overlay-view.open { display: block; }
  .ov-h { font-size: 17px; font-weight: 700; color: #FFFFFF; }
  .ov-s { font-size: 11.5px; color: var(--ink-muted); margin: 3px 0 16px; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: rgba(0,0,0,0.16); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
  .card h4 { font-size: 12.5px; color: #FFFFFF; margin-bottom: 3px; }
  .card .sub { font-size: 11px; color: var(--ink-muted); margin-bottom: 10px; }
  .ch-box { position: relative; height: 245px; }
  .tbl { width: 100%; border-collapse: collapse; font-size: 11.5px; margin-top: 6px; }
  .tbl th { text-align: left; padding: 7px 8px; color: var(--ink-muted); border-bottom: 1px solid var(--border); font-weight: 600; }
  .tbl td { padding: 7px 8px; border-bottom: 1px solid rgba(255,255,255,0.06); font-variant-numeric: tabular-nums; }
  .tbl tr.hi td { color: #7EE0D2; font-weight: 700; background: rgba(91,192,179,0.14); }
  .cm-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
  .cm-box { background: rgba(255,255,255,0.06); border-radius: 9px; padding: 14px; text-align: center; }
  .cm-box .num { font-size: 24px; font-weight: 800; }
  .cm-box .lbl { font-size: 10.5px; color: var(--ink-muted); margin-top: 2px; }
</style>
</head>
<body>

<div id="map-stage">
  <svg id="map-svg" viewBox="0 0 1280 740" preserveAspectRatio="xMidYMid slice"></svg>
</div>
<div id="tooltip"></div>

<!-- Top Floating Bar -->
<div class="top-bar">
  <div class="brand-row">
    <div class="brand-mark">Irigasi Surya</div>
    <div class="chip-dark">DIY &amp; Jateng <span class="sub">8 kabupaten</span></div>
  </div>

  <div class="nav-pills">
    <button class="nav-btn active" data-tab="map">Peta ROI</button>
    <button class="nav-btn" data-tab="climate">Iklim &amp; Sinergi</button>
    <button class="nav-btn" data-tab="ml">Prediksi ML</button>
    <button class="nav-btn" data-tab="summary">Sumber</button>
  </div>

  <div class="status-pill" id="top-status">Model kami · 15 Thn (2011–2025)</div>
</div>

<!-- Left Matte Slate Panel -->
<aside class="sidebar">
  <div>
    <div class="sb-title">Kelayakan pompa irigasi surya</div>
    <p class="sb-copy" style="margin-top:5px;">
      Perkiraan model kami: kebutuhan air padi harian (NFR) dan titik impas (BEP) pompa surya vs diesel di 8 kabupaten, dari 1,05 juta baris cuaca per jam.
    </p>
  </div>

  <div class="seg-wrap">
    <div class="seg-row" id="ctrl-land">
      <button class="seg-btn active" data-val="Kelompok Tani (1 ha/kWp)">Kelompok Tani</button>
      <button class="seg-btn" data-val="Individu (1 ha)">Individu (1 ha)</button>
    </div>
    <div class="seg-row" id="ctrl-cap">
      <button class="seg-btn" data-val="1">1 kWp</button>
      <button class="seg-btn" data-val="3">3 kWp</button>
      <button class="seg-btn active" data-val="5">5 kWp</button>
    </div>
  </div>

  <div class="sec-head">
    <span>Peringkat 8 kabupaten</span>
    <span class="muted" id="sb-summary">-</span>
  </div>

  <div class="reg-list" id="reg-list"></div>

  <div class="sb-footer">
    <div class="leg-row">
      <span><span class="sq" style="background:#5BC0B3"></span>layak (&lt; 5 thn)</span>
      <span><span class="sq" style="background:#A79ED6"></span>lama (&gt; 5 thn)</span>
    </div>
  </div>
</aside>

<!-- Bottom Foundry Scrubber (minimal, zero play button) -->
<div class="bottom-dock" id="bottom-dock">
  <div class="scrubber" style="padding: 9px 18px;">
    <div class="slider-col">
      <div class="slider-ticks">
        <span class="tick-link" data-price="6800" style="cursor:pointer;">Rp 6.800 (Biosolar)</span>
        <span class="tick-link" data-price="15000" style="cursor:pointer;">Rp 15.000</span>
        <span class="tick-link" data-price="23700" style="cursor:pointer;">Rp 23.700 (Dexlite)</span>
        <span class="tick-link" data-price="30000" style="cursor:pointer;">Rp 30.000</span>
      </div>
      <input type="range" id="price-slider" min="6800" max="30000" step="100" value="6800" />
    </div>
    <div class="price-readout">
      <strong id="price-display">Rp 6.800 / L</strong>
      <span id="price-tag">Biosolar subsidi</span>
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
      <div class="sub">Batang emas menandai lonjakan tahun kering El Niño (2018, 2019, 2023).</div>
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
        <div class="cm-box"><div class="num" style="color:#7EE0D2">3.209</div><div class="lbl">True Positive (Tepat Siram)</div></div>
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
      <p style="font-size:12px; color:#E4E4E7; line-height:1.65; margin-top:6px;">
        <strong>1. Skala Kelompok Tani (5 kWp / 5 ha):</strong> Hindari <em>over-sizing</em> pada petani individu 1 ha (1 kWp paling rasional). Pada skema komunal 5 ha, <strong>4 kabupaten</strong> (Gunungkidul, Klaten, Bantul, Wonogiri) sudah tembus BEP <strong>&lt; 5 tahun</strong> bahkan dengan Biosolar subsidi.<br/><br/>
        <strong>2. Sensitivitas Subsidi BBM:</strong> Jika subsidi Biosolar dibatasi pasca-2026 (Dexlite Rp 23.700/L), <strong>seluruh 8 kabupaten</strong> balik modal dalam <strong>1,20–2,77 tahun</strong>. Prioritas #1 Gunungkidul, #2 Klaten.
      </p>
    </div>
    <div class="card">
      <h4>Sumber Data Riil &amp; Atribusi</h4>
      <p style="font-size:11.5px; color:#E4E4E7; line-height:1.65; margin-top:6px;">
        • <strong>Open-Meteo Archive API (CC BY 4.0):</strong> 1.051.968 baris/jam (2011–2025, 0 null).<br/>
        • <strong>NASA POWER Project:</strong> 43.832 baris validasi silang radiasi (r = 0,74–0,78).<br/>
        • <strong>Batas Wilayah:</strong> geoBoundaries IDN ADM2 (66 poligon Jawa Tengah &amp; DIY).<br/>
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
  price: 6800,
  selectedKab: "Gunungkidul",
};

const fmtRp = (n) => "Rp " + Math.round(n).toLocaleString("id-ID");

function lerpHex(a, b, t) {
  const c = Math.max(0, Math.min(1, t));
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return "#" + pa.map((v, i) => Math.round(v + (pb[i] - v) * c).toString(16).padStart(2, "0")).join("");
}

// Smooth continuous 3-stop Foundry diverging ramp: teal (#2D9C8D) -> pearl (#E6E8EB) -> lavender (#8A7DC7)
function bepFill(bep, minBep, maxBep) {
  if (bep === null) return "#8A7DC7";
  const rel = maxBep > minBep ? (bep - minBep) / (maxBep - minBep) : 0.5;
  // Blend 55% absolute scale (1.2..8.5 yr) + 45% relative spread so transition is always smooth & legible
  const absT = Math.max(0, Math.min(1, (bep - 1.2) / 6.5));
  const t = Math.max(0, Math.min(1, 0.50 * absT + 0.50 * rel));
  if (t <= 0.5) return lerpHex("#2D9C8D", "#DCEAE7", t * 2);
  return lerpHex("#E2E0EC", "#8A7DC7", (t - 0.5) * 2);
}
function bepStatusCol(bep) {
  return (bep === null || bep > 5) ? "#6453B4" : "#1E7F74";
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

// Projection framed on Central/South Java coastline (edge-to-edge landmass, white Indian Ocean below!)
const LON_MIN = 109.25, LON_MAX = 111.75;
const LAT_MIN = -8.48,  LAT_MAX = -7.02;
const SVG_W = 1280, SVG_H = 740;
const PAD_L = 310, PAD_R = 20, PAD_T = 25, PAD_B = 55;

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

// Non-overlapping Foundry callout anchors: [anchorLon, anchorLat, labelLon, labelLat]
// Radiates cleanly into white Indian Ocean below & open Central Java north!
const CALLOUTS = {
  "Purworejo":     [109.98, -7.72, 109.68, -8.04],
  "Kulon Progo":   [110.16, -7.83, 110.03, -8.17],
  "Bantul":        [110.35, -7.91, 110.36, -8.25],
  "Gunungkidul":   [110.62, -8.00, 110.74, -8.26],
  "Wonogiri":      [110.95, -7.90, 111.18, -8.12],
  "Kab. Magelang": [110.22, -7.52, 110.05, -7.24],
  "Sleman":        [110.38, -7.71, 110.42, -7.30],
  "Klaten":        [110.63, -7.70, 110.95, -7.42],
};
const NEIGHBOR_LABELS = [
  ["Kebumen", 109.66, -7.68],
  ["Semarang", 110.42, -7.12],
  ["Surakarta", 110.83, -7.57],
  ["Pacitan", 111.14, -8.16],
];

const svg = document.getElementById("map-svg");
const SVG_NS = "http://www.w3.org/2000/svg";
const el = (tag, attrs = {}) => {
  const n = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
};

// Soft cartographic coastal shadow filter + land clipPath for hillshade
const defs = el("defs");
const flt = el("filter", { id: "land-shadow", x: "-5%", y: "-5%", width: "110%", height: "115%" });
flt.appendChild(el("feDropShadow", { dx: "0", dy: "3", stdDeviation: "4", "flood-color": "#334155", "flood-opacity": "0.14" }));
defs.appendChild(flt);
const landClip = el("clipPath", { id: "java-land-clip" });
defs.appendChild(landClip);
svg.appendChild(defs);

const gViewport = el("g");
const gGrat = el("g");
const gLandWrap = el("g", { filter: "url(#land-shadow)" });
const gNeighbors = el("g");
const gStudy = el("g");
const gEnclaves = el("g");
const gHillshade = el("g", { "clip-path": "url(#java-land-clip)", style: "mix-blend-mode: multiply; opacity: 0.38; pointer-events: none;" });
const gLandmarks = el("g");
const gCallouts = el("g");
gLandWrap.append(gNeighbors, gStudy, gEnclaves);
gViewport.append(gGrat, gLandWrap, gHillshade, gLandmarks, gCallouts);
svg.appendChild(gViewport);

const studyPaths = {};
const labelStatus = {};
const labelPills = {};
const tooltip = document.getElementById("tooltip");

const PEAKS = [
  ["G. Merapi", 110.446, -7.541],
  ["G. Sumbing", 110.072, -7.384],
  ["G. Lawu", 111.192, -7.625],
];

function initMap() {
  // Subtle lat/lon graticule grid
  [109.5, 110.0, 110.5, 111.0, 111.5].forEach((lon) => {
    const [x, y1] = project(lon, LAT_MAX);
    const [, y2] = project(lon, LAT_MIN);
    gGrat.appendChild(el("line", { x1: x, y1: 0, x2: x, y2: SVG_H, class: "grat-line" }));
    const t = el("text", { x: x + 4, y: 74, class: "grat-lbl" });
    t.textContent = `${lon.toFixed(1)}°E`;
    gGrat.appendChild(t);
  });
  [-7.5, -8.0].forEach((lat) => {
    const [, y] = project(LON_MIN, lat);
    gGrat.appendChild(el("line", { x1: PAD_L, y1: y, x2: SVG_W, y2: y, class: "grat-line" }));
    const t = el("text", { x: SVG_W - 36, y: y - 4, class: "grat-lbl" });
    t.textContent = `${Math.abs(lat).toFixed(1)}°S`;
    gGrat.appendChild(t);
  });

  // Subtle Indian Ocean watermark
  const [ox, oy] = project(109.85, -8.32);
  const oceanTxt = el("text", { x: ox, y: oy, class: "ocean-lbl" });
  oceanTxt.textContent = "SAMUDRA HINDIA";
  gGrat.appendChild(oceanTxt);

  DATA.geojson.features.forEach((feat) => {
    const kab = feat.properties.kab;
    const rawName = feat.properties.name;
    const d = geomToPath(feat.geometry);
    landClip.appendChild(el("path", { d }));
    if (!kab) {
      const target = (rawName === "Kota Yogyakarta" || rawName === "Kota Magelang") ? gEnclaves : gNeighbors;
      target.appendChild(el("path", { d, class: "poly-neighbor" }));
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

  // Real Esri World Hillshade elevation relief clipped strictly to Java landmass
  if (DATA.hillshade) {
    gHillshade.appendChild(el("image", {
      href: DATA.hillshade,
      x: PAD_L,
      y: PAD_T,
      width: SVG_W - PAD_L - PAD_R,
      height: SVG_H - PAD_T - PAD_B,
      preserveAspectRatio: "none",
    }));
  }

  // Subtle mountain peak triangles (explains orographic rain/clouds in Magelang & Sleman)
  PEAKS.forEach(([name, lon, lat]) => {
    const [x, y] = project(lon, lat);
    gLandmarks.appendChild(el("polygon", {
      points: `${x},${y - 4.5} ${x - 4},${y + 3} ${x + 4},${y + 3}`,
      fill: "#64748B", opacity: "0.7",
    }));
    const t = el("text", { x: x + 6, y: y + 2.5, class: "peak-lbl" });
    t.textContent = name;
    gLandmarks.appendChild(t);
  });

  // Smooth zoom & pan (wheel + drag)
  let scale = 1, tx = 0, ty = 0, dragging = false, sx = 0, sy = 0;
  const applyTransform = () => gViewport.setAttribute("transform", `translate(${tx.toFixed(1)},${ty.toFixed(1)}) scale(${scale.toFixed(3)})`);
  const stage = document.getElementById("map-stage");
  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.12 : 0.89;
    const next = Math.max(0.85, Math.min(3.0, scale * factor));
    const rect = svg.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * SVG_W;
    const my = ((e.clientY - rect.top) / rect.height) * SVG_H;
    tx = mx - (mx - tx) * (next / scale);
    ty = my - (my - ty) * (next / scale);
    scale = next;
    applyTransform();
  }, { passive: false });
  stage.addEventListener("mousedown", (e) => {
    if (e.target.classList.contains("poly-study")) return;
    dragging = true; sx = e.clientX - tx; sy = e.clientY - ty;
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    tx = e.clientX - sx; ty = e.clientY - sy;
    applyTransform();
  });
  window.addEventListener("mouseup", () => { dragging = false; });
  stage.addEventListener("dblclick", () => { scale = 1; tx = 0; ty = 0; applyTransform(); });

  NEIGHBOR_LABELS.forEach(([name, lon, lat]) => {
    const [x, y] = project(lon, lat);
    const t = el("text", { x, y, class: "ctx-label" });
    t.textContent = name;
    gCallouts.appendChild(t);
  });

  // Foundry-style leader lines: terminate cleanly at outer edge (never cross text!)
  Object.entries(CALLOUTS).forEach(([kab, [aLon, aLat, lLon, lLat]]) => {
    const [ax, ay] = project(aLon, aLat);
    const [lx, ly] = project(lLon, lLat);
    const g = el("g");

    // Pick clean attachment point on callout block based on relative direction
    let tx = lx, ty = ly - 17; // default: label is below anchor -> attach to top of title
    if (Math.abs(ly - ay) < 35 && lx > ax) {
      tx = lx - 44; ty = ly + 6; // label is to the right (Wonogiri) -> attach to left side
    } else if (ly < ay) {
      tx = lx; ty = ly + 36;     // label is above anchor (Magelang, Sleman, Klaten) -> attach to bottom of pill
    }

    g.appendChild(el("line", { x1: ax, y1: ay, x2: tx, y2: ty, class: "leader-line" }));
    g.appendChild(el("circle", { cx: ax, cy: ay, r: 2.6, class: "anchor-dot" }));

    const title = el("text", { x: lx, y: ly - 4, class: "kab-name" });
    title.textContent = kab;
    g.appendChild(title);

    const status = el("text", { x: lx, y: ly + 9, class: "kab-status" });
    g.appendChild(status);

    const pillW = 72, pillH = 18;
    g.appendChild(el("rect", { x: lx - pillW / 2, y: ly + 15, width: pillW, height: pillH, class: "pill-bg" }));
    const pillTxt = el("text", { x: lx, y: ly + 24, class: "pill-txt" });
    g.appendChild(pillTxt);

    gCallouts.appendChild(g);
    labelStatus[kab] = status;
    labelPills[kab] = pillTxt;
  });
}

function showTooltip(kab, e) {
  const reg = DATA.regions.find((r) => r.kabupaten === kab);
  const sc = computeScenario(kab);
  tooltip.innerHTML = `
    <div class="tt-h">${kab} <span style="font-weight:500;color:#B4B6BC">(${reg.provinsi})</span></div>
    <div class="tt-r"><span>BEP (Low – High)</span><b>${sc.bepLow ? sc.bepLow.toFixed(2) : "N/A"} – ${sc.bepHigh ? sc.bepHigh.toFixed(2) : "N/A"} thn</b></div>
    <div class="tt-r"><span>Hemat Bersih/thn</span><b>${(sc.netLow / 1e6).toFixed(1)} jt</b></div>
    <div class="tt-r"><span>Solar Coverage</span><b>${sc.solar_coverage_pct.toFixed(1)}%</b></div>
    <div class="tt-r"><span>NFR / Radiasi</span><b>${reg.mean_nfr.toFixed(2)} mm · ${reg.mean_rad.toFixed(1)} MJ/m²</b></div>
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
  const validBeps = computed.map((x) => x.bepLow).filter((v) => v !== null);
  const minBep = Math.min(...validBeps);
  const maxBep = Math.max(...validBeps);
  const avgBep = computed.reduce((s, x) => s + (x.bepLow ?? 0), 0) / computed.length;
  document.getElementById("sb-summary").textContent = `${viable}/8 layak · avg ${avgBep.toFixed(2)} thn`;
  document.getElementById("top-status").textContent = `${state.cap} kWp · ${viable}/8 Kab Layak (< 5 thn)`;

  computed.forEach((item) => {
    const p = studyPaths[item.kabupaten];
    if (p) {
      const isSel = item.kabupaten === state.selectedKab;
      p.style.fill = bepFill(item.bepLow, minBep, maxBep);
      p.classList.toggle("selected", isSel);
      p.classList.toggle("dimmed", !isSel);
      if (isSel) gStudy.appendChild(p); // bring to front so full outline renders cleanly
    }
    labelStatus[item.kabupaten].textContent = item.bepLow ? `BEP ${item.bepLow.toFixed(2)} thn` : "tidak layak";
    labelStatus[item.kabupaten].setAttribute("fill", bepStatusCol(item.bepLow));
    labelPills[item.kabupaten].textContent = `${(item.netLow / 1e6).toFixed(1)} jt/thn`;
  });

  const listEl = document.getElementById("reg-list");
  listEl.innerHTML = "";
  const maxNet = Math.max(...computed.map((x) => Math.max(1, x.netLow)));

  computed.forEach((item) => {
    const fillCol = bepFill(item.bepLow, minBep, maxBep);
    const wPct = Math.max(12, Math.min(100, (item.netLow / maxNet) * 100));
    const row = document.createElement("div");
    row.className = "reg-row" + (item.kabupaten === state.selectedKab ? " selected" : "");
    row.innerHTML = `
      <div class="rr-top">
        <span class="rr-name">${item.kabupaten}</span>
        <span class="rr-val">${item.bepLow ? item.bepLow.toFixed(2) + " thn" : ">25 thn"}</span>
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
        { type: "bar", label: "NFR (mm/hr)", data: mData.map(x => x.nfr), backgroundColor: "rgba(91,192,179,0.80)", borderRadius: 3, yAxisID: "y" },
        { type: "line", label: "Radiasi (MJ/m²/hr)", data: mData.map(x => x.rad), borderColor: "#E8C05A", backgroundColor: "#E8C05A", tension: 0.35, yAxisID: "y1" },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#B4B6BC" }, grid: { color: "rgba(255,255,255,0.05)" } },
        y: { position: "left", ticks: { color: "#8AD5CB" }, grid: { color: "rgba(255,255,255,0.06)" } },
        y1: { position: "right", min: 14, max: 22, ticks: { color: "#E8C05A" }, grid: { drawOnChartArea: false } },
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
        backgroundColor: yData.map(x => [2018, 2019, 2023].includes(x.year) ? "#E8C05A" : "rgba(167,156,214,0.75)"),
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#B4B6BC" }, grid: { display: false } },
        y: { ticks: { color: "#B4B6BC" }, grid: { color: "rgba(255,255,255,0.06)" } },
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
          { label: "Prediksi (prob_lr)", data: cal.map(x => x.prob_lr), borderColor: "#8AD5CB", tension: 0.35, borderWidth: 2.5 },
          { label: "Aktual (target_next)", data: cal.map(x => x.actual), borderColor: "#C2BAE4", borderDash: [5, 4], tension: 0.35, borderWidth: 2.5 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
        scales: {
          x: { ticks: { color: "#B4B6BC" }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { min: 0.2, max: 1.0, ticks: { color: "#B4B6BC" }, grid: { color: "rgba(255,255,255,0.06)" } },
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

const slider = document.getElementById("price-slider");
const priceDisp = document.getElementById("price-display");
const priceTag = document.getElementById("price-tag");
function setPrice(val) {
  state.price = Number(val);
  slider.value = state.price;
  priceDisp.textContent = fmtRp(state.price) + " / L";
  priceTag.textContent = state.price <= 7500 ? "Biosolar subsidi" : (state.price >= 22000 ? "Non-subsidi" : "Skenario transisi");
  document.querySelectorAll(".tick-link").forEach((t) => {
    t.style.color = Number(t.dataset.price) === state.price ? "#FFFFFF" : "#A6A9B0";
    t.style.fontWeight = Number(t.dataset.price) === state.price ? "700" : "500";
  });
  renderAll();
}
slider.oninput = (e) => setPrice(e.target.value);
document.querySelectorAll(".tick-link").forEach((el) => { el.onclick = () => setPrice(el.dataset.price); });

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
