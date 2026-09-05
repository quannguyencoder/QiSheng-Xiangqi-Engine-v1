"""
XuanWu - kiem thu engine.  Chay: python3 tests/test_engine.py

Perft (dem so the co la o do sau N) doi chieu voi gia tri chuan cua co tuong -
day la luoi an toan quan trong nhat: chi can mot loi nho trong luat di quan la
con so lech ngay.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import (
    WHITE, BLACK, start_board, legal_moves, make_move, in_check,
    generate_pseudo_moves, kings_face_each_other,
)
from engine.evaluate import evaluate
from engine.search import evaluate_current_position

PERFT_CHUAN = {1: 44, 2: 1920, 3: 79666}   # the co khoi dau

_passed = _failed = 0


def check(ten, thuc_te, mong_doi):
    global _passed, _failed
    if thuc_te == mong_doi:
        _passed += 1
        print(f"  OK   {ten}")
    else:
        _failed += 1
        print(f"  SAI  {ten}: duoc {thuc_te!r}, mong doi {mong_doi!r}")


def perft(board, side, depth):
    if depth == 0:
        return 1
    return sum(perft(make_move(board, mv), BLACK if side == WHITE else WHITE, depth - 1)
               for mv in legal_moves(board, side))


def fen_to_board(fen):
    m = {"N": "H", "B": "E"}
    place, side = fen.split(" ")[:2]
    board = []
    for row_str in place.split("/"):
        row = []
        for ch in row_str:
            if ch.isdigit():
                row.extend(["."] * int(ch))
            else:
                u = m.get(ch.upper(), ch.upper())
                row.append(u if ch.isupper() else u.lower())
        board.append(row)
    return board, (WHITE if side == "w" else BLACK)


def test_perft():
    print("perft (the co khoi dau):")
    b = start_board()
    for depth, mong_doi in PERFT_CHUAN.items():
        t = time.time()
        check(f"perft({depth})", perft(b, WHITE, depth), mong_doi)
        print(f"       ({time.time() - t:.1f}s)")


def test_luat_di_quan():
    print("luat di quan:")
    # Phao phai co dung mot quan lam ngoi moi an duoc
    b, s = fen_to_board("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w")
    check("Phao nhay qua ngoi an duoc Ma", (7, 1, 0, 1) in legal_moves(b, s), True)

    # Tuong (E) khong duoc qua song
    b2 = [["."] * 9 for _ in range(10)]
    b2[9][4], b2[0][4], b2[7][2] = "K", "k", "E"
    dich = {(r, c) for _, _, r, c in generate_pseudo_moves(b2, 7, 2)}
    check("Tuong khong qua song", all(r >= 5 for r, _ in dich), True)

    # Ma bi can chan
    b3 = [["."] * 9 for _ in range(10)]
    b3[9][4], b3[0][4], b3[5][4], b3[4][4] = "K", "k", "H", "P"
    check("Ma bi can chan", (5, 4, 3, 5) in generate_pseudo_moves(b3, 5, 4), False)

    # Tot di ngang duoc sau khi qua song
    b4 = [["."] * 9 for _ in range(10)]
    b4[9][4], b4[0][4], b4[4][4] = "K", "k", "P"
    check("Tot qua song di ngang duoc", (4, 4, 4, 5) in generate_pseudo_moves(b4, 4, 4), True)

    # Luat ky mat tuong: hai Tuong khong duoc nhin thang nhau
    b5 = [["."] * 9 for _ in range(10)]
    b5[9][4], b5[0][4] = "K", "k"
    check("Ky mat tuong bi phat hien", kings_face_each_other(b5), True)
    check("Ky mat tuong tinh la bi chieu", in_check(b5, WHITE), True)


def test_thang_diem():
    print("thang diem 0-1000:")
    check("the co khoi dau = 505", evaluate(start_board(), WHITE), 505)

    # Trang chieu het ngay trong nuoc nay -> 1000
    b = [["."] * 9 for _ in range(10)]
    b[0][4], b[9][4] = "k", "K"       # Tuong Den o (0,4), Tuong Trang o (9,4)
    b[1][3], b[1][5] = "R", "R"       # hai Xe khoa hang 1
    b[2][4] = "R"                     # Xe chieu bi trong cung
    score, _ = evaluate_current_position(b, WHITE, depth=1)
    check("chieu het trong 1 nuoc = 1000", score, 1000)


if __name__ == "__main__":
    test_perft()
    test_luat_di_quan()
    test_thang_diem()
    print(f"\n{_passed} dat, {_failed} sai")
    sys.exit(1 if _failed else 0)
