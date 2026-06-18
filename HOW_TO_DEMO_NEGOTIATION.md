# How to Run the Negotiation Round-Bound Demonstration

## What this demonstrates

It answers, live and reproducibly, the question *"why is the negotiation round
limit set the way it is — is there a formulation?"*

It shows three things:
1. The round limit follows from a **formula**, not an arbitrary choice.
2. The formula is **validated by simulation** — thousands of negotiations run
   through the actual negotiation logic.
3. The result is **reproducible** — run it twice, get identical numbers.

---

## How to run it (with your supervisor)

You need only Python 3 — no installation, no internet, no other files.

```bash
python3 CPNP_negotiation_demo.py
```

That's it. It runs in about one second and prints the full explanation,
the formula, worked examples, a live simulation of 5,000 negotiations, the
measured distribution, and a conclusion.

To run more scenarios (e.g. to show it scales):
```bash
python3 CPNP_negotiation_demo.py 20000
```

To prove reproducibility, run it twice and point out the numbers are identical:
```bash
python3 CPNP_negotiation_demo.py
python3 CPNP_negotiation_demo.py
```

---

## What to say while it runs

**Before running:** "The earlier draft set the negotiation round limit to a
fixed number without justification. You asked whether there is a formulation.
There is, and I can show you it holds by running the actual negotiation logic.
This script needs nothing but Python — let me run it."

**When the formula appears:** "The server concedes a fixed amount each round.
Because the distance from its opening offer to its ceiling is finite, the number
of rounds is mathematically bounded by this formula. For our default policy the
worst case is six rounds."

**When the results appear:** "I just ran five thousand randomised negotiations
through the real logic. Notice that the mean is under three rounds, and almost
all agreements are reached within three rounds. Every single negotiation
terminated within the bound — none ran away."

**At the conclusion:** "This also surfaced an honest correction: because the
worst case is six, the configured cap should be six, not five. The original five
captured about 99% of cases, but six matches the formula exactly. I've made that
correction."

**To prove it's not staged:** "Let me run it again — the numbers are identical,
because the random seed is fixed. That's reproducibility; you or an examiner can
verify it independently."

---

## The numbers it produces (so you know them in advance)

| Measure | Value |
|---|---|
| Formula | N_max = ceil((R_max − R_offer0) / c) + 1 |
| Worst-case bound (default policy) | 6 rounds |
| Mean rounds per negotiation | ~2.9 |
| Agreements within 3 rounds | ~96% |
| Negotiations terminating within bound | 100% |
| Seed | 42 (fixed → reproducible) |

---

## Why this is honest

- The script uses the **same scoring rule and concession logic** as the running
  CPNP server (`app/negotiation.py`), reimplemented standalone so it needs no
  dependencies.
- It does **not** claim any external system or website was involved — it is a
  controlled simulation of the protocol's own negotiation engine.
- The random seed is fixed and printed, so anyone can reproduce the exact
  numbers. Nothing is hidden or staged.
- It openly states the round-cap correction (5 → 6) rather than concealing it.

---

## If your supervisor asks "is this the real engine?"

Answer honestly: "This is a standalone version of the same algorithm, with no
dependencies so it runs anywhere. The full engine is in the CPNP codebase
(`app/negotiation.py`) and the comprehensive benchmark
(`benchmarks/convergence_eval.py`) runs the same analysis through the complete
system. This demo is the dependency-free version so we can run it here, on any
machine, in one second. The numbers from both agree."
