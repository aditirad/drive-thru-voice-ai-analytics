"""Chart generation: everything is saved to output/charts/ as PNG files."""

import os

import matplotlib
matplotlib.use("Agg")  # save to files instead of opening a window

import matplotlib.pyplot as plt
import pandas as pd

CHART_DIR = "output/charts"

BLUE = "#4c72b0"
RED = "#d62728"
ORANGE = "#ff7f0e"
GREEN = "#2ca02c"
PURPLE = "#9467bd"
BROWN = "#8c564b"


def _setup():
    os.makedirs(CHART_DIR, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")


def _save(name):
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/{name}", dpi=120)
    plt.close()


def chart_kpi_overview(kpis):
    values = {"NIR": kpis["nir"] * 100, "AR": kpis["ar"] * 100,
              "AI Efficiency": kpis["ai_efficiency"] * 100,
              "Upsell attach": kpis["upsell_attach"] * 100}
    plt.figure(figsize=(6, 4))
    plt.bar(values.keys(), values.values(), color=BLUE)
    plt.title("Headline KPIs")
    plt.ylabel("Percent (%)")
    plt.ylim(0, 100)
    _save("kpi_overview.png")


def chart_mbt_vs_nir(hourly):
    plt.figure(figsize=(6, 4))
    plt.scatter(hourly["mbt"], hourly["nir"] * 100, c=hourly.index, cmap="viridis", s=60)
    for hour, row in hourly.iterrows():
        plt.annotate(f"{hour}h", (row["mbt"], row["nir"] * 100), fontsize=8)
    plt.xlabel("Average Menu Board Time (seconds)")
    plt.ylabel("Non-Intervention Rate (%)")
    plt.title("MBT vs NIR by Hour: slower = less automated")
    _save("mbt_vs_nir.png")


def chart_mbt_by_hour(hourly):
    plt.figure(figsize=(6, 4))
    hourly["mbt"].plot(kind="line", marker="o", color=RED)
    plt.title("Average Menu Board Time by Hour")
    plt.xlabel("Hour of day")
    plt.ylabel("Seconds")
    _save("mbt_by_hour.png")


def chart_asr_by_hour(hourly):
    plt.figure(figsize=(6, 4))
    hourly["asr"].plot(kind="line", marker="o", color=PURPLE)
    plt.title("Average ASR Confidence by Hour")
    plt.xlabel("Hour of day")
    plt.ylabel("Confidence")
    plt.ylim(0.5, 1.0)
    _save("asr_by_hour.png")


def chart_issue_types(issue_counts):
    plt.figure(figsize=(6, 4))
    issue_counts.plot(kind="bar", color=ORANGE)
    plt.title("Recurring Issue Types")
    plt.ylabel("Orders affected")
    plt.xticks(rotation=15)
    _save("issue_types.png")


def chart_friction_positions(friction):
    plt.figure(figsize=(6, 4))
    friction.plot(kind="bar", color=RED)
    plt.title("Where Friction Happens in the Conversation")
    plt.xlabel("Turn number in transcript")
    plt.ylabel("Repeats / corrections")
    _save("friction_positions.png")


def chart_nir_by_store(store_stats):
    plt.figure(figsize=(6, 4))
    store_stats["nir"].plot(kind="bar", color=BROWN)
    plt.title("Non-Intervention Rate by Store")
    plt.ylabel("NIR")
    plt.xticks(rotation=45)
    _save("nir_by_store.png")


def chart_upsell_by_store(store_stats):
    plt.figure(figsize=(6, 4))
    store_stats["upsell"].sort_values(ascending=False).plot(kind="bar", color=GREEN)
    plt.title("Upsell Acceptance Rate by Store")
    plt.ylabel("Acceptance rate")
    plt.xticks(rotation=45)
    _save("upsell_by_store.png")


def chart_daily_trend(df):
    daily = df.groupby("day").agg(nir=("ai_completed", "mean"),
                                  mbt=("menu_board_time_sec", "mean"))
    daily["nir_ma"] = daily["nir"].rolling(3, min_periods=1).mean()
    daily["mbt_ma"] = daily["mbt"].rolling(3, min_periods=1).mean()

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(daily.index, daily["nir_ma"], color=GREEN, marker="o", markersize=3, label="NIR (3-day avg)")
    ax1.set_xlabel("Day")
    ax1.set_ylabel("NIR", color=GREEN)
    ax1.set_ylim(0, 1)
    ax2 = ax1.twinx()
    ax2.plot(daily.index, daily["mbt_ma"], color=RED, marker="o", markersize=3, label="MBT (3-day avg)")
    ax2.set_ylabel("MBT (sec)", color=RED)
    fig.legend(loc="upper right", framealpha=1)
    plt.title("Daily Trend: NIR vs Menu Board Time")
    _save("daily_trend.png")


def save_all(df, kpis, hourly, issue_counts, friction, store_stats):
    """Generate every chart in one call."""
    _setup()
    chart_kpi_overview(kpis)
    chart_mbt_vs_nir(hourly)
    chart_mbt_by_hour(hourly)
    chart_asr_by_hour(hourly)
    chart_issue_types(issue_counts)
    chart_friction_positions(friction)
    chart_nir_by_store(store_stats)
    chart_upsell_by_store(store_stats)
    chart_daily_trend(df)
    print(f"Charts saved to {CHART_DIR}/")
