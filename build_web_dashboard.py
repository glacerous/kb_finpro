"""Build standalone Foundry-style interactive web dashboard from real project data.

Reads real data from PostgreSQL (`kb_solar_irrigation`) and `data/processed/`,
embeds it into a single self-contained HTML file: `docs/dashboard_interaktif.html`.
"""

import json
from pathlib import Path
import pandas as pd

from etl_fetch import REGIONS
from etl_load_pg import get_conn
from stage5_roi_sim import CAPEX_TABLE

OUT_HTML = Path("docs/dashboard_interaktif.html")


def extract_real_payload() -> dict:
    roi_df = pd.read_csv("data/processed/roi_simulation_table.csv")
    ml_df = pd.read_csv("data/processed/ml_test_predictions_2023_2025.csv")
    stage4 = json.loads(Path("data/processed/stage4_results.json").read_text(encoding="utf-8"))

    # Query monthly climate & yearly irrigation days directly from PostgreSQL
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

    # Monthly ML calibration (2023-2025 out-of-sample)
    ml_df["month"] = pd.to_datetime(ml_df["full_date"]).dt.month
    ml_cal = (
        ml_df.groupby("month", as_index=False)
        .agg(prob_lr=("prob_lr", "mean"), actual=("target_next", "mean"), count=("target_next", "count"))
        .sort_values("month")
    )

    # Compact ROI records (deduplicated across fuel_scenario since JS computes dynamically from fuel_price!)
    base_roi = roi_df[roi_df["fuel_price_idr"] == 23700][
        [
            "kabupaten", "capacity_kwp", "land_mode", "land_area_ha", "diesel_l_per_m3",
            "annual_demand_m3", "annual_solar_m3", "solar_coverage_pct",
            "annual_diesel_saved_l", "annual_opex_low_idr", "annual_opex_high_idr",
        ]
    ].copy()
    base_roi["capex_low"] = base_roi["capacity_kwp"].map(lambda c: CAPEX_TABLE[float(c)][0])
    base_roi["capex_high"] = base_roi["capacity_kwp"].map(lambda c: CAPEX_TABLE[float(c)][1])

    assert len(base_roi) == 96, f"Expected 96 unique base ROI scenarios, got {len(base_roi)}"
    assert len(monthly_by_kab) == 8, "Expected 8 kabupaten monthly climate series"

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
            "mean_rain": reg_stats[r["kabupaten"]]["mean_rain_mm"],
        }
        for r in REGIONS
    ]

    return {
        "regions": regions_out,
        "roi": base_roi.to_dict(orient="records"),
        "monthly": monthly_by_kab,
        "yearly": yearly_by_kab,
        "stats": {
            "anova_F": round(stage4["stats"]["anova_nfr_F"], 2),
            "anova_p": stage4["stats"]["anova_nfr_p"],
            "ttest_season_t": round(stage4["stats"]["ttest_nfr_kemarau_vs_hujan_t"], 2),
            "mean_nfr_kemarau": round(stage4["stats"]["mean_nfr_kemarau"], 2),
            "mean_nfr_hujan": round(stage4["stats"]["mean_nfr_hujan"], 2),
        },
        "ml": {
            "train_rows": stage4["ml"]["train_rows"],
            "test_rows": stage4["ml"]["test_rows"],
            "models": stage4["ml"]["models"],
            "top_features": stage4["ml"]["top10_rf_features"],
            "calibration": ml_cal.round(4).to_dict(orient="records"),
        },
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>SOLAR-GRID DIY & Jateng — Dashboard Interaktif Pompa Irigasi Surya</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  :root {
    --glass-bg: rgba(24, 25, 29, 0.90);
    --glass-border: rgba(255, 255, 255, 0.10);
    --pill-bg: rgba(34, 36, 42, 0.92);
    --text-main: #F4F4F5;
    --text-muted: #A1A1AA;
    --mint: #2DD4BF;
    --amber: #F59E0B;
    --rose: #F43F5E;
    --purple: #A78BFA;
    --font: "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: var(--font); background: #E9ECEF; color: var(--text-main); overflow: hidden; height: 100vh; width: 100vw; }
  #map { position: fixed; inset: 0; z-index: 1; background: #E9ECEF; }

  /* Floating Top Bar (Foundry style) */
  .top-bar {
    position: fixed; top: 14px; left: 16px; right: 16px; z-index: 20;
    display: flex; align-items: center; justify-content: space-between; pointer-events: none;
  }
  .top-bar > * { pointer-events: auto; }
  .brand-pill {
    display: flex; align-items: center; gap: 10px;
    background: var(--glass-bg); backdrop-filter: blur(14px);
    border: 1px solid var(--glass-border); border-radius: 999px;
    padding: 7px 14px; box-shadow: 0 8px 24px rgba(0,0,0,0.22);
  }
  .brand-logo {
    width: 22px; height: 22px; border-radius: 6px; background: var(--mint); color: #0F172A;
    font-weight: 800; font-size: 12px; display: grid; place-items: center;
  }
  .brand-title { font-weight: 700; font-size: 13.5px; letter-spacing: 0.3px; }
  .brand-tag { font-size: 11px; color: var(--text-muted); background: rgba(255,255,255,0.08); padding: 2px 8px; border-radius: 999px; }

  .nav-pills {
    display: flex; gap: 4px; background: var(--glass-bg); backdrop-filter: blur(14px);
    border: 1px solid var(--glass-border); border-radius: 999px; padding: 4px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.22);
  }
  .nav-btn {
    border: none; background: transparent; color: var(--text-muted); font-family: var(--font);
    font-size: 12.5px; font-weight: 600; padding: 6px 14px; border-radius: 999px; cursor: pointer;
    transition: all 0.15s ease;
  }
  .nav-btn:hover { color: var(--text-main); }
  .nav-btn.active { background: rgba(255,255,255,0.14); color: #FFFFFF; }

  .meta-pill {
    background: var(--glass-bg); backdrop-filter: blur(14px);
    border: 1px solid var(--glass-border); border-radius: 999px;
    padding: 7px 14px; font-size: 11.5px; color: #FDE68A; font-weight: 600;
    box-shadow: 0 8px 24px rgba(0,0,0,0.22);
  }

  /* Left Dark Glass Sidebar */
  .sidebar {
    position: fixed; top: 68px; left: 16px; bottom: 16px; width: 340px; z-index: 15;
    background: var(--glass-bg); backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border); border-radius: 18px;
    padding: 16px; display: flex; flex-direction: column; gap: 12px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.28); overflow-y: auto;
  }
  .sidebar::-webkit-scrollbar { width: 5px; }
  .sidebar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
  .sb-kicker { font-size: 11px; color: var(--mint); font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; }
  .sb-desc { font-size: 12px; color: var(--text-muted); line-height: 1.45; }

  .ctrl-group { display: flex; flex-direction: column; gap: 5px; }
  .ctrl-label { font-size: 10.5px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
  .seg-row { display: flex; gap: 4px; background: rgba(255,255,255,0.06); padding: 3px; border-radius: 10px; }
  .seg-btn {
    flex: 1; border: none; background: transparent; color: var(--text-muted);
    font-family: var(--font); font-size: 11.5px; font-weight: 600; padding: 6px 6px;
    border-radius: 7px; cursor: pointer; transition: all 0.15s;
  }
  .seg-btn.active { background: #FFFFFF; color: #111827; }

  .kpi-strip { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .kpi-mini {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 9px 11px;
  }
  .kpi-mini .k-lbl { font-size: 10.5px; color: var(--text-muted); }
  .kpi-mini .k-val { font-size: 18px; font-weight: 700; margin-top: 2px; color: #FFFFFF; }
  .kpi-mini .k-sub { font-size: 10px; color: var(--mint); margin-top: 1px; }

  .reg-list { display: flex; flex-direction: column; gap: 7px; }
  .reg-item {
    background: rgba(255,255,255,0.04); border: 1px solid transparent;
    border-radius: 11px; padding: 8px 10px; cursor: pointer; transition: all 0.15s;
  }
  .reg-item:hover { background: rgba(255,255,255,0.09); }
  .reg-item.selected { border-color: var(--mint); background: rgba(45, 212, 191, 0.10); }
  .reg-top { display: flex; justify-content: space-between; align-items: baseline; font-size: 12.5px; }
  .reg-name { font-weight: 600; color: #FFFFFF; }
  .reg-bep { font-weight: 700; font-variant-numeric: tabular-nums; }
  .reg-meta { font-size: 10.5px; color: var(--text-muted); margin: 2px 0 5px; display: flex; justify-content: space-between; }
  .bar-track { height: 5px; background: rgba(255,255,255,0.10); border-radius: 999px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 999px; transition: width 0.25s ease, background 0.25s ease; }

  .legend-row { display: flex; gap: 12px; font-size: 10.5px; color: var(--text-muted); padding-top: 4px; border-top: 1px solid var(--glass-border); }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }

  /* Bottom Fuel Price Scrubber (Foundry timeline style) */
  .bottom-dock {
    position: fixed; bottom: 16px; left: 372px; right: 16px; z-index: 15;
    display: flex; flex-direction: column; gap: 8px; align-items: flex-start; pointer-events: none;
  }
  .bottom-dock > * { pointer-events: auto; }
  .preset-row { display: flex; gap: 6px; }
  .preset-pill {
    background: var(--glass-bg); backdrop-filter: blur(14px); border: 1px solid var(--glass-border);
    color: var(--text-muted); border-radius: 999px; padding: 5px 12px; font-size: 11.5px;
    font-weight: 600; cursor: pointer; font-family: var(--font); transition: all 0.15s;
  }
  .preset-pill.active, .preset-pill:hover { color: #FFFFFF; border-color: rgba(255,255,255,0.35); }
  .scrubber {
    width: 100%; background: var(--glass-bg); backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border); border-radius: 14px;
    padding: 10px 16px; display: flex; align-items: center; gap: 14px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.24);
  }
  .play-btn {
    width: 32px; height: 32px; border-radius: 50%; border: none; background: #FFFFFF; color: #111827;
    font-size: 12px; font-weight: 800; cursor: pointer; flex-shrink: 0; display: grid; place-items: center;
  }
  .slider-wrap { flex: 1; display: flex; flex-direction: column; gap: 3px; }
  .slider-top { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); }
  .slider-top strong { color: #FFFFFF; font-size: 12.5px; }
  input[type="range"] { width: 100%; accent-color: var(--mint); cursor: pointer; }

  /* Map custom floating badges (Foundry MW-pill style) */
  .map-badge {
    background: rgba(17, 18, 22, 0.90); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.18);
    border-radius: 8px; padding: 4px 8px; font-family: var(--font); font-size: 11px;
    white-space: nowrap; box-shadow: 0 4px 12px rgba(0,0,0,0.28); text-align: center;
  }
  .map-badge .mb-name { font-weight: 700; display: block; font-size: 11px; }
  .map-badge .mb-val { font-weight: 700; font-size: 11.5px; }

  /* Full Overlay Views (Iklim / ML / Ringkasan) */
  .overlay-view {
    position: fixed; top: 68px; left: 372px; right: 16px; bottom: 16px; z-index: 16;
    background: var(--glass-bg); backdrop-filter: blur(18px);
    border: 1px solid var(--glass-border); border-radius: 18px;
    padding: 20px 22px; overflow-y: auto; display: none;
    box-shadow: 0 14px 36px rgba(0,0,0,0.32);
  }
  .overlay-view.open { display: block; }
  .ov-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px; border-bottom: 1px solid var(--glass-border); padding-bottom: 10px; }
  .ov-title { font-size: 18px; font-weight: 700; }
  .ov-sub { font-size: 12px; color: var(--text-muted); }
  .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .chart-card {
    background: rgba(255,255,255,0.04); border: 1px solid var(--glass-border);
    border-radius: 14px; padding: 14px;
  }
  .chart-card h4 { font-size: 13px; margin-bottom: 4px; color: #FFFFFF; }
  .chart-card p { font-size: 11px; color: var(--text-muted); margin-bottom: 10px; }
  .chart-box { position: relative; height: 245px; }

  .data-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
  .data-table th { text-align: left; padding: 8px; color: var(--text-muted); border-bottom: 1px solid var(--glass-border); font-weight: 600; }
  .data-table td { padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); font-variant-numeric: tabular-nums; }
  .data-table tr.hi td { color: var(--mint); font-weight: 700; background: rgba(45,212,191,0.08); }
  .cm-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
  .cm-cell { background: rgba(255,255,255,0.05); border-radius: 10px; padding: 14px; text-align: center; }
  .cm-cell .n { font-size: 26px; font-weight: 800; }
  .cm-cell .l { font-size: 11px; color: var(--text-muted); margin-top: 3px; }
</style>
</head>
<body>

<div id="map"></div>

<!-- Top Floating Bar -->
<div class="top-bar">
  <div class="brand-pill">
    <div class="brand-logo">SG</div>
    <span class="brand-title">SOLAR-GRID</span>
    <span class="brand-tag">DIY-JATENG · 8 Kab</span>
  </div>

  <div class="nav-pills">
    <button class="nav-btn active" data-tab="map">Peta ROI</button>
    <button class="nav-btn" data-tab="climate">Iklim &amp; Sinergi</button>
    <button class="nav-btn" data-tab="ml">Prediksi ML H+1</button>
    <button class="nav-btn" data-tab="summary">Ringkasan</button>
  </div>

  <div class="meta-pill">Data Riil 2011–2025 · 1,05 Juta Baris</div>
</div>

<!-- Left Dark Glass Sidebar -->
<aside class="sidebar">
  <div>
    <div class="sb-kicker">Kelayakan Pompa Surya Padi</div>
    <p class="sb-desc" style="margin-top:4px;">
      Simulasi riil 15 tahun (Open-Meteo + NASA POWER + CAPEX Tokopedia Nov 2026). Klik kabupaten untuk fokus &amp; geser harga solar di bawah.
    </p>
  </div>

  <div class="ctrl-group">
    <span class="ctrl-label">Mode Kepemilikan Lahan</span>
    <div class="seg-row" id="ctrl-land">
      <button class="seg-btn active" data-val="Kelompok Tani (1 ha/kWp)">Kelompok Tani</button>
      <button class="seg-btn" data-val="Individu (1 ha)">Individu (1 ha)</button>
    </div>
  </div>

  <div style="display:grid; grid-template-columns: 1.25fr 1fr; gap: 8px;">
    <div class="ctrl-group">
      <span class="ctrl-label">Kapasitas Pompa</span>
      <div class="seg-row" id="ctrl-cap">
        <button class="seg-btn" data-val="1">1 kWp</button>
        <button class="seg-btn" data-val="3">3</button>
        <button class="seg-btn active" data-val="5">5 kWp</button>
      </div>
    </div>
    <div class="ctrl-group">
      <span class="ctrl-label">Diesel (L/m³)</span>
      <div class="seg-row" id="ctrl-rate">
        <button class="seg-btn active" data-val="0.04">0,04</button>
        <button class="seg-btn" data-val="0.06">0,06</button>
      </div>
    </div>
  </div>

  <div class="kpi-strip">
    <div class="kpi-mini">
      <div class="k-lbl">Rata-rata BEP (Low)</div>
      <div class="k-val" id="kpi-bep">-</div>
      <div class="k-sub" id="kpi-viable">-</div>
    </div>
    <div class="kpi-mini">
      <div class="k-lbl">Cakupan Surya</div>
      <div class="k-val" id="kpi-cov">-</div>
      <div class="k-sub" id="kpi-save">-</div>
    </div>
  </div>

  <div class="ctrl-label" style="margin-top:2px;">Peringkat 8 Kabupaten (Tercepat Balik Modal)</div>
  <div class="reg-list" id="reg-list"></div>

  <div class="legend-row">
    <span><span class="dot" style="background:var(--mint)"></span>&lt; 3 thn (Sangat Layak)</span>
    <span><span class="dot" style="background:var(--amber)"></span>3–5 thn</span>
    <span><span class="dot" style="background:var(--rose)"></span>&gt; 5 thn</span>
  </div>
</aside>

<!-- Bottom Fuel Price Scrubber (visible on Map tab) -->
<div class="bottom-dock" id="bottom-dock">
  <div class="preset-row">
    <button class="preset-pill" data-price="6800">Biosolar Subsidi (Rp 6.800/L)</button>
    <button class="preset-pill" data-price="15000">Transisi (Rp 15.000/L)</button>
    <button class="preset-pill active" data-price="23700">Dexlite Non-Subsidi (Rp 23.700/L)</button>
  </div>
  <div class="scrubber">
    <button class="play-btn" id="play-btn" title="Animasi kenaikan harga BBM">▶</button>
    <div class="slider-wrap">
      <div class="slider-top">
        <span>Simulasi Harga Solar Real-Time (Rp 6.800 – Rp 30.000/L)</span>
        <strong id="price-display">Rp 23.700 / liter</strong>
      </div>
      <input type="range" id="price-slider" min="6800" max="30000" step="100" value="23700" />
    </div>
  </div>
</div>

<!-- Overlay Tab: Climate & Synergy -->
<section class="overlay-view" id="view-climate">
  <div class="ov-header">
    <div>
      <div class="ov-title" id="clim-title">Iklim &amp; Sinergi Agroklimat — Gunungkidul</div>
      <div class="ov-sub">Klik kabupaten di panel kiri untuk melihat profil iklimnya. ANOVA 8 Kab: F = <span id="st-f"></span> (p &lt; 0,001) · Welch t-test Kemarau vs Hujan: t = <span id="st-t"></span></div>
    </div>
  </div>
  <div class="chart-grid">
    <div class="chart-card">
      <h4>Sinergi Bulanan: Kebutuhan Air (NFR) vs Radiasi Surya</h4>
      <p>Saat kebutuhan air sawah melonjak di musim kemarau (Apr–Jun), pasokan matahari juga tinggi (Bulan 7–10 masa Bera).</p>
      <div class="chart-box"><canvas id="chart-monthly"></canvas></div>
    </div>
    <div class="chart-card">
      <h4>Tren Hari Butuh Irigasi Per Tahun (2011–2025)</h4>
      <p>Menangkap lonjakan kekeringan pada tahun fenomena El Niño (2018, 2019, 2023).</p>
      <div class="chart-box"><canvas id="chart-yearly"></canvas></div>
    </div>
  </div>
</section>

<!-- Overlay Tab: ML H+1 -->
<section class="overlay-view" id="view-ml">
  <div class="ov-header">
    <div>
      <div class="ov-title">Model Prediktif ML H+1 (Test Out-of-Sample 2023–2025 · 5.808 Hari)</div>
      <div class="ov-sub">Logistic Regression unggul atas baseline &amp; Random Forest; tuning FN:FP = 3:1 (t = 0,21) pangkas gagal siram 90%</div>
    </div>
  </div>
  <div class="chart-grid">
    <div class="chart-card">
      <h4>Kalibrasi Probabilitas Bulanan (Prediksi vs Aktual)</h4>
      <p>Rata-rata probabilitas Logistic Regression menempel erat dengan kejadian aktual sepanjang tahun.</p>
      <div class="chart-box"><canvas id="chart-ml-cal"></canvas></div>
    </div>
    <div class="chart-card">
      <h4>Confusion Matrix — Logistic Regression (t = 0,21)</h4>
      <p>Penalti biaya 3:1 menghasilkan Recall 97,33% dan menekan gagal irigasi (FN) dari 849 ke 88 hari.</p>
      <div class="cm-grid">
        <div class="cm-cell"><div class="n" style="color:var(--mint)">3.209</div><div class="l">True Positive (Tepat Siram)</div></div>
        <div class="cm-cell"><div class="n" style="color:var(--rose)">88</div><div class="l">False Negative (Gagal Siram · -90%)</div></div>
        <div class="cm-cell"><div class="n" style="color:var(--amber)">2.227</div><div class="l">False Positive (Siaga Berlebih)</div></div>
        <div class="cm-cell"><div class="n" style="color:var(--text-main)">284</div><div class="l">True Negative (Tepat Tidak Siram)</div></div>
      </div>
    </div>
  </div>
  <div class="chart-card" style="margin-top:16px;">
    <h4>Perbandingan Seluruh Model (Temporal Split Anti-Leakage)</h4>
    <table class="data-table" id="ml-table"></table>
  </div>
</section>

<!-- Overlay Tab: Summary -->
<section class="overlay-view" id="view-summary">
  <div class="ov-header">
    <div>
      <div class="ov-title">Ringkasan Eksekutif &amp; Sumber Data Riil</div>
      <div class="ov-sub">Tugas Besar Kecerdasan Bisnis — Kelas SI-C, UPN "Veteran" Yogyakarta (2026)</div>
    </div>
  </div>
  <div class="chart-grid">
    <div class="chart-card">
      <h4>2 Tuas Keputusan Bisnis Utama</h4>
      <p style="color:var(--text-main); font-size:12.5px; line-height:1.6;">
        <strong>1. Skala Kelompok Tani (5 kWp / 5 ha):</strong> Hindari <em>over-sizing</em> pada petani individu 1 ha (1 kWp paling efisien). Pada skema patungan 5 ha, <strong>4 kabupaten</strong> (Gunungkidul, Klaten, Bantul, Wonogiri) sudah tembus BEP <strong>&lt; 5 tahun</strong> bahkan dengan Biosolar subsidi.<br/><br/>
        <strong>2. Risiko Pencabutan Subsidi BBM:</strong> Begitu harga solar beralih ke Dexlite (Rp 23.700/L), <strong>seluruh 8 kabupaten</strong> balik modal dalam <strong>1,20 – 2,77 tahun</strong>. Prioritas investasi #1 Gunungkidul &amp; #2 Klaten.
      </p>
    </div>
    <div class="chart-card">
      <h4>Sumber Data &amp; Atribusi Wajib</h4>
      <p style="color:var(--text-main); font-size:12px; line-height:1.6;">
        • <strong>Open-Meteo Archive API (CC BY 4.0):</strong> 1.051.968 baris/jam (2011–2025, 0 null).<br/>
        • <strong>NASA POWER Project (AG Daily):</strong> 43.832 baris validasi silang (r = 0,74–0,78).<br/>
        • <strong>CAPEX Marketplace (Tokopedia, Nov 2026):</strong> 1 kWp Rp 8,5–15,5 jt | 3 kWp Rp 20–38 jt | 5 kWp Rp 35–65 jt (+15% instalasi, OPEX 2%/thn).<br/>
        • <strong>Standar Agronomi:</strong> FAO-56, KP-01 PUPR, kurva debit studi Gowa (Unram).
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
const bepColor = (bep) => (bep === null || bep > 5) ? "#F43F5E" : (bep <= 3 ? "#2DD4BF" : "#F59E0B");

// Initialize clean CartoDB Positron map (Foundry minimalist style)
const map = L.map("map", { zoomControl: false, attributionControl: true }).setView([-7.78, 110.35], 10);
L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  attribution: "&copy; OpenStreetMap &copy; CARTO | Weather: Open-Meteo (CC BY 4.0)",
  maxZoom: 15,
}).addTo(map);

