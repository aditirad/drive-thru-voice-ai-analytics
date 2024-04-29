"""Pattern detection: correlations, friction, anomalies, and keywords.

This is the "investigation" part of the analyst's job - not just measuring
the scoreboard, but explaining *why* the numbers look the way they do.
"""

import re

import pandas as pd

# Tiny stopword list (no NLP library needed) for keyword mining.
STOPWORDS = set("""
a an the and i you me to for of it that this no yes have can get like want
is on at with my your please just say said never mind forget need would
could yeah sure okay thanks thank anything else what how much are do does
he she we they there here one thanks about order add going will i'd i'll
that's it's you're don't won't can't isn't
""".split())


def mbt_nir_correlation(df):
    """Correlate average Menu Board Time with NIR across hours of the day."""
    hourly = df.groupby("hour").agg(
        nir=("ai_completed", "mean"),
        mbt=("menu_board_time_sec", "mean"),
        asr=("asr_confidence", "mean"),
    )
    corr = hourly["nir"].corr(hourly["mbt"])
    return hourly, corr


def issue_breakdown(df):
    """Count how many orders hit each recurring issue type."""
    return pd.Series([i for issues in df["issues"] for i in issues]).value_counts()


def friction_positions(df):
    """Which turn number of the transcript does friction usually appear at?

    Scans transcripts for repeats and corrections ("I said...", "No, a...",
    "could you repeat") and records the 1-based turn index where they occur.
    """
    markers = ("repeat", "no, a", "i said", "no onions", "never mind", "forget it", "didn't catch")
    positions = []
    for turns in df["transcript"]:
        for idx, turn in enumerate(turns):
            if turn["speaker"] == "guest" and any(m in turn["text"].lower() for m in markers):
                positions.append(idx + 1)
    return pd.Series(positions).value_counts().sort_index()


def top_phrases(df, outcomes):
    """Most frequent meaningful words in guest speech for a set of outcomes."""
    words = []
    mask = df["outcome"].isin(outcomes)
    for turns in df.loc[mask, "transcript"]:
        for turn in turns:
            if turn["speaker"] == "guest":
                for word in re.findall(r"[a-z']+", turn["text"].lower()):
                    if word not in STOPWORDS and len(word) > 2:
                        words.append(word)
    return pd.Series(words).value_counts().head(8)


def anomaly_stores(df):
    """Flag stores whose NIR is more than 1 std below the average store NIR."""
    store_nir = df.groupby("store_id")["ai_completed"].mean()
    mean_nir, std_nir = store_nir.mean(), store_nir.std()
    return store_nir[store_nir < mean_nir - std_nir]


def extreme_orders(df):
    """Flag the worst orders: MBT above Q3 + 1.5*IQR (the boxplot rule)."""
    q1 = df["menu_board_time_sec"].quantile(0.25)
    q3 = df["menu_board_time_sec"].quantile(0.75)
    iqr = q3 - q1
    extreme = df[df["menu_board_time_sec"] > q3 + 1.5 * iqr].nlargest(3, "menu_board_time_sec")
    return extreme, (q1, q3, iqr)


def upsell_impact(df):
    """Estimate the revenue added by AI upsells over the sampled period."""
    attempted = df[df["upsell_attempted"]]
    return {
        "attempts": int(attempted["upsell_accepted"].count()),
        "accepted": int(attempted["upsell_accepted"].sum()),
        "attach": attempted["upsell_accepted"].mean(),
        "total_uplift": round(attempted["upsell_addon"].sum(), 2),
        "avg_uplift": round(attempted["upsell_addon"].mean(), 2),
    }
