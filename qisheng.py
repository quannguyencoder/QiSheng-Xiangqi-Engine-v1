"""
QiSheng - engine co tuong tu viet, khong dung thu vien co ngoai.

Ban co: 10 hang (0..9) x 9 cot (0..8).
  Hang 0 = hau phuong Den (tren cung), hang 9 = hau phuong Trang (duoi cung).
  Quan chu HOA = Trang, chu THUONG = Den.
    R/r = Xe        H/h = Ma
    E/e = Tuong     A/a = Si
    K/k = Tuong soai C/c = Phao
    P/p = Tot
  O trong = '.'

Thang diem danh gia: 0..1000, tinh theo goc nhin cua Trang.
  500 = can bang.  505 = the co khoi dau (Trang di truoc, +5 diem tempo).
  1000 = Trang co nuoc chieu het ngay trong luot nay. 0 = nguoc lai cho Den.
"""

import math
from typing import List, Optional, Tuple

Board = List[List[str]]
Move = Tuple[int, int, int, int]  # (from_row, from_col, to_row, to_col)

WHITE, BLACK = "w", "b"

MIN_SCORE = 0
MAX_SCORE = 1000
NEUTRAL_SCORE = 500
TEMPO_BONUS = 5

PIECE_VALUES = {"R": 900, "C": 450, "H": 400, "A": 200, "E": 200, "P": 100, "K": 0}
SOLDIER_CROSSED_BONUS = 100
MATERIAL_SCALE = 1600.0
MOBILITY_WEIGHT = 2


# ---------------------------------------------------------------------------
# Ban co
# ---------------------------------------------------------------------------

def start_board() -> Board:
    return [
        list("rheakaehr"),
        list("........."),
        list(".c.....c."),
        list("p.p.p.p.p"),
        list("........."),
        list("........."),
        list("P.P.P.P.P"),
        list(".C.....C."),
        list("........."),
        list("RHEAKAEHR"),
    ]


def color_of(p: str) -> Optional[str]:
    if p == ".":
        return None
    return WHITE if p.isupper() else BLACK


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < 10 and 0 <= c < 9


def in_palace(r: int, c: int, side: str) -> bool:
    if not (3 <= c <= 5):
        return False
    return (0 <= r <= 2) if side == BLACK else (7 <= r <= 9)


def own_half(r: int, side: str) -> bool:
    return r >= 5 if side == WHITE else r <= 4


def print_board(board: Board) -> None:
    print("   " + " ".join(str(c) for c in range(9)))
    for r, row in enumerate(board):
        print(f"{r:2d} " + " ".join(row))


# ---------------------------------------------------------------------------
# Sinh nuoc di theo tung loai quan (pseudo-legal, chua loc chieu tuong)
# ---------------------------------------------------------------------------

def generate_pseudo_moves(board: Board, r: int, c: int) -> List[Move]:
    p = board[r][c]
    if p == ".":
        return []
    side = color_of(p)
    kind = p.upper()
    moves: List[Move] = []

    def add(tr: int, tc: int) -> None:
        if in_bounds(tr, tc):
            target = board[tr][tc]
            if target == "." or color_of(target) != side:
                moves.append((r, c, tr, tc))

    if kind == "K":
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tr, tc = r + dr, c + dc
            if in_palace(tr, tc, side):
                add(tr, tc)
    elif kind == "A":
        for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            tr, tc = r + dr, c + dc
            if in_palace(tr, tc, side):
                add(tr, tc)
    elif kind == "E":
        for dr, dc in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
            tr, tc = r + dr, c + dc
            eye_r, eye_c = r + dr // 2, c + dc // 2
            if in_bounds(tr, tc) and own_half(tr, side) and board[eye_r][eye_c] == ".":
                add(tr, tc)
    elif kind == "H":
        # (huong chan ngua, huong toi)
        deltas = [
            (1, 0, 2, 1), (1, 0, 2, -1),
            (-1, 0, -2, 1), (-1, 0, -2, -1),
            (0, 1, 1, 2), (0, 1, -1, 2),
            (0, -1, 1, -2), (0, -1, -1, -2),
        ]
        for leg_dr, leg_dc, dr, dc in deltas:
            leg_r, leg_c = r + leg_dr, c + leg_dc
            tr, tc = r + dr, c + dc
            if in_bounds(leg_r, leg_c) and board[leg_r][leg_c] == "." and in_bounds(tr, tc):
                add(tr, tc)
    elif kind == "R":
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tr, tc = r + dr, c + dc
            while in_bounds(tr, tc):
                target = board[tr][tc]
                if target == ".":
                    moves.append((r, c, tr, tc))
                else:
                    if color_of(target) != side:
                        moves.append((r, c, tr, tc))
                    break
                tr += dr
                tc += dc
    elif kind == "C":
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tr, tc = r + dr, c + dc
            screen = False
            while in_bounds(tr, tc):
                target = board[tr][tc]
                if not screen:
                    if target == ".":
                        moves.append((r, c, tr, tc))
                    else:
                        screen = True
                else:
                    if target != ".":
                        if color_of(target) != side:
                            moves.append((r, c, tr, tc))
                        break
                tr += dr
                tc += dc
    elif kind == "P":
        forward = -1 if side == WHITE else 1
        add(r + forward, c)
        crossed = (r <= 4) if side == WHITE else (r >= 5)
        if crossed:
            add(r, c + 1)
            add(r, c - 1)
    return moves


