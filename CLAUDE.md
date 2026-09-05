# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

XuanWu (玄武) is a Xiangqi engine written from scratch. No external chess
library. The evaluation is a blend of a handcrafted function and a neural
network trained on 16 million positions labelled by Pikafish.

Positions are scored on a **0–1000 scale from Red's (White's) point of view**:
500 = balanced, 505 = starting position (500 + 5 tempo), 1000 = mate available
this move. This scale is a hard requirement — do not change it.

## Build and run

```bash
bash csrc/build.sh                       # compile the C core (required for speed)
python3 tests/test_engine.py             # 11 tests, must all pass
python3 main.py --manh-nhat --giay 10    # analyse a position, 10-second budget
python3 web/server.py                    # local web UI, opens the browser
```

The C library `engine/libxuanwu.so` is platform-specific and gitignored. The
engine falls back to pure Python if it is missing (about 30× slower, still
correct — verified by running the test suite with the library removed).

## Layout

```
engine/     board rules, search, evaluation, C bridge, game rules, book
csrc/       the C core: move generation, search, NNUE forward pass
tools/      data collection, training, matches, measurement
web/        local server and single-page UI
weights/    network weights (.npz) and opening book
docs/       measurement logs — read these before repeating an experiment
```

## Non-negotiable rules

**Never generate training labels yourself.** Every label comes from an external
engine (Pikafish depth 10) or from chessdb. Positions may be generated locally;
labels may not.

**Verify with perft after any change to move generation.** Reference values from
the starting position: `44 / 1,920 / 79,666 / 3,290,240`. Perft alone is not
sufficient — it starts from one position and misses rule bugs that only appear
elsewhere. Also diff against the Python implementation across thousands of real
positions.

**Only head-to-head play measures strength.** Every indirect metric has misled
this project at least once: RMSE against labels, error versus Pikafish's score,
and "picks Pikafish's best move" all pointed the wrong way. Run a match, report
the confidence interval, and discard changes whose interval contains zero.

## Measured facts, so they are not re-derived

Search speed with the C core, blend evaluator, from the starting position:

| depth | time |
|---|---|
| 8 | 0.46 s |
| 10 | 1.27 s |
| 12 | 6.38 s |

Strength, 24–30 games per row, versus Pikafish limited by node count:

| configuration | 2,000 nodes | 20,000 nodes | 200,000 nodes |
|---|---|---|---|
| depth 8, no book | 35.4% | 14.6% | 16.7% |
| depth 10, book | 54.2% | — | — |
| depth 12, book | — | 39.5% | 27.3% |

## Changes that were tried and rejected — do not retry without new evidence

| Change | Result |
|---|---|
| Double the network (331k → 678k params) | no improvement at all |
| HalfKP features (5.8M params) | 23% **worse** — overfits on 16M samples |
| Cosine learning-rate schedule | RMSE 57 → 56, negligible |
| Phase-dependent blend weight | **−117 Elo** (CI −251…−11) |
| Check extensions | +12 Elo but 64% slower — net loss at equal time |
| Opening book | 35.4% → 35.0%, no measurable gain |
| Bitboards for move generation | 1.6× only; the mask is fast but extracting a
  move list is a Python loop |
| Make/unmake instead of copying the board | 0% — memcpy of 90 bytes is free |

The bottleneck is **training data volume**: 16 million positions, roughly 100×
fewer than Pikafish's network was trained on. Adding capacity does not help.

## Silent bugs that were found the hard way

These produced plausible output while being wrong. Watch for the pattern.

- **Zobrist table never loaded in C** — every position hashed to 0, so all
  positions shared one transposition-table slot and the engine returned garbage
  scores. No crash, no error.
- **LMR counted illegal moves in its index** after switching to lazy legality,
  so it reduced the wrong moves. No test failed; perft stayed correct.
- **Legality filter missed the horse-leg squares** — a piece blocking an enemy
  horse's leg can expose the general when it moves, and those squares are not on
  the general's rank or file. Perft passed; 18 of 4,000 positions differed.
- **Aspiration window stored the abort value** when time ran out, so the
  evaluation bar jumped to 0 mid-search.
- **A/B test that never disabled the network** — the blend function always ran
  the network before applying the weight, so setting the weight to 0 changed
  nothing and the measurement was meaningless.

## Style

Code comments are in English. Explain **why**, not what — especially the reason
a non-obvious approach was chosen, and any measurement that justified it.

Commit messages are in Vietnamese, and state what was measured, not just what
changed. Include the numbers.
