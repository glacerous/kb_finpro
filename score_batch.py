"""Standalone batch scoring pipeline for H+1 irrigation prediction (LK Minggu 11).

Loads trained Logistic Regression artifact (`models/irrigation_lr_v1.joblib`),
scores the latest daily rows from PostgreSQL (`fact_irrigation_daily`) or `--from-raw`,
and optionally performs idempotent UPSERT into `fact_ml_predictions`.
"""

import argparse
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from etl_load_pg import get_conn
from stage4_stats_ml import MODEL_PATH, build_ml_features, load_daily_from_pg, load_daily_from_raw

ACTION_ALERT = "SIAGA IRIGASI BESOK (PATS)"
ACTION_IDLE = "TIDAK PERLU IRIGASI"


def score_latest(df: pd.DataFrame, model_path: Path = MODEL_PATH, days: int = 7) -> pd.DataFrame:
    assert model_path.exists(), f"Model artifact not found: {model_path}. Run `py stage4_stats_ml.py` first."
    bundle = joblib.load(model_path)
    pipe = bundle["pipeline"]
    threshold = float(bundle["threshold"])
    feats = bundle["num_feats"] + bundle["cat_feats"]

    ml_df, _, _ = build_ml_features(df)
    latest = ml_df.sort_values(["region_id", "full_date"]).groupby("region_id", group_keys=False).tail(days).copy()

    probs = pipe.predict_proba(latest[feats])[:, 1]
    latest["prob_lr"] = np.round(probs, 4)
    latest["pred_lr_050"] = (probs >= 0.5).astype(int)
    latest["pred_lr_fn3"] = (probs >= threshold).astype(int)
    latest["aksi_rekomendasi"] = np.where(latest["pred_lr_fn3"] == 1, ACTION_ALERT, ACTION_IDLE)
    return latest[
        [
            "region_id",
            "kabupaten",
            "date_id",
            "full_date",
            "next_date",
            "next_season",
            "target_next",
            "prob_lr",
            "pred_lr_050",
            "pred_lr_fn3",
            "aksi_rekomendasi",
        ]
    ]


def upsert_predictions(scored: pd.DataFrame) -> int:
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                rows = [
                    (
                        int(r.region_id),
                        int(r.date_id),
                        str(r.next_date),
                        str(r.next_season),
                        int(r.target_next),
                        float(r.prob_lr),
                        int(r.pred_lr_050),
                        int(r.pred_lr_fn3),
                    )
                    for r in scored.itertuples(index=False)
                ]
                cur.executemany(
                    """
                    INSERT INTO fact_ml_predictions
                        (region_id, date_id, next_date, next_season, target_next, prob_lr, pred_lr_050, pred_lr_fn3)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (region_id, date_id) DO UPDATE SET
                        prob_lr = EXCLUDED.prob_lr,
                        pred_lr_050 = EXCLUDED.pred_lr_050,
                        pred_lr_fn3 = EXCLUDED.pred_lr_fn3
                    """,
                    rows,
                )
        return len(rows)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch Scoring Pipeline (H+1 Irrigation Alert)")
    parser.add_argument("--from-raw", action="store_true", help="Read daily features from data/raw/*.csv instead of PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Preview scored rows without writing to PostgreSQL")
    parser.add_argument("--days", type=int, default=3, help="Number of latest in-season days per kabupaten to score")
    args = parser.parse_args()

    df = load_daily_from_raw() if args.from_raw else load_daily_from_pg()
    scored = score_latest(df, days=args.days)

    print(f"=== BATCH SCORING PREVIEW ({len(scored)} rows, latest {args.days} in-season days/kabupaten) ===")
    print(scored[["kabupaten", "full_date", "next_date", "prob_lr", "pred_lr_fn3", "aksi_rekomendasi"]].to_string(index=False))

    if args.dry_run:
        print("\n[DRY-RUN] Skipped PostgreSQL UPSERT.")
        return

    n = upsert_predictions(scored)
    print(f"\n[UPSERT OK] Updated {n} rows in fact_ml_predictions.")


if __name__ == "__main__":
    main()
