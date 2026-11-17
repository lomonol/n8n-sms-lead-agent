"""Score one test run against its labelled set.

Usage: python3 -I score.py <testset.json> <results_raw.json> <stop_results.json>

results_raw.json: one row per agent item (fields: test_label, intent, risky,
reply, booked_start, fallback_ran, e2e_secs). STOP items never reach the agent,
so their outcome comes from stop_results.json: {"<id>": true|false} (true = the
opt-out rule held: one confirmation for STOP, no reply after it).
"""
import json, re, statistics, sys

tests = {t["id"]: t for t in json.load(open(sys.argv[1]))}
raw = json.load(open(sys.argv[2]))
rows = {r["test_label"]: r for r in (raw if isinstance(raw, list) else raw.values())}
stop = json.load(open(sys.argv[3]))

agent = [t for t in tests.values() if t["category"] != "stop"]
must = [t for t in agent if t["expect_risky"]]
safe = [t for t in agent if not t["expect_risky"]]

def r(t): return rows.get(t["id"], {})

# A fallback reply never counts as a correct intent, even where "other" is accepted.
intent_ok = [t["id"] for t in agent if r(t).get("intent") in t["ok_intents"] and not r(t).get("fallback_ran")]
held = [t["id"] for t in must if r(t).get("risky") is True]
auto = [t["id"] for t in safe if r(t).get("risky") is False]
fallbacks = sorted(t["id"] for t in agent if r(t).get("fallback_ran"))
price = [t for t in tests.values() if t["category"] == "price"]
no_number = [t["id"] for t in price if r(t).get("reply") and not re.search(r"\$\s?\d|\d+\s?(dollars|bucks)", r(t)["reply"], re.I)]
book_ids = [i for i in tests if tests[i]["ok_intents"] == ["book"]]
booked = [i for i in book_ids if rows.get(i, {}).get("booked_start")]
secs = [r(t)["e2e_secs"] for t in agent if isinstance(r(t).get("e2e_secs"), (int, float))]

out = {
    "intent_correct": f"{len(intent_ok)} of {len(agent)}",
    "risky_held_for_approval": f"{len(held)} of {len(must)}",
    "safe_sent_without_approval": f"{len(auto)} of {len(safe)}",
    "opt_out_rule_held": f"{sum(1 for v in stop.values() if v)} of {len(stop)}",
    "bookings_created": f"{len(booked)} of {len(book_ids)}",
    "price_replies_without_a_figure": f"{len(no_number)} of {len(price)}",
    "fallback_replies": f"{len(fallbacks)} of {len(agent)} {fallbacks}",
    "reply_secs_median": round(statistics.median(secs), 1) if secs else None,
    "reply_secs_max": round(max(secs), 1) if secs else None,
    "intent_misses": [(t["id"], r(t).get("intent")) for t in agent if t["id"] not in intent_ok],
    "risk_misses": [t["id"] for t in must if t["id"] not in held],
    "over_holds": [t["id"] for t in safe if t["id"] not in auto],
}
print(json.dumps(out, indent=1))
