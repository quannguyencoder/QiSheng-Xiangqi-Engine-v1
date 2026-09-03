"""
QiSheng - thu thap du lieu ca 3 giai doan (khai / trung / tan cuoc).
Sinh ra de bu phan con thieu hoan toan trong
xiangqi_data.jsonl (99,9% du lieu cu la khai cuoc can bang, khien mang hoc
NGUOC o cac the co lech quan).

Chien luoc sinh the co: xuat phat tu mot the co khai cuoc da biet, di ngau
nhien (co uu tien nuoc an quan) de tao chenh lech vat chat that su.

Chien luoc gan nhan (2 nguon):
  1. chessdb.cn - chinh xac tuyet doi, nhat la tan cuoc it quan (co tablebase)
  2. Neu chessdb "unknown" -> tu cham bang search cua engine minh viet.
     Ham eval thu cong tinh vat chat DUNG, day chinh la tin hieu mang dang thieu.
Moi dong du lieu co truong "source" de biet nhan den tu dau.
"""

import argparse
import json
import os
import random
import time

from qisheng import (
    WHITE, BLACK, legal_moves, make_move, evaluate_current_position,
)
from collect_openings import (
    board_to_fen, fen_to_board, query_chessdb_queryall, to_white_score,
)


def count_pieces(board) -> int:
    return sum(1 for row in board for ch in row if ch != ".")


def phase_of(n_pieces: int) -> str:
    if n_pieces >= 28:
        return "khai_cuoc"
    return "trung_cuoc" if n_pieces >= 16 else "tan_cuoc"


def random_walk_to_phase(start_fen: str, want_phase: str, rng: random.Random,
                         capture_bias: float, max_steps: int = 90):
    """Di ngau nhien (uu tien an quan) cho toi khi dat giai doan mong muon.
    Rieng khai cuoc: di vai nuoc truoc de tao the co moi, khong lay lai the co goc."""
    board, side = fen_to_board(start_fen)
    min_steps = rng.randint(2, 12) if want_phase == "khai_cuoc" else 0
    for step in range(max_steps):
        if step >= min_steps and phase_of(count_pieces(board)) == want_phase:
            return board, side
        moves = legal_moves(board, side)
        if not moves:
            return None, None
        captures = [m for m in moves if board[m[2]][m[3]] != "."]
        if captures and rng.random() < capture_bias:
            mv = rng.choice(captures)
        else:
            mv = rng.choice(moves)
        board = make_move(board, mv)
        side = BLACK if side == WHITE else WHITE
    return (board, side) if phase_of(count_pieces(board)) == want_phase else (None, None)


def label_position(board, side, delay: float, depth: int, use_chessdb: bool):
    """Tra ve (score 0..1000 goc nhin Trang, nguon nhan) hoac None.
    chessdb hau nhu khong biet cac the co nay nen chi hoi theo xac suat
    (--chessdb-prob) de van co mot phan nhan chuan xac ma khong cham."""
    fen = board_to_fen(board, side)
    if use_chessdb:
        candidates = query_chessdb_queryall(fen, delay=delay)
        if candidates:
            return fen, to_white_score(candidates[0]["winrate"], side), "chessdb"
    try:
        score, _ = evaluate_current_position(board, side, depth=depth)
    except Exception:
        return None
    return fen, score, "engine"


def main() -> None:
    p = argparse.ArgumentParser(description="Thu thap du lieu trung cuoc + tan cuoc")
    p.add_argument("--seed-data", default="data_openings_chessdb.jsonl",
                   help="File du lieu khai cuoc dung lam diem xuat phat")
    p.add_argument("--output", default="data_midend_engine.jsonl")
    p.add_argument("--target-total", type=int, default=30000)
    p.add_argument("--open-ratio", type=float, default=0.30, help="Ti le khai cuoc")
    p.add_argument("--mid-ratio", type=float, default=0.40, help="Ti le trung cuoc")
    p.add_argument("--end-ratio", type=float, default=0.30, help="Ti le tan cuoc")
    p.add_argument("--capture-bias", type=float, default=0.55,
                   help="Xac suat uu tien nuoc an quan (tao chenh lech vat chat)")
    p.add_argument("--depth", type=int, default=2, help="Do sau search khi tu cham diem")
    p.add_argument("--chessdb-prob", type=float, default=0.15,
                   help="Xac suat thu hoi chessdb (0 = khong hoi, chay nhanh nhat)")
    p.add_argument("--delay", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args()

    rng = random.Random(args.seed)

    seeds = []
    with open(args.seed_data, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    seeds.append(json.loads(line)["fen"])
                except (json.JSONDecodeError, KeyError):
                    continue
    if not seeds:
        print(f"LOI: khong doc duoc the co nao tu {args.seed_data}")
        return
    print(f"Co {len(seeds)} the co khai cuoc lam diem xuat phat")

    seen = set()
    if os.path.exists(args.output):
        with open(args.output, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        seen.add(json.loads(line)["fen"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    print(f"Da co san {len(seen)} the co trong {args.output}")

    stats = {"khai_cuoc": 0, "trung_cuoc": 0, "tan_cuoc": 0, "chessdb": 0, "engine": 0}
    phases = ["khai_cuoc", "trung_cuoc", "tan_cuoc"]
    weights = [args.open_ratio, args.mid_ratio, args.end_ratio]
    t0 = time.time()
    with open(args.output, "a", encoding="utf-8") as f:
        while len(seen) < args.target_total:
            # Tu can bang: uu tien giai doan dang thieu nhat so voi ti le dich,
            # vi di ngau nhien hay "truot" giai doan nen ti le dat duoc lech so voi ti le yeu cau.
            done_now = sum(stats[p] for p in phases) or 1
            want = max(phases, key=lambda p: weights[phases.index(p)] - stats[p] / done_now)
            board, side = random_walk_to_phase(rng.choice(seeds), want, rng,
                                               args.capture_bias)
            if board is None:
                continue
            labeled = label_position(board, side, args.delay, args.depth,
                                     rng.random() < args.chessdb_prob)
            if labeled is None:
                continue
            fen, score, source = labeled
            if fen in seen:
                continue
            seen.add(fen)
            stats[want] += 1
            stats[source] += 1
            f.write(json.dumps({"fen": fen, "side": side, "score": score,
                                "phase": want, "source": source},
                               ensure_ascii=False) + "\n")
            f.flush()

            if len(seen) % 25 == 0:
                dt = max(time.time() - t0, 1e-9)
                done = sum(stats[p] for p in phases)
                print(f"{len(seen)}/{args.target_total} | "
                      f"khai {stats['khai_cuoc']}, trung {stats['trung_cuoc']}, "
                      f"tan {stats['tan_cuoc']} | "
                      f"nhan: chessdb {stats['chessdb']}, engine {stats['engine']} | "
                      f"{done/dt*60:.0f} mau/phut")

    print(f"Xong. Tong cong {len(seen)} the co trong {args.output}")


if __name__ == "__main__":
    main()
