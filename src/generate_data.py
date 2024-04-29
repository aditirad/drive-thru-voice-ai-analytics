"""Synthetic drive-thru order + transcript generator.

A real Business Analyst reviews actual call recordings. Since real audio is
private, this module generates fake but realistic orders and turn-by-turn
transcripts instead. The generator encodes real-world behaviour (noisy sites,
rush hours, ASR errors) so that the analysis later finds genuine patterns.
"""

import json
import os
import random
from statistics import mean

random.seed(42)  # fixed seed -> fully reproducible results

OUTPUT_PATH = "data/orders.json"

# Six stores with real-sounding locations. "noise" is how hard the site is
# for the AI's speech recognition: traffic, acoustics, staff chatter, etc.
# ST-103 "Highway Exit" is intentionally the noisiest so the analysis has a
# clear underperforming store to find.
STORES = {
    "ST-101": {"name": "Downtown Ave", "region": "A", "noise": 0.8},
    "ST-102": {"name": "Mall Food Court", "region": "A", "noise": 1.0},
    "ST-103": {"name": "Highway Exit", "region": "B", "noise": 1.6},
    "ST-104": {"name": "Airport Rd", "region": "B", "noise": 1.2},
    "ST-105": {"name": "Suburb West", "region": "C", "noise": 0.9},
    "ST-106": {"name": "Train Station", "region": "C", "noise": 1.3},
}

# The menu items a guest can order, with prices.
MENU = [
    ("classic burger", 6.5),
    ("double cheeseburger", 9.5),
    ("chicken tenders", 7.0),
    ("fries", 3.0),
    ("soft drink", 2.5),
    ("milkshake", 4.5),
    ("veggie wrap", 8.0),
]

# Upsell items the AI suggests, with their price add-ons.
UPSELS = {
    "large fries": 1.5,
    "apple pie": 2.0,
    "extra sauce": 0.5,
    "drink upgrade": 1.0,
}

# The four recurring issue types voice AI teams track, and where each one
# happens in the real pipeline:
#   asr_error        - speech-to-text got the guest's words wrong
#   menu_mismatch    - the AI mapped speech to the wrong menu item
#   modifier_mapping - a modifier ("no onions") got lost
#   pos_injection    - the finished order never reached the cash register/POS
ISSUE_TYPES = ["asr_error", "menu_mismatch", "modifier_mapping", "pos_injection"]

# How each order ends:
#   completed_ai -> the AI took and finished the whole order, no staff help
#   assisted     -> a staff member had to step in at some point
#   abandoned    -> the guest gave up and drove off
#   error        -> the AI could not process the order at all
OUTCOMES = ["completed_ai", "assisted", "abandoned", "error"]

PEAK_HOURS = {11, 12, 13, 17, 18, 19}  # lunch and dinner rush
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# --------------------------------------------------------------------------
# Order-level behaviour
# --------------------------------------------------------------------------
def pick_issues(noise, peak):
    """Decide which (if any) AI issues occur on this order."""
    roll = random.random()
    if roll < 0.72:
        issues = []
    elif roll < 0.92:
        issues = [random.choice(ISSUE_TYPES)]
    else:
        issues = random.sample(ISSUE_TYPES, 2)
    # Noisy stores during rush hours are extra error-prone.
    if random.random() < 0.06 * noise * (1 + peak):
        issues.append(random.choice(ISSUE_TYPES))
    return issues


def order_outcome(noise, num_issues, peak):
    """Pick an outcome; noise, errors, and rush all hurt AI success."""
    success_chance = 0.82 / noise - 0.12 * num_issues - 0.08 * peak
    roll = random.random()
    if roll < success_chance:
        return "completed_ai"
    if roll < success_chance + 0.15:
        return "assisted"
    if roll < success_chance + 0.23:
        return "abandoned"
    return "error"


# --------------------------------------------------------------------------
# Transcript generation
# --------------------------------------------------------------------------
def build_transcript(items, issues, outcome, upsell_item, upsell_accepted, total):
    """Return a list of (speaker, text) turns for one order."""
    turns = []
    turns.append(("ai", "Welcome to the drive-thru. What can I get you today?"))

    queue = list(issues)
    for item_index, item in enumerate(items):
        phrase = random.choice([
            f"I'll have a {item}",
            f"Can I get a {item}, please",
            f"I'd like a {item}",
        ])
        # A modifier only appears once per order, and not too often.
        if item_index == 0 and random.random() < 0.2:
            phrase += " with no onions"
        turns.append(("guest", phrase))

        # Each issue type produces its own visible friction in the transcript.
        if queue:
            issue = queue.pop(0)
            if issue == "asr_error":
                turns.append(("ai", "Sorry, I didn't catch that. Could you repeat?"))
                turns.append(("guest", f"I said, {phrase}"))
            elif issue == "menu_mismatch":
                turns.append(("ai", f"One large {item}, got it."))
                turns.append(("guest", f"No, a regular {item}."))
            elif issue == "modifier_mapping":
                turns.append(("guest", "And no onions on that one."))
                turns.append(("ai", "Sure. Anything else?"))
            elif issue == "pos_injection":
                turns.append(("ai", "One moment while I send that to the kitchen..."))
                turns.append(("ai", "Sorry for the wait, confirmed."))

        turns.append(("ai", f"One {item}. Anything else?"))

    if upsell_item:
        turns.append(("ai", f"Would you like {upsell_item} with that? It's popular today."))
        if upsell_accepted:
            turns.append(("guest", "Yeah, sure."))
            turns.append(("ai", f"Great, added {upsell_item}."))
        else:
            turns.append(("guest", "No thanks."))
            turns.append(("ai", "No problem."))

    turns.append(("ai", "Will there be anything else?"))

    if outcome == "abandoned":
        turns.append(("guest", "You know what, never mind. Forget it."))
        turns.append(("ai", "I'm sorry about that. Drive safe."))
    elif outcome == "assisted":
        turns.append(("ai", "Let me get a team member to help you with that."))
        turns.append(("guest", "Thank you."))
    elif outcome == "error":
        turns.append(("ai", "I'm having trouble with this order. Please order again at the window."))
    else:
        turns.append(("guest", "That's everything, thanks."))
        turns.append(("ai", f"Your total is ${total:.2f}. Please pull forward."))

    return turns


