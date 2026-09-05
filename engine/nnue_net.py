"""
QiSheng - danh gia the co bang mang kieu NNUE, chay bang NumPy.

Khac engine/nnue.py (mang CNN) o cho: kien truc nay duoc thiet ke de CAP NHAT
TANG DAN. Lop dau tien la mot phep cong don cac cot trong so ung voi tung quan
dang co tren ban. Khi mot quan di tu o A sang o B, vec-to tich luy chi can:

    acc = acc - W1[(quan, A)] + W1[(quan, B)]

thay vi tinh lai tu dau. Neu co quan bi an thi tru them cot cua quan do.

Do duoc tren may nay:
    ham danh gia thu cong   89,0 us
    mang CNN (engine/nnue)  312,0 us
    mang nay, tinh tu dau    20,2 us
    mang nay, tang dan        7,8 us

Chi so dac trung PHAI khop voi luc huan luyen (tools/train_big.fen_to_uint8):
    thu tu quan la "RHEAKCP" cho Trang roi "rheakcp" cho Den,
    chi so = so_thu_tu_quan * 90 + hang * 9 + cot.
"""

import os
from typing import List, Optional, Tuple

import numpy as np

import numpy as _np

from engine.board import Board
from engine import loi_c

_CO_LOI_C = loi_c.co_loi_c()

QUAN = "RHEAKCPrheakcp"
_CHI_SO_QUAN = {p: i for i, p in enumerate(QUAN)}
SO_DAC_TRUNG = 1260


def chi_so_dac_trung(quan: str, r: int, c: int) -> int:
    """(quan, hang, cot) -> chi so dac trung, khop voi luc huan luyen."""
    return _CHI_SO_QUAN[quan] * 90 + r * 9 + c


def cac_dac_trung(board: Board) -> np.ndarray:
    """Danh sach chi so dac trung dang bat cho mot the co."""
    out = []
    for r in range(10):
        row = board[r]
        for c in range(9):
            p = row[c]
            if p != ".":
                out.append(_CHI_SO_QUAN[p] * 90 + r * 9 + c)
    return np.array(out, dtype=np.int32)


class MangNnue:
    """Mang NNUE da xuat ra .npz. Tra ve diem 0..1000 theo goc nhin Trang."""

    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Khong tim thay trong so: {path}")
        z = np.load(path)
        self.w1 = z["w1"].astype(np.float32)      # (1260, so_tich_luy)
        self.b1 = z["b1"].astype(np.float32)
        self.w2 = z["w2"].astype(np.float32)      # (so_tich_luy+1, so_an)
        self.b2 = z["b2"].astype(np.float32)
        self.w3 = z["w3"].astype(np.float32)      # (so_an,)
        self.b3 = float(z["b3"])
        self.so_tich_luy = self.w1.shape[1]

    # -- phan tinh tu tich luy ra diem ------------------------------------

    def _tu_tich_luy(self, acc: np.ndarray, trang_di: bool) -> int:
        a = np.clip(acc, 0.0, 1.0)
        vao = np.empty(self.so_tich_luy + 1, dtype=np.float32)
        vao[:self.so_tich_luy] = a
        vao[self.so_tich_luy] = 1.0 if trang_di else 0.0
        h = np.clip(vao @ self.w2 + self.b2, 0.0, 1.0)
        out = float(h @ self.w3) + self.b3
        prob = 1.0 / (1.0 + np.exp(-out))
        # Giu trong [1, 999]: 0 va 1000 danh rieng cho chieu het da xac nhan
        return max(1, min(999, int(round(prob * 1000))))

    # -- duong tinh lai tu dau (dung ngay duoc, khong can sua search) ------

    def tich_luy(self, board: Board) -> np.ndarray:
        if _CO_LOI_C:
            # Liet ke dac trung trong C: vong lap quet 90 o tung chiem 17%
            # thoi gian tim kiem khi viet bang Python.
            buf, n = loi_c.dac_trung(board)
            idx = _np.ctypeslib.as_array(buf)[:n]
            return self.w1[idx].sum(axis=0) + self.b1
        return self.w1[cac_dac_trung(board)].sum(axis=0) + self.b1

    def evaluate(self, board: Board, side_to_move: str) -> int:
        """Giao dien giong engine/evaluate.py de cam thang vao set_evaluator()."""
        return self._tu_tich_luy(self.tich_luy(board), side_to_move == "w")

    # -- duong cap nhat tang dan (nhanh hon ~2,6 lan, danh cho B2) ---------

    def cap_nhat(self, acc: np.ndarray, bo: List[int], them: List[int]) -> np.ndarray:
        """Tra ve tich luy moi sau khi tat cac dac trung 'bo' va bat 'them'."""
        moi = acc.copy()
        for i in bo:
            moi -= self.w1[i]
        for i in them:
            moi += self.w1[i]
        return moi

    @staticmethod
    def thay_doi(board: Board, mv: Tuple[int, int, int, int]) -> Tuple[List[int], List[int]]:
        """Nuoc di -> (dac trung phai tat, dac trung phai bat).

        Goi TRUOC khi thuc hien nuoc di, vi can biet quan nao dang dung o dau.
        """
        r0, c0, r1, c1 = mv
        quan = board[r0][c0]
        bo = [_CHI_SO_QUAN[quan] * 90 + r0 * 9 + c0]
        bi_an = board[r1][c1]
        if bi_an != ".":
            bo.append(_CHI_SO_QUAN[bi_an] * 90 + r1 * 9 + c1)
        them = [_CHI_SO_QUAN[quan] * 90 + r1 * 9 + c1]
        return bo, them

    def diem_tu_tich_luy(self, acc: np.ndarray, side_to_move: str) -> int:
        return self._tu_tich_luy(acc, side_to_move == "w")


_da_nap: Optional[MangNnue] = None


def load(path: str = "weights/nnue_net.npz") -> MangNnue:
    """Nap mot lan roi dung lai (tranh doc file moi lan search)."""
    global _da_nap
    if _da_nap is None:
        _da_nap = MangNnue(path)
    return _da_nap
