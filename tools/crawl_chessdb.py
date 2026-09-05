"""
XuanWu - CRAWLER CHI LAY DU LIEU TU BEN NGOAI (chessdb.cn).
TUYET DOI khong tu sinh nhan: moi mau deu co source="chessdb".
The co nao chessdb tra ve "unknown" thi BO QUA, khong tu cham diem.

Chien luoc: duyet theo chieu rong (BFS) tren chinh cay the co ma chessdb da
phan tich. Moi lan hoi mot the co, chessdb tra ve TAT CA nuoc di no biet ->
moi nuoc do sinh ra mot the co con cung nam trong vung da phan tich. Nho vay
gan nhu moi request deu thu duoc 1 mau moi, thay vi di ngau nhien roi truot ra
ngoai vung du lieu nhu cach cu (chi duoc 5.297 mau roi dung).

Chay song song bang cach chia shard theo crc32(FEN) % so_shard, moi worker chi
xu ly phan cua minh; the co con thuoc shard khac duoc ghi sang file handoff
(chi ghi them, khong bao gio cat bot) de worker kia doc tiep tu offset cua no.
"""

import argparse
import json
import os
import time
import zlib
from collections import deque

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.collect_openings import (
    board_to_fen, fen_to_board, iccs_to_move, query_chessdb_queryall, to_white_score,
)
from engine.board import WHITE, BLACK, make_move


def shard_of(fen: str, num_shards: int) -> int:
    return zlib.crc32(fen.encode()) % num_shards


def load_fens(path: str) -> set:
    out = set()
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.add(json.loads(line)["fen"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return out


def drain_handoff(path: str, offset_path: str, frontier: deque, queued: set, seen: set) -> int:
    """Doc phan moi cua file handoff tu offset da luu (file chi duoc ghi them)."""
    if not os.path.exists(path):
        return 0
    offset = 0
    if os.path.exists(offset_path):
        try:
            offset = int(open(offset_path).read().strip() or 0)
        except ValueError:
            offset = 0
    added = 0
    with open(path, "r", encoding="utf-8") as f:
        f.seek(offset)
        while True:
            line = f.readline()          # readline() (khong phai "for line in f")
            if not line:                 # vi for-loop lam f.tell() bi vo hieu hoa
                break
            if not line.endswith("\n"):  # dong dang duoc ghi do dang -> de lan sau
                break
            fen = line.strip()
            if fen and fen not in queued and fen not in seen:
                frontier.append(fen)
                queued.add(fen)
                added += 1
            offset = f.tell()
    with open(offset_path, "w") as f:
        f.write(str(offset))
    return added


def main() -> None:
    p = argparse.ArgumentParser(description="Crawl chessdb.cn theo BFS, chi dung nhan tu ben ngoai")
    p.add_argument("--output", required=True)
    p.add_argument("--target-total", type=int, default=833334, help="Muc tieu so mau cho RIENG worker nay")
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--num-shards", type=int, default=1)
    p.add_argument("--seed-data", default="data/data_openings_chessdb.jsonl",
                   help="File the co da biet, dung lam diem xuat phat cho BFS")
    p.add_argument("--delay", type=float, default=0.35, help="Giay nghi giua 2 request (lich su voi dich vu mien phi)")
    p.add_argument("--save-every", type=int, default=200)
    args = p.parse_args()

    frontier_path = f"data/frontier_s{args.shard}.txt"
    seen = load_fens(args.output)
    frontier: deque = deque()
    queued: set = set()

    if os.path.exists(frontier_path):
        for line in open(frontier_path, encoding="utf-8"):
            fen = line.strip()
            if fen and fen not in seen:
                frontier.append(fen)
                queued.add(fen)

    if not frontier:  # lan dau: nap the co goc thuoc shard nay
        from engine.board import start_board
        roots = [board_to_fen(start_board(), WHITE)]
        roots += sorted(load_fens(args.seed_data))
        for fen in roots:
            if shard_of(fen, args.num_shards) == args.shard and fen not in seen:
                frontier.append(fen)
                queued.add(fen)

    print(f"[shard {args.shard}] da co {len(seen)} mau, frontier {len(frontier)} the co", flush=True)

    stats = {"query": 0, "moi": 0, "unknown": 0, "loi": 0, "loi_mang": 0}
    t0 = time.time()
    with open(args.output, "a", encoding="utf-8") as out:
        while len(seen) < args.target_total:
            if not frontier:
                drain_handoff(f"data/handoff_s{args.shard}.txt", f"data/handoff_s{args.shard}.offset",
                              frontier, queued, seen)
                if not frontier:
                    print(f"[shard {args.shard}] het the co de duyet, dung.", flush=True)
                    break

            fen = frontier.popleft()
            queued.discard(fen)
            if fen in seen:
                continue

            try:
                candidates = query_chessdb_queryall(fen, delay=args.delay,
                                                    raise_on_network_error=True)
            except OSError as exc:
                # Mat mang (may ngu, wifi rot...): KHONG vut the co di, day lai
                # cuoi hang doi de thu lai sau, roi cho mot chut cho mang hoi phuc.
                frontier.append(fen)
                queued.add(fen)
                stats["loi_mang"] += 1
                if stats["loi_mang"] % 20 == 1:
                    print(f"[shard {args.shard}] mat mang ({exc}), da hoan {stats['loi_mang']} "
                          f"the co vao hang doi, cho thu lai...", flush=True)
                time.sleep(min(30.0, 2.0 * min(stats["loi_mang"], 15)))
                continue
            stats["query"] += 1
            if not candidates:
                stats["unknown"] += 1
                continue

            board, side = fen_to_board(fen)
            out.write(json.dumps({
                "fen": fen, "side": side,
                "score": to_white_score(candidates[0]["winrate"], side),
                "best_move": candidates[0]["move"],
                "n_moves": len(candidates),
                "source": "chessdb",
            }, ensure_ascii=False) + "\n")
            out.flush()
            seen.add(fen)
            stats["moi"] += 1

            # Mo rong: moi nuoc chessdb biet -> mot the co con cung trong vung da phan tich
            for cand in candidates:
                try:
                    child_board = make_move(board, iccs_to_move(cand["move"]))
                except Exception:
                    stats["loi"] += 1
                    continue
                child_fen = board_to_fen(child_board, BLACK if side == WHITE else WHITE)
                if child_fen in seen or child_fen in queued:
                    continue
                tgt = shard_of(child_fen, args.num_shards)
                if tgt == args.shard:
                    frontier.append(child_fen)
                    queued.add(child_fen)
                else:
                    with open(f"data/handoff_s{tgt}.txt", "a", encoding="utf-8") as hf:
                        hf.write(child_fen + "\n")

            if stats["moi"] % args.save_every == 0:
                with open(frontier_path, "w", encoding="utf-8") as ff:
                    ff.write("\n".join(frontier))
                drain_handoff(f"data/handoff_s{args.shard}.txt", f"data/handoff_s{args.shard}.offset",
                              frontier, queued, seen)
                dt = max(time.time() - t0, 1e-9)
                print(f"[shard {args.shard}] {len(seen)}/{args.target_total} mau | "
                      f"frontier {len(frontier)} | query {stats['query']}, unknown {stats['unknown']}, "
                      f"loi mang {stats['loi_mang']} | "
                      f"{stats['moi']/dt*60:.0f} mau/phut", flush=True)

    with open(frontier_path, "w", encoding="utf-8") as ff:
        ff.write("\n".join(frontier))
    print(f"[shard {args.shard}] Xong. {len(seen)} mau trong {args.output}", flush=True)


if __name__ == "__main__":
    main()
