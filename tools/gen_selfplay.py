"""
XuanWu - sinh the co tu VAN CO CUA CHINH XUANWU, roi nho Pikafish cham diem.

Vi sao can: toan bo 16 trieu mau hien co deu la the co PIKAFISH tu choi. Nhung
XuanWu danh khac Pikafish, no di vao nhung the co ma Pikafish khong bao gio
gap - va do chinh la nhung cho no danh gia sai nhat. Chan doan cho thay sai so
lon nhat o tan cuoc (65,5 diem) va the lech quan (67,1 diem).

Nhan van do PIKAFISH cham, dung nhu moi lan truoc. Chi khac o cho THE CO den
tu dau: tu van co that cua XuanWu thay vi cua Pikafish.

  python3 tools/sinh_the_co_xuanwu.py --output data/data_xuanwu_s0.jsonl \\
      --so-van 200 --depth 6
"""

import argparse
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import WHITE, BLACK, start_board, legal_moves, make_move
from engine import c_core
from engine.evaluate import evaluate as thu_cong
from engine.nnue_net import MangNnue
from tools.collect_openings import board_to_fen, fen_to_board
from tools.label_pikafish import CP_SCALE, EngineTreo, Pikafish, cp_to_score


def main() -> None:
    ap = argparse.ArgumentParser(description="Sinh the co tu van co XuanWu")
    ap.add_argument("--output", required=True)
    ap.add_argument("--so-van", type=int, default=200)
    ap.add_argument("--depth", type=int, default=6)
    ap.add_argument("--max-plies", type=int, default=140)
    ap.add_argument("--mang", default="weights/nnue_tanh.npz")
    ap.add_argument("--trong-so", type=float, default=0.4)
    ap.add_argument("--binary",
                    default="/Users/quan.nguyen/quannguyen/Coding/Pikafish/src/pikafish")
    ap.add_argument("--pikafish-depth", type=int, default=10)
    ap.add_argument("--random-prob", type=float, default=0.10,
                    help="Ti le di nuoc ngau nhien de van co da dang")
    ap.add_argument("--khai-cuoc", default="data/data_openings_chessdb.jsonl")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if not c_core.co_loi_c():
        raise SystemExit("Can thu vien C - chay csrc/build.sh truoc")
    net = MangNnue(args.mang)
    c_core.nap_mang(net.w1, net.b1, net.w2, net.b2, net.w3, net.b3)
    b0 = start_board()
    w = args.trong_so
    c_core.tim_kiem_khoi_tao(
        w, 505.0 - ((1 - w) * thu_cong(b0, "w") + w * net.evaluate(b0, "w")))

    rng = random.Random(args.seed)
    khai = []
    if os.path.exists(args.khai_cuoc):
        with open(args.khai_cuoc, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        khai.append(json.loads(line)["fen"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    rng.shuffle(khai)

    # Buoc 1: cho XuanWu tu danh, thu thap the co no di qua
    print(f"Danh {args.so_van} van XuanWu vs XuanWu (depth {args.depth})...",
          flush=True)
    the_co = []
    for v in range(args.so_van):
        board, side = (fen_to_board(khai[v % len(khai)]) if khai
                       else (start_board(), WHITE))
        for _ in range(args.max_plies):
            mvs = legal_moves(board, side)
            if not mvs:
                break
            the_co.append(board_to_fen(board, side))
            if rng.random() < args.random_prob:
                mv = rng.choice(mvs)
            else:
                _, mv, _ = c_core.tim_kiem(board, side, args.depth)
                if mv is None:
                    break
            board = make_move(board, mv)
            side = BLACK if side == WHITE else WHITE
        if (v + 1) % 20 == 0:
            print(f"  {v+1}/{args.so_van} van | {len(the_co):,} the co", flush=True)

    # Bo trung lap va nhung the co da co trong du lieu cu
    seen = set()
    if os.path.exists(args.output):
        with open(args.output, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        seen.add(json.loads(line)["fen"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    moi = [f for f in dict.fromkeys(the_co) if f not in seen]
    print(f"\n{len(moi):,} the co moi -> nho Pikafish cham diem", flush=True)

    # Buoc 2: Pikafish cham diem. Nhan 100% tu Pikafish, khong tu tao.
    eng = Pikafish(args.binary)
    dem = 0
    try:
        with open(args.output, "a", encoding="utf-8") as out:
            for i, fen in enumerate(moi):
                try:
                    res = eng.analyse(fen, args.pikafish_depth)
                except EngineTreo as e:
                    print(f"[canh bao] {e} -> dung engine moi", flush=True)
                    eng.restart()
                    continue
                if res is None:
                    continue
                cp, best = res
                cp_trang = cp if fen.split()[1] == "w" else -cp
                out.write(json.dumps({
                    "fen": fen, "side": fen.split()[1],
                    "score": cp_to_score(cp_trang), "cp": cp_trang,
                    "best_move": best, "depth": args.pikafish_depth,
                    "source": "xuanwu_games",
                }, ensure_ascii=False) + "\n")
                dem += 1
                if dem % 2000 == 0:
                    out.flush()
                    print(f"  cham {dem:,}/{len(moi):,}", flush=True)
    finally:
        eng.close()
    print(f"\nXong: {dem:,} the co moi -> {args.output}")


if __name__ == "__main__":
    main()
