"""
QiSheng - tim kiem nuoc di.

Gom 4 ky thuat:
  1. Alpha-beta tren khung minimax (Trang toi da hoa, Den toi thieu hoa).
  2. Move ordering MVV-LVA: thu nuoc an quan gia tri cao bang quan re truoc,
     giup alpha-beta cat nhanh hon rat nhieu.
  3. Transposition table + bam Zobrist: cung mot the co den tu nhieu thu tu
     nuoc di khac nhau chi phai tinh mot lan.
  4. Quiescence search: o do sau 0 khong dung dot ngot giua pha doi quan
     (hieu ung chan troi) ma danh not cac nuoc an quan cho toi khi the co "yen".

Diem chieu het duoc tru dan theo do sau (1000, 999, 998...) de engine chon
duong chieu het NGAN nhat; chieu het ngay trong nuoc nay van dung 1000.
"""

import math
import random
from typing import Dict, List, Optional, Tuple

from engine.board import (
    Board, Move, WHITE, BLACK, legal_moves, make_move, in_check,
)
from engine.evaluate import PIECE_VALUES
from engine.evaluate import evaluate as handcrafted_evaluate
from engine.scoring import MIN_SCORE, MAX_SCORE

# Ham danh gia dang dung. Mac dinh la danh gia thu cong (Python thuan, khong
# phu thuoc gi). Co the thay bang mang no-ron qua set_evaluator() - xem
# engine/nnue.py va co --nnue cua main.py.
_evaluator = handcrafted_evaluate


def set_evaluator(fn) -> None:
    """Thay ham danh gia tinh ma search dung (nhan board, side -> diem 0..1000)."""
    global _evaluator
    _evaluator = fn


def evaluate(board: Board, side_to_move: str) -> int:
    return _evaluator(board, side_to_move)

# --------------------------------------------------------------------------
# Bam Zobrist
# --------------------------------------------------------------------------

_rng = random.Random(20260903)          # co dinh de ket qua lap lai duoc
_PIECES = "RHEAKCPrheakcp"
ZOBRIST = {p: [[_rng.getrandbits(64) for _ in range(9)] for _ in range(10)]
           for p in _PIECES}
ZOBRIST_BLACK_TO_MOVE = _rng.getrandbits(64)

EXACT, LOWER_BOUND, UPPER_BOUND = 0, 1, 2
MAX_TT_ENTRIES = 400_000
QUIESCENCE_MAX_PLY = 4
_MATE_MARGIN = 50        # khong luu vao TT cac diem sat bien (diem chieu het)


def board_hash(board: Board, side_to_move: str) -> int:
    h = 0
    for r in range(10):
        row = board[r]
        for c in range(9):
            p = row[c]
            if p != ".":
                h ^= ZOBRIST[p][r][c]
    if side_to_move == BLACK:
        h ^= ZOBRIST_BLACK_TO_MOVE
    return h


# --------------------------------------------------------------------------
# Sap xep nuoc di (MVV-LVA)
# --------------------------------------------------------------------------

def order_moves(board: Board, moves: List[Move], tt_move: Optional[Move] = None) -> List[Move]:
    """Nuoc tu transposition table truoc, roi den cac nuoc an quan theo MVV-LVA
    (Most Valuable Victim - Least Valuable Attacker), cuoi cung la nuoc thuong."""
    def key(mv: Move) -> int:
        if tt_move is not None and mv == tt_move:
            return -10 ** 9
        victim = board[mv[2]][mv[3]]
        if victim == ".":
            return 0
        attacker = board[mv[0]][mv[1]]
        return -(PIECE_VALUES[victim.upper()] * 10 - PIECE_VALUES[attacker.upper()])
    return sorted(moves, key=key)


def _terminal_score(side_to_move: str, ply: int) -> int:
    """Ben den luot ma het nuoc di = thua (dung luat co tuong, khong hoa).
    Tru dan theo do sau de uu tien duong chieu het ngan nhat."""
    penalty = max(0, ply - 1)
    return (MIN_SCORE + penalty) if side_to_move == WHITE else (MAX_SCORE - penalty)


# --------------------------------------------------------------------------
# Quiescence search
# --------------------------------------------------------------------------

