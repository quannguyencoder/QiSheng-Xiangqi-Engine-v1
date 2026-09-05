"""
XuanWu - danh gia the co bang mang no-ron, chay bang NumPy.

Vi sao khong dung thang PyTorch trong search: search goi ham danh gia o hang
nghin nut moi lan tim kiem. Moi lan goi PyTorch keo theo chi phi khoi tao
tensor rat lon so voi mot phep nhan ma tran nho. NumPy chay truc tiep tren
trong so da xuat san (.npz) nhanh hon nhieu va khong keo theo PyTorch luc choi.

Mang: 3 lop tich chap (15->32->64->64, kernel 3x3, padding 1) roi 2 lop day
(5760->128->1), dau ra qua sigmoid ra thang 0..1000.

Trong so duoc xuat bang tools/export_nnue.py tu file .pt sau khi huan luyen.
"""

import os
from typing import Optional

import numpy as np

from engine.board import Board

PIECE_ORDER = "RHEAKCP"          # Xe, Ma, Tuong, Si, Tuong soai, Phao, Tot
_INTERNAL_INDEX = {p: i for i, p in enumerate(PIECE_ORDER)}


def board_to_planes(board: Board, white_to_move: bool) -> np.ndarray:
    """Ban co -> 15 mat phang 10x9 (7 loai quan x 2 mau + 1 mat phang ben di)."""
    planes = np.zeros((15, 10, 9), dtype=np.float32)
    for r in range(10):
        row = board[r]
        for c in range(9):
            p = row[c]
            if p == ".":
                continue
            idx = _INTERNAL_INDEX[p.upper()]
            planes[idx if p.isupper() else 7 + idx, r, c] = 1.0
    if white_to_move:
        planes[14, :, :] = 1.0
    return planes


def _conv3x3(x: np.ndarray, w: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Tich chap 3x3 padding 1, cai dat bang im2col + mot phep nhan ma tran."""
    cin, h, wd = x.shape
    cout = w.shape[0]
    padded = np.zeros((cin, h + 2, wd + 2), dtype=np.float32)
    padded[:, 1:-1, 1:-1] = x

    # im2col: moi cot la mot cua so 3x3 tren tat ca kenh dau vao
    cols = np.empty((cin * 9, h * wd), dtype=np.float32)
    k = 0
    for dy in range(3):
        for dx in range(3):
            patch = padded[:, dy:dy + h, dx:dx + wd]      # (cin, h, wd)
            cols[k * cin:(k + 1) * cin, :] = patch.reshape(cin, -1)
            k += 1

    # sap xep lai trong so cho khop thu tu cua cols
    w_re = np.empty((cout, cin * 9), dtype=np.float32)
    k = 0
    for dy in range(3):
        for dx in range(3):
            w_re[:, k * cin:(k + 1) * cin] = w[:, :, dy, dx]
            k += 1

    return (w_re @ cols + b[:, None]).reshape(cout, h, wd)


class NnueEvaluator:
    """Danh gia bang mang no-ron da xuat ra .npz. Tra ve diem 0..1000."""

    def __init__(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Khong tim thay trong so: {path}")
        z = np.load(path)
        self.c0w, self.c0b = z["c0w"].astype(np.float32), z["c0b"].astype(np.float32)
        self.c1w, self.c1b = z["c1w"].astype(np.float32), z["c1b"].astype(np.float32)
        self.c2w, self.c2b = z["c2w"].astype(np.float32), z["c2b"].astype(np.float32)
        self.f0w, self.f0b = z["f0w"].astype(np.float32), z["f0b"].astype(np.float32)
        self.f1w, self.f1b = z["f1w"].astype(np.float32), z["f1b"].astype(np.float32)

    def evaluate(self, board: Board, side_to_move: str) -> int:
        x = board_to_planes(board, white_to_move=(side_to_move == "w"))
        x = np.maximum(_conv3x3(x, self.c0w, self.c0b), 0.0)
        x = np.maximum(_conv3x3(x, self.c1w, self.c1b), 0.0)
        x = np.maximum(_conv3x3(x, self.c2w, self.c2b), 0.0)
        v = x.reshape(-1)
        v = np.maximum(self.f0w @ v + self.f0b, 0.0)
        out = float(self.f1w @ v + self.f1b)
        prob = 1.0 / (1.0 + np.exp(-out))
        # Giu trong [1, 999]: 0 va 1000 danh rieng cho chieu het da xac nhan
        return max(1, min(999, int(round(prob * 1000))))


_cached: Optional[NnueEvaluator] = None


def load(path: str = "weights/eval_net.npz") -> NnueEvaluator:
    """Nap mot lan roi dung lai (tranh doc file moi lan search)."""
    global _cached
    if _cached is None:
        _cached = NnueEvaluator(path)
    return _cached
