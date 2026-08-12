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


if __name__ == "__main__":
    main()