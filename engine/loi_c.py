"""
QiSheng - cau noi toi phan loi viet bang C (csrc/qisheng.c).

Vi sao co file nay: sinh nuoc di va phat hien chieu chiem 55% thoi gian tim
kiem va deu la vong lap Python quet tung o. Viet lai bang C rieng phan do.
Day KHONG phai dung thu vien co ngoai - toan bo luat co tuong trong qisheng.c
la code cua chinh du an, va duoc kiem chung bang perft doi chieu voi ban Python.

Diem thiet ke quan trong: goi C MOT lan cho ca nut (tra ve toan bo nuoc di hop
le) chu khong goi tung quan mot. Moi lan goi qua ctypes ton ~1-2 us; neu goi 16
lan moi nut thi chi phi goi se nuot het phan loi.

Neu khong bien dich duoc thu vien, module tu bao co_loi_c() = False va engine
chay tiep bang Python thuan.
"""

import ctypes
import os
from typing import List, Optional

from engine.board import Board, Move, WHITE

_thu_vien: Optional[ctypes.CDLL] = None
_da_thu = False
_dem = (ctypes.c_int * 256)()

# Bang tra san: ma nuoc di 16 bit -> bo bon (hang, cot, hang, cot).
# Giai ma bang phep chia trong vong lap Python la mot trong nhung cho ton nhat
# cua cau noi, ma chi co 90x90 kha nang nen tra bang la xong.
_GIAI_MA = {}
for _f in range(90):
    for _t in range(90):
        _GIAI_MA[(_f << 8) | _t] = (_f // 9, _f % 9, _t // 9, _t % 9)


def _nap() -> Optional[ctypes.CDLL]:
    global _thu_vien, _da_thu
    if _da_thu:
        return _thu_vien
    _da_thu = True
    duong = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libqisheng.so")
    if not os.path.exists(duong):
        return None
    try:
        lib = ctypes.CDLL(duong)
    except OSError:
        return None
    lib.qs_gen_legal.restype = ctypes.c_int
    lib.qs_gen_legal.argtypes = [ctypes.c_char_p, ctypes.c_int,
                                 ctypes.POINTER(ctypes.c_int)]
    lib.qs_bi_chieu.restype = ctypes.c_int
    lib.qs_bi_chieu.argtypes = [ctypes.c_char_p, ctypes.c_int]
    F = ctypes.POINTER(ctypes.c_float)
    lib.qs_nnue_nap.restype = ctypes.c_int
    lib.qs_nnue_nap.argtypes = [F, F, F, F, F, ctypes.c_float,
                                ctypes.c_int, ctypes.c_int]
    lib.qs_nnue_danh_gia.restype = ctypes.c_int
    lib.qs_nnue_danh_gia.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.qs_danh_gia_tron.restype = ctypes.c_int
    lib.qs_danh_gia_tron.argtypes = [ctypes.c_char_p, ctypes.c_int,
                                     ctypes.c_double, ctypes.c_double]
    lib.qs_dac_trung.restype = ctypes.c_int
    lib.qs_dac_trung.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
    lib.qs_bam.restype = ctypes.c_ulonglong
    lib.qs_bam.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.qs_dat_zobrist.argtypes = [ctypes.POINTER(ctypes.c_ulonglong),
                                   ctypes.c_ulonglong]
    lib.qs_danh_gia_tho.restype = ctypes.c_int
    lib.qs_danh_gia_tho.argtypes = [ctypes.c_char_p]
    lib.qs_perft.restype = ctypes.c_longlong
    lib.qs_perft.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    _thu_vien = lib
    return lib


def co_loi_c() -> bool:
    return _nap() is not None


def _sang_c(board: Board) -> bytes:
    # Goi 738.507 lan o depth 6 nen tung vi giay deu dang ke: dung map thay
    # bieu thuc sinh, va mot lan encode thay vi 10 lan.
    return "".join(map("".join, board)).encode("ascii")


def nuoc_di_hop_le(board: Board, side: str) -> List[Move]:
    """Toan bo nuoc di hop le, tinh trong C bang MOT lan goi."""
    lib = _nap()
    b = _sang_c(board)
    n = lib.qs_gen_legal(b, 1 if side == WHITE else 0, _dem)
    giai = _GIAI_MA
    return [giai[_dem[i]] for i in range(n)]


def bi_chieu(board: Board, side: str) -> bool:
    lib = _nap()
    return bool(lib.qs_bi_chieu(_sang_c(board), 1 if side == WHITE else 0))


def perft(board: Board, side: str, depth: int) -> int:
    lib = _nap()
    return int(lib.qs_perft(_sang_c(board), 1 if side == WHITE else 0, depth))


def danh_gia_tho(board: Board) -> int:
    """Vat chat + vi tri, tinh trong C. Doi chieu 2.000 the co khong lech."""
    return _nap().qs_danh_gia_tho(_sang_c(board))


_dt = (ctypes.c_int * 90)()
_da_nap_zobrist = False


def nap_zobrist(bang, den) -> None:
    """Nap bang Zobrist cua Python vao C de hai ben cho cung ma bam."""
    global _da_nap_zobrist
    if _da_nap_zobrist:
        return
    mang = (ctypes.c_ulonglong * (14 * 90))(*bang)
    _nap().qs_dat_zobrist(mang, ctypes.c_ulonglong(den))
    _da_nap_zobrist = True


def dac_trung(board: Board):
    """Chi so dac trung NNUE cua the co, liet ke trong C."""
    n = _nap().qs_dac_trung(_sang_c(board), _dt)
    return _dt, n


def bam(board: Board, side: str) -> int:
    return int(_nap().qs_bam(_sang_c(board), 1 if side == WHITE else 0))


_da_nap_mang = False


def nap_mang(w1, b1, w2, b2, w3, b3) -> bool:
    """Nap trong so mang NNUE vao C. Cac mang phai lien tuc va la float32."""
    import numpy as np
    global _da_nap_mang
    lib = _nap()
    if lib is None:
        return False
    F = ctypes.POINTER(ctypes.c_float)
    def p(a):
        return np.ascontiguousarray(a, dtype=np.float32).ctypes.data_as(F)
    # Giu tham chieu de NumPy khong thu hoi bo nho truoc khi C chep xong
    giu = [np.ascontiguousarray(x, dtype=np.float32) for x in (w1, b1, w2, b2, w3)]
    ok = lib.qs_nnue_nap(giu[0].ctypes.data_as(F), giu[1].ctypes.data_as(F),
                         giu[2].ctypes.data_as(F), giu[3].ctypes.data_as(F),
                         giu[4].ctypes.data_as(F), ctypes.c_float(float(b3)),
                         int(w1.shape[1]), int(w2.shape[1]))
    _da_nap_mang = bool(ok)
    return _da_nap_mang


def da_nap_mang() -> bool:
    return _da_nap_mang


def nnue_danh_gia(board: Board, side: str) -> int:
    return _nap().qs_nnue_danh_gia(_sang_c(board), 1 if side == WHITE else 0)


def danh_gia_tron(board: Board, side: str, trong_so: float, lech: float) -> int:
    """Ham danh gia hoan chinh: thu cong + mang + tron, mot lan goi duy nhat."""
    return _nap().qs_danh_gia_tron(_sang_c(board), 1 if side == WHITE else 0,
                                   trong_so, lech)
