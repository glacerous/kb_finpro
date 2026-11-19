"""Stage 4: Statistical tests (ANOVA, t-test) & H+1 irrigation classification ML.

Reads directly from PostgreSQL (`kb_solar_irrigation`) and writes summary metrics
and out-of-sample test predictions (2023-2025) to `data/processed/`.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from etl_load_pg import get_conn

OUT_DIR = Path("data/processed")


def load_daily_from_pg() -> pd.DataFrame:
    query = """
        SELECT
            f.region_id,
            r.kabupaten,
            r.provinsi,
            d.date_id,
            d.full_date,
            d.year,
            d.month,
            d.day_of_year,
            d.climate_season,
            d.planting_season,
            d.kc_paddy,
            f.et0_mm,
            f.rain_mm,
            f.rad_mj_m2,
            f.temp_mean_c,
            f.rh_mean_pct,
            f.cloud_mean_pct,
            f.wind_mean_kmh,
            f.solar_water_1kwp_m3,
            f.active_pump_hours,
            f.nfr_mm,
            f.need_irrigation
        FROM fact_irrigation_daily f
        JOIN dim_region r ON r.region_id = f.region_id
        JOIN dim_date d   ON d.date_id   = f.date_id
        ORDER BY f.region_id, d.full_date
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        return pd.DataFrame(rows, columns=cols)
    finally:
        conn.close()


def run_statistical_tests(df: pd.DataFrame) -> dict:
    in_season = df[df["planting_season"] != "Bera"].copy()

    # 1. One-way ANOVA & Kruskal-Wallis across 8 kabupaten (in-season NFR & radiation)
    nfr_groups = [g["nfr_mm"].to_numpy() for _, g in in_season.groupby("kabupaten")]
    rad_groups = [g["rad_mj_m2"].to_numpy() for _, g in df.groupby("kabupaten")]
    anova_nfr = stats.f_oneway(*nfr_groups)
    kw_nfr = stats.kruskal(*nfr_groups)
    anova_rad = stats.f_oneway(*rad_groups)

    # 2. Welch's t-test & Mann-Whitney U: Hujan vs Kemarau (radiation all year; NFR in-season)
    hujan_nfr = in_season.loc[in_season["climate_season"] == "Hujan", "nfr_mm"]
    kemarau_nfr = in_season.loc[in_season["climate_season"] == "Kemarau", "nfr_mm"]
    t_nfr_season = stats.ttest_ind(kemarau_nfr, hujan_nfr, equal_var=False)
    u_nfr_season = stats.mannwhitneyu(kemarau_nfr, hujan_nfr, alternative="two-sided")

    mt1_nfr = in_season.loc[in_season["planting_season"] == "MT1", "nfr_mm"]
    mt2_nfr = in_season.loc[in_season["planting_season"] == "MT2", "nfr_mm"]
    t_nfr_mt = stats.ttest_ind(mt2_nfr, mt1_nfr, equal_var=False)

    hujan_rad = df.loc[df["climate_season"] == "Hujan", "rad_mj_m2"]
    kemarau_rad = df.loc[df["climate_season"] == "Kemarau", "rad_mj_m2"]
    t_rad_season = stats.ttest_ind(kemarau_rad, hujan_rad, equal_var=False)

    reg_summary = (
        in_season.groupby("kabupaten", as_index=False)
        .agg(
            in_season_days=("date_id", "count"),
            mean_nfr_mm=("nfr_mm", "mean"),
            pct_need_irrig=("need_irrigation", lambda s: s.mean() * 100.0),
            mean_rad_mj=("rad_mj_m2", "mean"),
            mean_solar_m3_1kwp=("solar_water_1kwp_m3", "mean"),
            mean_rain_mm=("rain_mm", "mean"),
        )
        .sort_values("mean_nfr_mm", ascending=False)
    )

    print("=== 1. REGIONAL SUMMARY (IN-SEASON MT1+MT2, 2011-2025) ===")
    print(reg_summary.round(2).to_string(index=False))

    print("\n=== 2. STATISTICAL TESTS ===")
    print(f"ANOVA NFR across 8 kabupaten (in-season) : F={anova_nfr.statistic:.2f}, p={anova_nfr.pvalue:.3e}")
    print(f"Kruskal-Wallis NFR across 8 kabupaten    : H={kw_nfr.statistic:.2f}, p={kw_nfr.pvalue:.3e}")
    print(f"ANOVA Radiation across 8 kabupaten (all) : F={anova_rad.statistic:.2f}, p={anova_rad.pvalue:.3e}")
    print(
        f"Welch t-test NFR Kemarau ({kemarau_nfr.mean():.2f}) vs Hujan ({hujan_nfr.mean():.2f}) mm/d : "
        f"t={t_nfr_season.statistic:.2f}, p={t_nfr_season.pvalue:.3e} (Mann-Whitney p={u_nfr_season.pvalue:.3e})"
    )
    print(
        f"Welch t-test NFR MT2 ({mt2_nfr.mean():.2f}) vs MT1 ({mt1_nfr.mean():.2f}) mm/d         : "
        f"t={t_nfr_mt.statistic:.2f}, p={t_nfr_mt.pvalue:.3e}"
    )
    print(
        f"Welch t-test Rad Kemarau ({kemarau_rad.mean():.2f}) vs Hujan ({hujan_rad.mean():.2f}) MJ/m2: "
        f"t={t_rad_season.statistic:.2f}, p={t_rad_season.pvalue:.3e}"
    )

    return {
        "anova_nfr_F": float(anova_nfr.statistic),
        "anova_nfr_p": float(anova_nfr.pvalue),
        "kruskal_nfr_H": float(kw_nfr.statistic),
        "kruskal_nfr_p": float(kw_nfr.pvalue),
        "anova_rad_F": float(anova_rad.statistic),
        "anova_rad_p": float(anova_rad.pvalue),
        "ttest_nfr_kemarau_vs_hujan_t": float(t_nfr_season.statistic),
        "ttest_nfr_kemarau_vs_hujan_p": float(t_nfr_season.pvalue),
        "mean_nfr_kemarau": float(kemarau_nfr.mean()),
        "mean_nfr_hujan": float(hujan_nfr.mean()),
        "ttest_nfr_mt2_vs_mt1_t": float(t_nfr_mt.statistic),
        "ttest_nfr_mt2_vs_mt1_p": float(t_nfr_mt.pvalue),
        "regional_summary": reg_summary.round(3).to_dict(orient="records"),
    }