def quiescence(board: Board, side: str, alpha: float, beta: float,
               ply: int, root_ply: int) -> float:
    checked = in_check(board, side)
    stand_pat = evaluate(board, side)

    if ply >= QUIESCENCE_MAX_PLY and not checked:
        return stand_pat

    moves = legal_moves(board, side)
    if not moves:
        return _terminal_score(side, root_ply + ply)

    if not checked:
        # The co "yen": chi xet tiep nuoc an quan. Neu khong con nuoc an nao
        # thi the co da du yen de tin vao danh gia tinh.
        moves = [m for m in moves if board[m[2]][m[3]] != "."]
        if not moves:
            return stand_pat

    if side == WHITE:
        best = -math.inf if checked else stand_pat
        if not checked:
            if stand_pat >= beta:
                return stand_pat
            alpha = max(alpha, stand_pat)
        for mv in order_moves(board, moves):
            sc = quiescence(make_move(board, mv), BLACK, alpha, beta, ply + 1, root_ply)
            if sc > best:
                best = sc
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best

    best = math.inf if checked else stand_pat
    if not checked:
        if stand_pat <= alpha:
            return stand_pat
        beta = min(beta, stand_pat)
    for mv in order_moves(board, moves):
        sc = quiescence(make_move(board, mv), WHITE, alpha, beta, ply + 1, root_ply)
        if sc < best:
            best = sc
        beta = min(beta, best)
        if alpha >= beta:
            break
    return best


# --------------------------------------------------------------------------
# Tim kiem chinh
# --------------------------------------------------------------------------

def search(board: Board, side_to_move: str, depth: int,
           alpha: float = MIN_SCORE, beta: float = MAX_SCORE,
           tt: Optional[Dict] = None, ply: int = 0) -> Tuple[float, Optional[Move]]:
    if tt is None:
        tt = {}
    alpha_orig, beta_orig = alpha, beta

    key = board_hash(board, side_to_move)
    tt_move = None
    entry = tt.get(key)
    if entry is not None:
        e_depth, e_score, e_flag, e_move = entry
        tt_move = e_move
        if e_depth >= depth:
            if e_flag == EXACT:
                return e_score, e_move
            if e_flag == LOWER_BOUND:
                alpha = max(alpha, e_score)
            else:
                beta = min(beta, e_score)
            if alpha >= beta:
                return e_score, e_move

    moves = legal_moves(board, side_to_move)
    if not moves:
        return _terminal_score(side_to_move, ply), None

    if depth == 0:
        return quiescence(board, side_to_move, alpha, beta, 0, ply), None

    best_move = None
    if side_to_move == WHITE:
        best_score = -math.inf
        for mv in order_moves(board, moves, tt_move):
            sc, _ = search(make_move(board, mv), BLACK, depth - 1, alpha, beta, tt, ply + 1)
            if sc > best_score:
                best_score, best_move = sc, mv
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
    else:
        best_score = math.inf
        for mv in order_moves(board, moves, tt_move):
            sc, _ = search(make_move(board, mv), WHITE, depth - 1, alpha, beta, tt, ply + 1)
            if sc < best_score:
                best_score, best_move = sc, mv
            beta = min(beta, best_score)
            if alpha >= beta:
                break

    # Diem chieu het phu thuoc do sau tuong doi nen khong an toan de tai su dung
    # o mot nhanh khac -> chi luu cac diem binh thuong.
    if (MIN_SCORE + _MATE_MARGIN) < best_score < (MAX_SCORE - _MATE_MARGIN):
        if len(tt) < MAX_TT_ENTRIES:
            if best_score <= alpha_orig:
                flag = UPPER_BOUND
            elif best_score >= beta_orig:
                flag = LOWER_BOUND
            else:
                flag = EXACT
            tt[key] = (depth, best_score, flag, best_move)

    return best_score, best_move


def evaluate_current_position(board: Board, side_to_move: str,
                              depth: int = 1) -> Tuple[int, Optional[Move]]:
    """Ham chinh: tra ve (diem cua Trang tren thang 0..1000, nuoc di tot nhat).
    depth=1 du de phat hien 'chieu het ngay trong nuoc nay' -> 1000."""
    score, move = search(board, side_to_move, depth, tt={})
    return round(score), move