# ---------------------------------------------------------------------------
# Chieu tuong / nuoc di hop le
# ---------------------------------------------------------------------------

def find_king(board: Board, side: str) -> Optional[Tuple[int, int]]:
    """Tra ve None neu tuong soai khong con tren ban co (da bi an trong lúc duyet
    nuoc di gia hop le) - de search khong bi crash o cac the co trung gian."""
    target = "K" if side == WHITE else "k"
    for r in range(10):
        for c in range(9):
            if board[r][c] == target:
                return r, c
    return None


def kings_face_each_other(board: Board) -> bool:
    white_king = find_king(board, WHITE)
    black_king = find_king(board, BLACK)
    if white_king is None or black_king is None:
        return False
    wr, wc = white_king
    br, bc = black_king
    if wc != bc:
        return False
    step = 1 if br > wr else -1
    for r in range(wr + step, br, step):
        if board[r][wc] != ".":
            return False
    return True


def is_square_attacked(board: Board, r: int, c: int, by_side: str) -> bool:
    for rr in range(10):
        for cc in range(9):
            p = board[rr][cc]
            if p != "." and color_of(p) == by_side:
                for _, _, tr, tc in generate_pseudo_moves(board, rr, cc):
                    if (tr, tc) == (r, c):
                        return True
    return False


def in_check(board: Board, side: str) -> bool:
    king = find_king(board, side)
    if king is None:
        return True  # tuong soai da bi an -> the co nay khong hop le voi ben do
    kr, kc = king
    opp = BLACK if side == WHITE else WHITE
    return is_square_attacked(board, kr, kc, opp) or kings_face_each_other(board)


def make_move(board: Board, move: Move) -> Board:
    fr, fc, tr, tc = move
    new_board = [row[:] for row in board]
    new_board[tr][tc] = new_board[fr][fc]
    new_board[fr][fc] = "."
    return new_board


def legal_moves(board: Board, side: str) -> List[Move]:
    result = []
    for r in range(10):
        for c in range(9):
            p = board[r][c]
            if p != "." and color_of(p) == side:
                for mv in generate_pseudo_moves(board, r, c):
                    if not in_check(make_move(board, mv), side):
                        result.append(mv)
    return result


# ---------------------------------------------------------------------------
# Danh gia the co (thang 0..1000, goc nhin Trang)
# ---------------------------------------------------------------------------

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


def evaluate(board: Board, side_to_move: str) -> int:
    """Danh gia tinh (khong tim kiem). Luon nam trong [1, 999] -
    0 va 1000 duoc danh rieng cho ket qua chieu het da xac nhan boi search()."""
    raw = material_score(board) + mobility_score(board) * MOBILITY_WEIGHT
    normalized = math.tanh(raw / MATERIAL_SCALE) * (NEUTRAL_SCORE - 5)
    tempo = TEMPO_BONUS if side_to_move == WHITE else -TEMPO_BONUS
    score = NEUTRAL_SCORE + normalized + tempo
    return max(1, min(999, round(score)))


# ---------------------------------------------------------------------------
# Tim kiem minimax + alpha-beta
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    board = start_board()
    print_board(board)

    static_score = evaluate(board, WHITE)
    print(f"\nDiem tinh (khong tim kiem), Trang di truoc: {static_score}")

    score, best_move = evaluate_current_position(board, WHITE, depth=1)
    print(f"Diem sau tim kiem depth=1: {score}, nuoc di tot nhat: {best_move}")
