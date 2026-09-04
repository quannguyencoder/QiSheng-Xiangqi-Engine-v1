<div align="center">

# QiSheng — Xiangqi Engine v1

**棋聖**

### A Xiangqi AI built from nothing but Python

No chess library. No borrowed engine. Every rule, every search, every evaluation — written from scratch.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Runtime](https://img.shields.io/badge/runtime-zero%20dependencies-success)
![Perft](https://img.shields.io/badge/perft-verified%20✓-success)
![Positions](https://img.shields.io/badge/training%20positions-16M-blue)
![Scale](https://img.shields.io/badge/scoring-0--1000-orange)

</div>

---

## Table of Contents

| Section | |
|---|---|
| [What It Is](#what-it-is) | The idea in 30 seconds |
| [How It Thinks](#how-it-thinks) | Architecture at a glance |
| [Strengths](#strengths) | What it already does well |
| [Under Repair](#under-repair) | Known weaknesses being worked on |
| [What's Coming](#whats-coming) | Development roadmap |
| [Try It](#try-it) | Run it yourself |

---

## What It Is

Show QiSheng any Xiangqi position. It answers with **one number from 0 to 1000** — how good
that position is for Red — and the move it would play.

```mermaid
flowchart LR
    P["♟ Any position"] --> Q(("QiSheng"))
    Q --> S["Score 0–1000"]
    Q --> M["Best move"]
    style Q fill:#c62828,stroke:#7f0000,color:#fff
```

| 1000 | 505 | 500 | 0 |
|:---:|:---:|:---:|:---:|
| mate **this move** | opening position | dead level | lost |

Mate scores decay with distance, so it always takes the **shortest** mate — never just *a* mate.

## How It Thinks

```mermaid
flowchart LR
    subgraph ENGINE["engine/ — pure Python, zero dependencies"]
        direction LR
        B["Rules<br/><small>10×9 board · 7 piece types<br/>flying general</small>"]
        S["Search<br/><small>alpha-beta · quiescence<br/>transposition table</small>"]
        E["Judgement<br/><small>material · mobility<br/>piece-square tables</small>"]
        C["Scale<br/><small>0–1000</small>"]
        B --> S --> E --> C
    end
    IN["FEN"] --> B
    C --> OUT["Score + move"]
    style ENGINE fill:#f8f9fa,stroke:#adb5bd
```

Four independent layers. The scale can be recalibrated without touching judgement; judgement can
be replaced by a neural network without touching search.

## Strengths

```mermaid
flowchart TD
    R(("QiSheng<br/>strengths"))
    R --- A["🎯 <b>Provably correct rules</b><br/>perft 44 / 1,920 / 79,666 — exact match"]
    R --- B["🔍 <b>No horizon blindness</b><br/>a trap scoring 610 without quiescence<br/>is correctly seen as 481"]
    R --- C["📚 <b>Trained on 16M positions</b><br/>labeled by Pikafish at depth 10,<br/>never by itself"]
    R --- D["⚖️ <b>Two independent teachers</b><br/>engine evaluation + real-game win rates<br/>agree to within 21 points"]
    R --- E["🪶 <b>Runs anywhere</b><br/>stock Python — no install, no GPU"]
    style R fill:#c62828,stroke:#7f0000,color:#fff
```

**Balanced training diet.** Positions are drawn deliberately across all three phases, and most
carry a real material imbalance — the situations where a weak evaluator gives itself away.

```mermaid
pie showData
    title Training positions by phase
    "Middlegame" : 51
    "Opening" : 24
    "Endgame" : 24
```

## Under Repair

```mermaid
flowchart LR
    subgraph NOW["Known weaknesses"]
        direction TB
        W1["🎯 The network alone plays WORSE<br/>than the handcrafted evaluator"]
        W2["🐌 Depth 4 takes 16 s —<br/>depth 7 would take an hour"]
        W3["🔍 Search lacks null-move,<br/>LMR, killers, history"]
    end
    W1 --> F1["Blend both: +104 Elo, measured"]
    W2 --> F2["Make/unmake + incremental accumulator"]
    W3 --> F3["Add them — they change the exponent"]
    style NOW fill:#fff8e1,stroke:#f9a825
```

### What the measurements actually say

Every number below comes from games played, not from estimation.

| Evaluator | Head-to-head vs handcrafted | Verdict |
|---|---|---|
| Handcrafted (material + mobility + PST) | — | baseline |
| NNUE alone | −7 Elo at depth 1, −66 at depth 2 | **loses** |
| **Blend, 50/50** | **+104 Elo** (95% CI: +7 … +221) | **strongest** |

The network predicts Pikafish's evaluation more accurately and runs 2.6× faster than the
handcrafted function — and still plays worse on its own. What matters when picking a move is
ranking sibling positions correctly, not absolute accuracy. The handcrafted function errs
systematically, so its ordering survives; the network errs randomly, and at shallow depth that
noise exceeds the real difference between candidate moves. Averaging the two cancels part of the
noise while keeping the positional knowledge.

48 games per data point, each opening played from both sides. Confidence intervals are reported
because at this sample size a single number would overstate what is known.

## What's Coming

```mermaid
flowchart LR
    A["✅ Rules<br/>+ perft"] --> B["✅ Search<br/>upgrades"] --> C["✅ 16M<br/>positions"]
    C --> D["✅ Neural<br/>evaluation"] --> E["✅ Measured<br/>Elo"] --> F["◻ Depth 7<br/>search"] --> G["◻ Web<br/>board"]
    style A fill:#c8e6c9,stroke:#2e7d32
    style B fill:#c8e6c9,stroke:#2e7d32
    style C fill:#c8e6c9,stroke:#2e7d32
```

The web board is the finish line: an interactive position, a live evaluation bar, and an arrow
pointing at the move QiSheng would play.

## Try It

```bash
python3 main.py                       # analyse the opening position
python3 main.py "<FEN>" --depth 2     # analyse any position
python3 tests/test_engine.py          # verify the rules yourself
```

Nothing to install — the engine runs on a stock Python interpreter.
