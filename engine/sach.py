"""
XuanWu - tra cuu SACH KHAI CUOC.

Sach do tools/build_book.py soan tu chinh du lieu huan luyen: moi lan goi
Pikafish luc thu thap deu tra ve nuoc di tot nhat, va ta da luu lai. Nen day la
nuoc di cua Pikafish depth 10, tot hon han search depth 5-6 cua ta o khai cuoc.

Luu tru: hai mang NumPy song song, mang khoa (bam Zobrist 64 bit) DA SAP XEP.
Tra cuu bang np.searchsorted - tim kiem nhi phan chay trong C, nhanh hon nhieu
so voi dict Python co hang trieu muc va ton it bo nho hon nhieu.

Va bam 64 bit van co the trung (rat hiem), nen nuoc lay tu sach LUON duoc kiem
tra tinh hop le truoc khi dung. Trung bam se cho ra mot nuoc khong hop le trong
the co hien tai va bi loai ngay.
"""

import os
from typing import Optional

import numpy as np

from engine.board import Board, Move, legal_moves

_khoa: Optional[np.ndarray] = None
_nuoc: Optional[np.ndarray] = None
_da_thu_nap = False


def nap(path: str = "weights/sach_khai_cuoc.npz") -> bool:
    """Nap sach mot lan. Tra ve True neu co sach dung duoc."""
    global _khoa, _nuoc, _da_thu_nap
    if _da_thu_nap:
        return _khoa is not None
    _da_thu_nap = True
    if not os.path.exists(path):
        return False
    z = np.load(path)
    _khoa, _nuoc = z["khoa"], z["nuoc"]
    return True


def so_muc() -> int:
    return 0 if _khoa is None else len(_khoa)


def tra_sach(board: Board, side_to_move: str, ma_bam: int) -> Optional[Move]:
    """Tra nuoc di trong sach cho the co nay, hoac None neu khong co.

    Nuoc tra ve DA duoc kiem tra hop le - vua chan va bam trung, vua chan
    truong hop sach hong.
    """
    if not nap():
        return None
    i = int(np.searchsorted(_khoa, np.uint64(ma_bam)))
    if i >= len(_khoa) or int(_khoa[i]) != ma_bam:
        return None
    ma = int(_nuoc[i])
    di, den = (ma >> 7) & 127, ma & 127
    mv = (di // 9, di % 9, den // 9, den % 9)
    return mv if mv in legal_moves(board, side_to_move) else None