def enrich_turns(turns, noise, peak):
    """Add an ASR confidence to each guest turn and a latency to each AI turn."""
    records = []
    for idx, (speaker, text) in enumerate(turns):
        if speaker == "guest":
            base = 0.97 - 0.05 * noise - 0.03 * peak
            if idx > 0 and any(m in text.lower() for m in
                               ("repeat", "i said", "no, a", "no onions", "never mind")):
                base -= 0.05  # guests who must repeat are usually less clear
            conf = max(0.50, base + random.uniform(-0.02, 0.02))
            records.append({"speaker": "guest", "text": text,
                            "asr_confidence": round(conf, 2), "latency_ms": None})
        else:
            records.append({"speaker": "ai", "text": text,
                            "asr_confidence": None, "latency_ms": random.randint(300, 1800)})
    return records


# --------------------------------------------------------------------------
# Full order builder
# --------------------------------------------------------------------------
def build_order(index):
    """Build one complete order record, including its transcript."""
    store_id = random.choice(list(STORES))
    store = STORES[store_id]
    noise = store["noise"] * random.uniform(0.7, 1.3)  # per-order site noise

    hour = random.randint(6, 23)
    peak = 1 if hour in PEAK_HOURS else 0
    day = random.randint(1, 30)
    dow = DOW[(day - 1) % 7]

    num_items = random.randint(1, 5)
    items = random.sample([name for name, _ in MENU], num_items)
    base_total = round(sum(dict(MENU)[name] for name in items), 2)

    issues = pick_issues(noise, peak)
    outcome = order_outcome(noise, len(issues), peak)
    corrections = len(issues) + (1 if outcome == "assisted" else 0)

    upsell_attempted = random.random() < 0.45
    upsell_item = random.choice(list(UPSELS)) if upsell_attempted else None
    upsell_accepted = bool(upsell_attempted and random.random() < (0.6 - 0.1 * len(issues)))
    upsell_addon = round(UPSELS[upsell_item], 2) if upsell_accepted else 0.0
    total = round(base_total + upsell_addon, 2)

    transcript = enrich_turns(
        build_transcript(items, issues, outcome, upsell_item, upsell_accepted, total),
        noise, peak)

    # Menu Board Time: seconds at the board. It grows with items, errors,
    # staff assists, and rush-hour traffic.
    mbt = int(25 + 7 * num_items + 14 * len(issues) + 12 * (outcome == "assisted")
              + 15 * peak + random.uniform(-6, 10))
    mbt = max(15, mbt)

    sentiment = max(-1.0, min(1.0,
        0.35 - 0.18 * len(issues) - 0.12 * corrections
        - 0.10 * (outcome in ("assisted", "abandoned", "error"))
        + (0.10 if upsell_accepted else 0)
        + random.uniform(-0.12, 0.12)))

    ai_latencies = [t["latency_ms"] for t in transcript if t["speaker"] == "ai"]
    confs = [t["asr_confidence"] for t in transcript if t["speaker"] == "guest"]

    return {
        "order_id": f"ORD-{1000 + index}",
        "store_id": store_id,
        "store_name": store["name"],
        "region": store["region"],
        "day": day,
        "day_of_week": dow,
        "hour": hour,
        "is_peak": peak,
        "items": items,
        "num_items": num_items,
        "base_total": base_total,
        "total": total,
        "upsell_attempted": upsell_attempted,
        "upsell_item": upsell_item,
        "upsell_accepted": upsell_accepted,
        "upsell_addon": upsell_addon,
        "outcome": outcome,
        "menu_board_time_sec": mbt,
        "asr_confidence": round(mean(confs), 2),
        "latency_avg_ms": round(mean(ai_latencies)),
        "issues": issues,
        "num_issues": len(issues),
        "corrections": corrections,
        "sentiment_score": round(sentiment, 2),
        "transaction_completed": outcome in ("completed_ai", "assisted"),
        "transcript": transcript,
    }


def generate_dataset(n=1000):
    """Generate n orders and write them to OUTPUT_PATH."""
    os.makedirs("data", exist_ok=True)
    orders = [build_order(i) for i in range(n)]
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(orders, fh, indent=2)
    return orders


if __name__ == "__main__":
    orders = generate_dataset()
    print(f"Generated {len(orders)} orders -> {OUTPUT_PATH}")
