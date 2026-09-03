"""
QiSheng - sinh va gan nhan the co bang Pikafish chay LOCAL.

Vi sao lam the nay: Pikafish la ENGINE, khong phai kho du lieu - no khong co
san the co nao de lay. Ta phai tu sinh the co roi dua cho no cham diem.
Day dung la cach project tham khao Qilin lam (datagen_sf.py dung Stockfish).

Cach sinh: tu mot the co khai cuoc THAT (da cao tu chessdb), cho Pikafish
tu choi tiep. Moi nuoc di deu goi "go depth D" mot lan - lan goi do vua cho
diem cua the co hien tai, vua cho biet nuoc di de di tiep. Nho vay moi lan
goi engine = 1 mau du lieu, khong lang phi.

Thinh thoang co y di nuoc ngau nhien (--random-prob) hoac nuoc an quan
(--capture-prob) de tao the co LECH QUAN - dung cho lo hong ma du lieu
chessdb khong co (chessdb gan nhu chi co khai cuoc can bang).

Nhan 100% den tu Pikafish. Engine cua QiSheng khong tham gia cham diem.
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import WHITE, BLACK, legal_moves, make_move
from tools.collect_openings import board_to_fen, fen_to_board, iccs_to_move

# Hieu chinh tren 500 the co co nhan chessdb: K=200 cho sai lech nho nhat
# (21 diem tren thang 0..1000), tuc hai nguon nhan nam cung mot thang.
CP_SCALE = 200.0
MATE_CP = 30000


def cp_to_score(cp: int) -> int:
    """Centipawn (goc nhin Trang) -> thang 0..1000 cua QiSheng."""
    return max(0, min(1000, round(1000 / (1 + math.exp(-cp / CP_SCALE)))))


class Pikafish:
    def __init__(self, binary: str, threads: int = 1, hash_mb: int = 128):
        self.p = subprocess.Popen(
            [binary], cwd=os.path.dirname(binary),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self._send("uci"); self._wait("uciok")
        self._send(f"setoption name Threads value {threads}")
        self._send(f"setoption name Hash value {hash_mb}")
        self._send("isready"); self._wait("readyok")

    def _send(self, cmd: str) -> None:
        self.p.stdin.write(cmd + "\n"); self.p.stdin.flush()

    def _wait(self, token: str):
        out = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                break
            out.append(line.strip())
            if line.startswith(token):
                break
        return out

    def analyse(self, fen: str, depth: int):
        """Tra ve (cp theo goc nhin ben di, nuoc di tot nhat) hoac None."""
        self._send(f"position fen {fen} - - 0 1")
        self._send(f"go depth {depth}")
        lines = self._wait("bestmove")
        if not lines:
            return None
        best = lines[-1].split()[1] if len(lines[-1].split()) > 1 else "(none)"
        if best == "(none)":
            return None
        cp = None
        for line in reversed(lines):
            if " score cp " in line:
                cp = int(line.split(" score cp ")[1].split()[0]); break
            if " score mate " in line:
                n = int(line.split(" score mate ")[1].split()[0])
                cp = MATE_CP if n > 0 else -MATE_CP
                break
        return None if cp is None else (cp, best)

    def close(self) -> None:
        try:
            self._send("quit"); self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


def load_seeds(paths):
    seeds = []
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        seeds.append(json.loads(line)["fen"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    return seeds


def load_seen(path):
    seen = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        seen.add(json.loads(line)["fen"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    return seen


def main() -> None:
    ap = argparse.ArgumentParser(description="Sinh + gan nhan the co bang Pikafish local")
    ap.add_argument("--binary", default="/Users/quan.nguyen/quannguyen/Coding/Pikafish/src/pikafish")
    ap.add_argument("--output", required=True)
    ap.add_argument("--target-total", type=int, default=1_333_334)
    ap.add_argument("--depth", type=int, default=10, help="Do sau Pikafish cham diem")
    ap.add_argument("--seed-data", nargs="+",
                    default=["data/data_openings_chessdb.jsonl"])
    ap.add_argument("--max-plies", type=int, default=120, help="So nuoc toi da moi van tu choi")
    ap.add_argument("--random-prob", type=float, default=0.12,
                    help="Xac suat di nuoc ngau nhien (tao da dang)")
    ap.add_argument("--capture-prob", type=float, default=0.10,
                    help="Xac suat ep di nuoc an quan (tao the LECH QUAN)")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--hash", type=int, default=128)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    seeds = load_seeds(args.seed_data)
    if not seeds:
        print(f"LOI: khong doc duoc the co goc tu {args.seed_data}"); return
    seen = load_seen(args.output)
    print(f"{len(seeds)} the co goc | da co {len(seen)} mau trong {args.output}", flush=True)

    eng = Pikafish(args.binary, args.threads, args.hash)
    stats = {"moi": 0, "van": 0, "ngau_nhien": 0, "an_quan": 0}
    t0 = time.time()

    try:
        with open(args.output, "a", encoding="utf-8") as out:
            while len(seen) < args.target_total:
                board, side = fen_to_board(rng.choice(seeds))
                stats["van"] += 1

                for _ in range(args.max_plies):
                    fen = board_to_fen(board, side)
                    res = eng.analyse(fen, args.depth)
                    if res is None:
                        break                      # het nuoc di (chieu het)
                    cp, best_iccs = res
                    cp_white = cp if side == WHITE else -cp

                    if fen not in seen:
                        seen.add(fen)
                        out.write(json.dumps({
                            "fen": fen, "side": side,
                            "score": cp_to_score(cp_white),
                            "cp": cp_white,
                            "best_move": best_iccs,
                            "depth": args.depth,
                            "source": "pikafish",
                        }, ensure_ascii=False) + "\n")
                        stats["moi"] += 1
                        if stats["moi"] % 500 == 0:
                            out.flush()
                            dt = max(time.time() - t0, 1e-9)
                            print(f"{len(seen)}/{args.target_total} | van {stats['van']} | "
                                  f"ngau nhien {stats['ngau_nhien']}, an quan {stats['an_quan']} | "
                                  f"{stats['moi']/dt*60:.0f} mau/phut", flush=True)
                        if len(seen) >= args.target_total:
                            break

                    # Chon nuoc di tiep: mac dinh theo Pikafish, thinh thoang lech
                    # di de tao the co da dang / lech quan.
                    move = None
                    roll = rng.random()
                    if roll < args.capture_prob or roll < args.capture_prob + args.random_prob:
                        moves = legal_moves(board, side)
                        if moves:
                            caps = [m for m in moves if board[m[2]][m[3]] != "."]
                            if roll < args.capture_prob and caps:
                                move = rng.choice(caps); stats["an_quan"] += 1
                            else:
                                move = rng.choice(moves); stats["ngau_nhien"] += 1
                    if move is None:
                        try:
                            move = iccs_to_move(best_iccs)
                        except Exception:
                            break

                    board = make_move(board, move)
                    side = BLACK if side == WHITE else WHITE
            out.flush()
    finally:
        eng.close()

    dt = max(time.time() - t0, 1e-9)
    print(f"Xong. {stats['moi']} mau moi trong {dt/60:.1f} phut "
          f"({stats['moi']/dt*3600:,.0f} mau/gio). Tong: {len(seen)}", flush=True)


if __name__ == "__main__":
    main()
