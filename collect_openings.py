"""
Thu thap du lieu the co (FEN + diem danh gia 0..1000 + nuoc di tot nhat) tu
Xiangqi Cloud Database (chessdb.cn) - mot co so du lieu cong dong duoc phan
tich boi cac engine manh (Pikafish...) + endgame tablebase, muc do phan tich
o cac dong khai cuoc/tan cuoc pho bien vuot xa 2000 elo.

Cach dung: engine tu viet trong qisheng.py di mot "self-play walk" bat
dau tu the co khoi diem, moi buoc hoi chessdb.cn ve the co hien tai (duoc ca
diem danh gia lan danh sach nuoc di goi y), luu lai thanh 1 dong du lieu, roi
chon (co ngau nhien uu tien nuoc tot) mot trong cac nuoc goi y de di tiep.
Nho vay duong di luon nam trong vung du lieu da duoc chessdb phan tich sau.

Engine ngoai (chessdb.cn) chi dung o day, luc thu thap du lieu offline -
khong duoc goi luc AI thi dau/choi that (xem qisheng.py).

API: https://www.chessdb.cn/cloudbook_api_en.html
"""

import argparse
import json
import os
import random
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from qisheng import (
    Board, Move, WHITE, BLACK,
    start_board, make_move, legal_moves,
)

CHESSDB_URL = "http://www.chessdb.cn/chessdb.php"
USER_AGENT = "AI_co_tuong-data-collector/1.0 (educational self-study project)"

# Chu FEN chuan (kieu co vua quoc te) khac chu noi bo cua qisheng.py o 2 quan:
INTERNAL_TO_FEN = {"H": "N", "E": "B"}
FEN_TO_INTERNAL = {"N": "H", "B": "E"}


def board_to_fen(board: Board, side_to_move: str) -> str:
    rows = []
    for row in board:
        fen_row = ""
        empty = 0
        for cell in row:
            if cell == ".":
                empty += 1
                continue
            if empty:
                fen_row += str(empty)
                empty = 0
            upper = cell.upper()
            mapped = INTERNAL_TO_FEN.get(upper, upper)
            fen_row += mapped if cell.isupper() else mapped.lower()
        if empty:
            fen_row += str(empty)
        rows.append(fen_row)
    return "/".join(rows) + (" w" if side_to_move == WHITE else " b")


def iccs_to_move(iccs: str) -> Move:
    from_col = ord(iccs[0]) - ord("a")
    from_row = 9 - int(iccs[1])
    to_col = ord(iccs[2]) - ord("a")
    to_row = 9 - int(iccs[3])
    return (from_row, from_col, to_row, to_col)


def fen_to_board(fen: str) -> tuple:
    """Nguoc lai voi board_to_fen: FEN -> (Board, ben di)."""
    placement, side = fen.split(" ")
    board = []
    for row_str in placement.split("/"):
        row = []
        for ch in row_str:
            if ch.isdigit():
                row.extend(["."] * int(ch))
            else:
                upper = ch.upper()
                internal = FEN_TO_INTERNAL.get(upper, upper)
                row.append(internal if ch.isupper() else internal.lower())
        board.append(row)
    return board, (WHITE if side == "w" else BLACK)


# Cache trong bo nho: tranh hoi lai chessdb ve cung mot the co nhieu lan.
_query_cache: Dict[str, Optional[List[Dict]]] = {}
MAX_CACHE_ENTRIES = 50000


def query_chessdb_queryall(fen: str, delay: float = 0.0, timeout: float = 10.0) -> Optional[List[Dict]]:
    if fen in _query_cache:
        return _query_cache[fen]  # khong ton request, khong can nghi
    url = f"{CHESSDB_URL}?action=queryall&board={urllib.parse.quote(fen)}&showall=1"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace").strip()
    except OSError as exc:
        print(f"  [canh bao] loi mang khi hoi chessdb: {exc}")
        return None
    finally:
        if delay > 0:
            time.sleep(delay)  # chi nghi khi that su goi mang

    if len(_query_cache) < MAX_CACHE_ENTRIES:
        _query_cache[fen] = None  # tam ghi None, cap nhat lai o cuoi neu co du lieu

    if "move:" not in text:
        return None  # "unknown" / "invalid board" / "checkmate" / "stalemate" / ...

    candidates = []
    for chunk in text.split("|"):
        fields = {}
        for part in chunk.split(","):
            if ":" not in part:
                continue
            key, _, value = part.partition(":")
            fields[key] = value
        if "move" not in fields or "score" not in fields:
            continue
        try:
            candidates.append({
                "move": fields["move"],
                "score": int(fields["score"]),
                "winrate": float(fields.get("winrate", 50.0)),
            })
        except ValueError:
            continue
    candidates.sort(key=lambda d: d["score"], reverse=True)
    result = candidates or None
    if fen in _query_cache:
        _query_cache[fen] = result
    return result