const markers = {};
const circles = {};

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

function renderAll() {
  const computed = DATA.regions.map((reg) => ({ ...reg, ...computeScenario(reg.kabupaten) }));
  computed.sort((a, b) => (a.bepLow ?? 99) - (b.bepLow ?? 99));

  // Top KPIs
  const avgBep = computed.reduce((s, x) => s + (x.bepLow ?? 0), 0) / computed.length;
  const viableCount = computed.filter((x) => x.bepLow !== null && x.bepLow <= 5).length;
  const avgCov = computed.reduce((s, x) => s + x.solar_coverage_pct, 0) / computed.length;
  const totalNet = computed.reduce((s, x) => s + Math.max(0, x.netLow), 0);

  document.getElementById("kpi-bep").textContent = avgBep.toFixed(2) + " thn";
  document.getElementById("kpi-bep").style.color = bepColor(avgBep);
  document.getElementById("kpi-viable").textContent = `${viableCount}/8 kab layak (< 5 thn)`;
  document.getElementById("kpi-cov").textContent = avgCov.toFixed(1) + "%";
  document.getElementById("kpi-save").textContent = fmtRp(totalNet / 8 / 1e6).replace("Rp ", "Rp ") + " jt/kab/thn";

  // Ranked sidebar list
  const listEl = document.getElementById("reg-list");
  listEl.innerHTML = "";
  const maxBep = Math.max(...computed.map((x) => x.bepLow ?? 10), 6);

  computed.forEach((item) => {
    const col = bepColor(item.bepLow);
    const pct = item.bepLow ? Math.min(100, Math.max(12, (1 - item.bepLow / (maxBep + 2)) * 100)) : 5;
    const div = document.createElement("div");
    div.className = "reg-item" + (item.kabupaten === state.selectedKab ? " selected" : "");
    div.innerHTML = `
      <div class="reg-top">
        <span class="reg-name">${item.kabupaten}</span>
        <span class="reg-bep" style="color:${col}">${item.bepLow ? item.bepLow.toFixed(2) + " thn" : ">25 thn"}</span>
      </div>
      <div class="reg-meta">
        <span>Hemat ${(item.netLow / 1e6).toFixed(1)} jt/thn</span>
        <span>Range ${item.bepLow?.toFixed(1)}–${item.bepHigh?.toFixed(1)} thn</span>
      </div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%; background:${col}"></div></div>
    `;
    div.onclick = () => {
      state.selectedKab = item.kabupaten;
      map.panTo([item.lat, item.lon - 0.12], { animate: true });
      renderAll();
      if (state.tab === "climate") renderClimateCharts();
    };
    listEl.appendChild(div);

    // Map circle + floating Foundry pill badge
    const radius = 5500 + (item.netLow / 1e6) * 260;
    if (!circles[item.kabupaten]) {
      circles[item.kabupaten] = L.circle([item.lat, item.lon], { radius, weight: 2, fillOpacity: 0.25 }).addTo(map);
    }
    circles[item.kabupaten].setStyle({ color: col, fillColor: col }).setRadius(Math.min(16000, Math.max(5000, radius)));

    const icon = L.divIcon({
      className: "",
      html: `<div class="map-badge" style="border-color:${item.kabupaten === state.selectedKab ? '#2DD4BF' : 'rgba(255,255,255,0.2)'}">
               <span class="mb-name">${item.kabupaten}</span>
               <span class="mb-val" style="color:${col}">${item.bepLow ? item.bepLow.toFixed(2) + " thn" : "N/A"}</span>
             </div>`,
      iconSize: [108, 36],
      iconAnchor: [54, 18],
    });
    if (!markers[item.kabupaten]) {
      markers[item.kabupaten] = L.marker([item.lat, item.lon], { icon }).addTo(map).on("click", () => {
        state.selectedKab = item.kabupaten;
        renderAll();
        if (state.tab === "climate") renderClimateCharts();
      });
    } else {
      markers[item.kabupaten].setIcon(icon);
    }
  });
}

