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
    Board, Move, WHITE, BLACK, legal_moves as _legal_py,
    pseudo_legal_moves, make_move, in_check as _in_check_py,
)
from engine import loi_c

# Dung phan loi viet bang C neu bien dich duoc (nhanh 29,5x cho sinh nuoc di),
# nguoc lai chay tiep bang Python thuan. Ca hai da doi chieu 3.000 truong hop
# khong lech va perft khop chuan 44/1.920/79.666.
if loi_c.co_loi_c():
    legal_moves = loi_c.nuoc_di_hop_le
    in_check = loi_c.bi_chieu
else:
    legal_moves = _legal_py
    in_check = _in_check_py
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


def _nap_zobrist_vao_c() -> bool:
    """Day bang Zobrist cua Python sang C de hai ben cho cung ma bam."""
    if not loi_c.co_loi_c():
        return False
    thu_tu = "RHEAKCPrheakcp"
    bang = []
    for p in thu_tu:
        for r in range(10):
            for c in range(9):
                bang.append(ZOBRIST[p][r][c])
    loi_c.nap_zobrist(bang, ZOBRIST_BLACK_TO_MOVE)
    return True


_BAM_BANG_C = _nap_zobrist_vao_c()


def board_hash(board: Board, side_to_move: str) -> int:
    if _BAM_BANG_C:
        return loi_c.bam(board, side_to_move)
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

# --- Killer moves va history heuristic ---------------------------------
# Hai ky thuat sap xep nuoc di, khong doi ket qua, chi doi THU TU thu.
#
# Killer: nuoc di THUONG (khong an quan) tung gay cat tia o cung do sau ply
# thuong lai gay cat tia lan nua o nhanh anh em. Giu 2 nuoc moi tang.
#
# History: dem xem tung cap (o di, o den) da gay cat tia bao nhieu lan trong
# ca lan tim kiem. Nuoc nao hay cat tia thi thu truoc.
#
# Ca hai deu chi anh huong thu tu, nen diem tra ve PHAI giong het truoc khi
# them - day cung la cach kiem chung.

_MAX_PLY = 64
_killers: List[List[Optional[Move]]] = [[None, None] for _ in range(_MAX_PLY)]
_history: Dict[Tuple[int, int, int, int], int] = {}


def reset_heuristics() -> None:
    """Xoa killer va history. Goi o dau moi lan tim kiem tu goc."""
    global _killers, _history
    _killers = [[None, None] for _ in range(_MAX_PLY)]
    _history = {}


def _ghi_cat_tia(mv: Move, board: Board, ply: int, depth: int) -> None:
    """Mot nuoc THUONG vua gay cat tia -> ghi lai de lan sau thu no som hon."""
    if board[mv[2]][mv[3]] != ".":
        return                      # nuoc an quan da duoc MVV-LVA lo, khong can
    if ply < _MAX_PLY:
        k = _killers[ply]
        if k[0] != mv:
            k[1] = k[0]
            k[0] = mv
    # Cong theo depth^2: cat tia o do sau lon dang tin hon nhieu
    _history[mv] = _history.get(mv, 0) + depth * depth


def order_moves(board: Board, moves: List[Move], tt_move: Optional[Move] = None,
                ply: int = 0) -> List[Move]:
    """Thu tu thu: nuoc tu transposition table, roi nuoc an quan theo MVV-LVA
    (Most Valuable Victim - Least Valuable Attacker), roi killer, roi cac nuoc
    thuong xep theo history, cuoi cung la phan con lai."""
    k0 = k1 = None
    if ply < _MAX_PLY:
        k0, k1 = _killers[ply]

    def key(mv: Move) -> int:
        if tt_move is not None and mv == tt_move:
            return -10 ** 9
        victim = board[mv[2]][mv[3]]
        if victim != ".":
            attacker = board[mv[0]][mv[1]]
            return -(PIECE_VALUES[victim.upper()] * 10 - PIECE_VALUES[attacker.upper()])
        if mv == k0:
            return -500
        if mv == k1:
            return -499
        return -_history.get(mv, 0) // 1000 if _history else 0
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

