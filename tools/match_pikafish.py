"""
QiSheng - danh doi khang voi Pikafish de DO SUC CO THAT.

Cho toi truoc khi co file nay, du an khong co cach nao do Elo, nen README
khong dam ghi bat ky con so suc co nao. Cach do: cho QiSheng danh nhieu van
voi Pikafish bi ha suc (gioi han do sau / thoi gian), doi ben moi van, roi
suy ra chenh lech Elo tu ti le diem.

Elo = -400 * log10(1/score_rate - 1)   voi score_rate = (thang + 0.5*hoa) / so_van

Luu y: Pikafish o depth 1 van rat manh (danh gia NNUE cua no rat tot du khong
tim sau), nen day la thuoc do "con bao xa" chu chua phai thang do Elo tuyet doi.
"""

import argparse
import math
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import WHITE, BLACK, start_board, legal_moves, make_move
from engine.search import evaluate_current_position
from tools.collect_openings import board_to_fen, iccs_to_move


class Pikafish:
    def __init__(self, binary: str, depth: int, movetime: int = 0, nodes: int = 0):
        self.depth, self.movetime, self.nodes = depth, movetime, nodes
        self.p = subprocess.Popen(
            [binary], cwd=os.path.dirname(binary),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self._send("uci"); self._wait("uciok")
        self._send("setoption name Threads value 1")
        self._send("isready"); self._wait("readyok")

    def _send(self, c): self.p.stdin.write(c + "\n"); self.p.stdin.flush()

    def _wait(self, tok):
        out = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            out.append(line.strip())
            if line.startswith(tok):
                break
        return out

    def best_move(self, fen: str):
        self._send(f"position fen {fen} - - 0 1")
        if self.nodes:
            limit = f"nodes {self.nodes}"
        elif self.movetime:
            limit = f"movetime {self.movetime}"
        else:
            limit = f"depth {self.depth}"
        self._send(f"go {limit}")
        lines = self._wait("bestmove")
        if not lines:
            return None
        parts = lines[-1].split()
        return None if len(parts) < 2 or parts[1] == "(none)" else parts[1]

    def close(self):
        try:
            self._send("quit"); self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


def play_game(eng: Pikafish, qisheng_is_white: bool, depth: int, max_plies: int):
    """Tra ve 1.0 neu QiSheng thang, 0.5 hoa, 0.0 thua."""
    board, side = start_board(), WHITE
    for _ in range(max_plies):
        moves = legal_moves(board, side)
        if not moves:
            # Ben den luot het nuoc di = thua (dung luat co tuong)
            qisheng_to_move = (side == WHITE) == qisheng_is_white
            return 0.0 if qisheng_to_move else 1.0

        if (side == WHITE) == qisheng_is_white:
            _, mv = evaluate_current_position(board, side, depth=depth)
            if mv is None:
                return 0.0
        else:
            iccs = eng.best_move(board_to_fen(board, side))
            if iccs is None:
                return 1.0
            try:
                mv = iccs_to_move(iccs)
            except Exception:
                return 1.0
            if mv not in moves:
                return 1.0        # Pikafish tra nuoc la -> tinh nhu ta thang

        board = make_move(board, mv)
        side = BLACK if side == WHITE else WHITE
    return 0.5                    # het so nuoc cho phep -> tinh hoa


def main() -> None:
    ap = argparse.ArgumentParser(description="Do suc co QiSheng vs Pikafish")
    ap.add_argument("--binary", default="/Users/quan.nguyen/quannguyen/Coding/Pikafish/src/pikafish")
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--qisheng-depth", type=int, default=2)
    ap.add_argument("--pikafish-depth", type=int, default=1)
    ap.add_argument("--pikafish-nodes", type=int, default=0,
                    help="Ha suc Pikafish bang gioi han so nut tim kiem (0 = khong gioi han)")
    ap.add_argument("--max-plies", type=int, default=120)
    ap.add_argument("--nnue", default=None, help="Dung mang no-ron (.npz) thay danh gia thu cong")
    args = ap.parse_args()

    if args.nnue:
        from engine.nnue import NnueEvaluator
        from engine.search import set_evaluator
        net = NnueEvaluator(args.nnue)
        set_evaluator(net.evaluate)
        print(f"Dung mang no-ron: {args.nnue}")
    else:
        print("Dung danh gia thu cong")

    eng = Pikafish(args.binary, args.pikafish_depth, nodes=args.pikafish_nodes)
    score, results = 0.0, []
    t0 = time.time()
    try:
        for g in range(args.games):
            qs_white = (g % 2 == 0)       # doi ben moi van cho cong bang
            r = play_game(eng, qs_white, args.qisheng_depth, args.max_plies)
            score += r
            results.append(r)
            ten = {1.0: "THANG", 0.5: "hoa", 0.0: "thua"}[r]
            print(f"  van {g+1}/{args.games}: QiSheng cam "
                  f"{'Trang' if qs_white else 'Den'} -> {ten}"
                  f"  (tong {score}/{g+1})", flush=True)
    finally:
        eng.close()

    n = len(results)
    rate = score / n
    print(f"\nKet qua: {score}/{n} = ti le diem {rate:.1%} "
          f"({results.count(1.0)} thang, {results.count(0.5)} hoa, {results.count(0.0)} thua)")
    print(f"Thoi gian: {(time.time()-t0)/60:.1f} phut")
    if rate <= 0.0:
        print("Chenh lech Elo: thap hon Pikafish qua nhieu de do bang so van nay "
              "(khong thang duoc van nao).")
    elif rate >= 1.0:
        print("Chenh lech Elo: cao hon (thang toan bo) - can them van de do chinh xac.")
    else:
        elo = -400 * math.log10(1 / rate - 1)
        doi_thu = (f"Pikafish {args.pikafish_nodes} nut" if args.pikafish_nodes
                   else f"Pikafish depth {args.pikafish_depth}")
        print(f"Chenh lech Elo uoc tinh so voi {doi_thu}: {elo:+.0f}")


if __name__ == "__main__":
    main()
