"""
QiSheng - tim kiem nuoc di (minimax + alpha-beta).

Giai doan 2 se bo sung: quiescence search, transposition table, move ordering.
"""

import math
from typing import Optional, Tuple

from engine.board import Board, Move, WHITE, BLACK, legal_moves, make_move
from engine.evaluate import evaluate
from engine.scoring import MIN_SCORE, MAX_SCORE


def search(board: Board, side_to_move: str, depth: int,
           alpha: float = MIN_SCORE, beta: float = MAX_SCORE) -> Tuple[float, Optional[Move]]:
    moves = legal_moves(board, side_to_move)
    if not moves:
        # Het nuoc di (bi chieu het hoac khong con nuoc nao hop le) = thua,
        # theo dung luat co tuong (khac co vua quoc te, khong tinh la hoa).
        return (MIN_SCORE, None) if side_to_move == WHITE else (MAX_SCORE, None)

    if depth == 0:
        return evaluate(board, side_to_move), None

    best_move = None
    if side_to_move == WHITE:
        best_score = -math.inf
        for mv in moves:
            score, _ = search(make_move(board, mv), BLACK, depth - 1, alpha, beta)
            if score > best_score:
                best_score, best_move = score, mv
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
    else:
        best_score = math.inf
        for mv in moves:
            score, _ = search(make_move(board, mv), WHITE, depth - 1, alpha, beta)
            if score < best_score:
                best_score, best_move = score, mv
            beta = min(beta, best_score)
            if alpha >= beta:
                break
    return best_score, best_move


def evaluate_current_position(board: Board, side_to_move: str, depth: int = 1) -> Tuple[int, Optional[Move]]:
    """Ham chinh: tra ve (diem cua Trang tren thang 0..1000, nuoc di tot nhat tim duoc).
    depth=1 la du de phat hien 'Trang chieu het duoc ngay trong nuoc nay' -> 1000."""
    score, move = search(board, side_to_move, depth)
    return round(score), move

