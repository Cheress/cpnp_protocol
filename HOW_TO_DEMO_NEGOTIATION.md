# How to Run the Negotiation Round-Bound Demonstration


It shows three things:
1. The round limit follows from a **formula**, not an arbitrary choice.
2. The formula is **validated by simulation** — thousands of negotiations run
   through the actual negotiation logic.
3. The result is **reproducible** — run it twice, get identical numbers.

---

## How to run it

You need only Python 3 — no installation, no internet, no other files.

```bash
python3 CPNP_negotiation_demo.py
```

```bash
python3 CPNP_negotiation_demo.py 20000
```

To prove reproducibility, run it twice and point out the numbers are identical:
```bash
python3 CPNP_negotiation_demo.py
python3 CPNP_negotiation_demo.py
```

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




