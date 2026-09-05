"""
QiSheng - ban co bang BIT, tang toc sinh nuoc di va phat hien chieu.

Vi sao lam duoc trong Python thuan: ban co tuong co 90 o, ma so nguyen Python
la so lon vo han - ca ban co nhet vua MOT bien int. Moi phep dich, AND, OR tren
do chay bang toc do C chu khong phai toc do vong lap Python.

Ho so chay cho thay generate_pseudo_moves chiem 30% va is_square_attacked chiem
25% thoi gian tim kiem, deu la vong lap Python quet tung o. Day la cho de thay.

HAI CACH DANH SO O:
    thuong    sq  = r * 9 + c    (0..89)  - moi HANG la 9 bit lien nhau
    chuyen vi sqT = c * 10 + r   (0..89)  - moi COT la 10 bit lien nhau

Giu ca hai vi lay "the co tren hang" chi can (occ >> r*9) & 511, nhung lay
"the co tren cot" theo cach thuong phai thu 10 bit roi - rat cham. Voi ban
chuyen vi thi thanh (occT >> c*10) & 1023, cung mot phep dich.

Bang tra duoc tinh san mot lan luc nap module, tong khoang 24.000 muc - du nho
de tinh trong chua toi mot giay.
"""

from typing import Dict, List, Tuple

# --------------------------------------------------------------------------
# Danh so o
# --------------------------------------------------------------------------

def o(r: int, c: int) -> int:
    return r * 9 + c


def o_chuyen_vi(r: int, c: int) -> int:
    return c * 10 + r


TOAN_BAN = (1 << 90) - 1

# --------------------------------------------------------------------------
# Bang tra cho quan di theo TIA (Xe va Phao)
# --------------------------------------------------------------------------
# HANG_XE[c][the_co_9bit]  -> mat na 9 bit cac o Xe voi toi tren hang do
# COT_XE[r][the_co_10bit]  -> mat na 10 bit cac o Xe voi toi tren cot do
# Phao khac o cho: no can dung MOT quan lam ngoi roi moi an duoc quan sau ngoi.

def _tia_xe(vi_tri: int, the_co: int, do_dai: int) -> int:
    """Xe: di tiep toi khi gap quan; o co quan dau tien thi vao duoc (an)."""
    mat_na = 0
    for buoc in (1, -1):
        i = vi_tri + buoc
        while 0 <= i < do_dai:
            mat_na |= 1 << i
            if the_co & (1 << i):
                break
            i += buoc
    return mat_na


def _tia_phao(vi_tri: int, the_co: int, do_dai: int) -> Tuple[int, int]:
    """Phao: tra ve (o di duoc, o an duoc).

    O di duoc  = cac o trong lien tiep (chua gap quan nao).
    O an duoc  = o cua quan dau tien SAU khi da nhay qua dung mot quan lam ngoi.
    """
    di, an = 0, 0
    for buoc in (1, -1):
        i = vi_tri + buoc
        while 0 <= i < do_dai and not (the_co & (1 << i)):
            di |= 1 << i
            i += buoc
        # i dang o ngoi (hoac ngoai bien)
        if 0 <= i < do_dai:
            j = i + buoc
            while 0 <= j < do_dai and not (the_co & (1 << j)):
                j += buoc
            if 0 <= j < do_dai:
                an |= 1 << j
    return di, an


HANG_XE: List[List[int]] = [[0] * 512 for _ in range(9)]
HANG_PHAO_DI: List[List[int]] = [[0] * 512 for _ in range(9)]
HANG_PHAO_AN: List[List[int]] = [[0] * 512 for _ in range(9)]
for _c in range(9):
    for _t in range(512):
        HANG_XE[_c][_t] = _tia_xe(_c, _t, 9)
        HANG_PHAO_DI[_c][_t], HANG_PHAO_AN[_c][_t] = _tia_phao(_c, _t, 9)

COT_XE: List[List[int]] = [[0] * 1024 for _ in range(10)]
COT_PHAO_DI: List[List[int]] = [[0] * 1024 for _ in range(10)]
COT_PHAO_AN: List[List[int]] = [[0] * 1024 for _ in range(10)]
for _r in range(10):
    for _t in range(1024):
        COT_XE[_r][_t] = _tia_xe(_r, _t, 10)
        COT_PHAO_DI[_r][_t], COT_PHAO_AN[_r][_t] = _tia_phao(_r, _t, 10)

# BUNG_COT[c][mat_na_10bit] -> bitboard THUONG cua cac o do tren cot c.
# Can buoc nay vi bang cot cho ket qua o he chuyen vi, phai doi ve he thuong
# moi ghep duoc voi cac bitboard khac.
BUNG_COT: List[List[int]] = [[0] * 1024 for _ in range(9)]
for _c in range(9):
    for _m in range(1024):
        _bb = 0
        _x = _m
        while _x:
            _r = (_x & -_x).bit_length() - 1
            _bb |= 1 << (_r * 9 + _c)
            _x &= _x - 1
        BUNG_COT[_c][_m] = _bb

# BUNG_HANG[r][mat_na_9bit] -> bitboard THUONG cua cac o do tren hang r.
BUNG_HANG: List[List[int]] = [[0] * 512 for _ in range(10)]
for _r in range(10):
    for _m in range(512):
        BUNG_HANG[_r][_m] = _m << (_r * 9)
