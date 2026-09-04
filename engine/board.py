"""
QiSheng - bieu dien ban co va luat di quan (khong dung thu vien co ngoai).

Ban co: 10 hang (0..9) x 9 cot (0..8).
  Hang 0 = hau phuong Den (tren cung), hang 9 = hau phuong Trang (duoi cung).
  Quan chu HOA = Trang, chu THUONG = Den.
    R/r = Xe        H/h = Ma
    E/e = Tuong     A/a = Si
    K/k = Tuong soai C/c = Phao
    P/p = Tot
  O trong = '.'
"""

from typing import List, Optional, Tuple

Board = List[List[str]]
Move = Tuple[int, int, int, int]  # (from_row, from_col, to_row, to_col)

WHITE, BLACK = "w", "b"

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

# Tuong soai luon o trong cung: chi 9 o can duyet thay vi ca 90 o cua ban co.
_PALACE_SQUARES = {
    WHITE: [(r, c) for r in (7, 8, 9) for c in (3, 4, 5)],
    BLACK: [(r, c) for r in (0, 1, 2) for c in (3, 4, 5)],
}


def find_king(board: Board, side: str) -> Optional[Tuple[int, int]]:
    """Tra ve None neu tuong soai khong con tren ban co (da bi an trong lúc duyet
    nuoc di gia hop le) - de search khong bi crash o cac the co trung gian."""
    target = "K" if side == WHITE else "k"
    for r, c in _PALACE_SQUARES[side]:
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
    """O (r, c) co bi ben `by_side` tan cong khong?

    Do tia NGUOC tu chinh o can kiem tra thay vi quet ca 90 o roi sinh toan bo
    nuoc di cua doi phuong. Cung ket qua nhung it viec hon rat nhieu - day la
    ham duoc goi nhieu nhat trong toan bo engine (moi nuoc di hop le deu goi).
    """
    up = by_side == WHITE          # quan cua by_side viet HOA hay thuong

    # O da co quan cua chinh ben tan cong thi khong the "an" vao do
    here = board[r][c]
    if here != "." and here.isupper() == up:
        return False

    # Bang tra: ky tu quan -> co phai quan cua by_side khong (thay cho ham goi
    # 9,9 trieu lan trong mot lan tim kiem depth 3).
    mine = "RHEAKCP" if up else "rheakcp"
    R, H, E, A, K, C, P = mine[0], mine[1], mine[2], mine[3], mine[4], mine[5], mine[6]

    # --- Xe va Phao: di theo 4 tia thang ---
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        tr, tc = r + dr, c + dc
        while 0 <= tr < 10 and 0 <= tc < 9 and board[tr][tc] == ".":
            tr += dr
            tc += dc
        if not (0 <= tr < 10 and 0 <= tc < 9):
            continue
        first = board[tr][tc]
        # Xe: toi duoc o trong lan o co quan (an)
        if first == R:
            return True
        # Tuong soai chi di duoc trong cung cua no
        if (first == K and abs(tr - r) + abs(tc - c) == 1
                and in_palace(r, c, by_side)):
            return True
        # Phao KHONG co ngoi: chi di duoc vao o TRONG
        if first == C and here == ".":
            return True
        # Di tiep qua quan do (lam ngoi) tim Phao phia sau.
        # Phao co ngoi thi chi AN duoc, tuc o dich phai co quan.
        if here != ".":
            tr += dr
            tc += dc
            while 0 <= tr < 10 and 0 <= tc < 9 and board[tr][tc] == ".":
                tr += dr
                tc += dc
            if 0 <= tr < 10 and 0 <= tc < 9 and board[tr][tc] == C:
                return True

    # --- Ma: 8 o co the co Ma dung, kem kiem tra chan chan ---
    for dr, dc in ((2, 1), (2, -1), (-2, 1), (-2, -1),
                   (1, 2), (1, -2), (-1, 2), (-1, -2)):
        hr, hc = r + dr, c + dc          # vi tri Ma neu no an duoc o nay
        if not (0 <= hr < 10 and 0 <= hc < 9) or board[hr][hc] != H:
            continue
        # Chan Ma nam ke Ma, ve phia buoc dai cua chu L
        if abs(dr) == 2:
            leg_r, leg_c = hr - (1 if dr > 0 else -1), hc
        else:
            leg_r, leg_c = hr, hc - (1 if dc > 0 else -1)
        if board[leg_r][leg_c] == ".":
            return True

    # --- Tot: an duoc o phia truoc va (sau khi qua song) hai ben ---
    # Tot cua by_side tien ve huong nao: Trang tien len (row giam), Den nguoc lai
    back = 1 if up else -1           # lui lai theo huong tien cua ho = tim o xuat phat
    pr, pc = r + back, c
    if 0 <= pr < 10 and 0 <= pc < 9 and board[pr][pc] == P:
        return True
    for dc in (1, -1):
        pr, pc = r, c + dc
        if 0 <= pr < 10 and 0 <= pc < 9 and board[pr][pc] == P:
            crossed = (pr <= 4) if up else (pr >= 5)
            if crossed:              # chi Tot da qua song moi di ngang duoc
                return True

    # --- Si: cheo mot buoc trong cung ---
    for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        ar, ac = r + dr, c + dc
        if 0 <= ar < 10 and 0 <= ac < 9 and board[ar][ac] == A \
                and in_palace(ar, ac, by_side) and in_palace(r, c, by_side):
            return True

    # --- Tuong (voi): cheo hai buoc, khong bi can mat, KHONG qua song ---
    if own_half(r, by_side):
        for dr, dc in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
            er, ec = r + dr, c + dc
            if 0 <= er < 10 and 0 <= ec < 9 and board[er][ec] == E \
                    and board[er - dr // 2][ec - dc // 2] == ".":
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