def build_ml_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    df = df.sort_values(["region_id", "full_date"]).copy()
    g = df.groupby("region_id", group_keys=False)

    # Target: tomorrow's irrigation need (strictly H+1 within each region)
    df["target_next"] = g["need_irrigation"].shift(-1)
    df["next_date"] = g["full_date"].shift(-1)
    df["next_season"] = g["planting_season"].shift(-1)

    # Cyclical calendar features (day t)
    df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365.25)

    # Strictly causal lags & rolling stats (<= day t, per region)
    for lag in [1, 2, 3, 7]:
        df[f"rain_lag{lag}"] = g["rain_mm"].shift(lag)
        df[f"et0_lag{lag}"] = g["et0_mm"].shift(lag)
        df[f"nfr_lag{lag}"] = g["nfr_mm"].shift(lag)
        df[f"need_lag{lag}"] = g["need_irrigation"].shift(lag)

    for win in [3, 7]:
        df[f"rain_roll{win}"] = g["rain_mm"].transform(lambda s: s.rolling(win).mean())
        df[f"rh_roll{win}"] = g["rh_mean_pct"].transform(lambda s: s.rolling(win).mean())
        df[f"cloud_roll{win}"] = g["cloud_mean_pct"].transform(lambda s: s.rolling(win).mean())
        df[f"nfr_roll{win}"] = g["nfr_mm"].transform(lambda s: s.rolling(win).mean())

    num_feats = [
        "et0_mm", "rain_mm", "rad_mj_m2", "temp_mean_c", "rh_mean_pct",
        "cloud_mean_pct", "wind_mean_kmh", "nfr_mm", "need_irrigation",
        "doy_sin", "doy_cos",
        "rain_lag1", "rain_lag2", "rain_lag3", "rain_lag7",
        "et0_lag1", "et0_lag2", "et0_lag3", "et0_lag7",
        "nfr_lag1", "nfr_lag2", "nfr_lag3", "nfr_lag7",
        "need_lag1", "need_lag2", "need_lag3", "need_lag7",
        "rain_roll3", "rain_roll7", "rh_roll3", "rh_roll7",
        "cloud_roll3", "cloud_roll7", "nfr_roll3", "nfr_roll7",
    ]
    cat_feats = ["kabupaten"]

    # Keep only rows where tomorrow is in paddy planting season (MT1 or MT2)
    ml_df = df[df["next_season"].isin(["MT1", "MT2"])].dropna(subset=num_feats + ["target_next"]).copy()
    ml_df["target_next"] = ml_df["target_next"].astype(int)

    # Leakage guard: verify next_date is strictly 1 day after full_date
    day_diff = (pd.to_datetime(ml_df["next_date"]) - pd.to_datetime(ml_df["full_date"])).dt.days
    assert (day_diff == 1).all(), "Date alignment bug in H+1 target!"
    return ml_df, num_feats, cat_feats