# --- Null-move pruning -------------------------------------------------
# Y tuong: neu ta BO LUOT cho doi thu di hai nuoc lien tiep ma the co van tot
# den muc vuot beta, thi nuoc di that su cua ta chac chan cung vuot beta -
# khong can tim nhanh nay nua. Rat manh vi no cat ca mot nhanh, khong phai chi
# sap xep lai.
#
# Ba dieu kien bat buoc, thieu mot la sai ket qua:
#   1. Khong dang bi chieu (bo luot khi bi chieu la bi an Tuong)
#   2. Con quan manh (Xe/Ma/Phao) - tranh zugzwang, the co ma MOI nuoc di deu
#      lam xau di, luc do "bo luot" tot hon di that va suy luan tren sai
#   3. Khong bo luot hai lan lien tiep
NULL_MOVE_R = 2          # bot bao nhieu tang khi bo luot
NULL_MOVE_MIN_DEPTH = 3

# --- Late move reduction ----------------------------------------------
# Sau khi sap xep, nhung nuoc di o CUOI danh sach gan nhu chac chan khong phai
# nuoc tot nhat. Tim chung nong hon truoc; neu bat ngo tot thi tim lai day du.
LMR_MIN_DEPTH = 3
LMR_SAU_NUOC_THU = 3     # ba nuoc dau luon tim day du


def _co_quan_manh(board: Board, side: str) -> bool:
    """Ben do con Xe, Ma hoac Phao khong. Dung de tranh zugzwang."""
    quan = "RHC" if side == WHITE else "rhc"
    for r in range(10):
        row = board[r]
        for c in range(9):
            if row[c] in quan:
                return True
    return False


def search(board: Board, side_to_move: str, depth: int,
           alpha: float = MIN_SCORE, beta: float = MAX_SCORE,
           tt: Optional[Dict] = None, ply: int = 0,
           cho_bo_luot: bool = True) -> Tuple[float, Optional[Move]]:
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

    if depth == 0:
        return quiescence(board, side_to_move, alpha, beta, 0, ply), None

    # Hop le luoi bieng: sinh nuoc CHUA loc, kiem tra tinh hop le cua tung nuoc
    # ngay truoc khi tim no. Nuoc nao bi alpha-beta cat thi khong ton mot lan
    # in_check nao. Dem so nuoc hop le da thuc su thu de con biet chieu bi.
    # Voi loi C, sinh nuoc HOP LE chi ton 6,9 us - re ngang sinh nuoc chua loc,
    # nen loc luon thay vi kiem tra luoi bieng tung nuoc.
    moves = legal_moves(board, side_to_move)
    if not moves:
        return _terminal_score(side_to_move, ply), None

    doi_ben = BLACK if side_to_move == WHITE else WHITE
    dang_bi_chieu = in_check(board, side_to_move)
    so_hop_le = 0

    # --- Null-move pruning ---
    if (cho_bo_luot and ply > 0 and depth >= NULL_MOVE_MIN_DEPTH
            and not dang_bi_chieu and _co_quan_manh(board, side_to_move)):
        d_null = depth - 1 - NULL_MOVE_R
        if d_null > 0:
            if side_to_move == WHITE:
                sc, _ = search(board, doi_ben, d_null, beta - 1, beta, tt,
                               ply + 1, cho_bo_luot=False)
                if sc >= beta:
                    return beta, None
            else:
                sc, _ = search(board, doi_ben, d_null, alpha, alpha + 1, tt,
                               ply + 1, cho_bo_luot=False)
                if sc <= alpha:
                    return alpha, None

    best_move = None
    if side_to_move == WHITE:
        best_score = -math.inf
        for mv in order_moves(board, moves, tt_move, ply):
            con = make_move(board, mv)
            so_hop_le += 1
            # --- Late move reduction ---
            giam = 0
            # Dem theo so nuoc HOP LE, khong theo chi so i: i con dem ca nuoc
            # khong hop le da bi bo qua, dung no se giam nham nuoc.
            if (so_hop_le > LMR_SAU_NUOC_THU and depth >= LMR_MIN_DEPTH
                    and not dang_bi_chieu and board[mv[2]][mv[3]] == "."):
                giam = 1 if so_hop_le < 7 else 2
                if giam >= depth:
                    giam = depth - 1
            if giam:
                sc, _ = search(con, BLACK, depth - 1 - giam, alpha, alpha + 1,
                               tt, ply + 1)
                if sc <= alpha:          # dung nhu du doan, khong can tim lai
                    continue
            sc, _ = search(con, BLACK, depth - 1, alpha, beta, tt, ply + 1)
            if sc > best_score:
                best_score, best_move = sc, mv
            alpha = max(alpha, best_score)
            if alpha >= beta:
                _ghi_cat_tia(mv, board, ply, depth)
                break
    else:
        best_score = math.inf
        for mv in order_moves(board, moves, tt_move, ply):
            con = make_move(board, mv)
            so_hop_le += 1
            giam = 0
            # Dem theo so nuoc HOP LE, khong theo chi so i: i con dem ca nuoc
            # khong hop le da bi bo qua, dung no se giam nham nuoc.
            if (so_hop_le > LMR_SAU_NUOC_THU and depth >= LMR_MIN_DEPTH
                    and not dang_bi_chieu and board[mv[2]][mv[3]] == "."):
                giam = 1 if so_hop_le < 7 else 2
                if giam >= depth:
                    giam = depth - 1
            if giam:
                sc, _ = search(con, WHITE, depth - 1 - giam, beta - 1, beta,
                               tt, ply + 1)
                if sc >= beta:
                    continue
            sc, _ = search(con, WHITE, depth - 1, alpha, beta, tt, ply + 1)
            if sc < best_score:
                best_score, best_move = sc, mv
            beta = min(beta, best_score)
            if alpha >= beta:
                _ghi_cat_tia(mv, board, ply, depth)
                break

    if so_hop_le == 0:               # khong con nuoc hop le nao -> thua
        return _terminal_score(side_to_move, ply), None

    if best_move is None:            # moi nuoc deu bi LMR cat -> tim lai day du
        if side_to_move == WHITE:
            best_score = -math.inf
            for mv in order_moves(board, moves, tt_move, ply):
                con = make_move(board, mv)
                sc, _ = search(con, BLACK, depth - 1, alpha_orig, beta_orig,
                               tt, ply + 1)
                if sc > best_score:
                    best_score, best_move = sc, mv
        else:
            best_score = math.inf
            for mv in order_moves(board, moves, tt_move, ply):
                con = make_move(board, mv)
                sc, _ = search(con, WHITE, depth - 1, alpha_orig, beta_orig,
                               tt, ply + 1)
                if sc < best_score:
                    best_score, best_move = sc, mv

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


