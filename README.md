# ProofCheck

An AI test triage tool that doesn't just guess why your tests failed — it keeps score on its own guesses, and shows you the receipts.

## The problem

AI test triage tools tell you "90% confident this is a real bug" and never check afterward whether they were right. This tool does.

## What leaves your machine

Only one thing: the failure's test name and traceback, sent to the LLM API
(Gemini, using the key you provide in `.env`) for classification. Nothing else
— no source code beyond what's in the traceback, no data sent to us, no
telemetry.

## How it works

1. Your `pytest` suite runs and fails sometimes.
2. `classify.py` sorts each failure into a category (`real_bug`, `flaky`, `environment`, `test_issue`) with a confidence score, using an LLM. It checks memory first — near-duplicate failures reuse a prior guess instead of calling the API again.
3. `check_outcomes.py` later checks whether each guess held up: did the "flaky" one actually flip between pass/fail across runs? Did the "real bug" one actually stop failing after a code change?
4. `verify.py` independently recomputes the same tally from the raw logs — proving the scorekeeping isn't self-graded.

## Setup

**After cloning, make sure you `cd` into the repo folder before running any of the following commands** — `pip install` will fail with a confusing "file not found" error several steps later if you're still one level up.

```
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file with:
```
GEMINI_API_KEY=your_key_here
```
"After cloning, cd into the repo folder before running any setup commands." — the wrong-folder trap, silent until pip install fails several steps later.
A short Windows troubleshooting note, something like:

### Windows troubleshooting

If `pip install` is blocked by Windows Smart App Control, or `python -m venv venv` hangs with no output, try:

## Usage

```
pytest --ctrf report.json
python classify.py
python check_outcomes.py
python verify.py
```

## Example output

```
suite/test_real_bug.py::test_cart_total
{'category': 'real_bug', 'confidence': 0.89, 'reason': 'The function calculate_total returned 21 instead of the expected 20 for inputs 10 and 2, indicating an arithmetic or logic error in the code under test.'}
```

```
--- Calibration Summary ---
environment: not enough data yet (7 confident calls, need 20+) — 4 confirmed, 3 unknown, 2 no_data
...
Totals across all categories: 23 confirmed · 9 unknown · 24 no_data
```

```
Don't take the tool's word for it — recomputed independently from raw logs:
→ 23 confirmed · 9 unknown · 24 no_data
```

## Design choices

- **Local-only.** Runs on your own machine, not a hosted service — companies with sensitive code can use it without their test data ever leaving their infrastructure.
- **Open format.** Test data flows through CTRF, an open standard — nothing locked behind a proprietary format.
- **Append-only logs.** `guesses.jsonl` and `outcomes.jsonl` are never edited or rewritten, only appended to — every guess and every outcome check is permanently recorded, which is what makes independent verification meaningful.
- **Honest about limits.** The calibration summary refuses to show a percentage below 20 confident guesses per category, and says so plainly, instead of showing a misleading number from too little data.

## Real-world validation

Tested against two real codebases beyond the original fake suite: a fork of
[PyGithub](https://github.com/PyGithub/PyGithub) with deliberately introduced,
known-answer bugs, and a self-built 82-test WordPress E2E suite (Playwright +
REST API) run against a live local WordPress install with real, naturally
occurring failures.

**What this surfaced:** one real, damaging bug in the classifier itself — the
memory-matching logic was collapsing distinct test failures with similarly-shaped
tracebacks into one shared, partly-wrong answer. Fixed by requiring both the
traceback *and* the test name to match before reusing a prior guess.

**Current numbers** (small sample, not yet statistically meaningful — the tool's
own calibration guard agrees, and won't show a percentage until each category
has 20+ confident guesses):

- 24 confirmed · 19 unknown · 32 no_data, independently recomputed and matching
  via `verify.py`
- "Confirmed" means a guess's predicted resolution happened (e.g. a flagged bug
  got fixed, a flaky test showed both a pass and a fail) — not that the original
  label was necessarily correct. "Unknown" mostly means the underlying issue is
  still open, not that the guess was wrong.
- Memory hit-rate is being tracked going forward but doesn't have enough history
  yet on genuinely novel failures to report meaningfully.

## CI

GitHub Actions runs `pytest` + `classify.py` on every push to `main`. Note: guess history (`guesses.jsonl`, `outcomes.jsonl`) doesn't persist between CI runs — this tool is designed to run on a persistent local machine, where history accumulates permanently. CI here demonstrates the pipeline works end-to-end, not long-term memory.

## Roadmap

Out of scope for this MVP, planned for later: real embeddings instead of `difflib` similarity matching, multi-framework support beyond `pytest`, a hosted dashboard, richer contradicted-guess detection.
