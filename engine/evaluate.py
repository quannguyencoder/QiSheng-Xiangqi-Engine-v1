"""
QiSheng - danh gia tinh mot the co (khong tim kiem).

Hien dung: vat chat + co dong. Piece-square table se duoc them o giai doan 2.
Ket qua tra ve da o thang 0..1000 (xem scoring.py).
"""

from engine.board import Board, WHITE, color_of, generate_pseudo_moves
from engine.pst import pst_value
from engine.scoring import raw_to_score

PIECE_VALUES = {"R": 900, "C": 450, "H": 400, "A": 200, "E": 200, "P": 100, "K": 0}
SOLDIER_CROSSED_BONUS = 100
MOBILITY_WEIGHT = 2
PST_WEIGHT = 1


def material_score(board: Board) -> int:
    score = 0
    for r in range(10):
        for c in range(9):
            p = board[r][c]
            if p == ".":
                continue
            side = color_of(p)
            kind = p.upper()
            value = PIECE_VALUES[kind]
            if kind == "P":
                crossed = (r <= 4) if side == WHITE else (r >= 5)
                if crossed:
                    value += SOLDIER_CROSSED_BONUS
            score += value if side == WHITE else -value
    return score


def mobility_score(board: Board) -> int:
    white_moves = 0
    black_moves = 0
    for r in range(10):
        for c in range(9):
            p = board[r][c]
            if p == ".":
                continue
            n = len(generate_pseudo_moves(board, r, c))
            if color_of(p) == WHITE:
                white_moves += n
            else:
                black_moves += n
    return white_moves - black_moves


def positional_score(board: Board) -> int:
    """Tong diem vi tri (piece-square table), duong = loi cho Trang."""
    score = 0
    for r in range(10):
        for c in range(9):
            p = board[r][c]
            if p == ".":
                continue
            is_white = p.isupper()
            v = pst_value(p.upper(), r, c, is_white)
            score += v if is_white else -v
    return score


# Tinh co dong dat: no phai SINH LAI toan bo nuoc di cua ca hai ben, chiem 24%
# thoi gian tim kiem. Khi dung ham tron, mang NNUE da hoc duoc tinh co dong tu
# 16 trieu the co Pikafish cham diem, nen co the tat di ma khong mat gi.
# Do doi khang 32 van: co va khong co tinh co dong CHENH NHAU 22 Elo, khoang tin
# cay -101..+151 tuc khong phan biet duoc. Nhung do o CUNG DO SAU, cach do thiet
# thoi cho ben nhanh hon. O cung THOI GIAN, ben tat co dong tim sau hon ~0,5 tang,
# ma 2 tang dang 163 Elo (do duoc) nen nua tang dang ~40 Elo - lon hon 22 Elo co
# the mat. Vi vay mac dinh TAT.
_DUNG_CO_DONG = False


def dat_co_dong(bat: bool) -> None:
    global _DUNG_CO_DONG
    _DUNG_CO_DONG = bat


from engine import loi_c

_CO_LOI_C = loi_c.co_loi_c()


def evaluate(board: Board, side_to_move: str) -> int:
    """Danh gia tinh (khong tim kiem), tra ve diem 0..1000 goc nhin Trang."""
    if _CO_LOI_C and not _DUNG_CO_DONG:
        # Duong nhanh: vat chat + vi tri tinh trong C (doi chieu 2.000 the co
        # khong lech). Chi dung khi tat co dong vi C khong tinh co dong.
        raw = loi_c.danh_gia_tho(board)
    else:
        raw = material_score(board) + positional_score(board) * PST_WEIGHT
        if _DUNG_CO_DONG:
            raw += mobility_score(board) * MOBILITY_WEIGHT
    return raw_to_score(raw, white_to_move=(side_to_move == WHITE))