NEUTRAL_TU_SACH = 505      # the co con trong sach -> coi nhu can bang


def evaluate_current_position(board: Board, side_to_move: str,
                              depth: int = 1,
                              dung_sach: bool = False) -> Tuple[int, Optional[Move]]:
    """Ham chinh: tra ve (diem cua Trang tren thang 0..1000, nuoc di tot nhat).
    depth=1 du de phat hien 'chieu het ngay trong nuoc nay' -> 1000."""
    # --- Sach khai cuoc ---
    # Nuoc trong sach la nuoc Pikafish depth 10 da chon, tot hon search depth
    # 5-6 cua ta o khai cuoc, va lay ra tuc thi nen danh duoc ca thoi gian cho
    # trung cuoc. Chi dung khi dung_sach = True de cac phep do doi khang van
    # so sanh dung phan search.
    if dung_sach:
        from engine import sach
        mv_sach = sach.tra_sach(board, side_to_move,
                                board_hash(board, side_to_move))
        if mv_sach is not None:
            return NEUTRAL_TU_SACH, mv_sach

    reset_heuristics()
    # --- Iterative deepening ---
    # Tim depth 1 truoc, roi 2, roi 3... Nghe co ve lang phi nhung thuc te
    # NHANH HON tim thang depth N: moi vong luu nuoc tot nhat vao transposition
    # table, vong sau thu nuoc do TRUOC nen alpha-beta cat som hon nhieu.
    # Ngoai ra luon co san nuoc di tot nhat cua vong truoc neu phai dung giua chung.
    tt: Dict = {}
    score, move = 0, None
    for d in range(1, depth + 1):
        score, mv = search(board, side_to_move, d, tt=tt)
        if mv is not None:
            move = mv
    return round(score), move