def eval_preds(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray | None = None) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    res = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if y_prob is not None else None,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }
    return res


def find_optimal_threshold(y_val: np.ndarray, p_val: np.ndarray, fn_cost: float, fp_cost: float = 1.0) -> float:
    best_t, best_cost = 0.5, float("inf")
    for t in np.linspace(0.15, 0.85, 71):
        pred = (p_val >= t).astype(int)
        _, fp, fn, _ = confusion_matrix(y_val, pred).ravel()
        cost = fn * fn_cost + fp * fp_cost
        if cost < best_cost:
            best_cost = cost
            best_t = float(t)
    return round(best_t, 2)


def run_ml_pipeline(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    ml_df, num_feats, cat_feats = build_ml_features(df)

    # Temporal split: Train-fit (2011-2020), Val for threshold (2021-2022), Test untouched (2023-2025)
    # Full train (2011-2022) used to refit final model after picking threshold on 2021-2022.
    tr_sub = ml_df[ml_df["year"] <= 2020]
    val_df = ml_df[(ml_df["year"] >= 2021) & (ml_df["year"] <= 2022)]
    train_full = ml_df[ml_df["year"] <= 2022]
    test_df = ml_df[ml_df["year"] >= 2023].copy()

    y_tr_sub = tr_sub["target_next"].to_numpy()
    y_val = val_df["target_next"].to_numpy()
    y_tr_full = train_full["target_next"].to_numpy()
    y_te = test_df["target_next"].to_numpy()

    # Baselines
    clim_table = train_full.groupby(["kabupaten", "month"])["target_next"].mean()
    p_clim = test_df.set_index(["kabupaten", "month"]).index.map(clim_table).to_numpy(dtype=float)
    pred_clim = (p_clim >= 0.5).astype(int)
    pred_persist = test_df["need_irrigation"].to_numpy(dtype=int)

    # Models
    pre_lr = ColumnTransformer([
        ("num", StandardScaler(), num_feats),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_feats),
    ])
    lr_pipe = Pipeline([("pre", pre_lr), ("clf", LogisticRegression(max_iter=1000, C=1.0))])

    pre_rf = ColumnTransformer([
        ("num", "passthrough", num_feats),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_feats),
    ])
    rf_pipe = Pipeline([
        ("pre", pre_rf),
        ("clf", RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=5, random_state=42, n_jobs=-1)),
    ])

    # Tune thresholds strictly on 2021-2022 validation set
    lr_pipe.fit(tr_sub[num_feats + cat_feats], y_tr_sub)
    p_lr_val = lr_pipe.predict_proba(val_df[num_feats + cat_feats])[:, 1]
    t_lr_fn3 = find_optimal_threshold(y_val, p_lr_val, fn_cost=3.0)

    rf_pipe.fit(tr_sub[num_feats + cat_feats], y_tr_sub)
    p_rf_val = rf_pipe.predict_proba(val_df[num_feats + cat_feats])[:, 1]
    t_fn3 = find_optimal_threshold(y_val, p_rf_val, fn_cost=3.0)
    t_fn5 = find_optimal_threshold(y_val, p_rf_val, fn_cost=5.0)

    # Fit final models on full 2011-2022 train and evaluate on 2023-2025 test
    lr_pipe.fit(train_full[num_feats + cat_feats], y_tr_full)
    p_lr = lr_pipe.predict_proba(test_df[num_feats + cat_feats])[:, 1]

    rf_pipe.fit(train_full[num_feats + cat_feats], y_tr_full)
    p_rf = rf_pipe.predict_proba(test_df[num_feats + cat_feats])[:, 1]

    results = {
        "train_rows": int(len(train_full)),
        "test_rows": int(len(test_df)),
        "test_positive_rate": float(y_te.mean()),
        "models": {
            "Climatology (baseline)": eval_preds(y_te, pred_clim, p_clim),
            "Persistence (baseline)": eval_preds(y_te, pred_persist, None),
            "Logistic Regression (t=0.50)": eval_preds(y_te, (p_lr >= 0.5).astype(int), p_lr),
            f"Logistic Regression (FN:FP=3:1, t={t_lr_fn3:.2f})": eval_preds(y_te, (p_lr >= t_lr_fn3).astype(int), p_lr),
            "Random Forest (t=0.50)": eval_preds(y_te, (p_rf >= 0.5).astype(int), p_rf),
            f"Random Forest (FN:FP=3:1, t={t_fn3:.2f})": eval_preds(y_te, (p_rf >= t_fn3).astype(int), p_rf),
            f"Random Forest (FN:FP=5:1, t={t_fn5:.2f})": eval_preds(y_te, (p_rf >= t_fn5).astype(int), p_rf),
        },
        "thresholds_tuned_on_val_2021_2022": {"lr_fn3_fp1": t_lr_fn3, "rf_fn3_fp1": t_fn3, "rf_fn5_fp1": t_fn5},
    }

    # Feature importances (Random Forest)
    feat_names = num_feats + list(rf_pipe.named_steps["pre"].named_transformers_["cat"].get_feature_names_out(cat_feats))
    imp = pd.Series(rf_pipe.named_steps["clf"].feature_importances_, index=feat_names).sort_values(ascending=False)
    results["top10_rf_features"] = {k: round(float(v), 4) for k, v in imp.head(10).items()}

    print("\n=== 3. ML H+1 CLASSIFICATION (ALL 8 KABUPATEN, TEST 2023-2025) ===")
    print(f"Train (2011-2022): {len(train_full):,} rows | Test (2023-2025): {len(test_df):,} rows | Pos rate: {y_te.mean()*100:.1f}%")
    rows_tbl = []
    for name, m in results["models"].items():
        rows_tbl.append({
            "Model": name,
            "Acc": round(m["accuracy"], 3),
            "Prec": round(m["precision"], 3),
            "Rec": round(m["recall"], 3),
            "F1": round(m["f1"], 3),
            "AUC": round(m["roc_auc"], 3) if m["roc_auc"] is not None else "-",
            "FN": m["fn"],
            "FP": m["fp"],
        })
    print(pd.DataFrame(rows_tbl).to_string(index=False))

    print("\n=== 4. TOP 10 RANDOM FOREST FEATURES ===")
    for k, v in results["top10_rf_features"].items():
        print(f"  {k:20s}: {v:.4f}")

    # Save test predictions for Power BI / ROI integration
    pred_out = test_df[["region_id", "kabupaten", "date_id", "full_date", "next_date", "next_season", "target_next"]].copy()
    pred_out["prob_lr"] = np.round(p_lr, 4)
    pred_out["pred_lr_050"] = (p_lr >= 0.5).astype(int)
    pred_out["pred_lr_fn3"] = (p_lr >= t_lr_fn3).astype(int)
    pred_out["prob_rf"] = np.round(p_rf, 4)
    pred_out["pred_rf_050"] = (p_rf >= 0.5).astype(int)
    pred_out["pred_rf_fn3"] = (p_rf >= t_fn3).astype(int)
    return results, pred_out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_daily_from_pg()
    assert len(df) == 43_832, f"Expected 43,832 daily rows, got {len(df)}"

    stat_res = run_statistical_tests(df)
    ml_res, pred_out = run_ml_pipeline(df)

    (OUT_DIR / "stage4_results.json").write_text(
        json.dumps({"stats": stat_res, "ml": ml_res}, indent=2), encoding="utf-8"
    )
    pred_out.to_csv(OUT_DIR / "ml_test_predictions_2023_2025.csv", index=False)
    print(f"\nSaved outputs to {OUT_DIR}/stage4_results.json & {OUT_DIR}/ml_test_predictions_2023_2025.csv")


if __name__ == "__main__":
    main()
