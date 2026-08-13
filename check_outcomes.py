import os
import json

GUESSES_FILE = "guesses.jsonl"
OUTCOMES_FILE = "outcomes.jsonl"
REPORT_FILE = "report.json"


def load_guesses():
    guesses = []
    with open(GUESSES_FILE) as f:
        for line in f:
            guesses.append(json.loads(line))
    return guesses


def load_current_test_statuses():
    with open(REPORT_FILE) as f:
        data = json.load(f)
    return {t["name"]: t["status"] for t in data["results"]["tests"]}


def load_past_outcomes():
    if not os.path.exists(OUTCOMES_FILE):
        return []
    past = []
    with open(OUTCOMES_FILE) as f:
        for line in f:
            past.append(json.loads(line))
    return past


def check_outcome(guess, current_statuses, past_outcomes):
    status = current_statuses.get(guess["test_name"])

    if status is None:
        return "no_data", "Test wasn't part of the most recent run; can't check yet.", None

    if guess["category"] == "flaky":
        prior_statuses = {
            o["status"]
            for o in past_outcomes
            if o["test_name"] == guess["test_name"] and o.get("status")
        }
        seen = prior_statuses | {status}
        if "passed" in seen and "failed" in seen:
            return "confirmed", "Observed both passing and failing across separate runs, consistent with flaky behavior.", status
        return "unknown", "Only one outcome observed so far; need both a pass and a fail to confirm flaky behavior.", status

    if status == "passed":
        return "confirmed", "Test no longer fails in the latest run.", status
    return "unknown", "Test is still failing; not enough signal yet to confirm or contradict.", status


def main():
    guesses = load_guesses()
    current_statuses = load_current_test_statuses()
    past_outcomes = load_past_outcomes()

    with open(OUTCOMES_FILE, "a") as out:
        for guess in guesses:
            verdict, reason, status = check_outcome(guess, current_statuses, past_outcomes)
            entry = {
                "test_name": guess["test_name"],
                "category": guess["category"],
                "confidence": guess["confidence"],
                "verdict": verdict,
                "reason": reason,
                "status": status,
            }
            out.write(json.dumps(entry) + "\n")
            print(f"{guess['test_name']} ({guess['category']}, {guess['confidence']}) -> {verdict.upper()}")


def print_summary():
    all_outcomes = []
    with open(OUTCOMES_FILE) as f:
        for line in f:
            all_outcomes.append(json.loads(line))

    categories = {}
    for outcome in all_outcomes:
        cat = outcome["category"]
        categories.setdefault(cat, {"confirmed": 0, "unknown": 0, "no_data": 0, "total": 0})
        categories[cat][outcome["verdict"]] += 1
        categories[cat]["total"] += 1

    print("\n--- Calibration Summary ---")
    MIN_SAMPLES = 20

    total_confirmed = 0
    total_unknown = 0
    total_no_data = 0

    for cat, counts in categories.items():
        checkable = counts["confirmed"] + counts["unknown"]
        if checkable < MIN_SAMPLES:
            print(f"{cat}: not enough data yet ({checkable} confident calls, need {MIN_SAMPLES}+) — {counts['confirmed']} confirmed, {counts['unknown']} unknown, {counts['no_data']} no_data")
        else:
            accuracy = counts["confirmed"] / checkable * 100
            print(f"{cat}: {accuracy:.0f}% ({counts['confirmed']}/{checkable} confirmed)")

        total_confirmed += counts["confirmed"]
        total_unknown += counts["unknown"]
        total_no_data += counts["no_data"]

    print(f"\nTotals across all categories: {total_confirmed} confirmed · {total_unknown} unknown · {total_no_data} no_data")

if __name__ == "__main__":
    main()
    print_summary()