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
    p.add_argument("--tron", nargs="?", type=float, const=0.4, default=None,
                   help="Tron ham thu cong voi mang NNUE (mac dinh 0.5 = 50/50). "
                        "Day la cau hinh MANH NHAT do duoc.")
    p.add_argument("--mang", default="weights/nnue_tanh.npz",
                   help="Duong dan mang NNUE dung cho --tron / --mang-thuan")
    p.add_argument("--mang-thuan", action="store_true",
                   help="Dung mang NNUE mot minh, khong tron")
    p.add_argument("--nnue", nargs="?", const="weights/eval_net.npz", default=None,
                   help="Danh gia bang mang no-ron thay vi ham thu cong "
                        "(mac dinh weights/eval_net.npz)")
    args = p.parse_args()

    from engine.search import set_evaluator
    if args.tron is not None:
        # Cau hinh MANH NHAT do duoc: tron ham thu cong voi mang NNUE.
        # Do doi khang 48 van cho thay tron 50/50 manh hon ham thu cong thuan
        # +104 Elo (khoang tin cay 95%: +7 den +221), va manh hon ca mang thuan.
        from engine.evaluate import evaluate as thu_cong
        from engine.ket_hop import tao_ham_tron
        from engine.nnue_net import MangNnue
        set_evaluator(tao_ham_tron(thu_cong, MangNnue(args.mang).evaluate, args.tron))
        print(f"Danh gia: tron {int((1-args.tron)*100)}% thu cong "
              f"+ {int(args.tron*100)}% mang ({args.mang})")
    elif args.mang_thuan:
        from engine.nnue_net import MangNnue
        set_evaluator(MangNnue(args.mang).evaluate)
        print(f"Danh gia: mang NNUE thuan ({args.mang})")
    elif args.nnue:
        from engine.nnue import NnueEvaluator
        set_evaluator(NnueEvaluator(args.nnue).evaluate)
        print(f"Danh gia: mang CNN ({args.nnue})")
    else:
        print("Danh gia: ham thu cong (vat chat + co dong + vi tri)")

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