// Charts (Climate & ML)
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
        { type: "bar", label: "NFR (mm/hr)", data: mData.map(x => x.nfr), backgroundColor: "rgba(45,212,191,0.65)", yAxisID: "y" },
        { type: "line", label: "Radiasi (MJ/m²/hr)", data: mData.map(x => x.rad), borderColor: "#F59E0B", backgroundColor: "#F59E0B", tension: 0.35, yAxisID: "y1" },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#A1A1AA" }, grid: { color: "rgba(255,255,255,0.05)" } },
        y: { position: "left", ticks: { color: "#2DD4BF" }, grid: { color: "rgba(255,255,255,0.06)" } },
        y1: { position: "right", min: 14, max: 22, ticks: { color: "#F59E0B" }, grid: { drawOnChartArea: false } },
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
        backgroundColor: yData.map(x => [2018, 2019, 2023].includes(x.year) ? "#F43F5E" : "rgba(167,139,250,0.65)"),
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: "#A1A1AA" }, grid: { display: false } },
        y: { ticks: { color: "#A1A1AA" }, grid: { color: "rgba(255,255,255,0.06)" } },
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
          { label: "Prediksi (prob_lr)", data: cal.map(x => x.prob_lr), borderColor: "#2DD4BF", tension: 0.35, borderWidth: 2.5 },
          { label: "Aktual (target_next)", data: cal.map(x => x.actual), borderColor: "#A78BFA", borderDash: [5, 4], tension: 0.35, borderWidth: 2.5 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#E4E4E7", font: { size: 11 } } } },
        scales: {
          x: { ticks: { color: "#A1A1AA" }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { min: 0.2, max: 1.0, ticks: { color: "#A1A1AA" }, grid: { color: "rgba(255,255,255,0.06)" } },
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

// Event bindings
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
  priceDisp.textContent = fmtRp(state.price) + " / liter";
  document.querySelectorAll(".preset-pill").forEach((p) => p.classList.toggle("active", Number(p.dataset.price) === state.price));
  renderAll();
}
slider.oninput = (e) => setPrice(e.target.value);
document.querySelectorAll(".preset-pill").forEach((btn) => { btn.onclick = () => setPrice(btn.dataset.price); });

document.getElementById("play-btn").onclick = () => {
  const btn = document.getElementById("play-btn");
  if (state.playing) {
    clearInterval(state.timer);
    state.playing = false;
    btn.textContent = "▶";
  } else {
    if (state.price >= 28000) setPrice(6800);
    state.playing = true;
    btn.textContent = "❚❚";
    state.timer = setInterval(() => {
      if (state.price >= 24000) {
        clearInterval(state.timer);
        state.playing = false;
        btn.textContent = "▶";
        return;
      }
      setPrice(state.price + 400);
    }, 120);
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
