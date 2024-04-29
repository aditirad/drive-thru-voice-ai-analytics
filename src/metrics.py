"""KPI calculations for drive-thru voice AI performance.

A KPI is just a ratio computed from the order table. This module is the
"scoreboard" for the system.
"""

import pandas as pd


def compute_kpis(df):
    """Return a dict of headline KPIs for the whole system."""
    attempted = df[df["upsell_attempted"]]
    return {
        "total_orders": len(df),
        "nir": df["ai_completed"].mean(),                      # Non-Intervention Rate
        "ar": df["outcome"].isin(["completed_ai", "assisted"]).mean(),  # Automation Rate
        "ai_efficiency": df.loc[df["ai_completed"], "corrections"].eq(0).mean(),
        "mbt": df["menu_board_time_sec"].mean(),               # Menu Board Time
        "latency": df["latency_avg_ms"].mean(),                # avg AI reply speed
        "asr": df["asr_confidence"].mean(),                    # avg speech confidence
        "sentiment": df["sentiment_score"].mean(),
        "upsell_attach": attempted["upsell_accepted"].mean(),  # attach rate when asked
        "abandonment": df["outcome"].eq("abandoned").mean(),
        "avg_ticket": df["total"].mean(),
    }


def by_store(df):
    """Per-store performance table (used for comparisons and anomalies)."""
    attempted = df[df["upsell_attempted"]]
    stats = attempted.groupby("store_id").agg(
        nir=("ai_completed", "mean"),
        mbt=("menu_board_time_sec", "mean"),
        asr=("asr_confidence", "mean"),
        upsell=("upsell_accepted", "mean"),
        issues=("num_issues", "mean"),
        orders=("order_id", "count"),
    )
    # Add store names back in so the report reads nicely.
    names = df.drop_duplicates("store_id").set_index("store_id")["store_name"]
    stats.insert(0, "store_name", names)
    return stats.sort_values("nir")


def by_region(df):
    """Average KPIs per region (upsell computed among attempted orders)."""
    attempted = df[df["upsell_attempted"]]
    return attempted.groupby("region").agg(
        nir=("ai_completed", "mean"),
        mbt=("menu_board_time_sec", "mean"),
        issues=("num_issues", "mean"),
        upsell=("upsell_accepted", "mean"),
    ).sort_values("nir", ascending=False)


def peak_vs_offpeak(df):
    """Compare rush hours against the rest of the day."""
    return df.groupby("is_peak").agg(
        nir=("ai_completed", "mean"),
        mbt=("menu_board_time_sec", "mean"),
        asr=("asr_confidence", "mean"),
        issues=("num_issues", "mean"),
    )
