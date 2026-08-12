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


def check_outcome(guess, current_statuses):
    status = current_statuses.get(guess["test_name"])
    if status is None:
        return "no_data", "Test wasn't part of the most recent run; can't check yet."
    if status == "passed":
        return "confirmed", "Test no longer fails in the latest run."
    return "unknown", "Test is still failing; not enough signal yet to confirm or contradict."


def main():
    guesses = load_guesses()
    current_statuses  = load_current_test_statuses()

    with open(OUTCOMES_FILE, "a") as out:
        for guess in guesses:
            verdict, reason = check_outcome(guess, current_statuses )
            entry = {
                "test_name": guess["test_name"],
                "category": guess["category"],
                "confidence": guess["confidence"],
                "verdict": verdict,
                "reason": reason,
            }
            out.write(json.dumps(entry) + "\n")
            print(f"{guess['test_name']} ({guess['category']}, {guess['confidence']}) -> {verdict.upper()}")


if __name__ == "__main__":
    main()