def to_white_score(winrate_for_mover: float, side_to_move: str) -> int:
    """winrate cua chessdb la ti le thang cua BEN DANG DI (mover-relative),
    doi ve thang diem tuyet doi 0..1000 theo goc nhin Trang nhu qisheng.py."""
    white_winrate = winrate_for_mover if side_to_move == WHITE else (100.0 - winrate_for_mover)
    return max(0, min(1000, round(white_winrate * 10)))


def self_play_walk(max_plies: int, delay: float, top_k: int, rng: random.Random,
                   start_fen: Optional[str] = None) -> List[Dict]:
    """start_fen=None: di tu dau van. Nguoc lai: xuat phat tu the co da biet
    (giup di thang toi vung chua kham pha thay vi lap lai khai cuoc moi lan)."""
    if start_fen is None:
        board, side = start_board(), WHITE
    else:
        board, side = fen_to_board(start_fen)
    examples = []
    for _ in range(max_plies):
        fen = board_to_fen(board, side)
        candidates = query_chessdb_queryall(fen, delay=delay)
        if not candidates:
            break

        best = candidates[0]
        examples.append({
            "fen": fen,
            "side": side,
            "score": to_white_score(best["winrate"], side),
            "best_move": best["move"],
        })

        top = candidates[:top_k]
        weights = [1.0 / (i + 1) for i in range(len(top))]
        chosen = rng.choices(top, weights=weights, k=1)[0]
        move = iccs_to_move(chosen["move"])

        if move not in legal_moves(board, side):
            print(f"  [canh bao] nuoc di tu chessdb ({chosen['move']}) khong hop le voi engine noi bo, dung walk nay.")
            break

        board = make_move(board, move)
        side = BLACK if side == WHITE else WHITE
    return examples


def load_existing_fens(path: str) -> set:
    fens = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    fens.add(json.loads(line)["fen"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return fens


def main() -> None:
    parser = argparse.ArgumentParser(description="Thu thap du lieu the co tu chessdb.cn")
    parser.add_argument("--games", type=int, default=20, help="So luot self-play walk")
    parser.add_argument("--max-plies", type=int, default=40, help="So nuoc toi da moi walk")
    parser.add_argument("--top-k", type=int, default=5, help="Chon ngau nhien trong top-k nuoc goi y")
    parser.add_argument("--delay", type=float, default=0.3, help="Giay nghi giua 2 request (lich su voi dich vu cong dong)")
    parser.add_argument("--output", type=str, default="data_openings_chessdb.jsonl", help="File JSONL luu du lieu")
    parser.add_argument("--target-total", type=int, default=None,
                         help="Dung som ngay khi tong so the co (ca cu + moi) dat muc nay")
    parser.add_argument("--stall-patience", type=int, default=100,
                         help="Dung neu bay nhieu walk lien tiep khong tim duoc the co moi nao (het vung du lieu da phan tich)")
    parser.add_argument("--frontier-prob", type=float, default=0.8,
                         help="Xac suat xuat phat walk tu mot the co da biet thay vi tu dau van (0..1)")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    seen_fens = load_existing_fens(args.output)
    known_fens = list(seen_fens)  # de chon ngau nhien diem xuat phat
    print(f"Da co san {len(seen_fens)} the co trong {args.output}")
    if args.target_total is not None and len(seen_fens) >= args.target_total:
        print(f"Da dat muc tieu {args.target_total} the co, khong can thu thap them.")
        return

    total_new = 0
    stall_count = 0
    with open(args.output, "a", encoding="utf-8") as f:
        for g in range(args.games):
            start_fen = None
            if known_fens and rng.random() < args.frontier_prob:
                start_fen = rng.choice(known_fens)
            examples = self_play_walk(args.max_plies, args.delay, args.top_k, rng, start_fen)
            new_in_walk = 0
            for ex in examples:
                if ex["fen"] in seen_fens:
                    continue
                seen_fens.add(ex["fen"])
                known_fens.append(ex["fen"])
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                new_in_walk += 1
            f.flush()
            total_new += new_in_walk
            print(f"Walk {g + 1}/{args.games}: {len(examples)} the co ({new_in_walk} moi) -> "
                  f"tong moi: {total_new}, tong cong: {len(seen_fens)}")

            if args.target_total is not None and len(seen_fens) >= args.target_total:
                print(f"Da dat muc tieu {args.target_total} the co, dung thu thap.")
                break

            stall_count = 0 if new_in_walk > 0 else stall_count + 1
            if stall_count >= args.stall_patience:
                print(f"Khong tim duoc the co moi sau {args.stall_patience} walk lien tiep - "
                      f"co ve da het vung du lieu chessdb.cn da phan tich ma walk nay con toi duoc. Dung som.")
                break

    print(f"Xong. Tong so the co moi them vao {args.output}: {total_new} (tong cong: {len(seen_fens)})")


if __name__ == "__main__":
    main()
