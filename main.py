"""
QiSheng - CLI phan tich mot the co tuong.

  python3 main.py                          # the co khoi dau
  python3 main.py "<FEN>" --depth 2        # mot the co bat ky
"""

import argparse

from engine.board import WHITE, BLACK, start_board, print_board
from engine.evaluate import evaluate
from engine.search import evaluate_current_position


def fen_to_board(fen: str):
    """FEN cua co tuong -> (Board, ben di). Chu FEN chuan: N=Ma, B=Tuong."""
    fen_to_internal = {"N": "H", "B": "E"}
    placement, side = fen.split(" ")[:2]
    board = []
    for row_str in placement.split("/"):
        row = []
        for ch in row_str:
            if ch.isdigit():
                row.extend(["."] * int(ch))
            else:
                mapped = fen_to_internal.get(ch.upper(), ch.upper())
                row.append(mapped if ch.isupper() else mapped.lower())
        board.append(row)
    return board, (WHITE if side == "w" else BLACK)


def main() -> None:
    p = argparse.ArgumentParser(description="Phan tich the co tuong")
    p.add_argument("fen", nargs="?", help="FEN cua the co (bo trong = the co khoi dau)")
    p.add_argument("--depth", type=int, default=1, help="Do sau tim kiem")
    args = p.parse_args()

    if args.fen:
        board, side = fen_to_board(args.fen)
    else:
        board, side = start_board(), WHITE

    print_board(board)
    print(f"\nBen di: {'Trang' if side == WHITE else 'Den'}")
    print(f"Diem tinh (khong tim kiem): {evaluate(board, side)}")
    score, best = evaluate_current_position(board, side, depth=args.depth)
    print(f"Diem sau tim kiem depth={args.depth}: {score} | nuoc di tot nhat: {best}")


if __name__ == "__main__":
    main()
