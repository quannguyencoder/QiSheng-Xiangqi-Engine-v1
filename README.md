# QiSheng (棋聖) — Xiangqi Engine v1

A **Xiangqi** (Chinese chess) engine written entirely from scratch in Python — its own move
generation, its own search, its own evaluation. **No chess library of any kind is used.**
The neural evaluator is trained on positions labeled by *external* sources; the engine never
scores its own training data.

## Scoring scale

Every position is scored on a **0–1000 scale from Red/White's perspective**:

| Score | Meaning |
|---:|---|
| 1000 | White has a **mate in this very move** |
| 505 | the starting position (White moves first, +5 tempo) |
| 500 | balanced |
| 0 | the same, reversed, for Black |

Mate scores decay with depth (1000 → 999 → 998…), so the engine always prefers the
**shortest** mate.

## Project status

Under active development. What exists and — just as importantly — what does not:

| Component | Status |
|---|---|
| Rules + move generation | ✅ Verified by perft against reference values |
| Search (alpha-beta, quiescence, TT, move ordering) | ✅ Working |
| Handcrafted evaluation (material + mobility + PST) | ✅ Working |
| External data collection | 🔄 Running — 50337 positions so far |
| Neural evaluator | ⚠️ Trained, but **not yet wired into the engine** |
| Elo measurement | ❌ None — needs a match harness against Pikafish |
| Web interface | ❌ Not built |

**No Elo figure is claimed anywhere in this repository.** Without a match harness playing real
games against a reference engine, any strength number would be guesswork.

## Layout

```
engine/            engine core — pure Python, zero dependencies
  board.py           10×9 board, move generation for all 7 piece types, flying-general rule
  evaluate.py        static evaluation: material + mobility + placement
  pst.py             piece-square tables per piece type
  search.py          alpha-beta + quiescence + transposition table + move ordering
  scoring.py         conversion to the 0–1000 scale (kept separate so it can be recalibrated)
tools/             offline scripts — used only for data collection and training
  crawl_chessdb.py   BFS crawler harvesting labeled positions from chessdb.cn
  collect_openings.py opening collection via self-play walks
  train.py           trains the evaluation network (PyTorch)
tests/             perft, movement rules, scoring
data/              training data (JSONL) + BFS queues
weights/           trained network weights
web/               interactive board (not built yet)
main.py            CLI position analyzer
```

The engine itself runs on **pure Python**. `requirements.txt` (PyTorch, NumPy) is needed
**only for training**, never at play time.

## Usage

```bash
python3 main.py                              # analyze the starting position
python3 main.py "<FEN>" --depth 2            # analyze any position
python3 tests/test_engine.py                 # run the full test suite
python3 tools/train.py --epochs 60           # retrain the evaluation network
python3 tools/crawl_chessdb.py --output data/x.jsonl --shard 0 --num-shards 6
```

## Search techniques

| Technique | Effect |
|---|---|
| Alpha-beta pruning | skips branches that cannot affect the result |
| MVV-LVA move ordering | tries high-value captures by cheap attackers first, pruning far more |
| Transposition table (Zobrist) | a position reached by different move orders is computed once |
| Quiescence search | never stops mid-exchange (defeats the horizon effect) |

**What quiescence actually fixed:** from the starting position, White's cannon can jump over
Black's cannon to capture a horse. Without quiescence the engine scored that move **610**
(thinking it had won material) because it could not see the immediate recapture. With
quiescence the same move scores **481** — its true value.

## Data

All labels come from **external sources**. The engine does not grade its own training data.

| Source | Positions | Notes |
|---|---:|---|
| chessdb.cn | 12924 | win rates from real games + strong engine analysis; growing |
| internal engine (frozen) | 37,391 | legacy set, kept because it teaches material correctly |
| **Total** | **50337** | |

`crawl_chessdb.py` runs a **breadth-first search over the analyzed part of chessdb's own
position tree**: each query returns every move chessdb knows for that position, and each of
those moves leads to a child position that is also inside the analyzed region. Nearly every
request therefore yields a labeled sample, instead of wandering out of the covered region as
random walks do.

**Why the internal-engine set is kept.** Measured, not assumed. A network trained on chessdb
data alone gets a better MAE on openings (36.1 vs 53.1) but understands material **backwards**:
remove one of Black's chariots and it thinks Black *improved* — wrong 81% of the time. The
chessdb data available so far consists almost entirely of balanced openings, so the network
never sees material imbalance.

## Target dataset size

The network has **797,313 parameters**. At the common heuristic of ~10 samples per parameter,
the useful ceiling for this architecture is about **8 million positions** — which is the current
collection target. Beyond that, a fixed-capacity model gains little: it starts averaging over
examples it lacks the capacity to separate.

One honest caveat: BFS-adjacent positions differ by a single move, so the dataset is highly
redundant. Eight million BFS positions carry far less information than eight million independent
ones, and 1–2 million diverse positions may already capture most of the benefit.

At the measured crawl rate of **15,588 positions/hour** (374,112/day), 8 million positions
require **~21 days** of continuous crawling. A local Pikafish labeler would cut this by an
order of magnitude and, unlike chessdb, could grade material-imbalanced positions too.

## Tests

```
perft(1) =     44   ✓
perft(2) =  1,920   ✓
perft(3) = 79,666   ✓
```

Perft counts leaf positions at depth N and matches the reference values for Xiangqi exactly —
a single flaw in the movement rules would change these numbers immediately. The suite also
covers the cannon's screen requirement, the horse's blocked leg, the elephant's inability to
cross the river, the soldier's sideways move after crossing, and the flying-general rule.

## Performance

| Depth | Time |
|---:|---|
| 1 | 0.2 s |
| 2 | 2.1 s |
| 3 | 13.6 s |

The bottleneck is `is_square_attacked()`: every check test scans all 90 squares and generates
every enemy move. Replacing it with ray casting from the general's square would be several times
faster without changing any result — the highest-value optimization left.

## Roadmap

- [ ] Optimize `is_square_attacked()` to reach deeper searches
- [ ] Wire the neural evaluator into the engine (trained, but currently unused)
- [ ] Add Pikafish as a second label source (it can grade imbalanced positions; chessdb cannot)
- [ ] Build a match harness to **measure real Elo**
- [ ] Web interface: interactive board, evaluation bar, best-move arrows

## License

Not chosen yet. Data under `data/` originates from chessdb.cn — check their terms before
reusing it for other purposes.
