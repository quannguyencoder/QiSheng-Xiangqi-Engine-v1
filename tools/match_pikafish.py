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
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import WHITE, BLACK, start_board, legal_moves, make_move
from engine.search import evaluate_current_position
from tools.collect_openings import board_to_fen, iccs_to_move
from tools.label_pikafish import EngineTreo


class Pikafish:
    """Bao boc Pikafish. Dung chung dong ho canh voi tools/label_pikafish.py:
    readline() tren pipe se cho vinh vien neu tien trinh con ket, va mot van
    dau treo la mat ca buoi do Elo."""

    def __init__(self, binary: str, depth: int, movetime: int = 0, nodes: int = 0,
                 timeout: float = 60.0):
        self.depth, self.movetime, self.nodes = depth, movetime, nodes
        self.binary, self.timeout = binary, timeout
        self._start()

    def _start(self) -> None:
        self.p = subprocess.Popen(
            [self.binary], cwd=os.path.dirname(self.binary),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self._send("uci"); self._wait("uciok")
        self._send("setoption name Threads value 1")
        self._send("isready"); self._wait("readyok")

    def restart(self) -> None:
        try:
            self.p.kill(); self.p.wait(timeout=5)
        except Exception:
            pass
        self._start()

    def _send(self, c):
        try:
            self.p.stdin.write(c + "\n"); self.p.stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as e:
            raise EngineTreo(f"khong gui duoc lenh: {e}")

    def _wait(self, tok):
        out = []
        het_gio = []
        def _giet():
            het_gio.append(True)
            try:
                self.p.kill()
            except Exception:
                pass
        wd = threading.Timer(self.timeout, _giet)
        wd.daemon = True
        wd.start()
        try:
            while True:
                line = self.p.stdout.readline()
                if not line:
                    break
                out.append(line.strip())
                if line.startswith(tok):
                    break
        except (ValueError, OSError) as e:
            raise EngineTreo(f"loi doc ket qua: {e}")
        finally:
            wd.cancel()
        if het_gio:
            raise EngineTreo(f"Pikafish khong tra loi trong {self.timeout:.0f}s")
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
            try:
                iccs = eng.best_move(board_to_fen(board, side))
            except EngineTreo as e:
                print(f"  [canh bao] {e} -> dung engine moi, tinh van nay la hoa",
                      flush=True)
                eng.restart()
                return 0.5
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
    ap.add_argument("--nnue", default=None, help="Dung mang CNN (.npz) thay danh gia thu cong")
    ap.add_argument("--nnue-net", default=None, help="Dung mang NNUE (.npz) thay danh gia thu cong")
    args = ap.parse_args()

    from engine.search import set_evaluator
    if args.nnue_net:
        from engine.nnue_net import MangNnue
        set_evaluator(MangNnue(args.nnue_net).evaluate)
        print(f"Danh gia: mang NNUE ({args.nnue_net})")
    elif args.nnue:
        from engine.nnue import NnueEvaluator
        set_evaluator(NnueEvaluator(args.nnue).evaluate)
        print(f"Danh gia: mang CNN ({args.nnue})")
    else:
        print("Danh gia: ham thu cong")

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
