import json

GUESSES_FILE = "guesses.jsonl"
OUTCOMES_FILE = "outcomes.jsonl"


def load_jsonl(path):
    entries = []
    with open(path) as f:
        for line in f:
            entries.append(json.loads(line))
    return entries


def main():
    outcomes = load_jsonl(OUTCOMES_FILE)

    confirmed = sum(1 for o in outcomes if o["verdict"] == "confirmed")
    unknown = sum(1 for o in outcomes if o["verdict"] == "unknown")
    no_data = sum(1 for o in outcomes if o["verdict"] == "no_data")

    print(f"{confirmed} confirmed · {unknown} unknown · {no_data} no_data")


if __name__ == "__main__":
    main()