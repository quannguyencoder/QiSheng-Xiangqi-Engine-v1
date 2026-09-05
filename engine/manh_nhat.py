"""
XuanWu - cau hinh MANH NHAT: tim kiem va danh gia deu chay trong C.

Gop tat ca lai mot cho de nguoi dung khong phai tu nap mang, tu tinh hieu chinh,
tu khoi tao bang chuyen vi. Goi tim_nuoc_di() la xong.

Do duoc tren may nay:
    depth  8 : 0,686 giay
    depth 10 : 1,895 giay
    depth 12 : 10,4 giay

Neu khong co thu vien C, module tu quay ve duong Python (cham hon nhieu nhung
van dung) - xem san_sang().
"""

import os
from typing import Optional, Tuple

from engine.board import Board, Move, WHITE
from engine import loi_c

MANG_MAC_DINH = "weights/nnue_tanh.npz"
TRONG_SO_MAC_DINH = 0.4        # do doi khang: 0,25-0,40 ngang nhau, tot hon 0,50

_da_chuan_bi = False
_dung_c = False


def chuan_bi(duong_mang: str = MANG_MAC_DINH,
             trong_so: float = TRONG_SO_MAC_DINH) -> bool:
    """Nap mang vao C va tinh hieu chinh. Tra ve True neu dung duoc duong C."""
    global _da_chuan_bi, _dung_c
    if _da_chuan_bi:
        return _dung_c
    _da_chuan_bi = True
    if not loi_c.co_loi_c() or not os.path.exists(duong_mang):
        return False
    from engine.board import start_board
    from engine.evaluate import evaluate as thu_cong
    from engine.nnue_net import MangNnue

    net = MangNnue(duong_mang)
    if not loi_c.nap_mang(net.w1, net.b1, net.w2, net.b2, net.w3, net.b3):
        return False
    # Hieu chinh de the co khoi dau dung 505 diem - moc chuan cua thang diem
    b0 = start_board()
    tho = (1.0 - trong_so) * thu_cong(b0, "w") + trong_so * net.evaluate(b0, "w")
    loi_c.tim_kiem_khoi_tao(trong_so, 505.0 - tho)
    _dung_c = True
    return True


def san_sang() -> bool:
    return chuan_bi()


def tim_nuoc_di(board: Board, side_to_move: str, depth: int = 8,
                dung_sach: bool = True) -> Tuple[int, Optional[Move], int]:
    """Tra ve (diem 0..1000 goc nhin Trang, nuoc di tot nhat, so nut da xet)."""
    if dung_sach:
        from engine import sach
        from engine.search import board_hash
        mv = sach.tra_sach(board, side_to_move, board_hash(board, side_to_move))
        if mv is not None:
            return 505, mv, 0          # con trong sach -> coi nhu can bang

    if chuan_bi():
        return loi_c.tim_kiem(board, side_to_move, depth)

    # Duong du phong: Python thuan
    from engine.ket_hop import tao_ham_tron, tao_ham_tron_c
    from engine.search import evaluate_current_position, set_evaluator
    ham = tao_ham_tron_c(MANG_MAC_DINH, TRONG_SO_MAC_DINH)
    if ham is None:
        from engine.evaluate import evaluate as thu_cong
        from engine.nnue_net import MangNnue
        ham = tao_ham_tron(thu_cong, MangNnue(MANG_MAC_DINH).evaluate,
                           TRONG_SO_MAC_DINH)
    set_evaluator(ham)
    diem, mv = evaluate_current_position(board, side_to_move, depth=depth)
    return diem, mv, 0
