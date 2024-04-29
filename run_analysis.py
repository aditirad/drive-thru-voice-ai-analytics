"""Drive-Thru Voice AI Order Analytics - main entry point.

Run from the project root with:  python run_analysis.py

Pipeline:  generate data -> measure KPIs -> find patterns -> charts -> report
"""

import os

import pandas as pd

from src.generate_data import generate_dataset
from src.metrics import compute_kpis, by_store, by_region, peak_vs_offpeak
from src.patterns import (mbt_nir_correlation, issue_breakdown, friction_positions,
                          top_phrases, anomaly_stores, extreme_orders, upsell_impact)
from src.charts import save_all
from src.report import write_report


def load_data():
    """Generate the dataset, load it, and add derived columns."""
    generate_dataset()
    df = pd.read_json("data/orders.json")
    df["ai_completed"] = df["outcome"] == "completed_ai"
    return df


def main():
    df = load_data()

    # --- measure ---
    kpis = compute_kpis(df)
    store_stats = by_store(df)
    region_stats = by_region(df)
    peak_stats = peak_vs_offpeak(df)

    print("\n=== KEY PERFORMANCE METRICS ===")
    print(f"Orders analysed        : {kpis['total_orders']}")
    print(f"Non-Intervention Rate  : {kpis['nir']:.0%}")
    print(f"Automation Rate        : {kpis['ar']:.0%}")
    print(f"AI Efficiency          : {kpis['ai_efficiency']:.0%}")
    print(f"Avg Menu Board Time    : {kpis['mbt']:.0f} sec")
    print(f"Avg AI reply latency   : {kpis['latency']:.0f} ms")
    print(f"Avg ASR confidence     : {kpis['asr']:.0%}")
    print(f"Upsell attach rate     : {kpis['upsell_attach']:.0%}")
    print(f"Abandonment rate       : {kpis['abandonment']:.0%}")

    # --- investigate ---
    hourly, corr = mbt_nir_correlation(df)
    issue_counts = issue_breakdown(df)
    friction = friction_positions(df)
    phrases_abandoned = top_phrases(df, ["abandoned", "error"])
    anomalies = anomaly_stores(df)
    extreme, extreme_bounds = extreme_orders(df)
    upsell = upsell_impact(df)

    print("\n=== PATTERNS ===")
    print(f"MBT-NIR correlation (hourly): {corr:+.2f}")
    print(f"Top issue type: {issue_counts.index[0]} ({issue_counts.iloc[0]} orders)")
    if not anomalies.empty:
        print("Underperforming stores: " + ", ".join(anomalies.index))
    print(f"Extreme orders (MBT beyond Q3+1.5IQR): {len(extreme)} worst flagged")
    print(f"Upsells add ~${upsell['total_uplift']:.0f} over 30 days")

    # --- deliver ---
    save_all(df, kpis, hourly, issue_counts, friction, store_stats)
    write_report(df, kpis, store_stats, region_stats, peak_stats, issue_counts,
                 friction, hourly, corr, phrases_abandoned, anomalies, extreme,
                 extreme_bounds, upsell)
    print("\nDone.")


if __name__ == "__main__":
    main()
